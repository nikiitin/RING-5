"""
Comprehensive tests for Scalar stat type.

Following Rule 004 (QA Testing Mastery):
- Fixture-first design
- AAA pattern (Arrange-Act-Assert)
- Parametrization for multiple scenarios
- Testing all edge cases and error paths
"""

import pytest

from src.core.parsing.types.scalar import Scalar


class TestScalarInitialization:
    """Test Scalar type initialization."""

    def test_init_default_repeat(self):
        # Arrange & Act
        scalar = Scalar()

        # Assert
        assert scalar.repeat == 1
        assert scalar._content == []
        assert scalar._balanced is False
        assert scalar._reduced is False

    def test_init_with_custom_repeat(self):
        # Arrange & Act
        scalar = Scalar(repeat=5)

        # Assert
        assert scalar.repeat == 5

    def test_required_params_empty(self):
        # Arrange & Act & Assert
        assert Scalar.required_params == []


class TestScalarValidateContent:
    """Test Scalar content validation."""

    def test_validate_integer(self):
        # Arrange
        scalar = Scalar()

        # Act & Assert - Should not raise
        scalar._validate_content(42)

    def test_validate_float(self):
        # Arrange
        scalar = Scalar()

        # Act & Assert - Should not raise
        scalar._validate_content(3.14)

    def test_validate_numeric_string(self):
        # Arrange
        scalar = Scalar()

        # Act & Assert - Should not raise
        scalar._validate_content("123")
        scalar._validate_content("45.67")

    def test_validate_non_numeric_string_raises(self):
        # Arrange
        scalar = Scalar()

        # Act & Assert
        with pytest.raises(TypeError, match="non-convertible to float or int"):
            scalar._validate_content("not_a_number")

    def test_validate_none_raises(self):
        # Arrange
        scalar = Scalar()

        # Act & Assert
        with pytest.raises(TypeError, match="non-convertible"):
            scalar._validate_content(None)

    def test_validate_list_raises(self):
        # Arrange
        scalar = Scalar()

        # Act & Assert
        with pytest.raises(TypeError):
            scalar._validate_content([1, 2, 3])


class TestScalarSetContent:
    """Test Scalar content setting."""

    def test_set_content_int(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(100)

        # Assert - integers are stored as floats
        assert len(scalar._content) == 1
        assert scalar._content[0] == 100.0

    def test_set_content_float(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(3.14159)

        # Assert - floats are truncated via int() then back to float
        assert len(scalar._content) == 1
        assert scalar._content[0] == 3.0

    def test_set_content_numeric_string(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content("42")

        # Assert
        assert scalar._content[0] == 42.0

    def test_set_content_float_string(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content("2.718")

        # Assert
        assert scalar._content[0] == 2.718

    def test_set_content_multiple_values(self):
        # Arrange
        scalar = Scalar(repeat=3)

        # Act
        scalar._set_content(10)
        scalar._set_content(20)
        scalar._set_content(30)

        # Assert
        assert scalar._content == [10.0, 20.0, 30.0]


class TestScalarContentProperty:
    """Test Scalar content property (via base class)."""

    def test_content_setter_validates(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar.content = 42

        # Assert
        assert scalar._content[0] == 42.0

    def test_content_setter_invalid_value_raises(self):
        # Arrange
        scalar = Scalar()

        # Act & Assert
        with pytest.raises(TypeError):
            scalar.content = "invalid"

    def test_content_getter(self):
        # Arrange
        scalar = Scalar()
        scalar._set_content(100)

        # Act
        result = scalar.content

        # Assert
        assert result == [100.0]


class TestScalarReduceDuplicates:
    """Test Scalar reduce_duplicates (arithmetic mean)."""

    def test_reduce_single_value(self):
        # Arrange
        scalar = Scalar(repeat=1)
        scalar._set_content(42)
        scalar.balance_content()

        # Act
        scalar.reduce_duplicates()

        # Assert
        assert scalar._reduced is True
        assert scalar._reduced_content == 42.0

    def test_reduce_multiple_values_mean(self):
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
        assert scalar._reduced_content == 20.0

    def test_reduce_empty_content(self):
        # Arrange
        scalar = Scalar()
        # Don't call balance_content() - that would pad with zeros

        # Act
        scalar.reduce_duplicates()

        # Assert - truly empty content returns "NA"
        assert scalar._reduced_content == "NA"

    def test_reduce_with_integer_division(self):
        # Arrange
        scalar = Scalar(repeat=2)
        scalar._set_content(100)
        scalar._set_content(200)
        scalar.balance_content()

        # Act
        scalar.reduce_duplicates()

        # Assert
        assert scalar._reduced_content == 150.0

    def test_reduce_uses_int_conversion(self):
        # Arrange - Test that reduce uses int() before summing
        scalar = Scalar(repeat=2)
        scalar._set_content(10.9)
        scalar._set_content(20.1)
        scalar.balance_content()

        # Act
        scalar.reduce_duplicates()

        # Assert
        # Implementation: int(10.9) + int(20.1) = 10 + 20 = 30, / 2 = 15.0
        assert scalar._reduced_content == 15.0


class TestScalarBalanceContent:
    """Test Scalar balance_content (via base class)."""

    def test_balance_pads_with_zeros(self):
        # Arrange
        scalar = Scalar(repeat=5)
        scalar._set_content(10)
        scalar._set_content(20)

        # Act
        scalar.balance_content()

        # Assert
        assert scalar._balanced is True
        assert len(scalar._content) == 5
        assert scalar._content == [10.0, 20.0, 0, 0, 0]

    def test_balance_exact_count_no_change(self):
        # Arrange
        scalar = Scalar(repeat=3)
        scalar._set_content(1)
        scalar._set_content(2)
        scalar._set_content(3)

        # Act
        scalar.balance_content()

        # Assert
        assert scalar._content == [1.0, 2.0, 3.0]

    def test_balance_too_many_values_raises(self):
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

    def test_access_reduced_content_before_balance_raises(self):
        # Arrange
        scalar = Scalar()
        scalar._set_content(10)

        # Act & Assert
        with pytest.raises(AttributeError, match="before calling balance_content"):
            _ = scalar.reduced_content

    def test_access_reduced_content_before_reduce_raises(self):
        # Arrange
        scalar = Scalar()
        scalar._set_content(10)
        scalar.balance_content()

        # Act & Assert
        with pytest.raises(AttributeError, match="before calling.*reduce_duplicates"):
            _ = scalar.reduced_content

    def test_access_reduced_content_after_both_succeeds(self):
        # Arrange
        scalar = Scalar()
        scalar._set_content(42)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Act
        result = scalar.reduced_content

        # Assert
        assert result == 42.0

    def test_access_via_reducedContent_alias(self):
        # Arrange
        scalar = Scalar()
        scalar._set_content(100)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Act
        result = scalar.reducedContent

        # Assert
        assert result == 100.0


class TestScalarBackwardCompatibility:
    """Test backward compatibility aliases."""

    def test_balanceContent_alias(self):
        # Arrange
        scalar = Scalar(repeat=3)
        scalar._set_content(10)

        # Act
        scalar.balanceContent()

        # Assert
        assert scalar._balanced is True
        assert len(scalar._content) == 3

    def test_reduceDuplicates_alias(self):
        # Arrange
        scalar = Scalar()
        scalar._set_content(50)
        scalar.balance_content()

        # Act
        scalar.reduceDuplicates()

        # Assert
        assert scalar._reduced is True
        assert scalar._reduced_content == 50.0


class TestScalarTypeRegistration:
    """Test Scalar type registration."""

    def test_scalar_registered_with_decorator(self):
        # Arrange & Act
        from src.core.parsing.types.base import StatTypeRegistry

        # Assert
        assert "scalar" in StatTypeRegistry.get_types()

    def test_create_scalar_via_registry(self):
        # Arrange
        from src.core.parsing.types.base import StatTypeRegistry

        # Act
        scalar = StatTypeRegistry.create("scalar", repeat=2)

        # Assert
        assert isinstance(scalar, Scalar)
        assert scalar.repeat == 2


class TestScalarEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_value(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(0)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Assert
        assert scalar._reduced_content == 0.0

    def test_negative_value(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(-42)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Assert
        assert scalar._reduced_content == -42.0

    def test_very_large_value(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content(1e100)
        scalar.balance_content()
        scalar.reduce_duplicates()

        # Assert
        assert scalar._reduced_content == 1e100

    def test_scientific_notation_string(self):
        # Arrange
        scalar = Scalar()

        # Act
        scalar._set_content("1.5e10")

        # Assert
        assert scalar._content[0] == 1.5e10

    def test_entries_property_returns_none(self):
        # Arrange
        scalar = Scalar()

        # Act
        result = scalar.entries

        # Assert
        assert result is None
