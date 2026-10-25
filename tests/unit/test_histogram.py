"""Histogram construction and missing-summary reduction contracts."""

import math

import pytest

from src.parsing.gem5.types.histogram import Histogram


def test_histogram_creation() -> None:
    histogram = Histogram(repeat=1, statistics=["samples"])
    assert histogram.repeat == 1
    assert histogram.content == {"samples": []}


def test_histogram_entries_merging() -> None:
    histogram = Histogram(bins=3, max_range=10.0, statistics=["samples"])
    assert histogram.entries == ["0-4", "5-9", "10+", "samples"]


def test_histogram_content_setting() -> None:
    histogram = Histogram(statistics=["samples"])
    histogram.add_observation({"0-9": 5.0, "samples": 100.0})
    assert histogram.content == {"0-9": [5.0], "samples": [100.0]}


def test_histogram_balance_with_missing_stats() -> None:
    histogram = Histogram(repeat=2, statistics=["samples"])
    histogram.add_observation({"0-9": 10})
    histogram.add_observation({"0-9": 20})
    histogram.balance_content()
    assert all(math.isnan(value) for value in histogram.content["samples"])
    assert histogram.content["0-9"] == [10.0, 20.0]


def test_histogram_balance_and_reduce() -> None:
    histogram = Histogram(repeat=2, statistics=["samples"])
    histogram.add_observation({"0-9": 10, "samples": 100})
    histogram.add_observation({"0-9": 20})
    histogram.balance_content()
    assert histogram.content["samples"][0] == 100.0
    assert math.isnan(histogram.content["samples"][1])
    histogram.reduce_duplicates()
    assert histogram.reduced_content["0-9"] == 15.0
    assert math.isnan(histogram.reduced_content["samples"])


def test_histogram_explicit_zero_summaries_remain_measured_zero() -> None:
    histogram = Histogram(repeat=2, statistics=["samples"])
    for _ in range(2):
        histogram.add_observation({"0-9": 0, "samples": 0})
    histogram.balance_content()
    histogram.reduce_duplicates()
    assert histogram.reduced_content == {"0-9": 0.0, "samples": 0.0}


def test_histogram_invalid_value() -> None:
    with pytest.raises(TypeError):
        Histogram().add_observation({"0-9": ["invalid"]})
