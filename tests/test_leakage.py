from vlmbench.qa import leakage_issues, validate_manifest


def test_different_question_same_image_leaks(row_factory):
    pilot = row_factory()
    final = row_factory(sample_id="another_question", question_en="Is there a cat?", is_pilot=False)
    codes = {item["code"] for item in leakage_issues([pilot], [final])}
    assert "PILOT_IMAGE_OVERLAP" in codes


def test_same_checksum_different_dataset_and_id_leaks(row_factory):
    pilot = row_factory()
    final = row_factory(source_dataset="vsr", image_id="different", metadata={"image_namespace": "other"})
    assert any(issue["code"] == "PILOT_CHECKSUM_OVERLAP" for issue in leakage_issues([pilot], [final]))


def test_coco_namespace_catches_cross_dataset_same_image(row_factory):
    pilot = row_factory()
    final = row_factory(source_dataset="vsr", image_sha256="b" * 64)
    assert any(issue["code"] == "PILOT_IMAGE_OVERLAP" for issue in leakage_issues([pilot], [final]))


def test_unrelated_ids_and_checksums_do_not_leak(row_factory):
    assert leakage_issues([row_factory()], [row_factory(image_id="002", image_sha256="c" * 64)]) == []


def test_main_requires_qa_and_explicit_pilot_exclusions(row_factory, tmp_path):
    report = validate_manifest([row_factory()], root=tmp_path, mode="main")
    assert not report["valid"]
    codes = {issue["code"] for issue in report["issues"]}
    assert {"PILOT_ROW_IN_MAIN", "MAIN_QA_NOT_APPROVED", "PILOT_EXCLUSIONS_REQUIRED"}.issubset(codes)
