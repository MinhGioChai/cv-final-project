"""Bounded RePOPE Dataset Viewer client; no model weights or full image corpus."""

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from ..io_utils import atomic_bytes, sha256_file, write_json
from ..qa import preflight_image
from ..sampling import CATEGORIES
from ..schemas import ManifestRow, PilotConfig

DATASET = "MM-Hallu/RePOPE"
HUB_API = f"https://huggingface.co/api/datasets/{DATASET}"
VIEWER_API = "https://datasets-server.huggingface.co"
LOG = logging.getLogger(__name__)


class SourceError(RuntimeError):
    pass


class BoundedClient:
    def __init__(self, max_bytes: int, *, allowed_hosts: set[str] | None = None):
        self.max_bytes = max_bytes
        self.downloaded_bytes = 0
        self.allowed_hosts = allowed_hosts or {"huggingface.co", "datasets-server.huggingface.co"}

    def get(self, url: str) -> bytes:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts:
            raise SourceError("Only official HTTPS endpoints on the configured host allowlist are supported")
        # Do not log query strings: cached-assets links are temporary signed URLs.
        for attempt in range(3):
            try:
                remaining = self.max_bytes - self.downloaded_bytes
                if remaining <= 0:
                    raise SourceError("Download budget exhausted; no automatic limit increase")
                request = urllib.request.Request(url, headers={"User-Agent": "vlmbench/0.1"})
                with urllib.request.urlopen(request, timeout=45) as response:
                    size = int(response.headers.get("Content-Length", 0))
                    if size > remaining:
                        raise SourceError("Response exceeds remaining Stage 0 download budget")
                    chunks = []
                    while True:
                        block = response.read(min(65536, remaining + 1))
                        self.downloaded_bytes += len(block)
                        remaining -= len(block)
                        if remaining < 0:
                            raise SourceError("Download budget exceeded; response discarded")
                        if not block:
                            return b"".join(chunks)
                        chunks.append(block)
            except urllib.error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise SourceError(f"Source HTTP {exc.code} at {parsed.hostname}{parsed.path}; retry later or use --offline with a complete cache") from None
                LOG.warning("Source HTTP %s; retry %s/2", exc.code, attempt + 1)
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise SourceError("Cannot reach source host. Check network access or use --offline with a complete cache") from None
                LOG.warning("Network request failed; retry %s/2", attempt + 1)
            time.sleep(0.5 * (attempt + 1))
        raise AssertionError("unreachable")

    def json(self, url: str) -> dict[str, Any]:
        try:
            return json.loads(self.get(url))
        except (ValueError, UnicodeError):
            raise SourceError("Source returned invalid JSON") from None


def _validate_pool(pool: list[dict[str, Any]], revision: str) -> None:
    if not pool:
        raise SourceError("Empty candidate pool")
    identities = set()
    for row in pool:
        required = {"source_row_id", "image_id", "question", "answer", "category", "image_url"}
        if not required.issubset(row):
            raise SourceError("RePOPE pool has missing fields")
        if not all(isinstance(row[key], str) and row[key] for key in required):
            raise SourceError("RePOPE pool fields must be nonempty strings")
        if row["category"] not in CATEGORIES or row["answer"] not in {"yes", "no"}:
            raise SourceError("Unexpected RePOPE category/ground truth; refusing to change source labels")
        if not row["image_id"].isdigit():
            raise SourceError("Expected numeric COCO image ID")
        url = urllib.parse.urlsplit(row["image_url"])
        if url.scheme != "https" or url.hostname != "datasets-server.huggingface.co" or f"/--/{revision}/--/" not in url.path:
            raise SourceError("Image URL revision does not match pinned RePOPE revision")
        if row["source_row_id"] in identities:
            raise SourceError("Duplicate source row IDs in RePOPE pool")
        identities.add(row["source_row_id"])


def load_pool(
    config: PilotConfig, *, root: Path, client: BoundedClient,
    offline: bool = False, refresh: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cache = root / config.cache_dir
    pool_file, receipt_file = cache / "pool.json", cache / "source_receipt.json"
    if offline and refresh:
        raise ValueError("--offline and --refresh cannot be combined")
    if pool_file.exists() and receipt_file.exists() and not refresh:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        if (receipt["revision"] != config.source_revision
                or receipt["pool_rows_per_page"] != config.pool_rows_per_page
                or receipt["pool_page_offsets"] != config.pool_page_offsets):
            raise SourceError("Cached source/config mismatch; inspect config before using --refresh")
        if receipt["pool_sha256"] != sha256_file(pool_file):
            raise SourceError("Candidate pool checksum mismatch; restore cache or use --refresh")
        pool = json.loads(pool_file.read_text(encoding="utf-8"))
        _validate_pool(pool, config.source_revision)
        return pool, receipt
    if offline:
        raise SourceError("No complete cached RePOPE snapshot. Run prepare-pilot online once (no GPU/token required)")
    hub = client.json(HUB_API)
    if hub.get("sha") != config.source_revision:
        raise SourceError("Hub HEAD differs from pinned revision. Dataset Viewer cannot pin old revisions; stop and review source config")
    pool = []
    source_total = None
    for offset in config.pool_page_offsets:
        query = urllib.parse.urlencode({
            "dataset": DATASET, "config": "default", "split": config.source_split,
            "offset": offset, "length": config.pool_rows_per_page,
        })
        LOG.info("Reading bounded RePOPE page at offset %s (up to %s rows)", offset, config.pool_rows_per_page)
        payload = client.json(f"{VIEWER_API}/rows?{query}")
        if payload.get("partial") or not payload.get("rows"):
            raise SourceError(f"Incomplete/empty viewer response at offset {offset}")
        if source_total is not None and source_total != payload["num_rows_total"]:
            raise SourceError("Source row count changed between pages")
        source_total = payload["num_rows_total"]
        for entry in payload["rows"]:
            if entry.get("truncated_cells"):
                raise SourceError("Truncated source fields; refusing partial records")
            row = entry["row"]
            pool.append({
                "source_row_id": str(entry['row_idx']),
                "viewer_row_idx": entry["row_idx"],
                "image_id": row["image_id"], "question": row["question"],
                "answer": row["answer"], "category": row["category"],
                "image_url": row["image"]["src"],
            })
    _validate_pool(pool, config.source_revision)
    if client.json(HUB_API).get("sha") != config.source_revision:
        raise SourceError("Dataset changed during acquisition; refusing mixed-revision snapshot")
    write_json(pool_file, pool)
    receipt = {
        "dataset": DATASET, "revision": config.source_revision,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": config.source_split, "source_card_license": hub.get("cardData", {}).get("license"),
        "pool_rows_per_page": config.pool_rows_per_page,
        "pool_page_offsets": config.pool_page_offsets,
        "pool_sha256": sha256_file(pool_file), "pool_rows": len(pool),
        "viewer_reported_total_rows": source_total,
        "selection_scope": "three_bounded_pages_not_representative_final_sample",
        "revision_check": "Hub HEAD before/after + revision in every image asset URL",
        "upstream_annotation_equivalence": "not_yet_independently_verified",
        "image_license": "MS COCO underlying images: review individual image rights before redistribution",
    }
    write_json(receipt_file, receipt)
    return pool, receipt


def materialize(
    selected: list[dict[str, Any]], config: PilotConfig, *, root: Path,
    client: BoundedClient, offline: bool = False,
) -> list[ManifestRow]:
    rows = []
    for candidate in selected:
        relative = Path(config.cache_dir) / "images" / f"{candidate['image_id']}.jpg"
        image_path = root / relative
        if not image_path.exists():
            if offline:
                raise SourceError(f"Cached image missing for {candidate['image_id']}; run online with --refresh if asset links expired")
            atomic_bytes(image_path, client.get(candidate["image_url"]))
        info = preflight_image(image_path)
        stable_id = hashlib.sha256(
            f"{config.source_revision}|{candidate['category']}|{candidate['image_id']}|{candidate['question']}".encode("utf-8")
        ).hexdigest()[:16]
        rows.append(ManifestRow(
            sample_id=f"repope_{candidate['category']}_{stable_id}",
            source_dataset="repope", source_split=config.source_split,
            source_row_id=candidate["source_row_id"], image_id=candidate["image_id"],
            image_path=relative.as_posix(), image_sha256=info["sha256"],
            task="object_existence", category=candidate["category"],
            question_en=candidate["question"], question_vi="",
            ground_truth=candidate["answer"], ground_truth_source="repope_hf_original_label",
            qa_status="pending", translation_status="missing", is_pilot=True,
            sampling_seed=config.seed,
            metadata={
                "source_repository": DATASET, "source_revision": config.source_revision,
                "image_namespace": "coco", "image_width": info["width"], "image_height": info["height"],
                "source_asset_path": urllib.parse.urlsplit(candidate["image_url"]).path,
                "stage": config.purpose, "human_label_qa": "pending",
            },
        ))
    return rows
