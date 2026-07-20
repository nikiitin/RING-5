"""Public dual-engine stacked area workflow."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_normalized_area_renders_both_engines_with_series_style() -> None:
    # [test->req~ring5.plot.area~1]
    data = pd.DataFrame(
        {
            "phase": [1, 2, 3, 1, 2, 3],
            "component": ["cpu"] * 3 + ["memory"] * 3,
            "power": [2.0, 3.0, 4.0, 1.0, 3.0, 2.0],
        }
    )
    config = {
        "x": "phase",
        "y": "power",
        "color": "component",
        "area_mode": "normalize",
        "area_interpolation": "hv",
        "series_styles": {"cpu": {"use_color": True, "color": "#336699"}},
    }

    with ring5.Session() as session:
        plot = session.create_plot("area", data=data, config=config, name="Power share")
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

        assert all(isinstance(trace, go.Scatter) for trace in plotly_figure.data)
        assert plotly_figure.data[0].fill == "tozeroy"
        assert plotly_figure.data[1].fill == "tonexty"
        assert plotly_figure.data[0].line.color == "#336699"
        assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
        assert len(matplotlib_figure.axes[0].collections) == 2
