"""Tests for Gem5StatsParser and type mapping."""

import pytest

from src.parsers.parser import Gem5StatsParser
from src.parsers.types import StatTypeRegistry


class TestGem5StatsParser:
    """Tests for Gem5StatsParser."""

    def setup_method(self):
        """Reset parser singleton before each test."""
        Gem5StatsParser.reset()

    def test_builder_creates_parser(self):
        """Test that builder creates a parser instance."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp/test")
            .with_pattern("stats.txt")
            .with_variable("simTicks", "scalar")
            .with_output("/tmp/output")
            .build()
        )

        assert parser is not None
        assert Gem5StatsParser.get_instance() is parser

    def test_builder_requires_path(self):
        """Test that builder raises if path not set."""
        with pytest.raises(ValueError, match="Stats path is required"):
            Gem5StatsParser.builder().with_variable("x", "scalar").with_output("/tmp").build()

    def test_builder_requires_variables(self):
        """Test that builder raises if no variables added."""
        with pytest.raises(ValueError, match="At least one variable"):
            Gem5StatsParser.builder().with_path("/tmp").with_output("/tmp").build()

    def test_singleton_behavior(self):
        """Test singleton is returned correctly."""
        parser1 = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_pattern("stats.txt")
            .with_variable("test", "scalar")
            .with_output("/tmp")
            .build()
        )
        parser2 = Gem5StatsParser.get_instance()

        assert parser1 is parser2

    def test_reset_clears_singleton(self):
        """Test reset clears the singleton."""
        Gem5StatsParser.builder().with_path("/tmp").with_variable("x", "scalar").with_output(
            "/tmp"
        ).build()

        assert Gem5StatsParser.get_instance() is not None
        Gem5StatsParser.reset()
        assert Gem5StatsParser.get_instance() is None


class TestParserVariableMapping:
    """Tests for variable mapping functionality."""

    def setup_method(self):
        Gem5StatsParser.reset()

    def test_map_scalar_variable(self):
        """Test mapping scalar variable."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("simTicks", "scalar")
            .with_output("/tmp")
            .build()
        )

        var_map = parser._map_variables()
        assert "simTicks" in var_map
        assert type(var_map["simTicks"]).__name__ == "Scalar"

    def test_map_vector_variable(self):
        """Test mapping vector variable with entries."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("testVector", "vector", vectorEntries="total,mean")
            .with_output("/tmp")
            .build()
        )

        var_map = parser._map_variables()
        assert "testVector" in var_map
        assert type(var_map["testVector"]).__name__ == "Vector"
        assert var_map["testVector"].entries == ["total", "mean"]

    def test_map_distribution_variable(self):
        """Test mapping distribution variable."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("dist", "distribution", minimum=0, maximum=5)
            .with_output("/tmp")
            .build()
        )

        var_map = parser._map_variables()
        assert "dist" in var_map
        assert type(var_map["dist"]).__name__ == "Distribution"
        assert var_map["dist"].minimum == 0
        assert var_map["dist"].maximum == 5

    def test_map_histogram_variable(self):
        """Test mapping histogram variable with statistics."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("hist", "histogram", bins=10, max_range=100.0, statistics="samples,mean")
            .with_output("/tmp")
            .build()
        )

        var_map = parser._map_variables()
        assert "hist" in var_map
        assert type(var_map["hist"]).__name__ == "Histogram"
        # Verify that statistics are correctly merged into entries
        entries = var_map["hist"].entries
        assert "samples" in entries
        assert "mean" in entries
        assert "0-10" in entries

    def test_map_configuration_variable(self):
        """Test mapping configuration variable."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("config", "configuration", onEmpty="DEFAULT")
            .with_output("/tmp")
            .build()
        )

        var_map = parser._map_variables()
        assert "config" in var_map
        assert type(var_map["config"]).__name__ == "Configuration"
        assert var_map["config"].onEmpty == "DEFAULT"

    def test_duplicate_variable_raises_error(self):
        """Test that duplicate variable names raise RuntimeError."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variables(
                [
                    {"name": "var1", "type": "scalar"},
                    {"name": "var1", "type": "scalar"},  # Duplicate
                ]
            )
            .with_output("/tmp")
            .build()
        )

        with pytest.raises(RuntimeError, match="Duplicate variable"):
            parser._map_variables()


class TestStatTypeRegistry:
    """Tests for the type registry."""

    def test_get_available_types(self):
        """Test getting list of available types."""
        types = StatTypeRegistry.get_types()
        assert "scalar" in types
        assert "vector" in types
        assert "distribution" in types
        assert "configuration" in types

    def test_create_unknown_type_raises(self):
        """Test creating unknown type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown stat type"):
            StatTypeRegistry.create("unknown_type")

    def test_create_scalar(self):
        """Test creating scalar type."""
        scalar = StatTypeRegistry.create("scalar", repeat=2)
        assert type(scalar).__name__ == "Scalar"
        assert scalar.repeat == 2

    def test_create_vector_requires_entries(self):
        """Test vector creation requires entries parameter."""
        with pytest.raises(ValueError, match="entries"):
            StatTypeRegistry.create("vector")
