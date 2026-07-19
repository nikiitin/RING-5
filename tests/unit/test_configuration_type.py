"""
Comprehensive tests for Configuration stat type.

Tests cover:
- Initialization with onEmpty parameter
- Content validation (string conversion)
- Content setting and storage
- balance_content (always balanced, no padding)
- reduce_duplicates (first value or onEmpty)
- onEmpty property
- Type registration
- Edge cases (None, empty string, numeric types)
- __str__ method
"""

import pytest

from src.parsing.gem5.types.base import StatTypeRegistry
from src.parsing.gem5.types.configuration import Configuration


class TestConfigurationInitialization:
    """Test Configuration object creation and initialization."""

    def test_init_with_on_empty(self) -> None:
        config = Configuration(onEmpty="default_value")

        assert config._repeat == 1
        assert config._on_empty == "default_value"
        assert config.content == []
        assert config.is_balanced is False
        assert config.is_reduced is False

    def test_init_with_custom_repeat_and_on_empty(self) -> None:
        config = Configuration(repeat=5, onEmpty="fallback")

        assert config._repeat == 5
        assert config._on_empty == "fallback"

    def test_init_on_empty_defaults_to_none_string_if_not_provided(self) -> None:
        config = Configuration(onEmpty=None)

        assert config._on_empty == "None"

    def test_required_params_contains_on_empty(self) -> None:
        required = Configuration.required_params

        assert "onEmpty" in required
        assert len(required) == 1


class TestConfigurationOnEmptyProperty:
    """Test onEmpty property getter."""

    # [test->req~ring5.ingestion.configuration-fallbacks~1]

    def test_on_empty_property_returns_string(self) -> None:
        config = Configuration(onEmpty="test_default")

        result = config.onEmpty

        assert result == "test_default"
        assert isinstance(result, str)

    def test_on_empty_property_converts_to_string(self) -> None:
        config = Configuration(onEmpty=123)

        result = config.onEmpty

        assert result == "123"
        assert isinstance(result, str)


class TestConfigurationValidateContent:
    """Test _validate_content method for string conversion validation."""

    def test_validate_string(self) -> None:
        config = Configuration(onEmpty="default")

        config._validate_content("test_value")

    def test_validate_integer(self) -> None:
        config = Configuration(onEmpty="default")

        config._validate_content(42)

    def test_validate_float(self) -> None:
        config = Configuration(onEmpty="default")

        config._validate_content(3.14159)

    def test_validate_none(self) -> None:
        config = Configuration(onEmpty="default")

        config._validate_content(None)

    def test_validate_boolean(self) -> None:
        config = Configuration(onEmpty="default")

        config._validate_content(True)
        config._validate_content(False)

    def test_validate_list(self) -> None:
        config = Configuration(onEmpty="default")

        config._validate_content([1, 2, 3])

    def test_validate_non_stringable_object_raises(self) -> None:
        config = Configuration(onEmpty="default")

        # Create an object that raises when stringified
        class NonStringable:
            def __str__(self) -> str:
                raise RuntimeError("Cannot convert to string")

        obj = NonStringable()

        with pytest.raises(RuntimeError, match="Cannot convert to string"):
            config._validate_content(obj)


class TestConfigurationSetContent:
    """Test _set_content method for storing values."""

    def test_set_content_string(self) -> None:
        config = Configuration(onEmpty="default")

        config._set_content("benchmark_name")

        assert len(config.content) == 1
        assert config.content[0] == "benchmark_name"

    def test_set_content_integer_converts_to_string(self) -> None:
        config = Configuration(onEmpty="default")

        config._set_content(12345)

        assert config.content[0] == "12345"
        assert isinstance(config.content[0], str)

    def test_set_content_float_converts_to_string(self) -> None:
        config = Configuration(onEmpty="default")

        config._set_content(3.14159)

        assert config.content[0] == "3.14159"
        assert isinstance(config.content[0], str)

    def test_set_content_none_converts_to_string(self) -> None:
        config = Configuration(onEmpty="default")

        config._set_content(None)

        assert config.content[0] == "None"

    def test_set_content_multiple_values(self) -> None:
        config = Configuration(repeat=3, onEmpty="default")

        config._set_content("value1")
        config._set_content("value2")
        config._set_content("value3")

        assert len(config.content) == 3
        assert config.content == ["value1", "value2", "value3"]


class TestConfigurationBalanceContent:
    """Test balance_content method (always balanced, no padding)."""

    # [test->req~ring5.ingestion.configuration~1]

    def test_balance_empty_content_no_padding(self) -> None:
        config = Configuration(onEmpty="default")

        config.balance_content()

        assert config.is_balanced is True
        assert config.content == []

    def test_balance_with_content_no_change(self) -> None:
        config = Configuration(repeat=3, onEmpty="default")
        config._set_content("val1")
        config._set_content("val2")

        config.balance_content()

        assert config.is_balanced is True
        assert len(config.content) == 2

    def test_balance_more_values_than_repeat_no_error(self) -> None:
        config = Configuration(repeat=1, onEmpty="default")
        config._set_content("val1")
        config._set_content("val2")
        config._set_content("val3")

        config.balance_content()
        assert config.is_balanced is True
        assert len(config.content) == 3


class TestConfigurationReduceDuplicates:
    """Test reduce_duplicates method (returns first value or onEmpty)."""

    def test_reduce_with_empty_content_returns_on_empty(self) -> None:
        config = Configuration(onEmpty="default_value")
        config.balance_content()

        config.reduce_duplicates()

        assert config.is_reduced is True
        assert config.reduced_content == "default_value"

    def test_reduce_with_single_value_returns_that_value(self) -> None:
        config = Configuration(onEmpty="default")
        config._set_content("only_value")
        config.balance_content()

        config.reduce_duplicates()

        assert config.is_reduced is True
        assert config.reduced_content == "only_value"

    def test_reduce_with_multiple_values_returns_first(self) -> None:
        config = Configuration(repeat=3, onEmpty="default")
        config._set_content("first")
        config._set_content("second")
        config._set_content("third")
        config.balance_content()

        config.reduce_duplicates()

        assert config.is_reduced is True
        assert config.reduced_content == "first"

    def test_reduce_marks_reduced_flag(self) -> None:
        config = Configuration(onEmpty="default")
        config._set_content("value")
        config.balance_content()

        config.reduce_duplicates()

        assert config.is_reduced is True


class TestConfigurationReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        config = Configuration(onEmpty="default")
        config._set_content("value")
        # Don't call balance_content()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = config.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        config = Configuration(onEmpty="default")
        config._set_content("value")
        config.balance_content()
        # Don't call reduce_duplicates()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = config.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        config = Configuration(onEmpty="default")
        config._set_content("test_value")
        config.balance_content()
        config.reduce_duplicates()

        result = config.reduced_content

        assert result == "test_value"


class TestConfigurationTypeRegistration:
    """Test Configuration is properly registered in the type system."""

    def test_configuration_registered_with_decorator(self) -> None:
        registered_types = StatTypeRegistry.get_types()

        assert "configuration" in registered_types

    def test_create_configuration_via_registry(self) -> None:
        config = StatTypeRegistry.create("configuration", onEmpty="test")

        assert isinstance(config, Configuration)
        assert config._on_empty == "test"


class TestConfigurationStrMethod:
    """Test __str__ method for string representation."""

    def test_str_method_empty_content(self) -> None:
        config = Configuration(onEmpty="default_value")

        result = str(config)

        assert "Configuration" in result
        assert "[]" in result
        assert "onEmpty=default_value" in result

    def test_str_method_with_content(self) -> None:
        config = Configuration(onEmpty="fallback")
        config._set_content("value1")
        config._set_content("value2")

        result = str(config)

        assert "Configuration" in result
        assert "value1" in result
        assert "value2" in result
        assert "onEmpty=fallback" in result


class TestConfigurationEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string_value(self) -> None:
        config = Configuration(onEmpty="default")

        config._set_content("")

        assert config.content[0] == ""

    def test_whitespace_only_value(self) -> None:
        config = Configuration(onEmpty="default")

        config._set_content("   ")

        assert config.content[0] == "   "

    def test_unicode_value(self) -> None:
        config = Configuration(onEmpty="default")

        config._set_content("测试值")

        assert config.content[0] == "测试值"

    def test_on_empty_empty_string(self) -> None:
        config = Configuration(onEmpty="")
        config.balance_content()

        config.reduce_duplicates()

        assert config.reduced_content == "None"

    def test_entries_property_returns_none(self) -> None:
        config = Configuration(onEmpty="default")

        result = config.entries

        assert result is None
