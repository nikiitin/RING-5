"""Tests for simple plot configuration and figure creation."""

from typing import Any
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
    """Tests for bar-plot configuration controls."""

    @patch("src.web.pages.ui.plotting.types.bar_plot.render_common_with_color")
    def test_config_no_saved_color(self, mock_render: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        mock_render.return_value = {
            "categorical_cols": ["benchmark", "config"],
            "numeric_cols": ["cycles", "ipc", "ipc.sd"],
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "color": None,
        }
        plot = BarPlot(1, "test")
        result = plot.render_config_ui(sample_df, {})
        assert result["color"] is None
        mock_render.assert_called_once()

    @patch("src.web.pages.ui.plotting.types.bar_plot.render_common_with_color")
    def test_config_with_saved_color(self, mock_render: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        mock_render.return_value = {
            "categorical_cols": ["benchmark", "config"],
            "numeric_cols": ["cycles", "ipc", "ipc.sd"],
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "color": "config",
        }
        plot = BarPlot(1, "test")
        result = plot.render_config_ui(sample_df, {"color": "config"})
        assert result["color"] == "config"


class TestBarPlotCreateFigure:
    """Tests for bar-plot figure creation."""

    def test_basic(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        config: dict[str, Any] = {
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
        config: dict[str, Any] = {
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
        config: dict[str, Any] = {
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
        assert len(list(fig.data)) > 0

    def test_get_legend_column_none(self) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        assert plot.get_legend_column({}) is None

    def test_get_legend_column_set(self) -> None:
        from src.web.pages.ui.plotting.types.bar_plot import BarPlot

        plot = BarPlot(1, "test")
        assert plot.get_legend_column({"color": "benchmark"}) == "benchmark"


class TestLinePlotRenderConfigUI:
    """Tests for line-plot configuration controls."""

    @patch("src.web.pages.ui.plotting.types.line_plot.render_common_with_color")
    def test_config_no_saved_color(self, mock_render: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        mock_render.return_value = {
            "categorical_cols": ["benchmark", "config"],
            "numeric_cols": ["cycles", "ipc", "ipc.sd"],
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "color": None,
        }
        plot = LinePlot(1, "test")
        result = plot.render_config_ui(sample_df, {})
        assert result["color"] is None
        mock_render.assert_called_once()

    @patch("src.web.pages.ui.plotting.types.line_plot.render_common_with_color")
    def test_config_with_saved_color(self, mock_render: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        mock_render.return_value = {
            "categorical_cols": ["benchmark", "config"],
            "numeric_cols": ["cycles", "ipc", "ipc.sd"],
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "color": "config",
        }
        plot = LinePlot(1, "test")
        result = plot.render_config_ui(sample_df, {"color": "config"})
        assert result["color"] == "config"


class TestLinePlotCreateFigure:
    """Tests for line-plot figure creation."""

    def test_basic(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        config: dict[str, Any] = {
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
        config: dict[str, Any] = {
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
        config: dict[str, Any] = {
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
    """Tests for line-plot advanced options."""

    @patch("src.web.pages.ui.plotting.types.line_plot.st")
    def test_complete_line_style(self, mock_st: MagicMock) -> None:
        # [test->req~ring5.figure.line-styles~1]
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        mock_st.selectbox.side_effect = ["Smooth spline", "Dash-dot", "diamond"]
        mock_st.number_input.side_effect = [3.5, 10]
        mock_st.checkbox.side_effect = [True, True]
        result = plot.render_specific_advanced_options(
            {
                "line_shape": "linear",
                "line_dash": "solid",
                "line_width": 2.0,
                "show_markers": True,
                "marker_symbol": "circle",
                "marker_size": 6,
                "connect_gaps": False,
            }
        )

        assert result["line_shape"] == "spline"
        assert result["line_dash"] == "dashdot"
        assert result["line_width"] == 3.5
        assert result["show_markers"] is True
        assert result["marker_symbol"] == "diamond"
        assert result["marker_size"] == 10
        assert result["connect_gaps"] is True

    @patch("src.web.pages.ui.plotting.types.line_plot.st")
    def test_line_style_falls_back_from_unknown_saved_values(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.plotting.types.line_plot import LinePlot

        plot = LinePlot(1, "test")
        mock_st.selectbox.side_effect = ["Straight", "Solid", "circle"]
        mock_st.number_input.side_effect = [2.0, 6]
        mock_st.checkbox.side_effect = [False, False]

        result = plot.render_specific_advanced_options(
            {
                "line_shape": "unknown",
                "line_dash": "unknown",
                "line_width": "wide",
                "marker_symbol": "unknown",
                "marker_size": 0,
            }
        )

        assert result["line_shape"] == "linear"
        assert result["line_dash"] == "solid"
        assert result["marker_symbol"] == "circle"
        assert result["show_markers"] is False
        assert mock_st.number_input.call_args_list[0].kwargs["value"] == 2.0
        assert mock_st.number_input.call_args_list[1].kwargs["value"] == 6


class TestScatterPlotRenderConfigUI:
    """Tests for scatter-plot configuration controls."""

    @patch("src.web.pages.ui.plotting.types.scatter_plot.render_common_with_color")
    def test_config_no_color(self, mock_render: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        mock_render.return_value = {
            "categorical_cols": ["benchmark"],
            "numeric_cols": ["cycles", "ipc", "ipc.sd"],
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "color": None,
        }
        plot = ScatterPlot(1, "test")
        result = plot.render_config_ui(sample_df, {})
        assert result["color"] is None
        mock_render.assert_called_once()

    @patch("src.web.pages.ui.plotting.types.scatter_plot.render_common_with_color")
    def test_config_with_color(self, mock_render: MagicMock, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        mock_render.return_value = {
            "categorical_cols": ["benchmark"],
            "numeric_cols": ["cycles", "ipc", "ipc.sd"],
            "x": "benchmark",
            "y": "cycles",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
            "color": "benchmark",
        }
        plot = ScatterPlot(1, "test")
        result = plot.render_config_ui(sample_df, {"color": "benchmark"})
        assert result["color"] == "benchmark"


class TestScatterPlotCreateFigure:
    """Tests for scatter-plot figure creation."""

    def test_basic(self, sample_df: pd.DataFrame) -> None:
        from src.web.pages.ui.plotting.types.scatter_plot import ScatterPlot

        plot = ScatterPlot(1, "test")
        config: dict[str, Any] = {
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
        config: dict[str, Any] = {
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
        config: dict[str, Any] = {
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
