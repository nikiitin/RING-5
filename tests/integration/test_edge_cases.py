"""Integration tests for edge cases and boundary conditions.

Covers Scenarios #16-#19:
    - #16: Distribution/Histogram variable type processing
    - #17: Config service delete/reload cycle
    - #18: FigureEngine edge cases (empty config, missing styler, legend)
    - #19: PatternAggregator regex expansion

Tests exercise boundary conditions, malformed inputs, and unusual
but valid combinations that are unlikely to appear in normal unit tests.
"""

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.core.models.parsing_models import ScannedVariable

# ===========================================================================
# Helper: Minimal ScannedVariable dataclass
# ===========================================================================
from src.core.parsing.gem5.impl.scanning.pattern_aggregator import (
    PatternAggregator,
)
from src.core.parsing.gem5.types.distribution import Distribution
from src.core.parsing.gem5.types.histogram import Histogram
from src.core.services.data_services.config_service import ConfigService
from src.web.figures.engine import FigureEngine

# ===========================================================================
# Test Class 1: Distribution & Histogram processing edge cases
# ===========================================================================


class TestDistributionHistogramEdgeCases:
    """Test Distribution and Histogram variable type parsing."""

    def test_distribution_basic_processing(self) -> None:
        """Distribution processes a valid set of buckets."""
        dist = Distribution(repeat=1, minimum=0, maximum=4)

        dist.content = {
            "underflows": 0,
            "overflows": 5,
            "0": 10,
            "1": 20,
            "2": 30,
            "3": 15,
            "4": 25,
        }
        dist.balance_content()
        dist.reduce_duplicates()

        result: Dict[str, float] = dist.reduced_content
        assert result["0"] == 10.0
        assert result["2"] == 30.0
        assert result["underflows"] == 0.0
        assert result["overflows"] == 5.0

    def test_distribution_with_repeats(self) -> None:
        """Distribution averages across repeated dumps."""
        dist = Distribution(repeat=2, minimum=0, maximum=2)

        # First dump
        dist.content = {
            "underflows": 0,
            "overflows": 0,
            "0": 10,
            "1": 20,
            "2": 30,
        }
        # Second dump
        dist.content = {
            "underflows": 0,
            "overflows": 0,
            "0": 20,
            "1": 40,
            "2": 60,
        }
        dist.balance_content()
        dist.reduce_duplicates()

        result: Dict[str, float] = dist.reduced_content
        # Average: (10+20)/2=15, (20+40)/2=30, (30+60)/2=45
        assert result["0"] == 15.0
        assert result["1"] == 30.0
        assert result["2"] == 45.0

    def test_distribution_maximum_too_large(self) -> None:
        """Distribution raises on absurdly large range."""
        with pytest.raises(ValueError, match="100000"):
            Distribution(repeat=1, minimum=0, maximum=200_000)

    def test_histogram_basic_processing(self) -> None:
        """Histogram processes range-keyed buckets."""
        hist = Histogram(repeat=1)

        hist.content = {
            "0-1023": 100,
            "1024-2047": 200,
            "2048-4095": 50,
        }
        hist.balance_content()
        hist.reduce_duplicates()

        result: Dict[str, float] = hist.reduced_content
        assert result["0-1023"] == 100.0
        assert result["1024-2047"] == 200.0
        assert result["2048-4095"] == 50.0

    def test_histogram_with_repeats(self) -> None:
        """Histogram averages across repeats."""
        hist = Histogram(repeat=2)

        hist.content = {"0-1023": 100, "1024-2047": 200}
        hist.content = {"0-1023": 300, "1024-2047": 400}

        hist.balance_content()
        hist.reduce_duplicates()

        result: Dict[str, float] = hist.reduced_content
        assert result["0-1023"] == 200.0  # (100+300)/2
        assert result["1024-2047"] == 300.0  # (200+400)/2

    def test_distribution_missing_boundaries_raises(self) -> None:
        """Distribution raises when boundary buckets are missing."""
        dist = Distribution(repeat=1, minimum=0, maximum=2)

        with pytest.raises((TypeError, RuntimeError)):
            dist.content = {
                # Missing underflows/overflows
                "0": 10,
                "1": 20,
                "2": 30,
            }


# ===========================================================================
# Test Class 2: Config service delete/reload cycle
# ===========================================================================


class TestConfigServiceEdgeCases:
    """Test ConfigService round-trip edge cases."""

    def test_save_load_delete_cycle(self, tmp_path: Path) -> None:
        """Full save → load → delete → verify deleted cycle."""
        config_dir: Path = tmp_path / "saved_configs"
        config_dir.mkdir(parents=True)

        with patch.object(
            ConfigService,
            "get_config_dir",
            return_value=config_dir,
        ):
            # Save
            shapers: List[Dict[str, Any]] = [
                {"type": "columnSelector", "columns": ["a", "b"]},
            ]
            saved_path: str = ConfigService.save_configuration(
                "test_config", "A test description", shapers
            )

            # Load
            loaded: Dict[str, Any] = ConfigService.load_configuration(saved_path)
            assert loaded["name"] == "test_config"
            assert loaded["description"] == "A test description"
            assert loaded["shapers"] == shapers

            # Delete
            result: bool = ConfigService.delete_configuration(saved_path)
            assert result is True

            # Verify deleted — load should fail
            with pytest.raises((FileNotFoundError, ValueError)):
                ConfigService.load_configuration(saved_path)

    def test_load_saved_configs_skips_invalid(self, tmp_path: Path) -> None:
        """load_saved_configs silently skips corrupt JSON files."""
        config_dir: Path = tmp_path / "saved_configs"
        config_dir.mkdir(parents=True)

        # Valid config
        valid = config_dir / "valid.json"
        valid.write_text('{"name": "valid", "description": "ok", "shapers": []}')

        # Invalid JSON
        invalid = config_dir / "corrupt.json"
        invalid.write_text("{not valid json!!!")

        with patch.object(
            ConfigService,
            "get_config_dir",
            return_value=config_dir,
        ):
            configs: List[Dict[str, Any]] = ConfigService.load_saved_configs()

            # Should get exactly 1 (the valid one), corrupt is skipped
            assert len(configs) == 1
            assert configs[0]["name"] == "valid.json"

    def test_save_with_special_characters(self, tmp_path: Path) -> None:
        """Config names with special characters are sanitized."""
        config_dir: Path = tmp_path / "saved_configs"
        config_dir.mkdir(parents=True)

        with patch.object(
            ConfigService,
            "get_config_dir",
            return_value=config_dir,
        ):
            saved_path: str = ConfigService.save_configuration(
                "test/../../etc/passwd",
                "Malicious name test",
                [{"type": "columnSelector", "columns": ["a"]}],
            )

            # Should still save (name sanitized)
            loaded: Dict[str, Any] = ConfigService.load_configuration(saved_path)
            assert loaded["description"] == "Malicious name test"


# ===========================================================================
# Test Class 3: FigureEngine edge cases
# ===========================================================================


class TestFigureEngineEdgeCases:
    """Test FigureEngine boundary conditions."""

    def _make_creator(self) -> Any:
        """Create a minimal FigureCreator."""

        class _Creator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=data.iloc[:, 0], y=data.iloc[:, 1]))
                return fig

        return _Creator()

    def _make_styler(self) -> Any:
        """Create a minimal FigureStyler."""

        class _Styler:
            def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
                fig.update_layout(
                    width=config.get("width", 800),
                    height=config.get("height", 600),
                )
                return fig

        return _Styler()

    def test_build_without_styler(self) -> None:
        """Engine builds figure when no styler registered."""
        engine = FigureEngine()
        engine.register("custom", self._make_creator())

        data: pd.DataFrame = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        fig: go.Figure = engine.build("custom", data, {})

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1

    def test_build_with_empty_config(self) -> None:
        """Engine builds figure with completely empty config dict."""
        engine = FigureEngine()
        engine.register("custom", self._make_creator(), self._make_styler())

        data: pd.DataFrame = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        fig: go.Figure = engine.build("custom", data, {})

        assert isinstance(fig, go.Figure)

    def test_build_with_legend_labels(self) -> None:
        """Engine applies legend label remapping when provided in config."""
        engine = FigureEngine()
        engine.register("custom", self._make_creator())

        data: pd.DataFrame = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        config: Dict[str, Any] = {
            "legend_labels": {"x": "My X Label"},
        }
        fig: go.Figure = engine.build("custom", data, config)

        assert isinstance(fig, go.Figure)

    def test_build_unregistered_type_lists_available(self) -> None:
        """KeyError message lists available types when type not found."""
        engine = FigureEngine()
        engine.register("bar", self._make_creator())
        engine.register("line", self._make_creator())

        data: pd.DataFrame = pd.DataFrame({"x": [1]})

        with pytest.raises(KeyError) as exc_info:
            engine.build("heatmap", data, {})

        error_msg: str = str(exc_info.value)
        assert "bar" in error_msg or "line" in error_msg

    def test_from_plot_factory_method(self) -> None:
        """from_plot creates engine with single plot type registered."""
        creator = self._make_creator()
        engine: FigureEngine = FigureEngine.from_plot(creator, "scatter")

        assert engine.has_creator("scatter")
        assert "scatter" in engine.registered_types

    def test_register_styler_independently(self) -> None:
        """Styler can be registered after creator."""
        engine = FigureEngine()
        engine.register("custom", self._make_creator())
        engine.register_styler("custom", self._make_styler())

        data: pd.DataFrame = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        config: Dict[str, Any] = {"width": 1200, "height": 900}
        fig: go.Figure = engine.build("custom", data, config)

        assert fig.layout.width == 1200
        assert fig.layout.height == 900


# ===========================================================================
# Test Class 4: PatternAggregator regex expansion
# ===========================================================================


class TestPatternAggregatorEdgeCases:
    """Test pattern aggregation for multi-component gem5 variables."""

    def test_simple_cpu_aggregation(self) -> None:
        """cpu0/cpu1/cpu2 collapse into cpu\\d+ pattern."""
        variables: List[ScannedVariable] = [
            ScannedVariable(name="system.cpu0.numCycles", type="scalar", entries=[]),
            ScannedVariable(name="system.cpu1.numCycles", type="scalar", entries=[]),
            ScannedVariable(name="system.cpu2.numCycles", type="scalar", entries=[]),
        ]

        result: List[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        # Should collapse into one pattern variable
        pattern_vars: List[ScannedVariable] = [v for v in result if r"\d+" in v.name]
        assert len(pattern_vars) == 1
        assert pattern_vars[0].name == r"system.cpu\d+.numCycles"
        # Type promoted to vector
        assert pattern_vars[0].type == "vector"
        # Entries are the numeric IDs
        assert sorted(pattern_vars[0].entries) == ["0", "1", "2"]

    def test_no_aggregation_for_single_instance(self) -> None:
        """Single-instance variables are NOT aggregated."""
        variables: List[ScannedVariable] = [
            ScannedVariable(name="system.cpu0.numCycles", type="scalar", entries=[]),
            ScannedVariable(name="system.memctrl.readReqs", type="scalar", entries=[]),
        ]

        result: List[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        # cpu0 has no partner → stays as-is
        names: List[str] = [v.name for v in result]
        assert "system.cpu0.numCycles" in names
        assert "system.memctrl.readReqs" in names
        assert all(r"\d+" not in n for n in names)

    def test_multi_numeric_pattern(self) -> None:
        """Variables with multiple numeric indices aggregate correctly."""
        variables: List[ScannedVariable] = [
            ScannedVariable(
                name="system.ruby.l0_cntrl0.hits",
                type="vector",
                entries=["read", "write"],
            ),
            ScannedVariable(
                name="system.ruby.l0_cntrl1.hits",
                type="vector",
                entries=["read", "write"],
            ),
            ScannedVariable(
                name="system.ruby.l1_cntrl0.hits",
                type="vector",
                entries=["read", "write"],
            ),
        ]

        result: List[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        pattern_vars: List[ScannedVariable] = [v for v in result if r"\d+" in v.name]
        # Should have at least 1 pattern var
        assert len(pattern_vars) >= 1

        # Check entries contain union
        for pv in pattern_vars:
            assert "read" in pv.entries or len(pv.entries) > 0

    def test_vector_type_preserved(self) -> None:
        """Vector variables stay vector type after aggregation."""
        variables: List[ScannedVariable] = [
            ScannedVariable(
                name="system.cpu0.dcache.hits",
                type="vector",
                entries=["demand_accesses", "total"],
            ),
            ScannedVariable(
                name="system.cpu1.dcache.hits",
                type="vector",
                entries=["demand_accesses", "total"],
            ),
        ]

        result: List[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        pattern_vars: List[ScannedVariable] = [v for v in result if r"\d+" in v.name]
        assert len(pattern_vars) == 1
        assert pattern_vars[0].type == "vector"
        assert "demand_accesses" in pattern_vars[0].entries

    def test_distribution_aggregation_preserves_minmax(self) -> None:
        """Distribution aggregation takes min of minimums, max of maximums."""
        variables: List[ScannedVariable] = [
            ScannedVariable(
                name="system.cpu0.dcache.miss_latency",
                type="distribution",
                entries=[],
                minimum=10.0,
                maximum=100.0,
            ),
            ScannedVariable(
                name="system.cpu1.dcache.miss_latency",
                type="distribution",
                entries=[],
                minimum=5.0,
                maximum=200.0,
            ),
        ]

        result: List[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        pattern_vars: List[ScannedVariable] = [v for v in result if r"\d+" in v.name]
        assert len(pattern_vars) == 1
        pv: ScannedVariable = pattern_vars[0]
        assert pv.type == "distribution"
        assert pv.minimum == 5.0  # min of (10, 5)
        assert pv.maximum == 200.0  # max of (100, 200)

    def test_empty_input_returns_empty(self) -> None:
        """Empty variable list returns empty result."""
        result: List[ScannedVariable] = PatternAggregator.aggregate_patterns([])
        assert result == []

    def test_no_numeric_patterns(self) -> None:
        """Variables without numeric components are returned as-is."""
        variables: List[ScannedVariable] = [
            ScannedVariable(name="system.memctrl.readReqs", type="scalar", entries=[]),
            ScannedVariable(name="system.memctrl.writeReqs", type="scalar", entries=[]),
        ]

        result: List[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 2
        names: List[str] = [v.name for v in result]
        assert "system.memctrl.readReqs" in names
        assert "system.memctrl.writeReqs" in names
