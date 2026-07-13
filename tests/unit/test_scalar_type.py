"""
Comprehensive tests for Scalar stat type.

Exercises scalar parsing and reduction behavior:
- Fixture-first design
- AAA pattern (Arrange-Act-Assert)
- Parametrization for multiple scenarios
- Testing all edge cases and error paths
"""

import math

import pytest

from src.parsing.gem5.types.scalar import Scalar


class TestScalarInitialization:
    """Test Scalar type initialization."""

    def test_init_default_repeat(self) -> None:
        # Arrange & Act
        scalar = Scalar()

        # Assert
        assert scalar.repeat == 1
        assert scalar.content == []
        assert scalar.is_balanced is False
        assert scalar.is_reduced is False

    def test_init_with_custom_repeat(self) -> None:
        # Arrange & Act
        scalar = Scalar(repeat=5)

        # Assert
        assert scalar.repeat == 5

    def test_required_params_empty(self) -> None:
        # Arrange & Act & Assert
        assert Scalar.required_params == []


class TestScalarValidateContent:
    """Test Scalar content validation."""

    def test_validate_integer(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act & Assert - Should not raise
        scalar._validate_content(42)

    def test_validate_float(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act & Assert - Should not raise
        scalar._validate_content(3.14)

    def test_validate_numeric_string(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act & Assert - Should not raise
        scalar._validate_content("123")
        scalar._validate_content("45.67")

    def test_validate_non_numeric_string_raises(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act & Assert
        with pytest.raises(TypeError, match="non-convertible to float or int"):
            scalar._validate_content("not_a_number")

    def test_validate_none_raises(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act & Assert
        with pytest.raises(TypeError, match="non-convertible"):
            scalar._validate_content(None)

    def test_validate_list_raises(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act & Assert
        with pytest.raises(TypeError):
            scalar._validate_content([1, 2, 3])


class TestScalarSetContent:
    """Test Scalar content setting."""

    def test_set_content_int(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(100)

        # Assert - integers are stored as floats
        assert len(scalar.content) == 1
        assert scalar.content[0] == 100.0

    def test_set_content_float(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(3.14159)

        # Assert - float precision is preserved (no int() truncation)
        assert len(scalar.content) == 1
        assert scalar.content[0] == pytest.approx(3.14159)

    def test_set_content_numeric_string(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content("42")

        # Assert
        assert scalar.content[0] == 42.0

    def test_set_content_float_string(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content("2.718")

        # Assert
        assert scalar.content[0] == 2.718

    def test_set_content_multiple_values(self) -> None:
        # Arrange
        scalar = Scalar(repeat=3)

        # Act
        scalar._set_content(10)
        scalar._set_content(20)
        scalar._set_content(30)

        # Assert
        assert scalar.content == [10.0, 20.0, 30.0]


class TestScalarContentProperty:
    """Test Scalar content property (via base class)."""

    def test_content_setter_validates(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar.content = 42

        # Assert
        assert scalar.content[0] == 42.0  # type: ignore[index]  # __setattr__ masks property type

    def test_content_setter_invalid_value_raises(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act & Assert
        with pytest.raises(TypeError):
            scalar.content = "invalid"

    def test_content_getter(self) -> None:
        # Arrange
        scalar = Scalar()
        scalar._set_content(100)

        # Act
        result = scalar.content

        # Assert
        assert result == [100.0]


class TestScalarReduceDuplicates:
    """Test Scalar reduce_duplicates (arithmetic mean)."""

    def test_reduce_single_value(self) -> None:
        # Arrange
        scalar = Scalar(repeat=1)
        scalar._set_content(42)
        scalar.balance_content()

        # Act
        scalar.reduce_duplicates()

        # Assert
        assert scalar.is_reduced is True
        assert scalar.reduced_content == 42.0

    def test_reduce_multiple_values_mean(self) -> None:
        # Arrange
        scalar = Scalar(repeat=3)
        scalar._set_content(10)
        scalar._set_content(20)
        scalar._set_content(30)
        scalar.balance_content()

        # Act
        scalar.reduce_duplicates()

        # Assert
        # Mean: (10 + 20 + 30) / 3 = 20.0
        assert scalar.reduced_content == 20.0

    def test_reduce_empty_content(self) -> None:
        # Arrange
        scalar = Scalar()
        # Don't call balance_content() - that would pad with zeros

        # Act
        scalar.reduce_duplicates()

        # Assert - truly empty content returns NaN (float)
        assert math.isnan(object.__getattribute__(scalar, "_reduced_content"))

    def test_reduce_with_integer_division(self) -> None:
        # Arrange
        scalar = Scalar(repeat=2)
        scalar._set_content(100)
        scalar._set_content(200)
        scalar.balance_content()

        # Act
        scalar.reduce_duplicates()

        # Assert
        assert scalar.reduced_content == 150.0

    def test_reduce_preserves_float_precision(self) -> None:
        # Arrange - fractional values must NOT be truncated via int()
        scalar = Scalar(repeat=2)
        scalar._set_content(10.9)
        scalar._set_content(20.1)
        scalar.balance_content()

        # Act
        scalar.reduce_duplicates()

        # Assert: (10.9 + 20.1) / 2 = 15.5
        assert scalar.reduced_content == pytest.approx(15.5)


class TestScalarBalanceContent:
    """Test Scalar balance_content (via base class)."""

    def test_balance_pads_with_nan(self) -> None:
        # Arrange
        scalar = Scalar(repeat=5)
        scalar._set_content(10)
        scalar._set_content(20)

        # Act
        scalar.balance_content()

        # Assert - missing dumps are NaN (not a fabricated 0), counted for traceability
        assert scalar.is_balanced is True
        assert len(scalar.content) == 5
        assert scalar.content[:2] == [10.0, 20.0]
        assert all(math.isnan(x) for x in scalar.content[2:])
        assert scalar.padded_count == 3

    def test_balance_exact_count_no_change(self) -> None:
        # Arrange
        scalar = Scalar(repeat=3)
        scalar._set_content(1)
        scalar._set_content(2)
        scalar._set_content(3)

        # Act
        scalar.balance_content()

        # Assert
        assert scalar.content == [1.0, 2.0, 3.0]

    def test_balance_too_many_values_raises(self) -> None:
        # Arrange
        scalar = Scalar(repeat=2)
        scalar._set_content(1)
        scalar._set_content(2)
        scalar._set_content(3)  # One too many

        # Act & Assert
        with pytest.raises(RuntimeError, match="More values .* than expected"):
            scalar.balance_content()


class TestScalarReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        # Arrange
        scalar = Scalar()
        scalar._set_content(10)

        # Act & Assert
        with pytest.raises(AttributeError, match="before calling balance_content"):
            _ = scalar.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        # Arrange
        scalar = Scalar()
        scalar._set_content(10)
        scalar.balance_content()

        # Act & Assert
        with pytest.raises(AttributeError, match="before calling.*reduce_duplicates"):
            _ = scalar.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        # Arrange
        scalar = Scalar()
        scalar._set_content(42)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Act
        result = scalar.reduced_content

        # Assert
        assert result == 42.0


class TestScalarTypeRegistration:
    """Test Scalar type registration."""

    def test_scalar_registered_with_decorator(self) -> None:
        # Arrange & Act
        from src.parsing.gem5.types.base import StatTypeRegistry

        # Assert
        assert "scalar" in StatTypeRegistry.get_types()

    def test_create_scalar_via_registry(self) -> None:
        # Arrange
        from src.parsing.gem5.types.base import StatTypeRegistry

        # Act
        scalar = StatTypeRegistry.create("scalar", repeat=2)

        # Assert
        assert isinstance(scalar, Scalar)
        assert scalar.repeat == 2


class TestScalarEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_value(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(0)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Assert
        assert scalar.reduced_content == 0.0

    def test_negative_value(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(-42)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Assert
        assert scalar.reduced_content == -42.0

    def test_very_large_value(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(1e100)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Assert
        assert scalar.reduced_content == 1e100

    def test_scientific_notation_string(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content("1.5e10")

        # Assert
        assert scalar.content[0] == 1.5e10

    def test_entries_property_returns_none(self) -> None:
        # Arrange
        scalar = Scalar()

        # Act
        result = scalar.entries

        # Assert
        assert result is None
