from PIL import Image

from vlmbench.qa import preflight_image, validate_manifest


def test_loads_pixels_and_checks_dimensions(row_factory, tmp_path):
    row = row_factory()
    info = preflight_image(tmp_path / row.image_path)
    assert (info["width"], info["height"], info["sha256"]) == (8, 6, row.image_sha256)
    assert validate_manifest([row], root=tmp_path)["valid"]


def test_missing_image_is_reported(row_factory, tmp_path):
    report = validate_manifest([row_factory(image_path="missing.png")], root=tmp_path)
    assert report["issues"][0]["code"] == "IMAGE_PREFLIGHT_FAILED"


def test_corrupt_image_is_reported(row_factory, tmp_path):
    row = row_factory()
    (tmp_path / row.image_path).write_bytes(b"broken_image")
    assert not validate_manifest([row], root=tmp_path)["valid"]


def test_changed_pixels_detected(row_factory, tmp_path):
    row = row_factory()
    Image.new("RGB", (8, 6), color="red").save(tmp_path / row.image_path)
    assert validate_manifest([row], root=tmp_path)["issues"][0]["code"] == "IMAGE_CHECKSUM_MISMATCH"


def test_duplicate_sample_ids_are_reported(row_factory, tmp_path):
    row = row_factory()
    assert any(issue["code"] == "DUPLICATE_SAMPLE_ID" for issue in validate_manifest([row, row], root=tmp_path)["issues"])


def test_empty_manifest_not_valid(tmp_path):
    assert not validate_manifest([], root=tmp_path)["valid"]
