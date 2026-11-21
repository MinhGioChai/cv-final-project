import unicodedata

import pytest

from vlmbench.parse import parse_response


@pytest.mark.parametrize("raw,expected,alias", [
    ("YES", "yes", False), (" no. ", "no", False), ("**YES**", "yes", False),
    ("“True”", "yes", True), ("FALSE", "no", True),
    ("Có!", "yes", True), ("KHÔNG", "no", True),
    (unicodedata.normalize("NFD", "không"), "no", True),
])
def test_binary_normalization(raw, expected, alias):
    result = parse_response(raw, "object_existence")
    assert (result.prediction, result.status, result.used_alias) == (expected, "valid", alias)


@pytest.mark.parametrize("raw", [None, "", "...", "yes and no", "Có, nhưng không rõ", "not yes", "There is a dog", "No dog is visible", "yes/no"])
def test_no_guessing_from_ambiguous_or_long_answers(raw):
    result = parse_response(raw, "object_existence")
    assert result.status == "invalid"
    assert result.prediction is None


def test_ambiguous_reason():
    assert parse_response("YES, no", "object_existence").reason == "INVALID_AMBIGUOUS"


@pytest.mark.parametrize("task", ["negation", "spatial"])
def test_truth_labels_are_not_inverted_for_negative_statements(task):
    assert parse_response("NO", task).prediction == "no"
    assert parse_response("YES", task).prediction == "yes"


@pytest.mark.parametrize("raw,expected", [("0", 0), ("12.", 12), (" 003 ", 3)])
def test_counting(raw, expected):
    assert parse_response(raw, "counting").prediction == expected


@pytest.mark.parametrize("raw", ["-1", "3.5", "3 dogs", "There are 2 or 3", "2 3", "one", "1e3", "１２"])
def test_counting_rejects_explanations_and_nonintegers(raw):
    assert parse_response(raw, "counting").status == "invalid"


def test_counting_optional_task_range():
    assert parse_response("11", "counting", max_count=10).reason == "INVALID_RANGE"


@pytest.mark.parametrize("raw,expected", [("A", "A"), (" h. ", "H"), ("(c)", "C"), ("breed A", None), ("0", None), ("I", None)])
def test_fixed_breed_candidate_ids(raw, expected):
    assert parse_response(raw, "fine_grained").prediction == expected
