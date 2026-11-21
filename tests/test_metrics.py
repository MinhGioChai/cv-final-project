"""Synthetic test-only records with hand-calculated paired metrics."""
import json

import pytest

from vlmbench.cli import main
from vlmbench.evaluate import evaluate_run, pair_predictions, read_evaluation, read_predictions
from vlmbench.io_utils import write_manifest
from vlmbench.parse import parse_response


@pytest.fixture
def make_record():
    def make(row, language, raw="NO", *, failed=False, attempt=1, **changes):
        parsed = parse_response(raw, row.task)
        record = dict(sample_id=row.sample_id, language=language, model_id="synthetic_test_only_model",
                      model_revision="synthetic_revision", processor_revision="synthetic_revision",
                      protocol_hash="synthetic_protocol", run_config_hash="synthetic_run",
                      source_dataset=row.source_dataset, task=row.task, image_id=row.image_id,
                      image_sha256=row.image_sha256, ground_truth=row.ground_truth,
                      prompt_text=getattr(row, f"question_{language}"), attempt=attempt,
                      raw_response=None if failed else raw, parsed_prediction=None if failed else parsed.prediction,
                      run_status="failed" if failed else "success", parse_status="not_attempted" if failed else parsed.status,
                      scope="synthetic_test_only")
        record.update(changes)
        return record
    return make


def row_at(row_factory, i, **changes):
    return row_factory(sample_id=f"synthetic_{i}", image_id=f"{i:012d}",
                       question_vi="synthetic_test_only_vi", translation_status="requires_review", **changes)


def test_hand_calculated_binary_pairing_invalid_failure_and_missing(row_factory, make_record):
    rows = [row_at(row_factory, i, ground_truth="no" if i < 3 else "yes") for i in range(1, 5)]
    records = [make_record(rows[0], "en", "NO"), make_record(rows[0], "vi", "YES"),
               make_record(rows[1], "en", "YES"), make_record(rows[1], "vi", failed=True),
               make_record(rows[2], "en", "YES"), make_record(rows[2], "vi", "NO"),
               make_record(rows[3], "en", "ambiguous long explanation")]
    report = evaluate_run(rows, records)
    group = report["groups"][0]
    en, vi = group["languages"]["en"], group["languages"]["vi"]
    assert (en["correct"], en["accuracy"], en["invalid"], en["invalid_rate"]) == (2, 0.5, 1, 0.25)
    assert (vi["accuracy"], vi["failed"], vi["missing"]) == (0, 1, 1)
    assert en["binary_valid_only"] == {"tp": 1, "fp": 1, "tn": 1, "fn": 0,
        "fpr": 0.5, "fnr": 0, "precision": 0.5, "recall": 1, "f1": pytest.approx(2 / 3), "balanced_accuracy": 0.75}
    assert group["paired"]["jointly_valid"] == 2
    assert group["paired"]["disagreement_rate"] == 1
    assert group["paired"]["en_correct_vi_wrong"] == 2
    assert group["categories"]["random"]["primary_repope"]["delta_fpr_pp"] == 100
    primary = report["primary_repope"]
    assert (primary["negative_rows_expected"], primary["jointly_valid_negative_pairs"], primary["delta_fpr_pp"]) == (2, 1, 100)
    bounds = primary["sensitivity_all_expected_negatives"]
    assert bounds["en"]["fpr_lower"] == bounds["en"]["fpr_upper"] == 0.5
    assert bounds["vi"]["fpr_lower"] == 0.5 and bounds["vi"]["fpr_upper"] == 1
    assert bounds["delta_fpr_lower_pp"] == 0 and bounds["delta_fpr_upper_pp"] == 50
    assert report["qa_status"] == {"pending": 4} and report["scope"] == "engineering_pilot"


def test_counting_mae_coverage_and_per_class_accuracy(row_factory, make_record):
    counts = [row_at(row_factory, i, source_dataset="tallyqa", task="counting", ground_truth=gt)
              for i, gt in enumerate([2, 4, 0], 1)]
    records = [make_record(counts[0], "en", "2"), make_record(counts[0], "vi", "3"),
               make_record(counts[1], "en", "four things"), make_record(counts[1], "vi", "4"),
               make_record(counts[2], "en", failed=True)]
    group = evaluate_run(counts, records)["groups"][0]
    assert group["languages"]["en"]["mae_valid_only"] == 0
    assert group["languages"]["vi"]["mae_valid_only"] == 0.5
    assert group["languages"]["en"]["accuracy"] == pytest.approx(1 / 3)
    assert group["languages"]["en"]["exact_match"] == pytest.approx(1 / 3)
    assert group["paired"]["disagreement_rate"] == 1
    pets = [row_at(row_factory, i, source_dataset="oxford_pet", task="fine_grained", ground_truth=label)
            for i, label in enumerate(["A", "B"], 1)]
    records = [make_record(pets[0], "en", "A"), make_record(pets[0], "vi", "B"),
               make_record(pets[1], "en", "a dog"), make_record(pets[1], "vi", "B")]
    group = evaluate_run(pets, records)["groups"][0]
    assert group["languages"]["vi"]["per_class_accuracy"] == {"A": {"expected": 1, "accuracy": 0}, "B": {"expected": 1, "accuracy": 1}}
    assert group["languages"]["vi"]["top1_accuracy"] == 0.5


def test_jsonl_blank_lines_keep_actual_source_line_numbers(row_factory, make_record, tmp_path):
    row = row_at(row_factory, 1)
    path = tmp_path / "synthetic_test_only.jsonl"
    path.write_text("\n" + json.dumps(make_record(row, "en", "YES")) + "\n\n", encoding="utf-8")
    pairs, _ = pair_predictions([row], read_predictions(path))
    assert pairs[0].en.source_line == 2


def test_spatial_truth_alias_keeps_ground_truth_polarity(row_factory, make_record):
    row = row_at(row_factory, 1, source_dataset="vsr", task="spatial", ground_truth="no")
    report = evaluate_run([row], [make_record(row, "en", "FALSE"), make_record(row, "vi", "NO")])
    assert report["groups"][0]["languages"]["en"]["accuracy"] == 1
    assert report["primary_repope"]["negative_rows_expected"] == 0


def test_expected_grid_does_not_hide_unobserved_rows(row_factory, make_record):
    rows = [row_at(row_factory, i, ground_truth="no") for i in range(1, 3)]
    report = evaluate_run(rows, [make_record(rows[0], "en")])
    assert report["expected_inferences"] == 4
    assert report["groups"][0]["languages"]["vi"]["missing"] == 2
    selection = {"sample_ids": [rows[0].sample_id], "selected_rows": 1, "expected_inferences": 2}
    assert evaluate_run(rows, [], selection)["expected_inferences"] == 2
    assert report["primary_repope"]["delta_fpr_pp"] is None
    assert report["primary_repope"]["sensitivity_all_expected_negatives"]["delta_fpr_lower_pp"] == -50


def test_retry_uses_final_attempt_and_rejects_duplicates_or_post_success_attempt(row_factory, make_record):
    row = row_at(row_factory, 1)
    failed = make_record(row, "en", failed=True)
    success = make_record(row, "en", "YES", attempt=2)
    pairs, _ = pair_predictions([row], [failed, success])
    assert pairs[0].en.status == "valid" and pairs[0].en.source_line == 2 and pairs[0].en.attempts == 2
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate_run([row], [failed, failed])
    with pytest.raises(ValueError, match="follows a successful"):
        evaluate_run([row], [success, make_record(row, "en", failed=True, attempt=3)])


@pytest.mark.parametrize("changes", [
    {"image_id": "other"}, {"image_sha256": "0" * 64}, {"ground_truth": "no"},
    {"source_dataset": "vsr"}, {"task": "spatial"}, {"language": "other"},
    {"sample_id": "other"}, {"attempt": True}, {"parsed_prediction": "no"},
    {"prompt_text": "unrelated question"}, {"parse_status": "invalid"},
])
def test_bad_record_provenance_or_parse_is_rejected(row_factory, make_record, changes):
    row = row_at(row_factory, 1)
    record = make_record(row, "en", "YES")
    record.update(changes)
    with pytest.raises(ValueError):
        evaluate_run([row], [record])


def test_mixed_runs_and_selection_mismatch_are_rejected(row_factory, make_record):
    row = row_at(row_factory, 1)
    for changes in [{"model_id": "other"}, {"protocol_hash": "other"}, {"run_config_hash": "other"}]:
        with pytest.raises(ValueError, match="one model"):
            evaluate_run([row], [make_record(row, "en"), make_record(row, "vi", **changes)])
    for selection in [{"sample_ids": [row.sample_id] * 2}, {"sample_ids": ["unknown"]},
                      {"sample_ids": [row.sample_id], "expected_inferences": 60},
                      {"sample_ids": [row.sample_id], "protocol_hash": "other"}]:
        with pytest.raises(ValueError):
            evaluate_run([row], [make_record(row, "en")], selection)


def test_evaluate_and_statistics_cli_replay_and_report_integrity(row_factory, make_record, tmp_path):
    rows = [row_at(row_factory, i, ground_truth="no") for i in [1, 2]]
    manifest, predictions = tmp_path / "manifest.csv", tmp_path / "raw.jsonl"
    write_manifest(manifest, rows)
    records = [make_record(row, language, "NO") for row in rows for language in ["en", "vi"]]
    predictions.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    raw_before = predictions.read_bytes()
    args = ["--root", str(tmp_path), "evaluate", "--manifest", "manifest.csv", "--predictions", "raw.jsonl",
            "--output", "evaluation.json", "--report", "report.md"]
    assert main(args) == 0
    result = tmp_path / "evaluation.json"
    original = result.read_bytes()
    assert main(args) == 0 and result.read_bytes() == original
    stats = ["--root", str(tmp_path), "statistics", "--evaluation", "evaluation.json", "--output", "statistics.json",
             "--resamples", "100"]
    assert main(stats) == 0 and main(stats) == 0
    assert json.loads((tmp_path / "statistics.json").read_text())["primary_repope"]["lower_pp"] == 0
    assert predictions.read_bytes() == raw_before
    report = read_evaluation(result)
    report["paired_rows"][0]["ground_truth"] = "yes"
    result.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        read_evaluation(result)
    result.write_text("{}", encoding="utf-8")
    assert main(args) == 1
    assert result.read_text() == "{}"
