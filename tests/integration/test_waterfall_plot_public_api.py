"""Public dual-engine waterfall workflow."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_waterfall_renders_exact_semantics_in_both_engines() -> None:
    # [test->req~ring5.plot.waterfall~1]
    data = pd.DataFrame(
        {
            "step": ["Starting balance", "Sales", "Costs", "Forecast", "Checkpoint"],
            "change": [50.0, 30.0, -20.0, 100.0, 0.0],
        }
    )
    config = {
        "x": "step",
        "y": "change",
        "waterfall_absolute": ["Starting balance", "Forecast"],
        "waterfall_subtotals": ["Checkpoint"],
        "waterfall_final_total": True,
        "waterfall_connectors": True,
        "waterfall_show_values": True,
    }

    with ring5.Session() as session:
        plot = session.create_plot("waterfall", data=data, config=config, name="Balance bridge")
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

        assert len(plotly_figure.data) == 1
        assert isinstance(plotly_figure.data[0], go.Waterfall)
        assert list(plotly_figure.data[0].measure) == [
            "absolute",
            "relative",
            "relative",
            "absolute",
            "total",
            "total",
        ]
        assert plotly_figure.data[0].increasing.marker.color == "#2ca02c"
        assert plotly_figure.data[0].decreasing.marker.color == "#d62728"
        assert plotly_figure.data[0].totals.marker.color == "#4c78a8"
        assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
        assert len(matplotlib_figure.axes[0].patches) == 6
        assert len(matplotlib_figure.axes[0].lines) == 5
