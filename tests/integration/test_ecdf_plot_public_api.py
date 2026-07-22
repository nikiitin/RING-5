"""Public dual-engine empirical cumulative distribution workflow."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_ecdf_renders_grouped_survival_counts_in_both_engines() -> None:
    # [test->req~ring5.plot.ecdf~1]
    data = pd.DataFrame(
        {
            "variant": ["base"] * 4 + ["new"] * 4,
            "latency": [1.0, 2.0, 2.0, 4.0, 1.5, 2.5, 3.5, 5.0],
        }
    )
    config = {
        "x": "latency",
        "color": "variant",
        "ecdf_complementary": True,
        "ecdf_y_mode": "count",
        "ecdf_markers": True,
        "series_styles": {"base": {"use_color": True, "color": "#336699"}},
    }

    with ring5.Session() as session:
        plot = session.create_plot("ecdf", data=data, config=config, name="Latency survival")
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

        assert all(isinstance(trace, go.Scatter) for trace in plotly_figure.data)
        assert plotly_figure.data[0].line.shape == "hv"
        assert plotly_figure.data[0].line.color == "#336699"
        assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
        assert matplotlib_figure.axes[0].lines[0].get_drawstyle() == "steps-post"
