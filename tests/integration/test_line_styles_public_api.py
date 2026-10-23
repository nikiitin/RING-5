"""Public API coverage for cross-engine line and connector styles."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sample": [0, 1, 2, 3, 4],
            "value": [1.0, 2.5, float("nan"), 3.0, 5.0],
        }
    )


def test_public_line_styles_match_in_both_engines() -> None:
    # [test->req~ring5.figure.line-styles~1]
    config = {
        "x": "sample",
        "y": "value",
        "line_shape": "spline",
        "line_dash": "dashdot",
        "line_width": 3.5,
        "show_markers": True,
        "marker_symbol": "diamond",
        "marker_size": 10,
        "connect_gaps": True,
    }
    with ring5.Session() as session:
        plot = session.create_plot("line", data=_data(), config=config)

        plotly_figure = session.render(plot, engine="plotly")
        plotly_line = plotly_figure.data[0]
        assert plotly_line.line.shape == "spline"
        assert plotly_line.line.dash == "dashdot"
        assert plotly_line.line.width == 3.5
        assert plotly_line.marker.symbol == "diamond"
        assert plotly_line.marker.size == 10
        assert plotly_line.connectgaps is True

        matplotlib_figure = session.render(plot, engine="matplotlib")
        matplotlib_line = matplotlib_figure.axes[0].lines[0]
        assert matplotlib_line.get_drawstyle() == "default"
        assert matplotlib_line.get_linestyle() == "-."
        assert matplotlib_line.get_linewidth() == 3.5
        assert matplotlib_line.get_marker() == "D"
        assert matplotlib_line.get_markersize() == 10
        assert len(matplotlib_line.get_xdata()) > 4
        assert np.isfinite(matplotlib_line.get_ydata()).all()
        assert len(matplotlib_line.get_markevery()) == 4


def test_line_gaps_remain_visible_by_default() -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "line",
            data=_data(),
            config={"x": "sample", "y": "value", "show_markers": False},
        )

        plotly_figure = session.render(plot, engine="plotly")
        assert plotly_figure.data[0].connectgaps is False
        assert plotly_figure.data[0].mode == "lines"

        matplotlib_figure = session.render(plot, engine="matplotlib")
        matplotlib_line = matplotlib_figure.axes[0].lines[0]
        assert np.isnan(matplotlib_line.get_ydata()).any()
        assert matplotlib_line.get_marker() == "None"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("line_shape", "curvy"),
        ("line_dash", "scribble"),
        ("line_width", 0.0),
        ("marker_symbol", "hexagon"),
        ("marker_size", 0),
        ("show_markers", "yes"),
        ("connect_gaps", 1),
    ],
)
def test_public_line_style_validation_is_typed(field: str, value: object) -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match=field):
            session.create_plot(
                "line",
                data=_data(),
                config={"x": "sample", "y": "value", field: value},
            )
        assert session.plots == []


@pytest.mark.parametrize("per_trace", [False, True])
def test_public_scatter_marker_diameters_match_after_common_styling(per_trace: bool) -> None:
    """Global and named overrides retain diameter semantics through both connectors."""
    from matplotlib import pyplot as plt

    config = {
        "x": "sample",
        "y": "value",
        "marker_size": 10,
        "series_styles": {"value": {"marker_size": 14}} if per_trace else {},
    }
    expected_diameter = 14 if per_trace else 10
    with ring5.Session() as session:
        plot = session.create_plot("scatter", data=_data(), config=config)
        plotly_figure = session.render(plot, engine="plotly")
        assert plotly_figure.data[0].marker.size == expected_diameter
        matplotlib_figure = session.render(plot, engine="matplotlib")
        try:
            points = matplotlib_figure.axes[0].collections[0]
            assert points.get_sizes().tolist() == [expected_diameter**2]
        finally:
            plt.close(matplotlib_figure)
