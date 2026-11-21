"""Versioned Gemma NF4 dtype pilot; legacy pilot/runtime hashes remain intact."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import re
import time
from typing import Literal

from PIL import Image
import yaml

from .environment import inspect_environment
from .io_utils import atomic_bytes, read_manifest, sha256_file, write_json
from .parse import parse_response
from . import parse as parser_module
from . import pilot_runtime as legacy
from .qa import validate_manifest
from .reviews import canonical_hash


class GemmaDiagnosticConfig(legacy.PilotRunConfig):
    precision: Literal["nf4_fp16", "nf4_bf16"]
    trace_version: Literal["gemma_token_logits_v1"]


def dtype_settings(precision: str, torch):
    if precision not in {"nf4_fp16", "nf4_bf16"}:
        raise ValueError("Use explicit nf4_fp16 or nf4_bf16; no automatic fallback")
    if precision == "nf4_bf16" and not torch.cuda.is_bf16_supported():
        raise RuntimeError("GPU does not support BF16; no automatic FP16 fallback")
    dtype = torch.bfloat16 if precision == "nf4_bf16" else torch.float16
    return dtype


def split_terminal_eos(token_ids: list[int], eos_token_ids: int | list[int]):
    """Separate one model-declared terminal EOS; never strip words/internal tokens."""
    eos = {eos_token_ids} if isinstance(eos_token_ids, int) else set(eos_token_ids)
    if token_ids and token_ids[-1] in eos:
        return token_ids[:-1], [token_ids[-1]]
    return token_ids[:], []


class GemmaTraceAdapter:
    def __init__(self, spec, config, *, offline: bool):
        self.spec, self.config, self.offline = spec, config, offline
        self.model = self.processor = self.torch = None

    def load_model(self):
        import torch
        from transformers import AutoProcessor, BitsAndBytesConfig, Gemma3ForConditionalGeneration

        if importlib.metadata.version("transformers") != "4.57.1":
            raise RuntimeError("Use pinned transformers==4.57.1 for this diagnostic")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU required; no automatic CPU fallback")
        self.torch = torch
        self.dtype = dtype_settings(self.config.precision, torch)
        torch.manual_seed(self.config.seed)
        torch.cuda.manual_seed_all(self.config.seed)
        shared = dict(revision=self.spec["revision"], trust_remote_code=False,
                      local_files_only=self.offline, token=os.environ.get("HF_TOKEN") or None)
        self.processor = AutoProcessor.from_pretrained(
            self.spec["model_id"], do_pan_and_scan=False, use_fast=False, **shared)
        quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                         bnb_4bit_use_double_quant=True,
                                         bnb_4bit_compute_dtype=self.dtype)
        self.model = Gemma3ForConditionalGeneration.from_pretrained(
            self.spec["model_id"], torch_dtype=self.dtype, device_map={"": 0},
            attn_implementation=self.config.attention, quantization_config=quantization, **shared).eval()

    def generate(self, image, prompt):
        torch = self.torch
        torch.cuda.reset_peak_memory_stats(0)
        torch.cuda.synchronize(0)
        started = time.perf_counter()
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[image], return_tensors="pt", add_special_tokens=False)
        inputs = inputs.to("cuda:0", dtype=self.dtype)
        input_length = inputs["input_ids"].shape[-1]
        with torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=False, max_new_tokens=self.config.max_new_tokens,
                                         return_dict_in_generate=True, output_logits=True)
        torch.cuda.synchronize(0)
        elapsed_ms = (time.perf_counter() - started) * 1000
        peak = torch.cuda.max_memory_allocated(0) / 1024 ** 2
        if not torch.equal(output.sequences[:, :input_length], inputs["input_ids"]):
            raise RuntimeError("Generated sequence does not retain input prefix; refusing an unverified slice")
        new_tokens = output.sequences[:, input_length:]
        ids = new_tokens[0].detach().cpu().tolist()
        # This pinned tokenizer does not flag end_of_turn (106) as special.
        # Use the model's EOS definition, retaining every original ID in trace.
        content_ids, terminal_eos = split_terminal_eos(ids, self.model.generation_config.eos_token_id)
        raw = self.processor.batch_decode([content_ids], skip_special_tokens=True,
                                          clean_up_tokenization_spaces=False)[0]
        with_special = self.processor.batch_decode(new_tokens, skip_special_tokens=False,
                                                   clean_up_tokenization_spaces=False)[0]
        logits = output.logits
        if logits is None or len(logits) != len(ids):
            raise RuntimeError("Expected one raw-logit tensor for each generated token")
        steps = [{"n_values": step.numel(), "n_nan": int(torch.isnan(step).sum().item()),
                  "n_posinf": int(torch.isposinf(step).sum().item()),
                  "n_neginf": int(torch.isneginf(step).sum().item()),
                  "all_finite": bool(torch.isfinite(step).all().item())} for step in logits]
        trace = {"version": self.config.trace_version, "input_token_count": input_length,
                 "generated_token_ids": ids, "decoded_with_special_tokens": with_special,
                 "content_token_ids": content_ids, "terminal_eos_token_ids": terminal_eos,
                 "generated_token_count": len(ids), "raw_logits_by_step": steps,
                 "all_raw_logits_finite": all(step["all_finite"] for step in steps),
                 "model_dtype": str(self.dtype), "compute_dtype": str(self.dtype),
                 "pixel_values_dtype": str(inputs["pixel_values"].dtype),
                 "pixel_values_shape": list(inputs["pixel_values"].shape),
                 "input_prefix_verified": True}
        return {"raw_response": raw, "elapsed_ms": elapsed_ms, "peak_allocated_mib": peak,
                "generation_trace": trace}

    def unload_model(self):
        self.model = self.processor = None
        gc.collect()
        if self.torch is not None and self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()


def run_gemma_pilot(*, root: Path, config_path: Path, output: Path, limit: int = 2,
                    platform_name: str = "local", dry_run: bool = False, resume: bool = False,
                    retry_failed: bool = False, offline: bool = True, adapter_factory=GemmaTraceAdapter):
    """Bounded 1–10 row diagnostic/pilot with explicit dtype and auditable resume."""
    if not 1 <= limit <= 10:
        raise ValueError("Gemma dtype pilot limit must be 1–10 rows")
    if platform_name not in {"local", "colab", "kaggle"} or output.suffix != ".jsonl":
        raise ValueError("Use local/colab/kaggle and a .jsonl output")
    config = GemmaDiagnosticConfig.model_validate(yaml.safe_load(config_path.read_text(encoding="utf-8")))
    manifest_path, prompts_path, models_path = (root / config.manifest, root / config.prompts, root / config.models)
    rows = read_manifest(manifest_path)
    validation = validate_manifest(rows, root=root, mode="pilot")
    if not validation["valid"] or any(row.task != "object_existence" or row.source_dataset != "repope" for row in rows):
        raise ValueError("Gemma diagnostic requires technically valid RePOPE pilot rows")
    if any(not row.question_vi or row.translation_status != "approved" or
           row.metadata.get("upstream_verification", {}).get("status") != "matched" for row in rows):
        raise ValueError("Pilot needs language-approved pairs and matched upstream provenance")
    prompts = yaml.safe_load(prompts_path.read_text(encoding="utf-8"))
    spec = yaml.safe_load(models_path.read_text(encoding="utf-8"))["models"]["gemma"]
    if not re.fullmatch(r"[0-9a-f]{40}", spec.get("revision") or ""):
        raise ValueError("Pin exact Gemma model revision")
    selected = legacy.select_smoke_rows(rows, limit)
    protocol = {"settings": config.model_dump(), "manifest_sha256": sha256_file(manifest_path),
                "prompts_sha256": sha256_file(prompts_path), "model": spec,
                "prompt_version": prompts["prompt_version"], "implementation_sha256": sha256_file(Path(__file__)),
                "legacy_helpers_sha256": sha256_file(Path(legacy.__file__)),
                "parser_sha256": sha256_file(Path(parser_module.__file__))}
    protocol_hash = canonical_hash(protocol)
    queue = [(row, lang) for row in selected for lang in ("en", "vi")]
    plan = {"model": "gemma", "platform": platform_name, "protocol_hash": protocol_hash,
            "selected_rows": len(selected), "expected_inferences": len(queue),
            "sample_ids": [row.sample_id for row in selected], "dry_run": dry_run,
            "image_qa_status": dict(Counter(row.qa_status for row in selected)), "scope": config.scope,
            "model_revision": spec["revision"], "precision": config.precision,
            "runner": "gemma_dtype_trace_v1"}
    if dry_run:
        return plan
    environment = inspect_environment()
    fingerprint = {key: environment[key] for key in ("python", "os", "packages", "gpus")}
    run_hash = canonical_hash({"protocol_hash": protocol_hash, "platform": platform_name, "environment": fingerprint})
    metadata_path = output.with_suffix(".meta.json")
    existing = legacy._read_predictions(output)
    if existing and not resume:
        raise ValueError("Output exists; use --resume or a new output path")
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata["run_config_hash"] != run_hash:
            raise ValueError("Output belongs to a different model/config/platform/runtime; use a new output path")
    elif existing:
        raise ValueError("Prediction metadata missing; restore it before resume")
    else:
        write_json(metadata_path, {**plan, "run_config_hash": run_hash, "protocol": protocol,
                                   "environment": environment, "offline": offline,
                                   "measurement_note": "processor+generation with raw-logit retention; excludes CPU trace/decode and model load"})
    if any(record.get("run_config_hash") != run_hash for record in existing):
        raise ValueError("Checkpoint contains predictions from another run")
    by_key = defaultdict(list)
    for record in existing:
        by_key[(record["sample_id"], record["language"])].append(record)
    pending = [(row, lang) for row, lang in queue
               if not any(r["run_status"] == "success" for r in by_key[(row.sample_id, lang)])
               and (retry_failed or not by_key[(row.sample_id, lang)])]
    adapter = adapter_factory(spec, config, offline=offline)
    stop_reason = None
    try:
        if pending:
            adapter.load_model()
        for row, language in pending:
            prompt = prompts[row.task][language].format(question=getattr(row, f"question_{language}"))
            record = {"experiment_id": config.experiment_id, "sample_id": row.sample_id,
                      "source_dataset": row.source_dataset, "task": row.task, "image_id": row.image_id,
                      "image_sha256": row.image_sha256, "language": language, "model_id": spec["model_id"],
                      "model_revision": spec["revision"], "processor_revision": spec["revision"],
                      "platform": platform_name, "precision": config.precision,
                      "prompt_version": prompts["prompt_version"], "prompt_text": prompt,
                      "ground_truth": row.ground_truth, "protocol_hash": protocol_hash,
                      "run_config_hash": run_hash, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                      "qa_status": row.qa_status, "translation_status": row.translation_status, "scope": config.scope,
                      "attempt": len(by_key[(row.sample_id, language)]) + 1,
                      "image_preprocess": {"policy_id": "rgb_thumbnail_lanczos_v1", "max_edge": config.image_max_edge,
                                           "qwen_min_pixels": config.qwen_min_pixels, "qwen_max_pixels": config.qwen_max_pixels},
                      "raw_response": None, "parsed_prediction": None, "parse_status": "not_attempted",
                      "elapsed_ms": None, "peak_allocated_mib": None, "error": None}
            try:
                with Image.open(root / row.image_path) as original:
                    image = original.convert("RGB")
                image.thumbnail((config.image_max_edge, config.image_max_edge), Image.Resampling.LANCZOS)
                result = adapter.generate(image, prompt)
                record.update(result)
                if not result["generation_trace"]["all_raw_logits_finite"]:
                    record.update(run_status="failed", error={"type": "NonFiniteLogits",
                                  "message": "Raw generation logits contain NaN/Inf; raw output and token trace retained"})
                else:
                    parsed = parse_response(result["raw_response"], row.task)
                    record.update(parsed_prediction=parsed.prediction, parse_status=parsed.status,
                                  parse_reason=parsed.reason, used_alias=parsed.used_alias, run_status="success")
            except Exception as exc:
                record.update(run_status="failed", error=legacy.safe_error(exc))
                if "outofmemory" in type(exc).__name__.lower() or "out of memory" in str(exc).lower():
                    stop_reason = "stopped_after_oom_no_automatic_config_change"
            existing.append(record)
            by_key[(row.sample_id, language)].append(record)
            atomic_bytes(output, ("".join(json.dumps(item, ensure_ascii=False, allow_nan=False) + "\n"
                                           for item in existing)).encode("utf-8"))
            if stop_reason:
                break
    except Exception as exc:
        write_json(output.with_suffix(".load_error.json"), {"phase": "model_load_or_run",
                   "error": legacy.safe_error(exc), **plan})
        raise RuntimeError("Gemma diagnostic load/run failed; see sanitized .load_error.json") from None
    finally:
        adapter.unload_model()
    latest = [by_key[(row.sample_id, lang)][-1] for row, lang in queue if by_key[(row.sample_id, lang)]]
    summary = {**plan, "dry_run": False, "run_config_hash": run_hash, "stop_reason": stop_reason,
               "success": sum(r["run_status"] == "success" for r in latest),
               "valid": sum(r["run_status"] == "success" and r["parse_status"] == "valid" for r in latest),
               "invalid": sum(r["run_status"] == "success" and r["parse_status"] == "invalid" for r in latest),
               "nonfinite": sum(r.get("generation_trace", {}).get("all_raw_logits_finite") is False for r in latest),
               "failed": sum(r["run_status"] == "failed" for r in latest), "missing": len(queue) - len(latest),
               "total_attempts_in_file": len(existing), "output": output.as_posix()}
    write_json(output.with_suffix(".summary.json"), summary)
    return summary
