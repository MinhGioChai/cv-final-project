import csv
import io
import json

import pytest

from vlmbench.cli import main
from vlmbench.io_utils import atomic_bytes, read_manifest, write_manifest
from vlmbench.reviews import FIELDS, export_review, import_review, write_review_preview
from vlmbench.translate import draft_question, load_dictionary


@pytest.fixture
def review_bundle(row_factory, tmp_path):
    rows = [row_factory()]
    manifest = tmp_path / "input.csv"
    write_manifest(manifest, rows)
    dictionary = tmp_path / "dictionary.csv"
    dictionary.write_text("object_en,object_vi,status,reviewer_id,reviewed_at,notes\ndog,chó,pending,,,synthetic_test_only\n", encoding="utf-8")
    review = tmp_path / "review.csv"
    export_review(rows, manifest_path=manifest, dictionary_path=dictionary, output=review)
    return rows, manifest, dictionary, review


def edit_review(path, **changes):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows[0].update(changes)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_bytes(path, buffer.getvalue().encode("utf-8-sig"))


def approve_translation():
    return dict(reviewer_1_id="synthetic_test_only_A", reviewer_1_status="approved", reviewer_1_reviewed_at="2026-11-09T18:00:00+07:00",
                reviewer_2_id="synthetic_test_only_B", reviewer_2_status="approved", reviewer_2_reviewed_at="2026-11-09T18:01:00+07:00", final_status="approved")


def run_import(bundle):
    rows, manifest, _, review = bundle
    return import_review(rows, manifest_path=manifest, review_path=review, operator="synthetic_test_only_operator")


def test_drafts_never_approve_rows(review_bundle):
    updated, audit = run_import(review_bundle)
    assert updated[0].question_vi == "Trong ảnh có chó nào không?"
    assert updated[0].translation_status == "requires_review"
    assert updated[0].qa_status == "pending"
    assert audit["translation_status"] == {"requires_review": 1}
    assert audit["events"][0]["before"]["question_vi"] == ""
    assert audit["export_context"]["dictionary_sha256"]


def test_dictionary_approval_alone_does_not_approve_question(review_bundle):
    dictionary = load_dictionary(review_bundle[2])
    dictionary["dog"]["status"] = "approved"
    assert draft_question("Is there a dog in the image?", dictionary)["translation_status"] == "requires_review"


@pytest.mark.parametrize("object_en,object_vi,classifier,expected", [
    ("bowl", "bát", "cái", "Trong ảnh có cái bát nào không?"),
    ("bicycle", "xe đạp", "chiếc", "Trong ảnh có chiếc xe đạp nào không?"),
    ("dog", "chó", "con", "Trong ảnh có con chó nào không?"),
    ("orange", "cam", "quả", "Trong ảnh có quả cam nào không?"),
    ("person", "người", "", "Trong ảnh có người nào không?"),
])
def test_explicit_vietnamese_classifiers(tmp_path, object_en, object_vi, classifier, expected):
    path = tmp_path / "classified_dictionary.csv"
    path.write_text(f"object_en,object_vi,classifier_vi,status,reviewer_id,reviewed_at,notes\n{object_en},{object_vi},{classifier},pending,,,synthetic_test_only\n", encoding="utf-8")
    draft = draft_question(f"Is there a {object_en} in the image?", load_dictionary(path))
    assert draft["question_vi"] == expected
    assert draft["translation_status"] == "requires_review"


def test_unknown_classifiers_are_not_guessed(tmp_path):
    path = tmp_path / "dictionary.csv"
    path.write_text("object_en,object_vi,classifier_vi,status,reviewer_id,reviewed_at,notes\nbowl,bát,unknown,pending,,,synthetic_test_only\n", encoding="utf-8")
    with pytest.raises(ValueError, match="classifier_vi"):
        load_dictionary(path)


def test_approved_dictionary_requires_recorded_reviewer(review_bundle):
    dictionary = review_bundle[2]
    dictionary.write_text(dictionary.read_text(encoding="utf-8").replace(",pending,,,", ",approved,,,"), encoding="utf-8")
    with pytest.raises(ValueError, match="reviewer ID"):
        load_dictionary(dictionary)


@pytest.mark.parametrize("question,reason", [("Is there a cat in the image?", "OBJECT_NOT_IN_DICTIONARY"),
                                             ("How many dogs are visible?", "TEMPLATE_MISMATCH"),
                                             ("Is there a dog in the image? Explain.", "TEMPLATE_MISMATCH")])
def test_unknown_or_nonmatching_question_stays_in_manual_queue(review_bundle, question, reason):
    draft = draft_question(question, load_dictionary(review_bundle[2]))
    assert draft["reason"] == reason
    assert draft["question_vi"] == ""


def test_rejected_dictionary_entry_is_never_used(review_bundle):
    dictionary = load_dictionary(review_bundle[2])
    dictionary["dog"]["status"] = "rejected"
    assert draft_question("Is there a dog in the image?", dictionary)["reason"] == "DICTIONARY_ENTRY_REJECTED"


def test_explicit_two_reviewer_translation_and_separate_image_qa(review_bundle):
    review = review_bundle[3]
    edit_review(review, **approve_translation())
    updated, _ = run_import(review_bundle)
    assert updated[0].translation_status == "approved"
    assert updated[0].qa_status == "pending"
    edit_review(review, qa_status="approved", qa_reviewer_id="synthetic_test_only_QA", qa_reviewed_at="2026-11-09T18:02:00+07:00")
    updated, audit = run_import(review_bundle)
    assert updated[0].qa_status == "approved"
    assert updated[0].ground_truth == review_bundle[0][0].ground_truth
    assert audit["events"][0]["review_record"]["qa_reviewer_id"] == "synthetic_test_only_QA"


def test_two_approvals_without_final_decision_remain_pending(review_bundle):
    decisions = approve_translation()
    decisions["final_status"] = "pending"
    edit_review(review_bundle[3], **decisions)
    assert run_import(review_bundle)[0][0].translation_status == "requires_review"


@pytest.mark.parametrize("changes", [
    {"final_status": "approved"},
    {"reviewer_2_id": "synthetic_test_only_A"},
    {"reviewer_1_id": ""}, {"reviewer_1_reviewed_at": "2026-11-09T18:00:00"},
    {"reviewer_1_reviewed_at": "invalid"}, {"question_vi": ""},
    {"qa_status": "approved", "qa_reviewer_id": "", "qa_reviewed_at": ""},
    {"final_status": "maybe"},
])
def test_incomplete_or_invalid_approvals_rejected(review_bundle, changes):
    decisions = approve_translation()
    if changes == {"final_status": "approved"}:
        decisions = changes  # No reviewer decisions recorded.
    else:
        decisions.update(changes)
    edit_review(review_bundle[3], **decisions)
    with pytest.raises(ValueError):
        run_import(review_bundle)


@pytest.mark.parametrize("changes", [{"ground_truth": "no"}, {"image_id": "000000000002"},
                                    {"question_en": "Is there a cat in the image?"}, {"source_row_sha256": "x"},
                                    {"sample_id": "unknown"}])
def test_protected_source_fields_cannot_be_edited(review_bundle, changes):
    edit_review(review_bundle[3], **changes)
    with pytest.raises(ValueError):
        run_import(review_bundle)


def test_stale_manifest_cannot_receive_old_review(review_bundle):
    rows, manifest, _, review = review_bundle
    data = rows[0].model_dump()
    data["metadata"]["new_version"] = True
    changed = [type(rows[0]).model_validate(data)]
    write_manifest(manifest, changed)
    with pytest.raises(ValueError, match="context|stale"):
        import_review(changed, manifest_path=manifest, review_path=review, operator="synthetic_test_only")


@pytest.mark.parametrize("mode", ["duplicate", "missing"])
def test_review_must_have_exactly_one_record_per_sample(review_bundle, mode):
    review = review_bundle[3]
    lines = review.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    lines = lines + lines[1:] if mode == "duplicate" else lines[:1]
    review.write_text("".join(lines), encoding="utf-8-sig")
    with pytest.raises(ValueError, match="IDs must match"):
        run_import(review_bundle)


def test_missing_context_cannot_be_imported(review_bundle):
    review_bundle[3].with_suffix(".context.json").unlink()
    with pytest.raises(ValueError, match="Missing review export context"):
        run_import(review_bundle)


def test_preview_preserves_unicode_and_links_to_original_image(review_bundle, tmp_path):
    rows, _, _, review = review_bundle
    preview = tmp_path / "reports/preview.md"
    write_review_preview(rows, review_path=review, output=preview, root=tmp_path)
    text = preview.read_text(encoding="utf-8")
    assert "Trong ảnh có chó nào không?" in text
    assert "../synthetic_test_only.png" in text
    assert "pending" in text


def test_export_rerun_preserves_human_edits(review_bundle):
    rows, manifest, dictionary, review = review_bundle
    edit_review(review, question_vi="Có con chó nào trong ảnh không?", notes="synthetic_test_only human edit")
    before = review.read_bytes()
    result = export_review(rows, manifest_path=manifest, dictionary_path=dictionary, output=review)
    assert result["existing_review_preserved"]
    assert review.read_bytes() == before


def test_rejection_records_notes_and_allows_empty_translation(review_bundle):
    edit_review(review_bundle[3], question_vi="", reviewer_1_id="synthetic_test_only_A", reviewer_1_status="rejected",
                reviewer_1_reviewed_at="2026-11-09T18:00:00+07:00", final_status="rejected", notes="synthetic_test_only ambiguous object")
    updated, _ = run_import(review_bundle)
    assert updated[0].translation_status == "rejected"


def test_import_cli_dry_run_replay_and_audit_history(review_bundle, tmp_path):
    _, manifest, _, review = review_bundle
    output, audit = tmp_path / "out.csv", tmp_path / "audit.json"
    args = ["--root", str(tmp_path), "import-translation-review", "--manifest", str(manifest), "--review", str(review),
            "--output", str(output), "--audit", str(audit), "--operator", "synthetic_test_only"]
    assert main(args + ["--dry-run"]) == 0
    assert not output.exists() and not audit.exists()
    assert main(args) == 0
    before_output, before_audit = output.read_bytes(), audit.read_bytes()
    assert main(args) == 0
    assert output.read_bytes() == before_output
    assert audit.read_bytes() == before_audit
    edit_review(review, question_vi="Có chó trong ảnh không?")
    assert main(args) == 1
    assert output.read_bytes() == before_output and audit.read_bytes() == before_audit
    assert not (tmp_path / "results").exists()


def test_invalid_review_does_not_publish_any_output(review_bundle, tmp_path):
    _, manifest, _, review = review_bundle
    edit_review(review, **{"ground_truth": "no"})
    output, audit = tmp_path / "out.csv", tmp_path / "audit.json"
    assert main(["--root", str(tmp_path), "import-translation-review", "--manifest", str(manifest), "--review", str(review),
                 "--output", str(output), "--audit", str(audit), "--operator", "synthetic_test_only"]) == 1
    assert not output.exists() and not audit.exists()


def test_changed_image_cannot_receive_review_import(review_bundle, tmp_path):
    from PIL import Image
    rows, manifest, _, review = review_bundle
    Image.new("RGB", (8, 6), color="red").save(tmp_path / rows[0].image_path)
    output, audit = tmp_path / "out.csv", tmp_path / "audit.json"
    assert main(["--root", str(tmp_path), "import-translation-review", "--manifest", str(manifest), "--review", str(review),
                 "--output", str(output), "--audit", str(audit), "--operator", "synthetic_test_only"]) == 1
    assert not output.exists() and not audit.exists()
