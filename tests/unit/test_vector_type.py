"""
Comprehensive tests for Vector stat type.

Tests cover:
- Initialization with exact entry lists
- Content validation (dict structure, numeric values)
- Whole numeric observation frames
- Entries property
- balance_content (padding, overflow)
- reduce_duplicates (arithmetic mean per entry)
- reduced_content property guards
- Warning for unknown entries
- Type registration
- Edge cases (empty entries, non-numeric values)
- __str__ method
"""

import logging
import math
from typing import Any

import pytest

from src.parsing.gem5.types.base import StatTypeRegistry
from src.parsing.gem5.types.vector import Vector


class TestVectorInitialization:
    """Test Vector object creation and initialization."""

    def test_required_params_contains_entries(self) -> None:
        required = Vector.required_params

        assert "entries" in required
        assert len(required) == 1

    def test_init_with_entry_list(self) -> None:
        vector = Vector(entries=["entry0", "entry1", "entry2"])

        assert vector._repeat == 1
        assert vector.entries == ["entry0", "entry1", "entry2"]
        assert vector.content == {"entry0": [], "entry1": [], "entry2": []}
        assert vector.is_balanced is False
        assert vector.is_reduced is False

    def test_string_entry_schema_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="list of text entry names"):
            Vector(entries="entry0, entry1, entry2")

    def test_init_with_custom_repeat(self) -> None:
        vector = Vector(repeat=5, entries=["a", "b"])

        assert vector._repeat == 5
        assert vector.entries == ["a", "b"]

    def test_init_without_entries_raises(self) -> None:
        with pytest.raises(ValueError, match="VECTOR.*entries parameter is required"):
            Vector()

    def test_init_with_none_entries_raises(self) -> None:
        with pytest.raises(ValueError, match="VECTOR.*entries parameter is required"):
            Vector(entries=None)


class TestVectorEntriesProperty:
    """Test entries property getter."""

    def test_entries_property_returns_list(self) -> None:
        vector = Vector(entries=["e0", "e1", "e2"])

        result = vector.entries

        assert isinstance(result, list)
        assert result == ["e0", "e1", "e2"]


class TestVectorContentProperty:
    """Test defensive content snapshots and typed observation ingestion."""

    def test_content_getter(self) -> None:
        vector = Vector(entries=["e0", "e1"])

        result = vector.content

        assert isinstance(result, dict)
        assert result == {"e0": [], "e1": []}

    def test_complete_observation_frames_preserve_entry_alignment(self) -> None:
        vector = Vector(repeat=2, entries=["e0", "e1"])
        vector.add_observation({"e0": 10, "e1": 30})
        vector.add_observation({"e0": 20, "e1": 40})
        assert vector.content["e0"] == [10, 20]
        assert vector.content["e1"] == [30, 40]

    def test_add_observation_non_dict_raises(self) -> None:
        vector = Vector(entries=["e0"])

        with pytest.raises(TypeError, match="VECTOR.*numeric entry mapping"):
            vector.add_observation([1, 2, 3])

    def test_add_observation_non_string_keys_raises(self) -> None:
        vector = Vector(entries=["e0"])

        # Create object with non-stringable keys
        class NonStringable:
            def __str__(self) -> str:
                raise RuntimeError("Cannot convert")

        with pytest.raises(TypeError, match="VECTOR.*Entry names must be text"):
            vector.add_observation({NonStringable(): 3.0})

    def test_add_observation_non_numeric_list_values_raises(self) -> None:
        vector = Vector(entries=["e0"])

        with pytest.raises(TypeError, match="VECTOR.*one numeric measurement"):
            vector.add_observation({"e0": ["invalid", "values"]})

    def test_numeric_frame_values_are_retained(self) -> None:
        vector = Vector(entries=["e0", "e1"])

        vector.add_observation({"e0": 60.0, "e1": 20.0})

        assert vector.content["e0"] == [60.0]
        assert vector.content["e1"] == [20.0]

    def test_add_observation_with_single_value(self) -> None:
        vector = Vector(entries=["e0"])

        vector.add_observation({"e0": 42})

        assert vector.content["e0"] == [42]

    def test_add_observation_skips_unknown_entries(self, caplog: Any) -> None:

        vector = Vector(entries=["e0", "e1"])

        with caplog.at_level(logging.WARNING):
            vector.add_observation({"e0": 10.0, "e1": 20.0, "e2": 30.0})

        assert "e0" in vector.content
        assert "e1" in vector.content
        assert "e2" not in vector.content
        assert "Skipping unknown entries" in caplog.text
        assert "e2" in caplog.text

    def test_add_observation_no_warning_for_standard_stats(self, caplog: Any) -> None:

        vector = Vector(entries=["e0"])

        with caplog.at_level(logging.WARNING):
            vector.add_observation({"e0": 10.0, "total": 100.0, "mean": 50.0})

        assert "total" not in caplog.text
        assert "mean" not in caplog.text


class TestVectorBalanceContent:
    """Test logical missingness without adding unobserved frames."""

    def test_balance_empty_entries_records_missingness(self) -> None:
        vector = Vector(repeat=3, entries=["e0", "e1"])
        # Empty content

        vector.balance_content()

        assert vector.is_balanced is True
        assert vector.content == {"e0": [], "e1": []}
        assert vector.padded_count == vector.missing_measurement_count == 6
        vector.reduce_duplicates()
        assert set(vector.reduced_content) == {"e0", "e1"}
        assert all(math.isnan(value) for value in vector.reduced_content.values())

    def test_balance_partial_entries_retains_actual_frames(self) -> None:
        vector = Vector(repeat=4, entries=["e0", "e1"])
        vector.add_observation({"e0": 10, "e1": 30})
        vector.add_observation({"e0": 20})
        vector.balance_content()
        assert vector.content["e0"] == [10, 20]
        assert len(vector.content["e1"]) == 2
        assert vector.content["e1"][0] == 30
        assert math.isnan(vector.content["e1"][1])
        assert vector.padded_count == vector.missing_measurement_count == 5
        vector.reduce_duplicates()
        assert set(vector.reduced_content) == {"e0", "e1"}
        assert all(math.isnan(value) for value in vector.reduced_content.values())

    def test_balance_exact_count_no_change(self) -> None:
        vector = Vector(repeat=2, entries=["e0"])
        # Assign individually
        vector.add_observation({"e0": 10})
        vector.add_observation({"e0": 20})

        vector.balance_content()

        assert vector.content["e0"] == [10, 20]

    def test_balance_too_many_values_raises(self) -> None:
        vector = Vector(repeat=2, entries=["e0"])
        # Assign 3 values individually
        vector.add_observation({"e0": 10})
        vector.add_observation({"e0": 20})
        vector.add_observation({"e0": 30})

        with pytest.raises(RuntimeError, match="VECTOR.*More observations.*than expected"):
            vector.balance_content()


class TestVectorReduceDuplicates:
    """Test reduce_duplicates method (arithmetic mean per entry)."""

    # [test->req~ring5.ingestion.vector~1]

    def test_reduce_single_value_per_entry(self) -> None:
        vector = Vector(entries=["e0", "e1"])
        vector.add_observation({"e0": 100.0, "e1": 200.0})
        vector.balance_content()

        vector.reduce_duplicates()

        assert vector.is_reduced is True
        assert vector.reduced_content == {"e0": 100.0, "e1": 200.0}

    def test_reduce_multiple_values_calculates_mean(self) -> None:
        # Each frame contains the entries measured in one temporal dump.
        vector = Vector(repeat=3, entries=["e0", "e1"])
        vector.add_observation({"e0": 10, "e1": 100})
        vector.add_observation({"e0": 20, "e1": 200})
        vector.add_observation({"e0": 30, "e1": 300})
        vector.balance_content()

        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == 20.0
        assert vector.reduced_content["e1"] == 200.0

    def test_reduce_empty_entry_returns_nan(self) -> None:
        vector = Vector(entries=["e0", "e1"])
        vector.balance_content()  # Pads absent entries with NaN

        vector.reduce_duplicates()

        assert math.isnan(vector.reduced_content["e0"])
        assert math.isnan(vector.reduced_content["e1"])

    def test_reduce_integer_values(self) -> None:
        vector = Vector(repeat=2, entries=["e0"])
        vector.add_observation({"e0": 10})
        vector.add_observation({"e0": 20})
        vector.balance_content()

        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == 15.0

    def test_missing_entry_reduces_to_nan_after_balancing(self) -> None:
        vector = Vector(entries=["e0", "e1"])
        vector.add_observation({"e0": 10})
        vector.balance_content()
        vector.reduce_duplicates()
        assert math.isnan(vector.reduced_content["e1"])


class TestVectorReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        vector = Vector(entries=["e0"])
        vector.add_observation({"e0": 10.0})
        # Don't call balance_content()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = vector.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        vector = Vector(entries=["e0"])
        vector.add_observation({"e0": 10.0})
        vector.balance_content()
        # Don't call reduce_duplicates()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = vector.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        vector = Vector(entries=["e0"])
        vector.add_observation({"e0": 10.0})
        vector.balance_content()
        vector.reduce_duplicates()

        result = vector.reduced_content

        assert result == {"e0": 10.0}

    def test_access_reduced_content_property_directly(self) -> None:
        vector = Vector(entries=["e0"])
        vector.add_observation({"e0": 15})
        # Don't call balance or reduce

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = vector.reduced_content


class TestVectorTypeRegistration:
    """Test Vector is properly registered in the type system."""

    def test_vector_registered_with_decorator(self) -> None:
        registered_types = StatTypeRegistry.get_types()

        assert "vector" in registered_types

    def test_create_vector_via_registry(self) -> None:
        vector = StatTypeRegistry.create("vector", entries=["e0", "e1"])

        assert isinstance(vector, Vector)
        assert vector.entries == ["e0", "e1"]


class TestVectorStrMethod:
    """Test __str__ method for string representation."""

    def test_str_method_empty_content(self) -> None:
        vector = Vector(entries=["e0", "e1"])

        result = str(vector)

        assert "vector" in result
        assert "repeat=1" in result
        assert "balanced=False, reduced=False, padded=0" in result

    def test_str_method_with_content(self) -> None:
        vector = Vector(entries=["e0"])
        # One complete numeric source/dump frame.
        vector.add_observation({"e0": 60.0})

        result = str(vector)

        assert "vector" in result
        assert "repeat=1" in result
        assert "balanced=False, reduced=False, padded=0" in result


class TestVectorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero_values(self) -> None:
        vector = Vector(entries=["e0"])

        vector.add_observation({"e0": 0.0})
        vector.balance_content()
        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == 0.0

    def test_negative_values(self) -> None:
        vector = Vector(entries=["e0"])

        vector.add_observation({"e0": -60.0})
        vector.balance_content()
        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == -60.0

    def test_float_values(self) -> None:
        vector = Vector(entries=["e0"])

        vector.add_observation({"e0": 6.0})
        vector.balance_content()
        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == 6.0

    def test_mixed_numeric_types(self) -> None:
        vector = Vector(entries=["e0"])

        vector.add_observation({"e0": 60.5})

        assert vector.content["e0"] == [60.5]

    def test_empty_entries_list(self) -> None:
        vector = Vector(entries=[])

        assert vector.entries == []
        assert vector.content == {}

    def test_multiple_content_assignments_extend(self) -> None:
        vector = Vector(entries=["e0"])

        vector.add_observation({"e0": 10.0})
        vector.add_observation({"e0": 20.0})
        vector.add_observation({"e0": 30.0})

        assert vector.content["e0"] == [10, 20, 30]
