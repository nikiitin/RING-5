"""
Tests for plot_config models — TypedDicts extracted from base_plot.py to Layer B.
"""

from typing import cast

from src.core.models.plot_config import ShapeConfig


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
        shape: ShapeConfig = cast(ShapeConfig, {"type": "circle"})
        assert shape["type"] == "circle"
