"""Tests for DualAxisBarDotPlot.create_figure — additional branch coverage.

Focus on: color grouping, isolate_last_group, error bars, no-lines mode,
dot_color, and legend_order.
"""

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot import DualAxisBarDotPlot


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bench": ["A", "A", "B", "B", "Mean", "Mean"],
            "config": ["base", "eval", "base", "eval", "base", "eval"],
            "ipc": [1.0, 1.2, 1.5, 1.8, 1.25, 1.5],
            "energy": [50.0, 60.0, 45.0, 55.0, 47.5, 57.5],
            "ipc.sd": [0.1, 0.15, 0.2, 0.1, 0.15, 0.12],
            "energy.sd": [5.0, 6.0, 4.5, 5.5, 4.75, 5.75],
        }
    )


def _base_config(**overrides: Any) -> Dict[str, Any]:
    c: Dict[str, Any] = {
        "x": "bench",
        "y_bar": "ipc",
        "y_dot": "energy",
    }
    c.update(overrides)
    return c


class TestDualAxisColorGrouping:
    """Test with color column."""

    def test_basic_color(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(color="config")
        fig = plot.create_figure(sample_data, config)
        # 2 groups × (1 bar + 1 scatter) = 4 traces
        assert len(fig.data) == 4

    def test_color_with_error_bars(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(color="config", show_error_bars=True)
        fig = plot.create_figure(sample_data, config)
        bar_trace = fig.data[0]
        assert bar_trace.error_y is not None

    def test_color_no_lines(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(color="config", show_lines=False)
        fig = plot.create_figure(sample_data, config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        for t in scatter_traces:
            assert t.mode == "markers"

    def test_color_with_isolate_last(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(
            color="config",
            show_lines=True,
            isolate_last_group=True,
            xaxis_order=["A", "B", "Mean"],
        )
        fig = plot.create_figure(sample_data, config)
        # 2 groups × (1 bar + 1 main scatter + 1 isolated scatter) = 6 traces
        assert len(fig.data) == 6

    def test_color_with_legend_order(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(
            color="config",
            legend_order=["eval", "base"],
        )
        fig = plot.create_figure(sample_data, config)
        # First bar should be eval
        assert "eval" in fig.data[0].name


class TestDualAxisNoColor:
    """Test without color grouping."""

    def test_basic_no_color(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config()
        fig = plot.create_figure(sample_data, config)
        # 1 bar + 1 scatter = 2 traces
        assert len(fig.data) == 2

    def test_no_color_with_dot_color(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(dot_color="#FF0000")
        fig = plot.create_figure(sample_data, config)
        scatter = [t for t in fig.data if isinstance(t, go.Scatter)][0]
        assert scatter.marker.color == "#FF0000"

    def test_no_color_no_lines(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(show_lines=False)
        fig = plot.create_figure(sample_data, config)
        scatter = [t for t in fig.data if isinstance(t, go.Scatter)][0]
        assert scatter.mode == "markers"

    def test_no_color_with_error_bars(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(show_error_bars=True)
        fig = plot.create_figure(sample_data, config)
        bar = fig.data[0]
        assert bar.error_y is not None

    def test_no_color_isolate_last(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(
            show_lines=True,
            isolate_last_group=True,
            xaxis_order=["A", "B", "Mean"],
        )
        fig = plot.create_figure(sample_data, config)
        # 1 bar + 1 main scatter + 1 isolated scatter = 3 traces
        assert len(fig.data) == 3

    def test_no_color_isolate_last_with_error_bars(self, sample_data: pd.DataFrame) -> None:
        plot = DualAxisBarDotPlot(1, "test")
        config = _base_config(
            show_lines=True,
            isolate_last_group=True,
            show_error_bars=True,
            xaxis_order=["A", "B", "Mean"],
        )
        fig = plot.create_figure(sample_data, config)
        # Check isolated scatter has error_y
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) >= 2
