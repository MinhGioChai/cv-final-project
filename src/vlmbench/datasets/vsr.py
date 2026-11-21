"""Pinned official VSR JSONL -> auditable metadata candidates."""
import json
import re
from urllib.parse import urlsplit

from .candidates import candidate, ensure_unique


def parse_vsr(payload: bytes, *, revision: str, variant: str = "random"):
    if variant not in {"random", "zeroshot"}:
        raise ValueError("Choose one VSR variant explicitly")
    rows = []
    for line, text in enumerate(payload.decode("utf-8-sig").splitlines(), 1):
        if not text.strip():continue
        record = json.loads(text)
        match = re.fullmatch(r"([0-9]{12})\.jpg", record["image"])
        url = urlsplit(record["image_link"])
        if (not match or type(record["label"]) is not int or record["label"] not in {0, 1}
                or url.hostname != "images.cocodataset.org" or url.path.split("/")[-1] != record["image"]
                or not isinstance(record["caption"], str) or not isinstance(record["relation"], str)):
            raise ValueError(f"Unexpected VSR record at line {line}")
        rows.append(candidate(dataset="vsr", split=f"{variant}/test", revision=revision,
            row_id=str(line), record=record, namespace="coco", image_id=match.group(1),
            image_ref=record["image_link"], task="spatial", category=record["relation"],
            question=record["caption"], truth="yes" if record["label"] == 1 else "no",
            metadata={"original_label": record["label"], "original_caption": record["caption"],
                      "relation": record["relation"], "external_answer_labels": ["TRUE", "FALSE"],
                      "label_mapping": {"1": "yes/TRUE", "0": "no/FALSE"}}))
    return ensure_unique(rows)
