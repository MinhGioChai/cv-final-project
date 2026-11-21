from pathlib import Path

from PIL import Image
import pytest

from vlmbench.io_utils import sha256_file
from vlmbench.schemas import ManifestRow


@pytest.fixture
def row_factory(tmp_path):
    """synthetic_test_only — no real labels or benchmark predictions."""
    def make(**changes):
        path = tmp_path / "synthetic_test_only.png"
        if not path.exists():
            Image.new("RGB", (8, 6), color="blue").save(path)
        data = dict(
            sample_id="synthetic_test_only_1", source_dataset="repope", source_split="train",
            source_row_id="random:0", image_id="000000000001", image_path=path.name,
            image_sha256=sha256_file(path), task="object_existence", category="random",
            question_en="Is there a dog in the image?", question_vi="",
            ground_truth="yes", ground_truth_source="synthetic_test_only",
            qa_status="pending", translation_status="missing", is_pilot=True,
            sampling_seed=42, metadata={"synthetic_test_only": True, "image_namespace": "coco"},
        )
        data.update(changes)
        return ManifestRow(**data)
    return make
