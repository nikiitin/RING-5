"""Tests for the new plot class hierarchy."""

from ring5 import Session

from typing import Any, Literal, cast

import pandas as pd
import plotly.graph_objects as go
import pytest
from pandas import DataFrame

from src.web.pages.ui.plotting import (
    BarPlot,
    GroupedBarPlot,
    GroupedStackedBarPlot,
    LinePlot,
    PlotFactory,
    ScatterPlot,
)


@pytest.fixture
def sample_data() -> DataFrame:
    """Create sample data for testing."""
    return pd.DataFrame(
        {
            "category": ["A", "B", "C", "A", "B", "C"],
            "value": [10, 20, 15, 12, 18, 16],
            "group": ["G1", "G1", "G1", "G2", "G2", "G2"],
            "stack": ["S1", "S1", "S2", "S1", "S2", "S2"],
        }
    )


class TestPlotFactory:
    """Test the PlotFactory."""

    def test_create_bar_plot(self) -> None:
        """Test creating a bar plot."""
        plot = PlotFactory.create_plot("bar", 1, "Test Bar")
        assert isinstance(plot, BarPlot)
        assert plot.plot_id == 1
        assert plot.name == "Test Bar"
        assert plot.plot_type == "bar"

    def test_create_grouped_bar_plot(self) -> None:
        """Test creating a grouped bar plot."""
        plot = PlotFactory.create_plot("grouped_bar", 2, "Test Grouped")
        assert isinstance(plot, GroupedBarPlot)
        assert plot.plot_type == "grouped_bar"

    def test_create_grouped_stacked_bar_plot(self) -> None:
        """Test creating a grouped stacked bar plot."""
        plot = PlotFactory.create_plot("grouped_stacked_bar", 3, "Test Stacked")
        assert isinstance(plot, GroupedStackedBarPlot)
        assert plot.plot_type == "grouped_stacked_bar"

    def test_create_line_plot(self) -> None:
        """Test creating a line plot."""
        plot = PlotFactory.create_plot("line", 4, "Test Line")
        assert isinstance(plot, LinePlot)
        assert plot.plot_type == "line"

    def test_create_scatter_plot(self) -> None:
        """Test creating a scatter plot."""
        plot = PlotFactory.create_plot("scatter", 5, "Test Scatter")
        assert isinstance(plot, ScatterPlot)
        assert plot.plot_type == "scatter"

    def test_invalid_plot_type(self) -> None:
        """Test that invalid plot type raises error."""
        with pytest.raises(ValueError, match="Unknown plot type"):
            PlotFactory.create_plot("invalid", 1, "Test")

    def test_get_available_plot_types(self) -> None:
        """Test getting available plot types."""
        types = PlotFactory.get_available_plot_types()
        assert "bar" in types
        assert "grouped_bar" in types
        assert "grouped_stacked_bar" in types
        assert "line" in types
        assert "scatter" in types


class TestBarPlot:
    """Test BarPlot functionality."""

    def test_initialization(self) -> None:
        """Test bar plot initialization."""
        plot = BarPlot(1, "My Plot")
        assert plot.plot_id == 1
        assert plot.name == "My Plot"
        assert plot.plot_type == "bar"
        assert plot.config == {}
        assert plot.processed_data is None

    def test_create_figure(self, sample_data: Any, plot_session: Session) -> None:
        """Test creating a figure."""
        plot = BarPlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "color": None,
            "title": "Test Plot",
            "xlabel": "Category",
            "ylabel": "Value",
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert fig is not None
        assert len(list(fig.data)) > 0

    def test_to_dict(self, sample_data: Any) -> None:
        """Test serialization to dictionary."""
        plot = BarPlot(1, "Test")
        plot.processed_data = sample_data
        plot.config = {"x": "category", "y": "value"}
        plot.pipeline = cast(Any, [{"id": 0, "type": "columnSelector", "config": {}}])

        data_dict = plot.to_dict()
        assert data_dict["id"] == 1
        assert data_dict["name"] == "Test"
        assert data_dict["plot_type"] == "bar"
        assert data_dict["config"] == {"x": "category", "y": "value"}
        assert data_dict["processed_data"]["format"] == "ring5.typed-table"
        assert data_dict["pipeline"] == [{"id": 0, "type": "columnSelector", "config": {}}]


class TestGroupedBarPlot:
    """Test GroupedBarPlot functionality."""

    def test_create_figure(self, sample_data: Any, plot_session: Session) -> None:
        """Test creating a grouped bar figure."""
        plot = GroupedBarPlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "group": "group",
            "title": "Test Plot",
            "xlabel": "Category",
            "ylabel": "Value",
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert fig is not None
        assert len(list(fig.data)) >= 2  # Multiple groups


class TestGroupedStackedBarPlot:
    """Test GroupedStackedBarPlot functionality."""

    def test_create_figure(self, sample_data: Any, plot_session: Session) -> None:
        """Test creating a grouped stacked bar figure."""
        plot = GroupedStackedBarPlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "group": "group",
            "stack": "stack",
            "title": "Test Plot",
            "xlabel": "Category",
            "ylabel": "Value",
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert fig is not None


class TestLinePlot:
    """Test LinePlot functionality."""

    def test_create_figure(self, sample_data: Any, plot_session: Session) -> None:
        """Test creating a line figure."""
        plot = LinePlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "color": "group",
            "title": "Test Plot",
            "xlabel": "Category",
            "ylabel": "Value",
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert fig is not None


class TestScatterPlot:
    """Test ScatterPlot functionality."""

    def test_create_figure(self, sample_data: Any, plot_session: Session) -> None:
        """Test creating a scatter figure."""
        plot = ScatterPlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "color": "group",
            "title": "Test Plot",
            "xlabel": "Category",
            "ylabel": "Value",
            "show_error_bars": False,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert fig is not None


class TestPlotSerialization:
    """Test plot serialization and deserialization."""

    def test_to_dict_and_from_dict(self, sample_data: Any) -> None:
        """Test round-trip serialization."""
        # Create and configure plot
        plot = BarPlot(1, "Test Plot")
        plot.processed_data = sample_data
        plot.config = {"x": "category", "y": "value"}
        plot.pipeline = [
            {"id": 0, "type": "columnSelector", "config": {"columns": ["category", "value"]}}  # type: ignore  # noqa: E501
        ]
        plot.config = {**plot.config, "legend_labels": {"A": "Label A", "B": "Label B"}}

        # Serialize
        data_dict = plot.to_dict()

        # Deserialize
        restored_plot = PlotFactory.from_dict(data_dict)

        assert restored_plot.plot_id == plot.plot_id
        assert restored_plot.name == plot.name
        assert restored_plot.plot_type == plot.plot_type
        assert restored_plot.config == plot.config
        assert restored_plot.pipeline == plot.pipeline
        assert restored_plot.config["legend_labels"] == plot.config["legend_labels"]
        assert restored_plot.processed_data is not None
        assert plot.processed_data is not None
        assert restored_plot.processed_data.equals(plot.processed_data)


class TestPlotCommonLayout:
    """Test common layout application."""

    def test_public_render_common_layout(self, sample_data: Any, plot_session: Session) -> None:
        """Test applying common layout settings."""
        plot = BarPlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "width": 1000,
            "height": 600,
            "legend_title": "My Legend",
            "show_error_bars": False,
        }

        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))

        assert fig.to_plotly_json()["layout"]["width"] == 1000
        assert fig.to_plotly_json()["layout"]["height"] == 600
        legend = fig.to_plotly_json()["layout"].get("legend", {})
        assert legend.get("title", {}).get("text") == "My Legend"


class TestPlotLegendLabels:
    """Test legend label customization."""

    @pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
    def test_legend_labels_applied_to_both_engines(
        self, sample_data: Any, plot_session: Session, engine: Literal["plotly", "matplotlib"]
    ) -> None:
        """Retain raw names and values while projecting actual native legend text."""
        from matplotlib.patches import Rectangle
        from src.core.models.visualization.trace_config import BarTraceConfig

        plot = BarPlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "color": "group",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "show_error_bars": False,
            "legend_labels": {"G1": "Group One", "G2": "Group Two"},
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = plot_session.render(plot, engine=engine)
        result = plot.render_artifact.trace_result
        assert result is not None
        assert [trace.name for trace in result.traces] == ["G1", "G2"]
        for trace, expected in zip(result.traces, [[10, 20, 15], [12, 18, 16]], strict=True):
            assert isinstance(trace, BarTraceConfig)
            assert trace.y == expected
        if isinstance(fig, go.Figure):
            names = []
            for native in fig.data:
                assert isinstance(native, go.Bar)
                names.append(native.name)
            assert names == ["Group One", "Group Two"]
            assert fig.layout.title.text == "Test"
        else:
            legend = fig.axes[0].get_legend()
            assert legend is not None
            assert [text.get_text() for text in legend.texts] == ["Group One", "Group Two"]
            heights = []
            for patch in fig.axes[0].patches:
                assert isinstance(patch, Rectangle)
                heights.append(patch.get_height())
            assert heights == [10, 20, 15, 12, 18, 16]
            assert fig.axes[0].get_title() == "Test"
        assert plot.config == config
