"""Tests for simple plot types render_config_ui and create_figure — branch coverage."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["a", "b", "c"],
            "config": ["x", "y", "z"],
            "cycles": [100.0, 200.0, 300.0],
            "ipc": [0.5, 0.6, 0.7],
            "ipc.sd": [0.05, 0.06, 0.07],
        }
    )


def _make_col_mock() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


class TestBarPlotRenderConfigUI:
    """Cover BarPlot.render_config_ui branches."""

    @patch("src.web.pages.ui.plotting.types.bar_plot.st")
    def test_config_no_saved_color(self, mock_st: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        plot.render_common_config = MagicMock(
            return_value={
                "categorical_cols": ["benchmark", "config"],
                "x": "benchmark",
                "y": "cycles",
                "title": "Test",
                "xlabel": "X",
                "ylabel": "Y",
            }
        )
        mock_st.selectbox.return_value = None

        result = plot.render_config_ui(sample_df, {})
        assert result["color"] is None

    @patch("src.web.pages.ui.plotting.types.bar_plot.st")
    def test_config_with_saved_color(self, mock_st: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        plot.render_common_config = MagicMock(
            return_value={
                "categorical_cols": ["benchmark", "config"],
                "x": "benchmark",
                "y": "cycles",
                "title": "Test",
                "xlabel": "X",
                "ylabel": "Y",
            }
        )
        mock_st.selectbox.return_value = "config"

        result = plot.render_config_ui(sample_df, {"color": "config"})
        assert result["color"] == "config"


class TestBarPlotCreateFigure:
    """Cover BarPlot.create_figure branches."""

    def test_basic(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        config: Dict[str, Any] = {
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)

    def test_with_error_bars(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        config: Dict[str, Any] = {
            "x": "benchmark",
            "y": "ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "show_error_bars": True,
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)

    def test_with_color_and_orders(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        config: Dict[str, Any] = {
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "color": "config",
            "xaxis_order": ["a", "b", "c"],
            "legend_order": ["x", "y", "z"],
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_get_legend_column_none(self) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        assert plot.get_legend_column({}) is None

    def test_get_legend_column_set(self) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        assert plot.get_legend_column({"color": "benchmark"}) == "benchmark"


class TestLinePlotRenderConfigUI:
    """Cover LinePlot.render_config_ui branches."""

    @patch("src.web.pages.ui.plotting.types.line_plot.st")
    def test_config_no_saved_color(self, mock_st: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        plot.render_common_config = MagicMock(
            return_value={
                "categorical_cols": ["benchmark", "config"],
                "x": "benchmark",
                "y": "cycles",
                "title": "Test",
                "xlabel": "X",
                "ylabel": "Y",
            }
        )
        mock_st.selectbox.return_value = None

        result = plot.render_config_ui(sample_df, {})
        assert result["color"] is None

    @patch("src.web.pages.ui.plotting.types.line_plot.st")
    def test_config_with_saved_color(self, mock_st: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        plot.render_common_config = MagicMock(
            return_value={
                "categorical_cols": ["benchmark", "config"],
                "x": "benchmark",
                "y": "cycles",
                "title": "Test",
                "xlabel": "X",
                "ylabel": "Y",
            }
        )
        mock_st.selectbox.return_value = "config"

        result = plot.render_config_ui(sample_df, {"color": "config"})
        assert result["color"] == "config"


class TestLinePlotCreateFigure:
    """Cover LinePlot.create_figure branches."""

    def test_basic(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        config: Dict[str, Any] = {
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)

    def test_with_error_bars(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        config: Dict[str, Any] = {
            "x": "benchmark",
            "y": "ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "show_error_bars": True,
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)

    def test_sorts_by_x(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        config: Dict[str, Any] = {
            "x": "cycles",
            "y": "ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)

    def test_get_legend_column(self) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        assert plot.get_legend_column({}) is None
        assert plot.get_legend_column({"color": "config"}) == "config"


class TestLinePlotAdvancedOptions:
    """Cover LinePlot.render_specific_advanced_options."""

    @patch("src.web.pages.ui.plotting.types.line_plot.st")
    def test_line_shape(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        mock_st.selectbox.return_value = "spline"
        result = plot.render_specific_advanced_options({"line_shape": "linear"})
        assert result["line_shape"] == "spline"


class TestScatterPlotRenderConfigUI:
    """Cover ScatterPlot.render_config_ui branches."""

    @patch("src.web.pages.ui.plotting.types.scatter_plot.st")
    def test_config_no_color(self, mock_st: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        plot = ScatterPlot(1, "test")
        plot.render_common_config = MagicMock(
            return_value={
                "categorical_cols": ["benchmark"],
                "x": "benchmark",
                "y": "cycles",
                "title": "Test",
                "xlabel": "X",
                "ylabel": "Y",
            }
        )
        mock_st.selectbox.return_value = None

        result = plot.render_config_ui(sample_df, {})
        assert result["color"] is None

    @patch("src.web.pages.ui.plotting.types.scatter_plot.st")
    def test_config_with_color(self, mock_st: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        plot = ScatterPlot(1, "test")
        plot.render_common_config = MagicMock(
            return_value={
                "categorical_cols": ["benchmark"],
                "x": "benchmark",
                "y": "cycles",
                "title": "Test",
                "xlabel": "X",
                "ylabel": "Y",
            }
        )
        mock_st.selectbox.return_value = "benchmark"

        result = plot.render_config_ui(sample_df, {"color": "benchmark"})
        assert result["color"] == "benchmark"


class TestScatterPlotCreateFigure:
    """Cover ScatterPlot.create_figure branches."""

    def test_basic(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        plot = ScatterPlot(1, "test")
        config: Dict[str, Any] = {
            "x": "cycles",
            "y": "ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)

    def test_with_error_bars(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        plot = ScatterPlot(1, "test")
        config: Dict[str, Any] = {
            "x": "cycles",
            "y": "ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "show_error_bars": True,
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)

    def test_with_color(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        plot = ScatterPlot(1, "test")
        config: Dict[str, Any] = {
            "x": "cycles",
            "y": "ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "color": "benchmark",
        }
        fig = plot.create_figure(sample_df, config)
        assert isinstance(fig, go.Figure)

    def test_get_legend_column(self) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        plot = ScatterPlot(1, "test")
        assert plot.get_legend_column({}) is None
        assert plot.get_legend_column({"color": "benchmark"}) == "benchmark"
