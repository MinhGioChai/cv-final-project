"""Metadata candidates are not image-verified or language-approved manifests."""
import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt, model_validator

from ..reviews import canonical_hash


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sample_id: str
    source_dataset: str
    source_split: str
    source_revision: str
    source_row_id: str
    source_record_sha256: str
    image_namespace: str
    image_id: str
    source_image_ref: str
    task: Literal["object_existence", "spatial", "counting", "fine_grained"]
    category: str
    question_en: str
    ground_truth: str | StrictInt
    metadata: dict
    stage: Literal["metadata_candidate_not_main_manifest"] = "metadata_candidate_not_main_manifest"

    @model_validator(mode="after")
    def check(self):
        if any(not getattr(self, k).strip() for k in ("sample_id", "source_dataset", "source_split",
               "source_revision", "source_row_id", "image_id", "source_image_ref", "question_en", "category")):
            raise ValueError("Candidate identity/content cannot be empty")
        if self.task in {"object_existence", "spatial"} and self.ground_truth not in {"yes", "no"}:
            raise ValueError("Binary candidate label must be yes/no")
        if self.task == "counting" and (type(self.ground_truth) is not int or self.ground_truth < 0):
            raise ValueError("Count must be a nonnegative source integer")
        if self.task == "fine_grained" and self.ground_truth not in tuple("ABCDEFGH"):
            raise ValueError("Pet subset labels must be A–H")
        return self


def candidate(*, dataset, split, revision, row_id, record, namespace, image_id, image_ref,
              task, category, question, truth, metadata=None):
    identity = f"{dataset}|{revision}|{split}|{row_id}"
    return Candidate(sample_id=f"{dataset}_" + hashlib.sha256(identity.encode()).hexdigest()[:16],
                     source_dataset=dataset, source_split=split, source_revision=revision,
                     source_row_id=str(row_id), source_record_sha256=canonical_hash(record),
                     image_namespace=namespace, image_id=image_id, source_image_ref=image_ref,
                     task=task, category=category, question_en=question, ground_truth=truth,
                     metadata=metadata or {})


def ensure_unique(rows):
    if not rows or len({r.sample_id for r in rows}) != len(rows):
        raise ValueError("Empty or duplicate source candidate IDs")
    return rows
