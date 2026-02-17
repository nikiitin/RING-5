"""
Phase 4 tests — Declarative widget section definitions and wiring.

Validates:
    1. All new standard sections have correct keys and default values
    2. Section defaults match base_ui.py hand-coded defaults
    3. LEGEND aggregate equals union of sub-sections
    4. DATA_LABELS section covers all expected config keys
    5. Sections have no duplicate keys internally
"""

from __future__ import annotations

from typing import Dict, Set

from src.core.visualization.widgets.widget_def import (
    AXIS_COLORS,
    BACKGROUNDS,
    DATA_LABELS,
    LAYOUT_DIMENSIONS,
    LAYOUT_MARGINS,
    LEGEND,
    LEGEND_APPEARANCE,
    LEGEND_POSITION,
    LEGEND_SIZING,
    STANDARD_SECTIONS,
    TYPOGRAPHY,
    CheckboxWidgetDef,
    ColorWidgetDef,
    NumberWidgetDef,
    SelectWidgetDef,
    SliderWidgetDef,
    TextWidgetDef,
)

# ─── 1. Default alignment with base_ui.py ───────────────────────────────────


class TestDefaultAlignment:
    """Standard section defaults must match base_ui.py hand-coded values."""

    def test_dimensions_defaults(self) -> None:
        d = LAYOUT_DIMENSIONS.defaults()
        assert d["width"] == 800
        assert d["height"] == 500

    def test_margin_defaults(self) -> None:
        d = LAYOUT_MARGINS.defaults()
        assert d["margin_l"] == 100
        assert d["margin_r"] == 100
        assert d["margin_t"] == 80
        assert d["margin_b"] == 120
        assert d["margin_pad"] == 0
        assert d["automargin"] is True

    def test_typography_defaults(self) -> None:
        d = TYPOGRAPHY.defaults()
        assert d["title_font_size"] == 18
        assert d["xaxis_title_font_size"] == 14
        assert d["yaxis_title_font_size"] == 14
        assert d["xaxis_tickfont_size"] == 12
        assert d["yaxis_tickfont_size"] == 12
        assert d["yaxis_title_standoff"] == 0
        assert d["yaxis_title_vshift"] == 0
        assert d["xaxis_tickfont_color"] == "#444444"
        assert d["yaxis_tickfont_color"] == "#444444"

    def test_backgrounds_defaults(self) -> None:
        d = BACKGROUNDS.defaults()
        assert d["transparent_bg"] is False
        assert d["plot_bgcolor"] == "#ffffff"
        assert d["paper_bgcolor"] == "#ffffff"

    def test_axis_colors_defaults(self) -> None:
        d = AXIS_COLORS.defaults()
        assert d["grid_color"] == "#e5e5e5"
        assert d["axis_color"] == "#444444"

    def test_legend_position_defaults(self) -> None:
        d = LEGEND_POSITION.defaults()
        assert d["legend_orientation"] == "v"
        assert d["legend_ncols"] == 0
        assert d["legend_col_width"] == 150
        assert d["legend_valign"] == "middle"

    def test_legend_appearance_defaults(self) -> None:
        d = LEGEND_APPEARANCE.defaults()
        assert d["transparent_legend"] is False
        assert d["legend_bgcolor"] == "#ffffff"
        assert d["legend_border_color"] == "#000000"
        assert d["legend_border_width"] == 0
        assert d["legend_font_color"] == "#000000"
        assert d["legend_font_size"] == 12
        assert d["legend_title_font_color"] == "#000000"
        assert d["legend_title_font_size"] == 14

    def test_legend_sizing_defaults(self) -> None:
        d = LEGEND_SIZING.defaults()
        assert d["legend_itemsizing"] == "constant"
        assert d["legend_itemwidth"] == 30
        assert d["legend_tracegroupgap"] == 10

    def test_data_labels_defaults(self) -> None:
        d = DATA_LABELS.defaults()
        assert d["show_values"] is False
        assert d["text_color_mode"] == "auto"
        assert d["text_color"] == "#000000"
        assert d["text_font_size"] == 10
        assert d["text_rotation"] == 0
        assert d["text_position"] == "auto"
        assert d["text_anchor"] == "auto"
        assert d["text_format"] == ".2f"
        assert d["text_display_logic"] == "all"
        assert d["text_threshold"] == 0.0
        assert d["text_constraint"] == "none"


# ─── 2. Section structural integrity ────────────────────────────────────────


class TestSectionIntegrity:
    """Verify sections have no internal issues."""

    def test_no_duplicate_keys_within_section(self) -> None:
        """Each section must have unique keys internally."""
        for section in STANDARD_SECTIONS:
            keys = section.keys()
            assert len(keys) == len(set(keys)), f"Section '{section.id}' has duplicate keys"

    def test_no_duplicate_keys_across_standard_sections(self) -> None:
        """Keys should not be duplicated across standard sections."""
        seen: Dict[str, str] = {}
        for section in STANDARD_SECTIONS:
            for key in section.keys():
                assert (
                    key not in seen
                ), f"Key '{key}' duplicated in '{section.id}' and '{seen[key]}'"
                seen[key] = section.id

    def test_legend_aggregate_equals_union(self) -> None:
        """LEGEND aggregate section should contain all legend sub-section keys."""
        sub_keys: Set[str] = set()
        for s in (LEGEND_POSITION, LEGEND_APPEARANCE, LEGEND_SIZING):
            sub_keys.update(s.keys())

        legend_keys = set(LEGEND.keys())
        assert legend_keys == sub_keys

    def test_all_color_widgets_have_hex_defaults(self) -> None:
        """ColorWidgetDef defaults must start with #."""
        for section in STANDARD_SECTIONS:
            for w in section.widgets:
                if isinstance(w, ColorWidgetDef):
                    assert str(w.default).startswith("#"), (
                        f"ColorWidgetDef '{w.key}' default '{w.default}' " f"is not a hex color"
                    )

    def test_all_select_widgets_have_options(self) -> None:
        """SelectWidgetDef must have at least 2 options."""
        for section in STANDARD_SECTIONS:
            for w in section.widgets:
                if isinstance(w, SelectWidgetDef):
                    assert len(w.options) >= 2, f"SelectWidgetDef '{w.key}' has < 2 options"

    def test_all_select_defaults_are_valid_options(self) -> None:
        """SelectWidgetDef default must be one of its options."""
        for section in STANDARD_SECTIONS:
            for w in section.widgets:
                if isinstance(w, SelectWidgetDef):
                    assert w.default in w.options, (
                        f"SelectWidgetDef '{w.key}' default '{w.default}' "
                        f"is not in options {w.options}"
                    )

    def test_number_widgets_default_in_range(self) -> None:
        """NumberWidgetDef default must be within min/max bounds."""
        for section in STANDARD_SECTIONS:
            for w in section.widgets:
                if isinstance(w, NumberWidgetDef):
                    if w.min_value is not None:
                        assert w.default >= w.min_value, (
                            f"NumberWidgetDef '{w.key}' default {w.default} " f"< min {w.min_value}"
                        )
                    if w.max_value is not None:
                        assert w.default <= w.max_value, (
                            f"NumberWidgetDef '{w.key}' default {w.default} " f"> max {w.max_value}"
                        )

    def test_data_labels_covers_all_expected_keys(self) -> None:
        """DATA_LABELS must include all config keys from base_ui render_data_labels_ui."""
        expected = {
            "show_values",
            "text_color_mode",
            "text_color",
            "text_font_size",
            "text_rotation",
            "text_position",
            "text_anchor",
            "text_format",
            "text_display_logic",
            "text_threshold",
            "text_constraint",
        }
        actual = set(DATA_LABELS.keys())
        assert expected == actual


# ─── 3. Widget type correctness ─────────────────────────────────────────────


class TestWidgetTypes:
    """Verify widgets use the correct DEF type for their purpose."""

    def test_sliders_for_dimensions(self) -> None:
        for w in LAYOUT_DIMENSIONS.widgets:
            assert isinstance(w, SliderWidgetDef)

    def test_checkbox_for_automargin(self) -> None:
        w = LAYOUT_MARGINS.find("automargin")
        assert w is not None
        assert isinstance(w, CheckboxWidgetDef)

    def test_text_widget_for_format(self) -> None:
        w = DATA_LABELS.find("text_format")
        assert w is not None
        assert isinstance(w, TextWidgetDef)

    def test_color_widgets_for_tick_colors(self) -> None:
        for key in ("xaxis_tickfont_color", "yaxis_tickfont_color"):
            w = TYPOGRAPHY.find(key)
            assert w is not None
            assert isinstance(w, ColorWidgetDef)
