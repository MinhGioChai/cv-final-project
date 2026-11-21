"""Reuse the pinned, corrected upstream RePOPE annotations as a complete frame."""
from .candidates import candidate, ensure_unique
from ..source_audit import parse_annotations


def parse_repope_frame(content: dict[str, bytes], *, revision: str):
    rows = []
    for (category, image_id, question), records in parse_annotations(content).items():
        for record in records:
            rows.append(candidate(dataset="repope", split="annotations", revision=revision,
                row_id=f"{category}:{record['question_id']}", record=record, namespace="coco",
                image_id=image_id, image_ref=record["image"], task="object_existence",
                category=category, question=question, truth=record["label"],
                metadata={"upstream_category": category, "upstream_question_id": record["question_id"],
                          "ground_truth_source": "pinned_corrected_repope_upstream"}))
    return ensure_unique(rows)
