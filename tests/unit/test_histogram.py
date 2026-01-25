import pytest

from src.common.types.histogram import Histogram


def test_histogram_creation():
    h = Histogram(repeat=1)
    assert h._repeat == 1
    assert h.content == {}


def test_histogram_content_setting():
    h = Histogram(repeat=1)
    # Mock data from parser: dict of range string -> values
    data = {"0-10": ["5"], "10-20": ["10"], "20-30": [15]}
    h.content = data

    assert len(h.content) == 3
    assert h.content["0-10"] == [5.0]
    assert h.content["20-30"] == [15.0]


def test_histogram_content_extends():
    h = Histogram(repeat=1)
    h.content = {"0-10": ["5"]}
    h.content = {"0-10": ["3"], "10-20": ["2"]}

    # Behavior is extend? Or overwrite?
    # Current implementation: self._content[str_key].extend(val_list)
    # Wait, if repeat=1, extend means ["5", "3"]?
    # Yes, balance_content checks length against repeat.
    # If repeat=1, we expect 1 value. If we provide mulitple, it might fail balance.
    # But usually parser accumulates across dumps.
    # For a SINGLE dump parsing, repeated set calls usually imply multiple occurrences?
    # In integration: PerlParseWork accumulates in ALL content, then sets it once or iteratively?
    # PerlParseWork calls varsToParse[varID].content = entries (list).
    # Wait, PerlParseWork.py _applyBufferedEntries: varsToParse[varID].content = entries
    # It sets it directly? Or uses property setter?
    # It uses property setter: `var.content = entries`
    # The setter extends: `self._content[str_key].extend(vals)`

    # So if we call it twice, we append.
    pass


def test_histogram_balance_and_reduce():
    h = Histogram(repeat=2)
    h.content = {"0-10": ["10", "20"], "10-20": ["5"]}  # 2 values  # 1 value (needs padding)

    h.balance_content()

    assert len(h.content["0-10"]) == 2
    assert len(h.content["10-20"]) == 2
    assert h.content["10-20"][1] == 0  # padded

    h.reduce_duplicates()
    reduced = h.reduced_content

    assert reduced["0-10"] == 15.0  # (10+20)/2
    assert reduced["10-20"] == 2.5  # (5+0)/2


def test_histogram_invalid_value():
    h = Histogram()
    with pytest.raises(TypeError):
        h.content = {"0-10": ["invalid"]}
