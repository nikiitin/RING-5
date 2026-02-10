import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)
from src.web.pages.ui.plotting.types.line_plot import LinePlot
from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "B", "B", "C"],
            "Config": ["Low", "High", "Low", "High", "Low"],
            "Value": [10, 20, 15, 25, 30],
            "Value2": [1, 2, 1.5, 2.5, 3.0],
            "Value.sd": [0.1, 0.2, 0.15, 0.25, 0.3],
        }
    )


class TestLinePlot:
    def test_create_figure(self, sample_data):
        plot = LinePlot(1, "Test Line")
        config = {
            "x": "Benchmark",
            "y": "Value",
            "color": "Config",
            "title": "Title",
            "xlabel": "X",
            "ylabel": "Y",
            "show_error_bars": True,
        }

        fig = plot.create_figure(sample_data, config)

        assert isinstance(fig, go.Figure)
        # Check layout properties
        assert fig.layout.title.text == "Title"
        assert fig.layout.xaxis.title.text == "X"
        assert fig.layout.yaxis.title.text == "Y"
        # Check traces (should be 2, one for Low, one for High due to color split)
        assert len(fig.data) == 2


class TestScatterPlot:
    def test_create_figure(self, sample_data):
        plot = ScatterPlot(2, "Test Scatter")
        config = {
            "x": "Value",
            "y": "Value2",
            "color": "Benchmark",
            "title": "Scatter",
            "xlabel": "Val",
            "ylabel": "Val2",
        }

        fig = plot.create_figure(sample_data, config)

        assert isinstance(fig, go.Figure)
        # Check traces (3 benchmarks -> 3 traces)
        assert len(fig.data) == 3


class TestGroupedStackedBarPlot:
    def test_create_figure_grouped(self, sample_data):
        plot = GroupedStackedBarPlot(3, "Test GSB")
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Value", "Value2"],
            "title": "GSB",
            "xlabel": "Bench",
            "ylabel": "V",
            "show_error_bars": False,
        }

        fig = plot.create_figure(sample_data, config)

        assert isinstance(fig, go.Figure)
        assert fig.layout.barmode == "stack"

        # Check traces.
        # Logic: 2 Y columns -> 2 traces (Value, Value2).
        assert len(fig.data) == 2

        trace0 = fig.data[0]
        # x coordinates are custom mapped floats
        assert trace0.x is not None
        # customdata should contain totals (Value + Value2)
        total_A_Low = 10 + 1
        # Validate that the expected total value is present in customdata.
        totals = trace0.customdata
        assert total_A_Low in totals

    def test_create_figure_simple_stack(self, sample_data):
        """Test without sub-grouping."""
        plot = GroupedStackedBarPlot(4, "Simple Stack")
        config = {
            "x": "Benchmark",
            "y_columns": ["Value", "Value2"],
            "title": "Stack",
            "xlabel": "Bench",
            "ylabel": "V",
        }

        fig = plot.create_figure(sample_data, config)

        assert len(fig.data) == 2
        # x axis should simply be the Benchmark column
        # trace x should contain A, B, C etc
        assert "A" in fig.data[0].x
