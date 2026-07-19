"""
Comprehensive tests for Vector stat type.

Tests cover:
- Initialization with entries (list and comma-separated string)
- Content validation (dict structure, numeric values)
- Content setting (dict assignment, aggregation)
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

    def test_init_with_entry_list(self) -> None:
        vector = Vector(entries=["entry0", "entry1", "entry2"])

        assert vector._repeat == 1
        assert vector.entries == ["entry0", "entry1", "entry2"]
        assert vector.content == {"entry0": [], "entry1": [], "entry2": []}
        assert vector.is_balanced is False
        assert vector.is_reduced is False

    def test_init_with_comma_separated_string(self) -> None:
        vector = Vector(entries="entry0, entry1, entry2")

        assert vector.entries == ["entry0", "entry1", "entry2"]
        assert "entry0" in vector.content
        assert "entry1" in vector.content

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

    def test_required_params_contains_entries(self) -> None:
        required = Vector.required_params

        assert "entries" in required
        assert len(required) == 1


class TestVectorEntriesProperty:
    """Test entries property getter."""

    def test_entries_property_returns_list(self) -> None:
        vector = Vector(entries=["e0", "e1", "e2"])

        result = vector.entries

        assert isinstance(result, list)
        assert result == ["e0", "e1", "e2"]


class TestVectorContentProperty:
    """Test content property getter and setter."""

    def test_content_getter(self) -> None:
        vector = Vector(entries=["e0", "e1"])

        result = vector.content

        assert isinstance(result, dict)
        assert result == {"e0": [], "e1": []}

    def test_content_setter_with_valid_dict(self) -> None:
        vector = Vector(entries=["e0", "e1"])

        vector.content = {"e0": 10}
        vector.content = {"e0": 20}
        vector.content = {"e1": 30}
        vector.content = {"e1": 40}

        assert vector.content["e0"] == [10, 20]
        assert vector.content["e1"] == [30, 40]

    def test_content_setter_non_dict_raises(self) -> None:
        vector = Vector(entries=["e0"])

        with pytest.raises(TypeError, match="VECTOR.*Content must be dict"):
            vector.content = [1, 2, 3]

    def test_content_setter_non_string_keys_raises(self) -> None:
        vector = Vector(entries=["e0"])

        # Create object with non-stringable keys
        class NonStringable:
            def __str__(self) -> str:
                raise RuntimeError("Cannot convert")

        with pytest.raises(TypeError, match="VECTOR.*Unable to convert keys to strings"):
            vector.content = {NonStringable(): [1, 2]}

    def test_content_setter_non_numeric_list_values_raises(self) -> None:
        vector = Vector(entries=["e0"])

        with pytest.raises(TypeError, match="VECTOR.*non-convertible to int or float"):
            vector.content = {"e0": ["invalid", "values"]}

    def test_content_setter_aggregates_list_values(self) -> None:
        vector = Vector(entries=["e0", "e1"])

        vector.content = {"e0": [10, 20, 30], "e1": [5, 15]}

        assert vector.content["e0"] == [60.0]
        assert vector.content["e1"] == [20.0]

    def test_content_setter_with_single_value(self) -> None:
        vector = Vector(entries=["e0"])

        vector.content = {"e0": 42}

        assert vector.content["e0"] == [42]

    def test_content_setter_skips_unknown_entries(self, caplog: Any) -> None:

        vector = Vector(entries=["e0", "e1"])

        with caplog.at_level(logging.WARNING):
            vector.content = {"e0": [10], "e1": [20], "e2": [30]}

        assert "e0" in vector.content
        assert "e1" in vector.content
        assert "e2" not in vector.content
        assert "not the same as configured entries" in caplog.text
        assert "e2" in caplog.text

    def test_content_setter_no_warning_for_standard_stats(self, caplog: Any) -> None:

        vector = Vector(entries=["e0"])

        with caplog.at_level(logging.WARNING):
            vector.content = {"e0": [10], "total": [100], "mean": [50]}

        assert "total" not in caplog.text
        assert "mean" not in caplog.text


class TestVectorBalanceContent:
    """Test balance_content method (padding per entry)."""

    def test_balance_empty_entries_pads_with_nan(self) -> None:
        vector = Vector(repeat=3, entries=["e0", "e1"])
        # Empty content

        vector.balance_content()

        assert vector.is_balanced is True
        assert len(vector.content["e0"]) == 3
        assert all(math.isnan(x) for x in vector.content["e0"])
        assert all(math.isnan(x) for x in vector.content["e1"])

    def test_balance_partial_entries_pads_remainder(self) -> None:
        vector = Vector(repeat=4, entries=["e0", "e1"])
        # Assign individually to avoid aggregation
        vector.content = {"e0": 10}
        vector.content = {"e0": 20}
        vector.content = {"e1": 30}

        vector.balance_content()

        assert vector.content["e0"][:2] == [10, 20]
        assert all(math.isnan(x) for x in vector.content["e0"][2:])
        assert vector.content["e1"][:1] == [30]
        assert all(math.isnan(x) for x in vector.content["e1"][1:])

    def test_balance_exact_count_no_change(self) -> None:
        vector = Vector(repeat=2, entries=["e0"])
        # Assign individually
        vector.content = {"e0": 10}
        vector.content = {"e0": 20}

        vector.balance_content()

        assert vector.content["e0"] == [10, 20]

    def test_balance_too_many_values_raises(self) -> None:
        vector = Vector(repeat=2, entries=["e0"])
        # Assign 3 values individually
        vector.content = {"e0": 10}
        vector.content = {"e0": 20}
        vector.content = {"e0": 30}

        with pytest.raises(RuntimeError, match="VECTOR.*more values than expected"):
            vector.balance_content()


class TestVectorReduceDuplicates:
    """Test reduce_duplicates method (arithmetic mean per entry)."""

    # [test->req~ring5.ingestion.vector~1]

    def test_reduce_single_value_per_entry(self) -> None:
        vector = Vector(entries=["e0", "e1"])
        vector.content = {"e0": [100], "e1": [200]}
        vector.balance_content()

        vector.reduce_duplicates()

        assert vector.is_reduced is True
        assert vector.reduced_content == {"e0": 100.0, "e1": 200.0}

    def test_reduce_multiple_values_calculates_mean(self) -> None:
        # in a single assignment, so individual assignments simulate dumps)
        vector = Vector(repeat=3, entries=["e0", "e1"])
        vector.content = {"e0": 10, "e1": 100}
        vector.content = {"e0": 20, "e1": 200}
        vector.content = {"e0": 30, "e1": 300}
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
        vector.content = {"e0": 10}
        vector.content = {"e0": 20}
        vector.balance_content()

        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == 15.0

    def test_reduce_with_truly_empty_entry(self) -> None:
        vector = Vector(entries=["e0", "e1"])
        # Only set content for e0, leave e1 truly empty
        vector.content = {"e0": 10}
        # e1 remains []

        vector.reduce_duplicates()

        assert math.isnan(object.__getattribute__(vector, "_reduced_content")["e1"])


class TestVectorReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        vector = Vector(entries=["e0"])
        vector.content = {"e0": [10]}
        # Don't call balance_content()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = vector.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        vector = Vector(entries=["e0"])
        vector.content = {"e0": [10]}
        vector.balance_content()
        # Don't call reduce_duplicates()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = vector.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        vector = Vector(entries=["e0"])
        vector.content = {"e0": [10]}
        vector.balance_content()
        vector.reduce_duplicates()

        result = vector.reduced_content

        assert result == {"e0": 10.0}

    def test_access_reduced_content_property_directly(self) -> None:
        vector = Vector(entries=["e0"])
        vector.content = {"e0": 15}
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

        assert "Vector" in result
        assert "e0" in result
        assert "e1" in result

    def test_str_method_with_content(self) -> None:
        vector = Vector(entries=["e0"])
        # List values are aggregated: [10, 20, 30] → 60.0
        vector.content = {"e0": [10, 20, 30]}

        result = str(vector)

        assert "Vector" in result
        assert "60" in result or "60.0" in result


class TestVectorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero_values(self) -> None:
        vector = Vector(entries=["e0"])

        vector.content = {"e0": [0, 0, 0]}
        vector.balance_content()
        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == 0.0

    def test_negative_values(self) -> None:
        vector = Vector(entries=["e0"])

        vector.content = {"e0": [-10, -20, -30]}
        vector.balance_content()
        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == -60.0

    def test_float_values(self) -> None:
        vector = Vector(entries=["e0"])

        vector.content = {"e0": [3.14, 2.86]}
        vector.balance_content()
        vector.reduce_duplicates()

        assert vector.reduced_content["e0"] == 6.0

    def test_mixed_numeric_types(self) -> None:
        vector = Vector(entries=["e0"])

        vector.content = {"e0": [10, 20.5, "30"]}

        assert vector.content["e0"] == [60.5]

    def test_empty_entries_list(self) -> None:
        vector = Vector(entries=[])

        assert vector.entries == []
        assert vector.content == {}

    def test_multiple_content_assignments_extend(self) -> None:
        vector = Vector(entries=["e0"])

        vector.content = {"e0": [10]}
        vector.content = {"e0": [20]}
        vector.content = {"e0": [30]}

        assert vector.content["e0"] == [10, 20, 30]
