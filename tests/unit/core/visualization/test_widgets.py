"""
Tests for the declarative widget system.

Tests:
  - WidgetDef and subclass construction
  - WidgetSection keys/defaults/find

  - Standard section definitions
"""

import pytest

from src.web.rendering.widgets.widget_def import (
    LAYOUT_MARGINS,
    STANDARD_SECTIONS,
    TYPOGRAPHY,
    CheckboxWidgetDef,
    ColorWidgetDef,
    NumberWidgetDef,
    SelectWidgetDef,
    SliderWidgetDef,
    TextWidgetDef,
    WidgetSection,
)


class TestWidgetDefConstruction:
    """Test widget definition dataclass construction."""

    def test_number_widget(self) -> None:
        w = NumberWidgetDef(key="size", label="Size", default=10, min_value=1, max_value=100)
        assert w.key == "size"
        assert w.default == 10
        assert w.min_value == 1
        assert w.as_int is True

    def test_slider_widget(self) -> None:
        w = SliderWidgetDef(key="w", label="Width", default=700, min_value=200, max_value=2000)
        assert w.min_value == 200
        assert w.max_value == 2000

    def test_select_widget(self) -> None:
        w = SelectWidgetDef(key="o", label="Orient", default="v", options=("v", "h"))
        assert w.options == ("v", "h")
        assert w.default == "v"

    def test_checkbox_widget(self) -> None:
        w = CheckboxWidgetDef(key="t", label="Toggle", default=True)
        assert w.default is True

    def test_color_widget(self) -> None:
        w = ColorWidgetDef(key="c", label="Color", default="#FF0000")
        assert w.default == "#FF0000"

    def test_text_widget(self) -> None:
        w = TextWidgetDef(key="n", label="Name", default="foo", max_chars=50)
        assert w.max_chars == 50

    def test_widget_frozen(self) -> None:
        """WidgetDef instances should be immutable (frozen)."""
        w = NumberWidgetDef(key="x", label="X", default=5)
        with pytest.raises(AttributeError):
            w.key = "changed"  # type: ignore[misc]

    def test_spec_path(self) -> None:
        w = NumberWidgetDef(
            key="margin_l",
            label="Left",
            default=100,
            spec_path="dimensions.margins.left",
        )
        assert w.spec_path == "dimensions.margins.left"


class TestWidgetSection:
    """Test widget section grouping."""

    def test_keys(self) -> None:
        section = WidgetSection(
            id="test",
            label="Test",
            widgets=(
                NumberWidgetDef(key="a", label="A", default=1),
                NumberWidgetDef(key="b", label="B", default=2),
            ),
        )
        assert section.keys() == ["a", "b"]

    def test_defaults(self) -> None:
        section = WidgetSection(
            id="test",
            label="Test",
            widgets=(
                NumberWidgetDef(key="a", label="A", default=10),
                CheckboxWidgetDef(key="b", label="B", default=True),
            ),
        )
        assert section.defaults() == {"a": 10, "b": True}

    def test_find(self) -> None:
        w = NumberWidgetDef(key="target", label="Target", default=42)
        section = WidgetSection(id="s", label="S", widgets=(w,))
        assert section.find("target") is w
        assert section.find("missing") is None

    def test_standard_margin_section(self) -> None:
        """LAYOUT_MARGINS should have margin + automargin widgets."""
        assert len(LAYOUT_MARGINS.widgets) == 6
        keys = LAYOUT_MARGINS.keys()
        assert "margin_l" in keys
        assert "margin_r" in keys
        assert "margin_t" in keys
        assert "margin_b" in keys
        assert "margin_pad" in keys
        assert "automargin" in keys

    def test_standard_typography_section(self) -> None:
        """TYPOGRAPHY should have font size + color widgets."""
        assert len(TYPOGRAPHY.widgets) == 9
        assert "title_font_size" in TYPOGRAPHY.keys()
        assert "xaxis_tickfont_color" in TYPOGRAPHY.keys()
        assert "yaxis_title_standoff" in TYPOGRAPHY.keys()

    def test_all_standard_sections(self) -> None:
        """All standard sections should exist and have widgets."""
        assert len(STANDARD_SECTIONS) == 9
        for section in STANDARD_SECTIONS:
            assert len(section.widgets) > 0
            assert section.id != ""
            assert section.label != ""

    def test_all_spec_paths_unique(self) -> None:
        """No two widgets across standard sections should share a spec_path."""
        paths = []
        for section in STANDARD_SECTIONS:
            for w in section.widgets:
                if w.spec_path:
                    assert w.spec_path not in paths, f"Duplicate spec_path: {w.spec_path}"
                    paths.append(w.spec_path)
