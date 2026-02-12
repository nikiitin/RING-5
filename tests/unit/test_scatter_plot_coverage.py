"""Tests for ScatterPlot create_figure — 50% → 90%+."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4],
            "y": [10, 20, 15, 25],
            "category": ["A", "B", "A", "B"],
            "y.sd": [1.0, 2.0, 1.5, 2.5],
        }
    )


class TestScatterPlotCreateFigure:
    """Tests for ScatterPlot.create_figure."""

    def test_basic_scatter(self, sample_data: pd.DataFrame) -> None:
        plot = ScatterPlot(1, "test")
        config = {"x": "x", "y": "y", "title": "T", "xlabel": "X", "ylabel": "Y"}
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

    def test_scatter_with_color(self, sample_data: pd.DataFrame) -> None:
        plot = ScatterPlot(1, "test")
        config = {
            "x": "x",
            "y": "y",
            "color": "category",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
        }
        fig = plot.create_figure(sample_data, config)
        assert len(fig.data) >= 2

    def test_scatter_with_error_bars(self, sample_data: pd.DataFrame) -> None:
        plot = ScatterPlot(1, "test")
        config = {
            "x": "x",
            "y": "y",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "show_error_bars": True,
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_scatter_error_no_sd_col(self) -> None:
        data = pd.DataFrame({"x": [1], "y": [2]})
        plot = ScatterPlot(1, "test")
        config = {
            "x": "x",
            "y": "y",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "show_error_bars": True,
        }
        fig = plot.create_figure(data, config)
        assert isinstance(fig, go.Figure)

    def test_get_legend_column_with_color(self) -> None:
        plot = ScatterPlot(1, "test")
        assert plot.get_legend_column({"color": "cat"}) == "cat"

    def test_get_legend_column_without_color(self) -> None:
        plot = ScatterPlot(1, "test")
        assert plot.get_legend_column({}) is None
