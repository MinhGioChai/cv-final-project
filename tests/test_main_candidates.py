import json

import pytest

from vlmbench.datasets.candidates import Candidate
from vlmbench.datasets.oxford_pet import parse_oxford_pet, read_pet_list
from vlmbench.datasets.repope_frame import parse_repope_frame
from vlmbench.datasets.tallyqa import parse_tallyqa
from vlmbench.datasets.vsr import parse_vsr
from vlmbench.schemas import ManifestRow


def vsr_record(**changes):
    return {"image": "000000000123.jpg", "image_link": "http://images.cocodataset.org/train2017/000000000123.jpg",
            "caption": "synthetic_test_only: the dog is not behind the chair.", "label": 0, "relation": "behind", **changes}


def tally_record(**changes):
    return {"image": "VG_100K_2/1.jpg", "answer": 0, "data_source": "synthetic_test_only",
            "question": "synthetic_test_only: How many dogs?", "image_id": 90000001,
            "question_id": 123, "issimple": False, **changes}


def test_vsr_preserves_statement_relation_and_false_label():
    source = vsr_record()
    row = parse_vsr(json.dumps(source).encode(), revision="synthetic_test_only")[0]
    assert row.ground_truth == "no" and row.question_en == source["caption"]
    assert row.image_id == "000000000123" and row.image_namespace == "coco"
    assert row.metadata["original_label"] == 0 and row.metadata["external_answer_labels"] == ["TRUE", "FALSE"]


@pytest.mark.parametrize("changes", [dict(label=True), dict(label=2), dict(image="123.jpg"),
    dict(image_link="https://example.com/000000000123.jpg"), dict(image_link="https://images.cocodataset.org/train2017/000000000124.jpg")])
def test_vsr_unknown_schema_cannot_silently_relabel(changes):
    with pytest.raises(ValueError):parse_vsr(json.dumps(vsr_record(**changes)).encode(), revision="synthetic_test_only")


def test_vsr_variants_stay_separate():
    payload = json.dumps(vsr_record(label=1)).encode()
    a = parse_vsr(payload, revision="synthetic_test_only", variant="random")[0]
    b = parse_vsr(payload, revision="synthetic_test_only", variant="zeroshot")[0]
    assert a.sample_id != b.sample_id and a.ground_truth == b.ground_truth == "yes"


def test_tally_uses_underlying_vg_identity_not_encoded_source_id():
    a = parse_tallyqa(json.dumps([tally_record()]).encode(), revision="synthetic_test_only")[0]
    b = parse_tallyqa(json.dumps([tally_record(image="VG_100K/1.jpg")]).encode(), revision="synthetic_test_only")[0]
    assert a.image_namespace == "visual_genome" and a.image_id == b.image_id == "1"
    assert a.metadata["original_image_id"] == 90000001
    assert a.ground_truth == 0 and a.category == "complex"


@pytest.mark.parametrize("changes", [dict(answer=True), dict(answer=-1), dict(answer="2"), dict(issimple=1),
                                      dict(image="VG_100K/../../1.jpg")])
def test_tally_invalid_types_and_paths_rejected(changes):
    with pytest.raises(ValueError):parse_tallyqa(json.dumps([tally_record(**changes)]).encode(), revision="synthetic_test_only")


def test_tally_duplicate_question_identity_rejected():
    with pytest.raises(ValueError):parse_tallyqa(json.dumps([tally_record(), tally_record()]).encode(), revision="synthetic_test_only")


def pet_fixture():
    breeds = ["synthetic_dog_" + c for c in "abcdefgh"]
    payload = "\n".join(f"{name}_1 {i+1} 2 {i+1}" for i, name in enumerate(breeds)).encode()
    return breeds, payload


def test_pet_mapping_is_explicit_and_subset_only():
    breeds, payload = pet_fixture()
    rows = parse_oxford_pet(payload, revision="synthetic_test_only", breeds=breeds[::-1])
    assert rows[0].ground_truth == "H" and rows[-1].ground_truth == "A"
    assert rows[0].metadata["source_class_id"] == 1 and rows[0].metadata["source_species"] == 2
    assert rows[0].metadata["evaluation_scope"].endswith("not_37_way")


@pytest.mark.parametrize("case", ["seven", "duplicate", "missing", "cat"])
def test_pet_bad_class_selection_rejected(case):
    breeds, payload = pet_fixture()
    if case == "seven":breeds = breeds[:7]
    if case == "duplicate":breeds[1] = breeds[0]
    if case == "missing":breeds[-1] = "synthetic_missing"
    if case == "cat":payload = payload.replace(b"1 2 1", b"1 1 1", 1)
    with pytest.raises(ValueError):parse_oxford_pet(payload, revision="synthetic_test_only", breeds=breeds)


def test_pet_duplicate_source_image_rejected():
    with pytest.raises(ValueError):read_pet_list(b"synthetic_dog_1 1 2 1\nsynthetic_dog_1 1 2 1")


def test_repope_whole_frame_retains_categories_and_source_labels():
    record = {"image": "COCO_val2014_000000000001.jpg", "text": "synthetic_test_only?", "label": "no", "question_id": 1}
    rows = parse_repope_frame({c:json.dumps(record).encode() for c in ("random", "popular", "adversarial")}, revision="synthetic_test_only")
    assert len(rows) == len({r.sample_id for r in rows}) == 3
    assert all(r.ground_truth == "no" and r.image_id == "000000000001" for r in rows)
    assert {r.category for r in rows} == {"random", "popular", "adversarial"}


def test_metadata_candidate_cannot_be_used_as_image_ready_manifest():
    row = parse_vsr(json.dumps(vsr_record()).encode(), revision="synthetic_test_only")[0]
    assert row.stage == "metadata_candidate_not_main_manifest"
    with pytest.raises(ValueError):ManifestRow.model_validate(row.model_dump())
