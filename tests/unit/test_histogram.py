import pytest

from src.parsers.types.histogram import Histogram


def test_histogram_creation():
    # Verify pre-initialization with statistics
    h = Histogram(repeat=1, statistics=["samples"])
    assert h._repeat == 1
    # _content should be pre-initialized with statistical buckets
    assert "samples" in h.content
    assert h.content["samples"] == []


def test_histogram_entries_merging():
    # Verify that entries merges buckets and statistics correctly
    h = Histogram(repeat=1, bins=2, max_range=10.0, statistics=["samples"])
    entries = h.entries
    assert "samples" in entries
    assert "0-5" in entries
    assert "5-10" in entries


def test_histogram_content_setting():
    h = Histogram(repeat=1, statistics=["samples"])
    # Mock data from parser: dict of range string -> values
    data = {"0-10": ["5"], "samples": ["100"]}
    h.content = data

    assert h.content["0-10"] == [5.0]
    assert h.content["samples"] == [100.0]


def test_histogram_balance_with_missing_stats():
    # Verify that balance_content pads missing statistics
    h = Histogram(repeat=2, statistics=["samples"])
    h.content = {"0-10": ["10", "20"]}  # samples is missing

    h.balance_content()
    assert "samples" in h.content
    assert h.content["samples"] == [0.0, 0.0]


def test_histogram_balance_and_reduce():
    h = Histogram(repeat=2, statistics=["samples"])
    h.content = {"0-10": ["10", "20"], "samples": ["100"]}

    h.balance_content()
    assert h.content["samples"] == [100.0, 0.0]

    h.reduce_duplicates()
    reduced = h.reduced_content

    assert reduced["0-10"] == 15.0  # (10+20)/2
    assert reduced["samples"] == 50.0  # (100+0)/2


def test_histogram_invalid_value():
    h = Histogram()
    with pytest.raises(TypeError):
        h.content = {"0-10": ["invalid"]}
