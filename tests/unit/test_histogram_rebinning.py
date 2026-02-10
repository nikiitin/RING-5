import pytest

from src.core.parsing.gem5.types.histogram import Histogram


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
    # 0-100 overlaps with first bin (0-111 using new logic if bins=10 -> 9 std bins)
    # Just check key existence
    list(hist.content.keys())
    # Rebinned keys are not in 'content' (raw), but computed in 'reduced_content'
    # Check that a rebinned key exists. For 1000/9 ~ 111. Key "0-111"
    assert "0-111" in hist.reduced_content


def test_histogram_rebinning_with_summary_stats():
    """Verify that rebinning preserves non-range statistics in reduced_content."""
    # bins=3, max=100.
    # Regular bins: 2 (0-50, 50-100). Overflow: 1 (100+)
    hist = Histogram(repeat=1, bins=3, max_range=100)

    # Raw data has a bucket and a summary stat
    hist.content = {"0-100": [100], "mean": [50]}
    hist.balance_content()
    hist.reduce_duplicates()

    # Rebinned buckets should exist
    assert hist.reduced_content["0-50"] == 50.0
    # Overlap 50-100 (50 units)
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
    """Regression test for rebinning distribution logic."""
    # bins=3. max=200.
    # Regular=2. Width=100. Keys: 0-100, 100-200, 200+
    hist = Histogram(repeat=1, bins=3, max_range=200)

    # Add a raw bucket 0-150 with value 150
    # Should split: 100 to 0-100, 50 to 100-200.
    hist.content = {"0-150": [150]}
    hist.balance_content()
    hist.reduce_duplicates()

    expected_buckets = ["0-100", "100-200", "200+"]
    assert hist.entries == expected_buckets

    assert pytest.approx(hist.reduced_content["0-100"]) == 100.0
    assert pytest.approx(hist.reduced_content["100-200"]) == 50.0
    assert pytest.approx(hist.reduced_content["200+"]) == 0.0


def test_histogram_rebinning_overflow():
    """Verify that values above max_range are added to the dedicated overflow bucket."""
    # Max range 100, 2 bins.
    # Logic: 1 regular bin (0-100), 1 overflow bin (100+)
    hist = Histogram(repeat=1, bins=2, max_range=100)

    # Bucket 150-200 (val 10): Entirely overflow -> 100+
    # Bucket 90-110 (val 20): Overlap 90-100 (10 units) -> 0-100. Overflow 100-110 (10 units) -> 100+  # noqa: E501

    hist.content = {"150-200": [10], "90-110": [20]}
    hist.balance_content()
    hist.reduce_duplicates()

    # Checks
    # 0-100 should contain 10 (from 90-110)
    assert "0-100" in hist.reduced_content
    # The first bin (0-100) got exactly 10 units from 90-110 (50% of 20)
    assert pytest.approx(hist.reduced_content["0-100"]) == 10.0

    # 100+ should contain 10 (from 150-200) + 10 (from 90-110) = 20
    overflow_key = "100+"
    assert overflow_key in hist.reduced_content
    assert pytest.approx(hist.reduced_content[overflow_key]) == 20.0
