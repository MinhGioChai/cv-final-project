"""Export bound review sheets and import explicit human decisions with provenance."""

from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any

from .io_utils import atomic_bytes, sha256_file, write_json
from .schemas import ManifestRow
from .translate import TEMPLATE_VERSION, draft_question, load_dictionary, require_review_identity

PROTECTED = ("sample_id", "image_id", "image_sha256", "category", "question_en", "ground_truth", "source_row_sha256", "manifest_sha256")
DRAFT_FIELDS = ("object_en", "object_vi", "dictionary_status", "template_version", "draft_reason")
EDITABLE = ("question_vi", "reviewer_1_id", "reviewer_1_status", "reviewer_1_reviewed_at",
            "reviewer_2_id", "reviewer_2_status", "reviewer_2_reviewed_at", "final_status",
            "qa_reviewer_id", "qa_status", "qa_reviewed_at", "notes")
FIELDS = PROTECTED + DRAFT_FIELDS + EDITABLE


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def row_hash(row: ManifestRow) -> str:
    return canonical_hash(row.model_dump())


def _unique_rows(rows: list[ManifestRow]) -> None:
    if not rows or len({row.sample_id for row in rows}) != len(rows):
        raise ValueError("Review requires nonempty, unique manifest sample IDs")


def protected_values(row: ManifestRow, manifest_hash: str) -> dict[str, str]:
    return {"sample_id": row.sample_id, "image_id": row.image_id, "image_sha256": row.image_sha256,
            "category": row.category, "question_en": row.question_en, "ground_truth": str(row.ground_truth),
            "source_row_sha256": row_hash(row), "manifest_sha256": manifest_hash}


def export_review(rows: list[ManifestRow], *, manifest_path: Path, dictionary_path: Path, output: Path) -> dict[str, Any]:
    _unique_rows(rows)
    dictionary = load_dictionary(dictionary_path)
    manifest_hash = sha256_file(manifest_path)
    context = {"schema_version": 1, "manifest_sha256": manifest_hash,
               "dictionary_sha256": sha256_file(dictionary_path), "template_version": TEMPLATE_VERSION,
               "sample_ids": [row.sample_id for row in rows]}
    context_path = output.with_suffix(".context.json")
    reasons: Counter = Counter()
    dictionary_statuses: Counter = Counter()
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if row.source_dataset != "repope" or row.task != "object_existence":
            raise ValueError("Template export currently supports RePOPE object-existence only")
        draft = draft_question(row.question_en, dictionary)
        reasons[draft["reason"]] += 1
        dictionary_statuses[draft["dictionary_status"]] += 1
        record = {key: "" for key in FIELDS}
        record.update(protected_values(row, manifest_hash))
        record.update({key: draft[key] for key in ("object_en", "object_vi", "dictionary_status", "template_version")})
        # Preserve an existing translation as a proposal, but never auto-approve it.
        record.update(question_vi=row.question_vi or draft["question_vi"], draft_reason=draft["reason"],
                      reviewer_1_status="pending", reviewer_2_status="pending", final_status="pending", qa_status="pending")
        writer.writerow(record)
    preserved = output.exists()
    if preserved:
        if not context_path.is_file() or json.loads(context_path.read_text(encoding="utf-8")) != context:
            raise ValueError("Existing review belongs to a different context. Preserve it and use a new output path")
    else:
        if context_path.exists() and json.loads(context_path.read_text(encoding="utf-8")) != context:
            raise ValueError("Existing review context differs; use a new output path")
        write_json(context_path, context)
        atomic_bytes(output, buffer.getvalue().encode("utf-8-sig"))
    return {**context, "n_rows": len(rows), "draft_reasons": dict(reasons),
            "dictionary_statuses": dict(dictionary_statuses), "existing_review_preserved": preserved,
            "human_approvals_created": 0, "warning": "Drafts remain pending; the import step validates human decisions"}


def read_review(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or []) != FIELDS:
            raise ValueError("Unexpected review columns/order; use export-translation-review to create a sheet")
        records = []
        for line, record in enumerate(reader, start=2):
            if None in record or any(value is None for value in record.values()):
                raise ValueError(f"Malformed review CSV at line {line}")
            records.append(record)
    return records


def write_review_preview(rows: list[ManifestRow], *, review_path: Path, output: Path, root: Path) -> None:
    by_id = {record["sample_id"]: record for record in read_review(review_path)}
    lines = ["# Bản dịch RePOPE để review", "",
             "Bảng này hiển thị nội dung CSV hiện tại; quyết định QA chỉ có hiệu lực sau khi import và validation thành công.",
             "Nhãn là nhãn nguồn, không phải đáp án model. Sửa bản dịch/quyết định trong file CSV gốc.", "",
             f"[Mở CSV review]({Path(os.path.relpath(review_path, output.parent)).as_posix()})", "",
             "| Image ID | Câu hỏi EN | Bản dịch VI | Nhãn nguồn | Duyệt bản dịch | QA ảnh/nhãn | Ảnh |",
             "|---|---|---|---|---|---|---|"]
    for row in rows:
        record = by_id[row.sample_id]
        vi = record["question_vi"].replace("|", "\\|").replace("\n", " ") or "Cần dịch thủ công"
        en = row.question_en.replace("|", "\\|")
        link = Path(os.path.relpath(root / row.image_path, output.parent)).as_posix()
        lines.append(f"| `{row.image_id}` | {en} | {vi} | {row.ground_truth} | {record['final_status']} | {record['qa_status']} | [Mở ảnh]({link}) |")
    atomic_bytes(output, ("\n".join(lines) + "\n").encode("utf-8"))


def _validate_decisions(record: dict[str, str]) -> None:
    for prefix in ("reviewer_1", "reviewer_2"):
        status = record[f"{prefix}_status"]
        if status not in {"pending", "approved", "rejected"}:
            raise ValueError(f"Invalid {prefix} status")
        if status != "pending":
            require_review_identity(record[f"{prefix}_id"], record[f"{prefix}_reviewed_at"], field=prefix)
        if status == "rejected" and not record["notes"].strip():
            raise ValueError("Rejection requires notes")
    final = record["final_status"]
    if final not in {"pending", "approved", "rejected"}:
        raise ValueError("Invalid final_status")
    if final == "approved":
        if record["reviewer_1_status"] != "approved" or record["reviewer_2_status"] != "approved":
            raise ValueError("Approval requires two explicitly approved translation reviews")
        if record["reviewer_1_id"].strip().casefold() == record["reviewer_2_id"].strip().casefold():
            raise ValueError("Translation approval requires two distinct reviewer IDs")
        if not record["question_vi"].strip():
            raise ValueError("Cannot approve an empty Vietnamese translation")
    if final == "rejected" and "rejected" not in {record["reviewer_1_status"], record["reviewer_2_status"]}:
        raise ValueError("Final rejection needs a recorded reviewer rejection")
    if record["qa_status"] not in {"pending", "approved", "rejected"}:
        raise ValueError("Invalid image/label qa_status")
    if record["qa_status"] != "pending":
        require_review_identity(record["qa_reviewer_id"], record["qa_reviewed_at"], field="image/label QA")
    if record["qa_status"] == "rejected" and not record["notes"].strip():
        raise ValueError("Image/label QA rejection requires notes")


def import_review(
    rows: list[ManifestRow], *, manifest_path: Path, review_path: Path, operator: str,
) -> tuple[list[ManifestRow], dict[str, Any]]:
    _unique_rows(rows)
    if not operator.strip():
        raise ValueError("Import operator ID is required for provenance")
    records = read_review(review_path)
    by_id = {record["sample_id"]: record for record in records}
    if len(by_id) != len(records) or set(by_id) != {row.sample_id for row in rows}:
        raise ValueError("Review IDs must match the entire input manifest exactly, without duplicate/missing/unknown IDs")
    manifest_hash = sha256_file(manifest_path)
    review_hash = sha256_file(review_path)
    context_path = review_path.with_suffix(".context.json")
    if not context_path.is_file():
        raise ValueError("Missing review export context sidecar; restore it or export a new version")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    if (context.get("schema_version") != 1 or context.get("manifest_sha256") != manifest_hash
            or context.get("sample_ids") != [row.sample_id for row in rows]):
        raise ValueError("Review export context does not match the input manifest")
    context_hash = sha256_file(context_path)
    run_key = canonical_hash({"manifest_sha256": manifest_hash, "review_csv_sha256": review_hash,
                              "review_context_sha256": context_hash,
                              "operator": operator.strip(), "import_policy": "two_translation_reviewers_plus_separate_label_qa_v1"})
    # Validate every record before producing any output; no partial approvals/imports.
    for row in rows:
        record = by_id[row.sample_id]
        if any(record[key] != value for key, value in protected_values(row, manifest_hash).items()):
            raise ValueError(f"Protected source fields/stale fingerprint changed for {row.sample_id}; source labels cannot be edited through review")
        try:
            _validate_decisions(record)
        except ValueError as exc:
            raise ValueError(f"{row.sample_id}: {exc}") from exc
    updated = []
    events = []
    for row in rows:
        record = by_id[row.sample_id]
        data = row.model_dump()
        question_vi = record["question_vi"].strip()
        final = record["final_status"]
        translation_status = (final if final in {"approved", "rejected"} else "requires_review" if question_vi else "missing")
        # A translation sheet does not erase earlier image/label QA evidence.
        qa_status = row.qa_status if record["qa_status"] == "pending" else record["qa_status"]
        data.update(question_vi=question_vi, translation_status=translation_status, qa_status=qa_status)
        data["metadata"]["translation_review"] = {
            "run_key": run_key, "review_csv_sha256": review_hash, "source_row_sha256": row_hash(row),
            "export_context": context, "review_context_sha256": context_hash,
            "operator": operator.strip(), "decisions": {key: record[key] for key in EDITABLE if key != "question_vi"},
            "draft_context_claims": {key: record[key] for key in DRAFT_FIELDS},
        }
        if record["qa_status"] != "pending":
            data["metadata"]["human_label_qa"] = {"status": qa_status, "reviewer_id": record["qa_reviewer_id"], "reviewed_at": record["qa_reviewed_at"]}
        new = ManifestRow.model_validate(data)
        updated.append(new)
        keys = ("question_vi", "translation_status", "qa_status")
        events.append({"sample_id": row.sample_id, "before": {key: getattr(row, key) for key in keys},
                       "after": {key: getattr(new, key) for key in keys},
                       "source_row_sha256": row_hash(row), "output_row_sha256": row_hash(new),
                       "review_record": record})
    return updated, {
        "schema_version": 1, "run_key": run_key, "operator": operator.strip(),
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_manifest_sha256": manifest_hash, "review_csv_sha256": review_hash,
        "review_context_sha256": context_hash, "export_context": context,
        "policy": "two_translation_reviewers_plus_separate_label_qa_v1",
        "n_rows": len(updated), "translation_status": dict(Counter(row.translation_status for row in updated)),
        "qa_status": dict(Counter(row.qa_status for row in updated)), "events": events,
        "limitations": ["CSV records reviewer attestations; it does not authenticate identities or prove a human performed review"],
    }
