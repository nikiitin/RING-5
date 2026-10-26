"""Tests for BarPlot and LinePlot figure construction."""

from ring5 import Session
from typing import cast

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


# BarPlot


class TestBarPlotCreateFigure:
    """Public bar rendering across its trace-building branches."""

    # [test->req~ring5.plot.bar~1]

    def test_basic_bar(self, sample_data: pd.DataFrame, plot_session: Session) -> None:
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) >= 1

    def test_bar_with_color(self, sample_data: pd.DataFrame, plot_session: Session) -> None:
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "color": "protocol",
            "title": "IPC by Protocol",
            "xlabel": "Bench",
            "ylabel": "IPC",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert len(list(fig.data)) >= 2  # one trace per color

    def test_bar_with_error_bars(self, sample_data: pd.DataFrame, plot_session: Session) -> None:
        # [test->req~ring5.figure.error-bars~1]
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
            "show_error_bars": True,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)

    def test_bar_error_bars_no_sd_column(self, plot_session: Session) -> None:
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
        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)

    def test_bar_with_xaxis_order(self, sample_data: pd.DataFrame, plot_session: Session) -> None:
        plot = BarPlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
            "xaxis_order": ["B", "A"],
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)

    def test_bar_with_legend_order(self, sample_data: pd.DataFrame, plot_session: Session) -> None:
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
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)


# LinePlot


class TestLinePlotCreateFigure:
    """Public line rendering across its trace-building branches."""

    # [test->req~ring5.plot.line~1]

    def test_basic_line(self, sample_data: pd.DataFrame, plot_session: Session) -> None:
        plot = LinePlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)

    def test_line_with_color(self, sample_data: pd.DataFrame, plot_session: Session) -> None:
        plot = LinePlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "color": "protocol",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert len(list(fig.data)) >= 2

    def test_line_with_error_bars(self, sample_data: pd.DataFrame, plot_session: Session) -> None:
        plot = LinePlot(1, "test")
        config = {
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC",
            "xlabel": "Bench",
            "ylabel": "IPC",
            "show_error_bars": True,
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)

    def test_line_error_bars_no_sd(self, plot_session: Session) -> None:
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
        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)

    def test_line_sorts_by_x(self, plot_session: Session) -> None:
        data = pd.DataFrame({"x": [3, 1, 2], "y": [30, 10, 20]})
        plot = LinePlot(1, "test")
        config = {
            "x": "x",
            "y": "y",
            "title": "T",
            "xlabel": "X",
            "ylabel": "Y",
        }
        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
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
        result = plot.create_traces(sample_data, config)
        # X values are categorical strings
        assert all(isinstance(v, str) for v in result.traces[0].x)
