"""Tests for matplotlib_trace_renderer — draws TraceConfig on matplotlib axes."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, cast

import matplotlib
import matplotlib.axes
import matplotlib.pyplot as plt
import numpy as np
import pytest

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    BoxTraceConfig,
    HeatmapTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    RadarTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
    ViolinTraceConfig,
    WaterfallTraceConfig,
)
from src.web.rendering._heatmap_utils import is_dark_cell
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


# render (main entry)


class TestRender:
    """Tests for ``MatplotlibTraceRenderer.render``."""

    def test_empty_traces(self, ax: matplotlib.axes.Axes) -> None:
        count = MatplotlibTraceRenderer.render([], ax)
        assert count.trace_count == 0

    def test_single_bar(self, ax: matplotlib.axes.Axes) -> None:
        trace = BarTraceConfig(name="s1", x=["a", "b"], y=[1, 2])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_vertical_and_horizontal_boxes_use_precomputed_statistics(
        self, ax: matplotlib.axes.Axes
    ) -> None:
        # [test->req~ring5.plot.box~1]
        vertical = BoxTraceConfig(
            name="A",
            category="A",
            values=[1.0, 2.0, 10.0],
            q1=1.5,
            median=2.0,
            q3=3.0,
            lower_whisker=1.0,
            upper_whisker=3.0,
            outliers=[10.0],
            point_mode="outliers",
            show_mean=True,
        )
        result = MatplotlibTraceRenderer.render([vertical], ax)
        assert result.trace_count == 1
        assert [tick.get_text() for tick in ax.get_xticklabels()] == ["A"]
        assert ax.collections

        fig, horizontal_ax = plt.subplots()
        try:
            horizontal = BoxTraceConfig(
                name="B",
                category="B",
                values=[2.0, 3.0],
                q1=2.25,
                median=2.5,
                q3=2.75,
                lower_whisker=2.0,
                upper_whisker=3.0,
                orientation="horizontal",
                point_mode="all",
                notched=True,
                notch_lower=2.2,
                notch_upper=2.8,
            )
            horizontal_result = MatplotlibTraceRenderer.render([horizontal], horizontal_ax)
            assert horizontal_result.trace_count == 1
            assert [tick.get_text() for tick in horizontal_ax.get_yticklabels()] == ["B"]
        finally:
            plt.close(fig)

    def test_single_line(self, ax: matplotlib.axes.Axes) -> None:
        trace = LineTraceConfig(name="l1", x=[0, 1], y=[1, 2], line_shape="hv")
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1
        assert ax.lines[0].get_drawstyle() == "steps-post"

    def test_ecdf_line_uses_post_step_drawstyle(self, ax: matplotlib.axes.Axes) -> None:
        # [test->req~ring5.plot.ecdf~1]
        trace = LineTraceConfig(name="ECDF", x=[1.0, 2.0], y=[0.5, 1.0], line_shape="hv")

        result = MatplotlibTraceRenderer.render([trace], ax)

        assert result.trace_count == 1
        assert ax.lines[0].get_drawstyle() == "steps-post"

    def test_area_line_fills_against_precomputed_baseline(self, ax: matplotlib.axes.Axes) -> None:
        # [test->req~ring5.plot.area~1]
        trace = LineTraceConfig(
            name="Area",
            x=[1.0, 2.0, 3.0],
            y=[2.0, 4.0, 5.0],
            fill="tonexty",
            fill_base=[1.0, 1.5, 2.0],
            line_shape="hv",
            color="#336699",
        )

        result = MatplotlibTraceRenderer.render([trace], ax)

        assert result.trace_count == 1
        assert len(ax.collections) == 1
        assert ax.lines[0].get_drawstyle() == "steps-post"

    def test_radar_draws_shared_frame_once_and_closed_profiles(
        self, ax: matplotlib.axes.Axes
    ) -> None:
        # [test->req~ring5.plot.radar~1]
        traces = [
            RadarTraceConfig(
                name="base",
                categories=["A", "B", "C"],
                values=[1.0, 2.0, 3.0],
                radial_max=4.0,
                color="#336699",
            ),
            RadarTraceConfig(
                name="new",
                categories=["A", "B", "C"],
                values=[2.0, 3.0, 1.0],
                radial_max=4.0,
                fill_area=False,
            ),
        ]

        result = MatplotlibTraceRenderer.render(traces, ax)

        assert result.trace_count == 2
        assert len(ax.texts) == 3
        assert len(ax.patches) == 1
        assert not ax.axison

    def test_waterfall_draws_explicit_geometry_connectors_and_labels(
        self, ax: matplotlib.axes.Axes
    ) -> None:
        # [test->req~ring5.plot.waterfall~1]
        trace = WaterfallTraceConfig(
            name="Change",
            categories=["Start", "Loss", "Subtotal"],
            values=[10.0, -3.0, 0.0],
            measures=["absolute", "relative", "total"],
            kinds=["absolute", "relative", "subtotal"],
            starts=[0.0, 10.0, 0.0],
            ends=[10.0, 7.0, 7.0],
            connector_visible=True,
            value_labels=["10", "-3", "7"],
        )

        result = MatplotlibTraceRenderer.render([trace], ax)

        assert result.trace_count == 1
        assert [tick.get_text() for tick in ax.get_xticklabels()] == trace.categories
        assert len(ax.patches) == 3
        assert len(ax.lines) == 2
        assert [text.get_text() for text in ax.texts] == trace.value_labels

    def test_vertical_and_horizontal_violins_use_precomputed_density(
        self, ax: matplotlib.axes.Axes
    ) -> None:
        # [test->req~ring5.plot.violin~1]
        vertical = ViolinTraceConfig(
            name="A",
            category="A",
            values=[1.0, 2.0, 3.0],
            density_coordinates=[0.5, 1.5, 2.5, 3.5],
            density=[0.1, 1.0, 0.8, 0.1],
            q1=1.5,
            median=2.0,
            q3=2.5,
            mean=2.0,
            show_box=True,
            show_mean=True,
            point_mode="all",
        )
        result = MatplotlibTraceRenderer.render([vertical], ax)
        assert result.trace_count == 1
        assert [tick.get_text() for tick in ax.get_xticklabels()] == ["A"]
        assert ax.collections

        fig, horizontal_ax = plt.subplots()
        try:
            horizontal = ViolinTraceConfig(
                name="B",
                category="B",
                values=[2.0, 3.0],
                density_coordinates=[1.5, 2.5, 3.5],
                density=[0.1, 1.0, 0.1],
                orientation="horizontal",
                side="negative",
                show_box=False,
            )
            horizontal_result = MatplotlibTraceRenderer.render([horizontal], horizontal_ax)
            assert horizontal_result.trace_count == 1
            assert [tick.get_text() for tick in horizontal_ax.get_yticklabels()] == ["B"]
        finally:
            plt.close(fig)

    def test_single_scatter(self, ax: matplotlib.axes.Axes) -> None:
        trace = ScatterTraceConfig(name="sc", x=[0, 1], y=[1, 2])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_single_histogram(self, ax: matplotlib.axes.Axes) -> None:
        trace = HistogramTraceConfig(name="h1", x=[1, 2, 3, 4, 5])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_mixed_traces(self, ax: matplotlib.axes.Axes) -> None:
        traces = [
            BarTraceConfig(name="bar", x=["a", "b"], y=[1, 2]),
            LineTraceConfig(name="line", x=[0, 1], y=[3, 4]),
        ]
        count = MatplotlibTraceRenderer.render(traces, ax)
        assert count.trace_count == 2

    def test_palette_colors_applied(self, ax: matplotlib.axes.Axes) -> None:
        trace = BarTraceConfig(name="b", x=["a"], y=[1])
        count = MatplotlibTraceRenderer.render([trace], ax, palette_colors=["#ff0000"])
        assert count.trace_count == 1

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
        assert count.trace_count == 2

    def test_bar_with_border_width(self, ax: matplotlib.axes.Axes) -> None:
        trace = BarTraceConfig(name="b", x=["a"], y=[1])
        count = MatplotlibTraceRenderer.render([trace], ax, bar_border_width=1.5)
        assert count.trace_count == 1

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
        assert count.trace_count == 1

    def test_line_with_dash(self, ax: matplotlib.axes.Axes) -> None:
        trace = LineTraceConfig(name="dashed", x=[0, 1], y=[1, 2], line_dash="dash")
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_scatter_with_color(self, ax: matplotlib.axes.Axes) -> None:
        trace = ScatterTraceConfig(name="colored", x=[0, 1], y=[1, 2], color="#00ff00")
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_histogram_with_color(self, ax: matplotlib.axes.Axes) -> None:
        trace = HistogramTraceConfig(name="colored", x=[1, 2, 3], color="#0000ff", nbins=5)
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_none_y_values_handled(self, ax: matplotlib.axes.Axes) -> None:
        """None values in y should be converted to NaN gracefully."""
        trace = BarTraceConfig(name="nans", x=["a", "b"], y=[1, None])  # type: ignore[list-item]
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_unknown_trace_type_logged(self, ax: matplotlib.axes.Axes) -> None:
        """Unknown TraceConfig subtype should log warning, not crash."""
        trace = TraceConfig(name="unknown", x=["a"], y=[1])
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 0  # fallback doesn't match specific types


# _compute_categorical_positions


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


# _stack_bottom


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


# heatmap rendering


class TestHeatmapRendering:
    """Tests for heatmap trace rendering."""

    def test_single_heatmap(self, ax: matplotlib.axes.Axes) -> None:
        trace = HeatmapTraceConfig(
            name="hm",
            col_labels=["c1", "c2"],
            row_labels=["r1", "r2"],
            z=[[1.0, 2.0], [3.0, 4.0]],
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_heatmap_with_text_annotations(self, ax: matplotlib.axes.Axes) -> None:
        trace = HeatmapTraceConfig(
            name="annotated",
            col_labels=["a", "b"],
            row_labels=["x", "y"],
            z=[[10.0, 20.0], [30.0, 40.0]],
            show_values=True,
            text=[["10", "20"], ["30", "40"]],
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1
        # Check that text annotations were added
        texts = ax.texts
        assert len(texts) == 4

    def test_heatmap_without_text(self, ax: matplotlib.axes.Axes) -> None:
        trace = HeatmapTraceConfig(
            name="no_text",
            col_labels=["a", "b"],
            row_labels=["x"],
            z=[[1.0, 2.0]],
            show_values=False,
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1
        assert len(ax.texts) == 0

    def test_heatmap_with_none_values(self, ax: matplotlib.axes.Axes) -> None:
        """None values in z should be converted to NaN."""
        trace = HeatmapTraceConfig(
            name="nans",
            col_labels=["a", "b"],
            row_labels=["r1"],
            z=[[1.0, None]],
            show_values=True,
            text=[["1", ""]],
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_heatmap_empty_z(self, ax: matplotlib.axes.Axes) -> None:
        """Empty z matrix should render without error."""
        trace = HeatmapTraceConfig(
            name="empty",
            col_labels=[],
            row_labels=[],
            z=[],
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_heatmap_custom_colorscale(self, ax: matplotlib.axes.Axes) -> None:
        trace = HeatmapTraceConfig(
            name="blues",
            col_labels=["a"],
            row_labels=["b"],
            z=[[5.0]],
            colorscale="Blues",
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_heatmap_reversed_colorscale(self, ax: matplotlib.axes.Axes) -> None:
        trace = HeatmapTraceConfig(
            name="reversed",
            col_labels=["a"],
            row_labels=["b"],
            z=[[5.0]],
            colorscale="Viridis_r",
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1

    def test_heatmap_list_colorscale(self, ax: matplotlib.axes.Axes) -> None:
        """List-format colorscale (palette-derived) renders correctly."""
        trace = HeatmapTraceConfig(
            name="palette_cs",
            col_labels=["a", "b"],
            row_labels=["x", "y"],
            z=[[1.0, 2.0], [3.0, 4.0]],
            colorscale=[[0.0, "#000000"], [0.5, "#ff0000"], [1.0, "#ffffff"]],
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1
        assert count.heatmap_image is not None

    def test_heatmap_separator_right(self, ax: matplotlib.axes.Axes) -> None:
        """Totals position='right' draws a vertical separator line."""
        trace = HeatmapTraceConfig(
            name="sep_right",
            col_labels=["A", "B", "Total"],
            row_labels=["m1"],
            z=[[1.0, 2.0, 1.5]],
            totals_position="right",
            totals_count=1,
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1
        # Check that a vertical line was drawn (axvline adds a Line2D)
        lines = ax.get_lines()
        assert len(lines) >= 1

    def test_heatmap_separator_top(self, ax: matplotlib.axes.Axes) -> None:
        """Totals position='top' draws a horizontal separator line."""
        trace = HeatmapTraceConfig(
            name="sep_top",
            col_labels=["A", "B"],
            row_labels=["Total", "m1", "m2"],
            z=[[2.0, 3.0], [1.0, 2.0], [3.0, 4.0]],
            totals_position="top",
            totals_count=1,
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1
        lines = ax.get_lines()
        assert len(lines) >= 1

    def test_heatmap_no_separator_without_totals(self, ax: matplotlib.axes.Axes) -> None:
        """No separator lines when totals are not configured."""
        trace = HeatmapTraceConfig(
            name="no_sep",
            col_labels=["A", "B"],
            row_labels=["m1"],
            z=[[1.0, 2.0]],
        )
        count = MatplotlibTraceRenderer.render([trace], ax)
        assert count.trace_count == 1
        # No separator lines expected
        assert len(ax.get_lines()) == 0


# is_dark_cell


class TestIsDarkCell:
    """Tests for contrast-aware text colour helper."""

    def test_high_value_is_dark(self) -> None:
        z = np.array([[0.0, 1.0], [0.5, 0.9]])
        assert is_dark_cell(z, 0, 1) is True  # 1.0 is max

    def test_low_value_is_not_dark(self) -> None:
        z = np.array([[0.0, 1.0], [0.5, 0.9]])
        assert is_dark_cell(z, 0, 0) is False  # 0.0 is min

    def test_nan_returns_false(self) -> None:
        z = np.array([[np.nan, 1.0]])
        assert is_dark_cell(z, 0, 0) is False

    def test_uniform_values_returns_false(self) -> None:
        z = np.array([[5.0, 5.0]])
        assert is_dark_cell(z, 0, 0) is False  # vmax == vmin


# heatmap vmin/vmax


class TestHeatmapVminVmax:
    """Tests for heatmap rendering with explicit vmin/vmax colour limits."""

    def test_heatmap_vmin_vmax_clim(self, ax: matplotlib.axes.Axes) -> None:
        """When vmin/vmax are provided, pcolormesh clim matches them."""
        trace = HeatmapTraceConfig(
            name="hm_clim",
            col_labels=["a", "b"],
            row_labels=["r1"],
            z=[[1.0, 5.0]],
        )
        result = MatplotlibTraceRenderer.render(
            [trace],
            ax,
            heatmap_vmin=-2.0,
            heatmap_vmax=10.0,
        )
        assert result.trace_count == 1
        assert result.heatmap_image is not None
        clim = result.heatmap_image.get_clim()
        assert clim[0] == -2.0
        assert clim[1] == 10.0

    def test_heatmap_without_vmin_vmax_uses_data_range(self, ax: matplotlib.axes.Axes) -> None:
        """Without explicit vmin/vmax, clim defaults to the data range."""
        trace = HeatmapTraceConfig(
            name="hm_auto",
            col_labels=["a", "b"],
            row_labels=["r1"],
            z=[[3.0, 7.0]],
        )
        result = MatplotlibTraceRenderer.render([trace], ax)
        assert result.trace_count == 1
        assert result.heatmap_image is not None
        clim = result.heatmap_image.get_clim()
        assert clim[0] == 3.0
        assert clim[1] == 7.0


# create_multi_figure


class TestCreateMultiFigure:
    """Tests for FigureSpecToMatplotlib.create_multi_figure."""

    def test_returns_correct_number_of_axes(self) -> None:
        """create_multi_figure(nrows=3) returns exactly 3 axes."""
        from src.core.models.visualization.figure_config import FigureConfig
        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        spec = FigureConfig()
        fig, axes_list = FigureSpecToMatplotlib.create_multi_figure(spec, nrows=3)
        assert len(axes_list) == 3
        plt.close(fig)

    def test_single_row_returns_list(self) -> None:
        """create_multi_figure(nrows=1) wraps the single axes in a list."""
        from src.core.models.visualization.figure_config import FigureConfig
        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        spec = FigureConfig()
        fig, axes_list = FigureSpecToMatplotlib.create_multi_figure(spec, nrows=1)
        assert isinstance(axes_list, list)
        assert len(axes_list) == 1
        plt.close(fig)
