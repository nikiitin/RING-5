"""
Tests for plot_config models — TypedDicts extracted from base_plot.py to Layer B.
"""

from src.core.models.plot_config import RelayoutData, SeriesStyle, ShapeConfig


class TestShapeConfig:
    """Tests for ShapeConfig TypedDict."""

    def test_basic_shape(self) -> None:
        shape: ShapeConfig = {
            "type": "line",
            "x0": 0.0,
            "y0": 0.5,
            "x1": 1.0,
            "y1": 0.5,
            "line": {"color": "#FF0000", "width": 2},
        }
        assert shape["type"] == "line"
        assert shape["x0"] == 0.0
        assert shape["line"]["color"] == "#FF0000"

    def test_string_coordinates(self) -> None:
        """Coordinates can be strings for categorical axes."""
        shape: ShapeConfig = {
            "type": "rect",
            "x0": "category_a",
            "y0": 0,
            "x1": "category_b",
            "y1": 10,
            "line": {"color": "#000000", "width": 1},
        }
        assert shape["x0"] == "category_a"

    def test_partial_shape(self) -> None:
        """total=False allows partial TypedDicts."""
        shape: ShapeConfig = {"type": "circle"}
        assert shape["type"] == "circle"


class TestSeriesStyle:
    """Tests for SeriesStyle TypedDict."""

    def test_full_style(self) -> None:
        style: SeriesStyle = {
            "name": "Custom Trace",
            "color": "#00FF00",
            "marker_symbol": "diamond",
            "pattern_shape": "/",
        }
        assert style["name"] == "Custom Trace"
        assert style["color"] == "#00FF00"

    def test_partial_style(self) -> None:
        style: SeriesStyle = {"name": "Only Name"}
        assert style["name"] == "Only Name"


class TestRelayoutData:
    """Tests for RelayoutData TypedDict."""

    def test_axis_range(self) -> None:
        data: RelayoutData = {
            "xaxis_range": [0.0, 10.0],
            "yaxis_range": [-1.0, 1.0],
        }
        assert data["xaxis_range"] == [0.0, 10.0]

    def test_legend_position(self) -> None:
        data: RelayoutData = {
            "legend_x": 0.5,
            "legend_y": 0.9,
            "legend_xanchor": "left",
            "legend_yanchor": "top",
        }
        assert data["legend_x"] == 0.5
        assert data["legend_xanchor"] == "left"

    def test_autorange(self) -> None:
        data: RelayoutData = {
            "xaxis_autorange": True,
            "yaxis_autorange": False,
        }
        assert data["xaxis_autorange"] is True
