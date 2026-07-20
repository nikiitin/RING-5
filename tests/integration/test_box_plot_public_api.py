"""Public dual-engine box plot workflow."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_box_plot_renders_both_engines_with_series_style() -> None:
    # [test->req~ring5.plot.box~1]
    data = pd.DataFrame(
        {
            "benchmark": ["A"] * 5 + ["B"] * 5,
            "variant": ["base", "base", "new", "new", "new"] * 2,
            "ipc": [1.0, 1.2, 1.1, 1.3, 4.0, 2.0, 2.2, 2.1, 2.3, 5.0],
        }
    )
    config = {
        "x": "benchmark",
        "y": "ipc",
        "color": "variant",
        "orientation": "vertical",
        "point_mode": "all",
        "quartile_method": "inclusive",
        "whisker_mode": "minmax",
        "series_styles": {
            "base": {"use_color": True, "color": "#336699"},
            "new": {"use_color": True, "color": "#cc5500"},
        },
    }

    with ring5.Session() as session:
        plot = session.create_plot("box", data=data, config=config, name="IPC spread")
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

        assert all(isinstance(trace, go.Box) for trace in plotly_figure.data)
        assert plotly_figure.layout.boxmode == "group"
        assert plotly_figure.data[0].fillcolor == "#336699"
        assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
        assert matplotlib_figure.axes[0].patches
