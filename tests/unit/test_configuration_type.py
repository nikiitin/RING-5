"""
Comprehensive tests for Configuration stat type.

Tests cover:
- Initialization with on_empty parameter
- Typed string observation validation
- Content setting and storage
- balance_content (always balanced, no padding)
- reduce_duplicates (first value or on_empty)
- on_empty property
- Type registration
- Edge cases (None, empty string, numeric types)
- __str__ method
"""

import pytest

from src.parsing.gem5.types.base import StatTypeRegistry
from src.parsing.gem5.types.configuration import Configuration


class TestConfigurationInitialization:
    """Test Configuration object creation and initialization."""

    def test_required_params_contains_on_empty(self) -> None:
        required = Configuration.required_params

        assert "on_empty" in required
        assert len(required) == 1

    def test_init_with_on_empty(self) -> None:
        config = Configuration(on_empty="default_value")

        assert config._repeat == 1
        assert config._on_empty == "default_value"
        assert config.content == []
        assert config.is_balanced is False
        assert config.is_reduced is False

    def test_init_with_custom_repeat_and_on_empty(self) -> None:
        config = Configuration(repeat=5, on_empty="fallback")

        assert config._repeat == 5
        assert config._on_empty == "fallback"

    def test_default_fallback_is_text_and_none_is_rejected(self) -> None:
        config = Configuration()
        assert config.on_empty == "None"
        with pytest.raises(TypeError, match="on_empty must be text"):
            Configuration(on_empty=None)


class TestConfigurationOnEmptyProperty:
    """Test on_empty property getter."""

    # [test->req~ring5.ingestion.configuration-fallbacks~1]

    def test_on_empty_property_returns_string(self) -> None:
        config = Configuration(on_empty="test_default")

        result = config.on_empty

        assert result == "test_default"
        assert isinstance(result, str)

    def test_non_text_fallback_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="on_empty must be text"):
            Configuration(on_empty=123)


class TestConfigurationValidateContent:
    """Test typed observation admission without text coercion."""

    def test_validate_string(self) -> None:
        config = Configuration(on_empty="default")

        config.add_observation("test_value")

    def test_reject_integer(self) -> None:
        config = Configuration(on_empty="default")
        for value in (42,):
            with pytest.raises(TypeError, match="Observation must be text"):
                config.add_observation(value)
        assert config.content == []

    def test_reject_float(self) -> None:
        config = Configuration(on_empty="default")
        for value in (3.14159,):
            with pytest.raises(TypeError, match="Observation must be text"):
                config.add_observation(value)
        assert config.content == []

    def test_reject_none(self) -> None:
        config = Configuration(on_empty="default")
        for value in (None,):
            with pytest.raises(TypeError, match="Observation must be text"):
                config.add_observation(value)
        assert config.content == []

    def test_reject_boolean(self) -> None:
        config = Configuration(on_empty="default")
        for value in (True, False):
            with pytest.raises(TypeError, match="Observation must be text"):
                config.add_observation(value)
        assert config.content == []

    def test_reject_list(self) -> None:
        config = Configuration(on_empty="default")
        for value in ([1, 2, 3],):
            with pytest.raises(TypeError, match="Observation must be text"):
                config.add_observation(value)
        assert config.content == []

    def test_non_text_object_is_rejected_without_string_coercion(self) -> None:
        class NonStringable:
            def __str__(self) -> str:
                raise AssertionError("String coercion must not run")

        config = Configuration(on_empty="default")
        with pytest.raises(TypeError, match="Observation must be text"):
            config.add_observation(NonStringable())
        assert config.content == []


class TestConfigurationSetContent:
    """Test typed text observation storage."""

    def test_add_observation_string(self) -> None:
        config = Configuration(on_empty="default")

        config.add_observation("benchmark_name")

        assert len(config.content) == 1
        assert config.content[0] == "benchmark_name"

    def test_reject_integer(self) -> None:
        config = Configuration(on_empty="default")
        with pytest.raises(TypeError, match="Observation must be text"):
            config.add_observation(12345)
        assert config.content == []

    def test_reject_float(self) -> None:
        config = Configuration(on_empty="default")
        with pytest.raises(TypeError, match="Observation must be text"):
            config.add_observation(3.14159)
        assert config.content == []

    def test_reject_none(self) -> None:
        config = Configuration(on_empty="default")
        with pytest.raises(TypeError, match="Observation must be text"):
            config.add_observation(None)
        assert config.content == []

    def test_add_observation_multiple_values(self) -> None:
        config = Configuration(repeat=3, on_empty="default")

        config.add_observation("value1")
        config.add_observation("value2")
        config.add_observation("value3")

        assert len(config.content) == 3
        assert config.content == ["value1", "value2", "value3"]


class TestConfigurationBalanceContent:
    """Test balance_content method (always balanced, no padding)."""

    # [test->req~ring5.ingestion.configuration~1]

    def test_balance_empty_content_no_padding(self) -> None:
        config = Configuration(on_empty="default")

        config.balance_content()

        assert config.is_balanced is True
        assert config.content == []

    def test_balance_with_content_no_change(self) -> None:
        config = Configuration(repeat=3, on_empty="default")
        config.add_observation("val1")
        config.add_observation("val2")

        config.balance_content()

        assert config.is_balanced is True
        assert len(config.content) == 2

    def test_balance_more_values_than_repeat_no_error(self) -> None:
        config = Configuration(repeat=1, on_empty="default")
        config.add_observation("val1")
        config.add_observation("val2")
        config.add_observation("val3")

        config.balance_content()
        assert config.is_balanced is True
        assert len(config.content) == 3


class TestConfigurationReduceDuplicates:
    """Test reduce_duplicates method (returns first value or on_empty)."""

    def test_reduce_with_empty_content_returns_on_empty(self) -> None:
        config = Configuration(on_empty="default_value")
        config.balance_content()

        config.reduce_duplicates()

        assert config.is_reduced is True
        assert config.reduced_content == "default_value"

    def test_reduce_with_single_value_returns_that_value(self) -> None:
        config = Configuration(on_empty="default")
        config.add_observation("only_value")
        config.balance_content()

        config.reduce_duplicates()

        assert config.is_reduced is True
        assert config.reduced_content == "only_value"

    def test_reduce_with_multiple_values_returns_first(self) -> None:
        config = Configuration(repeat=3, on_empty="default")
        config.add_observation("first")
        config.add_observation("second")
        config.add_observation("third")
        config.balance_content()

        config.reduce_duplicates()

        assert config.is_reduced is True
        assert config.reduced_content == "first"

    def test_reduce_marks_reduced_flag(self) -> None:
        config = Configuration(on_empty="default")
        config.add_observation("value")
        config.balance_content()

        config.reduce_duplicates()

        assert config.is_reduced is True


class TestConfigurationReducedContentAccess:
    """Test reduced_content property access guards."""

    def test_access_reduced_content_before_balance_raises(self) -> None:
        config = Configuration(on_empty="default")
        config.add_observation("value")
        # Don't call balance_content()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = config.reduced_content

    def test_access_reduced_content_before_reduce_raises(self) -> None:
        config = Configuration(on_empty="default")
        config.add_observation("value")
        config.balance_content()
        # Don't call reduce_duplicates()

        with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
            _ = config.reduced_content

    def test_access_reduced_content_after_both_succeeds(self) -> None:
        config = Configuration(on_empty="default")
        config.add_observation("test_value")
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
        config = StatTypeRegistry.create("configuration", on_empty="test")

        assert isinstance(config, Configuration)
        assert config._on_empty == "test"


class TestConfigurationStrMethod:
    """Test __str__ method for string representation."""

    def test_str_method_empty_content(self) -> None:
        config = Configuration(on_empty="default_value")

        result = str(config)

        assert "configuration" in result
        assert "repeat=1" in result
        assert "balanced=False, reduced=False, padded=0" in result

    def test_str_method_with_content(self) -> None:
        config = Configuration(on_empty="fallback")
        config.add_observation("value1")
        config.add_observation("value2")

        result = str(config)

        assert "configuration" in result
        assert "repeat=1" in result
        assert "balanced=False, reduced=False, padded=0" in result


class TestConfigurationEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string_value(self) -> None:
        config = Configuration(on_empty="default")

        config.add_observation("")

        assert config.content[0] == ""

    def test_whitespace_only_value(self) -> None:
        config = Configuration(on_empty="default")

        config.add_observation("   ")

        assert config.content[0] == "   "

    def test_unicode_value(self) -> None:
        config = Configuration(on_empty="default")

        config.add_observation("测试值")

        assert config.content[0] == "测试值"

    def test_on_empty_empty_string(self) -> None:
        config = Configuration(on_empty="")
        config.balance_content()

        config.reduce_duplicates()

        assert config.reduced_content == ""

    def test_entries_property_returns_none(self) -> None:
        config = Configuration(on_empty="default")

        result = config.entries

        assert result is None
