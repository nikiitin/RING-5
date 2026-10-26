"""
Comprehensive tests for Distribution stat type.

Tests cover:
- Explicit grid initialization, summary-only extraction and geometry limits
- Exact native entries and selected summary ownership
- Numeric frame validation and visible missing boundaries
- Content setting (aggregation, range validation, statistics_only)
- balance_content (padding per bucket, overflow detection)
- reduce_duplicates (arithmetic mean per bucket)
- reduced_content property guards
- Type registration
- Edge cases (large ranges, empty buckets, out-of-range values)
- __str__ method
"""

import math
from typing import Any, cast

import pytest

from src.parsing.gem5.types.base import StatTypeRegistry
from src.parsing.gem5.types.distribution import Distribution
from src.core.models.distribution_geometry import MAX_DISTRIBUTION_BUCKETS


class TestDistributionInitialization:
    """Test Distribution object creation and initialization."""

    def test_required_params_contains_min_max(self) -> None:
        required = Distribution.required_params

        assert "minimum" in required
        assert "maximum" in required
        assert set(required) == {"minimum", "maximum", "bucket_size", "zero_policy"}

    def test_init_with_default_range(self) -> None:
        dist = Distribution(minimum=0, maximum=10, bucket_size=1, zero_policy="missing")

        assert dist._repeat == 1
        assert "underflows" in dist.entries
        assert "10" in dist.entries
        assert dist.entries[-1] == "overflows"
        assert dist._statistics_only is False
        # Check bucket initialization
        assert "underflows" in dist.content
        assert "overflows" in dist.content
        assert "0" in dist.content
        assert "10" in dist.content
        assert len(dist.content) == 13  # underflows + 0-10 + overflows

    def test_init_with_custom_repeat(self) -> None:
        dist = Distribution(repeat=5, minimum=0, maximum=5, bucket_size=1, zero_policy="missing")

        assert dist._repeat == 5

    def test_init_with_statistics(self) -> None:
        dist = Distribution(
            minimum=0, maximum=5, statistics=["mean", "stdev"], bucket_size=1, zero_policy="missing"
        )

        assert dist.entries[-2:] == ["mean", "stdev"]
        assert "mean" in dist.content
        assert "stdev" in dist.content

    def test_init_statistics_only_mode(self) -> None:
        dist = Distribution(statistics=["mean", "samples"], statistics_only=True)

        assert dist._statistics_only is True
        assert dist.entries == ["mean", "samples"]
        # Only statistics keys, no buckets
        assert "mean" in dist.content
        assert "samples" in dist.content
        assert "underflows" not in dist.content
        assert "overflows" not in dist.content

    def test_init_exceeds_safety_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="between 1"):
            Distribution(
                minimum=0,
                maximum=MAX_DISTRIBUTION_BUCKETS + 1,
                bucket_size=1,
                zero_policy="missing",
            )

    def test_init_large_range_within_limit(self) -> None:
        dist = Distribution(minimum=0, maximum=1000, bucket_size=1, zero_policy="missing")

        assert len(dist.content) == 1003  # underflows + 0-1000 + overflows


class TestDistributionProperties:
    """Test Distribution property getters."""

    def test_native_entries_preserve_the_declared_origin(self) -> None:
        dist = Distribution(minimum=10, maximum=20, bucket_size=1, zero_policy="missing")
        assert dist.entries[1] == "10"

    def test_native_entries_preserve_the_declared_last_slot(self) -> None:
        dist = Distribution(minimum=10, maximum=20, bucket_size=1, zero_policy="missing")
        assert dist.entries[-2] == "20"

    def test_selected_statistics_are_explicit_output_entries(self) -> None:
        dist = Distribution(
            minimum=0, maximum=5, bucket_size=1, zero_policy="missing", statistics=["mean", "total"]
        )
        assert dist.entries[-2:] == ["mean", "total"]

    def test_entries_property_returns_bucket_names(self) -> None:
        dist = Distribution(minimum=0, maximum=2, bucket_size=1, zero_policy="missing")

        result = dist.entries

        assert isinstance(result, list)
        # Should contain underflows, 0, 1, 2, overflows
        assert "underflows" in result
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert "overflows" in result

    def test_content_property_getter(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")

        result = dist.content

        assert isinstance(result, dict)
        assert "underflows" in result
        assert "overflows" in result


class TestDistributionContentValidation:
    """Test typed numeric observation validation."""

    def test_add_observation_non_dict_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=5, bucket_size=1, zero_policy="missing")

        with pytest.raises(TypeError, match="DISTRIBUTION.*numeric entry mapping"):
            dist.add_observation(cast(Any, [1, 2, 3]))

    def test_missing_underflow_remains_absent_without_an_omission_guarantee(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        dist.add_observation({"0": 10.0, "1": 20.0, "overflows": 0.0})
        assert dist.missing_measurement_count == 1
        dist.balance_content()
        dist.reduce_duplicates()
        assert math.isnan(dist.reduced_content["underflows"])

    def test_missing_overflow_remains_absent_without_an_omission_guarantee(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        dist.add_observation({"underflows": 0.0, "0": 10.0, "1": 20.0})
        assert dist.missing_measurement_count == 1
        dist.balance_content()
        dist.reduce_duplicates()
        assert math.isnan(dist.reduced_content["overflows"])

    def test_omitted_boundary_and_internal_cells_remain_missing(self) -> None:
        dist = Distribution(minimum=0, maximum=5, bucket_size=1, zero_policy="missing")
        dist.add_observation({"underflows": 0.0, "1": 10.0, "5": 20.0, "overflows": 0.0})
        assert dist.missing_measurement_count == 4
        dist.balance_content()
        dist.reduce_duplicates()
        assert math.isnan(dist.reduced_content["0"])
        assert math.isnan(dist.reduced_content["2"])

    def test_add_observation_out_of_range_bucket_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=5, bucket_size=1, zero_policy="missing")

        with pytest.raises(RuntimeError, match="contradicts the declared native grid"):
            dist.add_observation(
                {"underflows": 0.0, "0": 10.0, "5": 20.0, "10": 999.0, "overflows": 0.0}
            )

    def test_add_observation_non_numeric_values_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")

        with pytest.raises(TypeError, match="one numeric measurement"):
            dist.add_observation({"underflows": 0.0, "0": ["invalid"], "1": 10.0, "overflows": 0.0})


class TestDistributionContentSetting:
    """Test complete numeric observation frames."""

    def test_add_observation_with_valid_dict(self) -> None:
        dist = Distribution(minimum=0, maximum=2, bucket_size=1, zero_policy="missing")

        dist.add_observation({"underflows": 5, "0": 10, "1": 20, "2": 30, "overflows": 2})

        assert dist.content["underflows"] == [5]
        assert dist.content["0"] == [10]
        assert dist.content["2"] == [30]

    def test_numeric_frame_values_are_retained(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")

        dist.add_observation({"underflows": 6.0, "0": 30.0, "1": 45.0, "overflows": 0.0})

        assert dist.content["underflows"] == [6.0]
        assert dist.content["0"] == [30.0]
        assert dist.content["1"] == [45.0]

    def test_add_observation_with_statistics(self) -> None:
        dist = Distribution(
            minimum=0, maximum=1, statistics=["mean"], bucket_size=1, zero_policy="missing"
        )

        dist.add_observation(
            {"underflows": 0.0, "0": 10.0, "1": 20.0, "overflows": 0.0, "mean": 15.5}
        )

        assert dist.content["mean"] == [15.5]

    def test_add_observation_statistics_only_mode(self) -> None:
        dist = Distribution(statistics=["mean", "samples"], statistics_only=True)

        dist.add_observation({"mean": 42.5, "samples": 1000.0})

        assert dist.content["mean"] == [42.5]
        assert dist.content["samples"] == [1000]

    def test_add_observation_statistics_only_skips_bucket_data(self) -> None:
        dist = Distribution(statistics=["mean"], statistics_only=True)

        dist.add_observation({"mean": 10.0, "0": 100.0, "underflows": 5.0})

        assert "mean" in dist.content
        assert "0" not in dist.content
        assert "underflows" not in dist.content

    def test_add_observation_skips_unknown_non_numeric_keys(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")

        dist.add_observation(
            {"underflows": 0.0, "0": 10.0, "1": 20.0, "overflows": 0.0, "unknown_stat": 999.0}
        )

        assert "unknown_stat" not in dist.content

    def test_add_observation_multiple_assignments_extend(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")

        dist.add_observation({"underflows": 1.0, "0": 10.0, "1": 20.0, "overflows": 0.0})
        dist.add_observation({"underflows": 2.0, "0": 30.0, "1": 40.0, "overflows": 1.0})

        assert dist.content["underflows"] == [1, 2]
        assert dist.content["0"] == [10, 30]


class TestDistributionBalanceContent:
    """Test logical missing measurements while retaining actual frames."""

    def test_balance_empty_buckets_preserves_missingness(self) -> None:
        dist = Distribution(repeat=3, minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        # No content set

        dist.balance_content()

        assert dist.is_balanced is True
        assert dist.content == {"underflows": [], "0": [], "1": [], "overflows": []}
        assert dist.padded_count == dist.missing_measurement_count == 12
        dist.reduce_duplicates()
        assert set(dist.reduced_content) == {"underflows", "0", "1", "overflows"}
        assert all(math.isnan(value) for value in dist.reduced_content.values())

    def test_balance_partial_buckets_retains_actual_frames(self) -> None:
        dist = Distribution(repeat=4, minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        # Supply complete source/dump frames.
        dist.add_observation({"underflows": 1.0, "0": 10.0, "1": 30.0, "overflows": 0.0})
        dist.add_observation({"underflows": 0.0, "0": 20.0, "1": 0.0, "overflows": 0.0})

        dist.balance_content()

        assert dist.content["underflows"] == [1, 0]
        assert dist.content["0"] == [10, 20]
        assert dist.content["1"] == [30, 0]
        assert dist.padded_count == dist.missing_measurement_count == 8
        dist.reduce_duplicates()
        assert set(dist.reduced_content) == {"underflows", "0", "1", "overflows"}
        assert all(math.isnan(value) for value in dist.reduced_content.values())

    def test_balance_exact_count_no_change(self) -> None:
        dist = Distribution(repeat=2, minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        dist.add_observation({"underflows": 1.0, "0": 10.0, "1": 20.0, "overflows": 0.0})
        dist.add_observation({"underflows": 2.0, "0": 30.0, "1": 40.0, "overflows": 1.0})

        dist.balance_content()

        assert dist.content["0"] == [10, 30]
        assert dist.content["1"] == [20, 40]

    def test_balance_too_many_values_raises(self) -> None:
        dist = Distribution(repeat=1, minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        # Assign 2 values when repeat=1
        dist.add_observation({"underflows": 1.0, "0": 10.0, "1": 20.0, "overflows": 0.0})
        dist.add_observation({"underflows": 2.0, "0": 30.0, "1": 40.0, "overflows": 1.0})

        with pytest.raises(RuntimeError, match="More observations.*than expected"):
            dist.balance_content()


class TestDistributionReduceDuplicates:
    """Test reduce_duplicates method (arithmetic mean per bucket)."""

    # [test->req~ring5.ingestion.distribution~1]

    def test_reduce_single_value_per_bucket(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        dist.add_observation({"underflows": 5.0, "0": 100.0, "1": 200.0, "overflows": 3.0})
        dist.balance_content()

        dist.reduce_duplicates()

        assert dist.is_reduced is True
        assert dist.reduced_content["underflows"] == 5.0
        assert dist.reduced_content["0"] == 100.0
        assert dist.reduced_content["1"] == 200.0

    def test_reduce_multiple_values_calculates_mean(self) -> None:
        dist = Distribution(repeat=3, minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        for value in (1, 2, 3):
            dist.add_observation(
                {"underflows": value, "0": value * 10, "1": value * 100, "overflows": 0}
            )
        dist.balance_content()

        dist.reduce_duplicates()

        assert dist.reduced_content["underflows"] == 2.0
        assert dist.reduced_content["0"] == 20.0
        assert dist.reduced_content["1"] == 200.0

    def test_reduce_empty_bucket_returns_nan(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        dist.balance_content()  # All requested observations are missing.

        dist.reduce_duplicates()

        assert math.isnan(dist.reduced_content["underflows"])
        assert math.isnan(dist.reduced_content["0"])

    def test_reduce_with_statistics(self) -> None:
        dist = Distribution(
            minimum=0, maximum=1, statistics=["mean"], bucket_size=1, zero_policy="missing"
        )
        dist.add_observation(
            {"underflows": 0.0, "0": 10.0, "1": 20.0, "overflows": 0.0, "mean": 15.5}
        )
        dist.balance_content()

        dist.reduce_duplicates()

        assert dist.reduced_content["mean"] == 15.5


class TestDistributionReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        dist.add_observation({"underflows": 0.0, "0": 10.0, "1": 20.0, "overflows": 0.0})
        # Don't call balance_content()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = dist.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        dist.add_observation({"underflows": 0.0, "0": 10.0, "1": 20.0, "overflows": 0.0})
        dist.balance_content()
        # Don't call reduce_duplicates()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = dist.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")
        dist.add_observation({"underflows": 0.0, "0": 10.0, "1": 20.0, "overflows": 0.0})
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
        dist = StatTypeRegistry.create(
            "distribution", minimum=0, maximum=10, bucket_size=1, zero_policy="missing"
        )

        assert isinstance(dist, Distribution)
        assert "underflows" in dist.entries
        assert "10" in dist.entries


class TestDistributionStrMethod:
    """Test __str__ method for string representation."""

    def test_str_method(self) -> None:
        dist = Distribution(repeat=3, minimum=0, maximum=100, bucket_size=1, zero_policy="missing")

        result = str(dist)

        assert "Distribution" in result
        assert "entries=103" in result
        assert "repeat=3" in result


class TestDistributionEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero_range_distribution(self) -> None:
        dist = Distribution(minimum=0, maximum=0, bucket_size=1, zero_policy="missing")

        assert "0" in dist.content
        assert len(dist.content) == 3  # underflows, 0, overflows

    def test_negative_range(self) -> None:
        dist = Distribution(minimum=-10, maximum=-5, bucket_size=1, zero_policy="missing")

        assert "-10" in dist.entries
        assert "-5" in dist.entries
        assert "-10" in dist.content
        assert "-5" in dist.content

    def test_float_values_in_content(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")

        dist.add_observation({"underflows": 0.5, "0": 10.7, "1": 20.3, "overflows": 1.1})

        assert dist.content["0"] == [10.7]

    def test_large_bucket_values(self) -> None:
        dist = Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing")

        dist.add_observation({"underflows": 0.0, "0": 1000000.0, "1": 9999999.0, "overflows": 0.0})
        dist.balance_content()
        dist.reduce_duplicates()

        assert dist.reduced_content["0"] == 1_000_000.0
        assert dist.reduced_content["1"] == 9_999_999.0

    def test_statistics_only_no_validation_errors(self) -> None:
        dist = Distribution(statistics=["mean"], statistics_only=True)

        dist.add_observation({"mean": 42.0})
        dist.balance_content()
        dist.reduce_duplicates()

        assert dist.reduced_content["mean"] == 42.0

    def test_missing_observation_cannot_become_a_measured_zero(self) -> None:
        dist = Distribution(repeat=2, minimum=0, maximum=2, bucket_size=1, zero_policy="missing")
        dist.add_observation({"underflows": 0, "0": 10, "1": 20, "2": 0, "overflows": 0})
        dist.balance_content()
        dist.reduce_duplicates()
        assert math.isnan(dist.reduced_content["2"])
