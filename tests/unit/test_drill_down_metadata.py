"""Point-aligned drill-down metadata tests for every registered plot family."""

from __future__ import annotations

from ring5 import Session
from typing import cast
import plotly.graph_objects as go

from typing import Any

import pandas as pd
import pytest

from src.web.pages.ui.plotting.plot_factory import PlotFactory

_CATEGORICAL = pd.DataFrame(
    {
        "workload": ["A", "A", "B"],
        "variant": ["v1", "v2", "v1"],
        "ipc": [1.0, 2.0, 3.0],
        "power": [4.0, 5.0, 6.0],
    }
)


@pytest.mark.parametrize(
    ("plot_type", "config", "data"),
    [
        ("bar", {"x": "workload", "y": "ipc", "color": "variant"}, _CATEGORICAL),
        ("line", {"x": "workload", "y": "ipc", "color": "variant"}, _CATEGORICAL),
        ("scatter", {"x": "workload", "y": "ipc", "color": "variant"}, _CATEGORICAL),
        ("stacked_bar", {"x": "workload", "y_columns": ["ipc", "power"]}, _CATEGORICAL),
        (
            "grouped_bar",
            {"x": "workload", "y": "ipc", "group": "variant"},
            _CATEGORICAL,
        ),
        (
            "grouped_stacked_bar",
            {"x": "workload", "group": "variant", "y_columns": ["ipc", "power"]},
            _CATEGORICAL,
        ),
        (
            "dual_axis_bar_dot",
            {"x": "workload", "y_bar": "ipc", "y_dot": "power", "color": "variant"},
            _CATEGORICAL,
        ),
        (
            "heatmap",
            {"x": "workload", "metric_columns": ["ipc", "power"]},
            _CATEGORICAL,
        ),
        (
            "histogram",
            {"histogram_variable": "latency"},
            pd.DataFrame({"latency..0-9": [1, 2], "latency..10-19": [3, 4]}),
        ),
    ],
)
def test_every_plot_family_embeds_source_filters_without_mutating_data(
    plot_type: str,
    config: dict[str, Any],
    data: pd.DataFrame,
    plot_session: Session,
) -> None:
    # [test->req~ring5.plots.drill-down~1]
    snapshot = data.copy(deep=True)
    plot = PlotFactory.create_plot(plot_type, 1, plot_type)

    plot.processed_data = data
    plot.config = config
    figure = cast(go.Figure, plot_session.render(plot))

    assert figure.data
    assert all(
        isinstance(trace.meta, dict) and "ring5_drilldown" in trace.meta for trace in figure.data
    )
    assert data.equals(snapshot)


def test_metadata_keeps_existing_hover_customdata_and_heatmap_cell_alignment(
    plot_session: Session,
) -> None:
    stacked = PlotFactory.create_plot("stacked_bar", 1, "stacked")
    stacked.processed_data = _CATEGORICAL
    stacked.config = {"x": "workload", "y_columns": ["ipc", "power"]}
    stacked_figure = cast(go.Figure, plot_session.render(stacked))
    assert list(stacked_figure.data[0].customdata) == [5.0, 7.0, 9.0]
    assert stacked_figure.data[0].meta["ring5_drilldown"][0] == {"workload": "A"}

    heatmap = PlotFactory.create_plot("heatmap", 2, "heatmap")
    heatmap.processed_data = _CATEGORICAL
    heatmap.config = {"x": "workload", "metric_columns": ["ipc", "power"]}
    heatmap_figure = cast(go.Figure, plot_session.render(heatmap))
    payload = heatmap_figure.data[0].meta["ring5_drilldown"]
    assert payload[0][1] == {"workload": "B"}
