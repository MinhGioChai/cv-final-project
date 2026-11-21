"""UTF-8 I/O and atomic replacement for small artifacts."""

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import yaml

from .schemas import ManifestRow, PilotConfig


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            name = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def write_json(path: Path, value: Any) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def read_config(path: Path) -> PilotConfig:
    return PilotConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def manifest_bytes(rows: list[ManifestRow]) -> bytes:
    if not rows:
        raise ValueError("Refusing to write an empty manifest")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(ManifestRow.model_fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        record = row.model_dump()
        for key in ("metadata", "ground_truth", "sampling_seed", "is_pilot"):
            record[key] = json.dumps(record[key], ensure_ascii=False, sort_keys=True)
        writer.writerow(record)
    return buffer.getvalue().encode("utf-8")


def write_manifest(path: Path, rows: list[ManifestRow]) -> None:
    atomic_bytes(path, manifest_bytes(rows))


def read_manifest(path: Path) -> list[ManifestRow]:
    if path.suffix == ".jsonl":
        return [ManifestRow.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix != ".csv":
        raise ValueError("Stage 0 supports .csv and .jsonl manifests only")
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for number, record in enumerate(csv.DictReader(stream), start=2):
            try:
                for key in ("metadata", "ground_truth", "sampling_seed", "is_pilot"):
                    record[key] = json.loads(record[key])
                rows.append(ManifestRow.model_validate(record))
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"Invalid manifest row at CSV line {number}: {exc}") from exc
    return rows
