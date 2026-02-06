"""Tests for Gem5StatsParser and type mapping."""

import pytest

from src.core.parsing.parser import Gem5StatsParser
from src.core.parsing.types import StatTypeRegistry


class TestGem5StatsParser:
    """Tests for Gem5StatsParser."""

    def setup_method(self) -> None:
        """Reset parser singleton before each test."""
        Gem5StatsParser.reset()

    def test_builder_creates_parser(self) -> None:
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

    def test_builder_requires_path(self) -> None:
        """Test that builder raises if path not set."""
        with pytest.raises(ValueError, match="Stats path is required"):
            Gem5StatsParser.builder().with_variable("x", "scalar").with_output("/tmp").build()

    def test_builder_requires_variables(self) -> None:
        """Test that builder raises if no variables added."""
        with pytest.raises(ValueError, match="At least one variable"):
            Gem5StatsParser.builder().with_path("/tmp").with_output("/tmp").build()

    def test_singleton_behavior(self) -> None:
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

    def test_reset_clears_singleton(self) -> None:
        """Test reset clears the singleton."""
        Gem5StatsParser.builder().with_path("/tmp").with_variable("x", "scalar").with_output(
            "/tmp"
        ).build()

        assert Gem5StatsParser.get_instance() is not None
        Gem5StatsParser.reset()
        assert Gem5StatsParser.get_instance() is None


class TestParserVariableMapping:
    """Tests for variable mapping functionality."""

    def setup_method(self) -> None:
        Gem5StatsParser.reset()

    def test_map_scalar_variable(self) -> None:
        """Test mapping scalar variable."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("simTicks", "scalar")
            .with_output("/tmp")
            .build()
        )

        # Verify configuration state directly
        assert len(parser._variables) == 1
        var = parser._variables[0]
        assert var.name == "simTicks"
        assert var.type == "scalar"

    def test_map_vector_variable(self) -> None:
        """Test mapping vector variable with entries."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("testVector", "vector", vectorEntries="total,mean")
            .with_output("/tmp")
            .build()
        )

        assert len(parser._variables) == 1
        var = parser._variables[0]
        assert var.name == "testVector"
        assert var.type == "vector"
        assert "vectorEntries" in var.params
        assert var.params["vectorEntries"] == "total,mean"

    def test_map_distribution_variable(self) -> None:
        """Test mapping distribution variable."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("dist", "distribution", minimum=0, maximum=5)
            .with_output("/tmp")
            .build()
        )

        var = parser._variables[0]
        assert var.name == "dist"
        assert var.type == "distribution"
        assert var.params["minimum"] == 0
        assert var.params["maximum"] == 5

    def test_map_histogram_variable(self) -> None:
        """Test mapping histogram variable with statistics."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("hist", "histogram", bins=11, max_range=100.0, statistics="samples,mean")
            .with_output("/tmp")
            .build()
        )

        var = parser._variables[0]
        assert var.name == "hist"
        assert var.type == "histogram"
        assert var.params["bins"] == 11
        assert var.params["statistics"] == "samples,mean"

    def test_map_configuration_variable(self) -> None:
        """Test mapping configuration variable."""
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variable("config", "configuration", onEmpty="DEFAULT")
            .with_output("/tmp")
            .build()
        )

        var = parser._variables[0]
        assert var.name == "config"
        assert var.type == "configuration"
        assert var.params["onEmpty"] == "DEFAULT"

    def test_duplicate_variable_handling(self) -> None:
        """Test that builder accepts duplicates (strategy handles them later or allows them)."""
        # Note: New strategy architecture might allow processing same var twice or handle it
        # differently.
        # The builder itself just accumulates config.
        parser = (
            Gem5StatsParser.builder()
            .with_path("/tmp")
            .with_variables(
                [
                    {"name": "var1", "type": "scalar"},
                    {"name": "var1", "type": "scalar"},
                ]
            )
            .with_output("/tmp")
            .build()
        )

        assert len(parser._variables) == 2
        assert parser._variables[0].name == "var1"
        assert parser._variables[1].name == "var1"


class TestStatTypeRegistry:
    """Tests for the type registry."""

    def test_get_available_types(self) -> None:
        """Test getting list of available types."""
        types = StatTypeRegistry.get_types()
        assert "scalar" in types
        assert "vector" in types
        assert "distribution" in types
        assert "configuration" in types

    def test_create_unknown_type_raises(self) -> None:
        """Test creating unknown type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown stat type"):
            StatTypeRegistry.create("unknown_type")

    def test_create_scalar(self) -> None:
        """Test creating scalar type."""
        scalar = StatTypeRegistry.create("scalar", repeat=2)
        assert type(scalar).__name__ == "Scalar"
        assert scalar.repeat == 2

    def test_create_vector_requires_entries(self) -> None:
        """Test vector creation requires entries parameter."""
        with pytest.raises(ValueError, match="entries"):
            StatTypeRegistry.create("vector")
