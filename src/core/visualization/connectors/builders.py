"""
Bidirectional builders — construct FigureSpec from various sources.

  - ``PlotlyFigureSpecBuilder`` — extract spec from Plotly figure + config dict
  - ``PresetSpecBuilder`` — build spec from a LaTeXPreset (journal template)

These replace:
  - ``LayoutExtractor.extract_layout()`` (Plotly → raw dict)
  - ``LayoutApplier._build_*_config()`` methods (LaTeXPreset → dataclasses)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.visualization.figure_spec import (
    DimensionsSpec,
    FigureSpec,
    MarginsSpec,
    SeparatorSpec,
)
from src.core.visualization.typography_spec import TypographySpec
from src.core.visualization.axis_spec import AxesSpec, AxisSpec
from src.core.visualization.legend_spec import LegendSpec, LegendSpacingSpec
from src.core.visualization.annotation_spec import AnnotationSpec


class PlotlyFigureSpecBuilder:
    """Build a FigureSpec by extracting state from a Plotly figure + config.

    This is what ``LayoutExtractor`` currently does, but producing a typed
    ``FigureSpec`` instead of a raw dictionary.

    Usage:
        spec = PlotlyFigureSpecBuilder.from_plotly(fig, config)
    """

    @staticmethod
    def from_plotly(
        fig: Any,
        config: Dict[str, Any],
    ) -> FigureSpec:
        """Extract a FigureSpec from an existing Plotly figure and config.

        Args:
            fig: A ``plotly.graph_objects.Figure``.
            config: The plot config dict (``BasePlot.config``).

        Returns:
            A FigureSpec populated from the figure's current state.
            May contain sentinel values (-1) for fields not set.
        """
        layout = fig.layout if hasattr(fig, "layout") else {}

        # ── Dimensions ───────────────────────────────────────────
        margins = _extract_margins(layout)
        dims = DimensionsSpec(
            width=_px_to_inches(getattr(layout, "width", None) or config.get("width", 700)),
            height=_px_to_inches(getattr(layout, "height", None) or config.get("height", 400)),
            dpi=config.get("dpi", 96),
            margins=margins,
            bargap=config.get("bargap", 0.15),
            bargroupgap=config.get("bargroupgap", 0.1),
        )

        # ── Typography ───────────────────────────────────────────
        typo = _extract_typography(layout, config)

        # ── Axes ─────────────────────────────────────────────────
        axes = _extract_axes(layout, config)

        # ── Legends ──────────────────────────────────────────────
        legends = _extract_legends(layout, config)

        # ── Annotations ──────────────────────────────────────────
        annotations = _extract_annotations(layout)

        # ── Title ────────────────────────────────────────────────
        title = ""
        title_obj = getattr(layout, "title", None)
        if title_obj:
            title = getattr(title_obj, "text", "") or config.get("title", "")

        # ── Backgrounds ──────────────────────────────────────────
        paper_bg = getattr(layout, "paper_bgcolor", None) or config.get(
            "paper_bgcolor", "white"
        )
        plot_bg = getattr(layout, "plot_bgcolor", None) or config.get(
            "plot_bgcolor", "white"
        )

        return FigureSpec(
            dimensions=dims,
            typography=typo,
            axes=axes,
            legends=legends,
            annotations=annotations,
            title=title,
            paper_bgcolor=paper_bg,
            plot_bgcolor=plot_bg,
        )


class PresetSpecBuilder:
    """Build a FigureSpec from a LaTeXPreset (journal template).

    This replaces the 4 builder methods in ``LayoutApplier``:
      - ``_build_font_config()``
      - ``_build_positioning_config()``
      - ``_build_separator_config()``
      - ``_build_legend_spacing_config()``

    Usage:
        spec = PresetSpecBuilder.from_preset(preset)
    """

    @staticmethod
    def from_preset(preset: Dict[str, Any]) -> FigureSpec:
        """Build a FigureSpec from a LaTeXPreset dictionary.

        Args:
            preset: A ``LaTeXPreset`` TypedDict (or compatible dict).

        Returns:
            A FigureSpec populated from the preset values.
        """
        # ── Dimensions ───────────────────────────────────────────
        dims = DimensionsSpec(
            width=preset.get("width_inches", 7.0),
            height=preset.get("height_inches", 4.0),
            dpi=preset.get("dpi", 300),
            bar_width_scale=preset.get("bar_width_scale", 1.0),
        )

        # ── Typography ───────────────────────────────────────────
        typo = TypographySpec(
            font_size_base=preset.get("font_size_base", 10),
            font_size_title=preset.get("font_size_title", 10),
            font_size_xlabel=preset.get("font_size_xlabel", 9),
            font_size_ylabel=preset.get("font_size_ylabel", 9),
            font_size_y2label=preset.get("font_size_y2label", -1),
            font_size_ticks=preset.get("font_size_ticks", 7),
            font_size_yticks=preset.get("font_size_yticks", 7),
            font_size_y2ticks=preset.get("font_size_y2ticks", -1),
            font_size_annotations=preset.get("font_size_annotations", 6),
            font_size_legend=preset.get("font_size_legend", 8),
            font_size_legend2=preset.get("font_size_legend2", -1),
            font_size_legend3=preset.get("font_size_legend3", -1),
            legend3_number_fontsize=preset.get("legend3_number_fontsize", -1),
            legend3_text_fontsize=preset.get("legend3_text_fontsize", -1),
            bold_title=preset.get("bold_title", False),
            bold_xlabel=preset.get("bold_xlabel", False),
            bold_ylabel=preset.get("bold_ylabel", False),
            bold_y2label=preset.get("bold_y2label", False),
            bold_ticks=preset.get("bold_ticks", False),
            bold_annotations=preset.get("bold_annotations", True),
            bold_group_labels=preset.get("bold_group_labels", True),
            bold_legend=preset.get("bold_legend", False),
            bold_legend2=preset.get("bold_legend2", False),
            bold_legend3=preset.get("bold_legend3", False),
        )

        # ── Axes positioning ─────────────────────────────────────
        x_axis = AxisSpec(
            tick_angle=preset.get("xtick_rotation", 45.0),
            tick_pad=preset.get("xtick_pad", 5.0),
            tick_ha=preset.get("xtick_ha", "right"),
            tick_offset=preset.get("xtick_offset", 0.0),
            margin=preset.get("xaxis_margin", 0.02),
        )
        y_axis = AxisSpec(
            label_pad=preset.get("ylabel_pad", 10.0),
            label_position=preset.get("ylabel_y_position", 0.5),
            tick_pad=preset.get("ytick_pad", 5.0),
        )

        axes = AxesSpec(
            x=x_axis,
            y=y_axis,
            group_label_offset=preset.get("group_label_offset", -0.12),
            group_label_alternate=preset.get("group_label_alternate", True),
            group_label_alt_spacing=preset.get("group_label_alt_spacing", 0.05),
        )

        # ── Legends ──────────────────────────────────────────────
        primary_spacing = LegendSpacingSpec(
            columnspacing=preset.get("legend_columnspacing", 0.5),
            handletextpad=preset.get("legend_handletextpad", 0.3),
            labelspacing=preset.get("legend_labelspacing", 0.2),
            handlelength=preset.get("legend_handlelength", 1.0),
            handleheight=preset.get("legend_handleheight", 0.7),
            borderpad=preset.get("legend_borderpad", 0.2),
            borderaxespad=preset.get("legend_borderaxespad", 0.5),
        )
        primary_legend = LegendSpec(
            role="primary",
            font_size=preset.get("font_size_legend", 8),
            bold=preset.get("bold_legend", False),
            ncol=preset.get("legend_ncol", 1),
            custom_position=preset.get("legend_custom_pos", False),
            position_x=preset.get("legend_x", -1.0),
            position_y=preset.get("legend_y", -1.0),
            spacing=primary_spacing,
        )

        # Secondary legend (legend2)
        legend2_spacing = LegendSpacingSpec(
            columnspacing=preset.get("legend2_columnspacing", -1.0),
            handletextpad=preset.get("legend2_handletextpad", -1.0),
            labelspacing=preset.get("legend2_labelspacing", -1.0),
            handlelength=preset.get("legend2_handlelength", -1.0),
            handleheight=preset.get("legend2_handleheight", -1.0),
            borderpad=preset.get("legend2_borderpad", -1.0),
            borderaxespad=preset.get("legend2_borderaxespad", -1.0),
        )
        legend2 = LegendSpec(
            role="secondary",
            font_size=preset.get("font_size_legend2", -1),
            bold=preset.get("bold_legend2", False),
            ncol=preset.get("legend2_ncol", -1),
            spacing=legend2_spacing,
        )

        # Boxed annotation legend (legend3)
        legend3_spacing = LegendSpacingSpec(
            borderpad=preset.get("legend3_borderpad", -1.0),
            labelspacing=preset.get("legend3_labelspacing", -1.0),
        )
        legend3 = LegendSpec(
            role="boxed",
            font_size=preset.get("font_size_legend3", -1),
            bold=preset.get("bold_legend3", False),
            number_fontsize=preset.get("legend3_number_fontsize", -1),
            text_fontsize=preset.get("legend3_text_fontsize", -1),
            spacing=legend3_spacing,
        )

        legends = [primary_legend, legend2, legend3]

        # ── Separator ────────────────────────────────────────────
        separator = SeparatorSpec(
            enabled=preset.get("group_separator", False),
            style=preset.get("group_separator_style", "dashed"),
            color=preset.get("group_separator_color", "gray"),
        )

        return FigureSpec(
            dimensions=dims,
            typography=typo,
            axes=axes,
            legends=legends,
            separator=separator,
            font_family=preset.get("font_family", "serif"),
            latex_extra_preamble=preset.get("latex_extra_preamble", ""),
        )


# ────────────────────────────────────────────────────────────────────
# Helper functions for PlotlyFigureSpecBuilder
# ────────────────────────────────────────────────────────────────────

def _px_to_inches(px: Any, dpi: int = 96) -> float:
    """Convert pixels to inches."""
    if px is None:
        return 7.0
    try:
        return float(px) / dpi
    except (TypeError, ValueError):
        return 7.0


def _extract_margins(layout: Any) -> MarginsSpec:
    """Extract margins from Plotly layout."""
    margin = getattr(layout, "margin", None)
    if margin is None:
        return MarginsSpec()
    return MarginsSpec(
        top=float(getattr(margin, "t", 40) or 40),
        bottom=float(getattr(margin, "b", 80) or 80),
        left=float(getattr(margin, "l", 60) or 60),
        right=float(getattr(margin, "r", 30) or 30),
        pad=float(getattr(margin, "pad", 0) or 0),
    )


def _extract_typography(layout: Any, config: Dict[str, Any]) -> TypographySpec:
    """Extract typography settings from Plotly layout and config."""
    # Plotly stores font sizes in various places; config dict is primary
    return TypographySpec(
        font_size_title=config.get("title_font_size", 10),
        font_size_xlabel=config.get("xaxis_title_font_size", 9),
        font_size_ylabel=config.get("yaxis_title_font_size", 9),
        font_size_ticks=config.get("xaxis_tickfont_size", 7),
        font_size_yticks=config.get("yaxis_tickfont_size", 7),
        font_size_legend=config.get("legend_font_size", 8),
        font_size_annotations=config.get("text_font_size", 6),
    )


def _extract_axes(layout: Any, config: Dict[str, Any]) -> AxesSpec:
    """Extract axis configuration from Plotly layout."""
    xaxis = getattr(layout, "xaxis", None)
    yaxis = getattr(layout, "yaxis", None)
    yaxis2 = getattr(layout, "yaxis2", None)

    x = AxisSpec(
        label=config.get("xlabel", "") or _get_axis_title(xaxis),
        tick_angle=float(config.get("xaxis_tickangle", 0)),
        range=config.get("range_x"),
        category_order=config.get("xaxis_order"),
        label_aliases=config.get("xaxis_labels"),
        show_grid=config.get("show_grid", True),
    )

    y = AxisSpec(
        label=config.get("ylabel", "") or _get_axis_title(yaxis),
        range=config.get("range_y"),
        dtick=config.get("yaxis_dtick"),
        show_grid=config.get("show_grid", True),
    )

    y2: Optional[AxisSpec] = None
    if yaxis2 is not None:
        y2 = AxisSpec(
            label=_get_axis_title(yaxis2),
            range=_get_range(yaxis2),
        )

    return AxesSpec(x=x, y=y, y2=y2)


def _extract_legends(layout: Any, config: Dict[str, Any]) -> List[LegendSpec]:
    """Extract legend configurations from Plotly layout."""
    legends: List[LegendSpec] = []

    legend = getattr(layout, "legend", None)
    primary = LegendSpec(
        role="primary",
        font_size=config.get("legend_font_size", 8),
        font_color=config.get("legend_font_color", "#444"),
        orientation=(
            "horizontal"
            if config.get("legend_orientation") == "h"
            else "vertical"
        ),
    )

    if legend is not None:
        x = getattr(legend, "x", None)
        y = getattr(legend, "y", None)
        if x is not None:
            primary.position_x = float(x)
            primary.custom_position = True
        if y is not None:
            primary.position_y = float(y)
        xanchor = getattr(legend, "xanchor", None)
        if xanchor:
            primary.anchor_x = xanchor
        yanchor = getattr(legend, "yanchor", None)
        if yanchor:
            primary.anchor_y = yanchor

    legends.append(primary)

    # legend2
    legend2 = getattr(layout, "legend2", None)
    if legend2 is not None:
        sec = LegendSpec(role="secondary")
        x = getattr(legend2, "x", None)
        y = getattr(legend2, "y", None)
        if x is not None:
            sec.position_x = float(x)
            sec.custom_position = True
        if y is not None:
            sec.position_y = float(y)
        xanchor = getattr(legend2, "xanchor", None)
        if xanchor:
            sec.anchor_x = xanchor
        yanchor = getattr(legend2, "yanchor", None)
        if yanchor:
            sec.anchor_y = yanchor
        legends.append(sec)

    return legends


def _extract_annotations(layout: Any) -> List[AnnotationSpec]:
    """Extract annotation objects from Plotly layout."""
    annotations: List[AnnotationSpec] = []
    layout_anns = getattr(layout, "annotations", None) or []

    for ann in layout_anns:
        font = getattr(ann, "font", None)
        spec = AnnotationSpec(
            text=getattr(ann, "text", ""),
            x=float(getattr(ann, "x", 0)),
            y=float(getattr(ann, "y", 0)),
            xref="paper" if getattr(ann, "xref", "") == "paper" else "data",
            yref="paper" if getattr(ann, "yref", "") == "paper" else "data",
            show_arrow=bool(getattr(ann, "showarrow", False)),
            font_size=int(getattr(font, "size", 0) or 0) if font else -1,
            font_color=str(getattr(font, "color", "#444") or "#444") if font else "#444",
            text_angle=float(getattr(ann, "textangle", 0) or 0),
            border_width=float(getattr(ann, "borderwidth", 0) or 0),
            border_color=str(getattr(ann, "bordercolor", "") or ""),
            border_pad=float(getattr(ann, "borderpad", 0) or 0),
            bgcolor=str(getattr(ann, "bgcolor", "") or ""),
            align=getattr(ann, "align", "left") or "left",
        )
        xanchor = getattr(ann, "xanchor", None)
        if xanchor:
            spec.xanchor = xanchor
        yanchor = getattr(ann, "yanchor", None)
        if yanchor:
            spec.yanchor = yanchor
        annotations.append(spec)

    return annotations


def _get_axis_title(axis: Any) -> str:
    """Extract title text from a Plotly axis object."""
    if axis is None:
        return ""
    title = getattr(axis, "title", None)
    if title is None:
        return ""
    text = getattr(title, "text", None)
    return str(text) if text else ""


def _get_range(axis: Any) -> Optional[List[float]]:
    """Extract range from a Plotly axis object."""
    if axis is None:
        return None
    r = getattr(axis, "range", None)
    if r is None:
        return None
    try:
        return [float(r[0]), float(r[1])]
    except (TypeError, IndexError, ValueError):
        return None
