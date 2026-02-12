"""
Tests for FigureEngine — the Streamlit-free figure creation facade.

Validates:
    1. Creator registration and dispatch
    2. Build pipeline: create → style → legend labels
    3. Error handling for unregistered types
    4. Protocol compliance (any object with create_figure works)
    5. Custom styler injection
    6. Legend label application
    7. from_plot convenience factory
"""

from typing import Any, Dict
from unittest.mock import MagicMock

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.figures.engine import FigureEngine

# ─── Test Fixtures ───────────────────────────────────────────────────────────


class FakeCreator:
    """Minimal FigureCreator for testing — returns a simple bar figure."""

    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        fig: go.Figure = go.Figure()
        fig.add_trace(
            go.Bar(
                x=list(data[config["x"]]),
                y=list(data[config["y"]]),
                name="test_trace",
            )
        )
        return fig


class FakeStyler:
    """Minimal FigureStyler for testing — adds title from config."""

    def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        title: str = config.get("title", "Untitled")
        fig.update_layout(title_text=title)
        return fig


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Simple test DataFrame."""
    return pd.DataFrame({"benchmark": ["A", "B", "C"], "ipc": [1.2, 1.5, 0.9]})


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Minimal config for testing."""
    return {"x": "benchmark", "y": "ipc", "title": "IPC by Benchmark"}


@pytest.fixture
def engine() -> FigureEngine:
    """Pre-wired engine with fake creator and styler."""
    eng: FigureEngine = FigureEngine()
    eng.register("bar", FakeCreator())
    eng.register_styler("bar", FakeStyler())
    return eng


# ─── Registration Tests ─────────────────────────────────────────────────────


class TestFigureEngineRegistration:
    """Registration and type management."""

    def test_register_creator(self) -> None:
        """Registering a creator makes it available."""
        eng: FigureEngine = FigureEngine()
        eng.register("scatter", FakeCreator())
        assert eng.has_creator("scatter")

    def test_has_creator_false_for_unknown(self) -> None:
        """Unknown type returns False."""
        eng: FigureEngine = FigureEngine()
        assert not eng.has_creator("nonexistent")

    def test_registered_types(self) -> None:
        """registered_types returns all registered type keys."""
        eng: FigureEngine = FigureEngine()
        eng.register("bar", FakeCreator())
        eng.register("line", FakeCreator())
        assert sorted(eng.registered_types) == ["bar", "line"]

    def test_registered_types_empty(self) -> None:
        """Empty engine has no registered types."""
        eng: FigureEngine = FigureEngine()
        assert eng.registered_types == []

    def test_register_without_styler(self) -> None:
        """Registering a creator without styler leaves _stylers empty."""
        eng: FigureEngine = FigureEngine()
        eng.register("bar", FakeCreator())
        assert "bar" not in eng._stylers

    def test_register_with_styler(self) -> None:
        """Registering a creator with a styler stores both."""
        eng: FigureEngine = FigureEngine()
        custom_styler: FakeStyler = FakeStyler()
        eng.register("bar", FakeCreator(), styler=custom_styler)
        assert "bar" in eng._stylers
        assert eng._stylers["bar"] is custom_styler

    def test_register_preserves_custom_styler(self) -> None:
        """Custom styler via register_styler is not overwritten by register."""
        eng: FigureEngine = FigureEngine()
        custom_styler: FakeStyler = FakeStyler()
        eng.register_styler("bar", custom_styler)
        eng.register("bar", FakeCreator())  # No styler argument
        assert eng._stylers["bar"] is custom_styler

    def test_register_overwrites_creator(self) -> None:
        """Re-registering a creator replaces the previous one."""
        eng: FigureEngine = FigureEngine()
        creator1: FakeCreator = FakeCreator()
        creator2: FakeCreator = FakeCreator()
        eng.register("bar", creator1)
        eng.register("bar", creator2)
        assert eng._creators["bar"] is creator2


# ─── Build Pipeline Tests ────────────────────────────────────────────────────


class TestFigureEngineBuild:
    """Build pipeline: create → style → legend labels."""

    def test_build_returns_figure(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Build returns a go.Figure."""
        fig: go.Figure = engine.build("bar", sample_data, sample_config)
        assert isinstance(fig, go.Figure)

    def test_build_applies_creator(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Build calls the creator (figure has traces)."""
        fig: go.Figure = engine.build("bar", sample_data, sample_config)
        assert len(fig.data) == 1
        assert fig.data[0].type == "bar"

    def test_build_applies_styler(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Build calls the styler (title is applied)."""
        fig: go.Figure = engine.build("bar", sample_data, sample_config)
        assert fig.layout.title.text == "IPC by Benchmark"

    def test_build_applies_legend_labels(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Legend labels in config are applied to trace names."""
        sample_config["legend_labels"] = {"test_trace": "Custom Name"}
        fig: go.Figure = engine.build("bar", sample_data, sample_config)
        assert fig.data[0].name == "Custom Name"

    def test_build_without_legend_labels(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """No legend_labels key — trace names unchanged."""
        fig: go.Figure = engine.build("bar", sample_data, sample_config)
        assert fig.data[0].name == "test_trace"

    def test_build_with_empty_legend_labels(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Empty legend_labels dict — trace names unchanged."""
        sample_config["legend_labels"] = {}
        fig: go.Figure = engine.build("bar", sample_data, sample_config)
        assert fig.data[0].name == "test_trace"

    def test_build_legend_labels_partial_match(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Legend labels only applied to matching trace names."""
        sample_config["legend_labels"] = {"nonexistent": "Renamed"}
        fig: go.Figure = engine.build("bar", sample_data, sample_config)
        assert fig.data[0].name == "test_trace"  # Not renamed

    def test_build_without_styler(
        self, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Build works without a styler — skips styling step."""
        eng: FigureEngine = FigureEngine()
        eng.register("bar", FakeCreator())
        # No styler registered — should still build successfully
        fig: go.Figure = eng.build("bar", sample_data, sample_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1


# ─── Error Handling Tests ────────────────────────────────────────────────────


class TestFigureEngineErrors:
    """Error cases."""

    def test_build_unregistered_type_raises(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Building with an unregistered type raises KeyError."""
        with pytest.raises(KeyError, match="No figure creator registered for 'unknown'"):
            engine.build("unknown", sample_data, sample_config)

    def test_error_message_lists_available_types(
        self, engine: FigureEngine, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Error message includes available types."""
        with pytest.raises(KeyError, match="bar"):
            engine.build("unknown", sample_data, sample_config)


# ─── Protocol Compliance Tests ───────────────────────────────────────────────


class TestProtocolCompliance:
    """Verify that any object satisfying the protocol works."""

    def test_mock_creator_works(
        self, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """MagicMock with create_figure works as a creator."""
        mock_creator: MagicMock = MagicMock()
        mock_creator.create_figure.return_value = go.Figure(data=[go.Bar(x=["A"], y=[1.0])])

        mock_styler: MagicMock = MagicMock()
        mock_styler.apply_styles.side_effect = lambda fig, _: fig

        eng: FigureEngine = FigureEngine()
        eng.register("test", mock_creator)
        eng.register_styler("test", mock_styler)

        fig: go.Figure = eng.build("test", sample_data, sample_config)

        mock_creator.create_figure.assert_called_once_with(sample_data, sample_config)
        mock_styler.apply_styles.assert_called_once()
        assert isinstance(fig, go.Figure)

    def test_lambda_creator_works(
        self, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """An object wrapping a lambda satisfies FigureCreator."""

        class LambdaCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4])])

        eng: FigureEngine = FigureEngine()
        eng.register("lambda", LambdaCreator())
        eng.register_styler("lambda", FakeStyler())

        fig: go.Figure = eng.build("lambda", sample_data, sample_config)
        assert fig.data[0].type == "scatter"


# ─── Custom Styler Tests ────────────────────────────────────────────────────


class TestCustomStyler:
    """Custom styler injection."""

    def test_custom_styler_is_used(
        self, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Registered custom styler is called instead of default."""
        calls: list[bool] = []

        class TrackingStyler:
            def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
                calls.append(True)
                fig.update_layout(title_text="From Custom Styler")
                return fig

        eng: FigureEngine = FigureEngine()
        eng.register("bar", FakeCreator())
        eng.register_styler("bar", TrackingStyler())

        fig: go.Figure = eng.build("bar", sample_data, sample_config)
        assert len(calls) == 1
        assert fig.layout.title.text == "From Custom Styler"


# ─── Factory Tests ───────────────────────────────────────────────────────────


class TestFromPlotFactory:
    """from_plot convenience factory."""

    def test_from_plot_registers_type(self) -> None:
        """from_plot creates an engine with the plot registered."""
        creator: FakeCreator = FakeCreator()
        eng: FigureEngine = FigureEngine.from_plot(creator, "scatter")
        assert eng.has_creator("scatter")

    def test_from_plot_builds(self, sample_data: pd.DataFrame) -> None:
        """Engine from from_plot can build figures."""
        creator: FakeCreator = FakeCreator()
        eng: FigureEngine = FigureEngine.from_plot(creator, "bar")
        eng.register_styler("bar", FakeStyler())

        config: Dict[str, Any] = {
            "x": "benchmark",
            "y": "ipc",
            "title": "Test",
        }
        fig: go.Figure = eng.build("bar", sample_data, config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1


# ─── Multi-Type Tests ────────────────────────────────────────────────────────


class TestMultiTypeEngine:
    """Engine with multiple plot types registered."""

    def test_dispatch_to_correct_creator(
        self, sample_data: pd.DataFrame, sample_config: Dict[str, Any]
    ) -> None:
        """Each plot type dispatches to its own creator."""

        class BarCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure(data=[go.Bar(x=["A"], y=[1])])

        class LineCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure(data=[go.Scatter(x=[1], y=[2], mode="lines")])

        eng: FigureEngine = FigureEngine()
        eng.register("bar", BarCreator())
        eng.register("line", LineCreator())
        eng.register_styler("bar", FakeStyler())
        eng.register_styler("line", FakeStyler())

        bar_fig: go.Figure = eng.build("bar", sample_data, sample_config)
        line_fig: go.Figure = eng.build("line", sample_data, sample_config)

        assert bar_fig.data[0].type == "bar"
        assert line_fig.data[0].type == "scatter"
