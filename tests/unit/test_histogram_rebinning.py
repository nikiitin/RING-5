"""Histogram selection, interval allocation and overflow regression contracts."""

import pytest

from src.parsing.gem5.types.histogram import Histogram


def test_histogram_selection_priority() -> None:
    """Explicit entry selection overrides configured rebinning."""
    hist = Histogram(entries=["mean"], bins=10, max_range=1000)
    hist.add_observation({"0-99": 100, "mean": 50})
    hist.balance_content()
    hist.reduce_duplicates()
    assert hist.entries == ["mean"]
    assert hist.reduced_content == {"0-99": 100.0, "mean": 50.0}


def test_histogram_rebinning_with_summary_stats() -> None:
    """Rebinning preserves non-range summary measurements."""
    hist = Histogram(bins=3, max_range=100)
    hist.add_observation({"0-99": 100, "mean": 50})
    hist.balance_content()
    hist.reduce_duplicates()
    assert hist.reduced_content == {"0-49": 50.0, "50-99": 50.0, "100+": 0.0, "mean": 50.0}


def test_histogram_rebinning_fallback_to_raw() -> None:
    """Unconfigured rebinning retains the simulator's raw interval labels."""
    hist = Histogram()
    hist.add_observation({"0-9": 10, "10-19": 20})
    hist.balance_content()
    hist.reduce_duplicates()
    assert hist.entries == ["0-9", "10-19"]
    assert hist.reduced_content == {"0-9": 10.0, "10-19": 20.0}


def test_histogram_rebinning_exact_values() -> None:
    """Inclusive raw bucket widths determine proportional frequency allocation."""
    # [test->req~ring5.ingestion.histogram-rebinning~1]
    hist = Histogram(bins=3, max_range=200)
    hist.add_observation({"0-149": 150})
    hist.balance_content()
    hist.reduce_duplicates()
    assert hist.entries == ["0-99", "100-199", "200+"]
    assert hist.reduced_content == pytest.approx({"0-99": 100, "100-199": 50, "200+": 0})


def test_histogram_rebinning_overflow() -> None:
    """All frequency at or above max_range reaches the overflow bucket."""
    hist = Histogram(bins=2, max_range=100)
    hist.add_observation({"150-199": 10, "90-109": 20})
    hist.balance_content()
    hist.reduce_duplicates()
    assert hist.reduced_content == pytest.approx({"0-99": 10, "100+": 20})
