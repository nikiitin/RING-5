"""
Tests for connectors — Plotly connector, Matplotlib connector, and builders.

Covers:
  - FigureSpecToPlotly: apply spec to a Plotly figure
  - FigureSpecToMatplotlib: apply spec to matplotlib axes
  - PlotlyFigureSpecBuilder: extract spec from Plotly figure
  - PresetSpecBuilder: build spec from LaTeXPreset
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
    SeparatorConfig,
)
from src.core.models.visualization.legend_config import LegendConfig
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.typography_config import TypographyConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.config_builder import PlotlyFigureSpecBuilder, PresetSpecBuilder
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


class TestPlotlyFigureSpecBuilder:
    """Test extracting FigureConfig from Plotly figure + config."""

    def test_basic_extraction(self) -> None:
        """Extract spec from a simple figure."""
        fig = go.Figure(
            data=[go.Bar(x=["A", "B"], y=[1, 2])],
            layout=go.Layout(
                title="Test",
                width=800,
                height=600,
                paper_bgcolor="#FAFAFA",
                plot_bgcolor="#FFFFFF",
            ),
        )
        config = {
            "xlabel": "Category",
            "ylabel": "Value",
            "title_font_size": 14,
            "legend_font_size": 10,
        }

        spec = PlotlyFigureSpecBuilder.from_plotly(fig, config)

        assert spec.title == "Test"
        assert spec.axes.x.label == "Category"
        assert spec.axes.y.label == "Value"
        assert spec.typography.font_size_title == 14
        assert spec.typography.font_size_legend == 10
        assert spec.paper_bgcolor == "#FAFAFA"

    def test_empty_config(self) -> None:
        """Empty config should produce spec with defaults."""
        fig = go.Figure()
        config: dict = {}  # type: ignore[type-arg]

        spec = PlotlyFigureSpecBuilder.from_plotly(fig, config)

        assert spec.title == ""
        assert spec.axes.x.label == ""

    def test_legend_extraction(self) -> None:
        """Legends should be extracted from layout."""
        fig = go.Figure(
            data=[go.Bar(x=["A"], y=[1])],
            layout=go.Layout(
                legend=dict(
                    x=0.5,
                    y=1.0,
                    xanchor="center",
                    yanchor="top",
                ),
            ),
        )
        config = {"legend_font_size": 12, "legend_orientation": "h"}

        spec = PlotlyFigureSpecBuilder.from_plotly(fig, config)

        assert len(spec.legends) >= 1
        primary = spec.legends[0]
        assert primary.position_x == 0.5
        assert primary.position_y == 1.0
        assert primary.anchor_x == "center"
        assert primary.orientation == "horizontal"


class TestPresetSpecBuilder:
    """Test building FigureConfig from a LaTeXPreset dictionary."""

    def _make_preset(self) -> dict:  # type: ignore[type-arg]
        """Create a minimal LaTeXPreset-compatible dictionary."""
        return {
            "width_inches": 3.5,
            "height_inches": 2.5,
            "dpi": 600,
            "font_family": "sans-serif",
            "font_size_base": 8,
            "font_size_title": 10,
            "font_size_xlabel": 8,
            "font_size_ylabel": 8,
            "font_size_ticks": 6,
            "font_size_yticks": 6,
            "font_size_annotations": 5,
            "font_size_legend": 7,
            "font_size_legend2": -1,
            "font_size_legend3": -1,
            "bold_title": True,
            "bold_xlabel": False,
            "bold_ylabel": False,
            "bold_ticks": False,
            "bold_annotations": True,
            "bold_legend": False,
            "legend_ncol": 2,
            "legend_columnspacing": 1.0,
            "legend_handletextpad": 0.4,
            "legend_labelspacing": 0.3,
            "legend_handlelength": 1.5,
            "legend_handleheight": 0.8,
            "legend_borderpad": 0.3,
            "legend_borderaxespad": 0.6,
            "legend_custom_pos": True,
            "legend_x": 0.5,
            "legend_y": 1.05,
            "xtick_rotation": 30.0,
            "xtick_pad": 4.0,
            "xtick_ha": "right",
            "ytick_pad": 4.0,
            "ylabel_pad": 12.0,
            "ylabel_y_position": 0.5,
            "xaxis_margin": 0.03,
            "bar_width_scale": 0.9,
            "group_separator": True,
            "group_separator_style": "dot",
            "group_separator_color": "blue",
            "group_label_offset": -0.15,
            "group_label_alternate": False,
            "latex_extra_preamble": "",
        }

    def test_dimensions(self) -> None:
        """Preset dimensions should map correctly."""
        preset = self._make_preset()
        spec = PresetSpecBuilder.from_preset(preset)

        assert spec.dimensions.width == 3.5
        assert spec.dimensions.height == 2.5
        assert spec.dimensions.dpi == 600
        assert spec.dimensions.bar_width_scale == 0.9

    def test_typography(self) -> None:
        """Preset typography should map correctly."""
        preset = self._make_preset()
        spec = PresetSpecBuilder.from_preset(preset)

        assert spec.typography.font_size_base == 8
        assert spec.typography.font_size_title == 10
        assert spec.typography.font_size_legend == 7
        assert spec.typography.bold_title is True
        assert spec.typography.bold_annotations is True

    def test_legends(self) -> None:
        """Preset should produce 3 legends (primary, secondary, tertiary)."""
        preset = self._make_preset()
        spec = PresetSpecBuilder.from_preset(preset)

        assert len(spec.legends) == 3
        primary = spec.legends[0]
        assert primary.role == "primary"
        assert primary.ncol == 2
        assert primary.custom_position is True
        assert primary.position_x == 0.5
        assert primary.spacing.columnspacing == 1.0

        secondary = spec.legends[1]
        assert secondary.role == "secondary"
        assert secondary.font_size == -1  # sentinel, needs resolution

        tertiary = spec.legends[2]
        assert tertiary.role == "tertiary"
        assert tertiary.font_size == -1

    def test_axes(self) -> None:
        """Preset axis settings should map correctly."""
        preset = self._make_preset()
        spec = PresetSpecBuilder.from_preset(preset)

        assert spec.axes.x.tick_angle == 30.0
        assert spec.axes.x.tick_pad == 4.0
        assert spec.axes.x.tick_ha == "right"
        assert spec.axes.y.label_pad == 12.0
        assert spec.axes.group_label_offset == -0.15

    def test_separator(self) -> None:
        """Preset separator should map correctly."""
        preset = self._make_preset()
        spec = PresetSpecBuilder.from_preset(preset)

        assert spec.separator.enabled is True
        assert spec.separator.style == "dot"
        assert spec.separator.color == "blue"

    def test_font_family(self) -> None:
        """Font family from preset should be preserved."""
        preset = self._make_preset()
        spec = PresetSpecBuilder.from_preset(preset)

        assert spec.font_family == "sans-serif"

    def test_empty_preset(self) -> None:
        """Empty preset should produce spec with defaults."""
        spec = PresetSpecBuilder.from_preset({})

        assert spec.dimensions.width == 7.0
        assert spec.typography.font_size_base == 10
        assert len(spec.legends) == 3  # always 3

    def test_preset_then_resolve(self) -> None:
        """Preset spec with sentinels should resolve correctly."""
        preset = self._make_preset()
        spec = PresetSpecBuilder.from_preset(preset)
        resolved = resolve_config(spec)

        # legend2 font_size was -1, should inherit from primary (7)
        assert resolved.legends[1].font_size == 7
        # legend3 font_size was -1, should inherit from primary (7)
        assert resolved.legends[2].font_size == 7


# ────────────────────────────────────────────────────────────────────
# Step 10 — New FigureSpecToPlotly feature methods
# ────────────────────────────────────────────────────────────────────


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


class TestPlotlyConnectorSeparatorLines:
    """Test _apply_separator_lines."""

    def test_separator_creates_shapes(self) -> None:
        spec = FigureConfig(separator=SeparatorConfig(enabled=True, style="dash", color="gray"))
        fig = go.Figure(data=[go.Bar(x=["A", "B", "C"], y=[1, 2, 3])])
        FigureSpecToPlotly._apply_separator_lines(spec, fig)
        # Should create N-1 = 2 shapes for 3 categories
        assert len(cast(Any, fig.layout).shapes) == 2

    def test_separator_disabled_no_shapes(self) -> None:
        spec = FigureConfig(separator=SeparatorConfig(enabled=False))
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        FigureSpecToPlotly._apply_separator_lines(spec, fig)
        assert len(cast(Any, fig.layout).shapes) == 0


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
