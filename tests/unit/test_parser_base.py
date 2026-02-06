"""
Tests for ParserStrategy base interface.

Following Rule 004 (QA Testing Mastery):
- Interface testing verifies ABC behavior
- Tests that abstract methods must be implemented
- Tests instantiation rules
"""

import pytest

from src.core.parsing.base import ParserStrategy
from src.core.parsing.models import StatConfig


class TestParserStrategyInterface:
    """Test ParserStrategy abstract base class."""

    def test_cannot_instantiate_directly(self):
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ParserStrategy()

    def test_subclass_must_implement_parse(self):
        # Arrange - Create invalid subclass without implementing parse
        class IncompleteParser(ParserStrategy):
            pass

        # Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteParser()

    def test_valid_subclass_can_be_instantiated(self):
        # Arrange - Create valid subclass
        class ValidParser(ParserStrategy):
            def parse(self, stats_path, stats_pattern, variables, output_dir):
                return "result.csv"

        # Act
        parser = ValidParser()
        result = parser.parse("/path", "*.txt", [], "/out")

        # Assert
        assert result == "result.csv"

    def test_parse_method_signature(self):
        # Arrange - Create concrete implementation
        class ConcreteParser(ParserStrategy):
            def parse(self, stats_path, stats_pattern, variables, output_dir):
                # Verify expected types can be passed
                assert isinstance(stats_path, str)
                assert isinstance(stats_pattern, str)
                assert isinstance(variables, list)
                assert isinstance(output_dir, str)
                return None

        # Act
        parser = ConcreteParser()
        result = parser.parse("/base", "stats.*", [], "/output")

        # Assert
        assert result is None  # Can return None

    def test_parse_accepts_statconfig_list(self):
        # Arrange
        class TestParser(ParserStrategy):
            def parse(self, stats_path, stats_pattern, variables, output_dir):
                return f"processed_{len(variables)}_variables"

        # Act
        parser = TestParser()
        vars_list = [
            StatConfig(name="cpu.ipc", type="scalar"),
            StatConfig(name="cpu.cycles", type="scalar"),
        ]
        result = parser.parse("/path", "*.txt", vars_list, "/out")

        # Assert
        assert result == "processed_2_variables"
