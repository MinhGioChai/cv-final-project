"""Conservative full-answer parser. Never infer a label from a long explanation."""

from dataclasses import dataclass
import re
import unicodedata
from typing import Literal

from .schemas import Task


@dataclass(frozen=True)
class ParseResult:
    prediction: str | int | None
    status: Literal["valid", "invalid"]
    reason: str
    used_alias: bool = False


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).strip().casefold()
    # Only strip boundary punctuation. Internal words/signs are never removed.
    return text.strip(" \t\r\n.!?。！？，,:;\"'“”‘’`*()[]{}")


def parse_response(raw: str | None, task: Task, *, max_count: int | None = None) -> ParseResult:
    if raw is None or not isinstance(raw, str) or not raw.strip():
        return ParseResult(None, "invalid", "INVALID_EMPTY")
    text = _clean(raw)
    if task in {"object_existence", "spatial", "negation"}:
        mapping = {"yes": "yes", "no": "no", "true": "yes", "false": "no", "có": "yes", "không": "no"}
        if text in mapping:
            return ParseResult(mapping[text], "valid", "OK", text not in {"yes", "no"})
        tokens = set(re.findall(r"\w+", text))
        if tokens.intersection({"yes", "true", "có"}) and tokens.intersection({"no", "false", "không"}):
            return ParseResult(None, "invalid", "INVALID_AMBIGUOUS")
        return ParseResult(None, "invalid", "INVALID_FORMAT")
    if task == "counting":
        if re.fullmatch(r"[0-9]+", text) and len(text) <= 9:
            value = int(text)
            if max_count is None or value <= max_count:
                return ParseResult(value, "valid", "OK")
            return ParseResult(None, "invalid", "INVALID_RANGE")
        return ParseResult(None, "invalid", "INVALID_FORMAT")
    if task == "fine_grained":
        if text in tuple("abcdefgh"):
            return ParseResult(text.upper(), "valid", "OK")
        return ParseResult(None, "invalid", "INVALID_FORMAT")
    raise ValueError(f"Unsupported task: {task}")
