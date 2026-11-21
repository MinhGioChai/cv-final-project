"""Build a private team handoff ZIP from explicit project inputs, never credentials/weights."""

import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from .io_utils import atomic_bytes, read_manifest, sha256_file
from .qa import validate_manifest


def build_pilot_bundle(root: Path, output: Path, manifest: str = "data/pilot/stage1_v3/pilot_manifest.csv") -> dict:
    files: set[Path] = set()
    for name in ("pyproject.toml", "README.md", "requirements-stage0.lock.txt", "requirements-inference.lock.txt"):
        files.add(root / name)
    for name in ("HUONG_DAN_NHOM.md", "CONTRIBUTING.md", "README_START_HERE.md", "AGENTS.md", "01_RESEARCH_OUTLINE_V42.md", "02_DRAFT_CONG_VIEC_V42.md", "03_CODEX_HANDOFF_V42.md", "project_topics.md"):
        if (root / name).is_file():
            files.add(root / name)
    for folder, suffixes in (("src", {".py", ".html"}), ("configs", {".yaml"}), ("scripts", {".py"}),
                             ("notebooks", {".ipynb"}), ("docs", {".md"}), ("tests", {".py", ".md", ".cjs"})):
        files.update(path for path in (root / folder).rglob("*") if path.is_file() and path.suffix in suffixes and "__pycache__" not in path.parts)
    for folder, suffixes in (("reports", {".md", ".json", ".jsonl", ".csv"}), ("data/reviews", {".csv", ".json"}),
                             ("data/dictionaries", {".csv", ".json", ".txt"}), ("data/pilot", {".csv", ".json"})):
        files.update(path for path in (root / folder).rglob("*") if path.is_file() and path.suffix in suffixes
                     and path.name not in {"portable_bundle.json", "bundle_verification.json"})
    files.add(root / manifest)
    files.add(root / "data/pilot/image_exclusions.json")
    files.add(root / "reports/stage1/v3/translation_acceptance.json")
    rows = read_manifest(root / manifest)
    if not validate_manifest(rows, root=root, mode="pilot")["valid"] or len(rows) > 30:
        raise ValueError("Only the bounded pilot is packaged")
    for row in rows:
        image = (root / row.image_path).resolve()
        if not image.is_relative_to(root.resolve()) or sha256_file(image) != row.image_sha256:
            raise ValueError("Image path/checksum is invalid; refusing to package")
        files.add(image)
    contents = {}
    for path in sorted(files):
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        if not path.is_file():
            raise ValueError(f"Bundle input missing: {relative}")
        contents[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024) as buffer:
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            def write_stable(name, payload):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED)
            for path in sorted(files):
                relative = path.resolve().relative_to(root.resolve()).as_posix()
                write_stable(f"vlmbench-pilot/{relative}", path.read_bytes())
            write_stable("vlmbench-pilot/BUNDLE_CONTENTS.json", json.dumps({"manifest": manifest, "rows": len(rows), "files": contents}, indent=2))
        buffer.seek(0)
        payload = buffer.read()
    if output.exists() and output.read_bytes() != payload:
        raise ValueError("Pilot bundle already exists with different contents; use a new output version")
    if not output.exists():
        atomic_bytes(output, payload)
    return {"output": output.as_posix(), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
            "n_rows": len(rows), "n_images": len({row.image_sha256 for row in rows}), "files": len(contents),
            "excludes": [".git", ".env", "HF tokens", "virtual environments", "model weights", "raw metadata caches", "private results/ checkpoints"],
            "includes_public_pilot_snapshots": (root / "reports/pilot_outputs").is_dir()}
