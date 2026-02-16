"""
Tests for ConfigSpecBuilder — config dict → FigureSpec mapping.

Validates that flat UI config dicts produce correctly-typed FigureSpec
instances with the expected field values.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from src.core.visualization.connectors.builders import ConfigSpecBuilder
from src.core.visualization.figure_spec import FigureSpec
from src.core.visualization.resolvers import resolve_spec


def _sample_config(**overrides: Any) -> Dict[str, Any]:
    """Build a minimal config dict with optional overrides."""
    base: Dict[str, Any] = {
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
        assert isinstance(spec, FigureSpec)

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
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_x=0.5, legend_y=0.9)
        )
        leg = spec.legends[0]
        assert leg.position_x == 0.5
        assert leg.position_y == 0.9

    def test_legend_orientation_horizontal(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_orientation="h")
        )
        assert spec.legends[0].orientation == "horizontal"

    def test_legend_orientation_vertical(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_orientation="v")
        )
        assert spec.legends[0].orientation == "vertical"

    def test_legend_border(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_border_width=2, legend_border_color="#FF0000")
        )
        leg = spec.legends[0]
        assert leg.border_width == 2
        assert leg.border_color == "#FF0000"

    def test_legend_bgcolor(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_bgcolor="#FAFAFA")
        )
        assert spec.legends[0].bgcolor == "#FAFAFA"


class TestConfigSpecBarSpecific:
    """Bar-chart specific settings."""

    def test_bargap_for_bar_type(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(bargap=0.3), plot_type="bar"
        )
        assert spec.dimensions.bargap == 0.3

    def test_bargroupgap_for_grouped(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(bargroupgap=0.1), plot_type="grouped_bar"
        )
        assert spec.dimensions.bargroupgap == 0.1

    def test_no_bargap_for_line(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(bargap=0.3), plot_type="line"
        )
        assert spec.dimensions.bargap == 0.0


class TestConfigSpecMultiLegend:
    """Multi-column legend configuration."""

    def test_no_secondary_legends_when_ncols_0(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_ncols=0)
        )
        assert len(spec.legends) == 1

    def test_secondary_legends_when_ncols_3(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_ncols=3)
        )
        assert len(spec.legends) == 3
        assert spec.legends[1].role == "secondary"
        assert spec.legends[2].role == "secondary"

    def test_secondary_legend_inherits_font(self) -> None:
        spec = ConfigSpecBuilder.from_config(
            _sample_config(legend_ncols=2, legend_font_size=15)
        )
        assert spec.legends[1].font_size == 15


class TestConfigSpecResolve:
    """Test that config → spec → resolve round-trips cleanly."""

    def test_resolve_does_not_raise(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config())
        resolved = resolve_spec(spec)
        assert isinstance(resolved, FigureSpec)

    def test_resolved_inherits_all_defaults(self) -> None:
        spec = ConfigSpecBuilder.from_config(_sample_config())
        resolved = resolve_spec(spec)
        # All sentinel values should be resolved
        assert resolved.typography.font_size_title == 18
        assert resolved.dimensions.width == 800.0


class TestStyleApplicatorLastSpec:
    """Verify that StyleApplicator stores the last_spec."""

    def test_last_spec_populated_after_apply(self) -> None:
        import plotly.graph_objects as go

        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        applicator = StyleApplicator("bar")
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        applicator.apply_styles(fig, _sample_config())

        assert applicator.last_spec is not None
        assert isinstance(applicator.last_spec, FigureSpec)
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
