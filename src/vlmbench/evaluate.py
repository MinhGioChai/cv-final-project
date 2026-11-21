"""Paired P0 evaluation of saved inference records against an explicit manifest."""

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, StrictInt, model_validator

from .parse import parse_response
from .reviews import canonical_hash
from .schemas import ManifestRow, Task

EVALUATION_VERSION = "paired_evaluation_v1"
IDENTITY_FIELDS = ("model_id", "model_revision", "processor_revision", "protocol_hash", "run_config_hash")
BINARY_TASKS = {"object_existence", "spatial"}


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["valid", "invalid", "failed", "missing"]
    prediction: str | StrictInt | None = None
    attempts: int = 0
    selected_attempt: int | None = None
    source_line: int | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def check_prediction(self) -> Self:
        if (self.status == "valid") != (self.prediction is not None):
            raise ValueError("Only valid observations carry a prediction")
        return self


class PairedSample(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sample_id: str
    dataset: str
    task: Task
    category: str
    image_namespace: str
    image_id: str
    image_sha256: str
    ground_truth: str | StrictInt
    ground_truth_source: str
    is_pilot: bool
    qa_status: str
    translation_status: str
    en: Observation
    vi: Observation

    @model_validator(mode="after")
    def check_labels(self) -> Self:
        if self.task == "negation":
            raise ValueError("P0 evaluation covers object existence, spatial, counting and fine-grained tasks")
        values = [self.ground_truth] + [o.prediction for o in (self.en, self.vi) if o.status == "valid"]
        for value in values:
            if self.task in BINARY_TASKS and value not in {"yes", "no"}:
                raise ValueError("Binary storage labels must be yes/no")
            if self.task == "counting" and (type(value) is not int or value < 0):
                raise ValueError("Counting labels must be nonnegative integers")
            if self.task == "fine_grained" and value not in tuple("ABCDEFGH"):
                raise ValueError("Fine-grained labels must use the fixed A-H mapping")
        return self


def rate(numerator: int | float, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def image_key(pair: PairedSample) -> tuple[str, str]:
    return pair.image_namespace, pair.image_id


def is_correct(pair: PairedSample, language: str) -> bool:
    observation = getattr(pair, language)
    return observation.status == "valid" and observation.prediction == pair.ground_truth


def read_predictions(path: Path) -> list[dict]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"Invalid prediction JSON at line {number}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Prediction line {number} must be an object")
        record["_evaluation_line_number"] = number
        records.append(record)
    return records


def _select_rows(rows: list[ManifestRow], selection: dict | None) -> list[ManifestRow]:
    if not rows or len({row.sample_id for row in rows}) != len(rows):
        raise ValueError("Evaluation requires a nonempty manifest with unique sample IDs")
    if selection is None:
        return sorted(rows, key=lambda row: row.sample_id)
    if not isinstance(selection, dict):
        raise ValueError("Selection must be a JSON object")
    ids = selection.get("sample_ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(item, str) for item in ids):
        raise ValueError("Selection must contain a nonempty sample_ids list")
    if len(set(ids)) != len(ids):
        raise ValueError("Selection sample IDs must be unique")
    by_id = {row.sample_id: row for row in rows}
    if set(ids) - by_id.keys():
        raise ValueError("Selection contains sample IDs outside the manifest")
    for field, expected in (("selected_rows", len(ids)), ("expected_inferences", len(ids) * 2)):
        if field in selection and (type(selection[field]) is not int or selection[field] != expected):
            raise ValueError(f"Selection {field} disagrees with its paired sample IDs")
    return [by_id[sample_id] for sample_id in sorted(ids)]


def _validated_attempts(rows: list[ManifestRow], records: list[dict], selection: dict | None) -> tuple[dict, dict]:
    by_id = {row.sample_id: row for row in rows}
    identity = None
    attempts = defaultdict(list)
    for index, record in enumerate(records, 1):
        line = record.get("_evaluation_line_number", index)
        current = {key: record.get(key) for key in IDENTITY_FIELDS}
        if any(not isinstance(value, str) or not value for value in current.values()):
            raise ValueError(f"Missing run identity at prediction line {line}")
        if identity is None:
            identity = current
        if identity != current:
            raise ValueError("Evaluate one model/protocol/runtime run at a time")
        for key in ("model_revision", "protocol_hash", "run_config_hash"):
            if selection and key in selection and selection[key] != current[key]:
                raise ValueError(f"Selection {key} differs from the raw run")
        sample_id, language = record.get("sample_id"), record.get("language")
        if not isinstance(sample_id, str) or not isinstance(language, str) or sample_id not in by_id or language not in {"en", "vi"}:
            raise ValueError(f"Unexpected sample or language at prediction line {line}")
        row = by_id[sample_id]
        expected = {"source_dataset": row.source_dataset, "task": row.task, "image_id": row.image_id,
                    "image_sha256": row.image_sha256, "ground_truth": row.ground_truth}
        for key, value in expected.items():
            if type(record.get(key)) is not type(value) or record[key] != value:
                raise ValueError(f"Prediction {key} differs from the manifest at line {line}")
        prompt = record.get("prompt_text")
        question = getattr(row, f"question_{language}")
        if not question.strip() or not isinstance(prompt, str) or question not in prompt:
            raise ValueError(f"Prediction prompt does not contain the manifest question at line {line}")
        attempt = record.get("attempt")
        if type(attempt) is not int or attempt < 1:
            raise ValueError(f"Attempt must be a positive integer at line {line}")
        if record.get("run_status") == "success":
            parsed = parse_response(record.get("raw_response"), row.task)
            prediction = record.get("parsed_prediction")
            if (record.get("parse_status") != parsed.status or type(prediction) is not type(parsed.prediction)
                    or prediction != parsed.prediction):
                raise ValueError(f"Stored parse disagrees with the current parser at line {line}")
        elif record.get("run_status") == "failed":
            if record.get("parsed_prediction") is not None or record.get("parse_status") != "not_attempted":
                raise ValueError(f"Failed generation carries a parsed prediction at line {line}")
        else:
            raise ValueError(f"Unknown run_status at line {line}")
        attempts[(sample_id, language)].append((attempt, line, record))
    for key, history in attempts.items():
        history.sort(key=lambda item: item[0])
        if len({item[0] for item in history}) != len(history):
            raise ValueError(f"Duplicate sample/language/attempt for {key}")
        if any(item[2]["run_status"] == "success" for item in history[:-1]):
            raise ValueError(f"Attempt follows a successful generation for {key}; use a separate run for reruns")
    return attempts, identity or {field: None for field in IDENTITY_FIELDS}


def _observation(history: list[tuple]) -> Observation:
    if not history:
        return Observation(status="missing", reason="NO_RECORD")
    attempt, line, record = history[-1]
    if record["run_status"] == "failed":
        return Observation(status="failed", attempts=len(history), selected_attempt=attempt,
                           source_line=line, reason="GENERATION_FAILED")
    return Observation(status=record["parse_status"], prediction=record["parsed_prediction"],
                       attempts=len(history), selected_attempt=attempt, source_line=line,
                       reason=parse_response(record.get("raw_response"), record["task"]).reason)


def pair_predictions(rows: list[ManifestRow], records: list[dict], selection: dict | None = None) -> tuple[list[PairedSample], dict]:
    selected = _select_rows(rows, selection)
    attempts, identity = _validated_attempts(selected, records, selection)
    pairs = []
    for row in selected:
        pairs.append(PairedSample(sample_id=row.sample_id, dataset=row.source_dataset, task=row.task,
                                  category=row.category, image_namespace=row.metadata.get("image_namespace", row.source_dataset),
                                  image_id=row.image_id, image_sha256=row.image_sha256, ground_truth=row.ground_truth,
                                  ground_truth_source=row.ground_truth_source, is_pilot=row.is_pilot,
                                  qa_status=row.qa_status, translation_status=row.translation_status,
                                  en=_observation(attempts[(row.sample_id, "en")]),
                                  vi=_observation(attempts[(row.sample_id, "vi")])))
    return pairs, identity


def language_metrics(pairs: list[PairedSample], language: str) -> dict:
    counts = Counter(getattr(pair, language).status for pair in pairs)
    valid = [pair for pair in pairs if getattr(pair, language).status == "valid"]
    correct = sum(is_correct(pair, language) for pair in pairs)
    result = {"expected": len(pairs), **{state: counts[state] for state in ("valid", "invalid", "failed", "missing")},
              "correct": correct, "accuracy": rate(correct, len(pairs)),
              "accuracy_valid_only": rate(correct, len(valid)), "valid_rate": rate(len(valid), len(pairs)),
              "invalid_rate": rate(counts["invalid"], len(pairs)),
              "invalid_rate_generated": rate(counts["invalid"], counts["valid"] + counts["invalid"])}
    if pairs and pairs[0].task in BINARY_TASKS:
        tp = sum(pair.ground_truth == "yes" and getattr(pair, language).prediction == "yes" for pair in valid)
        fp = sum(pair.ground_truth == "no" and getattr(pair, language).prediction == "yes" for pair in valid)
        tn = sum(pair.ground_truth == "no" and getattr(pair, language).prediction == "no" for pair in valid)
        fn = sum(pair.ground_truth == "yes" and getattr(pair, language).prediction == "no" for pair in valid)
        recall, specificity = rate(tp, tp + fn), rate(tn, tn + fp)
        result["binary_valid_only"] = {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
                                       "fpr": rate(fp, fp + tn), "fnr": rate(fn, tp + fn),
                                       "precision": rate(tp, tp + fp), "recall": recall,
                                       "f1": rate(2 * tp, 2 * tp + fp + fn),
                                       "balanced_accuracy": (recall + specificity) / 2
                                       if recall is not None and specificity is not None else None}
    if pairs and pairs[0].task == "counting":
        result["exact_match"] = result["accuracy"]
        result["mae_valid_only"] = rate(sum(abs(getattr(pair, language).prediction - pair.ground_truth)
                                            for pair in valid), len(valid))
    if pairs and pairs[0].task == "fine_grained":
        result["top1_accuracy"] = result["accuracy"]
        result["per_class_accuracy"] = {
            label: {"expected": len(subset), "accuracy": rate(sum(is_correct(pair, language) for pair in subset), len(subset))}
            for label in tuple("ABCDEFGH") if (subset := [pair for pair in pairs if pair.ground_truth == label])}
    return result


def paired_metrics(pairs: list[PairedSample]) -> dict:
    jointly_valid = [pair for pair in pairs if pair.en.status == pair.vi.status == "valid"]
    disagreements = sum(pair.en.prediction != pair.vi.prediction for pair in jointly_valid)
    excluded = Counter(f"en_{pair.en.status}__vi_{pair.vi.status}" for pair in pairs
                       if pair.en.status != "valid" or pair.vi.status != "valid")
    return {"expected_pairs": len(pairs), "jointly_valid": len(jointly_valid),
            "excluded_pairs": len(pairs) - len(jointly_valid), "excluded_status_counts": dict(sorted(excluded.items())),
            "disagreements": disagreements, "disagreement_rate": rate(disagreements, len(jointly_valid)),
            "en_correct_vi_wrong": sum(is_correct(pair, "en") and not is_correct(pair, "vi") for pair in jointly_valid),
            "en_wrong_vi_correct": sum(not is_correct(pair, "en") and is_correct(pair, "vi") for pair in jointly_valid),
            "delta_accuracy_pp": 100 * (sum(is_correct(pair, "vi") for pair in pairs)
                                          - sum(is_correct(pair, "en") for pair in pairs)) / len(pairs) if pairs else None}


def primary_repope(pairs: list[PairedSample]) -> dict:
    negatives = [pair for pair in pairs if pair.dataset == "repope" and pair.task == "object_existence"
                 and pair.ground_truth == "no"]
    complete = [pair for pair in negatives if pair.en.status == pair.vi.status == "valid"]
    fp_en = sum(pair.en.prediction == "yes" for pair in complete)
    fp_vi = sum(pair.vi.prediction == "yes" for pair in complete)
    observed, unknown = {}, {}
    for language in ("en", "vi"):
        observed[language] = sum(getattr(pair, language).status == "valid" and getattr(pair, language).prediction == "yes"
                                 for pair in negatives)
        unknown[language] = sum(getattr(pair, language).status != "valid" for pair in negatives)
    n = len(negatives)
    bounds = {language: {"observed_fp": observed[language], "unknown": unknown[language],
                         "fpr_lower": rate(observed[language], n),
                         "fpr_upper": rate(observed[language] + unknown[language], n)} for language in ("en", "vi")}
    return {"negative_rows_expected": n, "negative_images_expected": len({image_key(pair) for pair in negatives}),
            "jointly_valid_negative_pairs": len(complete), "excluded_negative_pairs": n - len(complete),
            "complete_case_image_clusters": len({image_key(pair) for pair in complete}),
            "fp_en": fp_en, "fp_vi": fp_vi, "fpr_en": rate(fp_en, len(complete)), "fpr_vi": rate(fp_vi, len(complete)),
            "delta_fpr_pp": 100 * (fp_vi - fp_en) / len(complete) if complete else None,
            "sensitivity_all_expected_negatives": {**bounds,
                "delta_fpr_lower_pp": 100 * (observed["vi"] - observed["en"] - unknown["en"]) / n if n else None,
                "delta_fpr_upper_pp": 100 * (observed["vi"] + unknown["vi"] - observed["en"]) / n if n else None,
                "unknown_policy": "invalid, failed and missing predictions may each be either YES or NO"}}


def task_summary(pairs: list[PairedSample]) -> dict:
    result = {"n_rows": len(pairs), "n_unique_images": len({image_key(pair) for pair in pairs}),
              "languages": {lang: language_metrics(pairs, lang) for lang in ("en", "vi")},
              "paired": paired_metrics(pairs)}
    if pairs and pairs[0].dataset == "repope" and pairs[0].task == "object_existence":
        result["primary_repope"] = primary_repope(pairs)
    return result


def evaluate_run(rows: list[ManifestRow], records: list[dict], selection: dict | None = None) -> dict:
    pairs, identity = pair_predictions(rows, records, selection)
    groups = defaultdict(list)
    for pair in pairs:
        groups[(pair.dataset, pair.task)].append(pair)
    result = {"evaluation_version": EVALUATION_VERSION, "run": identity,
              "scope": "engineering_pilot" if any(pair.is_pilot or pair.qa_status != "approved"
                                                    or pair.translation_status != "approved" for pair in pairs) else "qa_approved_data",
              "n_selected_rows": len(pairs), "n_manifest_rows": len(rows), "expected_inferences": len(pairs) * 2,
              "total_raw_attempts": len(records), "selection_policy": "explicit_selection" if selection else "entire_manifest",
              "qa_status": dict(Counter(pair.qa_status for pair in pairs)),
              "translation_status": dict(Counter(pair.translation_status for pair in pairs)),
              "recorded_inference_scopes": sorted({str(record.get("scope", "unspecified")) for record in records}),
              "policies": {"accuracy_denominator": "all expected rows; invalid, failed and missing count as incorrect",
                           "binary_secondary": "language-specific valid predictions", "primary": "jointly valid RePOPE negatives",
                           "disagreement": "jointly valid pairs", "mae": "valid counting predictions",
                           "attempts": "unique attempt numbers; retry after failure; final attempt selected",
                           "parser": "saved prediction checked against current full-answer parser"},
              "primary_repope": primary_repope(pairs),
              "groups": [{"dataset": dataset, "task": task, **task_summary(subset),
                          "categories": {category: task_summary([pair for pair in subset if pair.category == category])
                                         for category in sorted({pair.category for pair in subset})}}
                         for (dataset, task), subset in sorted(groups.items())],
              "paired_rows": [pair.model_dump() for pair in pairs]}
    return result


def seal_report(report: dict) -> dict:
    return {**report, "report_hash": canonical_hash(report)}


def read_evaluation(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Evaluation report must be a JSON object")
    payload = {key: value for key, value in report.items() if key != "report_hash"}
    if report.get("evaluation_version") != EVALUATION_VERSION or report.get("report_hash") != canonical_hash(payload):
        raise ValueError("Evaluation report version/hash is invalid")
    pairs = [PairedSample.model_validate(row) for row in report["paired_rows"]]
    if not pairs or len({pair.sample_id for pair in pairs}) != len(pairs):
        raise ValueError("Evaluation paired rows must be nonempty and unique")
    return report
