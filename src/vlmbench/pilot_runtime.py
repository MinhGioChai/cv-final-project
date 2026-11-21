"""Bounded portable pilot inference. Heavy dependencies are imported only on real runs."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Literal

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field
import yaml

from .environment import inspect_environment
from .io_utils import atomic_bytes, read_manifest, sha256_file, write_json
from .parse import parse_response
from . import parse as parser_module
from .qa import validate_manifest
from .reviews import canonical_hash
from .sampling import STRATA


class PilotRunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    experiment_id: str = Field(min_length=1)
    manifest: str = Field(min_length=1)
    prompts: str
    models: str
    seed: int
    precision: Literal["nf4_fp16", "fp16"]
    attention: Literal["eager", "sdpa"]
    max_new_tokens: int = Field(ge=1, le=32)
    image_max_edge: int = Field(ge=224, le=1024)
    qwen_min_pixels: int = Field(ge=784)
    qwen_max_pixels: int = Field(ge=784)
    scope: Literal["engineering_pilot_image_qa_pending"]


def select_smoke_rows(rows: list, limit: int) -> list:
    if limit < 1 or limit > 30:
        raise ValueError("Pilot limit must be 1–30 rows; no full-run command is enabled")
    buckets: dict = defaultdict(list)
    for row in sorted(rows, key=lambda item: item.sample_id):
        buckets[(row.category, row.ground_truth)].append(row)
    selected = []
    while len(selected) < min(limit, len(rows)):
        for key in STRATA:
            if buckets[key] and len(selected) < limit:
                selected.append(buckets[key].pop(0))
        if not any(buckets.values()):
            break
    return selected


def safe_error(exc: Exception) -> dict[str, str]:
    message = re.sub(r"hf_[A-Za-z0-9]+", "<redacted-token>", str(exc))
    message = re.sub(r"https?://\S+", "<url>", message)
    return {"type": type(exc).__name__, "message": message[:1000]}


class HuggingFaceAdapter:
    """One model per process, single GPU, no automatic precision/offload fallback."""
    def __init__(self, alias: str, model: dict[str, Any], config: PilotRunConfig):
        self.alias, self.spec, self.config = alias, model, config
        self.model = self.processor = self.torch = None

    def load_model(self) -> None:
        try:
            import torch
            from transformers import AutoProcessor, BitsAndBytesConfig, Gemma3ForConditionalGeneration, Qwen2_5_VLForConditionalGeneration
        except ImportError as exc:
            raise RuntimeError("Inference dependencies missing. Run scripts/setup_inference.py or the notebook setup cell") from exc
        if importlib.metadata.version("transformers") != "4.57.1":
            raise RuntimeError("Use the pinned transformers==4.57.1 environment for this pilot")
        if not torch.cuda.is_available():
            raise RuntimeError("No CUDA GPU is available in this Python runtime. Enable a GPU session or check the CUDA PyTorch install")
        self.torch = torch
        torch.manual_seed(self.config.seed)
        torch.cuda.manual_seed_all(self.config.seed)
        token = os.environ.get("HF_TOKEN") or None
        processor_kwargs = {"revision": self.spec["revision"], "token": token, "trust_remote_code": False}
        if self.alias == "qwen":
            processor_kwargs.update(min_pixels=self.config.qwen_min_pixels, max_pixels=self.config.qwen_max_pixels)
        else:
            processor_kwargs.update(do_pan_and_scan=False)
        self.processor = AutoProcessor.from_pretrained(self.spec["model_id"], **processor_kwargs)
        kwargs = {"revision": self.spec["revision"], "token": token, "trust_remote_code": False,
                  "torch_dtype": torch.float16, "device_map": {"": 0}, "attn_implementation": self.config.attention}
        if self.config.precision == "nf4_fp16":
            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                              bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)
        cls = Qwen2_5_VLForConditionalGeneration if self.alias == "qwen" else Gemma3ForConditionalGeneration
        self.model = cls.from_pretrained(self.spec["model_id"], **kwargs).eval()

    def generate(self, image: Image.Image, prompt: str) -> dict[str, Any]:
        torch = self.torch
        torch.cuda.reset_peak_memory_stats(0)
        torch.cuda.synchronize(0)
        started = time.perf_counter()
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[image], return_tensors="pt", add_special_tokens=False)
        inputs = inputs.to("cuda:0", dtype=torch.float16)
        with torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=False, max_new_tokens=self.config.max_new_tokens)
        raw = self.processor.batch_decode(output[:, inputs["input_ids"].shape[-1]:], skip_special_tokens=True,
                                          clean_up_tokenization_spaces=False)[0]
        torch.cuda.synchronize(0)
        return {"raw_response": raw, "elapsed_ms": (time.perf_counter() - started) * 1000,
                "peak_allocated_mib": torch.cuda.max_memory_allocated(0) / 1024 ** 2}

    def unload_model(self) -> None:
        self.model = self.processor = None
        gc.collect()
        if self.torch is not None and self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()


def _read_predictions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            records.append(json.loads(text))
        except ValueError as exc:
            raise ValueError(f"Corrupt prediction JSONL at line {line}; preserve and repair the file before resume") from exc
    return records


def run_pilot(
    *, root: Path, config_path: Path, alias: str, platform_name: str, output: Path, limit: int = 2,
    languages: tuple[str, ...] = ("en", "vi"), dry_run: bool = False, resume: bool = False,
    retry_failed: bool = False, adapter_factory=HuggingFaceAdapter,
) -> dict[str, Any]:
    if alias not in {"qwen", "gemma"} or platform_name not in {"local", "colab", "kaggle"}:
        raise ValueError("Choose qwen/gemma and local/colab/kaggle")
    if output.suffix != ".jsonl":
        raise ValueError("Prediction output must use a .jsonl path")
    if not languages or len(set(languages)) != len(languages) or set(languages) - {"en", "vi"}:
        raise ValueError("Languages must be unique en/vi values")
    config = PilotRunConfig.model_validate(yaml.safe_load(config_path.read_text(encoding="utf-8")))
    if config.qwen_min_pixels > config.qwen_max_pixels:
        raise ValueError("Invalid Qwen pixel bounds")
    manifest_path = root / config.manifest
    rows = read_manifest(manifest_path)
    validation = validate_manifest(rows, root=root, mode="pilot")
    if not validation["valid"] or any(row.task != "object_existence" or row.source_dataset != "repope" for row in rows):
        raise ValueError("Portable runner accepts only technically valid RePOPE pilot rows")
    if any(not row.question_vi or row.translation_status != "approved"
           or row.metadata.get("upstream_verification", {}).get("status") != "matched" for row in rows):
        raise ValueError("Pilot needs language-approved EN–VI pairs and matched upstream provenance")
    prompts_path, models_path = root / config.prompts, root / config.models
    prompts = yaml.safe_load(prompts_path.read_text(encoding="utf-8"))
    spec = yaml.safe_load(models_path.read_text(encoding="utf-8"))["models"][alias]
    if not re.fullmatch(r"[0-9a-f]{40}", spec.get("revision") or ""):
        raise ValueError("Pin an exact model revision before running")
    selected = select_smoke_rows(rows, limit)
    protocol = {"settings": config.model_dump(), "manifest_sha256": sha256_file(manifest_path),
                "prompts_sha256": sha256_file(prompts_path), "model": spec, "prompt_version": prompts["prompt_version"]}
    protocol["implementation_sha256"] = sha256_file(Path(__file__))
    protocol["parser_sha256"] = sha256_file(Path(parser_module.__file__))
    protocol_hash = canonical_hash(protocol)
    queue = [(row, language) for row in selected for language in languages]
    plan = {"model": alias, "platform": platform_name, "protocol_hash": protocol_hash, "selected_rows": len(selected),
            "expected_inferences": len(queue), "sample_ids": [row.sample_id for row in selected], "dry_run": dry_run,
            "image_qa_status": dict(Counter(row.qa_status for row in selected)), "scope": config.scope,
            "model_revision": spec["revision"], "precision": config.precision}
    if dry_run:
        return plan
    # Different model/platform/runtime settings never share a checkpoint file.
    environment = inspect_environment()
    fingerprint = {key: environment[key] for key in ("python", "os", "packages", "gpus")}
    run_hash = canonical_hash({"protocol_hash": protocol_hash, "platform": platform_name, "environment": fingerprint})
    metadata_path = output.with_suffix(".meta.json")
    existing = _read_predictions(output)
    if existing and not resume:
        raise ValueError("Output exists; pass --resume or use a new output path")
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata["run_config_hash"] != run_hash:
            raise ValueError("Output belongs to a different model/config/platform/runtime; use a new output path")
    elif existing:
        raise ValueError("Prediction metadata is missing; restore it before resume")
    else:
        write_json(metadata_path, {**plan, "run_config_hash": run_hash, "protocol": protocol, "environment": environment})
    if any(record.get("run_config_hash") != run_hash for record in existing):
        raise ValueError("Checkpoint contains predictions from another run")
    by_key: dict = defaultdict(list)
    for record in existing:
        by_key[(record["sample_id"], record["language"])].append(record)
    pending = [(row, lang) for row, lang in queue if not any(record["run_status"] == "success" for record in by_key[(row.sample_id, lang)])
               and (retry_failed or not by_key[(row.sample_id, lang)])]
    adapter = adapter_factory(alias, spec, config)
    stop_reason = None
    try:
        if pending:
            adapter.load_model()
        for row, language in pending:
            prompt = prompts[row.task][language].format(question=getattr(row, f"question_{language}"))
            record = {"experiment_id": config.experiment_id, "sample_id": row.sample_id, "source_dataset": row.source_dataset,
                      "task": row.task, "image_id": row.image_id, "image_sha256": row.image_sha256, "language": language,
                      "model_id": spec["model_id"], "model_revision": spec["revision"], "processor_revision": spec["revision"],
                      "platform": platform_name, "precision": config.precision, "prompt_version": prompts["prompt_version"],
                      "prompt_text": prompt, "ground_truth": row.ground_truth, "protocol_hash": protocol_hash,
                      "run_config_hash": run_hash, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                      "qa_status": row.qa_status, "translation_status": row.translation_status, "scope": config.scope,
                      "attempt": len(by_key[(row.sample_id, language)]) + 1,
                      "image_preprocess": {"policy_id": "rgb_thumbnail_lanczos_v1", "max_edge": config.image_max_edge,
                                           "qwen_min_pixels": config.qwen_min_pixels, "qwen_max_pixels": config.qwen_max_pixels},
                      "raw_response": None, "parsed_prediction": None, "parse_status": "not_attempted", "elapsed_ms": None,
                      "peak_allocated_mib": None, "error": None}
            try:
                with Image.open(root / row.image_path) as original:
                    image = original.convert("RGB")
                image.thumbnail((config.image_max_edge, config.image_max_edge), Image.Resampling.LANCZOS)
                result = adapter.generate(image, prompt)
                parsed = parse_response(result["raw_response"], row.task)
                record.update(result, parsed_prediction=parsed.prediction, parse_status=parsed.status,
                              parse_reason=parsed.reason, used_alias=parsed.used_alias, run_status="success")
            except Exception as exc:
                record.update(run_status="failed", error=safe_error(exc))
                if "outofmemory" in type(exc).__name__.lower() or "out of memory" in str(exc).lower():
                    stop_reason = "stopped_after_oom_no_automatic_config_change"
            existing.append(record)
            by_key[(row.sample_id, language)].append(record)
            # Small pilot only: atomic replacement protects even a single completed record.
            atomic_bytes(output, ("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in existing)).encode("utf-8"))
            if stop_reason:
                break
    except Exception as exc:
        write_json(output.with_suffix(".load_error.json"), {"phase": "model_load_or_run", "error": safe_error(exc), **plan})
        raise RuntimeError("Model load/run failed; see the sanitized .load_error.json report (Gemma may require accepted license + HF_TOKEN)") from None
    finally:
        adapter.unload_model()
    latest = [by_key[(row.sample_id, lang)][-1] for row, lang in queue if by_key[(row.sample_id, lang)]]
    summary = {**plan, "dry_run": False, "run_config_hash": run_hash, "stop_reason": stop_reason,
               "success": sum(item["run_status"] == "success" for item in latest),
               "invalid": sum(item["run_status"] == "success" and item["parse_status"] == "invalid" for item in latest),
               "failed": sum(item["run_status"] == "failed" for item in latest), "missing": len(queue) - len(latest),
               "total_attempts_in_file": len(existing), "output": output.as_posix()}
    write_json(output.with_suffix(".summary.json"), summary)
    return summary
