import json
from pathlib import Path

import pytest
import yaml

from vlmbench.io_utils import read_manifest, write_manifest
from vlmbench.pilot_runtime import run_pilot, safe_error


@pytest.fixture
def runtime_project(row_factory, tmp_path, monkeypatch):
    rows = []
    for index, (category, truth) in enumerate((c, a) for c in ("random", "popular", "adversarial") for a in ("yes", "no")):
        rows.append(row_factory(sample_id=f"synthetic_test_only_{index}", image_id=f"{index:012}", category=category,
                                ground_truth=truth, question_vi="Trong ảnh có con chó nào không?", translation_status="approved",
                                metadata={"synthetic_test_only": True, "upstream_verification": {"status": "matched"}}))
    write_manifest(tmp_path / "manifest.csv", rows)
    (tmp_path / "prompts.yaml").write_text(yaml.safe_dump({"prompt_version": "synthetic_test_only", "object_existence": {"en": "{question} YES/NO", "vi": "{question} YES/NO"}}), encoding="utf-8")
    (tmp_path / "models.yaml").write_text(yaml.safe_dump({"models": {name: {"model_id": f"synthetic_test_only_{name}", "revision": "a" * 40} for name in ("qwen", "gemma")}}), encoding="utf-8")
    config = dict(experiment_id="synthetic_test_only", manifest="manifest.csv", prompts="prompts.yaml", models="models.yaml", seed=42,
                  precision="nf4_fp16", attention="eager", max_new_tokens=8, image_max_edge=512,
                  qwen_min_pixels=200704, qwen_max_pixels=401408, scope="engineering_pilot_image_qa_pending")
    (tmp_path / "run.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr("vlmbench.pilot_runtime.inspect_environment", lambda: {"python": "synthetic_test_only", "os": "test", "packages": {}, "gpus": []})
    return dict(root=tmp_path, config_path=tmp_path / "run.yaml", alias="qwen", platform_name="local", output=tmp_path / "predictions.jsonl")


class FakeAdapter:
    calls = 0
    loads = 0
    def __init__(self, *args):
        pass
    def load_model(self):
        type(self).loads += 1
    def generate(self, image, prompt):
        type(self).calls += 1
        return {"raw_response": "YES", "elapsed_ms": 1.0, "peak_allocated_mib": 1.0}
    def unload_model(self):
        pass


def test_dry_run_same_protocol_on_all_three_platforms_without_outputs(runtime_project):
    hashes = []
    for platform in ("local", "colab", "kaggle"):
        options = {**runtime_project, "platform_name": platform}
        plan = run_pilot(**options, dry_run=True)
        hashes.append(plan["protocol_hash"])
        assert plan["expected_inferences"] == 4
        assert not options["output"].exists()
        assert not options["output"].with_suffix(".meta.json").exists()
    assert len(set(hashes)) == 1


def test_resume_never_duplicates_successful_predictions(runtime_project):
    FakeAdapter.calls = FakeAdapter.loads = 0
    first = run_pilot(**runtime_project, adapter_factory=FakeAdapter)
    assert first["success"] == 4 and FakeAdapter.calls == 4
    again = run_pilot(**runtime_project, adapter_factory=FakeAdapter, resume=True)
    assert again["total_attempts_in_file"] == 4 and FakeAdapter.calls == 4 and FakeAdapter.loads == 1
    records = [json.loads(line) for line in runtime_project["output"].read_text(encoding="utf-8").splitlines()]
    assert {record["qa_status"] for record in records} == {"pending"}
    assert len({(record["sample_id"],record["language"]) for record in records}) == 4


def test_failed_record_only_retried_explicitly(runtime_project):
    class FailsOnce(FakeAdapter):
        calls = 0
        def generate(self, image, prompt):
            type(self).calls += 1
            if type(self).calls == 1:
                raise ValueError("synthetic_test_only failure")
            return {"raw_response": "NO", "elapsed_ms": 1, "peak_allocated_mib": 1}
    result = run_pilot(**runtime_project, adapter_factory=FailsOnce)
    assert result["failed"] == 1 and result["success"] == 3
    assert run_pilot(**runtime_project, adapter_factory=FakeAdapter, resume=True)["failed"] == 1
    retried = run_pilot(**runtime_project, adapter_factory=FakeAdapter, resume=True, retry_failed=True)
    assert retried["success"] == 4 and retried["total_attempts_in_file"] == 5


def test_oom_stops_without_silent_precision_change(runtime_project):
    class OOM(FakeAdapter):
        def generate(self, image, prompt):
            raise RuntimeError("CUDA out of memory synthetic_test_only")
    result = run_pilot(**runtime_project, adapter_factory=OOM)
    assert result["failed"] == 1 and result["missing"] == 3
    assert result["precision"] == "nf4_fp16" and "oom" in result["stop_reason"]


def test_invalid_generated_answer_remains_auditable_and_is_not_regenerated(runtime_project):
    class Invalid(FakeAdapter):
        def generate(self, image, prompt):
            return {"raw_response": "yes and no", "elapsed_ms": 1, "peak_allocated_mib": 1}
    result = run_pilot(**runtime_project, adapter_factory=Invalid)
    assert result["invalid"] == result["success"] == 4
    assert run_pilot(**runtime_project, adapter_factory=FakeAdapter, resume=True)["invalid"] == 4


def test_cross_platform_resume_to_same_file_rejected(runtime_project):
    run_pilot(**runtime_project, adapter_factory=FakeAdapter)
    with pytest.raises(ValueError, match="different"):
        run_pilot(**{**runtime_project, "platform_name": "colab"}, adapter_factory=FakeAdapter, resume=True)


def test_unapproved_translation_cannot_run(runtime_project):
    path = runtime_project["root"] / "manifest.csv"
    rows = read_manifest(path)
    data = rows[0].model_dump()
    data["translation_status"] = "requires_review"
    rows[0] = type(rows[0]).model_validate(data)
    write_manifest(path, rows)
    with pytest.raises(ValueError, match="language-approved"):
        run_pilot(**runtime_project, dry_run=True)


def test_model_load_error_is_redacted_and_not_faked_as_predictions(runtime_project):
    class BadLoad(FakeAdapter):
        def load_model(self):
            raise RuntimeError("HF failure hf_SYNTHETICSECRET at https://example.com/?token=secret")
    with pytest.raises(RuntimeError, match="load/run failed"):
        run_pilot(**runtime_project, adapter_factory=BadLoad)
    assert not runtime_project["output"].exists()
    report = runtime_project["output"].with_suffix(".load_error.json").read_text()
    assert "hf_SYNTHETICSECRET" not in report and "token=secret" not in report


@pytest.mark.parametrize("limit", [0, 31])
def test_pilot_does_not_expand_into_full_run(runtime_project, limit):
    with pytest.raises(ValueError, match="1–30"):
        run_pilot(**runtime_project, limit=limit, dry_run=True)
