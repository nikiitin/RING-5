"""Tests for matplotlib_trace_renderer — draws TraceConfig on matplotlib axes."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, cast

import matplotlib
import matplotlib.axes
import matplotlib.pyplot as plt
import pytest

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.web.rendering.matplotlib_trace_renderer import (
    MatplotlibTraceRenderer,
    _compute_categorical_positions,
    _stack_bottom,
    _stack_bottom_numeric,
)

matplotlib.use("Agg")


@pytest.fixture
def ax() -> Generator[matplotlib.axes.Axes]:
    """Fresh matplotlib axes for each test."""
    fig, axes = plt.subplots()
    yield axes
    plt.close(fig)


# ── render (main entry) ─────────────────────────────────────────────


class TestRender:
    """Tests for ``MatplotlibTraceRenderer.render``."""

    def test_empty_traces(self, ax: matplotlib.axes.Axes) -> None:
        count = MatplotlibTraceRenderer.render([], ax)
        assert count == 0

    def test_single_bar(self, ax: matplotlib.axes.Axes) -> None:
        trace = BarTraceConfig(name="s1", x=["a", "b"], y=[1, 2])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_single_line(self, ax: matplotlib.axes.Axes) -> None:
        trace = LineTraceConfig(name="l1", x=[0, 1], y=[1, 2])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_single_scatter(self, ax: matplotlib.axes.Axes) -> None:
        trace = ScatterTraceConfig(name="sc", x=[0, 1], y=[1, 2])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_single_histogram(self, ax: matplotlib.axes.Axes) -> None:
        trace = HistogramTraceConfig(name="h1", x=[1, 2, 3, 4, 5])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_mixed_traces(self, ax: matplotlib.axes.Axes) -> None:
        traces = [
            BarTraceConfig(name="bar", x=["a", "b"], y=[1, 2]),
            LineTraceConfig(name="line", x=[0, 1], y=[3, 4]),
        ]
        count = MatplotlibTraceRenderer.render(traces, ax)
        assert count == 2

    def test_palette_colors_applied(self, ax: matplotlib.axes.Axes) -> None:
        trace = BarTraceConfig(name="b", x=["a"], y=[1])
        count = MatplotlibTraceRenderer.render([trace], ax, palette_colors=["#ff0000"])
        assert count == 1

    def test_secondary_y_creates_twin(self, ax: matplotlib.axes.Axes) -> None:
        t1 = BarTraceConfig(name="left", x=["a"], y=[1], yaxis="y")
        t2 = LineTraceConfig(name="right", x=[0], y=[2], yaxis="y2")
        MatplotlibTraceRenderer.render([t1, t2], ax)
        # Ensure Pyright is happy with private attribute access in tests
        assert cast(Any, ax)._ring5_twin is not None

    def test_stacked_bars(self, ax: matplotlib.axes.Axes) -> None:
        traces = [
            BarTraceConfig(name="b1", x=["a", "b"], y=[1, 2]),
            BarTraceConfig(name="b2", x=["a", "b"], y=[3, 4]),
        ]
        count = MatplotlibTraceRenderer.render(traces, ax, barmode="stack")
        assert count == 2

    def test_bar_with_border_width(self, ax: matplotlib.axes.Axes) -> None:
        trace = BarTraceConfig(name="b", x=["a"], y=[1])
        count = MatplotlibTraceRenderer.render([trace], ax, bar_border_width=1.5)
        assert count == 1

    def test_bar_with_x_positions(self, ax: matplotlib.axes.Axes) -> None:
        """Pre-computed x_positions bypass categorical positioning."""
        trace = BarTraceConfig(
            name="b",
            x=["a", "b"],
            y=[1, 2],
            x_positions=[0.5, 1.5],
            bar_width=0.3,
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_line_with_dash(self, ax: matplotlib.axes.Axes) -> None:
        trace = LineTraceConfig(name="dashed", x=[0, 1], y=[1, 2], line_dash="dash")
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_scatter_with_color(self, ax: matplotlib.axes.Axes) -> None:
        trace = ScatterTraceConfig(name="colored", x=[0, 1], y=[1, 2], color="#00ff00")
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_histogram_with_color(self, ax: matplotlib.axes.Axes) -> None:
        trace = HistogramTraceConfig(name="colored", x=[1, 2, 3], color="#0000ff", nbins=5)
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_none_y_values_handled(self, ax: matplotlib.axes.Axes) -> None:
        """None values in y should be converted to NaN gracefully."""
        trace = BarTraceConfig(name="nans", x=["a", "b"], y=[1, None])  # type: ignore[list-item]
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 1

    def test_unknown_trace_type_logged(self, ax: matplotlib.axes.Axes) -> None:
        """Unknown TraceConfig subtype should log warning, not crash."""
        trace = TraceConfig(name="unknown", x=["a"], y=[1])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count == 0  # fallback doesn't match specific types


# ── _compute_categorical_positions ──────────────────────────────────


class TestComputeCategoricalPositions:
    """Tests for categorical bar positioning helper."""

    def test_single_trace_stack(self) -> None:
        spec = BarTraceConfig(x=["a", "b"], y=[1, 2])
        positions, width = _compute_categorical_positions(spec, 0, [spec], "stack")
        assert len(positions) == 2
        assert width > 0

    def test_single_trace_group(self) -> None:
        spec = BarTraceConfig(x=["a", "b"], y=[1, 2])
        positions, width = _compute_categorical_positions(spec, 0, [spec], "group")
        assert len(positions) == 2
        assert width > 0

    def test_two_traces_grouped(self) -> None:
        s1 = BarTraceConfig(x=["a", "b"], y=[1, 2])
        s2 = BarTraceConfig(x=["a", "b"], y=[3, 4])
        p1, w1 = _compute_categorical_positions(s1, 0, [s1, s2], "group")
        p2, w2 = _compute_categorical_positions(s2, 1, [s1, s2], "group")
        # Second trace should be offset from first
        assert p1[0] != p2[0]
        assert w1 == w2

    def test_bargap_reduces_width(self) -> None:
        spec = BarTraceConfig(x=["a"], y=[1])
        _, w_small = _compute_categorical_positions(spec, 0, [spec], "stack", bargap=0.1)
        _, w_large = _compute_categorical_positions(spec, 0, [spec], "stack", bargap=0.5)
        assert w_small > w_large

    def test_bargroupgap(self) -> None:
        s1 = BarTraceConfig(x=["a"], y=[1])
        s2 = BarTraceConfig(x=["a"], y=[2])
        _, w_no_gap = _compute_categorical_positions(s1, 0, [s1, s2], "group", bargroupgap=0.0)
        _, w_with_gap = _compute_categorical_positions(s1, 0, [s1, s2], "group", bargroupgap=0.5)
        assert w_no_gap > w_with_gap


# ── _stack_bottom ────────────────────────────────────────────────────


class TestStackBottom:
    """Tests for cumulative stacking helpers."""

    def test_first_bar_zero_bottom(self) -> None:
        s1 = BarTraceConfig(x=["a", "b"], y=[1, 2])
        bottom = _stack_bottom(0, [s1])
        assert bottom == [0.0, 0.0]

    def test_second_bar_accumulates(self) -> None:
        s1 = BarTraceConfig(x=["a", "b"], y=[1, 2])
        s2 = BarTraceConfig(x=["a", "b"], y=[3, 4])
        bottom = _stack_bottom(1, [s1, s2])
        assert bottom == [1.0, 2.0]

    def test_third_bar_accumulates_all(self) -> None:
        s1 = BarTraceConfig(x=["a", "b"], y=[1, 2])
        s2 = BarTraceConfig(x=["a", "b"], y=[3, 4])
        s3 = BarTraceConfig(x=["a", "b"], y=[5, 6])
        bottom = _stack_bottom(2, [s1, s2, s3])
        assert bottom == [4.0, 6.0]

    def test_none_values_treated_as_zero(self) -> None:
        s1 = BarTraceConfig(x=["a"], y=[None])  # type: ignore[list-item]
        s2 = BarTraceConfig(x=["a"], y=[5])
        bottom = _stack_bottom(1, [s1, s2])
        assert bottom == [0.0]


class TestStackBottomNumeric:
    """Tests for numeric-axis stacking."""

    def test_matching_positions(self) -> None:
        s1 = BarTraceConfig(x=[], y=[1, 2], x_positions=[0.5, 1.5])
        s2 = BarTraceConfig(x=[], y=[3, 4], x_positions=[0.5, 1.5])
        bottom = _stack_bottom_numeric(1, [s1, s2], [0.5, 1.5])
        assert bottom == [1.0, 2.0]

    def test_no_matching_positions(self) -> None:
        s1 = BarTraceConfig(x=[], y=[1], x_positions=[0.5])
        s2 = BarTraceConfig(x=[], y=[3], x_positions=[5.0])
        # Positions don't match, so bottom remains 0
        bottom = _stack_bottom_numeric(1, [s1, s2], [5.0])
        assert bottom == [0.0]
