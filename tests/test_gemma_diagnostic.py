import json
from types import SimpleNamespace

import pytest
import yaml

from vlmbench.cli import main
from vlmbench.gemma_diagnostic import dtype_settings, run_gemma_pilot, split_terminal_eos
from vlmbench.io_utils import read_manifest, write_manifest


@pytest.fixture
def gemma_project(row_factory, tmp_path, monkeypatch):
    rows = [row_factory(sample_id=f"synthetic_test_only_{i}", image_id=f"{i:012}", category=c,
                        ground_truth=t, question_vi="synthetic_test_only", translation_status="approved",
                        metadata={"synthetic_test_only": True, "upstream_verification": {"status": "matched"}})
            for i, (c, t) in enumerate((c, t) for c in ("random", "popular", "adversarial") for t in ("yes", "no"))]
    write_manifest(tmp_path / "manifest.csv", rows)
    (tmp_path / "prompts.yaml").write_text(yaml.safe_dump({"prompt_version": "synthetic_test_only",
        "object_existence": {"en": "{question} YES/NO", "vi": "{question} YES/NO"}}), encoding="utf-8")
    (tmp_path / "models.yaml").write_text(yaml.safe_dump({"models": {"gemma": {
        "model_id": "synthetic_test_only", "revision": "a" * 40}}}), encoding="utf-8")
    config = dict(experiment_id="synthetic_test_only", manifest="manifest.csv", prompts="prompts.yaml",
                  models="models.yaml", seed=42, precision="nf4_bf16", attention="eager", max_new_tokens=8,
                  image_max_edge=512, qwen_min_pixels=200704, qwen_max_pixels=401408,
                  scope="engineering_pilot_image_qa_pending", trace_version="gemma_token_logits_v1")
    (tmp_path / "run.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr("vlmbench.gemma_diagnostic.inspect_environment", lambda: {
        "python": "synthetic_test_only", "os": "test", "packages": {}, "gpus": []})
    return dict(root=tmp_path, config_path=tmp_path / "run.yaml", output=tmp_path / "predictions.jsonl")


class SyntheticAdapter:
    calls = 0
    loads = 0

    def __init__(self, spec, config, *, offline):
        assert offline is True

    def load_model(self):
        type(self).loads += 1

    def generate(self, image, prompt):
        type(self).calls += 1
        return {"raw_response": "YES", "elapsed_ms": 1.0, "peak_allocated_mib": 1.0,
                "generation_trace": {"all_raw_logits_finite": True, "generated_token_ids": [123],
                                     "synthetic_test_only": True}}

    def unload_model(self):
        pass


@pytest.mark.parametrize("precision,dtype", [("nf4_bf16", "BF16"), ("nf4_fp16", "FP16")])
def test_dtype_selection_is_explicit(precision, dtype):
    torch = SimpleNamespace(float16="FP16", bfloat16="BF16", cuda=SimpleNamespace(is_bf16_supported=lambda: True))
    assert dtype_settings(precision, torch) == dtype


def test_bf16_unsupported_never_falls_back_to_fp16():
    torch = SimpleNamespace(float16="FP16", bfloat16="BF16", cuda=SimpleNamespace(is_bf16_supported=lambda: False))
    with pytest.raises(RuntimeError, match="no automatic FP16 fallback"):
        dtype_settings("nf4_bf16", torch)


def test_unknown_precision_rejected():
    with pytest.raises(ValueError):
        dtype_settings("auto", None)


@pytest.mark.parametrize("ids,eos,content,terminal", [
    ([26915, 106], [1, 106], [26915], [106]),
    ([106, 26915], [1, 106], [106, 26915], []),
    ([0, 0, 0], [1, 106], [0, 0, 0], []),
    ([1], 1, [], [1]),
    ([], [1, 106], [], []),
    ([26915, 106, 106], [1, 106], [26915, 106], [106]),
])
def test_only_model_declared_terminal_eos_removed(ids, eos, content, terminal):
    original = ids[:]
    assert split_terminal_eos(ids, eos) == (content, terminal)
    assert ids == original


def test_dry_run_no_outputs_or_model(gemma_project):
    plan = run_gemma_pilot(**gemma_project, dry_run=True)
    assert plan["expected_inferences"] == 4 and plan["precision"] == "nf4_bf16"
    assert not gemma_project["output"].exists()
    assert not gemma_project["output"].with_suffix(".meta.json").exists()


@pytest.mark.parametrize("limit", [0, 11, 1000])
def test_diagnostic_cannot_expand_to_main(gemma_project, limit):
    with pytest.raises(ValueError, match="1–10"):
        run_gemma_pilot(**gemma_project, limit=limit, dry_run=True)


def test_dtype_has_distinct_protocol_and_cannot_resume_into_old_file(gemma_project):
    run_gemma_pilot(**gemma_project, adapter_factory=SyntheticAdapter)
    before = gemma_project["output"].read_bytes()
    bf16_plan = run_gemma_pilot(**gemma_project, dry_run=True)
    path = gemma_project["config_path"]
    config = yaml.safe_load(path.read_text())
    config["precision"] = "nf4_fp16"
    path.write_text(yaml.safe_dump(config))
    fp16_plan = run_gemma_pilot(**gemma_project, dry_run=True)
    assert bf16_plan["sample_ids"] == fp16_plan["sample_ids"]
    assert bf16_plan["protocol_hash"] != fp16_plan["protocol_hash"]
    with pytest.raises(ValueError, match="different"):
        run_gemma_pilot(**gemma_project, resume=True, adapter_factory=SyntheticAdapter)
    assert gemma_project["output"].read_bytes() == before


def test_resume_and_expand_retains_token_traces_without_duplicate_calls(gemma_project):
    SyntheticAdapter.calls = SyntheticAdapter.loads = 0
    first = run_gemma_pilot(**gemma_project, adapter_factory=SyntheticAdapter)
    assert first["valid"] == 4
    assert run_gemma_pilot(**gemma_project, resume=True, adapter_factory=SyntheticAdapter)["valid"] == 4
    assert SyntheticAdapter.calls == 4 and SyntheticAdapter.loads == 1
    expanded = run_gemma_pilot(**gemma_project, limit=4, resume=True, adapter_factory=SyntheticAdapter)
    assert expanded["valid"] == 8 and SyntheticAdapter.calls == 8
    records = [json.loads(line) for line in gemma_project["output"].read_text().splitlines()]
    assert len({(r["sample_id"], r["language"]) for r in records}) == 8
    assert all(r["generation_trace"]["generated_token_ids"] == [123] and r["qa_status"] == "pending" for r in records)


def test_nonfinite_logits_never_scored_as_valid_even_when_decoded_yes(gemma_project):
    class NonFinite(SyntheticAdapter):
        def generate(self, image, prompt):
            result = super().generate(image, prompt)
            result["generation_trace"]["all_raw_logits_finite"] = False
            return result
    report = run_gemma_pilot(**gemma_project, adapter_factory=NonFinite)
    assert report["failed"] == report["nonfinite"] == 4 and report["valid"] == 0
    records = [json.loads(line) for line in gemma_project["output"].read_text().splitlines()]
    assert all(r["raw_response"] == "YES" and r["parsed_prediction"] is None and
               r["parse_status"] == "not_attempted" and r["error"]["type"] == "NonFiniteLogits" for r in records)
    calls = SyntheticAdapter.calls
    assert run_gemma_pilot(**gemma_project, resume=True, adapter_factory=SyntheticAdapter)["failed"] == 4
    assert SyntheticAdapter.calls == calls
    assert run_gemma_pilot(**gemma_project, resume=True, retry_failed=True,
                           adapter_factory=SyntheticAdapter)["total_attempts_in_file"] == 8


def test_finite_empty_answer_is_preserved_as_invalid_not_retried(gemma_project):
    class Empty(SyntheticAdapter):
        def generate(self, image, prompt):
            return {**super().generate(image, prompt), "raw_response": ""}
    first = run_gemma_pilot(**gemma_project, adapter_factory=Empty)
    assert first["success"] == first["invalid"] == 4 and first["failed"] == 0
    assert run_gemma_pilot(**gemma_project, resume=True, adapter_factory=SyntheticAdapter)["invalid"] == 4


def test_oom_stops_and_preserves_partial_run(gemma_project):
    class OOM(SyntheticAdapter):
        def generate(self, image, prompt):
            raise RuntimeError("CUDA out of memory synthetic_test_only")
    report = run_gemma_pilot(**gemma_project, adapter_factory=OOM)
    assert report["failed"] == 1 and report["missing"] == 3
    assert "oom" in report["stop_reason"] and report["precision"] == "nf4_bf16"


def test_translation_gate_not_bypassed(gemma_project):
    path = gemma_project["root"] / "manifest.csv"
    rows = read_manifest(path)
    rows[0] = rows[0].model_copy(update={"translation_status": "requires_review"})
    write_manifest(path, rows)
    with pytest.raises(ValueError, match="language-approved"):
        run_gemma_pilot(**gemma_project, dry_run=True)


def test_offline_load_error_redacted_without_fake_predictions(gemma_project):
    class BadLoad(SyntheticAdapter):
        def load_model(self):
            raise RuntimeError("synthetic hf_SECRET at https://example.com/?token=secret")
    with pytest.raises(RuntimeError, match="diagnostic load/run failed"):
        run_gemma_pilot(**gemma_project, adapter_factory=BadLoad)
    assert not gemma_project["output"].exists()
    error = gemma_project["output"].with_suffix(".load_error.json").read_text()
    assert "hf_SECRET" not in error and "token=secret" not in error


def test_cli_dry_run_requires_no_inference_dependency_or_writes(gemma_project, capsys):
    assert main(["--root", str(gemma_project["root"]), "infer-gemma-trace", "--config", "run.yaml",
                 "--output", "new.jsonl", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["runner"] == "gemma_dtype_trace_v1"
    assert not (gemma_project["root"] / "new.meta.json").exists()
