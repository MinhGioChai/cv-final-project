import pytest
from pydantic import ValidationError

from vlmbench.io_utils import read_manifest, write_manifest


def test_csv_round_trip_preserves_leading_zero_ids_and_unicode(row_factory, tmp_path):
    original = row_factory(question_vi="Trong ảnh có chó không?", translation_status="requires_review")
    path = tmp_path / "manifest.csv"
    write_manifest(path, [original])
    assert read_manifest(path) == [original]
    assert read_manifest(path)[0].image_id == "000000000001"


@pytest.mark.parametrize("changes", [
    {"ground_truth": "maybe"}, {"ground_truth": True}, {"image_sha256": "bad"},
    {"is_pilot": "false"}, {"question_en": " "}, {"sampling_seed": "42"},
    {"translation_status": "approved", "question_vi": ""},
    {"question_vi": "Có chó không?", "translation_status": "missing"},
    {"task": "counting", "ground_truth": "2"},
    {"task": "counting", "ground_truth": -1},
    {"task": "fine_grained", "ground_truth": "Labrador"},
])
def test_invalid_contract_rejected(row_factory, changes):
    with pytest.raises(ValidationError):
        row_factory(**changes)


def test_integer_ground_truth_round_trip(row_factory, tmp_path):
    row = row_factory(task="counting", ground_truth=2)
    path = tmp_path / "manifest.csv"
    write_manifest(path, [row])
    assert type(read_manifest(path)[0].ground_truth) is int


def test_missing_required_field_fails(row_factory):
    data = row_factory().model_dump()
    del data["ground_truth_source"]
    with pytest.raises(ValidationError):
        type(row_factory()).model_validate(data)
