"""Tests for BarPlot and LinePlot create_figure + get_legend_column."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.bar_plot import BarPlot
from src.web.pages.ui.plotting.types.line_plot import LinePlot


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["A", "A", "B", "B"],
            "protocol": ["P1", "P2", "P1", "P2"],
            "ipc": [1.0, 2.0, 1.5, 2.5],
            "ipc.sd": [0.1, 0.2, 0.15, 0.25],
        }
    )


# ── BarPlot ──────────────────────────────────────────────────────────


class TestBarPlotCreateFigure:
    """Tests for BarPlot.create_figure branches."""

    def test_basic_bar(self, sample_data: pd.DataFrame) -> None:
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

    def test_bar_with_color(self, sample_data: pd.DataFrame) -> None:
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "color": "protocol",
            "title": "IPC by Protocol",
            "xlabel": "Bench",
            "ylabel": "IPC",
        }
        fig = plot.create_figure(sample_data, config)
        assert len(fig.data) >= 2  # one trace per color

    def test_bar_with_error_bars(self, sample_data: pd.DataFrame) -> None:
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
            "show_error_bars": True,
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_bar_error_bars_no_sd_column(self) -> None:
        data = pd.DataFrame({"x": ["A", "B"], "y": [1.0, 2.0]})
        plot = BarPlot(1, "test")
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

    def test_bar_with_xaxis_order(self, sample_data: pd.DataFrame) -> None:
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "xaxis_order": ["B", "A"],
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_bar_with_legend_order(self, sample_data: pd.DataFrame) -> None:
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "color": "protocol",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_order": ["P2", "P1"],
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_get_legend_column_with_color(self) -> None:
        plot = BarPlot(1, "test")
        assert plot.get_legend_column({"color": "protocol"}) == "protocol"

    def test_get_legend_column_without_color(self) -> None:
        plot = BarPlot(1, "test")
        assert plot.get_legend_column({}) is None


# ── LinePlot ─────────────────────────────────────────────────────────


class TestLinePlotCreateFigure:
    """Tests for LinePlot.create_figure branches."""

    def test_basic_line(self, sample_data: pd.DataFrame) -> None:
        plot = LinePlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_line_with_color(self, sample_data: pd.DataFrame) -> None:
        plot = LinePlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "color": "protocol",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
        }
        fig = plot.create_figure(sample_data, config)
        assert len(fig.data) >= 2

    def test_line_with_error_bars(self, sample_data: pd.DataFrame) -> None:
        plot = LinePlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
            "show_error_bars": True,
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_line_error_bars_no_sd(self) -> None:
        data = pd.DataFrame({"x": ["A", "B"], "y": [1.0, 2.0]})
        plot = LinePlot(1, "test")
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

    def test_line_sorts_by_x(self) -> None:
        data = pd.DataFrame({"x": [3, 1, 2], "y": [30, 10, 20]})
        plot = LinePlot(1, "test")
        config = {
            "x": "x",
            "y": "y",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
        }
        fig = plot.create_figure(data, config)
        assert isinstance(fig, go.Figure)

    def test_line_xaxis_is_category(self, sample_data: pd.DataFrame) -> None:
        plot = LinePlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
        }
        fig = plot.create_figure(sample_data, config)
        assert fig.layout.xaxis.type == "category"

    def test_get_legend_column(self) -> None:
        plot = LinePlot(1, "test")
        assert plot.get_legend_column({"color": "protocol"}) == "protocol"
        assert plot.get_legend_column({}) is None
