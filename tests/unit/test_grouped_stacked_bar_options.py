from typing import Any, cast

import pandas as pd
import plotly.graph_objects as go
import pytest
from pandas import DataFrame

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)


@pytest.fixture
def sample_data() -> DataFrame:
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "B", "B"],
            "Config": ["Small", "Large", "Small", "Large"],
            "Ticks": [100, 200, 150, 250],
            "Energy": [10, 20, 15, 25],
            "Ticks.sd": [5, 10, 7, 12],
        }
    )


def test_create_figure_renaming(sample_data: Any) -> None:

    plot = GroupedStackedBarPlot(1, "Test Plot")

    config = {
        "x": "Benchmark",
        "group": "Config",
        "y_columns": ["Ticks", "Energy"],
        "series_styles": {
            "Ticks": {"name": "Total Cycles", "color": "#FF0000", "use_color": True},
            "Energy": {"name": "Joules", "color": "#00FF00", "use_color": True},
        },
    }

    fig = plot.create_figure(sample_data, config)
    plot._applicator.apply_styles(fig, config)

    traces = cast(list[go.Bar], list(fig.data))
    t1 = next(t for t in traces if t.name == "Total Cycles")
    assert cast(go.bar.Marker, t1.marker).color == "#FF0000"

    t2 = next(t for t in traces if t.name == "Joules")
    assert cast(go.bar.Marker, t2.marker).color == "#00FF00"


def test_create_figure_major_minor_renaming(sample_data: Any) -> None:

    plot = GroupedStackedBarPlot(1, "Test Plot")

    config = {
        "x": "Benchmark",
        "group": "Config",
        "y_columns": ["Ticks"],
        "xaxis_labels": {"A": "Alpha"},
        "group_renames": {"Small": "Tiny"},
        "bargroupgap": 0.1,
    }

    fig = plot.create_figure(sample_data, config)

    # The layout annotations are used for X-axis labels in this plot type
    layout = fig.layout
    annotations = layout.annotations
    labels = [a.text for a in annotations]

    assert "<b>Alpha</b>" in labels

    # Preserve string-valued minor-group labels instead of replacing them with indices.
    ticktext = fig.layout.xaxis.ticktext
    assert "Tiny" in ticktext, f"Expected 'Tiny' in ticktext, found: {ticktext}"
    assert "Large" in ticktext

    # A failed coordinate lookup leaves a gap in the rendered trace.
    trace0 = cast(go.Bar, fig.data[0])
    x_values = trace0.x
    assert x_values is not None
    assert len(list(x_values)) > 0
    assert all(
        x is not None for x in x_values
    ), f"Found None in X coordinates: {x_values}. Traces lost?"
