"""
Tests for PlotlyTemplateFactory — Step 12.

Covers:
  - create_base_template: colorway, font, axis defaults
  - create_preset_template: font sizes, dimensions, traces
  - register_all_templates: ring5_base + per-preset registration
  - Template composition: plotly_white+ring5_XXX produces valid figure
"""

import plotly.graph_objects as go
import plotly.io as pio

from src.core.visualization.connectors.plotly_templates import (
    WONG_PALETTE,
    create_base_template,
    create_preset_template,
    register_all_templates,
)

# ────────────────────────────────────────────────────────────────────
# Base template
# ────────────────────────────────────────────────────────────────────


class TestBaseTemplate:
    """Test create_base_template."""

    def test_colorway(self) -> None:
        tpl = create_base_template()
        assert list(tpl.layout.colorway) == WONG_PALETTE

    def test_font_defaults(self) -> None:
        tpl = create_base_template()
        assert tpl.layout.font.family == "Arial, sans-serif"
        assert tpl.layout.font.size == 10
        assert tpl.layout.font.color == "#333333"

    def test_paper_bgcolor(self) -> None:
        tpl = create_base_template()
        assert tpl.layout.paper_bgcolor == "white"
        assert tpl.layout.plot_bgcolor == "white"

    def test_xaxis_defaults(self) -> None:
        tpl = create_base_template()
        xa = tpl.layout.xaxis
        assert xa.showgrid is True
        assert xa.gridcolor == "#E5E5E5"
        assert xa.showline is True
        assert xa.linecolor == "#333333"
        assert xa.ticks == "outside"
        assert xa.zeroline is False

    def test_yaxis_defaults(self) -> None:
        tpl = create_base_template()
        ya = tpl.layout.yaxis
        assert ya.showgrid is True
        assert ya.showline is True
        assert ya.zeroline is False

    def test_legend_border(self) -> None:
        tpl = create_base_template()
        leg = tpl.layout.legend
        assert leg.bordercolor == "#CCCCCC"
        assert leg.borderwidth == 1

    def test_margins(self) -> None:
        tpl = create_base_template()
        m = tpl.layout.margin
        assert m.l == 60
        assert m.r == 20
        assert m.t == 40
        assert m.b == 60

    def test_is_valid_template_type(self) -> None:
        tpl = create_base_template()
        assert isinstance(tpl, go.layout.Template)


# ────────────────────────────────────────────────────────────────────
# Preset template
# ────────────────────────────────────────────────────────────────────


class TestPresetTemplate:
    """Test create_preset_template."""

    _ISCA_LIKE: dict = {  # type: ignore[type-arg]
        "font_family": "serif",
        "font_size_base": 8,
        "font_size_title": 9,
        "font_size_ticks": 7,
        "font_size_labels": 8,
        "line_width": 0.8,
        "marker_size": 3.0,
        "width_inches": 3.5,
        "height_inches": 1.97,
        "dpi": 300,
    }

    def test_font_family_serif(self) -> None:
        tpl = create_preset_template("isca", self._ISCA_LIKE)
        assert tpl.layout.font.family == "serif"

    def test_font_family_sans_serif(self) -> None:
        info = {**self._ISCA_LIKE, "font_family": "sans-serif"}
        tpl = create_preset_template("custom", info)
        assert tpl.layout.font.family == "Arial, sans-serif"

    def test_font_size_base(self) -> None:
        tpl = create_preset_template("isca", self._ISCA_LIKE)
        assert tpl.layout.font.size == 8

    def test_title_font_size(self) -> None:
        tpl = create_preset_template("isca", self._ISCA_LIKE)
        assert tpl.layout.title.font.size == 9

    def test_tick_font_size(self) -> None:
        tpl = create_preset_template("isca", self._ISCA_LIKE)
        assert tpl.layout.xaxis.tickfont.size == 7
        assert tpl.layout.yaxis.tickfont.size == 7

    def test_axis_title_font_size(self) -> None:
        tpl = create_preset_template("isca", self._ISCA_LIKE)
        assert tpl.layout.xaxis.title.font.size == 8
        assert tpl.layout.yaxis.title.font.size == 8

    def test_dimensions_in_pixels(self) -> None:
        tpl = create_preset_template("isca", self._ISCA_LIKE)
        # 3.5 * 300 = 1050, 1.97 * 300 = 591
        assert tpl.layout.width == 1050
        assert tpl.layout.height == 591

    def test_colorway(self) -> None:
        tpl = create_preset_template("isca", self._ISCA_LIKE)
        assert list(tpl.layout.colorway) == WONG_PALETTE

    def test_scatter_trace_defaults(self) -> None:
        tpl = create_preset_template("isca", self._ISCA_LIKE)
        scatter = tpl.data.scatter[0]
        assert scatter.line.width == 0.8
        assert scatter.marker.size == 3.0

    def test_defaults_when_keys_missing(self) -> None:
        """Preset with minimal keys should still produce valid template."""
        tpl = create_preset_template("minimal", {})
        assert tpl.layout.font.size == 8  # default
        assert tpl.layout.font.family == "serif"  # default


# ────────────────────────────────────────────────────────────────────
# Registration
# ────────────────────────────────────────────────────────────────────


class TestTemplateRegistration:
    """Test register_all_templates."""

    def test_base_registered(self) -> None:
        register_all_templates({})
        assert "ring5_base" in pio.templates

    def test_preset_registered(self) -> None:
        presets = {
            "isca": {"font_size_base": 8, "font_family": "serif"},
            "micro": {"font_size_base": 9, "font_family": "sans-serif"},
        }
        register_all_templates(presets)
        assert "ring5_isca" in pio.templates
        assert "ring5_micro" in pio.templates

    def test_registered_template_is_valid(self) -> None:
        presets = {"test_reg": {"font_size_base": 10}}
        register_all_templates(presets)
        tpl = pio.templates["ring5_test_reg"]
        assert isinstance(tpl, go.layout.Template)
        assert tpl.layout.font.size == 10


# ────────────────────────────────────────────────────────────────────
# Template composition
# ────────────────────────────────────────────────────────────────────


class TestTemplateComposition:
    """Test composing ring5 templates with Plotly built-ins."""

    def test_compose_with_plotly_white(self) -> None:
        register_all_templates({"comp": {"font_size_base": 12, "font_family": "serif"}})
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        fig.update_layout(template="plotly_white+ring5_comp")
        # The composed template should apply without error
        assert fig.layout.template is not None

    def test_base_template_standalone(self) -> None:
        register_all_templates({})
        fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4])])
        fig.update_layout(template="ring5_base")
        assert fig.layout.template is not None
