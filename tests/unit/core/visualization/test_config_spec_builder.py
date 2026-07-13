"""
Tests for ConfigSpecBuilder — config dict → FigureConfig mapping.

Validates that flat UI config dicts produce correctly-typed FigureConfig
instances with the expected field values.
"""

from __future__ import annotations

from typing import Any

from src.core.models.visualization.figure_config import FigureConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.config_builder import ConfigSpecBuilder


def _sample_config(**overrides: Any) -> dict[str, Any]:
    """Build a minimal config dict with optional overrides."""
    base: dict[str, Any] = {
        "width": 800,
        "height": 500,
        "margin_t": 80,
        "margin_b": 120,
        "margin_l": 100,
        "margin_r": 100,
        "margin_pad": 0,
        "title": "Test Plot",
        "title_font_size": 18,
        "xlabel": "X Axis",
        "ylabel": "Y Axis",
        "xaxis_title_font_size": 14,
        "yaxis_title_font_size": 14,
        "xaxis_tickangle": -45,
        "xaxis_tickfont_size": 12,
        "yaxis_tickfont_size": 12,
        "legend_orientation": "v",
        "legend_x": 1.02,
        "legend_y": 1.0,
        "legend_font_size": 12,
        "legend_font_color": "#444",
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
    }
    base.update(overrides)
    return base


class TestConfigSpecBuilderBasic:
    """Core construction tests."""

    def test_returns_figure_spec(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config())
        assert isinstance(spec, FigureConfig)

    def test_dimensions_passthrough(self) -> None:
        """dpi=1 means width/height are in pixels (passthrough)."""
        spec = ConfigSpecBuilder.from_config(_sample_config(width=900, height=600))
        assert spec.dimensions.width == 900.0
        assert spec.dimensions.height == 600.0
        assert spec.dimensions.dpi == 1

    def test_margins(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(margin_t=50, margin_b=100, margin_l=80, margin_r=60, margin_pad=5)
        )
        m = spec.dimensions.margins
        assert m.top == 50.0
        assert m.bottom == 100.0
        assert m.left == 80.0
        assert m.right == 60.0
        assert m.pad == 5.0

    def test_title(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(title="My Title"))
        assert spec.title == "My Title"

    def test_title_undefined_stripped(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(title="undefined"))
        assert spec.title == ""

    def test_backgrounds(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(plot_bgcolor="#f0f0f0", paper_bgcolor="#e0e0e0")
        )
        assert spec.plot_bgcolor == "#f0f0f0"
        assert spec.paper_bgcolor == "#e0e0e0"


class TestConfigSpecAxes:
    """Axis configuration mapping."""

    def test_x_axis_label(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(xlabel="Benchmark"))
        assert spec.axes.x.label == "Benchmark"

    def test_y_axis_label(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(ylabel="IPC"))
        assert spec.axes.y.label == "IPC"

    def test_xlabel_undefined_stripped(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(xlabel="undefined"))
        assert spec.axes.x.label == ""

    def test_x_tick_angle(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(xaxis_tickangle=90))
        assert spec.axes.x.tick_angle == 90.0

    def test_y_dtick(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(yaxis_dtick=0.5))
        assert spec.axes.y.dtick == 0.5

    def test_xaxis_category_order(self) -> None:
        order = ["A", "B", "C"]
        spec = ConfigSpecBuilder.from_config(_sample_config(xaxis_order=order))
        assert spec.axes.x.category_order == order


class TestConfigSpecTypography:
    """Typography mapping."""

    def test_title_font_size(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(title_font_size=24))
        assert spec.typography.font_size_title == 24

    def test_xlabel_font_size(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(xaxis_title_font_size=16))
        assert spec.typography.font_size_xlabel == 16

    def test_legend_font_size(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(legend_font_size=10))
        assert spec.typography.font_size_legend == 10


class TestConfigSpecLegend:
    """Legend configuration mapping."""

    def test_primary_legend_position(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(legend_x=0.5, legend_y=0.9))
        leg = spec.legends[0]
        assert leg.position_x == 0.5
        assert leg.position_y == 0.9

    def test_legend_orientation_always_default(self) -> None:
        """Orientation removed from UI — always model default ('vertical')."""
        spec = ConfigSpecBuilder.from_config(_sample_config(legend_orientation="h"))
        assert spec.legends[0].orientation == "vertical"

    def test_legend_orientation_vertical(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(legend_orientation="v"))
        assert spec.legends[0].orientation == "vertical"

    def test_legend_border(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_border_width=2, legend_border_color="#FF0000")
        )
        leg = spec.legends[0]
        assert leg.border_width == 2
        assert leg.border_color == "#FF0000"

    def test_legend_bgcolor(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(legend_bgcolor="#FAFAFA"))
        assert spec.legends[0].bgcolor == "#FAFAFA"


class TestConfigSpecBarSpecific:
    """Bar-chart specific settings."""

    def test_bargap_for_bar_type(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(bargap=0.3), plot_type="bar")
        assert spec.dimensions.bargap == 0.3

    def test_bargroupgap_for_grouped(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(bargroupgap=0.1), plot_type="grouped_bar"
        )
        assert spec.dimensions.bargroupgap == 0.1

    def test_no_bargap_for_line(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(bargap=0.3), plot_type="line")
        assert spec.dimensions.bargap == 0.0


class TestConfigSpecMultiLegend:
    """Multi-legend configuration via legend2_/legend3_ prefixes."""

    def test_no_secondary_legends_by_default(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config())
        assert len(spec.legends) == 1

    def test_secondary_legend_from_legend2_keys(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(legend2_font_size=12, legend2_x=0.5))
        assert len(spec.legends) == 2
        assert spec.legends[1].role == "secondary"

    def test_secondary_legend_inherits_font(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(legend2_font_size=15, legend2_x=0.0))
        assert spec.legends[1].font_size == 15


class TestConfigSpecResolve:
    """Test that config → spec → resolve round-trips cleanly."""

    def test_resolve_does_not_raise(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config())
        resolved = resolve_config(spec)
        assert isinstance(resolved, FigureConfig)

    def test_resolved_inherits_all_defaults(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config())
        resolved = resolve_config(spec)
        # All sentinel values should be resolved
        assert resolved.typography.font_size_title == 18
        assert resolved.dimensions.width == 800.0


class TestApplicatorLastSpec:
    """Verify that apply_styles stores the last FigureConfig built."""

    def test_last_spec_populated_after_apply(self) -> None:
        import plotly.graph_objects as go

        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        applicator = StyleApplicator("bar")
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        applicator.apply_styles(fig, _sample_config())

        assert applicator.last_spec is not None
        assert isinstance(applicator.last_spec, FigureConfig)
        assert applicator.last_spec.title == "Test Plot"

    def test_last_spec_updated_on_each_call(self) -> None:
        import plotly.graph_objects as go

        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        applicator = StyleApplicator("line")
        fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4])])

        applicator.apply_styles(fig, _sample_config(title="First"))
        assert applicator.last_spec is not None
        assert applicator.last_spec.title == "First"

        applicator.apply_styles(fig, _sample_config(title="Second"))
        assert applicator.last_spec.title == "Second"

    def test_last_spec_is_none_initially(self) -> None:
        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        applicator = StyleApplicator("bar")
        assert applicator.last_spec is None


# Additional configuration mappings


class TestConfigSpecDataLabels:
    """Test data label config → DataLabelConfig mapping."""

    def test_no_data_labels_when_show_values_false(self) -> None:
        config = _sample_config(show_values=False)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is None

    def test_no_data_labels_when_key_missing(self) -> None:
        config = _sample_config()
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is None

    def test_data_labels_enabled(self) -> None:
        config = _sample_config(show_values=True)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.enabled is True

    def test_data_labels_color_mode(self) -> None:
        config = _sample_config(show_values=True, text_color_mode="contrast")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.color_mode == "contrast"

    def test_data_labels_custom_color(self) -> None:
        config = _sample_config(show_values=True, text_color="#FF0000")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.custom_color == "#FF0000"

    def test_data_labels_font_size(self) -> None:
        config = _sample_config(show_values=True, text_font_size=14)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.font_size == 14

    def test_data_labels_rotation(self) -> None:
        config = _sample_config(show_values=True, text_rotation=45)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.rotation == 45

    def test_data_labels_position(self) -> None:
        config = _sample_config(show_values=True, text_position="inside")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.position == "inside"

    def test_data_labels_format(self) -> None:
        config = _sample_config(show_values=True, text_format=".1%")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.format_string == ".1%"

    def test_data_labels_invalid_font_size_fallback(self) -> None:
        config = _sample_config(show_values=True, text_font_size="invalid")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.font_size == 12

    def test_data_labels_invalid_rotation_fallback(self) -> None:
        config = _sample_config(show_values=True, text_rotation="bad")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.data_labels is not None
        assert spec.data_labels.rotation == 0


class TestConfigSpecReferenceLines:
    """Test reference line config → ReferenceLineConfig mapping."""

    def test_no_reference_lines_when_disabled(self) -> None:
        config = _sample_config(reference_line_enabled=False)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.reference_lines == []

    def test_no_reference_lines_when_key_missing(self) -> None:
        config = _sample_config()
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.reference_lines == []

    def test_reference_line_enabled(self) -> None:
        config = _sample_config(
            reference_line_enabled=True,
            reference_line_y=1.0,
            reference_line_color="blue",
            reference_line_width=2.0,
            reference_line_style="solid",
        )
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert len(spec.reference_lines) == 1
        rl = spec.reference_lines[0]
        assert rl.enabled is True
        assert rl.axis == "y"
        assert rl.value == 1.0
        assert rl.color == "blue"
        assert rl.width == 2.0
        assert rl.style == "solid"

    def test_reference_line_defaults(self) -> None:
        config = _sample_config(reference_line_enabled=True)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        rl = spec.reference_lines[0]
        assert rl.value == 0.0
        assert rl.color == "red"
        assert rl.width == 1.5
        assert rl.style == "dash"


class TestConfigSpecSeriesStyles:
    """Test series styling config → SeriesStyleConfig mapping."""

    def test_no_series_styles_when_keys_missing(self) -> None:
        config = _sample_config()
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.series_styles == []

    def test_bar_border_width(self) -> None:
        config = _sample_config(bar_border_width=1.5)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert len(spec.series_styles) == 1
        assert spec.series_styles[0].bar_border_width == 1.5

    def test_marker_size(self) -> None:
        config = _sample_config(marker_size=10)
        spec = ConfigSpecBuilder.from_config(config, "line")
        assert len(spec.series_styles) == 1
        assert spec.series_styles[0].marker_size == 10

    def test_line_width(self) -> None:
        config = _sample_config(line_width=3.0)
        spec = ConfigSpecBuilder.from_config(config, "line")
        assert len(spec.series_styles) == 1
        assert spec.series_styles[0].line_width == 3.0


class TestConfigSpecColorPalette:
    """Test color palette resolution."""

    def test_none_palette_fallback_to_wong(self) -> None:
        config = _sample_config()
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert len(spec.color_palette) == 8
        assert spec.color_palette[0] == "#000000"

    def test_plotly_palette_name(self) -> None:
        config = _sample_config(color_palette="Plotly")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert len(spec.color_palette) >= 8
        assert spec.color_palette[0].startswith("#")

    def test_unknown_palette_fallback(self) -> None:
        config = _sample_config(color_palette="NonExistentXYZ")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.color_palette[0] == "#000000"


class TestConfigSpecScalarFlags:
    """Test scalar feature flags."""

    def test_show_error_bars_default(self) -> None:
        config = _sample_config()
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.show_error_bars is False

    def test_show_error_bars_enabled(self) -> None:
        config = _sample_config(show_error_bars=True)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.show_error_bars is True

    def test_enable_stripes_default(self) -> None:
        config = _sample_config()
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.enable_stripes is False

    def test_enable_stripes_enabled(self) -> None:
        config = _sample_config(enable_stripes=True)
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.enable_stripes is True

    def test_hovermode_default(self) -> None:
        config = _sample_config()
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.hovermode == "x unified"

    def test_hovermode_custom(self) -> None:
        config = _sample_config(hovermode="closest")
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        assert spec.hovermode == "closest"


class TestGlobalSeriesStyle:
    """The global series style must carry ONLY explicitly-set values.

    Regression: bar_border_width used to force marker_size=6 / line_width=2.0
    onto the single global style, which the matplotlib per-trace styling then
    stamped on every trace — clobbering a dual-axis line's own width and
    blacking the bars. Unset knobs must stay 0 (treated as "skip").
    """

    def test_bar_border_width_does_not_force_marker_or_line(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(bar_border_width=0.2), "grouped_stacked_bar"
        )
        assert len(spec.series_styles) == 1
        style = spec.series_styles[0]
        assert style.bar_border_width == 0.2
        assert style.marker_size == 0  # not 6 — unset, so the styling step skips it
        assert style.line_width == 0.0  # not 2.0 — unset

    def test_bar_border_color_passthrough(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(bar_border_width=0.2, bar_border_color="white"),
            "grouped_stacked_bar",
        )
        assert spec.series_styles[0].bar_border_color == "white"

    def test_explicit_marker_and_line_are_kept(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(marker_size=9, line_width=1.4), "line")
        style = spec.series_styles[0]
        assert style.marker_size == 9
        assert style.line_width == 1.4

    def test_no_series_keys_means_no_global_style(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config(), "grouped_bar")
        assert spec.series_styles == []
