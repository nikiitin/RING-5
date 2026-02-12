"""Unit tests for GroupedBarUtils — coordinate calculations and visual shapes."""

import pytest

from src.web.pages.ui.plotting.utils.grouped_bar_utils import GroupedBarUtils


class TestGroupedBarUtils:
    """Tests for grouped bar utility methods."""

    # -- Shapes --

    def test_create_shade_shape(self) -> None:
        shape = GroupedBarUtils.create_shade_shape(0.0, 2.0)
        assert shape["type"] == "rect"
        assert shape["x0"] == 0.0
        assert shape["x1"] == 2.0
        assert shape["layer"] == "below"
        assert "fillcolor" in shape

    def test_create_shade_shape_custom(self) -> None:
        shape = GroupedBarUtils.create_shade_shape(1.0, 3.0, "#FF0000", 0.3)
        assert shape["fillcolor"] == "#FF0000"
        assert shape["opacity"] == 0.3

    def test_create_separator_shape(self) -> None:
        shape = GroupedBarUtils.create_separator_shape(1.5)
        assert shape["type"] == "line"
        assert shape["x0"] == 1.5
        assert shape["x1"] == 1.5
        assert shape["line"]["dash"] == "dash"

    def test_create_separator_shape_custom(self) -> None:
        shape = GroupedBarUtils.create_separator_shape(2.0, "#000", "solid", 3)
        assert shape["line"]["color"] == "#000"
        assert shape["line"]["dash"] == "solid"
        assert shape["line"]["width"] == 3

    def test_create_isolation_separator(self) -> None:
        shape = GroupedBarUtils.create_isolation_separator(5.0)
        assert shape["type"] == "line"
        assert shape["x0"] == 5.0
        assert shape["line"]["width"] == 2
        assert shape["line"]["dash"] == "solid"

    # -- Annotations --

    def test_build_category_annotations_empty(self) -> None:
        anns = GroupedBarUtils.build_category_annotations([])
        assert anns == []

    def test_build_category_annotations(self) -> None:
        centers = [(0.5, "mcf"), (2.5, "omnetpp")]
        anns = GroupedBarUtils.build_category_annotations(centers)
        assert len(anns) == 2
        assert "<b>mcf</b>" in anns[0]["text"]
        assert anns[0]["x"] == 0.5
        assert anns[0]["showarrow"] is False

    def test_build_category_annotations_custom_font(self) -> None:
        centers = [(1.0, "A")]
        anns = GroupedBarUtils.build_category_annotations(
            centers, font_size=18, font_color="#333", y_offset=-0.2
        )
        assert anns[0]["font"]["size"] == 18
        assert anns[0]["font"]["color"] == "#333"
        assert anns[0]["y"] == -0.2

    # -- Coordinate calculation --

    def test_calculate_grouped_coordinates_basic(self) -> None:
        categories = ["mcf", "omnetpp"]
        groups = ["base", "opt"]
        config = {"bargroupgap": 1.0, "bargap": 0.2}

        result = GroupedBarUtils.calculate_grouped_coordinates(categories, groups, config)

        assert "coord_map" in result
        assert "tick_vals" in result
        assert "tick_text" in result
        assert "cat_centers" in result
        assert "shapes" in result
        assert "bar_width" in result

        # 2 categories × 2 groups = 4 coordinates
        assert len(result["coord_map"]) == 4
        assert len(result["tick_vals"]) == 4

    def test_calculate_grouped_coordinates_bar_width(self) -> None:
        result = GroupedBarUtils.calculate_grouped_coordinates(
            ["A"], ["g1"], {"bargroupgap": 0.0, "bargap": 0.3}
        )
        assert result["bar_width"] == pytest.approx(0.7)

    def test_calculate_grouped_coordinates_no_groups(self) -> None:
        result = GroupedBarUtils.calculate_grouped_coordinates(
            ["A", "B"], [], {"bargroupgap": 0.0, "bargap": 0.2}
        )
        # Each category is a single bar
        assert len(result["tick_vals"]) == 2

    def test_calculate_grouped_coordinates_with_separators(self) -> None:
        config = {
            "bargroupgap": 1.0,
            "bargap": 0.2,
            "show_separators": True,
            "separator_color": "#CCC",
        }
        result = GroupedBarUtils.calculate_grouped_coordinates(
            ["A", "B", "C"], ["g1", "g2"], config
        )
        # Should have separator shapes between A-B and B-C
        sep_shapes = [s for s in result["shapes"] if s["type"] == "line"]
        assert len(sep_shapes) == 2

    def test_calculate_grouped_coordinates_shade_alternate(self) -> None:
        config = {
            "bargroupgap": 1.0,
            "bargap": 0.2,
            "shade_alternate": True,
        }
        result = GroupedBarUtils.calculate_grouped_coordinates(["A", "B", "C"], ["g1"], config)
        rect_shapes = [s for s in result["shapes"] if s["type"] == "rect"]
        assert len(rect_shapes) == 1  # Only "B" (index 1) is shaded

    def test_calculate_grouped_coordinates_isolate_last(self) -> None:
        config = {
            "bargroupgap": 1.0,
            "bargap": 0.2,
            "isolate_last_group": True,
            "isolation_gap": 0.5,
        }
        result = GroupedBarUtils.calculate_grouped_coordinates(["A", "B", "C"], ["g1"], config)
        # Should have an isolation separator
        iso_shapes = [
            s
            for s in result["shapes"]
            if s["type"] == "line" and s.get("line", {}).get("width") == 2
        ]
        assert len(iso_shapes) == 1

    def test_coord_map_keys_are_tuples_with_groups(self) -> None:
        result = GroupedBarUtils.calculate_grouped_coordinates(
            ["A"], ["g1", "g2"], {"bargroupgap": 0.0, "bargap": 0.2}
        )
        assert ("A", "g1") in result["coord_map"]
        assert ("A", "g2") in result["coord_map"]

    def test_coord_map_keys_simple_with_no_groups(self) -> None:
        result = GroupedBarUtils.calculate_grouped_coordinates(
            ["A", "B"], [], {"bargroupgap": 0.0, "bargap": 0.2}
        )
        assert "A" in result["coord_map"]
        assert "B" in result["coord_map"]

    def test_cat_centers_count(self) -> None:
        result = GroupedBarUtils.calculate_grouped_coordinates(
            ["A", "B", "C"], ["g1", "g2"], {"bargroupgap": 0.5, "bargap": 0.2}
        )
        assert len(result["cat_centers"]) == 3

    def test_tick_text_matches_groups(self) -> None:
        result = GroupedBarUtils.calculate_grouped_coordinates(
            ["A", "B"], ["low", "high"], {"bargroupgap": 0.0, "bargap": 0.2}
        )
        assert result["tick_text"] == ["low", "high", "low", "high"]
