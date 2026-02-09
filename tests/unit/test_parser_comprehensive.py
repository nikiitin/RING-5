"""
Comprehensive tests for Gem5StatsParser parsing logic.

Following Rule 004 (QA Testing Mastery):
- Fixture-first design with tmp_path for I/O
- AAA pattern (Arrange-Act-Assert)
- Parametrization for strategy types
- Testing actual parse() and _persist_results() methods
- Monkeypatch for strategy mocking
"""

import os
from typing import Any, Dict, List, Optional

import pandas as pd
import pytest

from src.core.parsing.models import StatConfig
from src.core.parsing.parser import Gem5StatsParser, ParserBuilder
from src.core.parsing.strategies.file_parser_strategy import ParserStrategy
from src.core.parsing.types.base import StatType


class MockStat(StatType):
    """Mock stat type for testing."""

    def __init__(self, value: Any, entries: Optional[List[str]] = None, repeat: int = 1, **kwargs):
        super().__init__(repeat=repeat, **kwargs)
        self._test_value = value
        self._test_entries = entries
        self._balanced = False
        self._reduced = False
        self._reduced_content: Any = {}

    @property
    def entries(self) -> Optional[List[str]]:
        return self._test_entries

    def balance_content(self) -> None:
        self._balanced = True

    def reduce_duplicates(self) -> None:
        self._reduced = True
        if self._test_entries:
            # Create dict with entries
            self._reduced_content = {e: f"val_{e}" for e in self._test_entries}
        else:
            self._reduced_content = self._test_value

    @property
    def reduced_content(self) -> Any:
        return self._reduced_content


class MockStrategy(ParserStrategy):
    """Mock strategy for testing parser logic."""

    def __init__(self, results: Optional[List[Dict[str, Any]]] = None):
        self.results = results or []
        self.execute_called = False

    def execute(
        self, stats_path: str, stats_pattern: str, variables: List[StatConfig]
    ) -> List[Dict[str, Any]]:
        self.execute_called = True
        return self.results


@pytest.fixture(autouse=True)
def reset_parser():
    """Reset parser singleton before each test."""
    Gem5StatsParser.reset()
    yield
    Gem5StatsParser.reset()


class TestParserBuilderConfiguration:
    """Test ParserBuilder fluent interface."""

    def test_with_path(self):
        # Arrange
        builder = ParserBuilder()

        # Act
        result = builder.with_path("/test/path")

        # Assert
        assert result is builder  # Fluent interface
        assert builder._stats_path == "/test/path"

    def test_with_pattern(self):
        # Arrange
        builder = ParserBuilder()

        # Act
        result = builder.with_pattern("*.txt")

        # Assert
        assert result is builder
        assert builder._stats_pattern == "*.txt"

    def test_with_output(self):
        # Arrange
        builder = ParserBuilder()

        # Act
        result = builder.with_output("/output/dir")

        # Assert
        assert result is builder
        assert builder._output_dir == "/output/dir"

    def test_with_variable_fluent(self):
        # Arrange
        builder = ParserBuilder()

        # Act
        result = builder.with_variable("test_var", "scalar")

        # Assert
        assert result is builder
        assert len(builder._variables) == 1
        assert builder._variables[0].name == "test_var"

    def test_with_variable_params(self):
        # Arrange
        builder = ParserBuilder()

        # Act
        builder.with_variable("vec", "vector", vectorEntries="a,b,c", repeat=3)

        # Assert
        var = builder._variables[0]
        assert var.params["vectorEntries"] == "a,b,c"
        assert var.repeat == 3

    def test_with_variable_statistics_only(self):
        # Arrange
        builder = ParserBuilder()

        # Act
        builder.with_variable("stat", "scalar", statistics_only=True)

        # Assert
        assert builder._variables[0].statistics_only is True

    def test_with_variables_list_of_dicts(self):
        # Arrange
        builder = ParserBuilder()
        vars_list = [
            {"name": "var1", "type": "scalar"},
            {"name": "var2", "type": "vector", "vectorEntries": "0,1"},
        ]

        # Act
        builder.with_variables(vars_list)

        # Assert
        assert len(builder._variables) == 2
        assert builder._variables[0].name == "var1"
        assert builder._variables[1].name == "var2"

    def test_with_variables_list_of_statconfig(self):
        # Arrange
        builder = ParserBuilder()
        vars_list = [
            StatConfig(name="config1", type="configuration"),
            StatConfig(name="scalar1", type="scalar"),
        ]

        # Act
        builder.with_variables(vars_list)

        # Assert
        assert len(builder._variables) == 2
        assert all(isinstance(v, StatConfig) for v in builder._variables)

    @pytest.mark.parametrize(
        "strategy_name,expected",
        [
            ("simple", "SimpleStatsStrategy"),
            ("Simple", "SimpleStatsStrategy"),
            ("SIMPLE", "SimpleStatsStrategy"),
            ("config_aware", "ConfigAwareStrategy"),
            ("config_AWARE", "ConfigAwareStrategy"),
        ],
    )
    def test_with_strategy_case_insensitive(self, strategy_name, expected):
        # Arrange
        builder = ParserBuilder()

        # Act
        result = builder.with_strategy(strategy_name)

        # Assert
        assert result is builder
        assert builder._strategy_type == strategy_name.lower()

    def test_default_output_uses_temp_dir(self):
        # Arrange
        builder = ParserBuilder()

        # Act & Assert
        assert "ring5_output" in builder._output_dir
        assert os.path.isabs(builder._output_dir)

    def test_default_pattern_is_stats_txt(self):
        # Arrange
        builder = ParserBuilder()

        # Act & Assert
        assert builder._stats_pattern == "stats.txt"

    def test_default_strategy_is_simple(self):
        # Arrange
        builder = ParserBuilder()

        # Act & Assert
        assert builder._strategy_type == "simple"


class TestParserBuilderValidation:
    """Test ParserBuilder build validation."""

    def test_build_without_path_raises(self):
        # Arrange
        builder = ParserBuilder().with_variable("x", "scalar")

        # Act & Assert
        with pytest.raises(ValueError, match="Stats path is required"):
            builder.build()

    def test_build_without_variables_raises(self):
        # Arrange
        builder = ParserBuilder().with_path("/test")

        # Act & Assert
        with pytest.raises(ValueError, match="At least one variable"):
            builder.build()

    def test_build_with_invalid_strategy_raises(self):
        # Arrange
        builder = (
            ParserBuilder()
            .with_path("/test")
            .with_variable("x", "scalar")
            .with_strategy("invalid_strategy")
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown strategy type"):
            builder.build()

    def test_build_creates_simple_strategy(self):
        # Arrange
        builder = (
            ParserBuilder().with_path("/test").with_variable("x", "scalar").with_strategy("simple")
        )

        # Act
        parser = builder.build()

        # Assert
        assert parser._strategy.__class__.__name__ == "SimpleStatsStrategy"

    def test_build_creates_config_aware_strategy(self):
        # Arrange
        builder = (
            ParserBuilder()
            .with_path("/test")
            .with_variable("x", "scalar")
            .with_strategy("config_aware")
        )

        # Act
        parser = builder.build()

        # Assert
        assert parser._strategy.__class__.__name__ == "ConfigAwareStrategy"

    def test_build_sets_singleton(self):
        # Arrange
        builder = ParserBuilder().with_path("/test").with_variable("x", "scalar")

        # Act
        parser = builder.build()

        # Assert
        assert Gem5StatsParser.get_instance() is parser


class TestParserParse:
    """Test Gem5StatsParser.parse() execution."""

    def test_parse_calls_strategy_execute(self, tmp_path):
        # Arrange
        mock_strategy = MockStrategy(results=[{"var1": "value1"}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="var1", type="scalar")],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        parser.parse()

        # Assert
        assert mock_strategy.execute_called

    def test_parse_returns_csv_path(self, tmp_path):
        # Arrange
        mock_stat = MockStat(42.0, entries=None)
        mock_strategy = MockStrategy(results=[{"var1": mock_stat}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="var1", type="scalar")],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        result = parser.parse()

        # Assert
        assert result is not None
        assert result.endswith("results.csv")
        assert os.path.exists(result)

    def test_parse_with_empty_results_returns_none(self, tmp_path):
        # Arrange
        mock_strategy = MockStrategy(results=[])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="var1", type="scalar")],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        result = parser.parse()

        # Assert
        assert result is None


class TestParserPersistResults:
    """Test Gem5StatsParser._persist_results() CSV generation."""

    def test_persist_scalar_variables(self, tmp_path):
        # Arrange
        mock_stat = MockStat(100.5)
        mock_strategy = MockStrategy(results=[{"cpu_ipc": mock_stat}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="cpu_ipc", type="scalar")],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        csv_path = parser.parse()

        # Assert
        assert csv_path is not None
        df = pd.read_csv(csv_path)
        assert "cpu_ipc" in df.columns
        assert len(df) == 1

    def test_persist_vector_variables_with_entries(self, tmp_path):
        # Arrange
        mock_stat = MockStat(None, entries=["0", "1", "2"])
        mock_strategy = MockStrategy(results=[{"vec": mock_stat}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="vec", type="vector", params={"vectorEntries": "0,1,2"})],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        csv_path = parser.parse()

        # Assert
        df = pd.read_csv(csv_path)
        assert "vec..0" in df.columns
        assert "vec..1" in df.columns
        assert "vec..2" in df.columns

    def test_persist_multiple_simulations(self, tmp_path):
        # Arrange
        results = [
            {"var1": MockStat(10.0)},
            {"var1": MockStat(20.0)},
            {"var1": MockStat(30.0)},
        ]
        mock_strategy = MockStrategy(results=results)
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="var1", type="scalar")],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        csv_path = parser.parse()

        # Assert
        df = pd.read_csv(csv_path)
        assert len(df) == 3

    def test_persist_calls_balance_and_reduce(self, tmp_path):
        # Arrange
        mock_stat = MockStat(42.0)
        mock_strategy = MockStrategy(results=[{"var1": mock_stat}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="var1", type="scalar")],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        parser.parse()

        # Assert
        assert mock_stat._balanced is True
        assert mock_stat._reduced is True

    def test_persist_handles_missing_variable_in_results(self, tmp_path, caplog):
        # Arrange
        mock_strategy = MockStrategy(results=[{"other_var": MockStat(1.0)}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="expected_var", type="scalar")],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        csv_path = parser.parse()

        # Assert
        assert csv_path is not None
        # Should log error about missing critical variable
        assert "Critical variable" in caplog.text or "missing for simulation" in caplog.text

    def test_persist_creates_output_directory(self, tmp_path):
        # Arrange
        output_dir = tmp_path / "nested" / "output" / "dir"
        mock_stat = MockStat(5.0)
        mock_strategy = MockStrategy(results=[{"var1": mock_stat}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="var1", type="scalar")],
            output_dir=str(output_dir),
            strategy=mock_strategy,
        )

        # Act
        csv_path = parser.parse()

        # Assert
        assert os.path.exists(output_dir)
        assert os.path.exists(csv_path)

    def test_persist_handles_raw_data_without_stat_object(self, tmp_path):
        # Arrange - Raw string/int data from config strategy
        mock_strategy = MockStrategy(results=[{"benchmark": "test_bench"}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="benchmark", type="configuration")],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        csv_path = parser.parse()

        # Assert
        df = pd.read_csv(csv_path)
        assert df["benchmark"].iloc[0] == "test_bench"

    def test_persist_vector_with_missing_entries_uses_nan(self, tmp_path):
        # Arrange
        # Create a custom mock stat that returns reduced_content with missing entry
        class PartialMockStat(MockStat):
            def reduce_duplicates(self) -> None:
                self._reduced = True
                # Intentionally missing entry "1"
                self._reduced_content = {"0": "val_0", "2": "val_2"}

        mock_stat = PartialMockStat(None, entries=["0", "1", "2"])
        mock_strategy = MockStrategy(results=[{"vec": mock_stat}])
        parser = Gem5StatsParser(
            stats_path="/test",
            stats_pattern="*.txt",
            variables=[StatConfig(name="vec", type="vector", params={"vectorEntries": "0,1,2"})],
            output_dir=str(tmp_path),
            strategy=mock_strategy,
        )

        # Act
        csv_path = parser.parse()

        # Assert
        df = pd.read_csv(csv_path)
        # pandas reads "NaN" string as actual NaN value
        assert pd.isna(df["vec..1"].iloc[0]) or df["vec..1"].iloc[0] == "NaN"


class TestParserSingletonAndReset:
    """Test singleton pattern and reset functionality."""

    def test_get_instance_returns_none_initially(self):
        # Arrange & Act
        instance = Gem5StatsParser.get_instance()

        # Assert
        assert instance is None

    def test_get_instance_returns_built_parser(self):
        # Arrange
        parser = ParserBuilder().with_path("/test").with_variable("x", "scalar").build()

        # Act
        instance = Gem5StatsParser.get_instance()

        # Assert
        assert instance is parser

    def test_reset_clears_instance(self):
        # Arrange
        ParserBuilder().with_path("/test").with_variable("x", "scalar").build()

        # Act
        Gem5StatsParser.reset()

        # Assert
        assert Gem5StatsParser.get_instance() is None

    def test_builder_returns_new_builder_instance(self):
        # Arrange & Act
        builder1 = Gem5StatsParser.builder()
        builder2 = Gem5StatsParser.builder()

        # Assert
        assert builder1 is not builder2
        assert isinstance(builder1, ParserBuilder)


class TestParserThreadSafety:
    """Test thread-safe singleton initialization."""

    def test_lock_exists(self):
        # Arrange & Act & Assert
        assert hasattr(Gem5StatsParser, "_lock")
        import threading

        assert isinstance(Gem5StatsParser._lock, type(threading.Lock()))

    def test_build_uses_lock(self):
        # Arrange
        builder = ParserBuilder().with_path("/test").with_variable("x", "scalar")

        # Act
        parser = builder.build()

        # Assert - Just verify no exceptions, lock is internal
        assert parser is not None
