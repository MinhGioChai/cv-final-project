"""Compare manifest annotations to a pinned upstream RePOPE snapshot."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
import yaml

from .datasets.repope import BoundedClient, SourceError
from .io_utils import atomic_bytes, sha256_file, write_json
from .sampling import CATEGORIES
from .schemas import ManifestRow


class SourceAuditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    repository: Literal["YanNeu/RePOPE"]
    revision: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    cache_dir: str = Field(min_length=1)
    max_download_mb: int = Field(ge=1, le=10)


def read_audit_config(path: Path) -> SourceAuditConfig:
    return SourceAuditConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_upstream(config: SourceAuditConfig, *, root: Path, offline: bool = False) -> tuple[dict[str, bytes], dict[str, Any]]:
    cache = root / config.cache_dir
    receipt_path = cache / "receipt.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("repository") != config.repository or receipt.get("revision") != config.revision:
            raise SourceError("Upstream cache revision mismatch")
        content = {}
        for category in CATEGORIES:
            path = cache / f"coco_repope_{category}.json"
            if not path.is_file() or sha256_file(path) != receipt["files"][category]["sha256"]:
                raise SourceError(f"Missing/corrupt upstream cache for {category}; restore the pinned snapshot")
            content[category] = path.read_bytes()
        return content, receipt
    if offline:
        raise SourceError("No upstream snapshot; run audit-source online once to cache pinned annotations")
    client = BoundedClient(config.max_download_mb * 1024 * 1024, allowed_hosts={"raw.githubusercontent.com"})
    files = {}
    content = {}
    for category in CATEGORIES:
        filename = f"coco_repope_{category}.json"
        url = f"https://raw.githubusercontent.com/{config.repository}/{config.revision}/annotations/{filename}"
        payload = client.get(url)
        # Validate JSONL before retaining a snapshot.
        parse_annotations({category: payload})
        path = cache / filename
        atomic_bytes(path, payload)
        content[category] = payload
        files[category] = {"sha256": sha256_file(path), "bytes": len(payload), "url": url}
    receipt = {
        "repository": config.repository, "revision": config.revision,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "files": files,
        "downloaded_bytes": client.downloaded_bytes,
        "license_status": "No redistribution license inferred from annotations or mirror card",
    }
    write_json(receipt_path, receipt)
    return content, receipt


def parse_annotations(content: dict[str, bytes]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    index: dict = defaultdict(list)
    for category, payload in content.items():
        if category not in CATEGORIES:
            raise ValueError("Unknown upstream category")
        for line_number, line in enumerate(payload.decode("utf-8-sig").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                image = re.fullmatch(r"COCO_val2014_([0-9]{12})\.jpg", record["image"])
                if (not image or record["label"] not in {"yes", "no"}
                        or not isinstance(record["text"], str) or not record["text"].strip()
                        or type(record["question_id"]) is not int):
                    raise ValueError("Unexpected annotation schema")
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"Invalid upstream annotation at {category}:{line_number}") from exc
            index[(category, image.group(1), record["text"])].append(record)
    if not index:
        raise ValueError("Empty upstream annotations")
    return dict(index)


def audit_rows(rows: list[ManifestRow], content: dict[str, bytes], receipt: dict[str, Any]) -> tuple[list[ManifestRow], dict[str, Any]]:
    if not rows or len({row.sample_id for row in rows}) != len(rows):
        raise ValueError("Source audit needs nonempty, unique manifest sample IDs")
    index = parse_annotations(content)
    details = []
    verified = []
    for row in rows:
        if row.source_dataset != "repope" or row.task != "object_existence":
            raise ValueError("Source audit supports RePOPE object-existence rows only")
        matches = index.get((row.category, row.image_id, row.question_en), [])
        status = "matched"
        if not matches:
            status = "missing_upstream_question"
        elif len(matches) > 1:
            status = "ambiguous_upstream_question"
        elif row.ground_truth != matches[0]["label"]:
            status = "label_mismatch"
        detail = {"sample_id": row.sample_id, "category": row.category, "image_id": row.image_id,
                  "question_en": row.question_en, "manifest_label": row.ground_truth, "status": status,
                  "upstream_matches": [{"question_id": item["question_id"], "label": item["label"]} for item in matches]}
        details.append(detail)
        if status == "matched":
            data = row.model_dump()
            data["metadata"]["upstream_verification"] = {
                "status": "matched", "repository": receipt["repository"], "revision": receipt["revision"],
                "question_id": matches[0]["question_id"], "annotation_sha256": receipt["files"][row.category]["sha256"],
            }
            verified.append(ManifestRow.model_validate(data))
    counts = dict(Counter(detail["status"] for detail in details))
    report = {
        "all_matched": len(verified) == len(rows), "n_rows": len(rows), "status_counts": counts,
        "upstream_repository": receipt["repository"], "upstream_revision": receipt["revision"],
        "upstream_snapshot": receipt,
        "upstream_annotation_rows": sum(len(value) for value in index.values()),
        "scope": "Exact category/image_id/question/label agreement for supplied manifest only",
        "limitations": ["Annotation agreement does not certify visual ground truth or human QA",
                        "No comparison of image bytes to original COCO files"],
        "rows": details,
    }
    return verified, report
