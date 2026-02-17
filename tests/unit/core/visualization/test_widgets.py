"""
Tests for the declarative widget system.

Tests:
  - WidgetDef and subclass construction
  - WidgetSection keys/defaults/find
  - ConfigBridge spec_to_config and config_to_spec
  - _get_nested / _set_nested helpers
  - Standard section definitions
"""

from typing import Any, Dict

import pytest

from src.core.visualization.figure_spec import DimensionsSpec, FigureSpec, MarginsSpec
from src.core.visualization.legend_spec import LegendSpec
from src.core.visualization.typography_spec import TypographySpec
from src.core.visualization.widgets.config_bridge import (
    ConfigBridge,
    _get_nested,
    _set_nested,
)
from src.core.visualization.widgets.widget_def import (
    LAYOUT_MARGINS,
    LEGEND,
    LEGEND_APPEARANCE,
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


class TestGetNested:
    """Test the _get_nested helper."""

    def test_simple_attr(self) -> None:
        spec = FigureSpec(title="Hello")
        assert _get_nested(spec, "title") == "Hello"

    def test_nested_attr(self) -> None:
        spec = FigureSpec(dimensions=DimensionsSpec(width=3.5))
        assert _get_nested(spec, "dimensions.width") == 3.5

    def test_deep_nested(self) -> None:
        spec = FigureSpec(dimensions=DimensionsSpec(margins=MarginsSpec(left=42.0)))
        assert _get_nested(spec, "dimensions.margins.left") == 42.0

    def test_list_index(self) -> None:
        spec = FigureSpec(
            legends=[
                LegendSpec(role="primary", font_size=12),
            ]
        )
        assert _get_nested(spec, "legends.0.font_size") == 12

    def test_missing_attr(self) -> None:
        spec = FigureSpec()
        assert _get_nested(spec, "nonexistent.path") is None

    def test_none_root(self) -> None:
        assert _get_nested(None, "anything") is None

    def test_list_out_of_bounds(self) -> None:
        spec = FigureSpec(legends=[])
        assert _get_nested(spec, "legends.5.font_size") is None


class TestSetNested:
    """Test the _set_nested helper."""

    def test_simple_attr(self) -> None:
        spec = FigureSpec()
        _set_nested(spec, "title", "New Title")
        assert spec.title == "New Title"

    def test_nested_attr(self) -> None:
        spec = FigureSpec()
        _set_nested(spec, "dimensions.width", 10.0)
        assert spec.dimensions.width == 10.0

    def test_deep_nested(self) -> None:
        spec = FigureSpec()
        _set_nested(spec, "dimensions.margins.left", 99.0)
        assert spec.dimensions.margins.left == 99.0

    def test_list_index(self) -> None:
        spec = FigureSpec(
            legends=[
                LegendSpec(role="primary", font_size=8),
            ]
        )
        _set_nested(spec, "legends.0.font_size", 16)
        assert spec.legends[0].font_size == 16

    def test_missing_intermediate(self) -> None:
        """Should not crash if an intermediate is None/missing."""
        spec = FigureSpec()
        # axes.y2 is None by default — should silently no-op
        _set_nested(spec, "axes.y2.label", "test")
        # No crash


class TestConfigBridge:
    """Test bidirectional config ↔ FigureSpec mapping."""

    def _make_bridge(self) -> ConfigBridge:
        """Create a bridge with margins + typography + legend appearance."""
        return ConfigBridge([LAYOUT_MARGINS, TYPOGRAPHY, LEGEND_APPEARANCE])

    def test_mapped_keys(self) -> None:
        bridge = self._make_bridge()
        keys = bridge.mapped_keys
        assert "margin_l" in keys
        assert "title_font_size" in keys

    def test_spec_to_config(self) -> None:
        """Extract flat config from FigureSpec."""
        spec = FigureSpec(
            dimensions=DimensionsSpec(
                margins=MarginsSpec(left=150.0, right=50.0, top=30.0, bottom=90.0)
            ),
            typography=TypographySpec(font_size_title=18, font_size_xlabel=14),
        )
        bridge = self._make_bridge()
        config = bridge.spec_to_config(spec)

        assert config["margin_l"] == 150.0
        assert config["margin_r"] == 50.0
        assert config["title_font_size"] == 18
        assert config["xaxis_title_font_size"] == 14

    def test_config_to_spec(self) -> None:
        """Build FigureSpec from flat config."""
        config: Dict[str, Any] = {
            "margin_l": 200,
            "margin_r": 60,
            "title_font_size": 20,
        }
        bridge = self._make_bridge()
        spec = bridge.config_to_spec(config)

        assert spec.dimensions.margins.left == 200
        assert spec.dimensions.margins.right == 60
        assert spec.typography.font_size_title == 20

    def test_round_trip(self) -> None:
        """Spec → config → spec should preserve mapped values."""
        original = FigureSpec(
            dimensions=DimensionsSpec(
                margins=MarginsSpec(left=120.0, right=40.0, top=35.0, bottom=85.0, pad=5.0)
            ),
            typography=TypographySpec(
                font_size_title=16,
                font_size_xlabel=11,
                font_size_ylabel=11,
                font_size_ticks=7,
                font_size_yticks=7,
                font_size_legend=9,
                font_size_annotations=6,
            ),
        )
        bridge = self._make_bridge()
        config = bridge.spec_to_config(original)
        reconstructed = bridge.config_to_spec(config)

        assert reconstructed.dimensions.margins.left == original.dimensions.margins.left
        assert reconstructed.dimensions.margins.right == original.dimensions.margins.right
        assert reconstructed.typography.font_size_title == original.typography.font_size_title
        assert reconstructed.typography.font_size_xlabel == original.typography.font_size_xlabel
        assert reconstructed.typography.font_size_ticks == original.typography.font_size_ticks

    def test_base_spec_preserved(self) -> None:
        """config_to_spec with base_spec should not modify the base."""
        base = FigureSpec(title="Original")
        bridge = self._make_bridge()
        result = bridge.config_to_spec({"margin_l": 999}, base_spec=base)

        assert result.dimensions.margins.left == 999
        assert result.title == "Original"
        # Base should not be modified
        assert base.dimensions.margins.left != 999

    def test_unmapped_keys_ignored(self) -> None:
        """Config keys without spec_path should pass through without error."""
        config: Dict[str, Any] = {
            "margin_l": 100,
            "custom_thing": "foo",
        }
        bridge = self._make_bridge()
        spec = bridge.config_to_spec(config)
        # Should not crash; custom_thing is silently ignored
        assert spec.dimensions.margins.left == 100

    def test_legend_bridge(self) -> None:
        """Bridge with LEGEND section should map to legends list."""
        bridge = ConfigBridge([LEGEND])
        spec = FigureSpec(
            legends=[
                LegendSpec(role="primary", font_size=12, ncol=3),
            ]
        )
        config = bridge.spec_to_config(spec)
        assert config.get("legend_ncols") == 3
        assert config.get("legend_font_size") == 12
