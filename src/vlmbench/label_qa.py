"""Bound image/label QA, independent of already accepted translations."""

from collections import Counter
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .io_utils import atomic_bytes, sha256_file
from .qa import preflight_image
from .reviews import canonical_hash, row_hash
from .schemas import ManifestRow
from .translate import require_review_identity


class LabelDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sample_id: str
    status: Literal["pending", "approved", "rejected"]
    observed_answer: Literal["", "yes", "no", "uncertain"]
    reviewer_id: str
    reviewed_at: str
    notes: str


def review_context(rows, manifest_path):
    if not rows or len({r.sample_id for r in rows}) != len(rows):
        raise ValueError("Label QA requires nonempty, unique sample IDs")
    if any(r.task != "object_existence" or r.source_dataset != "repope" for r in rows):
        raise ValueError("This label QA workflow supports RePOPE existence rows")
    return {"schema_version": "label_qa_v1", "manifest_sha256": sha256_file(manifest_path),
            "sample_ids": [r.sample_id for r in rows],
            "source_row_sha256": {r.sample_id: row_hash(r) for r in rows}}


def pending_review(rows, manifest_path):
    return {"context": review_context(rows, manifest_path), "decisions": [
        LabelDecision(sample_id=r.sample_id, status="pending", observed_answer="", reviewer_id="",
                      reviewed_at="", notes="").model_dump() for r in rows]}


def _check_images(rows, root):
    for row in rows:
        path = (root / row.image_path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Image path must stay inside the project")
        if preflight_image(path)["sha256"] != row.image_sha256:
            raise ValueError(f"Image checksum changed: {row.sample_id}")


def export_label_qa(rows, *, manifest_path: Path, root: Path, output: Path, html_path: Path):
    if len({p.resolve() for p in (output, html_path, manifest_path)}) != 3:
        raise ValueError("Manifest/review/HTML paths must differ")
    _check_images(rows, root)
    review = pending_review(rows, manifest_path)
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if existing.get("context") != review["context"]:
            raise ValueError("Existing label QA context differs; use a new output version")
        # A rerun must not erase decisions already recorded by a reviewer.
        review = existing
    cards = []
    for row in rows:
        path = root / row.image_path
        image = preflight_image(path)
        mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(image["format"])
        if not mime:
            raise ValueError("Unsupported image format for offline review")
        cards.append({"sample_id": row.sample_id, "image_id": row.image_id, "category": row.category,
                      "question_en": row.question_en, "question_vi": row.question_vi,
                      "ground_truth": row.ground_truth, "translation_status": row.translation_status,
                      "image": f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")})
    template = Path(__file__).with_name("label_qa_template.html").read_text(encoding="utf-8")
    payload = json.dumps({"review": review, "cards": cards}, ensure_ascii=False).replace("<", "\\u003c")
    rendered = template.replace("__LABEL_QA_PAYLOAD__", payload).encode("utf-8")
    # Validate every input before publishing either output.
    if html_path.exists() and html_path.read_bytes() != rendered:
        raise ValueError("Existing HTML differs; preserve it and use a new path")
    if not output.exists():
        atomic_bytes(output, (json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    if not html_path.exists():
        atomic_bytes(html_path, rendered)
    return {"schema_version": "label_qa_v1", "rows": len(rows), "review": output.as_posix(),
            "html": html_path.as_posix(), "manifest_sha256": review["context"]["manifest_sha256"],
            "human_approvals_created": 0, "model_outputs_in_reviewer_view": False}


def import_label_qa(rows, *, manifest_path: Path, root: Path, review_path: Path, operator: str):
    if not operator.strip():
        raise ValueError("Import operator is required")
    expected = review_context(rows, manifest_path)
    _check_images(rows, root)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if (not isinstance(review, dict) or set(review) != {"context", "decisions"}
            or review["context"] != expected or not isinstance(review["decisions"], list)):
        raise ValueError("Label QA context does not match this manifest")
    decisions = [LabelDecision.model_validate(d) for d in review["decisions"]]
    by_id = {d.sample_id: d for d in decisions}
    if len(by_id) != len(decisions) or set(by_id) != {r.sample_id for r in rows}:
        raise ValueError("Review must contain every sample exactly once")
    for row in rows:
        d = by_id[row.sample_id]
        if d.status != "pending":
            require_review_identity(d.reviewer_id, d.reviewed_at, field=row.sample_id)
            if not d.observed_answer:
                raise ValueError("A decision needs an observed answer")
        if d.status == "approved" and d.observed_answer != row.ground_truth:
            raise ValueError("Approval must agree with the unchanged source label; log a rejection/uncertainty instead")
        if (d.status == "rejected" or d.observed_answer == "uncertain") and not d.notes.strip():
            raise ValueError("Rejection/uncertainty requires notes")
    run_key = canonical_hash({"context": expected, "review_sha256": sha256_file(review_path),
                              "operator": operator.strip(), "policy": "image_label_qa_preserve_translation_v1"})
    updated, events = [], []
    for row in rows:
        decision = by_id[row.sample_id]
        data = row.model_dump()
        if decision.status != "pending":
            data["qa_status"] = decision.status
            data["metadata"]["human_label_qa"] = {**decision.model_dump(), "run_key": run_key,
                                                   "source_row_sha256": row_hash(row)}
        result = ManifestRow.model_validate(data)
        updated.append(result)
        events.append({"sample_id": row.sample_id, "before": row.qa_status, "after": result.qa_status,
                       "decision": decision.model_dump(), "source_row_sha256": row_hash(row),
                       "output_row_sha256": row_hash(result)})
    audit = {"schema_version": "label_qa_v1", "run_key": run_key, "operator": operator.strip(),
             "imported_at_utc": datetime.now(timezone.utc).isoformat(), "context": expected,
             "review_sha256": sha256_file(review_path), "policy": "image_label_qa_preserve_translation_v1",
             "qa_status": dict(Counter(r.qa_status for r in updated)),
             "translation_status": dict(Counter(r.translation_status for r in updated)), "events": events,
             "limitations": ["Records reviewer attestations; does not authenticate identity or prove human review"]}
    return updated, audit
