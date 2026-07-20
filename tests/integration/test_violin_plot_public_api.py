"""Public dual-engine violin plot workflow."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_violin_plot_renders_both_engines_with_density_controls() -> None:
    # [test->req~ring5.plot.violin~1]
    data = pd.DataFrame(
        {
            "benchmark": ["A"] * 6 + ["B"] * 6,
            "variant": ["base"] * 3 + ["new"] * 3 + ["base"] * 3 + ["new"] * 3,
            "ipc": [1.0, 1.2, 1.4, 1.5, 1.8, 2.0, 2.0, 2.2, 2.4, 2.6, 3.0, 3.4],
        }
    )
    config = {
        "x": "benchmark",
        "y": "ipc",
        "color": "variant",
        "orientation": "vertical",
        "bandwidth_method": "silverman",
        "density_scale": "count",
        "summary_mode": "box+mean",
        "point_mode": "all",
        "series_styles": {"base": {"use_color": True, "color": "#336699"}},
    }

    with ring5.Session() as session:
        plot = session.create_plot("violin", data=data, config=config, name="IPC density")
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

        assert all(isinstance(trace, go.Violin) for trace in plotly_figure.data)
        assert plotly_figure.layout.violinmode == "group"
        assert plotly_figure.data[0].fillcolor == "#336699"
        assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
        assert matplotlib_figure.axes[0].collections
