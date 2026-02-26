from __future__ import annotations

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.web.pages.ui.plotting.types.heatmap_plot import HeatmapPlot
from src.web.rendering.trace_to_plotly import traces_to_plotly


def test_heatmap_plot_creates_trace_per_benchmark() -> None:
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
    assert trace_names == ["benchmark_name=bm1", "benchmark_name=bm2"]

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

    assert len(fig.data) == 2
    assert fig.layout.xaxis2 is not None
    assert fig.layout.yaxis2 is not None
