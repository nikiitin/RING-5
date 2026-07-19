"""Unit tests for GroupedBarUtils — coordinate calculations and visual shapes."""

import pytest

from src.web.pages.ui.plotting.utils.grouped_bar_utils import GroupedBarUtils


class TestGroupedBarUtils:
    """Tests for grouped bar utility methods."""

    # -- Shapes --

    def test_create_shade_shape(self) -> None:
        band = GroupedBarUtils.create_shade_shape(0.0, 2.0)
        assert band.x0 == 0.0
        assert band.x1 == 2.0
        assert band.color

    def test_create_shade_shape_custom(self) -> None:
        band = GroupedBarUtils.create_shade_shape(1.0, 3.0, "#FF0000", 0.3)
        assert band.color == "#FF0000"
        assert band.opacity == 0.3

    def test_create_separator_shape(self) -> None:
        sep = GroupedBarUtils.create_separator_shape(1.5)
        assert sep.x == 1.5
        assert sep.dash == "dash"

    def test_create_separator_shape_custom(self) -> None:
        sep = GroupedBarUtils.create_separator_shape(2.0, "#000", "solid", 3.0)
        assert sep.color == "#000"
        assert sep.dash == "solid"
        assert sep.width == 3.0

    def test_create_isolation_separator(self) -> None:
        sep = GroupedBarUtils.create_isolation_separator(5.0)
        assert sep.x == 5.0
        assert sep.width == 2.0
        assert sep.dash == "solid"

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
        assert "separator_lines" in result
        assert "shaded_regions" in result
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
        # [test->req~ring5.figure.group-separators~1]
        config = {
            "bargroupgap": 1.0,
            "bargap": 0.2,
            "show_separators": True,
            "separator_color": "#CCC",
        }
        result = GroupedBarUtils.calculate_grouped_coordinates(
            ["A", "B", "C"], ["g1", "g2"], config
        )
        # Should have separator lines between A-B and B-C
        assert len(result["separator_lines"]) == 2

    def test_calculate_grouped_coordinates_shade_alternate(self) -> None:
        # [test->req~ring5.figure.alternate-category-shading~1]
        config = {
            "bargroupgap": 1.0,
            "bargap": 0.2,
            "shade_alternate": True,
        }
        result = GroupedBarUtils.calculate_grouped_coordinates(["A", "B", "C"], ["g1"], config)
        assert len(result["shaded_regions"]) == 1  # Only "B" (index 1) is shaded

    def test_calculate_grouped_coordinates_isolate_last(self) -> None:
        # [test->req~ring5.figure.group-separators~1]
        config = {
            "bargroupgap": 1.0,
            "bargap": 0.2,
            "isolate_last_group": True,
            "isolation_gap": 0.5,
        }
        result = GroupedBarUtils.calculate_grouped_coordinates(["A", "B", "C"], ["g1"], config)
        # Should have an isolation separator (the thick, solid one, width 2.0)
        iso_seps = [s for s in result["separator_lines"] if s.width == 2.0]
        assert len(iso_seps) == 1

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
