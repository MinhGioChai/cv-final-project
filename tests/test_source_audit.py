import json

import pytest

from vlmbench.datasets.repope import SourceError
from vlmbench.source_audit import SourceAuditConfig, audit_rows, load_upstream, parse_annotations


def annotations(image_id="000000000001", label="yes", question="Is there a dog in the image?"):
    return {"random": (json.dumps({"question_id": 1, "image": f"COCO_val2014_{image_id}.jpg", "text": question, "label": label}) + "\n").encode()}


def receipt():
    return {"repository": "synthetic_test_only", "revision": "a" * 40,
            "files": {"random": {"sha256": "b" * 64}}}


def test_source_match_preserves_labels_and_qa(row_factory):
    row = row_factory()
    verified, report = audit_rows([row], annotations(), receipt())
    assert report["all_matched"]
    assert report["status_counts"] == {"matched": 1}
    assert row.metadata.get("upstream_verification") is None
    assert verified[0].ground_truth == row.ground_truth
    assert verified[0].qa_status == "pending"
    assert verified[0].metadata["upstream_verification"]["question_id"] == 1


def test_label_mismatch_is_reported_without_source_relabeling(row_factory):
    row = row_factory(ground_truth="no")
    verified, report = audit_rows([row], annotations(), receipt())
    assert verified == []
    assert not report["all_matched"]
    assert report["status_counts"] == {"label_mismatch": 1}
    assert row.ground_truth == "no"


@pytest.mark.parametrize("changes", [{"question_en": "Is there a cat in the image?"}, {"image_id": "000000000002"}, {"category": "popular"}])
def test_join_requires_same_image_question_and_category(row_factory, changes):
    _, report = audit_rows([row_factory(**changes)], annotations(), receipt())
    assert report["status_counts"] == {"missing_upstream_question": 1}


def test_ambiguous_duplicate_annotations_cannot_be_treated_as_verified(row_factory):
    content = annotations()
    content["random"] *= 2
    _, report = audit_rows([row_factory()], content, receipt())
    assert report["status_counts"] == {"ambiguous_upstream_question": 1}


@pytest.mark.parametrize("payload", [b'[]\n', b'{"image":"bad"}\n', b'not-json\n', b''])
def test_malformed_or_empty_source_rejected(payload):
    with pytest.raises(ValueError):
        parse_annotations({"random": payload})


def test_upstream_cache_download_replay_and_checksum(tmp_path, monkeypatch):
    # Reuses temporary root only; all upstream content remains synthetic_test_only.
    import vlmbench.source_audit as module
    config = SourceAuditConfig(repository="YanNeu/RePOPE", revision="a" * 40,
                               cache_dir="data/raw/upstream/synthetic_test_only", max_download_mb=1)
    class FakeClient:
        downloaded_bytes = 0
        def __init__(self, *args, **kwargs):
            pass
        def get(self, url):
            return annotations()["random"]
    monkeypatch.setattr(module, "BoundedClient", FakeClient)
    content, saved = load_upstream(config, root=tmp_path)
    assert set(content) == {"random", "popular", "adversarial"}
    assert load_upstream(config, root=tmp_path, offline=True) == (content, saved)
    (tmp_path / config.cache_dir / "coco_repope_random.json").write_bytes(b"bad")
    with pytest.raises(SourceError, match="corrupt"):
        load_upstream(config, root=tmp_path, offline=True)


def test_no_cached_upstream_offline_is_actionable(tmp_path):
    config = SourceAuditConfig(repository="YanNeu/RePOPE", revision="a" * 40, cache_dir="cache", max_download_mb=1)
    with pytest.raises(SourceError, match="No upstream snapshot"):
        load_upstream(config, root=tmp_path, offline=True)
