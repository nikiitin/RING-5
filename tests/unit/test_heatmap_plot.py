from __future__ import annotations

from typing import Any, cast

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.web.pages.ui.plotting.types.heatmap_plot import HeatmapPlot
from src.web.rendering.trace_to_plotly import traces_to_plotly


def test_heatmap_plot_creates_trace_per_benchmark() -> None:
    # [test->req~ring5.plot.heatmap~1]
    data = pd.DataFrame(
        {
            "config_abbrev": ["A", "B", "A", "B"],
            "benchmark_name": ["bm1", "bm1", "bm2", "bm2"],
            "l0_ctrl0_aborted_cycles": [10.0, 20.0, 30.0, 40.0],
            "l0_ctrl1_aborted_cycles": [11.0, 21.0, 31.0, 41.0],
        }
    )

    plot = HeatmapPlot(plot_id=1, name="Heatmap")
    result = plot.create_traces(
        data,
        {
            "x": "config_abbrev",
            "facet_col": "benchmark_name",
            "metric_columns": ["l0_ctrl0_aborted_cycles", "l0_ctrl1_aborted_cycles"],
            "aggregation": "mean",
            "show_cell_values": True,
        },
    )

    assert len(result.traces) == 2
    assert all(isinstance(trace, HeatmapTraceConfig) for trace in result.traces)

    trace_names = [trace.name for trace in result.traces]
    assert trace_names == ["bm1", "bm2"]

    first = result.traces[0]
    assert isinstance(first, HeatmapTraceConfig)
    assert first.col_labels == ["A", "B"]
    assert first.row_labels == ["l0_ctrl0_aborted_cycles", "l0_ctrl1_aborted_cycles"]
    assert first.z == [[10.0, 20.0], [11.0, 21.0]]


def test_heatmap_plot_aggregates_duplicate_rows() -> None:
    data = pd.DataFrame(
        {
            "config_abbrev": ["A", "A", "B", "B"],
            "benchmark_name": ["bm1", "bm1", "bm1", "bm1"],
            "l0_ctrl0_aborted_cycles": [10.0, 20.0, 40.0, 60.0],
            "l0_ctrl1_aborted_cycles": [30.0, 50.0, 70.0, 90.0],
        }
    )

    plot = HeatmapPlot(plot_id=2, name="Heatmap")
    result = plot.create_traces(
        data,
        {
            "x": "config_abbrev",
            "facet_col": "benchmark_name",
            "metric_columns": ["l0_ctrl0_aborted_cycles", "l0_ctrl1_aborted_cycles"],
            "aggregation": "mean",
            "show_cell_values": False,
        },
    )

    assert len(result.traces) == 1
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.z == [[15.0, 50.0], [40.0, 80.0]]


def test_multiple_heatmap_traces_render_as_subplots() -> None:
    # [test->req~ring5.figure.heatmap-controls~1]
    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(
                name="benchmark_name=bm1",
                col_labels=["A", "B"],
                row_labels=["l0_ctrl0_aborted_cycles"],
                z=[[1.0, 2.0]],
            ),
            HeatmapTraceConfig(
                name="benchmark_name=bm2",
                col_labels=["A", "B"],
                row_labels=["l0_ctrl0_aborted_cycles"],
                z=[[3.0, 4.0]],
            ),
        ]
    )

    fig = traces_to_plotly(result)

    assert len(cast(tuple[Any, ...], fig.data)) == 2
    assert fig.layout.xaxis2 is not None
    assert fig.layout.yaxis2 is not None


def test_heatmap_x_filter_restricts_columns() -> None:
    """When x_filter is provided, only those X values appear as columns."""
    data = pd.DataFrame(
        {
            "cfg": ["A", "B", "C"],
            "metric1": [1.0, 2.0, 3.0],
        }
    )
    plot = HeatmapPlot(plot_id=10, name="Filtered")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["metric1"],
            "aggregation": "mean",
            "show_cell_values": True,
            "x_filter": ["A", "B"],
        },
    )
    assert len(result.traces) == 1
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.col_labels == ["A", "B"]
    assert trace.z == [[1.0, 2.0]]


def test_heatmap_x_filter_empty_shows_all() -> None:
    """An empty x_filter is treated as 'no filter' — all X values shown."""
    data = pd.DataFrame(
        {
            "cfg": ["A", "B"],
            "metric1": [1.0, 2.0],
        }
    )
    plot = HeatmapPlot(plot_id=11, name="Empty")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["metric1"],
            "aggregation": "mean",
            "x_filter": [],
        },
    )
    # Empty list = no filter applied, all values appear
    assert len(result.traces) == 1
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.col_labels == ["A", "B"]


def test_heatmap_plotly_annotations_have_contrast_colors() -> None:
    """Cell-value annotations use white text on dark cells, black on light."""
    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(
                name="test",
                col_labels=["A", "B"],
                row_labels=["m1"],
                z=[[1.0, 100.0]],
                show_values=True,
                text=[["1.0", "100.0"]],
            ),
        ]
    )

    fig = traces_to_plotly(result)
    annotations = list(fig.layout.annotations)
    assert len(annotations) == 2

    # Cell (0,0) z=1.0 is in the lower half → black text
    ann_a = next(a for a in annotations if a.x == "A")
    assert ann_a.font.color == "black"

    # Cell (0,1) z=100.0 is in the upper half → white text
    ann_b = next(a for a in annotations if a.x == "B")
    assert ann_b.font.color == "white"


def test_heatmap_subplot_annotations_use_correct_axis_refs() -> None:
    """Multi-subplot heatmaps get correct xref/yref per subplot."""
    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(
                name="bm1",
                col_labels=["A"],
                row_labels=["m1"],
                z=[[10.0]],
                show_values=True,
                text=[["10"]],
            ),
            HeatmapTraceConfig(
                name="bm2",
                col_labels=["A"],
                row_labels=["m1"],
                z=[[20.0]],
                show_values=True,
                text=[["20"]],
            ),
        ]
    )

    fig = traces_to_plotly(result)
    annotations = list(fig.layout.annotations)

    # make_subplots adds subplot_titles as annotations; filter to cell annotations
    cell_annotations = [a for a in annotations if a.text in ("10", "20")]
    assert len(cell_annotations) == 2

    ann_bm1 = next(a for a in cell_annotations if a.text == "10")
    assert ann_bm1.xref == "x"
    assert ann_bm1.yref == "y"

    ann_bm2 = next(a for a in cell_annotations if a.text == "20")
    assert ann_bm2.xref == "x2"
    assert ann_bm2.yref == "y2"


def test_heatmap_totals_right_adds_column() -> None:
    """Totals position='right' adds an extra column to z and col_labels."""
    # [test->req~ring5.figure.heatmap-summary-controls~1]
    data = pd.DataFrame(
        {
            "cfg": ["A", "B"],
            "m1": [10.0, 20.0],
            "m2": [30.0, 40.0],
        }
    )
    plot = HeatmapPlot(plot_id=20, name="Totals")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1", "m2"],
            "aggregation": "mean",
            "show_cell_values": True,
            "show_totals": True,
            "totals_position": "right",
            "totals_aggregation": "mean",
        },
    )
    assert len(result.traces) == 1
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.col_labels == ["A", "B", "Total"]
    # m1 row: [10, 20, mean(10,20)=15], m2 row: [30, 40, mean(30,40)=35]
    assert trace.z == [[10.0, 20.0, 15.0], [30.0, 40.0, 35.0]]


def test_heatmap_totals_top_adds_row() -> None:
    """Totals position='top' prepends a row to z and row_labels."""
    data = pd.DataFrame(
        {
            "cfg": ["A", "B"],
            "m1": [10.0, 20.0],
            "m2": [30.0, 40.0],
        }
    )
    plot = HeatmapPlot(plot_id=21, name="Totals")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1", "m2"],
            "aggregation": "mean",
            "show_cell_values": True,
            "show_totals": True,
            "totals_position": "top",
            "totals_aggregation": "mean",
        },
    )
    assert len(result.traces) == 1
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.row_labels[0] == "Total"
    # Total row: col A mean(10,30)=20, col B mean(20,40)=30
    assert trace.z[0] == [20.0, 30.0]
    assert len(trace.z) == 3  # Total + m1 + m2


def test_heatmap_totals_sum_aggregation() -> None:
    """Totals with sum aggregation produces correct sums."""
    data = pd.DataFrame(
        {
            "cfg": ["A", "B"],
            "m1": [10.0, 20.0],
        }
    )
    plot = HeatmapPlot(plot_id=22, name="Sum")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "show_cell_values": True,
            "show_totals": True,
            "totals_position": "right",
            "totals_aggregation": "sum",
        },
    )
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    # m1: [10, 20, sum=30]
    assert trace.z == [[10.0, 20.0, 30.0]]


def test_heatmap_totals_with_none_values() -> None:
    """None values are excluded when computing totals."""
    # [test->req~ring5.figure.heatmap-summary-controls~1]
    data = pd.DataFrame(
        {
            "cfg": ["A", "B", "C"],
            "m1": [10.0, float("nan"), 30.0],
        }
    )
    plot = HeatmapPlot(plot_id=23, name="NoneTotal")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "show_cell_values": True,
            "show_totals": True,
            "totals_position": "right",
            "totals_aggregation": "mean",
        },
    )
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    # m1: [10, None, 30, mean(10,30)=20]
    assert trace.z[0][1] is None
    assert trace.z[0][3] == 20.0


def test_heatmap_apply_common_layout_restricts_xaxis_categories() -> None:
    """apply_common_layout overrides categoryarray to filtered col_labels only.

    When the ordering settings provide xaxis_order with ALL unique X values
    (including filtered-out ones), the Plotly connector sets categoryarray to
    that full list.  HeatmapPlot.apply_common_layout must restrict it to the
    col_labels actually present in the trace data so that filtered-out ticks
    don't appear and cells are not displaced.
    """
    data = pd.DataFrame(
        {
            "cfg": ["A", "B", "C", "D"],
            "m1": [1.0, 2.0, 3.0, 4.0],
        }
    )
    plot = HeatmapPlot(plot_id=30, name="CategoryRestrict")
    config = {
        "x": "cfg",
        "metric_columns": ["m1"],
        "aggregation": "mean",
        "show_cell_values": True,
        "x_filter": ["A", "C"],
        "xaxis_order": ["A", "B", "C", "D"],
    }
    fig = plot.create_figure(data, config)

    # At this point last_traces should have col_labels ["A", "C"] only
    assert plot.last_traces is not None
    first = plot.last_traces.traces[0]
    assert isinstance(first, HeatmapTraceConfig)
    assert first.col_labels == ["A", "C"]

    # Simulate a Plotly figure that has categoryarray set to ALL values
    # (this is what the base apply_common_layout would do via the connector)
    fig.update_xaxes(categoryorder="array", categoryarray=["A", "B", "C", "D"])

    # Now apply the heatmap override
    fig = plot.apply_common_layout(fig, config)

    # The override should restrict categoryarray to only the filtered values
    xaxis_layout = fig.layout.xaxis
    assert list(xaxis_layout.categoryarray) == ["A", "C"]
    assert xaxis_layout.categoryorder == "array"


def test_heatmap_data_labels_format_and_threshold() -> None:
    """Data labels configuration applies format and threshold logic."""
    # [test->req~ring5.figure.heatmap-controls~1]
    # [test->req~ring5.figure.heatmap-summary-controls~1]
    data = pd.DataFrame(
        {
            "cfg": ["A", "B", "C"],
            "m1": [1.0, 5.0, 10.0],
        }
    )
    plot = HeatmapPlot(plot_id=24, name="DL")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "show_values": True,
            "text_format": ".1f",
            "text_display_logic": "above_threshold",
            "text_threshold": 3.0,
        },
    )
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.text is not None
    # A=1.0 below threshold → empty, B=5.0 above → "5.0", C=10.0 above → "10.0"
    assert trace.text[0] == ["", "5.0", "10.0"]


# R1: Facet ordering & renaming


def test_heatmap_facet_ordering() -> None:
    """Facet order config controls the order of traces."""
    # [test->req~ring5.plot.heatmap~1]
    data = pd.DataFrame(
        {
            "cfg": ["A", "A", "A"],
            "bm": ["z_last", "a_first", "m_mid"],
            "m1": [1.0, 2.0, 3.0],
        }
    )
    plot = HeatmapPlot(plot_id=50, name="FacetOrder")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "facet_col": "bm",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "facet_order": ["m_mid", "z_last", "a_first"],
        },
    )
    assert len(result.traces) == 3
    names = [t.name for t in result.traces]
    assert names == ["m_mid", "z_last", "a_first"]


def test_heatmap_facet_renaming() -> None:
    """Facet labels config renames trace names."""
    data = pd.DataFrame(
        {
            "cfg": ["A", "A"],
            "bm": ["bm1", "bm2"],
            "m1": [1.0, 2.0],
        }
    )
    plot = HeatmapPlot(plot_id=51, name="FacetRename")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "facet_col": "bm",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "facet_labels": {"bm1": "Benchmark Alpha", "bm2": "Benchmark Beta"},
        },
    )
    assert len(result.traces) == 2
    names = [t.name for t in result.traces]
    assert names == ["Benchmark Alpha", "Benchmark Beta"]


def test_heatmap_facet_order_and_rename_combined() -> None:
    """Facet ordering and renaming work together."""
    # [test->req~ring5.figure.ordering-renaming~1]
    data = pd.DataFrame(
        {
            "cfg": ["A", "A"],
            "bm": ["bm1", "bm2"],
            "m1": [1.0, 2.0],
        }
    )
    plot = HeatmapPlot(plot_id=52, name="FacetBoth")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "facet_col": "bm",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "facet_order": ["bm2", "bm1"],
            "facet_labels": {"bm1": "First", "bm2": "Second"},
        },
    )
    names = [t.name for t in result.traces]
    assert names == ["Second", "First"]


# R2: Colorscale from palette


def test_heatmap_colorscale_from_palette() -> None:
    """When color_palette is set, colorscale is derived from it."""
    # [test->req~ring5.figure.heatmap-controls~1]
    data = pd.DataFrame({"cfg": ["A"], "m1": [1.0]})
    plot = HeatmapPlot(plot_id=60, name="PaletteCS")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "color_palette": "wong",
        },
    )
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    # Colorscale should be a list of [position, hex_color] pairs
    assert isinstance(trace.colorscale, list)
    assert len(trace.colorscale) > 0
    assert trace.colorscale[0][0] == 0.0
    assert trace.colorscale[-1][0] == 1.0


def test_heatmap_colorscale_reverse_list() -> None:
    """Reversing a list-format colorscale flips positions."""
    # [test->req~ring5.figure.heatmap-summary-controls~1]
    data = pd.DataFrame({"cfg": ["A"], "m1": [1.0]})
    plot = HeatmapPlot(plot_id=61, name="ReverseCS")
    result_normal = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "color_palette": "wong",
            "reverse_colorscale": False,
        },
    )
    result_reversed = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "color_palette": "wong",
            "reverse_colorscale": True,
        },
    )
    t_normal = result_normal.traces[0]
    t_reversed = result_reversed.traces[0]
    assert isinstance(t_normal, HeatmapTraceConfig)
    assert isinstance(t_reversed, HeatmapTraceConfig)
    assert isinstance(t_normal.colorscale, list)
    assert isinstance(t_reversed.colorscale, list)
    # First color of normal should be last color of reversed
    assert t_normal.colorscale[0][1] == t_reversed.colorscale[-1][1]


def test_heatmap_colorscale_legacy_string() -> None:
    """Legacy string colorscale is preserved when no palette is set."""
    data = pd.DataFrame({"cfg": ["A"], "m1": [1.0]})
    plot = HeatmapPlot(plot_id=62, name="LegacyCS")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "colorscale": "Viridis",
        },
    )
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.colorscale == "Viridis"


# R4: Totals separator metadata


def test_heatmap_totals_separator_metadata_right() -> None:
    """Totals position='right' populates separator metadata on the trace."""
    data = pd.DataFrame({"cfg": ["A", "B"], "m1": [1.0, 2.0]})
    plot = HeatmapPlot(plot_id=70, name="SepRight")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "show_totals": True,
            "totals_position": "right",
            "totals_aggregation": "mean",
        },
    )
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.totals_position == "right"
    assert trace.totals_count == 1


def test_heatmap_totals_separator_metadata_top() -> None:
    """Totals position='top' populates separator metadata on the trace."""
    data = pd.DataFrame({"cfg": ["A", "B"], "m1": [1.0, 2.0]})
    plot = HeatmapPlot(plot_id=71, name="SepTop")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
            "show_totals": True,
            "totals_position": "top",
            "totals_aggregation": "mean",
        },
    )
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.totals_position == "top"
    assert trace.totals_count == 1


def test_heatmap_no_totals_no_separator_metadata() -> None:
    """When totals are disabled, separator metadata is empty."""
    data = pd.DataFrame({"cfg": ["A"], "m1": [1.0]})
    plot = HeatmapPlot(plot_id=72, name="NoSep")
    result = plot.create_traces(
        data,
        {
            "x": "cfg",
            "metric_columns": ["m1"],
            "aggregation": "mean",
        },
    )
    trace = result.traces[0]
    assert isinstance(trace, HeatmapTraceConfig)
    assert trace.totals_position == ""
    assert trace.totals_count == 0


# R4: Plotly separator shapes


def test_heatmap_plotly_separator_line_right() -> None:
    """Totals position='right' generates a vertical separator shape."""
    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(
                name="test",
                col_labels=["A", "B", "Total"],
                row_labels=["m1", "m2"],
                z=[[1.0, 2.0, 1.5], [3.0, 4.0, 3.5]],
                totals_position="right",
                totals_count=1,
            ),
        ]
    )
    fig = traces_to_plotly(result)
    shapes = list(fig.layout.shapes)
    # Should have at least one vertical separator line
    sep_shapes = [s for s in shapes if s.type == "line"]
    assert len(sep_shapes) >= 1
    # The line should be at x = n_cols - 1.5 = 3 - 1.5 = 1.5
    assert any(abs(s.x0 - 1.5) < 0.01 for s in sep_shapes)


def test_heatmap_plotly_separator_line_top() -> None:
    """Totals position='top' generates a horizontal separator shape."""
    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(
                name="test",
                col_labels=["A", "B"],
                row_labels=["Total", "m1", "m2"],
                z=[[2.0, 3.0], [1.0, 2.0], [3.0, 4.0]],
                totals_position="top",
                totals_count=1,
            ),
        ]
    )
    fig = traces_to_plotly(result)
    shapes = list(fig.layout.shapes)
    sep_shapes = [s for s in shapes if s.type == "line"]
    assert len(sep_shapes) >= 1
    # The line should be at y = 0.5
    assert any(abs(s.y0 - 0.5) < 0.01 for s in sep_shapes)


def test_heatmap_plotly_no_separator_without_totals() -> None:
    """No separator shapes when totals are not enabled."""
    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(
                name="test",
                col_labels=["A", "B"],
                row_labels=["m1"],
                z=[[1.0, 2.0]],
            ),
        ]
    )
    fig = traces_to_plotly(result)
    shapes = list(fig.layout.shapes or [])
    assert len(shapes) == 0


# Plotly colorbar configuration


def test_plotly_shared_colorbar_zmin_zmax_match() -> None:
    """Shared colorbar mode: all traces get identical zmin/zmax, only last shows scale."""
    # [test->req~ring5.figure.heatmap-controls~1]
    import plotly.graph_objects as go

    from src.core.models.visualization.figure_config import FigureConfig
    from src.core.models.visualization.legend_config import ColorbarConfig, LegendConfig
    from src.web.rendering.plotly_connector import FigureSpecToPlotly

    fig = go.Figure(
        data=[
            go.Heatmap(x=["A", "B"], y=["m1"], z=[[1.0, 5.0]], name="hm1"),
            go.Heatmap(x=["A", "B"], y=["m1"], z=[[2.0, 8.0]], name="hm2"),
        ]
    )
    legend = LegendConfig(
        role="primary",
        title="Z-Values",
        colorbar=ColorbarConfig(shared=True, range_mode="manual", zmin=0.0, zmax=10.0),
    )
    spec = FigureConfig(legends=[legend])
    FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)

    t0 = cast(Any, fig.data[0])
    t1 = cast(Any, fig.data[1])

    # Both traces share the same zmin/zmax
    assert t0.zmin == 0.0
    assert t0.zmax == 10.0
    assert t1.zmin == 0.0
    assert t1.zmax == 10.0

    # Only the last trace shows the colorbar
    assert t0.showscale is False
    assert t1.showscale is True


def test_plotly_individual_colorbar_mode() -> None:
    """Individual colorbar mode: every trace keeps showscale=True."""
    import plotly.graph_objects as go

    from src.core.models.visualization.figure_config import FigureConfig
    from src.core.models.visualization.legend_config import ColorbarConfig, LegendConfig
    from src.web.rendering.plotly_connector import FigureSpecToPlotly

    fig = go.Figure(
        data=[
            go.Heatmap(x=["A", "B"], y=["m1"], z=[[1.0, 5.0]], name="hm1"),
            go.Heatmap(x=["A", "B"], y=["m1"], z=[[2.0, 8.0]], name="hm2"),
        ]
    )
    legend = LegendConfig(
        role="primary",
        colorbar=ColorbarConfig(shared=False),
    )
    spec = FigureConfig(legends=[legend])
    FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)

    t0 = cast(Any, fig.data[0])
    t1 = cast(Any, fig.data[1])

    assert t0.showscale is True
    assert t1.showscale is True


def test_plotly_colorbar_title_side_is_top() -> None:
    """Colorbar title side defaults to 'top'."""
    import plotly.graph_objects as go

    from src.core.models.visualization.figure_config import FigureConfig
    from src.core.models.visualization.legend_config import ColorbarConfig, LegendConfig
    from src.web.rendering.plotly_connector import FigureSpecToPlotly

    fig = go.Figure(
        data=[
            go.Heatmap(x=["A", "B"], y=["m1"], z=[[1.0, 5.0]], name="hm1"),
        ]
    )
    legend = LegendConfig(
        role="primary",
        title="My Title",
        colorbar=ColorbarConfig(title_side="top"),
    )
    spec = FigureConfig(legends=[legend])
    FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)

    hm = cast(Any, fig.data[0])
    assert hm.colorbar.title.side == "top"
