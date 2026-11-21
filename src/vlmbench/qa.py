"""Image preflight, QA gates, and pilot/final leakage checks."""

from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image

from .io_utils import sha256_file
from .schemas import ManifestRow


def preflight_image(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"Image does not exist: {path}")
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            return {"width": image.width, "height": image.height, "format": image.format,
                    "mode": image.mode, "sha256": sha256_file(path)}
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError(f"Unreadable image: {path}") from exc


def leakage_issues(pilot: list[ManifestRow], final: list[ManifestRow]) -> list[dict[str, Any]]:
    by_identity = {(row.metadata.get("image_namespace", row.source_dataset), row.image_id) for row in pilot}
    hashes = {row.image_sha256 for row in pilot}
    issues = []
    for row in final:
        identity = (row.metadata.get("image_namespace", row.source_dataset), row.image_id)
        if identity in by_identity:
            issues.append({"sample_id": row.sample_id, "code": "PILOT_IMAGE_OVERLAP"})
        if row.image_sha256 in hashes:
            issues.append({"sample_id": row.sample_id, "code": "PILOT_CHECKSUM_OVERLAP"})
    return issues


def validate_manifest(
    rows: list[ManifestRow], *, root: Path, mode: str = "pilot", pilot: list[ManifestRow] | None = None,
) -> dict[str, Any]:
    if mode not in {"pilot", "main"}:
        raise ValueError("mode must be pilot/main")
    issues: list[dict[str, Any]] = []
    if not rows:
        issues.append({"sample_id": None, "code": "EMPTY_MANIFEST"})
    counts = Counter(row.sample_id for row in rows)
    for sample_id, count in counts.items():
        if count > 1:
            issues.append({"sample_id": sample_id, "code": "DUPLICATE_SAMPLE_ID"})
    for row in rows:
        try:
            info = preflight_image(root / row.image_path)
            if info["sha256"] != row.image_sha256:
                issues.append({"sample_id": row.sample_id, "code": "IMAGE_CHECKSUM_MISMATCH"})
        except ValueError as exc:
            issues.append({"sample_id": row.sample_id, "code": "IMAGE_PREFLIGHT_FAILED", "detail": str(exc)})
        if mode == "main":
            if row.is_pilot:
                issues.append({"sample_id": row.sample_id, "code": "PILOT_ROW_IN_MAIN"})
            if row.qa_status != "approved" or row.translation_status != "approved" or not row.question_vi.strip():
                issues.append({"sample_id": row.sample_id, "code": "MAIN_QA_NOT_APPROVED"})
        elif not row.is_pilot:
            issues.append({"sample_id": row.sample_id, "code": "NONPILOT_ROW_IN_PILOT"})
    if mode == "main":
        if pilot is None:
            issues.append({"sample_id": None, "code": "PILOT_EXCLUSIONS_REQUIRED"})
        else:
            issues.extend(leakage_issues(pilot, rows))
    return {
        "valid": not issues, "mode": mode, "n_rows": len(rows),
        "n_unique_images": len({(row.metadata.get('image_namespace', row.source_dataset), row.image_id) for row in rows}),
        "qa_status": dict(Counter(row.qa_status for row in rows)),
        "translation_status": dict(Counter(row.translation_status for row in rows)),
        "warnings": ["Pilot validation does not approve translations or source labels for final evaluation"] if mode == "pilot" else [],
        "issues": issues,
    }
