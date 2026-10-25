"""Scientific correctness regressions across trace construction and both engines."""

from __future__ import annotations

import copy
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from matplotlib.container import ErrorbarContainer

import ring5
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    BoxTraceConfig,
    HeatmapTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
)
from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot
from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot
from src.web.pages.ui.plotting.types.parallel_coordinates_plot import ParallelCoordinatesPlot
from src.web.rendering._heatmap_utils import compute_nice_range, compute_z_extent, is_dark_cell
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.linked_selection import apply_linked_selection
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer
from src.web.rendering.trace_to_plotly import traces_to_plotly


@pytest.fixture(autouse=True)
def close_figures() -> Any:
    yield
    plt.close("all")


def test_sparse_bars_share_categories_and_stack_by_label_and_axis() -> None:
    traces = [
        BarTraceConfig(name="first", x=["a", "b"], y=[1, 2]),
        BarTraceConfig(name="sparse", x=["b"], y=[9]),
        BarTraceConfig(name="right", x=["b", "a"], y=[100, 200], yaxis="y2"),
        BarTraceConfig(name="right2", x=["a"], y=[300], yaxis="y2"),
    ]
    _, axis = plt.subplots()
    MatplotlibTraceRenderer.render(traces, axis, barmode="stack")
    assert [patch.get_y() for patch in axis.patches] == [0, 0, 2]
    assert [patch.get_x() + patch.get_width() / 2 for patch in axis.patches] == [0, 1, 1]
    twin = getattr(axis, "_ring5_twin")
    assert [patch.get_y() for patch in twin.patches] == [0, 0, 200]
    assert [patch.get_x() + patch.get_width() / 2 for patch in twin.patches] == [1, 0, 0]
    assert [tick.get_text() for tick in axis.get_xticklabels()] == ["a", "b"]


def test_grouped_numeric_coordinates_are_distinct_and_identical_in_both_engines() -> None:
    data = pd.DataFrame({"x": ["a", "b", "b"], "g": ["A", "A", "B"], "y": [1, 2, 9]})
    result = GroupedBarPlot(1, "Grouped").create_traces(data, {"x": "x", "y": "y", "group": "g"})
    first, second = result.traces
    assert isinstance(first, BarTraceConfig) and isinstance(second, BarTraceConfig)
    assert second.x_positions[0] > first.x_positions[-1]
    figure = traces_to_plotly(result)
    _, axis = plt.subplots()
    MatplotlibTraceRenderer.render(result.traces, axis)
    assert [patch.get_x() + patch.get_width() / 2 for patch in axis.patches] == pytest.approx(
        [position for trace in figure.data for position in trace.x]
    )


def test_relative_stacks_keep_negative_and_positive_baselines_separate() -> None:
    _, axis = plt.subplots()
    MatplotlibTraceRenderer.render(
        [
            BarTraceConfig(x=["a", "b"], y=[5, -4]),
            BarTraceConfig(x=["a", "b"], y=[-2, 3]),
            BarTraceConfig(x=["a", "b"], y=[2, -1]),
        ],
        axis,
        barmode="relative",
    )
    assert [patch.get_y() for patch in axis.patches] == [0, 0, 0, 0, 5, -4]


@pytest.mark.parametrize("kind", [BarTraceConfig, LineTraceConfig, ScatterTraceConfig])
def test_error_bars_are_real_uncertainty_artists(kind: Any) -> None:
    _, axis = plt.subplots()
    trace = kind(name="uncertain", x=[1, 2], y=[2, 5], error_y=[0.5, 1.5])
    MatplotlibTraceRenderer.render([trace], axis)
    containers = [
        container for container in axis.containers if isinstance(container, ErrorbarContainer)
    ]
    assert len(containers) == 1
    segments = containers[0].lines[2][0].get_segments()
    np.testing.assert_allclose(segments, [[[1, 1.5], [1, 2.5]], [[2, 3.5], [2, 6.5]]])
    plotly_trace = traces_to_plotly(TraceBuildResult(traces=[trace])).data[0]
    assert list(plotly_trace.error_y.array) == [0.5, 1.5]


def test_line_error_bars_follow_gap_mask_instead_of_spline_coordinates() -> None:
    _, axis = plt.subplots()
    trace = LineTraceConfig(
        x=[0, 1, 2, 3],
        y=[1, float("nan"), 3, 4],
        error_y=[0.1, 99, 0.3, 0.4],
        connect_gaps=True,
        line_shape="spline",
    )
    MatplotlibTraceRenderer.render([trace], axis)
    errors = next(
        container for container in axis.containers if isinstance(container, ErrorbarContainer)
    )
    assert len(errors.lines[2][0].get_segments()) == 3
    assert [segment[0][0] for segment in errors.lines[2][0].get_segments()] == [0, 2, 3]


@pytest.mark.parametrize(
    ("columns", "counts", "expected_centers", "expected_counts", "widths"),
    [
        (["10-20", "0-10"], [7, 3], [5, 15], [3, 7], [10, 10]),
        (["0-4", "5-9", "10-14", "15-19"], [3, 5, 7, 4], [5, 15], [8, 11], [10, 10]),
        (["-10--6", "-5--1", "0-4"], [2, 4, 6], [-5, 2.5], [6, 6], [10, 5]),
        (["[0,2.5)", "[2.5,5)"], [2, 3], [2.5], [5], [5]),
    ],
)
def test_histogram_rebinning_keeps_sorted_counts_geometry_and_mass(
    columns: list[str],
    counts: list[float],
    expected_centers: list[float],
    expected_counts: list[float],
    widths: list[float],
) -> None:
    data = pd.DataFrame(
        {f"h..{column}": [value] for column, value in zip(columns, counts, strict=True)}
    )
    size = 5 if columns[0].startswith("[") else 10
    result = HistogramPlot(1, "Histogram").create_traces(
        data, {"histogram_variable": "h", "bucket_size": size}
    )
    trace = result.traces[0]
    assert isinstance(trace, BarTraceConfig)
    assert trace.x_positions == pytest.approx(expected_centers)
    assert trace.y == pytest.approx(expected_counts)
    assert sum(trace.y) == pytest.approx(sum(counts))
    assert trace.bar_width == widths
    _, axis = plt.subplots()
    MatplotlibTraceRenderer.render(result.traces, axis)
    assert [patch.get_width() for patch in axis.patches] == widths
    assert list(traces_to_plotly(result).data[0].width) == widths


def test_histogram_density_integrates_to_one_and_cumulative_density_ends_at_one() -> None:
    plot = HistogramPlot(1, "Histogram")
    data = pd.DataFrame({"h..[0,2)": [3], "h..[2,5)": [7]})
    config = {"histogram_variable": "h", "normalization": "density"}
    result = plot.create_traces(data, config)
    trace = result.traces[0]
    assert isinstance(trace, BarTraceConfig)
    assert np.dot(trace.y, trace.bar_width) == pytest.approx(1)
    cumulative = plot.create_traces(data, {**config, "cumulative": True}).traces[0]
    assert cumulative.y == pytest.approx([0.3, 1])


def test_histogram_retains_both_tails_and_refuses_unknown_density_widths() -> None:
    data = pd.DataFrame({"h..10+": [7], "h..<0": [2], "h..0-9": [3]})
    plot = HistogramPlot(1, "Histogram")
    result = plot.create_traces(data, {"histogram_variable": "h"})
    assert result.traces[0].y == [2, 3, 7]
    assert result.custom_x_ticks == {"vals": [-5, 5, 15], "text": ["<0", "0-9", "10+"]}
    with pytest.raises(ValueError, match="requires finite bucket bounds"):
        plot.create_traces(data, {"histogram_variable": "h", "normalization": "density"})


@pytest.mark.parametrize("column,value", [("bad", 1), ("0-9", float("nan")), ("0-9", -1)])
def test_histogram_invalid_buckets_and_counts_fail_visibly(column: str, value: float) -> None:
    with pytest.raises(ValueError):
        HistogramPlot(1, "Histogram").create_traces(
            pd.DataFrame({f"h..{column}": [value]}), {"histogram_variable": "h"}
        )


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
def test_plotly_boxes_use_precomputed_statistics_with_nested_samples(orientation: Any) -> None:
    trace = BoxTraceConfig(
        values=[0, 1, 2, 50],
        q1=0.75,
        median=1.5,
        q3=14,
        lower_whisker=0,
        upper_whisker=50,
        mean=13.25,
        notch_lower=1,
        notch_upper=2,
        orientation=orientation,
        position=2,
    )
    converted = traces_to_plotly(TraceBuildResult(traces=[trace])).data[0]
    assert list(converted.q1) == [0.75]
    assert list(converted.median) == [1.5]
    assert list(converted.q3) == [14]
    assert list(converted.upperfence) == [50]
    assert list(converted.mean) == [13.25]
    assert list(converted.notchspan) == [0.5]
    assert list(converted.y if orientation == "vertical" else converted.x) == [[0, 1, 2, 50]]


@pytest.mark.parametrize(
    "plot_type,config,data",
    [
        ("radar", {"x": "x", "y": "y"}, pd.DataFrame({"x": ["a", "b", "c"], "y": [1, 2, 3]})),
        (
            "sankey",
            {"sankey_source": "x", "sankey_target": "g", "sankey_value": "y"},
            pd.DataFrame({"x": ["a", "b"], "g": ["b", "c"], "y": [1, 2]}),
        ),
        (
            "parallel_coordinates",
            {"parallel_dimensions": ["x", "y"]},
            pd.DataFrame({"x": [1, 2], "y": [2, 3]}),
        ),
    ],
)
@pytest.mark.parametrize("shared_legend", [True, False])
def test_noncartesian_dashboard_panels_render_both_engines(
    plot_type: str, config: Any, data: pd.DataFrame, shared_legend: bool
) -> None:
    with ring5.Session() as session:
        plots = [
            session.create_plot(
                plot_type, data=ring5.Table(data), config=config, name=f"Panel {index}"
            )
            for index in range(2)
        ]
        dashboard = session.create_dashboard(
            plots,
            columns=2,
            shared_legend=shared_legend,
            panel_labels=["A", "B"],
            panel_captions=["First", "Second"],
        )
        figure = session.render_dashboard(dashboard, engine="plotly")
        assert len(figure.data) == 2
        assert {"A", "B", "First", "Second"} <= {
            annotation.text for annotation in figure.layout.annotations
        }
        assert len(session.render_dashboard(dashboard, engine="matplotlib").axes) >= 2


@pytest.mark.parametrize("plot_type", ["line", "scatter", "radar"])
def test_value_labels_use_supported_scatter_properties(plot_type: str) -> None:
    with ring5.Session() as session:
        figure = session.plot(
            plot_type,
            data=ring5.Table(pd.DataFrame({"x": ["a", "b", "c"], "y": [1, 2, 3]})),
            config={"x": "x", "y": "y", "show_values": True},
        )
        trace = figure.data[0]
        assert "text" in trace.mode
        assert trace.textposition == "top center"


def test_linked_filters_keep_drilldown_metadata_aligned_for_points_and_cells() -> None:
    spec = LinkedSelectionSpec((1, 2), mode="filter")
    point = go.Figure(
        go.Scatter(x=["a", "b"], y=[1, 2], meta={"ring5_drilldown": [{"x": "a"}, {"x": "b"}]})
    )
    filtered = apply_linked_selection(point, spec, ["b"])
    assert filtered.data[0].meta["ring5_drilldown"] == [{"x": "b"}]
    heatmap = HeatmapTraceConfig(
        col_labels=["a", "b", "Total"],
        row_labels=["m"],
        z=[[1, 2, 3]],
        text=[["1", "2", "3"]],
        totals_position="right",
        totals_count=1,
        custom_data={"drilldown": [[{"x": "a"}, {"x": "b"}, {"x": "Total"}]]},
    )
    source = traces_to_plotly(TraceBuildResult(traces=[heatmap]))
    selected = apply_linked_selection(source, spec, ["b", "Total"])
    assert selected.data[0].meta["ring5_drilldown"] == [[{"x": "b"}, {"x": "Total"}]]
    assert [annotation.x for annotation in selected.layout.annotations] == ["b", "Total"]
    assert selected.layout.shapes[0].x0 == 0.5
    without_total = apply_linked_selection(source, spec, ["b"])
    assert not without_total.layout.shapes
    assert len(source.layout.annotations) == 3


def test_palette_luminance_and_reversal_control_heatmap_text() -> None:
    z = [[0.0, 1.0]]
    assert is_dark_cell(z, 0, 0, "Viridis")
    assert not is_dark_cell(z, 0, 1, "Viridis")
    assert not is_dark_cell(z, 0, 0, "Viridis_r")
    assert is_dark_cell(z, 0, 1, "Viridis_r")
    scale = [[0, "black"], [0.5, "white"], [1, "black"]]
    assert not is_dark_cell([[0, 0.5, 1]], 0, 1, scale)
    assert is_dark_cell([[0, 0.5, 1]], 0, 2, scale)


def test_nonfinite_heatmap_values_fail_with_a_clear_error() -> None:
    with pytest.raises(ValueError, match="finite"):
        compute_z_extent([HeatmapTraceConfig(z=[[1, float("inf")]])])
    with pytest.raises(ValueError, match="finite"):
        compute_nice_range(0, float("inf"))


def test_global_font_and_barmode_survive_configuration_roundtrip() -> None:
    figure = ConfigSpecBuilder.from_config({"font_family": "monospace"})
    assert figure.font_family == "monospace"
    for mode in ["group", "stack", "relative", "overlay"]:
        assert FigureConfig.from_dict(FigureConfig(barmode=mode).to_dict()).barmode == mode


def test_parallel_brush_configuration_is_not_mutated() -> None:
    config = {
        "parallel_dimensions": ["x", "y"],
        "parallel_brushes": {"y": [1, 2]},
        "parallel_brush_dimension": "x",
        "parallel_brush_range": [1, 2],
    }
    before = copy.deepcopy(config)
    ParallelCoordinatesPlot(1, "Parallel").create_traces(
        pd.DataFrame({"x": [1, 2], "y": [2, 3]}), config
    )
    assert config == before


def test_faceted_heatmaps_keep_category_ticks_and_overall_dimensions() -> None:
    from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_traces

    traces = [
        HeatmapTraceConfig(
            name=name, col_labels=["a", "b"], row_labels=["m1", "m2"], z=[[1, 2], [3, 4]]
        )
        for name in ["A", "B"]
    ]
    figure, _ = build_matplotlib_figure_from_traces(
        {"width": 800, "height": 600}, "heatmap", TraceBuildResult(traces=traces)
    )
    assert figure.get_size_inches() * figure.dpi == pytest.approx([800, 600])
    for axis in figure.axes[:2]:
        assert [tick.get_text() for tick in axis.get_xticklabels()] == ["a", "b"]
        assert [tick.get_text() for tick in axis.get_yticklabels()] == ["m1", "m2"]
        assert axis.get_xticks().tolist() == [0.5, 1.5]


@pytest.mark.parametrize("plot_type", ["bar", "line", "scatter"])
def test_matplotlib_category_aliases_keep_data_coordinates(plot_type: str) -> None:
    with ring5.Session() as session:
        figure = session.plot(
            plot_type,
            data=ring5.Table(pd.DataFrame({"x": ["a", "b"], "y": [1, 2]})),
            config={
                "x": "x",
                "y": "y",
                "xaxis_labels": {"a": "Alpha", "b": "Beta"},
                "font_family": "monospace",
                "title": "Title",
            },
            engine="matplotlib",
        )
        axis = figure.axes[0]
        assert [tick.get_text() for tick in axis.get_xticklabels()] == ["Alpha", "Beta"]
        assert axis.title.get_fontfamily() == ["monospace"]


def test_direct_dimensions_convert_pixel_margins_using_dpi() -> None:
    from src.core.models.visualization.figure_config import DimensionConfig, MarginsConfig

    _, axis = plt.subplots()
    spec = FigureConfig(
        dimensions=DimensionConfig(
            width=8, height=5, dpi=100, margins=MarginsConfig(left=80, right=40, bottom=50, top=25)
        )
    )
    FigureSpecToMatplotlib._apply_margins(spec, axis)
    assert axis.figure.subplotpars.left == 0.1
    assert axis.figure.subplotpars.right == 0.95
    assert axis.figure.subplotpars.bottom == 0.1
    assert axis.figure.subplotpars.top == 0.95


def test_vertical_horizontal_vertical_line_has_distinct_geometry() -> None:
    _, axis = plt.subplots()
    trace = LineTraceConfig(x=[0, 2], y=[0, 4], line_shape="vhv", show_markers=True)
    MatplotlibTraceRenderer.render([trace], axis)
    assert axis.lines[0].get_xydata().tolist() == [[0, 0], [0, 2], [2, 2], [2, 4]]
    assert axis.lines[0].get_markevery() == [0, 3]


def test_secondary_axis_styling_and_unified_legend_follow_configuration() -> None:
    from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_traces

    result = TraceBuildResult(
        traces=[
            BarTraceConfig(name="Left", x=["a"], y=[1]),
            LineTraceConfig(name="Right", x=[0], y=[10], yaxis="y2"),
        ],
        secondary_y=True,
    )
    figure, spec = build_matplotlib_figure_from_traces(
        {
            "dual_axis": True,
            "ylabel_right": "Right metric",
            "show_y2tick_labels": False,
            "show_y2tick_marks": False,
            "show_y2grid": False,
            "y2tick_font_color": "red",
            "unified_legend": True,
        },
        "grouped_stacked_bar",
        result,
    )
    primary, twin = figure.axes
    assert twin.get_ylabel() == "Right metric"
    assert twin.get_legend() is None
    assert {label.get_text() for label in primary.get_legend().get_texts()} == {"Left", "Right"}
    assert spec.axes.y2 is not None
    assert not any(label.get_visible() for label in twin.get_yticklabels())


@pytest.mark.parametrize("bucket_size", [None, 10])
def test_histogram_union_schemas_conserve_only_observed_interval_mass(
    bucket_size: float | None,
) -> None:
    """Different runs can expose different ranges in the same wide CSV schema."""
    data = pd.DataFrame({"h..0-9": [10, np.nan], "h..0-19": [np.nan, 20]})
    config = {"histogram_variable": "h", "bucket_size": bucket_size}
    trace = HistogramPlot(1, "Histogram").create_traces(data, config).traces[0]
    assert trace.y == [20, 10]
    assert trace.x_positions == [5, 15]
    assert data.isna().sum().sum() == 2


def test_linked_selection_preserves_numpy_point_arrays_and_marker_outlines() -> None:
    source = go.Figure(
        go.Scatter(
            x=np.array([1, 2, 3], dtype="int8"),
            y=np.array([2.0, 4.0, 8.0]),
            marker={"line": {"width": [1, 2, 3]}},
        )
    )
    selected = apply_linked_selection(source, LinkedSelectionSpec((1, 2), mode="filter"), [2])
    assert list(selected.data[0].x) == [2]
    assert list(selected.data[0].y) == [4]
    assert list(selected.data[0].marker.line.width) == [2]
    assert list(source.data[0].x) == [1, 2, 3]


def test_right_axis_configuration_does_not_relabel_other_dashboard_panels() -> None:
    from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
    from src.core.services.visualization.config_resolver import resolve_config

    figure, (left, other) = plt.subplots(1, 2)
    MatplotlibTraceRenderer.render([LineTraceConfig(yaxis="y2", x=[1], y=[2])], left)
    other.set_ylabel("Other panel")
    spec = resolve_config(FigureConfig(axes=AxesConfig(y2=AxisConfig(label="Secondary"))))
    FigureSpecToMatplotlib._apply_axis_labels(spec, left)
    assert other.get_ylabel() == "Other panel"
    assert getattr(left, "_ring5_twin").get_ylabel() == "Secondary"


@pytest.mark.parametrize("shared", [True, False])
def test_heatmap_contrast_uses_resolved_manual_bounds_in_both_engines(shared: bool) -> None:
    from src.core.services.visualization.config_resolver import resolve_config
    from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_traces
    from src.web.rendering.plotly_connector import FigureSpecToPlotly

    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(
                name=name, col_labels=["a", "b"], row_labels=["m"], z=[[0, 5]], text=[["0", "5"]]
            )
            for name in ["A", "B"]
        ]
    )
    config = {
        "legend_colorbar_range_mode": "manual",
        "legend_colorbar_zmin": 0,
        "legend_colorbar_zmax": 100,
        "legend_colorbar_shared": shared,
    }
    plotly = traces_to_plotly(result)
    FigureSpecToPlotly._apply_heatmap_colorbars(
        resolve_config(ConfigSpecBuilder.from_config(config)), plotly
    )
    assert all(
        annotation.font.color == "white"
        for annotation in plotly.layout.annotations
        if annotation.name == "ring5-heatmap-auto"
    )
    assert all(trace.zmax == 100 for trace in plotly.data)
    matplotlib, _ = build_matplotlib_figure_from_traces(config, "heatmap", result)
    for axis in matplotlib.axes[:2]:
        assert [text.get_color() for text in axis.texts] == ["white", "white"]
        assert axis.collections[0].get_clim() == (0, 100)


@pytest.mark.parametrize(
    ("columns", "centers", "counts", "widths"),
    [
        (["0-0", "0-9"], [0.5, 5.5], [1.2, 1.8], [1, 9]),
        (["0-1", "1-2"], [0.5, 1.5, 2.5], [0.5, 1.5, 1], [1, 1, 1]),
    ],
)
def test_histogram_geometry_is_inferred_per_observed_row(
    columns: list[str],
    centers: list[float],
    counts: list[float],
    widths: list[float],
) -> None:
    data = pd.DataFrame({f"h..{columns[0]}": [1, np.nan], f"h..{columns[1]}": [np.nan, 2]})
    trace = HistogramPlot(1, "Histogram").create_traces(data, {"histogram_variable": "h"}).traces[0]
    assert trace.x_positions == centers
    assert trace.y == pytest.approx(counts)
    assert trace.bar_width == widths
    assert sum(trace.y) == pytest.approx(3)


def test_histogram_csv_can_mix_legacy_and_inclusive_observation_geometry() -> None:
    data = pd.DataFrame(
        {
            "h..0-10": [10, np.nan],
            "h..10-20": [20, np.nan],
            "h..0-9": [np.nan, 30],
            "h..10-19": [np.nan, 40],
        }
    )
    trace = HistogramPlot(1, "Histogram").create_traces(data, {"histogram_variable": "h"}).traces[0]
    assert trace.x_positions == [5, 15]
    assert trace.y == [40, 60]
    assert trace.bar_width == [10, 10]


def test_grouped_right_lines_keep_aliased_categories_with_a_partial_preferred_order() -> None:
    from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import GroupedStackedBarPlot

    data = pd.DataFrame(
        {
            "x": ["a", "a", "b", "b"],
            "g": ["G", "H", "G", "H"],
            "left": [1, 2, 3, 4],
            "right": [10, 20, 30, 40],
        }
    )
    result = GroupedStackedBarPlot(1, "Grouped").create_traces(
        data,
        {
            "x": "x",
            "group": "g",
            "y_columns": ["left"],
            "y_columns_right": ["right"],
            "dual_axis": True,
            "right_axis_type": "dots",
            "right_show_lines": True,
            "right_line_per_group": True,
            "xaxis_order": ["b"],
            "xaxis_labels": {"a": "Alpha", "b": "Beta"},
        },
    )
    line = next(trace for trace in result.traces if isinstance(trace, LineTraceConfig))
    np.testing.assert_allclose(line.x, [0, 1, np.nan, 2, 3], equal_nan=True)
    np.testing.assert_allclose(line.y, [30, 40, np.nan, 10, 20], equal_nan=True)
    figure = traces_to_plotly(result)
    np.testing.assert_allclose(figure.data[-1].y, line.y, equal_nan=True)
    _, axis = plt.subplots()
    MatplotlibTraceRenderer.render(result.traces, axis)
    drawn = getattr(axis, "_ring5_twin").lines[0]
    np.testing.assert_allclose(drawn.get_ydata(), line.y, equal_nan=True)


def test_bar_aligned_dual_axis_keeps_categories_omitted_from_preferred_order() -> None:
    from src.web.pages.ui.plotting.types.dual_axis_bar_dot_plot import DualAxisBarDotPlot

    data = pd.DataFrame(
        {
            "x": ["a", "a", "b", "b"],
            "g": ["G", "H", "G", "H"],
            "left": [1, 2, 3, 4],
            "right": [10, 20, 30, 40],
        }
    )
    result = DualAxisBarDotPlot(1, "Aligned").create_traces(
        data,
        {
            "x": "x",
            "color": "g",
            "y_bar": "left",
            "y_dot": "right",
            "dot_alignment": "bar",
            "xaxis_order": ["b"],
        },
    )
    bars = [trace for trace in result.traces if isinstance(trace, BarTraceConfig)]
    lines = [trace for trace in result.traces if isinstance(trace, LineTraceConfig)]
    assert [trace.y for trace in lines] == [[30, 10], [40, 20]]
    assert [trace.x for trace in lines] == [trace.x_positions for trace in bars]
    assert [trace.x for trace in bars] == [["b", "a"], ["b", "a"]]
    figure = traces_to_plotly(result)
    np.testing.assert_allclose(figure.data[1].x, bars[0].x_positions)
    _, axis = plt.subplots()
    MatplotlibTraceRenderer.render(result.traces, axis)
    drawn = getattr(axis, "_ring5_twin").lines
    assert [list(line.get_ydata()) for line in drawn] == [[30, 10], [40, 20]]


def test_default_neutral_data_annotations_render_with_valid_engine_coordinates() -> None:
    from src.core.models.visualization.annotation_config import AnnotationConfig
    from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_traces

    result = TraceBuildResult(
        traces=[LineTraceConfig(x=[1, 2], y=[2, 3])],
        annotations=[AnnotationConfig(text="Measured", x=1, y=2)],
    )
    interactive = traces_to_plotly(result)
    assert interactive.layout.annotations[0].xref == "x"
    assert interactive.layout.annotations[0].yref == "y"
    static, _ = build_matplotlib_figure_from_traces({}, "line", result)
    annotation = next(text for text in static.axes[0].texts if text.get_text() == "Measured")
    assert annotation.xy == (1, 2)
    assert annotation.xycoords is static.axes[0].transData
