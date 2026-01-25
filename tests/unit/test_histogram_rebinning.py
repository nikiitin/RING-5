import pytest

from src.parsers.types.histogram import Histogram


def test_histogram_selection_priority():
    """Verify that explicit entry selection overrides rebinning even if configured."""
    # User selected only 'mean', but also configured 10 bins
    hist = Histogram(repeat=1, entries=["mean"], bins=10, max_range=1000)

    hist.content = {"0-100": [100], "mean": [50]}
    hist.balance_content()
    hist.reduce_duplicates()

    # Entries should return ONLY the selection
    assert hist.entries == ["mean"]
    assert hist.reduced_content["mean"] == 50.0
    # Rebinned buckets should be in reduced_content but not in entries
    assert "0-100" in hist.reduced_content


def test_histogram_rebinning_with_summary_stats():
    """Verify that rebinning preserves non-range statistics in reduced_content."""
    hist = Histogram(repeat=1, bins=2, max_range=100)

    # Raw data has a bucket and a summary stat
    hist.content = {"0-100": [100], "mean": [50]}
    hist.balance_content()
    hist.reduce_duplicates()

    # Rebinned buckets should exist
    assert hist.reduced_content["0-50"] == 50.0
    assert hist.reduced_content["50-100"] == 50.0
    # Summary stat should be preserved
    assert hist.reduced_content["mean"] == 50.0


def test_histogram_rebinning_fallback_to_raw():
    """Verify fallback to raw buckets when no rebinning or selection is provided."""
    hist = Histogram(repeat=1)  # bins=0, entries=None

    hist.content = {"0-10": [10], "10-20": [20]}
    hist.balance_content()
    hist.reduce_duplicates()

    assert sorted(hist.entries) == ["0-10", "10-20"]
    assert hist.reduced_content["0-10"] == 10.0


def test_histogram_rebinning_exact_values():
    """Regression test for the user's specific case: max_range=2048, bins=10."""
    hist = Histogram(repeat=1, bins=10, max_range=2048)
    bin_width = 204.8

    # Add a raw bucket that overlaps with multiple target bins
    # 0-512 has 512 units.
    # Target bins are: [0-204], [204-409], [409-614]...
    hist.content = {"0-512": [512]}
    hist.balance_content()
    hist.reduce_duplicates()

    # Expected buckets
    expected_keys = [f"{int(b*bin_width)}-{int((b+1)*bin_width)}" for b in range(10)]
    assert hist.entries == expected_keys

    # Check first target bin [0-204]: overlap with [0-512] is 204.8 units -> 204.8 value
    assert hist.reduced_content[expected_keys[0]] == 204.8
    # Third target bin [409-614]: overlap with [0-512] is [409.6 - 512] = 102.4 units
    assert pytest.approx(hist.reduced_content[expected_keys[2]]) == 102.4
