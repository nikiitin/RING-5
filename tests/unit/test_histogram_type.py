"""
Comprehensive tests for Histogram stat type.

Tests cover:
- Initialization (default, with entries, with rebinning params, statistics)
- Properties (entries with different priority levels, content)
- Content validation (dict structure, numeric values)
- Content setting (aggregation, dynamic bucket discovery)
- balance_content (padding per bucket, overflow detection)
- reduce_duplicates (mean calculation, rebinning mode)
- Rebinning logic (_rebin_simulation_data, range parsing)
- reduced_content property guards
- Type registration
- Edge cases (various range formats, overflow handling)
- __str__ method
"""

import math
from typing import Any, cast

import pytest

from src.parsing.gem5.types.base import StatTypeRegistry
from src.parsing.gem5.types.histogram import Histogram


class TestHistogramInitialization:
    """Test Histogram object creation and initialization."""

    def test_required_params_empty(self) -> None:
        required = Histogram.required_params

        assert required == []

    def test_init_with_defaults(self) -> None:
        hist = Histogram()

        assert hist._repeat == 1
        assert hist._bins == 0
        assert hist._max_range == 0.0
        assert object.__getattribute__(hist, "_entries") == ()
        assert hist._statistics == ()
        assert hist.content == {}

    def test_init_with_custom_repeat(self) -> None:
        hist = Histogram(repeat=5)

        assert hist._repeat == 5

    def test_init_with_explicit_entries(self) -> None:
        hist = Histogram(entries=["0-10", "10-20", "20-30"])

        assert hist.entries == ["0-10", "10-20", "20-30"]

    def test_init_with_rebinning_params(self) -> None:
        hist = Histogram(bins=10, max_range=100.0)

        assert hist._bins == 10
        assert hist._max_range == 100.0

    def test_init_with_statistics(self) -> None:
        hist = Histogram(statistics=["mean", "total"])

        assert hist._statistics == ("mean", "total")
        # Statistics pre-initialized in content
        assert "mean" in hist.content
        assert "total" in hist.content

    def test_string_statistics_schema_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="list of text entry names"):
            Histogram(statistics="mean, total, samples")


class TestHistogramEntriesProperty:
    """Test entries property with priority ordering."""

    def test_entries_priority_1_explicit_entries(self) -> None:
        hist = Histogram(entries=["0-10", "10-20"], bins=5, max_range=50.0)

        result = hist.entries

        assert result == ["0-10", "10-20"]

    def test_entries_priority_2_rebinning_with_overflow(self) -> None:
        hist = Histogram(bins=3, max_range=30.0)

        result = hist.entries

        # bin_width = 30 / (3-1) = 15
        assert result is not None
        assert "0-14" in result
        assert "15-29" in result
        assert "30+" in result
        assert len(result) == 3

    def test_entries_priority_2_rebinning_single_bin(self) -> None:
        hist = Histogram(bins=1, max_range=10.0)

        result = hist.entries

        assert result is not None
        assert "0+" in result
        assert len(result) == 1

    def test_entries_priority_3_discovered_buckets(self) -> None:
        hist = Histogram()
        hist.add_observation({"0-10": 5, "10-20": 10, "20-30": 3})

        result = hist.entries

        assert result is not None
        assert "0-10" in result
        assert "10-20" in result
        assert "20-30" in result

    def test_entries_includes_statistics(self) -> None:
        hist = Histogram(statistics=["mean", "samples"])
        hist.add_observation({"0-10": 5})

        result = hist.entries

        assert result is not None
        assert "mean" in result
        assert "samples" in result


class TestHistogramContentProperty:
    """Test defensive content snapshots and typed observation ingestion."""

    def test_content_getter(self) -> None:
        hist = Histogram()

        result = hist.content

        assert isinstance(result, dict)

    def test_add_observation_non_dict_raises(self) -> None:
        hist = Histogram()

        with pytest.raises(TypeError, match="HISTOGRAM.*numeric entry mapping"):
            hist.add_observation(cast(Any, [1, 2, 3]))

    def test_add_observation_non_numeric_values_raises(self) -> None:
        hist = Histogram()

        with pytest.raises(TypeError, match="one numeric measurement"):
            hist.add_observation({"0-10": ["invalid"]})


class TestHistogramContentSetting:
    """Test complete numeric observation frames."""

    def test_add_observation_with_single_values(self) -> None:
        hist = Histogram()

        hist.add_observation({"0-10": 5, "10-20": 10})

        assert hist.content["0-10"] == [5.0]
        assert hist.content["10-20"] == [10.0]

    def test_numeric_frame_values_are_retained(self) -> None:
        hist = Histogram()

        hist.add_observation({"0-10": 30.0})

        assert hist.content["0-10"] == [30.0]

    def test_add_observation_multiple_assignments_extend(self) -> None:
        hist = Histogram()

        hist.add_observation({"0-10": 5})
        hist.add_observation({"0-10": 10})

        assert hist.content["0-10"] == [5.0, 10.0]

    def test_add_observation_dynamic_bucket_discovery(self) -> None:
        hist = Histogram()

        hist.add_observation({"0-100": 10})
        hist.add_observation({"100-200": 20})

        assert "0-100" in hist.content
        assert "100-200" in hist.content

    def test_add_observation_with_statistics(self) -> None:
        hist = Histogram(statistics=["mean"])

        hist.add_observation({"0-10": 5, "mean": 7.5})

        assert hist.content["mean"] == [7.5]


class TestHistogramBalanceContent:
    """Test logical missing measurements while retaining actual frames."""

    def test_balance_missing_observations_records_logical_count(self) -> None:
        hist = Histogram(repeat=3)
        hist.add_observation({"0-10": 5})
        # 0-10 has 1 value, needs 2 more

        hist.balance_content()

        assert hist.is_balanced is True
        assert hist.content == {"0-10": [5.0]}
        assert hist.padded_count == hist.missing_measurement_count == 2
        hist.reduce_duplicates()
        assert math.isnan(hist.reduced_content["0-10"])

    def test_balance_partial_buckets_retains_actual_frames(self) -> None:
        hist = Histogram(repeat=4)
        hist.add_observation({"0-10": 10})
        hist.add_observation({"0-10": 20})

        hist.balance_content()

        assert hist.content == {"0-10": [10.0, 20.0]}
        assert hist.padded_count == hist.missing_measurement_count == 2
        hist.reduce_duplicates()
        assert math.isnan(hist.reduced_content["0-10"])

    def test_balance_exact_count_no_change(self) -> None:
        hist = Histogram(repeat=2)
        hist.add_observation({"0-10": 5})
        hist.add_observation({"0-10": 10})

        hist.balance_content()

        assert hist.content["0-10"] == [5.0, 10.0]

    def test_balance_too_many_values_raises(self) -> None:
        hist = Histogram(repeat=1)
        hist.add_observation({"0-10": 5})
        hist.add_observation({"0-10": 10})

        with pytest.raises(RuntimeError, match="More observations.*than expected"):
            hist.balance_content()

    def test_balance_initializes_missing_statistics(self) -> None:
        hist = Histogram(repeat=2, statistics=["mean"])
        hist.add_observation({"0-10": 5})
        # mean not provided

        hist.balance_content()

        assert len(hist.content["mean"]) == 1
        assert math.isnan(hist.content["mean"][0])
        assert hist.padded_count == hist.missing_measurement_count == 3
        hist.reduce_duplicates()
        assert math.isnan(hist.reduced_content["mean"])


class TestHistogramReduceDuplicates:
    """Test reduce_duplicates method (mean calculation)."""

    # [test->req~ring5.ingestion.histogram~1]

    def test_reduce_single_value_per_bucket(self) -> None:
        hist = Histogram()
        hist.add_observation({"0-10": 100, "10-20": 200})
        hist.balance_content()

        hist.reduce_duplicates()

        assert hist.is_reduced is True
        assert hist.reduced_content["0-10"] == 100.0
        assert hist.reduced_content["10-20"] == 200.0

    def test_reduce_multiple_values_calculates_mean(self) -> None:
        hist = Histogram(repeat=3)
        for value in (1, 2, 3):
            hist.add_observation({"0-10": value * 10, "10-20": value * 100})
        hist.balance_content()

        hist.reduce_duplicates()

        assert hist.reduced_content["0-10"] == 20.0
        assert hist.reduced_content["10-20"] == 200.0

    def test_reduce_empty_bucket_returns_zero(self) -> None:
        hist = Histogram()
        hist.balance_content()  # All empty

        hist.reduce_duplicates()

        assert len(hist.reduced_content) == 0  # No buckets


class TestHistogramRebinning:
    """Test rebinning logic."""

    def test_reduce_with_rebinning_enabled(self) -> None:
        hist = Histogram(repeat=1, bins=2, max_range=20.0)
        # Provide raw data: 0-10 has 5, 10-20 has 10
        hist.add_observation({"0-9": 5, "10-19": 10})
        hist.balance_content()

        hist.reduce_duplicates()

        # bins=2 means 1 standard bin + 1 overflow: bin_width=20/(2-1)=20
        assert "0-19" in hist.reduced_content
        assert "20+" in hist.reduced_content

    def test_rebinning_proportional_distribution(self) -> None:
        hist = Histogram(repeat=1, bins=3, max_range=30.0)
        # bin_width = 30/(3-1) = 15
        # Target buckets: 0-15, 15-30, 30+
        # Raw bucket 0-30 has value 30
        hist.add_observation({"0-29": 30})
        hist.balance_content()

        hist.reduce_duplicates()

        # 0-15 gets 15/30 * 30 = 15
        # 15-30 gets 15/30 * 30 = 15
        assert hist.reduced_content["0-14"] == 15.0
        assert hist.reduced_content["15-29"] == 15.0

    def test_rebinning_overflow_bucket(self) -> None:
        hist = Histogram(repeat=1, bins=2, max_range=10.0)
        # bin_width = 10/(2-1) = 10
        # Target: 0-10, 10+
        # Raw: 0-20 with value 20
        hist.add_observation({"0-19": 20})
        hist.balance_content()

        hist.reduce_duplicates()

        assert hist.reduced_content["0-9"] == 10.0
        assert hist.reduced_content["10+"] == 10.0

    def test_rebinning_preserves_summary_stats(self) -> None:
        hist = Histogram(repeat=1, bins=2, max_range=10.0, statistics=["mean"])
        hist.add_observation({"0-9": 5, "mean": 7.5})
        hist.balance_content()

        hist.reduce_duplicates()

        assert hist.reduced_content["mean"] == 7.5

    def test_rebinning_single_bin_no_overflow(self) -> None:
        hist = Histogram(repeat=1, bins=1, max_range=10.0)
        hist.add_observation({"0-19": 20})
        hist.balance_content()

        hist.reduce_duplicates()

        assert hist.reduced_content == {"0+": 20.0}


class TestHistogramRangeParser:
    """Test _parse_range_key helper method."""

    # [test->req~ring5.ingestion.histogram~1]

    def test_parse_range_key_valid(self) -> None:
        hist = Histogram()

        result = hist._parse_range_key("0-1023")

        assert result == [0.0, 1023.0]

    def test_parse_range_key_multi_digit(self) -> None:
        hist = Histogram()

        result = hist._parse_range_key("128-255")

        assert result == [128.0, 255.0]

    def test_parse_range_key_invalid(self) -> None:
        hist = Histogram()

        result = hist._parse_range_key("total")

        assert result == []

    def test_parse_range_key_overflow_format(self) -> None:
        hist = Histogram()

        result = hist._parse_range_key("1024+")

        assert result == []


class TestHistogramReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        hist = Histogram()
        hist.add_observation({"0-10": 5})
        # Don't call balance_content()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = hist.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        hist = Histogram()
        hist.add_observation({"0-10": 5})
        hist.balance_content()
        # Don't call reduce_duplicates()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = hist.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        hist = Histogram()
        hist.add_observation({"0-10": 50})
        hist.balance_content()
        hist.reduce_duplicates()

        result = hist.reduced_content

        assert isinstance(result, dict)
        assert result["0-10"] == 50.0


class TestHistogramTypeRegistration:
    """Test Histogram is properly registered in the type system."""

    def test_histogram_registered_with_decorator(self) -> None:
        registered_types = StatTypeRegistry.get_types()

        assert "histogram" in registered_types

    def test_create_histogram_via_registry(self) -> None:
        hist = StatTypeRegistry.create("histogram", bins=5, max_range=100.0)

        assert isinstance(hist, Histogram)
        assert hist._bins == 5
        assert hist._max_range == 100.0


class TestHistogramStrMethod:
    """Test __str__ method for string representation."""

    def test_str_method_empty_histogram(self) -> None:
        hist = Histogram(repeat=3)

        result = str(hist)

        assert "Histogram" in result
        assert "buckets=0" in result
        assert "repeat=3" in result

    def test_str_method_with_buckets(self) -> None:
        hist = Histogram()
        hist.add_observation({"0-10": 5, "10-20": 10})

        result = str(hist)

        assert "Histogram" in result
        assert "buckets=2" in result


class TestHistogramEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero_value_buckets(self) -> None:
        hist = Histogram()

        hist.add_observation({"0-10": 0})
        hist.balance_content()
        hist.reduce_duplicates()

        assert hist.reduced_content["0-10"] == 0.0

    def test_float_bucket_values(self) -> None:
        hist = Histogram()

        hist.add_observation({"0-10": 5.5, "10-20": 10.7})

        assert hist.content["0-10"] == [5.5]
        assert hist.content["10-20"] == [10.7]

    def test_large_bucket_values(self) -> None:
        hist = Histogram()

        hist.add_observation({"0-1000000": 999999})
        hist.balance_content()
        hist.reduce_duplicates()

        assert hist.reduced_content["0-1000000"] == 999999.0

    def test_rebinning_preserves_singleton_bucket(self) -> None:
        hist = Histogram(repeat=1, bins=2, max_range=10.0)
        # Inclusive integer singleton at the overflow threshold.
        hist.add_observation({"10-10": 5.0})
        hist.balance_content()

        hist.reduce_duplicates()

        assert hist.reduced_content == {"0-9": 0.0, "10+": 5.0}

    def test_entries_property_sorted_order(self) -> None:
        hist = Histogram()
        hist.add_observation({"100-200": 1, "0-100": 2, "200-300": 3})

        result = hist.entries

        assert result is not None
        assert result[0] == "0-100"
        assert result[1] == "100-200"
        assert result[2] == "200-300"
