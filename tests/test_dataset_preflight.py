import hashlib
import io
import json
import urllib.parse

from PIL import Image
import pytest

from vlmbench.cli import main
from vlmbench.datasets.repope import BoundedClient, DATASET, HUB_API, SourceError, load_pool
from vlmbench.io_utils import read_config

REVISION = "a" * 40


@pytest.fixture
def config_root(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/pilot.yaml").write_text(
        f"""experiment_id: synthetic_test_only
dataset: repope
source_revision: {REVISION}
source_split: train
pool_rows_per_page: 10
pool_page_offsets: [0, 100, 200]
sample_size: 6
seed: 42
max_rows_per_image: 1
max_download_mb: 1
cache_dir: data/raw/repope/stage0
manifest: data/pilot/pilot_manifest.csv
report_dir: reports/stage0
require_approved: false
""", encoding="utf-8")
    return tmp_path


class SyntheticClient:
    """synthetic_test_only — never accesses network or produces model outputs."""
    downloaded_bytes = 0

    def __init__(self, max_bytes=1024 * 1024):
        pass

    def json(self, url):
        if url == HUB_API:
            return {"sha": REVISION, "cardData": {"license": "synthetic_test_only"}}
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        offset = int(query["offset"][0])
        category = {0: "random", 100: "popular", 200: "adversarial"}[offset]
        return {"num_rows_total": 300, "partial": False, "rows": [
            {"row_idx": offset + i, "truncated_cells": [], "row": {
                "image_id": f"{offset + i:012}", "question": "Is there a dog in the image?",
                "answer": "yes" if i % 2 else "no", "category": category,
                "image": {"src": f"https://datasets-server.huggingface.co/cached-assets/MM-Hallu/RePOPE/--/{REVISION}/--/default/train/{offset+i}/image/image.jpg"},
            }} for i in range(10)]}

    def get(self, url):
        buffer = io.BytesIO()
        Image.new("RGB", (5, 4), color="green").save(buffer, format="JPEG")
        return buffer.getvalue()


def test_online_then_offline_replay_without_network_or_overwriting_review(config_root, monkeypatch):
    monkeypatch.setattr("vlmbench.cli.BoundedClient", SyntheticClient)
    arguments = ["--root", str(config_root), "prepare-pilot"]
    assert main(arguments) == 0
    assert "Nhãn nguồn" in (config_root / "reports/stage0/samples.md").read_text(encoding="utf-8")
    manifest = config_root / "data/pilot/pilot_manifest.csv"
    before = hashlib.sha256(manifest.read_bytes()).hexdigest()
    review = config_root / "reports/stage0/sample_review.csv"
    review.write_text("human edits must survive", encoding="utf-8")
    def fail(*args, **kwargs):
        pytest.fail("Offline mode must not access the network")
    monkeypatch.setattr(SyntheticClient, "get", fail)
    monkeypatch.setattr(SyntheticClient, "json", fail)
    assert main(arguments + ["--offline"]) == 0
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == before
    assert review.read_text(encoding="utf-8") == "human edits must survive"
    assert not (config_root / "results").exists()
    assert main(["--root", str(config_root), "inspect", "--dataset", "repope", "--limit", "6"]) == 0
    assert main(["--root", str(config_root), "validate", "--manifest", "data/pilot/pilot_manifest.csv", "--mode", "main"]) == 1


def test_offline_without_cache_fails_with_actionable_error(config_root):
    config = read_config(config_root / "configs/pilot.yaml")
    with pytest.raises(SourceError, match="No complete cached"):
        load_pool(config, root=config_root, client=SyntheticClient(), offline=True)


def test_revision_mismatch_is_fatal(config_root):
    class WrongRevision(SyntheticClient):
        def json(self, url):
            return {"sha": "b" * 40}
    config = read_config(config_root / "configs/pilot.yaml")
    with pytest.raises(SourceError, match="HEAD differs"):
        load_pool(config, root=config_root, client=WrongRevision())


def test_image_asset_from_wrong_revision_is_fatal(config_root):
    class WrongAsset(SyntheticClient):
        def json(self, url):
            payload = super().json(url)
            for entry in payload.get("rows", []):
                entry["row"]["image"]["src"] = entry["row"]["image"]["src"].replace(REVISION, "b" * 40)
            return payload
    with pytest.raises(SourceError, match="revision"):
        load_pool(read_config(config_root / "configs/pilot.yaml"), root=config_root, client=WrongAsset())


def test_cached_metadata_tampering_rejected(config_root):
    config = read_config(config_root / "configs/pilot.yaml")
    load_pool(config, root=config_root, client=SyntheticClient())
    cache = config_root / config.cache_dir / "pool.json"
    cache.write_text("[]", encoding="utf-8")
    with pytest.raises(SourceError, match="checksum mismatch"):
        load_pool(config, root=config_root, client=SyntheticClient(), offline=True)


def test_download_budget_stops_before_large_response(monkeypatch):
    class LargeResponse:
        headers = {"Content-Length": "100"}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, length):
            pytest.fail("Oversized response should not be read")
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: LargeResponse())
    with pytest.raises(SourceError, match="exceeds remaining"):
        BoundedClient(20).get(HUB_API)


def test_non_hf_asset_host_rejected():
    with pytest.raises(SourceError, match="Only official HTTPS"):
        BoundedClient(100).get("https://example.com/image.jpg")


def test_prepare_expands_without_replacing_retained_manifest(config_root, monkeypatch):
    from vlmbench.io_utils import read_manifest
    monkeypatch.setattr("vlmbench.cli.BoundedClient", SyntheticClient)
    assert main(["--root", str(config_root), "prepare-pilot"]) == 0
    original = config_root / "data/pilot/pilot_manifest.csv"
    before = original.read_bytes()
    base = read_manifest(original)
    text = (config_root / "configs/pilot.yaml").read_text(encoding="utf-8")
    text = text.replace("sample_size: 6", "sample_size: 12").replace("manifest: data/pilot/pilot_manifest.csv", "manifest: data/pilot/expanded.csv").replace("report_dir: reports/stage0", "report_dir: reports/expanded")
    (config_root / "configs/expanded.yaml").write_text(text + "purpose: bilingual_pilot\n", encoding="utf-8")
    args = ["--root", str(config_root), "prepare-pilot", "--config", "configs/expanded.yaml", "--retain-manifest", str(original)]
    assert main(args) == 0
    expanded = read_manifest(config_root / "data/pilot/expanded.csv")
    by_id = {row.sample_id: row for row in expanded}
    assert all(by_id[row.sample_id] == row for row in base)
    assert original.read_bytes() == before
    assert len(expanded) == 12
    assert main(args + ["--offline"]) == 0
    registry = json.loads((config_root / "data/pilot/image_exclusions.json").read_text(encoding="utf-8"))
    assert len(registry["images"]) == 12
