"""Conservative RePOPE template drafts; drafting never confers human approval."""

import csv
from datetime import datetime
from pathlib import Path
import re
import unicodedata
from typing import Any

TEMPLATE_VERSION = "repope_object_existence_vi_v2_classifiers"
QUESTION_PATTERN = re.compile(r"Is there (?:a|an) (?P<object>[a-z]+(?:[ -][a-z]+)*) in the image\?")


def require_review_identity(reviewer_id: str, reviewed_at: str, *, field: str) -> None:
    if not reviewer_id.strip():
        raise ValueError(f"{field}: a recorded decision requires a reviewer ID")
    try:
        moment = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("timezone required")
    except ValueError:
        raise ValueError(f"{field}: reviewed_at must be ISO 8601 with timezone") from None


def load_dictionary(path: Path) -> dict[str, dict[str, str]]:
    required = {"object_en", "object_vi", "status", "reviewer_id", "reviewed_at", "notes"}
    entries = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if set(fields) not in (required, required | {"classifier_vi"}) or len(fields) != len(set(fields)):
            raise ValueError("Unexpected dictionary columns; classifier_vi is optional for legacy dictionaries")
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed dictionary CSV at line {line}")
            row = {key: unicodedata.normalize("NFC", value.strip()) for key, value in row.items()}
            row.setdefault("classifier_vi", "")
            if row["classifier_vi"] not in {"", "cái", "chiếc", "con", "quả", "cây", "bông", "đôi", "tấm", "cuốn"}:
                raise ValueError(f"Unknown classifier_vi at dictionary line {line}; review the vocabulary first")
            name = row["object_en"]
            if not re.fullmatch(r"[a-z]+(?:[ -][a-z]+)*", name) or name in entries:
                raise ValueError(f"Invalid/duplicate dictionary object at line {line}")
            if row["status"] not in {"pending", "approved", "rejected"}:
                raise ValueError(f"Invalid dictionary status at line {line}")
            if row["status"] in {"pending", "approved"} and not row["object_vi"]:
                raise ValueError(f"Dictionary object_vi is empty at line {line}")
            if row["status"] != "pending":
                require_review_identity(row["reviewer_id"], row["reviewed_at"], field=f"dictionary line {line}")
            if row["status"] == "rejected" and not row["notes"]:
                raise ValueError("Rejected dictionary entries need notes")
            entries[name] = row
    if not entries:
        raise ValueError("Dictionary is empty")
    return entries


def draft_question(question_en: str, dictionary: dict[str, dict[str, str]]) -> dict[str, Any]:
    result = {"question_vi": "", "object_en": "", "object_vi": "", "dictionary_status": "missing",
              "template_version": TEMPLATE_VERSION, "reason": "TEMPLATE_MISMATCH", "translation_status": "missing"}
    match = QUESTION_PATTERN.fullmatch(question_en)
    if not match:
        return result
    name = match.group("object")
    result["object_en"] = name
    entry = dictionary.get(name)
    if not entry:
        result["reason"] = "OBJECT_NOT_IN_DICTIONARY"
        return result
    result["dictionary_status"] = entry["status"]
    if entry["status"] == "rejected":
        result["reason"] = "DICTIONARY_ENTRY_REJECTED"
        return result
    noun_phrase = " ".join(part for part in (entry.get("classifier_vi", ""), entry["object_vi"]) if part)
    result.update(question_vi=f"Trong ảnh có {noun_phrase} nào không?", object_vi=noun_phrase,
                  reason="DRAFT_REQUIRES_HUMAN_REVIEW", translation_status="requires_review")
    return result
