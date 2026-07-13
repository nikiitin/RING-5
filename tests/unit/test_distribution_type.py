"""
Comprehensive tests for Distribution stat type.

Tests cover:
- Initialization (normal mode, statistics_only mode, safety limits)
- Properties (minimum, maximum, statistics, entries)
- Content validation (dict structure, mandatory keys, boundary checks)
- Content setting (aggregation, range validation, statistics_only)
- balance_content (padding per bucket, overflow detection)
- reduce_duplicates (arithmetic mean per bucket)
- reduced_content property guards
- Type registration
- Edge cases (large ranges, empty buckets, out-of-range values)
- __str__ method
"""

import pytest

from src.parsing.gem5.types.base import StatTypeRegistry
from src.parsing.gem5.types.distribution import SAFETY_MAX_BUCKETS, Distribution


class TestDistributionInitialization:
    """Test Distribution object creation and initialization."""

    def test_init_with_default_range(self) -> None:
        dist = Distribution(minimum=0, maximum=10)

        assert dist._repeat == 1
        assert dist._minimum == 0
        assert dist._maximum == 10
        assert dist._statistics == []
        assert dist._statistics_only is False
        # Check bucket initialization
        assert "underflows" in dist.content
        assert "overflows" in dist.content
        assert "0" in dist.content
        assert "10" in dist.content
        assert len(dist.content) == 13  # underflows + 0-10 + overflows

    def test_init_with_custom_repeat(self) -> None:
        dist = Distribution(repeat=5, minimum=0, maximum=5)

        assert dist._repeat == 5

    def test_init_with_statistics(self) -> None:
        dist = Distribution(minimum=0, maximum=5, statistics=["mean", "stdev"])

        assert dist._statistics == ["mean", "stdev"]
        assert "mean" in dist.content
        assert "stdev" in dist.content

    def test_init_statistics_only_mode(self) -> None:
        dist = Distribution(statistics=["mean", "samples"], statistics_only=True)

        assert dist._statistics_only is True
        assert dist._minimum == 0
        assert dist._maximum == 0
        # Only statistics keys, no buckets
        assert "mean" in dist.content
        assert "samples" in dist.content
        assert "underflows" not in dist.content
        assert "overflows" not in dist.content

    def test_init_exceeds_safety_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds safety limit"):
            Distribution(minimum=0, maximum=SAFETY_MAX_BUCKETS + 1)

    def test_init_large_range_within_limit(self) -> None:
        dist = Distribution(minimum=0, maximum=1000)

        assert len(dist.content) == 1003  # underflows + 0-1000 + overflows

    def test_required_params_contains_min_max(self) -> None:
        required = Distribution.required_params

        assert "minimum" in required
        assert "maximum" in required
        assert len(required) == 2


class TestDistributionProperties:
    """Test Distribution property getters."""

    def test_minimum_property(self) -> None:
        dist = Distribution(minimum=10, maximum=20)

        result = dist.minimum

        assert result == 10
        assert isinstance(result, int)

    def test_maximum_property(self) -> None:
        dist = Distribution(minimum=10, maximum=20)

        result = dist.maximum

        assert result == 20
        assert isinstance(result, int)

    def test_statistics_property(self) -> None:
        dist = Distribution(minimum=0, maximum=5, statistics=["mean", "total"])

        result = dist.statistics

        assert result == ["mean", "total"]
        assert isinstance(result, list)

    def test_entries_property_returns_bucket_names(self) -> None:
        dist = Distribution(minimum=0, maximum=2)

        result = dist.entries

        assert isinstance(result, list)
        # Should contain underflows, 0, 1, 2, overflows
        assert "underflows" in result
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert "overflows" in result

    def test_content_property_getter(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        result = dist.content

        assert isinstance(result, dict)
        assert "underflows" in result
        assert "overflows" in result


class TestDistributionContentValidation:
    """Test content setter validation rules."""

    def test_content_setter_non_dict_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=5)

        with pytest.raises(TypeError, match="DISTRIBUTION.*Content must be dict"):
            dist.content = [1, 2, 3]

    def test_content_setter_missing_underflows_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        with pytest.raises(TypeError, match="Missing mandatory keys.*underflows"):
            dist.content = {"0": [10], "1": [20], "overflows": [0]}

    def test_content_setter_missing_overflows_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        with pytest.raises(TypeError, match="Missing mandatory keys.*overflows"):
            dist.content = {"underflows": [0], "0": [10], "1": [20]}

    def test_content_setter_missing_boundary_buckets_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=5)

        with pytest.raises(RuntimeError, match="Boundary buckets.*missing"):
            dist.content = {"underflows": [0], "1": [10], "5": [20], "overflows": [0]}

    def test_content_setter_out_of_range_bucket_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=5)

        with pytest.raises(RuntimeError, match="out of configured range"):
            dist.content = {
                "underflows": [0],
                "0": [10],
                "5": [20],
                "10": [999],  # Out of range!
                "overflows": [0],
            }

    def test_content_setter_non_numeric_values_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        with pytest.raises(TypeError, match="Value error.*Expected numbers"):
            dist.content = {"underflows": [0], "0": ["invalid"], "1": [10], "overflows": [0]}


class TestDistributionContentSetting:
    """Test content setter with valid data."""

    def test_content_setter_with_valid_dict(self) -> None:
        dist = Distribution(minimum=0, maximum=2)

        dist.content = {"underflows": 5, "0": 10, "1": 20, "2": 30, "overflows": 2}

        assert dist.content["underflows"] == [5]
        assert dist.content["0"] == [10]
        assert dist.content["2"] == [30]

    def test_content_setter_aggregates_list_values(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        dist.content = {
            "underflows": [1, 2, 3],  # Sum = 6
            "0": [10, 20],  # Sum = 30
            "1": [5, 15, 25],  # Sum = 45
            "overflows": [0],
        }

        assert dist.content["underflows"] == [6.0]
        assert dist.content["0"] == [30.0]
        assert dist.content["1"] == [45.0]

    def test_content_setter_with_statistics(self) -> None:
        dist = Distribution(minimum=0, maximum=1, statistics=["mean"])

        dist.content = {"underflows": [0], "0": [10], "1": [20], "overflows": [0], "mean": [15.5]}

        assert dist.content["mean"] == [15.5]

    def test_content_setter_statistics_only_mode(self) -> None:
        dist = Distribution(statistics=["mean", "samples"], statistics_only=True)

        dist.content = {"mean": [42.5], "samples": [1000]}

        assert dist.content["mean"] == [42.5]
        assert dist.content["samples"] == [1000]

    def test_content_setter_statistics_only_skips_bucket_data(self) -> None:
        dist = Distribution(statistics=["mean"], statistics_only=True)

        dist.content = {"mean": [10], "0": [100], "underflows": [5]}  # Ignored  # Ignored

        assert "mean" in dist.content
        assert "0" not in dist.content
        assert "underflows" not in dist.content

    def test_content_setter_skips_unknown_non_numeric_keys(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        dist.content = {
            "underflows": [0],
            "0": [10],
            "1": [20],
            "overflows": [0],
            "unknown_stat": [999],  # Skipped silently
        }

        assert "unknown_stat" not in dist.content

    def test_content_setter_multiple_assignments_extend(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        dist.content = {"underflows": [1], "0": [10], "1": [20], "overflows": [0]}
        dist.content = {"underflows": [2], "0": [30], "1": [40], "overflows": [1]}

        assert dist.content["underflows"] == [1, 2]
        assert dist.content["0"] == [10, 30]


class TestDistributionBalanceContent:
    """Test balance_content method (padding per bucket)."""

    def test_balance_empty_buckets_pads_with_zeros(self) -> None:
        dist = Distribution(repeat=3, minimum=0, maximum=1)
        # No content set

        dist.balance_content()

        assert dist.is_balanced is True
        assert dist.content["underflows"] == [0.0, 0.0, 0.0]
        assert dist.content["0"] == [0.0, 0.0, 0.0]
        assert dist.content["overflows"] == [0.0, 0.0, 0.0]

    def test_balance_partial_buckets_pads_remainder(self) -> None:
        dist = Distribution(repeat=4, minimum=0, maximum=1)
        # Assign values individually to avoid aggregation
        dist.content = {"underflows": [1], "0": [10], "1": [30], "overflows": [0]}
        dist.content = {"underflows": [0], "0": [20], "1": [0], "overflows": [0]}

        dist.balance_content()

        assert dist.content["underflows"] == [1, 0, 0.0, 0.0]
        assert dist.content["0"] == [10, 20, 0.0, 0.0]
        assert dist.content["1"] == [30, 0, 0.0, 0.0]

    def test_balance_exact_count_no_change(self) -> None:
        dist = Distribution(repeat=2, minimum=0, maximum=1)
        dist.content = {"underflows": [1], "0": [10], "1": [20], "overflows": [0]}
        dist.content = {"underflows": [2], "0": [30], "1": [40], "overflows": [1]}

        dist.balance_content()

        assert dist.content["0"] == [10, 30]
        assert dist.content["1"] == [20, 40]

    def test_balance_too_many_values_raises(self) -> None:
        dist = Distribution(repeat=1, minimum=0, maximum=1)
        # Assign 2 values when repeat=1
        dist.content = {"underflows": [1], "0": [10], "1": [20], "overflows": [0]}
        dist.content = {"underflows": [2], "0": [30], "1": [40], "overflows": [1]}

        with pytest.raises(RuntimeError, match="more values than expected"):
            dist.balance_content()


class TestDistributionReduceDuplicates:
    """Test reduce_duplicates method (arithmetic mean per bucket)."""

    def test_reduce_single_value_per_bucket(self) -> None:
        dist = Distribution(minimum=0, maximum=1)
        dist.content = {"underflows": [5], "0": [100], "1": [200], "overflows": [3]}
        dist.balance_content()

        dist.reduce_duplicates()

        assert dist.is_reduced is True
        assert dist.reduced_content["underflows"] == 5.0
        assert dist.reduced_content["0"] == 100.0
        assert dist.reduced_content["1"] == 200.0

    def test_reduce_multiple_values_calculates_mean(self) -> None:
        dist = Distribution(repeat=3, minimum=0, maximum=1)
        dist.content = {
            "underflows": [1, 2, 3],
            "0": [10, 20, 30],
            "1": [100, 200, 300],
            "overflows": [0, 0, 0],
        }
        dist.balance_content()

        dist.reduce_duplicates()

        assert dist.reduced_content["underflows"] == 2.0
        assert dist.reduced_content["0"] == 20.0
        assert dist.reduced_content["1"] == 200.0

    def test_reduce_empty_bucket_returns_zero(self) -> None:
        dist = Distribution(minimum=0, maximum=1)
        dist.balance_content()  # All buckets padded with zeros

        dist.reduce_duplicates()

        assert dist.reduced_content["underflows"] == 0.0
        assert dist.reduced_content["0"] == 0.0

    def test_reduce_with_statistics(self) -> None:
        dist = Distribution(minimum=0, maximum=1, statistics=["mean"])
        dist.content = {"underflows": [0], "0": [10], "1": [20], "overflows": [0], "mean": [15.5]}
        dist.balance_content()

        dist.reduce_duplicates()

        assert dist.reduced_content["mean"] == 15.5


class TestDistributionReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=1)
        dist.content = {"underflows": [0], "0": [10], "1": [20], "overflows": [0]}
        # Don't call balance_content()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = dist.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=1)
        dist.content = {"underflows": [0], "0": [10], "1": [20], "overflows": [0]}
        dist.balance_content()
        # Don't call reduce_duplicates()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = dist.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        dist = Distribution(minimum=0, maximum=1)
        dist.content = {"underflows": [0], "0": [10], "1": [20], "overflows": [0]}
        dist.balance_content()
        dist.reduce_duplicates()

        result = dist.reduced_content

        assert isinstance(result, dict)
        assert result["0"] == 10.0


class TestDistributionTypeRegistration:
    """Test Distribution is properly registered in the type system."""

    def test_distribution_registered_with_decorator(self) -> None:
        registered_types = StatTypeRegistry.get_types()

        assert "distribution" in registered_types

    def test_create_distribution_via_registry(self) -> None:
        dist = StatTypeRegistry.create("distribution", minimum=0, maximum=10)

        assert isinstance(dist, Distribution)
        assert dist._minimum == 0
        assert dist._maximum == 10


class TestDistributionStrMethod:
    """Test __str__ method for string representation."""

    def test_str_method(self) -> None:
        dist = Distribution(repeat=3, minimum=0, maximum=100)

        result = str(dist)

        assert "Distribution" in result
        assert "[0, 100]" in result
        assert "repeat=3" in result


class TestDistributionEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero_range_distribution(self) -> None:
        dist = Distribution(minimum=0, maximum=0)

        assert "0" in dist.content
        assert len(dist.content) == 3  # underflows, 0, overflows

    def test_negative_range(self) -> None:
        dist = Distribution(minimum=-10, maximum=-5)

        assert dist._minimum == -10
        assert dist._maximum == -5
        assert "-10" in dist.content
        assert "-5" in dist.content

    def test_float_values_in_content(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        dist.content = {"underflows": [0.5], "0": [10.7], "1": [20.3], "overflows": [1.1]}

        assert dist.content["0"] == [10.7]

    def test_large_bucket_values(self) -> None:
        dist = Distribution(minimum=0, maximum=1)

        dist.content = {"underflows": [0], "0": [1_000_000], "1": [9_999_999], "overflows": [0]}
        dist.balance_content()
        dist.reduce_duplicates()

        assert dist.reduced_content["0"] == 1_000_000.0
        assert dist.reduced_content["1"] == 9_999_999.0

    def test_statistics_only_no_validation_errors(self) -> None:
        dist = Distribution(statistics=["mean"], statistics_only=True)

        dist.content = {"mean": [42]}
        dist.balance_content()
        dist.reduce_duplicates()

        assert dist.reduced_content["mean"] == 42.0

    def test_reduce_with_truly_empty_bucket(self) -> None:
        dist = Distribution(minimum=0, maximum=2)
        dist.content = {
            "underflows": [0],
            "0": [10],
            "1": [20],
            "2": [0],  # Will be in content but...
            "overflows": [0],
        }
        # Manually clear bucket "2" to test empty path
        dist.content["2"] = []

        object.__setattr__(dist, "_balanced", True)  # Hack to bypass guard
        dist.reduce_duplicates()

        assert object.__getattribute__(dist, "_reduced_content")["2"] == 0.0
