"""Public dual-engine radar chart workflow."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_radar_renders_shared_scale_and_styles_in_both_engines() -> None:
    # [test->req~ring5.plot.radar~1]
    data = pd.DataFrame(
        {
            "metric": ["speed", "energy", "size"] * 2,
            "variant": ["base"] * 3 + ["new"] * 3,
            "score": [0.6, 0.8, 0.7, 0.9, 0.5, 0.6],
        }
    )
    config = {
        "x": "metric",
        "y": "score",
        "color": "variant",
        "radar_scale_mode": "zero",
        "radar_fill": True,
        "radar_markers": True,
        "series_styles": {"base": {"use_color": True, "color": "#336699"}},
    }

    with ring5.Session() as session:
        plot = session.create_plot("radar", data=data, config=config, name="Profiles")
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

        assert all(isinstance(trace, go.Scatterpolar) for trace in plotly_figure.data)
        assert tuple(plotly_figure.layout.polar.radialaxis.range) == (0.0, 0.9)
        assert plotly_figure.data[0].line.color == "#336699"
        assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
        assert matplotlib_figure.axes[0].patches
        assert not matplotlib_figure.axes[0].axison
