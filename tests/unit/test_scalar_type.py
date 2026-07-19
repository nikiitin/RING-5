"""
Comprehensive tests for Scalar stat type.

Exercises scalar parsing and reduction behavior:
- Fixture-first design
- Parametrization for multiple scenarios
- Testing all edge cases and error paths
"""

import math

import pytest

from src.parsing.gem5.types.scalar import Scalar


class TestScalarInitialization:
    """Test Scalar type initialization."""

    def test_init_default_repeat(self) -> None:
        scalar = Scalar()

        assert scalar.repeat == 1
        assert scalar.content == []
        assert scalar.is_balanced is False
        assert scalar.is_reduced is False

    def test_init_with_custom_repeat(self) -> None:
        scalar = Scalar(repeat=5)

        assert scalar.repeat == 5

    def test_required_params_empty(self) -> None:
        assert Scalar.required_params == []


class TestScalarValidateContent:
    """Test Scalar content validation."""

    def test_validate_integer(self) -> None:
        scalar = Scalar()

        scalar._validate_content(42)

    def test_validate_float(self) -> None:
        scalar = Scalar()

        scalar._validate_content(3.14)

    def test_validate_numeric_string(self) -> None:
        scalar = Scalar()

        scalar._validate_content("123")
        scalar._validate_content("45.67")

    def test_validate_non_numeric_string_raises(self) -> None:
        scalar = Scalar()

        with pytest.raises(TypeError, match="non-convertible to float or int"):
            scalar._validate_content("not_a_number")

    def test_validate_none_raises(self) -> None:
        scalar = Scalar()

        with pytest.raises(TypeError, match="non-convertible"):
            scalar._validate_content(None)

    def test_validate_list_raises(self) -> None:
        scalar = Scalar()

        with pytest.raises(TypeError):
            scalar._validate_content([1, 2, 3])


class TestScalarSetContent:
    """Test Scalar content setting."""

    def test_set_content_int(self) -> None:
        scalar = Scalar()

        scalar._set_content(100)

        assert len(scalar.content) == 1
        assert scalar.content[0] == 100.0

    def test_set_content_float(self) -> None:
        scalar = Scalar()

        scalar._set_content(3.14159)

        assert len(scalar.content) == 1
        assert scalar.content[0] == pytest.approx(3.14159)

    def test_set_content_numeric_string(self) -> None:
        scalar = Scalar()

        scalar._set_content("42")

        assert scalar.content[0] == 42.0

    def test_set_content_float_string(self) -> None:
        scalar = Scalar()

        scalar._set_content("2.718")

        assert scalar.content[0] == 2.718

    def test_set_content_multiple_values(self) -> None:
        scalar = Scalar(repeat=3)

        scalar._set_content(10)
        scalar._set_content(20)
        scalar._set_content(30)

        assert scalar.content == [10.0, 20.0, 30.0]


class TestScalarContentProperty:
    """Test Scalar content property (via base class)."""

    def test_content_setter_validates(self) -> None:
        scalar = Scalar()

        scalar.content = 42

        assert scalar.content[0] == 42.0  # type: ignore[index]  # __setattr__ masks property type

    def test_content_setter_invalid_value_raises(self) -> None:
        scalar = Scalar()

        with pytest.raises(TypeError):
            scalar.content = "invalid"

    def test_content_getter(self) -> None:
        scalar = Scalar()
        scalar._set_content(100)

        result = scalar.content

        assert result == [100.0]


class TestScalarReduceDuplicates:
    """Test Scalar reduce_duplicates (arithmetic mean)."""

    # [test->req~ring5.ingestion.scalar~1]

    def test_reduce_single_value(self) -> None:
        scalar = Scalar(repeat=1)
        scalar._set_content(42)
        scalar.balance_content()

        scalar.reduce_duplicates()

        assert scalar.is_reduced is True
        assert scalar.reduced_content == 42.0

    def test_reduce_multiple_values_mean(self) -> None:
        scalar = Scalar(repeat=3)
        scalar._set_content(10)
        scalar._set_content(20)
        scalar._set_content(30)
        scalar.balance_content()

        scalar.reduce_duplicates()

        # Mean: (10 + 20 + 30) / 3 = 20.0
        assert scalar.reduced_content == 20.0

    def test_reduce_empty_content(self) -> None:
        scalar = Scalar()
        # Don't call balance_content() - that would pad with zeros

        scalar.reduce_duplicates()

        assert math.isnan(object.__getattribute__(scalar, "_reduced_content"))

    def test_reduce_with_integer_division(self) -> None:
        scalar = Scalar(repeat=2)
        scalar._set_content(100)
        scalar._set_content(200)
        scalar.balance_content()

        scalar.reduce_duplicates()

        assert scalar.reduced_content == 150.0

    def test_reduce_preserves_float_precision(self) -> None:
        scalar = Scalar(repeat=2)
        scalar._set_content(10.9)
        scalar._set_content(20.1)
        scalar.balance_content()

        scalar.reduce_duplicates()

        assert scalar.reduced_content == pytest.approx(15.5)


class TestScalarBalanceContent:
    """Test Scalar balance_content (via base class)."""

    def test_balance_pads_with_nan(self) -> None:
        scalar = Scalar(repeat=5)
        scalar._set_content(10)
        scalar._set_content(20)

        scalar.balance_content()

        assert scalar.is_balanced is True
        assert len(scalar.content) == 5
        assert scalar.content[:2] == [10.0, 20.0]
        assert all(math.isnan(x) for x in scalar.content[2:])
        assert scalar.padded_count == 3

    def test_balance_exact_count_no_change(self) -> None:
        scalar = Scalar(repeat=3)
        scalar._set_content(1)
        scalar._set_content(2)
        scalar._set_content(3)

        scalar.balance_content()

        assert scalar.content == [1.0, 2.0, 3.0]

    def test_balance_too_many_values_raises(self) -> None:
        scalar = Scalar(repeat=2)
        scalar._set_content(1)
        scalar._set_content(2)
        scalar._set_content(3)  # One too many

        with pytest.raises(RuntimeError, match="More values .* than expected"):
            scalar.balance_content()


class TestScalarReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        scalar = Scalar()
        scalar._set_content(10)

        with pytest.raises(AttributeError, match="before calling balance_content"):
            _ = scalar.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        scalar = Scalar()
        scalar._set_content(10)
        scalar.balance_content()

        with pytest.raises(AttributeError, match="before calling.*reduce_duplicates"):
            _ = scalar.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        scalar = Scalar()
        scalar._set_content(42)
        scalar.balance_content()
        scalar.reduce_duplicates()

        result = scalar.reduced_content

        assert result == 42.0


class TestScalarTypeRegistration:
    """Test Scalar type registration."""

    def test_scalar_registered_with_decorator(self) -> None:
        from src.parsing.gem5.types.base import StatTypeRegistry

        assert "scalar" in StatTypeRegistry.get_types()

    def test_create_scalar_via_registry(self) -> None:
        from src.parsing.gem5.types.base import StatTypeRegistry

        scalar = StatTypeRegistry.create("scalar", repeat=2)

        assert isinstance(scalar, Scalar)
        assert scalar.repeat == 2


class TestScalarEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_value(self) -> None:
        scalar = Scalar()

        scalar._set_content(0)
        scalar.balance_content()
        scalar.reduce_duplicates()

        assert scalar.reduced_content == 0.0

    def test_negative_value(self) -> None:
        scalar = Scalar()

        scalar._set_content(-42)
        scalar.balance_content()
        scalar.reduce_duplicates()

        assert scalar.reduced_content == -42.0

    def test_very_large_value(self) -> None:
        scalar = Scalar()

        scalar._set_content(1e100)
        scalar.balance_content()
        scalar.reduce_duplicates()

        assert scalar.reduced_content == 1e100

    def test_scientific_notation_string(self) -> None:
        scalar = Scalar()

        scalar._set_content("1.5e10")

        assert scalar.content[0] == 1.5e10

    def test_entries_property_returns_none(self) -> None:
        scalar = Scalar()

        result = scalar.entries

        assert result is None
