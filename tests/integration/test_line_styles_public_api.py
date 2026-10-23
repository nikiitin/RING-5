"""Public API coverage for cross-engine line and connector styles."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure

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
        assert isinstance(plotly_figure, go.Figure)
        plotly_line = plotly_figure.data[0]
        assert isinstance(plotly_line, go.Scatter)
        assert plotly_line.line.shape == "spline"
        assert plotly_line.line.dash == "dashdot"
        assert plotly_line.line.width == 3.5
        assert plotly_line.marker.symbol == "diamond"
        assert plotly_line.marker.size == 10
        assert plotly_line.connectgaps is True

        matplotlib_figure = session.render(plot, engine="matplotlib")
        assert isinstance(matplotlib_figure, Figure)
        matplotlib_line = matplotlib_figure.axes[0].lines[0]
        assert matplotlib_line.get_drawstyle() == "default"
        assert matplotlib_line.get_linestyle() == "-."
        assert matplotlib_line.get_linewidth() == 3.5
        assert matplotlib_line.get_marker() == "D"
        assert matplotlib_line.get_markersize() == 10
        assert len(np.asarray(matplotlib_line.get_xdata())) > 4
        assert np.isfinite(matplotlib_line.get_ydata()).all()
        marker_indices = matplotlib_line.get_markevery()
        assert isinstance(marker_indices, list)
        assert len(marker_indices) == 4


def test_line_gaps_remain_visible_by_default() -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "line",
            data=_data(),
            config={"x": "sample", "y": "value", "show_markers": False},
        )

        plotly_figure = session.render(plot, engine="plotly")
        assert isinstance(plotly_figure, go.Figure)
        trace = plotly_figure.data[0]
        assert isinstance(trace, go.Scatter)
        assert trace.connectgaps is False
        assert trace.mode == "lines"

        matplotlib_figure = session.render(plot, engine="matplotlib")
        assert isinstance(matplotlib_figure, Figure)
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
        assert isinstance(plotly_figure, go.Figure)
        trace = plotly_figure.data[0]
        assert isinstance(trace, go.Scatter)
        assert trace.marker.size == expected_diameter
        matplotlib_figure = session.render(plot, engine="matplotlib")
        assert isinstance(matplotlib_figure, Figure)
        try:
            points = matplotlib_figure.axes[0].collections[0]
            assert isinstance(points, PathCollection)
            assert points.get_sizes().tolist() == [expected_diameter**2]
        finally:
            plt.close(matplotlib_figure)


@pytest.mark.parametrize(
    ("symbol", "matplotlib_marker"),
    [
        ("circle", "o"),
        ("square", "s"),
        ("diamond", "D"),
        ("cross", "P"),
        ("x", "X"),
        ("triangle-up", "^"),
        ("triangle-down", "v"),
    ],
)
def test_public_scatter_overrides_preserve_geometry_and_borders(
    symbol: str, matplotlib_marker: str
) -> None:
    """Named marker overrides keep the reviewed coordinates and other styling."""
    from matplotlib import pyplot as plt
    from matplotlib.colors import to_rgba
    from matplotlib.markers import MarkerStyle

    config = {
        "x": "sample",
        "y": "value",
        "marker_size": 10,
        "bar_border_width": 2.5,
        "bar_border_color": "#cc3300",
        "series_styles": {
            "value": {
                "symbol": symbol,
                "marker_size": 14,
                "color": "#2468ac",
                "use_color": True,
                "name": "Observed",
            }
        },
    }
    with ring5.Session() as session:
        plot = session.create_plot("scatter", data=_data(), config=config)
        plotly_figure = session.render(plot, engine="plotly")
        assert isinstance(plotly_figure, go.Figure)
        trace = plotly_figure.data[0]
        assert isinstance(trace, go.Scatter)
        assert trace.name == "Observed"
        assert trace.marker.symbol == symbol
        assert trace.marker.size == 14
        assert trace.marker.color == "#2468ac"
        assert trace.marker.line.color == "#cc3300"
        assert trace.marker.line.width == 2.5

        matplotlib_figure = session.render(plot, engine="matplotlib")
        assert isinstance(matplotlib_figure, Figure)
        try:
            points = matplotlib_figure.axes[0].collections[0]
            assert isinstance(points, PathCollection)
            expected_marker = MarkerStyle(matplotlib_marker)
            expected_path = expected_marker.get_path().transformed(expected_marker.get_transform())
            np.testing.assert_allclose(
                np.asarray(points.get_paths()[0].vertices), np.asarray(expected_path.vertices)
            )
            np.testing.assert_array_equal(points.get_paths()[0].codes, expected_path.codes)
            np.testing.assert_allclose(
                np.ma.asarray(points.get_offsets(), dtype=float).filled(np.nan),
                np.array([[0, 1], [1, 2.5], [np.nan, np.nan], [3, 3], [4, 5]], dtype=float),
                equal_nan=True,
            )
            assert points.get_label() == "Observed"
            assert points.get_sizes().tolist() == [14**2]
            assert np.asarray(points.get_facecolor()).tolist() == [list(to_rgba("#2468ac"))]
            assert np.asarray(points.get_edgecolor()).tolist() == [list(to_rgba("#cc3300"))]
            assert np.asarray(points.get_linewidth()).tolist() == [2.5]
            assert points.get_alpha() == trace.opacity
        finally:
            plt.close(matplotlib_figure)
