"""
Tests for connectors — Plotly connector, Matplotlib connector, and builders.

Covers:
  - FigureSpecToPlotly: apply spec to a Plotly figure
  - FigureSpecToMatplotlib: apply spec to matplotlib axes
  - PlotlyFigureSpecBuilder: extract spec from Plotly figure
"""

from typing import Any, cast

import plotly.graph_objects as go

from src.core.models.visualization.annotation_config import ReferenceLineConfig
from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
    MarginsConfig,
)
from src.core.models.visualization.legend_config import ColorbarConfig, LegendConfig
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.typography_config import TypographyConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.plotly_connector import FigureSpecToPlotly


class TestFigureSpecToPlotly:
    """Test Plotly connector."""

    def _make_simple_fig(self) -> go.Figure:
        """Create a simple bar chart for testing."""
        return go.Figure(data=[go.Bar(x=["A", "B", "C"], y=[1, 2, 3], name="Test")])

    def test_apply_dimensions(self) -> None:
        """Dimensions should set width/height/margins on figure."""
        spec = FigureConfig(
            dimensions=DimensionConfig(
                width=7.0,
                height=4.0,
                dpi=100,  # 7*100=700px, 4*100=400px
                margins=MarginsConfig(top=10, bottom=20, left=30, right=40),
            )
        )
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        layout = cast(Any, fig.layout)
        assert layout.width == 700
        assert layout.height == 400
        assert layout.margin.t == 10
        assert layout.margin.b == 20
        assert layout.margin.l == 30
        assert layout.margin.r == 40

    def test_apply_backgrounds(self) -> None:
        """Background colors should be applied."""
        spec = FigureConfig(
            paper_bgcolor="#F0F0F0",
            plot_bgcolor="#FFFFFF",
        )
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        layout = cast(Any, fig.layout)
        assert layout.paper_bgcolor == "#F0F0F0"
        assert layout.plot_bgcolor == "#FFFFFF"

    def test_apply_title(self) -> None:
        """Title should be applied."""
        spec = FigureConfig(
            title="My Plot",
            typography=TypographyConfig(font_size_title=16),
        )
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        layout = cast(Any, fig.layout)
        assert layout.title.text == "My Plot"
        assert layout.title.font.size == 16

    def test_apply_xaxis(self) -> None:
        """X-axis configuration should be applied."""
        spec = FigureConfig(
            axes=AxesConfig(
                x=AxisConfig(
                    label="Benchmark",
                    tick_angle=45.0,
                    show_grid=True,
                    grid_color="#ccc",
                )
            ),
            typography=TypographyConfig(font_size_xlabel=12, font_size_ticks=8),
        )
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        layout = cast(Any, fig.layout)
        assert layout.xaxis.title.text == "Benchmark"
        assert layout.xaxis.title.font.size == 12
        assert layout.xaxis.tickangle == 45.0
        assert layout.xaxis.tickfont.size == 8

    def test_apply_yaxis(self) -> None:
        """Y-axis configuration should be applied."""
        spec = FigureConfig(
            axes=AxesConfig(y=AxisConfig(label="Speedup", dtick=0.5)),
            typography=TypographyConfig(
                font_size_ylabel=11,
                font_size_yticks=7,
            ),
        )
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        layout = cast(Any, fig.layout)
        assert layout.yaxis.title.text == "Speedup"
        assert layout.yaxis.title.font.size == 11
        assert layout.yaxis.dtick == 0.5

    def test_apply_legend(self) -> None:
        """Legend configuration should be applied."""
        spec = FigureConfig(
            legends=[
                LegendConfig(
                    role="primary",
                    font_size=10,
                    font_color="black",
                    orientation="horizontal",
                    custom_position=True,
                    position_x=0.5,
                    position_y=1.1,
                    anchor_x="center",
                    anchor_y="bottom",
                )
            ]
        )
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        layout = cast(Any, fig.layout)
        assert layout.legend.font.size == 10
        assert layout.legend.orientation == "h"
        assert layout.legend.x == 0.5
        assert layout.legend.y == 1.1
        assert layout.legend.xanchor == "center"
        assert layout.legend.yanchor == "bottom"

    def test_no_legend(self) -> None:
        """Empty legends list should not crash."""
        spec = FigureConfig(legends=[])
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)
        # Should not raise

    def test_no_title(self) -> None:
        """Empty title should not be applied."""
        spec = FigureConfig(title="")
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)
        # Should not crash, title remains whatever Plotly default is

    def test_apply_color_palette_with_heatmap_does_not_set_marker(self) -> None:
        """Palette application should not try marker updates on heatmap traces."""
        fig = go.Figure(
            data=[
                go.Heatmap(
                    x=[0, 1],
                    y=[0, 1],
                    z=cast(Any, [[1, 2], [3, 4]]),
                    name="hm",
                )
            ]
        )
        spec = FigureConfig(color_palette=["#111111", "#222222"])
        resolved = resolve_config(spec)

        FigureSpecToPlotly.apply(resolved, fig)

        assert cast(Any, fig.data[0]).type == "heatmap"
        assert fig.layout.colorway is not None

    def test_trace_overrides_with_heatmap_color_does_not_set_marker(self) -> None:
        """Trace override color should not try marker updates on heatmap traces."""
        fig = go.Figure(
            data=[
                go.Heatmap(
                    x=[0, 1],
                    y=[0, 1],
                    z=cast(Any, [[1, 2], [3, 4]]),
                    name="hm",
                )
            ]
        )
        spec = FigureConfig(
            trace_overrides={
                "hm": SeriesStyleConfig(
                    color="#ff0000",
                    symbol="diamond",
                    marker_size=12,
                )
            }
        )
        resolved = resolve_config(spec)

        FigureSpecToPlotly.apply(resolved, fig)

        assert cast(Any, fig.data[0]).type == "heatmap"


class TestPlotlyConnectorColorPalette:
    """Test _apply_color_palette."""

    def test_color_palette_set(self) -> None:
        spec = FigureConfig(color_palette=["#AA0000", "#00BB00"])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_color_palette(spec, fig)
        assert cast(Any, fig.layout).colorway == ("#AA0000", "#00BB00")

    def test_empty_palette_no_op(self) -> None:
        spec = FigureConfig(color_palette=[])
        fig = go.Figure()
        FigureSpecToPlotly._apply_color_palette(spec, fig)
        # No colorway set when empty


class TestPlotlyConnectorHovermode:
    """Test _apply_hovermode."""

    def test_hovermode_set(self) -> None:
        spec = FigureConfig(hovermode="closest")
        fig = go.Figure()
        FigureSpecToPlotly._apply_hovermode(spec, fig)
        assert cast(Any, fig.layout).hovermode == "closest"

    def test_hovermode_x_unified(self) -> None:
        spec = FigureConfig(hovermode="x unified")
        fig = go.Figure()
        FigureSpecToPlotly._apply_hovermode(spec, fig)
        assert cast(Any, fig.layout).hovermode == "x unified"


class TestPlotlyConnectorFontFamily:
    """Test _apply_font_family."""

    def test_font_family_set(self) -> None:
        spec = FigureConfig(font_family="serif")
        fig = go.Figure()
        FigureSpecToPlotly._apply_font_family(spec, fig)
        assert cast(Any, fig.layout).font.family == "serif"

    def test_font_family_sans_serif(self) -> None:
        spec = FigureConfig(font_family="sans-serif")
        fig = go.Figure()
        FigureSpecToPlotly._apply_font_family(spec, fig)
        assert cast(Any, fig.layout).font.family == "sans-serif"


class TestPlotlyConnectorReferenceLines:
    """Test _apply_reference_lines."""

    def test_horizontal_reference_line(self) -> None:
        rl = ReferenceLineConfig(
            enabled=True, axis="y", value=1.0, color="red", width=2.0, style="dash"
        )
        spec = FigureConfig(reference_lines=[rl])
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        FigureSpecToPlotly._apply_reference_lines(spec, fig)
        # Should add a shape
        assert len(cast(Any, fig.layout).shapes) >= 1

    def test_vertical_reference_line(self) -> None:
        rl = ReferenceLineConfig(enabled=True, axis="x", value=0.5, color="blue", style="solid")
        spec = FigureConfig(reference_lines=[rl])
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        FigureSpecToPlotly._apply_reference_lines(spec, fig)
        assert len(cast(Any, fig.layout).shapes) >= 1

    def test_disabled_reference_line_skipped(self) -> None:
        rl = ReferenceLineConfig(enabled=False, axis="y", value=1.0)
        spec = FigureConfig(reference_lines=[rl])
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        FigureSpecToPlotly._apply_reference_lines(spec, fig)
        assert len(cast(Any, fig.layout).shapes) == 0


class TestPlotlyConnectorDataLabels:
    """Test _apply_data_labels."""

    def test_data_labels_applied(self) -> None:
        dl = DataLabelConfig(enabled=True, font_size=12, format_string=".1f")
        spec = FigureConfig(data_labels=dl)
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1.1, 2.2])])
        FigureSpecToPlotly._apply_data_labels(spec, fig)
        trace = cast(Any, fig.data[0])
        assert trace.texttemplate == "%{y:.1f}"
        assert trace.textfont.size == 12

    def test_data_labels_disabled_no_op(self) -> None:
        spec = FigureConfig(data_labels=None)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_data_labels(spec, fig)
        assert cast(Any, fig.data[0]).texttemplate is None

    def test_data_labels_custom_color(self) -> None:
        dl = DataLabelConfig(enabled=True, color_mode="custom", custom_color="#FF0000")
        spec = FigureConfig(data_labels=dl)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_data_labels(spec, fig)
        assert cast(Any, fig.data[0]).textfont.color == "#FF0000"

    def test_data_labels_rotation(self) -> None:
        dl = DataLabelConfig(enabled=True, rotation=45)
        spec = FigureConfig(data_labels=dl)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_data_labels(spec, fig)
        assert cast(Any, fig.data[0]).textangle == 45


class TestPlotlyConnectorSeriesStyling:
    """Test _apply_series_styling."""

    def test_bar_border_width(self) -> None:
        ss = SeriesStyleConfig(bar_border_width=1.5, bar_border_color="#000")
        spec = FigureConfig(series_styles=[ss])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_series_styling(spec, fig)
        assert cast(Any, fig.data[0]).marker.line.width == 1.5

    def test_no_styles_no_op(self) -> None:
        spec = FigureConfig(series_styles=[])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_series_styling(spec, fig)
        # No changes


class TestPlotlyConnectorAxisColors:
    """Test _apply_axis_colors."""

    def test_tick_font_color(self) -> None:
        spec = FigureConfig(
            axes=AxesConfig(
                x=AxisConfig(tick_font_color="#333"),
                y=AxisConfig(tick_font_color="#666"),
            )
        )
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_axis_colors(spec, fig)
        layout = cast(Any, fig.layout)
        assert layout.xaxis.tickfont.color == "#333"
        assert layout.yaxis.tickfont.color == "#666"

    def test_axis_line_color(self) -> None:
        spec = FigureConfig(
            axes=AxesConfig(
                x=AxisConfig(axis_line_color="black"),
                y=AxisConfig(),
            )
        )
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_axis_colors(spec, fig)
        layout = cast(Any, fig.layout)
        assert layout.xaxis.linecolor == "black"
        assert layout.xaxis.showline is True

    def test_no_colors_no_update(self) -> None:
        spec = FigureConfig()
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_axis_colors(spec, fig)
        # Default AxisConfig has empty tick_font_color and axis_line_color


class TestPlotlyConnectorLegendOrder:
    """Test legend traceorder via order field."""

    def test_reversed_order(self) -> None:
        legend = LegendConfig(role="primary", order="reversed")
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_legends(spec, fig)
        assert cast(Any, fig.layout).legend.traceorder == "reversed"

    def test_normal_order_no_traceorder(self) -> None:
        legend = LegendConfig(role="primary", order="normal")
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_legends(spec, fig)
        # traceorder not set for normal
        assert cast(Any, fig.layout).legend.traceorder is None


class TestPlotlyConnectorColorbarTitle:
    """Test legend title mapping to heatmap colorbar."""

    def test_legend_title_maps_to_colorbar(self) -> None:
        """When a legend has a title, heatmap traces get colorbar title."""
        legend = LegendConfig(
            role="primary",
            title="My Metric",
            title_font_size=16,
            title_font_color="#ff0000",
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(
            data=[
                go.Heatmap(
                    x=["A", "B"],
                    y=["m1"],
                    z=[[1.0, 2.0]],
                )
            ]
        )
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm_trace = cast(Any, fig.data[0])
        assert hm_trace.colorbar.title.text == "My Metric"
        assert hm_trace.colorbar.title.font.size == 16
        assert hm_trace.colorbar.title.font.color == "#ff0000"

    def test_no_title_no_colorbar_update(self) -> None:
        """When legend has no title, heatmap colorbar title is empty."""
        legend = LegendConfig(role="primary", title="")
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(
            data=[
                go.Heatmap(
                    x=["A"],
                    y=["m1"],
                    z=[[1.0]],
                )
            ]
        )
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm_trace = cast(Any, fig.data[0])
        # Empty title text when legend has no title
        assert hm_trace.colorbar.title.text == ""

    def test_non_heatmap_traces_unaffected(self) -> None:
        """Bar traces should not get colorbar updates from legend title."""
        legend = LegendConfig(role="primary", title="Some Title", title_font_size=14)
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="bar")])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        bar_trace = cast(Any, fig.data[0])
        # Bar traces don't have colorbar
        assert not hasattr(bar_trace, "colorbar") or bar_trace.colorbar is None


# ────────────────────────────────────────────────────────────────────
# ColorbarConfig model tests
# ────────────────────────────────────────────────────────────────────


class TestColorbarConfig:
    """Test ColorbarConfig dataclass defaults and serialization."""

    def test_defaults(self) -> None:
        """Default ColorbarConfig has expected values."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        cfg = ColorbarConfig()
        assert cfg.title_side == "top"
        assert cfg.range_mode == "auto"
        assert cfg.zmin is None
        assert cfg.zmax is None
        assert cfg.nticks == 5
        assert cfg.tick_decimals == 2
        assert cfg.shared is True

    def test_to_dict(self) -> None:
        """to_dict() includes all fields."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        cfg = ColorbarConfig(
            title_side="right",
            range_mode="manual",
            zmin=-5.0,
            zmax=15.0,
            nticks=10,
            tick_decimals=3,
            shared=False,
        )
        d = cfg.to_dict()
        assert d["title_side"] == "right"
        assert d["range_mode"] == "manual"
        assert d["zmin"] == -5.0
        assert d["zmax"] == 15.0
        assert d["nticks"] == 10
        assert d["tick_decimals"] == 3
        assert d["shared"] is False

    def test_roundtrip_serialization(self) -> None:
        """from_dict(to_dict()) produces an equivalent object."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        original = ColorbarConfig(
            title_side="bottom",
            range_mode="manual",
            zmin=1.0,
            zmax=99.0,
            nticks=8,
            tick_decimals=1,
            shared=False,
        )
        restored = ColorbarConfig.from_dict(original.to_dict())
        assert restored.title_side == original.title_side
        assert restored.range_mode == original.range_mode
        assert restored.zmin == original.zmin
        assert restored.zmax == original.zmax
        assert restored.nticks == original.nticks
        assert restored.tick_decimals == original.tick_decimals
        assert restored.shared == original.shared

    def test_from_dict_ignores_unknown_keys(self) -> None:
        """from_dict() silently ignores unknown keys."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        d = {"title_side": "left", "unknown_key": 42}
        cfg = ColorbarConfig.from_dict(d)
        assert cfg.title_side == "left"

    def test_legend_config_embeds_colorbar(self) -> None:
        """LegendConfig.colorbar is a ColorbarConfig instance."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        legend = LegendConfig()
        assert isinstance(legend.colorbar, ColorbarConfig)

    def test_legend_config_roundtrip_with_colorbar(self) -> None:
        """LegendConfig serialization includes colorbar and round-trips."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        original = LegendConfig(
            role="primary",
            colorbar=ColorbarConfig(
                range_mode="manual",
                zmin=0.0,
                zmax=100.0,
                nticks=6,
                tick_decimals=1,
                shared=False,
            ),
        )
        d = original.to_dict()
        assert "colorbar" in d
        assert d["colorbar"]["range_mode"] == "manual"

        restored = LegendConfig.from_dict(d)
        assert restored.colorbar.range_mode == "manual"
        assert restored.colorbar.zmin == 0.0
        assert restored.colorbar.zmax == 100.0
        assert restored.colorbar.nticks == 6
        assert restored.colorbar.shared is False


# ────────────────────────────────────────────────────────────────────
# compute_nice_range and compute_z_extent utility tests
# ────────────────────────────────────────────────────────────────────


class TestComputeNiceRange:
    """Tests for compute_nice_range() in _heatmap_utils."""

    def test_basic_range(self) -> None:
        """Basic range produces nice boundaries that cover the data."""
        from src.web.rendering._heatmap_utils import compute_nice_range

        nice_min, nice_max, step = compute_nice_range(0.3, 9.7, nticks=5)
        assert nice_min <= 0.3
        assert nice_max >= 9.7
        assert step > 0

    def test_equal_values(self) -> None:
        """Equal min/max expands range by 1 in each direction."""
        from src.web.rendering._heatmap_utils import compute_nice_range

        nice_min, nice_max, step = compute_nice_range(5.0, 5.0)
        assert nice_min == 4.0
        assert nice_max == 6.0
        assert step == 1.0

    def test_large_range(self) -> None:
        """Large range is handled (no overflow or unreasonable values)."""
        from src.web.rendering._heatmap_utils import compute_nice_range

        nice_min, nice_max, step = compute_nice_range(0.0, 10000.0, nticks=5)
        assert nice_min <= 0.0
        assert nice_max >= 10000.0
        assert step > 0

    def test_fractional_range(self) -> None:
        """Small fractional range produces reasonable nice boundaries."""
        from src.web.rendering._heatmap_utils import compute_nice_range

        nice_min, nice_max, step = compute_nice_range(0.12, 0.87, nticks=5)
        assert nice_min <= 0.12
        assert nice_max >= 0.87
        assert step > 0


class TestComputeZExtent:
    """Tests for compute_z_extent() in _heatmap_utils."""

    def test_single_trace(self) -> None:
        """Single trace returns min/max of its z-values."""
        from types import SimpleNamespace

        from src.web.rendering._heatmap_utils import compute_z_extent

        trace = SimpleNamespace(z=[[1.0, 5.0], [3.0, 9.0]])
        zmin, zmax = compute_z_extent([trace])
        assert zmin == 1.0
        assert zmax == 9.0

    def test_multiple_traces(self) -> None:
        """Multiple traces returns global min/max across all."""
        from types import SimpleNamespace

        from src.web.rendering._heatmap_utils import compute_z_extent

        t1 = SimpleNamespace(z=[[1.0, 5.0]])
        t2 = SimpleNamespace(z=[[0.5, 3.0]])
        t3 = SimpleNamespace(z=[[2.0, 12.0]])
        zmin, zmax = compute_z_extent([t1, t2, t3])
        assert zmin == 0.5
        assert zmax == 12.0

    def test_empty_traces(self) -> None:
        """Empty trace list returns default fallback (0.0, 1.0)."""
        from src.web.rendering._heatmap_utils import compute_z_extent

        zmin, zmax = compute_z_extent([])
        assert zmin == 0.0
        assert zmax == 1.0

    def test_traces_with_none_values(self) -> None:
        """None values in z are ignored."""
        from types import SimpleNamespace

        from src.web.rendering._heatmap_utils import compute_z_extent

        trace = SimpleNamespace(z=[[None, 5.0], [3.0, None]])
        zmin, zmax = compute_z_extent([trace])
        assert zmin == 3.0
        assert zmax == 5.0

    def test_trace_without_z(self) -> None:
        """Traces without a z attribute are skipped."""
        from types import SimpleNamespace

        from src.web.rendering._heatmap_utils import compute_z_extent

        t1 = SimpleNamespace(z=None)
        t2 = SimpleNamespace(z=[[2.0, 7.0]])
        zmin, zmax = compute_z_extent([t1, t2])
        assert zmin == 2.0
        assert zmax == 7.0


# ────────────────────────────────────────────────────────────────────
# Plotly connector — colorbar config integration tests
# ────────────────────────────────────────────────────────────────────


class TestPlotlyConnectorColorbarConfig:
    """Test _apply_heatmap_colorbars with various ColorbarConfig settings."""

    def test_shared_colorbar_zmin_zmax(self) -> None:
        """Shared mode sets same zmin/zmax on all traces."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        legend = LegendConfig(
            role="primary",
            colorbar=ColorbarConfig(shared=True, range_mode="manual", zmin=0.0, zmax=20.0),
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(
            data=[
                go.Heatmap(x=["A", "B"], y=["m1"], z=[[2.0, 8.0]], name="hm1"),
                go.Heatmap(x=["C", "D"], y=["m1"], z=[[5.0, 15.0]], name="hm2"),
            ]
        )
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)

        t0 = cast(Any, fig.data[0])
        t1 = cast(Any, fig.data[1])
        assert t0.zmin == 0.0
        assert t0.zmax == 20.0
        assert t1.zmin == 0.0
        assert t1.zmax == 20.0
        assert t0.showscale is False
        assert t1.showscale is True

    def test_individual_colorbar_mode(self) -> None:
        """Individual mode keeps showscale=True on all traces."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        legend = LegendConfig(
            role="primary",
            colorbar=ColorbarConfig(shared=False),
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(
            data=[
                go.Heatmap(x=["A"], y=["m"], z=[[1.0, 5.0]], name="hm1"),
                go.Heatmap(x=["A"], y=["m"], z=[[3.0, 9.0]], name="hm2"),
            ]
        )
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)

        t0 = cast(Any, fig.data[0])
        t1 = cast(Any, fig.data[1])
        assert t0.showscale is True
        assert t1.showscale is True

    def test_colorbar_title_side_top(self) -> None:
        """Title side 'top' is applied to the colorbar configuration."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        legend = LegendConfig(
            role="primary",
            title="Z-value",
            colorbar=ColorbarConfig(title_side="top"),
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m"], z=[[5.0]], name="hm")])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)

        hm = cast(Any, fig.data[0])
        assert hm.colorbar.title.side == "top"

    def test_colorbar_tick_format(self) -> None:
        """tickformat matches tick_decimals setting."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        legend = LegendConfig(
            role="primary",
            colorbar=ColorbarConfig(tick_decimals=3),
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m"], z=[[5.0]], name="hm")])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)

        hm = cast(Any, fig.data[0])
        assert hm.colorbar.tickformat == ".3f"

    def test_auto_range_nice_numbers(self) -> None:
        """Auto mode applies nice rounding so zmin/zmax cover data."""
        from src.core.models.visualization.legend_config import ColorbarConfig

        legend = LegendConfig(
            role="primary",
            colorbar=ColorbarConfig(range_mode="auto", nticks=5),
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(
            data=[
                go.Heatmap(x=["A", "B"], y=["m1", "m2"], z=[[0.3, 9.7], [2.1, 7.4]], name="hm"),
            ]
        )
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)

        hm = cast(Any, fig.data[0])
        # Nice rounding should cover the full data range
        assert hm.zmin <= 0.3
        assert hm.zmax >= 9.7


# ────────────────────────────────────────────────────────────────────
# Config builder: _build_legend_from_config reads colorbar keys
# ────────────────────────────────────────────────────────────────────


class TestConfigBuilderColorbarKeys:
    """Test that ConfigSpecBuilder reads colorbar_* keys from config."""

    def test_colorbar_keys_in_legend(self) -> None:
        """Config keys with legend_ prefix populate colorbar settings."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {
            "legend_colorbar_range_mode": "manual",
            "legend_colorbar_zmin": 0.0,
            "legend_colorbar_zmax": 50.0,
            "legend_colorbar_nticks": 10,
            "legend_colorbar_tick_decimals": 1,
            "legend_colorbar_shared": False,
        }
        spec = ConfigSpecBuilder.from_config(config)
        primary = spec.legends[0]
        assert primary.colorbar.range_mode == "manual"
        assert primary.colorbar.zmin == 0.0
        assert primary.colorbar.zmax == 50.0
        assert primary.colorbar.nticks == 10
        assert primary.colorbar.tick_decimals == 1
        assert primary.colorbar.shared is False

    def test_colorbar_defaults_when_omitted(self) -> None:
        """When colorbar keys are omitted, defaults are applied."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        spec = ConfigSpecBuilder.from_config({})
        primary = spec.legends[0]
        assert primary.colorbar.range_mode == "auto"
        assert primary.colorbar.zmin is None
        assert primary.colorbar.zmax is None
        assert primary.colorbar.nticks == 5
        assert primary.colorbar.tick_decimals == 2
        assert primary.colorbar.shared is True


# ────────────────────────────────────────────────────────────────────
# F1: Legend anchor tests
# ────────────────────────────────────────────────────────────────────


class TestPlotlyConnectorLegendAnchor:
    """Test that anchor_x/anchor_y are applied to Plotly legend."""

    def test_anchor_x_applied(self) -> None:
        """Non-auto anchor_x is set on the Plotly legend."""
        legend = LegendConfig(
            role="primary",
            anchor_x="right",
            custom_position=True,
            position_x=1.0,
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_legends(spec, fig)
        layout = cast(Any, fig.layout)
        assert layout.legend.xanchor == "right"

    def test_anchor_y_applied(self) -> None:
        """Non-auto anchor_y is set on the Plotly legend."""
        legend = LegendConfig(
            role="primary",
            anchor_y="bottom",
            custom_position=True,
            position_x=1.0,
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_legends(spec, fig)
        layout = cast(Any, fig.layout)
        assert layout.legend.yanchor == "bottom"

    def test_auto_anchor_not_set(self) -> None:
        """Auto anchors should not be explicitly set on Plotly legend."""
        legend = LegendConfig(
            role="primary",
            anchor_x="auto",
            anchor_y="auto",
            custom_position=True,
            position_x=1.0,
        )
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_legends(spec, fig)
        legend_dict = FigureSpecToPlotly._build_legend_dict(legend)
        assert "xanchor" not in legend_dict
        assert "yanchor" not in legend_dict


class TestConfigBuilderLegendAnchor:
    """Test that config builder reads anchor keys."""

    def test_anchor_keys_read(self) -> None:
        """Anchor keys from config populate LegendConfig."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {
            "legend_anchor_x": "center",
            "legend_anchor_y": "top",
        }
        spec = ConfigSpecBuilder.from_config(config)
        primary = spec.legends[0]
        assert primary.anchor_x == "center"
        assert primary.anchor_y == "top"

    def test_anchor_defaults_to_auto(self) -> None:
        """Omitted anchor keys auto-derive from default position (1.02, 1.0)."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        spec = ConfigSpecBuilder.from_config({})
        primary = spec.legends[0]
        # Default position is (1.02, 1.0) → derive_anchors → ("left", "bottom")
        assert primary.anchor_x == "left"
        assert primary.anchor_y == "bottom"


class TestMatplotlibLegendAnchor:
    """Test _anchor_to_mpl_loc mapping."""

    def test_auto_auto(self) -> None:
        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        assert FigureSpecToMatplotlib._anchor_to_mpl_loc("auto", "auto") == "upper left"

    def test_center_center(self) -> None:
        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        assert FigureSpecToMatplotlib._anchor_to_mpl_loc("center", "middle") == "center"

    def test_right_bottom(self) -> None:
        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        assert FigureSpecToMatplotlib._anchor_to_mpl_loc("right", "bottom") == "lower right"

    def test_left_top(self) -> None:
        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        assert FigureSpecToMatplotlib._anchor_to_mpl_loc("left", "top") == "upper left"

    def test_center_top(self) -> None:
        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        assert FigureSpecToMatplotlib._anchor_to_mpl_loc("center", "top") == "upper center"


# ────────────────────────────────────────────────────────────────────
# F2: Legend orientation tests
# ────────────────────────────────────────────────────────────────────


class TestConfigBuilderLegendOrientation:
    """Test that config builder reads orientation keys."""

    def test_horizontal_read(self) -> None:
        """Horizontal orientation is read from config."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {"legend_orientation": "horizontal"}
        spec = ConfigSpecBuilder.from_config(config)
        primary = spec.legends[0]
        assert primary.orientation == "horizontal"

    def test_defaults_to_vertical(self) -> None:
        """Omitted orientation defaults to 'vertical'."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        spec = ConfigSpecBuilder.from_config({})
        primary = spec.legends[0]
        assert primary.orientation == "vertical"


# ────────────────────────────────────────────────────────────────────
# F3: Tick side tests
# ────────────────────────────────────────────────────────────────────


class TestPlotlyConnectorTickSide:
    """Test that tick side is applied to Plotly axes."""

    def test_xaxis_side_top(self) -> None:
        """X-axis side='top' is set on the Plotly figure."""
        spec = FigureConfig(
            axes=AxesConfig(x=AxisConfig(tick_side="top")),
        )
        resolved = resolve_config(spec)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_xaxis(resolved, fig)
        layout = cast(Any, fig.layout)
        assert layout.xaxis.side == "top"

    def test_yaxis_side_right(self) -> None:
        """Y-axis side='right' is set on the Plotly figure."""
        spec = FigureConfig(
            axes=AxesConfig(y=AxisConfig(tick_side="right")),
        )
        resolved = resolve_config(spec)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_yaxis(resolved, fig)
        layout = cast(Any, fig.layout)
        assert layout.yaxis.side == "right"

    def test_default_no_side_set(self) -> None:
        """Default (empty) tick_side does not set 'side' on Plotly axis."""
        spec = FigureConfig(
            axes=AxesConfig(x=AxisConfig(tick_side="")),
        )
        resolved = resolve_config(spec)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_xaxis(resolved, fig)
        # When we don't set 'side', Plotly leaves it as None (default)
        layout = cast(Any, fig.layout)
        assert layout.xaxis.side is None

    def test_xaxis_bottom_no_side_set(self) -> None:
        """tick_side='bottom' (X default) does not set 'side' on Plotly."""
        spec = FigureConfig(
            axes=AxesConfig(x=AxisConfig(tick_side="bottom")),
        )
        resolved = resolve_config(spec)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_xaxis(resolved, fig)
        layout = cast(Any, fig.layout)
        # Default "bottom" is skipped, so Plotly leaves it as None
        assert layout.xaxis.side is None


class TestConfigBuilderTickSide:
    """Test that config builder reads tick_side keys."""

    def test_tick_side_keys_read(self) -> None:
        """Tick side keys from config populate AxisConfig."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {
            "xaxis_tick_side": "top",
            "yaxis_tick_side": "right",
        }
        spec = ConfigSpecBuilder.from_config(config)
        assert spec.axes.x.tick_side == "top"
        assert spec.axes.y.tick_side == "right"

    def test_tick_side_defaults_empty(self) -> None:
        """Omitted tick_side defaults to empty string."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        spec = ConfigSpecBuilder.from_config({})
        assert spec.axes.x.tick_side == ""
        assert spec.axes.y.tick_side == ""


# ────────────────────────────────────────────────────────────────────
# F4: Y-axis tick rotation tests
# ────────────────────────────────────────────────────────────────────


class TestPlotlyConnectorYTickAngle:
    """Test that Y-axis tick angle is applied to Plotly."""

    def test_tickangle_applied(self) -> None:
        """Non-zero tick_angle sets tickangle on Plotly Y-axis."""
        spec = FigureConfig(
            axes=AxesConfig(y=AxisConfig(tick_angle=45.0)),
        )
        resolved = resolve_config(spec)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_yaxis(resolved, fig)
        layout = cast(Any, fig.layout)
        assert layout.yaxis.tickangle == 45.0

    def test_zero_angle_not_set(self) -> None:
        """Zero tick_angle does not set tickangle on Plotly Y-axis."""
        spec = FigureConfig(
            axes=AxesConfig(y=AxisConfig(tick_angle=0.0)),
        )
        resolved = resolve_config(spec)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1], name="t")])
        FigureSpecToPlotly._apply_yaxis(resolved, fig)
        layout = cast(Any, fig.layout)
        # tickangle should be None when not set (Plotly default)
        assert layout.yaxis.tickangle is None


class TestConfigBuilderYTickAngle:
    """Test that config builder reads Y-axis tick angle."""

    def test_yaxis_tickangle_read(self) -> None:
        """yaxis_tickangle from config populates AxisConfig.tick_angle."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {"yaxis_tickangle": 30}
        spec = ConfigSpecBuilder.from_config(config)
        assert spec.axes.y.tick_angle == 30.0

    def test_yaxis_tickangle_defaults_zero(self) -> None:
        """Omitted yaxis_tickangle defaults to 0.0."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        spec = ConfigSpecBuilder.from_config({})
        assert spec.axes.y.tick_angle == 0.0


# ── Colorbar tick angle & tick side ───────────────────────────────


class TestColorbarConfigTickFields:
    """Test ColorbarConfig tick_angle and tick_side fields."""

    def test_tick_angle_default(self) -> None:
        cbar = ColorbarConfig()
        assert cbar.tick_angle == 0.0

    def test_tick_side_default(self) -> None:
        cbar = ColorbarConfig()
        assert cbar.tick_side == "right"

    def test_tick_angle_custom(self) -> None:
        cbar = ColorbarConfig(tick_angle=45.0)
        assert cbar.tick_angle == 45.0

    def test_tick_side_left(self) -> None:
        cbar = ColorbarConfig(tick_side="left")
        assert cbar.tick_side == "left"

    def test_to_dict_includes_tick_fields(self) -> None:
        cbar = ColorbarConfig(tick_angle=30.0, tick_side="left")
        d = cbar.to_dict()
        assert d["tick_angle"] == 30.0
        assert d["tick_side"] == "left"

    def test_round_trip(self) -> None:
        original = ColorbarConfig(tick_angle=-45.0, tick_side="left")
        d = original.to_dict()
        restored = ColorbarConfig.from_dict(d)
        assert restored.tick_angle == -45.0
        assert restored.tick_side == "left"


class TestPlotlyColorbarTicks:
    """Test Plotly connector applies colorbar tick_angle and tick_side."""

    def test_tick_angle_applied(self) -> None:
        """Colorbar tick_angle is passed to Plotly trace."""
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m1"], z=[[5.0]])])
        legend = LegendConfig(
            role="primary",
            colorbar=ColorbarConfig(tick_angle=45.0),
        )
        spec = FigureConfig(legends=[legend])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm = cast(Any, fig.data[0])
        assert hm.colorbar.tickangle == 45.0

    def test_tick_side_left(self) -> None:
        """Colorbar tick_side='left' sets ticklabelposition."""
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m1"], z=[[5.0]])])
        legend = LegendConfig(
            role="primary",
            colorbar=ColorbarConfig(tick_side="left"),
        )
        spec = FigureConfig(legends=[legend])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm = cast(Any, fig.data[0])
        assert hm.colorbar.ticklabelposition == "outside left"

    def test_default_tick_side_no_position_key(self) -> None:
        """Default tick_side='right' does NOT add ticklabelposition."""
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m1"], z=[[5.0]])])
        legend = LegendConfig(role="primary", colorbar=ColorbarConfig())
        spec = FigureConfig(legends=[legend])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm = cast(Any, fig.data[0])
        assert hm.colorbar.ticklabelposition is None

    def test_default_tick_angle_no_tickangle_key(self) -> None:
        """Default tick_angle=0 does NOT set tickangle."""
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m1"], z=[[5.0]])])
        legend = LegendConfig(role="primary", colorbar=ColorbarConfig())
        spec = FigureConfig(legends=[legend])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm = cast(Any, fig.data[0])
        assert hm.colorbar.tickangle is None


class TestConfigBuilderColorbarTicks:
    """Test config builder reads colorbar tick_angle and tick_side."""

    def test_colorbar_tick_angle_read(self) -> None:
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {"legend_colorbar_tick_angle": 30.0}
        spec = ConfigSpecBuilder.from_config(config)
        assert spec.legends[0].colorbar.tick_angle == 30.0

    def test_colorbar_tick_side_read(self) -> None:
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {"legend_colorbar_tick_side": "left"}
        spec = ConfigSpecBuilder.from_config(config)
        assert spec.legends[0].colorbar.tick_side == "left"

    def test_colorbar_tick_defaults(self) -> None:
        from src.web.rendering.config_builder import ConfigSpecBuilder

        spec = ConfigSpecBuilder.from_config({})
        assert spec.legends[0].colorbar.tick_angle == 0.0
        assert spec.legends[0].colorbar.tick_side == "right"


# ── Legend derive_anchors & auto-derivation ───────────────────────


class TestLegendDeriveAnchors:
    """Test LegendConfig.derive_anchors static method."""

    def test_top_right_position(self) -> None:
        ax, ay = LegendConfig.derive_anchors(0.9, 0.9)
        assert ax == "left"
        assert ay == "bottom"

    def test_bottom_left_position(self) -> None:
        ax, ay = LegendConfig.derive_anchors(0.1, 0.1)
        assert ax == "right"
        assert ay == "top"

    def test_center_position(self) -> None:
        ax, ay = LegendConfig.derive_anchors(0.5, 0.5)
        assert ax == "center"
        assert ay == "middle"

    def test_outside_right(self) -> None:
        """x=1.02 (outside plot) should anchor left."""
        ax, ay = LegendConfig.derive_anchors(1.02, 1.0)
        assert ax == "left"
        assert ay == "bottom"

    def test_outside_left(self) -> None:
        """x=-0.1 (outside plot) should anchor right."""
        ax, ay = LegendConfig.derive_anchors(-0.1, 0.5)
        assert ax == "right"
        assert ay == "middle"


class TestConfigBuilderAutoAnchors:
    """Test config builder auto-derives anchors from position."""

    def test_auto_derives_anchors(self) -> None:
        """When anchor_x/anchor_y are absent, they are auto-derived from position."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {"legend_x": 0.9, "legend_y": 0.1}
        spec = ConfigSpecBuilder.from_config(config)
        legend = spec.legends[0]
        # 0.9 > 0.8 → "left", 0.1 < 0.2 → "top"
        assert legend.anchor_x == "left"
        assert legend.anchor_y == "top"

    def test_preserves_explicit_anchors(self) -> None:
        """When user explicitly sets anchors, they are NOT overridden."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        config = {
            "legend_x": 0.9,
            "legend_y": 0.1,
            "legend_anchor_x": "center",
            "legend_anchor_y": "middle",
        }
        spec = ConfigSpecBuilder.from_config(config)
        legend = spec.legends[0]
        assert legend.anchor_x == "center"
        assert legend.anchor_y == "middle"

    def test_default_primary_position_derives_left(self) -> None:
        """Default primary position (1.02, 1.0) auto-derives left/bottom."""
        from src.web.rendering.config_builder import ConfigSpecBuilder

        spec = ConfigSpecBuilder.from_config({})
        legend = spec.legends[0]
        # 1.02 > 0.8 → "left", 1.0 > 0.8 → "bottom"
        assert legend.anchor_x == "left"
        assert legend.anchor_y == "bottom"


# ── Colorbar position & orientation ──────────────────────────────


class TestPlotlyColorbarPosition:
    """Test that Plotly colorbar receives position and orientation from legend."""

    def test_colorbar_x_position(self) -> None:
        """Colorbar x position is passed from legend config."""
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m1"], z=[[5.0]])])
        legend = LegendConfig(
            role="primary",
            custom_position=True,
            position_x=0.5,
            position_y=0.5,
        )
        spec = FigureConfig(legends=[legend])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm = cast(Any, fig.data[0])
        assert hm.colorbar.x == 0.5
        assert hm.colorbar.y == 0.5

    def test_colorbar_horizontal_orientation(self) -> None:
        """Colorbar orientation 'h' is set when legend is horizontal."""
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m1"], z=[[5.0]])])
        legend = LegendConfig(
            role="primary",
            orientation="horizontal",
        )
        spec = FigureConfig(legends=[legend])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm = cast(Any, fig.data[0])
        assert hm.colorbar.orientation == "h"

    def test_colorbar_default_vertical_no_orientation(self) -> None:
        """Default vertical orientation does not set explicit orientation."""
        fig = go.Figure(data=[go.Heatmap(x=["A"], y=["m1"], z=[[5.0]])])
        legend = LegendConfig(role="primary")
        spec = FigureConfig(legends=[legend])
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        hm = cast(Any, fig.data[0])
        assert hm.colorbar.orientation is None
