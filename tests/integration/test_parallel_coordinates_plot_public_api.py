"""Public dual-engine parallel-coordinate workflow."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_parallel_coordinates_render_order_encoding_brushes_and_colors() -> None:
    # [test->req~ring5.plot.parallel-coordinates~1]
    data = pd.DataFrame(
        {
            "profile": ["base", "tuned", "efficient"],
            "ipc": [1.0, 2.0, 1.5],
            "power": [12.0, 20.0, 14.0],
            "cores": [2, 8, 4],
        }
    )
    config = {
        "parallel_dimensions": ["power", "profile", "ipc", "cores"],
        "parallel_color": "ipc",
        "parallel_ranges": {"power": [0, 25]},
        "parallel_brushes": {"ipc": [1.2, 2.0]},
        "parallel_colorscale": "Cividis",
        "parallel_reverse_colorscale": True,
        "parallel_show_colorbar": False,
    }

    with ring5.Session() as session:
        plot = session.create_plot(
            "parallel_coordinates", data=data, config=config, name="Profiles"
        )
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

        assert len(plotly_figure.data) == 1
        assert isinstance(plotly_figure.data[0], go.Parcoords)
        assert [dimension.label for dimension in plotly_figure.data[0].dimensions] == [
            "power",
            "profile",
            "ipc",
            "cores",
        ]
        assert list(plotly_figure.data[0].dimensions[1].ticktext) == [
            "base",
            "tuned",
            "efficient",
        ]
        assert tuple(plotly_figure.data[0].dimensions[2].constraintrange) == (1.2, 2.0)
        assert plotly_figure.data[0].line.reversescale
        assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
        assert len(matplotlib_figure.axes[0].lines) == 7
        assert not matplotlib_figure.axes[0].axison
