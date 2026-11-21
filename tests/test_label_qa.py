import json
import re

import pytest

from vlmbench.cli import main
from vlmbench.io_utils import read_manifest, write_manifest
from vlmbench.label_qa import export_label_qa, import_label_qa, pending_review


@pytest.fixture
def label_project(row_factory, tmp_path):
    rows = [row_factory(question_vi="synthetic_test_only", translation_status="approved")]
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, rows)
    review = tmp_path / "review.json"
    review.write_text(json.dumps(pending_review(rows, manifest)), encoding="utf-8")
    return rows, dict(root=tmp_path, manifest_path=manifest, review_path=review, operator="synthetic_test_only_importer")


def edit(options, **values):
    p = options["review_path"]
    data = json.loads(p.read_text())
    data["decisions"][0].update(values)
    p.write_text(json.dumps(data))


def test_pending_import_preserves_accepted_translation_and_entire_row(label_project):
    rows, options = label_project
    result, audit = import_label_qa(rows, **options)
    assert result == rows and audit["qa_status"] == {"pending": 1}
    assert result[0].translation_status == "approved"


def test_explicit_qa_decision_changes_only_label_qa(label_project):
    rows, options = label_project
    edit(options, status="approved", observed_answer="yes", reviewer_id="synthetic_test_only_reviewer",
         reviewed_at="2026-11-19T17:00:00+07:00")
    result, audit = import_label_qa(rows, **options)
    assert result[0].qa_status == "approved"
    for key in type(rows[0]).model_fields:
        if key not in {"metadata", "qa_status"}:
            assert getattr(result[0], key) == getattr(rows[0], key)
    assert audit["events"][0]["decision"]["reviewer_id"] == "synthetic_test_only_reviewer"


@pytest.mark.parametrize("changes", [
    dict(status="approved", observed_answer="yes"),
    dict(status="approved", observed_answer="no", reviewer_id="synthetic_test_only", reviewed_at="2026-11-19T17:00:00+07:00"),
    dict(status="approved", observed_answer="yes", reviewer_id="synthetic_test_only", reviewed_at="2026-11-19T17:00:00"),
    dict(status="rejected", observed_answer="uncertain", reviewer_id="synthetic_test_only", reviewed_at="2026-11-19T17:00:00+07:00"),
    dict(ground_truth="no"),
])
def test_invalid_or_injected_decisions_rejected_without_manifest_mutation(label_project, changes):
    rows, options = label_project
    before = options["manifest_path"].read_bytes()
    edit(options, **changes)
    with pytest.raises(ValueError):
        import_label_qa(rows, **options)
    assert options["manifest_path"].read_bytes() == before


def test_rejection_keeps_source_label(label_project):
    rows, options = label_project
    edit(options, status="rejected", observed_answer="no", reviewer_id="synthetic_test_only",
         reviewed_at="2026-11-19T17:00:00Z", notes="synthetic_test_only mismatch")
    result, _ = import_label_qa(rows, **options)
    assert result[0].qa_status == "rejected" and result[0].ground_truth == "yes"


@pytest.mark.parametrize("mutate", ["missing", "duplicate", "context", "image"])
def test_stale_or_incomplete_review_rejected(label_project, mutate):
    rows, options = label_project
    data = json.loads(options["review_path"].read_text())
    if mutate == "missing":data["decisions"] = []
    if mutate == "duplicate":data["decisions"] *= 2
    if mutate == "context":data["context"]["manifest_sha256"] = "0" * 64
    if mutate == "image":(options["root"] / rows[0].image_path).write_bytes(b"synthetic_bad_image")
    options["review_path"].write_text(json.dumps(data))
    with pytest.raises(ValueError):import_label_qa(rows, **options)


def test_export_is_offline_safe_and_never_includes_model_answers(label_project):
    rows, options = label_project
    html = options["root"] / "review.html"
    report = export_label_qa(rows, root=options["root"], manifest_path=options["manifest_path"],
                             output=options["review_path"], html_path=html)
    assert report["human_approvals_created"] == 0
    text = html.read_text(encoding="utf-8")
    assert "data:image/png;base64," in text and "raw_response" not in text
    payload = json.loads(re.search(r'id="payload">(.*?)</script>', text, re.S).group(1))
    assert payload["review"]["decisions"][0]["status"] == "pending"
    before = html.read_bytes()
    export_label_qa(rows, root=options["root"], manifest_path=options["manifest_path"],
                    output=options["review_path"], html_path=html)
    assert html.read_bytes() == before


def test_html_script_payload_cannot_be_closed_by_question(label_project):
    rows, options = label_project
    rows[0] = rows[0].model_copy(update={"question_vi": "</script><script>synthetic_test_only</script>"})
    write_manifest(options["manifest_path"], rows)
    options["review_path"].unlink()
    html = options["root"] / "review.html"
    export_label_qa(rows, root=options["root"], manifest_path=options["manifest_path"],
                    output=options["review_path"], html_path=html)
    assert "</script><script>synthetic_test_only" not in html.read_text(encoding="utf-8")


def test_cli_dry_run_never_writes_or_downgrades_translation(label_project, capsys):
    _, options = label_project
    argv = ["--root", str(options["root"]), "import-label-qa", "--manifest", "manifest.csv",
            "--review", "review.json", "--output", "new.csv", "--audit", "audit.json",
            "--operator", "synthetic_test_only", "--dry-run"]
    assert main(argv) == 0
    assert json.loads(capsys.readouterr().out)["translation_status"] == {"approved": 1}
    assert not (options["root"] / "new.csv").exists()
    assert not (options["root"] / "audit.json").exists()


def test_cli_import_is_versioned_and_idempotent(label_project, capsys):
    _, options = label_project
    argv = ["--root", str(options["root"]), "import-label-qa", "--manifest", "manifest.csv",
            "--review", "review.json", "--output", "new.csv", "--audit", "audit.json", "--operator", "synthetic_test_only"]
    assert main(argv) == 0
    before = (options["root"] / "audit.json").read_bytes()
    assert main(argv) == 0
    assert (options["root"] / "audit.json").read_bytes() == before
    assert read_manifest(options["root"] / "new.csv")[0].translation_status == "approved"
