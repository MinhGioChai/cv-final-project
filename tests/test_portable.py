import ast
import json
from pathlib import Path
import zipfile
import pytest

from vlmbench.io_utils import write_manifest
from vlmbench.portable import build_pilot_bundle


def test_bundle_contains_required_pilot_files_but_not_tokens_caches_or_weights(row_factory, tmp_path):
    for name in ("pyproject.toml", "README.md", "requirements-stage0.lock.txt", "requirements-inference.lock.txt"):
        (tmp_path / name).write_text("synthetic_test_only", encoding="utf-8")
    (tmp_path / "HUONG_DAN_NHOM.md").write_text("synthetic_test_only_team_guide",encoding="utf-8")
    (tmp_path / ".env").write_text("synthetic_secret_token", encoding="utf-8")
    (tmp_path / "model.safetensors").write_bytes(b"synthetic_model_weights")
    template = tmp_path / "src/vlmbench/label_qa_template.html"
    template.parent.mkdir(parents=True)
    template.write_text("<html>synthetic_test_only</html>")
    glossary = tmp_path / "data/dictionaries/synthetic_draft.json"
    glossary.parent.mkdir(parents=True)
    glossary.write_text('{"synthetic_test_only":true}')
    manifest = tmp_path / "data/pilot/stage1_v3/pilot_manifest.csv"
    write_manifest(manifest, [row_factory()])
    (tmp_path / "data/pilot/image_exclusions.json").write_text('{"images":[]}', encoding="utf-8")
    acceptance = tmp_path / "reports/stage1/v3/translation_acceptance.json"
    acceptance.parent.mkdir(parents=True)
    acceptance.write_text('{"synthetic_test_only":true}', encoding="utf-8")
    output = tmp_path / "exports/pilot.zip"
    result = build_pilot_bundle(tmp_path, output)
    first_bytes = output.read_bytes()
    assert result["n_rows"] == 1
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert "vlmbench-pilot/BUNDLE_CONTENTS.json" in names
        assert "vlmbench-pilot/HUONG_DAN_NHOM.md" in names
        assert "vlmbench-pilot/synthetic_test_only.png" in names
        assert "vlmbench-pilot/src/vlmbench/label_qa_template.html" in names
        assert "vlmbench-pilot/data/dictionaries/synthetic_draft.json" in names
        assert not any(".env" in name or "safetensors" in name for name in names)
        assert not any(b"synthetic_secret_token" in archive.read(name) for name in names)
    build_pilot_bundle(tmp_path, output)
    assert output.read_bytes() == first_bytes
    (tmp_path / "README.md").write_text("synthetic_test_only_changed",encoding="utf-8")
    with pytest.raises(ValueError,match="new output version"):
        build_pilot_bundle(tmp_path,output)
    assert output.read_bytes()==first_bytes


def test_notebook_cells_are_valid_python_have_ids_and_no_stored_outputs():
    root = Path(__file__).resolve().parents[1]
    for platform in ("colab", "kaggle"):
        notebook = json.loads((root / f"notebooks/pilot_{platform}.ipynb").read_text(encoding="utf-8"))
        assert len({cell["id"] for cell in notebook["cells"]}) == len(notebook["cells"])
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))
                assert cell["outputs"] == [] and cell["execution_count"] is None
