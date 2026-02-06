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

import pytest

from src.core.parsing.types.base import StatTypeRegistry
from src.core.parsing.types.histogram import Histogram


class TestHistogramInitialization:
    """Test Histogram object creation and initialization."""

    def test_init_with_defaults(self):
        # Arrange & Act
        hist = Histogram()

        # Assert
        assert hist._repeat == 1
        assert hist._bins == 0
        assert hist._max_range == 0.0
        assert hist._entries is None
        assert hist._statistics == []
        assert hist._content == {}

    def test_init_with_custom_repeat(self):
        # Arrange & Act
        hist = Histogram(repeat=5)

        # Assert
        assert hist._repeat == 5

    def test_init_with_explicit_entries(self):
        # Arrange & Act
        hist = Histogram(entries=["0-10", "10-20", "20-30"])

        # Assert
        assert hist._entries == ["0-10", "10-20", "20-30"]

    def test_init_with_rebinning_params(self):
        # Arrange & Act
        hist = Histogram(bins=10, max_range=100.0)

        # Assert
        assert hist._bins == 10
        assert hist._max_range == 100.0

    def test_init_with_statistics(self):
        # Arrange & Act
        hist = Histogram(statistics=["mean", "total"])

        # Assert
        assert hist._statistics == ["mean", "total"]
        # Statistics pre-initialized in content
        assert "mean" in hist._content
        assert "total" in hist._content

    def test_init_with_comma_separated_statistics(self):
        # Arrange & Act
        hist = Histogram(statistics="mean, total, samples")

        # Assert - string parsed and trimmed
        assert hist._statistics == ["mean", "total", "samples"]

    def test_required_params_empty(self):
        # Arrange & Act
        required = Histogram.required_params

        # Assert - histogram buckets are dynamic
        assert required == []


class TestHistogramEntriesProperty:
    """Test entries property with priority ordering."""

    def test_entries_priority_1_explicit_entries(self):
        # Arrange
        hist = Histogram(entries=["0-10", "10-20"], bins=5, max_range=50.0)

        # Act
        result = hist.entries

        # Assert - explicit entries take priority over rebinning
        assert result == ["0-10", "10-20"]

    def test_entries_priority_2_rebinning_with_overflow(self):
        # Arrange - bins > 1 creates overflow bucket
        hist = Histogram(bins=3, max_range=30.0)

        # Act
        result = hist.entries

        # Assert - rebinned buckets: 2 standard + 1 overflow
        # bin_width = 30 / (3-1) = 15
        assert "0-15" in result
        assert "15-30" in result
        assert "30+" in result
        assert len(result) == 3

    def test_entries_priority_2_rebinning_single_bin(self):
        # Arrange - bins = 1, no overflow
        hist = Histogram(bins=1, max_range=10.0)

        # Act
        result = hist.entries

        # Assert - single bucket, no overflow
        assert "0-10" in result
        assert len(result) == 1

    def test_entries_priority_3_discovered_buckets(self):
        # Arrange
        hist = Histogram()
        hist.content = {"0-10": 5, "10-20": 10, "20-30": 3}

        # Act
        result = hist.entries

        # Assert - sorted discovered buckets
        assert "0-10" in result
        assert "10-20" in result
        assert "20-30" in result

    def test_entries_includes_statistics(self):
        # Arrange
        hist = Histogram(statistics=["mean", "samples"])
        hist.content = {"0-10": 5}

        # Act
        result = hist.entries

        # Assert - statistics appended
        assert "mean" in result
        assert "samples" in result


class TestHistogramContentProperty:
    """Test content property getter and setter."""

    def test_content_getter(self):
        # Arrange
        hist = Histogram()

        # Act
        result = hist.content

        # Assert
        assert isinstance(result, dict)

    def test_content_setter_non_dict_raises(self):
        # Arrange
        hist = Histogram()

        # Act & Assert
        with pytest.raises(TypeError, match="HISTOGRAM.*Content must be dict"):
            hist.content = [1, 2, 3]

    def test_content_setter_non_numeric_values_raises(self):
        # Arrange
        hist = Histogram()

        # Act & Assert
        with pytest.raises(TypeError, match="Value non-convertible to number"):
            hist.content = {"0-10": ["invalid"]}


class TestHistogramContentSetting:
    """Test content setter with valid data."""

    def test_content_setter_with_single_values(self):
        # Arrange
        hist = Histogram()

        # Act
        hist.content = {"0-10": 5, "10-20": 10}

        # Assert - single values wrapped
        assert hist._content["0-10"] == [5.0]
        assert hist._content["10-20"] == [10.0]

    def test_content_setter_aggregates_list_values(self):
        # Arrange
        hist = Histogram()

        # Act - list values summed
        hist.content = {"0-10": [5, 10, 15]}

        # Assert - aggregated: 5+10+15=30
        assert hist._content["0-10"] == [30.0]

    def test_content_setter_multiple_assignments_extend(self):
        # Arrange
        hist = Histogram()

        # Act
        hist.content = {"0-10": 5}
        hist.content = {"0-10": 10}

        # Assert - values extended
        assert hist._content["0-10"] == [5.0, 10.0]

    def test_content_setter_dynamic_bucket_discovery(self):
        # Arrange
        hist = Histogram()

        # Act - new buckets dynamically added
        hist.content = {"0-100": 10}
        hist.content = {"100-200": 20}

        # Assert
        assert "0-100" in hist._content
        assert "100-200" in hist._content

    def test_content_setter_with_statistics(self):
        # Arrange
        hist = Histogram(statistics=["mean"])

        # Act
        hist.content = {"0-10": 5, "mean": 7.5}

        # Assert
        assert hist._content["mean"] == [7.5]


class TestHistogramBalanceContent:
    """Test balance_content method (padding per bucket)."""

    def test_balance_empty_buckets_pads_with_zeros(self):
        # Arrange
        hist = Histogram(repeat=3)
        hist.content = {"0-10": 5}
        # 0-10 has 1 value, needs 2 more

        # Act
        hist.balance_content()

        # Assert
        assert hist._balanced is True
        assert hist._content["0-10"] == [5.0, 0.0, 0.0]

    def test_balance_partial_buckets_pads_remainder(self):
        # Arrange
        hist = Histogram(repeat=4)
        hist.content = {"0-10": 10}
        hist.content = {"0-10": 20}

        # Act
        hist.balance_content()

        # Assert
        assert hist._content["0-10"] == [10.0, 20.0, 0.0, 0.0]

    def test_balance_exact_count_no_change(self):
        # Arrange
        hist = Histogram(repeat=2)
        hist.content = {"0-10": 5}
        hist.content = {"0-10": 10}

        # Act
        hist.balance_content()

        # Assert - no padding needed
        assert hist._content["0-10"] == [5.0, 10.0]

    def test_balance_too_many_values_raises(self):
        # Arrange
        hist = Histogram(repeat=1)
        hist.content = {"0-10": 5}
        hist.content = {"0-10": 10}

        # Act & Assert
        with pytest.raises(RuntimeError, match="more values than expected"):
            hist.balance_content()

    def test_balance_initializes_missing_statistics(self):
        # Arrange
        hist = Histogram(repeat=2, statistics=["mean"])
        hist.content = {"0-10": 5}
        # mean not provided

        # Act
        hist.balance_content()

        # Assert - mean initialized with zeros
        assert hist._content["mean"] == [0.0, 0.0]


class TestHistogramReduceDuplicates:
    """Test reduce_duplicates method (mean calculation)."""

    def test_reduce_single_value_per_bucket(self):
        # Arrange
        hist = Histogram()
        hist.content = {"0-10": 100, "10-20": 200}
        hist.balance_content()

        # Act
        hist.reduce_duplicates()

        # Assert - single value -> mean = value
        assert hist._reduced is True
        assert hist._reduced_content["0-10"] == 100.0
        assert hist._reduced_content["10-20"] == 200.0

    def test_reduce_multiple_values_calculates_mean(self):
        # Arrange
        hist = Histogram(repeat=3)
        hist.content = {"0-10": [10, 20, 30], "10-20": [100, 200, 300]}
        hist.balance_content()

        # Act
        hist.reduce_duplicates()

        # Assert - mean: (10+20+30)/3=20, (100+200+300)/3=200
        assert hist._reduced_content["0-10"] == 20.0
        assert hist._reduced_content["10-20"] == 200.0

    def test_reduce_empty_bucket_returns_zero(self):
        # Arrange
        hist = Histogram()
        hist.balance_content()  # All empty

        # Act
        hist.reduce_duplicates()

        # Assert - empty -> 0.0
        assert len(hist._reduced_content) == 0  # No buckets


class TestHistogramRebinning:
    """Test rebinning logic."""

    def test_reduce_with_rebinning_enabled(self):
        # Arrange - simple 2-bin rebinning
        hist = Histogram(repeat=1, bins=2, max_range=20.0)
        # Provide raw data: 0-10 has 5, 10-20 has 10
        hist.content = {"0-10": 5, "10-20": 10}
        hist.balance_content()

        # Act
        hist.reduce_duplicates()

        # Assert - rebinned buckets created
        # bins=2 means 1 standard bin + 1 overflow: bin_width=20/(2-1)=20
        assert "0-20" in hist._reduced_content
        assert "20+" in hist._reduced_content

    def test_rebinning_proportional_distribution(self):
        # Arrange - raw bucket overlaps multiple target bins
        hist = Histogram(repeat=1, bins=3, max_range=30.0)
        # bin_width = 30/(3-1) = 15
        # Target buckets: 0-15, 15-30, 30+
        # Raw bucket 0-30 has value 30
        hist.content = {"0-30": 30}
        hist.balance_content()

        # Act
        hist.reduce_duplicates()

        # Assert - 30 distributed across 0-15 and 15-30
        # 0-15 gets 15/30 * 30 = 15
        # 15-30 gets 15/30 * 30 = 15
        assert hist._reduced_content["0-15"] == 15.0
        assert hist._reduced_content["15-30"] == 15.0

    def test_rebinning_overflow_bucket(self):
        # Arrange
        hist = Histogram(repeat=1, bins=2, max_range=10.0)
        # bin_width = 10/(2-1) = 10
        # Target: 0-10, 10+
        # Raw: 0-20 with value 20
        hist.content = {"0-20": 20}
        hist.balance_content()

        # Act
        hist.reduce_duplicates()

        # Assert - half goes to 0-10, half to 10+
        assert hist._reduced_content["0-10"] == 10.0
        assert hist._reduced_content["10+"] == 10.0

    def test_rebinning_preserves_summary_stats(self):
        # Arrange
        hist = Histogram(repeat=1, bins=2, max_range=10.0, statistics=["mean"])
        hist.content = {"0-10": 5, "mean": 7.5}
        hist.balance_content()

        # Act
        hist.reduce_duplicates()

        # Assert - mean preserved as-is
        assert hist._reduced_content["mean"] == 7.5

    def test_rebinning_single_bin_no_overflow(self):
        # Arrange - bins=1, no overflow bucket
        hist = Histogram(repeat=1, bins=1, max_range=10.0)
        hist.content = {"0-20": 20}
        hist.balance_content()

        # Act
        hist.reduce_duplicates()

        # Assert - all goes to single bucket plus overflow fallback
        assert "0-10" in hist._reduced_content


class TestHistogramRangeParser:
    """Test _parse_range_key helper method."""

    def test_parse_range_key_valid(self):
        # Arrange
        hist = Histogram()

        # Act
        result = hist._parse_range_key("0-1023")

        # Assert
        assert result == [0.0, 1023.0]

    def test_parse_range_key_multi_digit(self):
        # Arrange
        hist = Histogram()

        # Act
        result = hist._parse_range_key("128-255")

        # Assert
        assert result == [128.0, 255.0]

    def test_parse_range_key_invalid(self):
        # Arrange
        hist = Histogram()

        # Act - non-range string
        result = hist._parse_range_key("total")

        # Assert - empty list
        assert result == []

    def test_parse_range_key_overflow_format(self):
        # Arrange
        hist = Histogram()

        # Act
        result = hist._parse_range_key("1024+")

        # Assert - no match for overflow format
        assert result == []


class TestHistogramReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self):
        # Arrange
        hist = Histogram()
        hist.content = {"0-10": 5}
        # Don't call balance_content()

        # Act & Assert
        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = hist.reduced_content

    def test_access_reduced_content_before_reduce_raises(self):
        # Arrange
        hist = Histogram()
        hist.content = {"0-10": 5}
        hist.balance_content()
        # Don't call reduce_duplicates()

        # Act & Assert
        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = hist.reduced_content

    def test_access_reduced_content_after_both_succeeds(self):
        # Arrange
        hist = Histogram()
        hist.content = {"0-10": 50}
        hist.balance_content()
        hist.reduce_duplicates()

        # Act
        result = hist.reduced_content

        # Assert
        assert isinstance(result, dict)
        assert result["0-10"] == 50.0

    def test_access_via_reducedContent_alias(self):
        # Arrange
        hist = Histogram()
        hist.content = {"0-10": 100}
        hist.balance_content()
        hist.reduce_duplicates()

        # Act - backward compatibility alias
        result = hist.reducedContent

        # Assert
        assert result["0-10"] == 100.0


class TestHistogramBackwardCompatibility:
    """Test backward compatibility aliases."""

    def test_balance_content_alias(self):
        # Arrange
        hist = Histogram()

        # Act
        hist.balanceContent()

        # Assert
        assert hist._balanced is True

    def test_reduce_duplicates_alias(self):
        # Arrange
        hist = Histogram()
        hist.content = {"0-10": 5}
        hist.balance_content()

        # Act
        hist.reduceDuplicates()

        # Assert
        assert hist._reduced is True


class TestHistogramTypeRegistration:
    """Test Histogram is properly registered in the type system."""

    def test_histogram_registered_with_decorator(self):
        # Act
        registered_types = StatTypeRegistry.get_types()

        # Assert
        assert "histogram" in registered_types

    def test_create_histogram_via_registry(self):
        # Act
        hist = StatTypeRegistry.create("histogram", bins=5, max_range=100.0)

        # Assert
        assert isinstance(hist, Histogram)
        assert hist._bins == 5
        assert hist._max_range == 100.0


class TestHistogramStrMethod:
    """Test __str__ method for string representation."""

    def test_str_method_empty_histogram(self):
        # Arrange
        hist = Histogram(repeat=3)

        # Act
        result = str(hist)

        # Assert
        assert "Histogram" in result
        assert "buckets=0" in result
        assert "repeat=3" in result

    def test_str_method_with_buckets(self):
        # Arrange
        hist = Histogram()
        hist.content = {"0-10": 5, "10-20": 10}

        # Act
        result = str(hist)

        # Assert
        assert "Histogram" in result
        assert "buckets=2" in result


class TestHistogramEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero_value_buckets(self):
        # Arrange
        hist = Histogram()

        # Act
        hist.content = {"0-10": 0}
        hist.balance_content()
        hist.reduce_duplicates()

        # Assert
        assert hist._reduced_content["0-10"] == 0.0

    def test_float_bucket_values(self):
        # Arrange
        hist = Histogram()

        # Act
        hist.content = {"0-10": 5.5, "10-20": 10.7}

        # Assert - floats accepted
        assert hist._content["0-10"] == [5.5]
        assert hist._content["10-20"] == [10.7]

    def test_large_bucket_values(self):
        # Arrange
        hist = Histogram()

        # Act
        hist.content = {"0-1000000": 999999}
        hist.balance_content()
        hist.reduce_duplicates()

        # Assert
        assert hist._reduced_content["0-1000000"] == 999999.0

    def test_rebinning_with_zero_span_bucket(self):
        # Arrange - raw bucket with start == end (zero span)
        hist = Histogram(repeat=1, bins=2, max_range=10.0)
        # Zero span buckets are skipped during rebinning (raw_span <= 0 check)
        hist._content = {"10-10": [5.0]}  # Zero span - will be skipped
        hist.balance_content()

        # Act
        hist.reduce_duplicates()

        # Assert - zero span bucket skipped, only target bins present
        # bins=2, max_range=10 → num_std_bins=1, bin_width=10 → "0-10" + "10+"
        assert "10-10" not in hist._reduced_content
        assert "0-10" in hist._reduced_content
        assert "10+" in hist._reduced_content
        # All values are 0.0 since the zero-span bucket was skipped
        assert hist._reduced_content["0-10"] == 0.0
        assert hist._reduced_content["10+"] == 0.0

    def test_entries_property_sorted_order(self):
        # Arrange
        hist = Histogram()
        hist.content = {"100-200": 1, "0-100": 2, "200-300": 3}

        # Act
        result = hist.entries

        # Assert - sorted lexicographically
        assert result[0] == "0-100"
        assert result[1] == "100-200"
        assert result[2] == "200-300"
