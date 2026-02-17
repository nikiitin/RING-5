"""Tests for extended WidgetSection definitions and spec_path wiring (Steps 27-28)."""

from src.core.visualization.widgets.widget_def import (
    ADVANCED_SECTION,
    ALL_SECTIONS,
    AXIS_COLORS,
    AXIS_X,
    AXIS_Y,
    AXIS_Y2,
    BACKGROUNDS,
    COLORS_PALETTE,
    DATA_LABELS,
    LAYOUT_DIMENSIONS,
    LAYOUT_MARGINS,
    LEGEND_APPEARANCE,
    LEGEND_POSITION,
    REFERENCE_LINES,
    STANDARD_SECTIONS,
    TYPOGRAPHY,
)


class TestExtendedSections:
    """Verify new WidgetSections have expected widget counts."""

    def test_axis_x_has_widgets(self) -> None:
        assert len(AXIS_X.widgets) >= 2
        assert AXIS_X.find("xaxis_tickangle") is not None

    def test_axis_y_has_widgets(self) -> None:
        assert len(AXIS_Y.widgets) >= 1
        assert AXIS_Y.find("yaxis_dtick") is not None

    def test_axis_y2_has_widgets(self) -> None:
        assert len(AXIS_Y2.widgets) >= 1
        assert AXIS_Y2.find("y2axis_dtick") is not None

    def test_colors_palette_has_widgets(self) -> None:
        assert len(COLORS_PALETTE.widgets) >= 1
        assert COLORS_PALETTE.find("color_palette") is not None

    def test_reference_lines_has_widgets(self) -> None:
        assert len(REFERENCE_LINES.widgets) >= 3
        assert REFERENCE_LINES.find("reference_line_enabled") is not None

    def test_advanced_section_has_widgets(self) -> None:
        assert len(ADVANCED_SECTION.widgets) >= 3
        assert ADVANCED_SECTION.find("show_error_bars") is not None
        assert ADVANCED_SECTION.find("download_format") is not None

    def test_all_sections_superset_of_standard(self) -> None:
        """ALL_SECTIONS contains everything in STANDARD_SECTIONS plus more."""
        standard_ids = {s.id for s in STANDARD_SECTIONS}
        all_ids = {s.id for s in ALL_SECTIONS}
        assert standard_ids <= all_ids
        assert len(ALL_SECTIONS) > len(STANDARD_SECTIONS)

    def test_no_duplicate_section_ids(self) -> None:
        """All section IDs in ALL_SECTIONS are unique."""
        ids = [s.id for s in ALL_SECTIONS]
        assert len(ids) == len(set(ids))


class TestSpecPathWiring:
    """Verify spec_path is set on key widgets for bidirectional bridge."""

    def test_dimensions_have_spec_path(self) -> None:
        w = LAYOUT_DIMENSIONS.find("width")
        assert w is not None and w.spec_path == "dimensions.width"
        h = LAYOUT_DIMENSIONS.find("height")
        assert h is not None and h.spec_path == "dimensions.height"

    def test_margins_have_spec_path(self) -> None:
        for key in ("margin_l", "margin_r", "margin_t", "margin_b", "margin_pad"):
            w = LAYOUT_MARGINS.find(key)
            assert w is not None and w.spec_path, f"{key} missing spec_path"

    def test_typography_font_sizes_have_spec_path(self) -> None:
        for key in (
            "title_font_size",
            "xaxis_title_font_size",
            "yaxis_title_font_size",
            "xaxis_tickfont_size",
            "yaxis_tickfont_size",
        ):
            w = TYPOGRAPHY.find(key)
            assert w is not None and w.spec_path, f"{key} missing spec_path"

    def test_tick_colors_have_spec_path(self) -> None:
        for key, section in (
            ("xaxis_tickfont_color", TYPOGRAPHY),
            ("yaxis_tickfont_color", TYPOGRAPHY),
        ):
            w = section.find(key)
            assert w is not None and w.spec_path, f"{key} missing spec_path"

    def test_legend_key_widgets_have_spec_path(self) -> None:
        for key in ("legend_bgcolor", "legend_border_color", "legend_font_size"):
            w = LEGEND_APPEARANCE.find(key)
            assert w is not None and w.spec_path, f"{key} missing spec_path"

        w = LEGEND_POSITION.find("legend_orientation")
        assert w is not None and w.spec_path

    def test_backgrounds_have_spec_path(self) -> None:
        for key in ("plot_bgcolor", "paper_bgcolor"):
            w = BACKGROUNDS.find(key)
            assert w is not None and w.spec_path, f"{key} missing spec_path"

    def test_grid_colors_have_spec_path(self) -> None:
        for key in ("grid_color", "axis_color"):
            w = AXIS_COLORS.find(key)
            assert w is not None and w.spec_path, f"{key} missing spec_path"

    def test_data_labels_key_widgets_have_spec_path(self) -> None:
        w = DATA_LABELS.find("show_values")
        assert w is not None and w.spec_path == "data_labels.enabled"
        w2 = DATA_LABELS.find("text_font_size")
        assert w2 is not None and w2.spec_path == "data_labels.font_size"

    def test_axis_x_has_spec_path(self) -> None:
        w = AXIS_X.find("xaxis_tickangle")
        assert w is not None and w.spec_path == "axes.xaxis.tick_angle"

    def test_colors_palette_has_spec_path(self) -> None:
        w = COLORS_PALETTE.find("color_palette")
        assert w is not None and w.spec_path == "color_palette"

    def test_total_wired_spec_paths(self) -> None:
        """At least 25 widgets should have spec_path wired."""
        count = sum(1 for s in ALL_SECTIONS for w in s.widgets if w.spec_path)
        assert count >= 25, f"Only {count} widgets have spec_path"
