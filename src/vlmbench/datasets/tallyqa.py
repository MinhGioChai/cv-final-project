"""Official TallyQA test JSON, preserving VG image identity and source counts."""
import json
import re

from .candidates import candidate, ensure_unique


def parse_tallyqa(payload: bytes, *, revision: str):
    records = json.loads(payload)
    if not isinstance(records, list):raise ValueError("TallyQA test must be a JSON array")
    rows = []
    for record in records:
        match = re.fullmatch(r"VG_100K(?:_2)?/([1-9][0-9]*)\.jpg", record["image"])
        if (not match or type(record["answer"]) is not int or record["answer"] < 0
                or type(record["issimple"]) is not bool or type(record["question_id"]) is not int
                or type(record["image_id"]) is not int or not isinstance(record["question"], str)):
            raise ValueError("Unexpected TallyQA test record/image reference")
        rows.append(candidate(dataset="tallyqa", split="test", revision=revision,
            row_id=str(record["question_id"]), record=record, namespace="visual_genome",
            image_id=match.group(1), image_ref=record["image"], task="counting",
            category="simple" if record["issimple"] else "complex", question=record["question"],
            truth=record["answer"], metadata={"original_answer": record["answer"],
                "original_image_id": record["image_id"], "data_source": record["data_source"],
                "issimple": record["issimple"]}))
    return ensure_unique(rows)
