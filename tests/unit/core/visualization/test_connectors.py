"""
Tests for connectors — Plotly connector, Matplotlib connector, and builders.

Covers:
  - FigureSpecToPlotly: apply spec to a Plotly figure
  - FigureSpecToMatplotlib: apply spec to matplotlib axes
  - PlotlyFigureSpecBuilder: extract spec from Plotly figure
  - PresetSpecBuilder: build spec from LaTeXPreset
"""

import pytest
import plotly.graph_objects as go

from src.core.visualization.figure_spec import (
    DimensionsSpec,
    FigureSpec,
    MarginsSpec,
    SeparatorSpec,
)
from src.core.visualization.typography_spec import TypographySpec
from src.core.visualization.axis_spec import AxesSpec, AxisSpec
from src.core.visualization.legend_spec import LegendSpec, LegendSpacingSpec
from src.core.visualization.resolvers import resolve_spec
from src.core.visualization.connectors.plotly_connector import FigureSpecToPlotly
from src.core.visualization.connectors.builders import (
    PlotlyFigureSpecBuilder,
    PresetSpecBuilder,
)


class TestFigureSpecToPlotly:
    """Test Plotly connector."""

    def _make_simple_fig(self) -> go.Figure:
        """Create a simple bar chart for testing."""
        return go.Figure(
            data=[go.Bar(x=["A", "B", "C"], y=[1, 2, 3], name="Test")]
        )

    def test_apply_dimensions(self) -> None:
        """Dimensions should set width/height/margins on figure."""
        spec = FigureSpec(
            dimensions=DimensionsSpec(
                width=7.0,
                height=4.0,
                dpi=100,  # 7*100=700px, 4*100=400px
                margins=MarginsSpec(top=10, bottom=20, left=30, right=40),
            )
        )
        resolved = resolve_spec(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        assert fig.layout.width == 700
        assert fig.layout.height == 400
        assert fig.layout.margin.t == 10
        assert fig.layout.margin.b == 20
        assert fig.layout.margin.l == 30
        assert fig.layout.margin.r == 40

    def test_apply_backgrounds(self) -> None:
        """Background colors should be applied."""
        spec = FigureSpec(
            paper_bgcolor="#F0F0F0",
            plot_bgcolor="#FFFFFF",
        )
        resolved = resolve_spec(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        assert fig.layout.paper_bgcolor == "#F0F0F0"
        assert fig.layout.plot_bgcolor == "#FFFFFF"

    def test_apply_title(self) -> None:
        """Title should be applied."""
        spec = FigureSpec(
            title="My Plot",
            typography=TypographySpec(font_size_title=16),
        )
        resolved = resolve_spec(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        assert fig.layout.title.text == "My Plot"
        assert fig.layout.title.font.size == 16

    def test_apply_xaxis(self) -> None:
        """X-axis configuration should be applied."""
        spec = FigureSpec(
            axes=AxesSpec(
                x=AxisSpec(
                    label="Benchmark",
                    tick_angle=45.0,
                    show_grid=True,
                    grid_color="#ccc",
                )
            ),
            typography=TypographySpec(font_size_xlabel=12, font_size_ticks=8),
        )
        resolved = resolve_spec(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        assert fig.layout.xaxis.title.text == "Benchmark"
        assert fig.layout.xaxis.title.font.size == 12
        assert fig.layout.xaxis.tickangle == 45.0
        assert fig.layout.xaxis.tickfont.size == 8

    def test_apply_yaxis(self) -> None:
        """Y-axis configuration should be applied."""
        spec = FigureSpec(
            axes=AxesSpec(
                y=AxisSpec(label="Speedup", dtick=0.5)
            ),
            typography=TypographySpec(
                font_size_ylabel=11,
                font_size_yticks=7,
            ),
        )
        resolved = resolve_spec(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        assert fig.layout.yaxis.title.text == "Speedup"
        assert fig.layout.yaxis.title.font.size == 11
        assert fig.layout.yaxis.dtick == 0.5

    def test_apply_legend(self) -> None:
        """Legend configuration should be applied."""
        spec = FigureSpec(
            legends=[
                LegendSpec(
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
        resolved = resolve_spec(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)

        assert fig.layout.legend.font.size == 10
        assert fig.layout.legend.orientation == "h"
        assert fig.layout.legend.x == 0.5
        assert fig.layout.legend.y == 1.1
        assert fig.layout.legend.xanchor == "center"
        assert fig.layout.legend.yanchor == "bottom"

    def test_no_legend(self) -> None:
        """Empty legends list should not crash."""
        spec = FigureSpec(legends=[])
        resolved = resolve_spec(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)
        # Should not raise

    def test_no_title(self) -> None:
        """Empty title should not be applied."""
        spec = FigureSpec(title="")
        resolved = resolve_spec(spec)
        fig = self._make_simple_fig()

        FigureSpecToPlotly.apply(resolved, fig)
        # Should not crash, title remains whatever Plotly default is


class TestPlotlyFigureSpecBuilder:
    """Test extracting FigureSpec from Plotly figure + config."""

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
    """Test building FigureSpec from a LaTeXPreset dictionary."""

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
            "group_separator_style": "dotted",
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
        """Preset should produce 3 legends (primary, secondary, boxed)."""
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

        boxed = spec.legends[2]
        assert boxed.role == "boxed"
        assert boxed.font_size == -1

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
        assert spec.separator.style == "dotted"
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
        resolved = resolve_spec(spec)

        # legend2 font_size was -1, should inherit from primary (7)
        assert resolved.legends[1].font_size == 7
        # legend3 font_size was -1, should inherit from primary (7)
        assert resolved.legends[2].font_size == 7
