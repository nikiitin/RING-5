"""
Bidirectional builders — construct FigureConfig from various sources.

  - ``PlotlyFigureSpecBuilder`` — extract spec from Plotly figure + config dict
  - ``PresetSpecBuilder`` — build spec from a LaTeXPreset (journal template)
  - ``ConfigSpecBuilder`` — build spec from a flat config dict (UI widgets)

These replace:
  - ``LayoutExtractor.extract_layout()`` (Plotly → raw dict)
  - ``LayoutApplier._build_*_config()`` methods (LaTeXPreset → dataclasses)
"""

from __future__ import annotations

from typing import Any, Literal

import plotly.graph_objects as go

from src.core.models.visualization.annotation_config import (
    AnnotationConfig,
    ReferenceLineConfig,
)
from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
    MarginsConfig,
    SeparatorConfig,
)
from src.core.models.visualization.legend_config import (
    LegendConfig,
    LegendSpacingConfig,
)
from src.core.models.visualization.palettes import resolve_palette
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.typography_config import TypographyConfig


class PlotlyFigureSpecBuilder:
    """Build a FigureConfig by extracting state from a Plotly figure + config.

    This is what ``LayoutExtractor`` currently does, but producing a typed
    ``FigureConfig`` instead of a raw dictionary.

    Usage:
        spec = PlotlyFigureSpecBuilder.from_plotly(fig, config)
    """

    @staticmethod
    def from_plotly(
        fig: go.Figure,
        config: dict[str, Any],
    ) -> FigureConfig:
        """Extract a FigureConfig from an existing Plotly figure and config.

        Args:
            fig: A ``plotly.graph_objects.Figure``.
            config: The plot config dict (``BasePlot.config``).

        Returns:
            A FigureConfig populated from the figure's current state.
            May contain sentinel values (-1) for fields not set.
        """
        layout: Any = fig.layout if hasattr(fig, "layout") else {}

        # ── Dimensions ───────────────────────────────────────────
        margins = _extract_margins(layout)
        dims = DimensionConfig(
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
        paper_bg = getattr(layout, "paper_bgcolor", None) or config.get("paper_bgcolor", "white")
        plot_bg = getattr(layout, "plot_bgcolor", None) or config.get("plot_bgcolor", "white")

        return FigureConfig(
            dimensions=dims,
            typography=typo,
            axes=axes,
            legends=legends,
            annotations=annotations,
            title=title,
            paper_bgcolor=paper_bg,
            plot_bgcolor=plot_bg,
        )

    @staticmethod
    def enrich_from_plotly(spec: FigureConfig, fig: go.Figure) -> None:
        """Merge layout metadata from a Plotly figure into an existing spec.

        Transfers computed layout data (tick positions/labels, annotations,
        legend3 items) that ``ConfigSpecBuilder.from_config()`` cannot
        capture because the data is set programmatically in
        ``create_figure()`` methods rather than stored in the config dict.

        Modifies *spec* in place.

        Args:
            spec: An already-built FigureConfig (typically from config).
            fig: A ``plotly.graph_objects.Figure`` with finalised layout.
        """
        layout: Any = fig.layout if hasattr(fig, "layout") else None
        if layout is None:
            return

        # ── Tick positions / labels ─────────────────────────────
        xaxis = getattr(layout, "xaxis", None)
        if xaxis is not None:
            tv = getattr(xaxis, "tickvals", None)
            tt = getattr(xaxis, "ticktext", None)
            if tv is not None:
                raw = tv.tolist() if hasattr(tv, "tolist") else list(tv)
                spec.axes.x.tick_values = raw
            if tt is not None:
                raw_t = tt.tolist() if hasattr(tt, "tolist") else list(tt)
                spec.axes.x.tick_text = [str(t) for t in raw_t]

        yaxis = getattr(layout, "yaxis", None)
        if yaxis is not None:
            tv = getattr(yaxis, "tickvals", None)
            tt = getattr(yaxis, "ticktext", None)
            if tv is not None:
                raw = tv.tolist() if hasattr(tv, "tolist") else list(tv)
                spec.axes.y.tick_values = raw
            if tt is not None:
                raw_t = tt.tolist() if hasattr(tt, "tolist") else list(tt)
                spec.axes.y.tick_text = [str(t) for t in raw_t]

        # ── Annotations ─────────────────────────────────────────
        # Only merge if spec has none (avoid duplicating config-based ones)
        if not spec.annotations:
            spec.annotations = _extract_annotations(layout)

        # ── Barmode ─────────────────────────────────────────────
        plotly_barmode = getattr(layout, "barmode", None)
        if plotly_barmode is not None:
            barmode_str = str(plotly_barmode)
            if barmode_str in ("group", "stack", "overlay", "relative"):
                spec.barmode = barmode_str  # type: ignore[assignment]

        # ── Legend3 (boxed legend items) ─────────────────────────
        legend3 = getattr(layout, "legend3", None)
        if legend3 is not None:
            from src.core.models.visualization.legend_config import LegendConfig

            box_kwargs: dict[str, Any] = {"role": "boxed"}
            x = getattr(legend3, "x", None)
            y = getattr(legend3, "y", None)
            if x is not None:
                box_kwargs["position_x"] = float(x)
                box_kwargs["custom_position"] = True
            if y is not None:
                box_kwargs["position_y"] = float(y)
            xanchor = getattr(legend3, "xanchor", None)
            if xanchor:
                box_kwargs["anchor_x"] = xanchor
            yanchor = getattr(legend3, "yanchor", None)
            if yanchor:
                box_kwargs["anchor_y"] = yanchor
            spec.legends.append(LegendConfig(**box_kwargs))


class PresetSpecBuilder:
    """Build a FigureConfig from a LaTeXPreset (journal template).

    This replaces the 4 builder methods in ``LayoutApplier``:
      - ``_build_font_config()``
      - ``_build_positioning_config()``
      - ``_build_separator_config()``
      - ``_build_legend_spacing_config()``

    Usage:
        spec = PresetSpecBuilder.from_preset(preset)
    """

    @staticmethod
    def from_preset(preset: dict[str, Any]) -> FigureConfig:
        """Build a FigureConfig from a LaTeXPreset dictionary.

        Args:
            preset: A ``LaTeXPreset`` TypedDict (or compatible dict).

        Returns:
            A FigureConfig populated from the preset values.
        """
        # ── Dimensions ───────────────────────────────────────────
        dims = DimensionConfig(
            width=preset.get("width_inches", 7.0),
            height=preset.get("height_inches", 4.0),
            dpi=preset.get("dpi", 300),
            bar_width_scale=preset.get("bar_width_scale", 1.0),
        )

        # ── Typography ───────────────────────────────────────────
        typo = TypographyConfig(
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
        x_axis = AxisConfig(
            tick_angle=preset.get("xtick_rotation", 45.0),
            tick_pad=preset.get("xtick_pad", 5.0),
            tick_ha=preset.get("xtick_ha", "right"),
            tick_offset=preset.get("xtick_offset", 0.0),
            margin=preset.get("xaxis_margin", 0.02),
            show_ticks=preset.get("show_xtick_marks", True),
            tick_dash=preset.get("xtick_dash", "solid"),
        )
        y_axis = AxisConfig(
            label_pad=preset.get("ylabel_pad", 10.0),
            label_position=preset.get("ylabel_y_position", 0.5),
            tick_pad=preset.get("ytick_pad", 5.0),
            show_ticks=preset.get("show_ytick_marks", True),
            tick_dash=preset.get("ytick_dash", "solid"),
        )

        axes = AxesConfig(
            x=x_axis,
            y=y_axis,
            group_label_offset=preset.get("group_label_offset", -0.12),
            group_label_alternate=preset.get("group_label_alternate", True),
            group_label_alt_spacing=preset.get("group_label_alt_spacing", 0.05),
        )

        # ── Legends ──────────────────────────────────────────────
        primary_spacing = LegendSpacingConfig(
            columnspacing=preset.get("legend_columnspacing", 0.5),
            handletextpad=preset.get("legend_handletextpad", 0.3),
            labelspacing=preset.get("legend_labelspacing", 0.2),
            handlelength=preset.get("legend_handlelength", 1.0),
            handleheight=preset.get("legend_handleheight", 0.7),
            borderpad=preset.get("legend_borderpad", 0.2),
            borderaxespad=preset.get("legend_borderaxespad", 0.5),
        )
        primary_legend = LegendConfig(
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
        legend2_spacing = LegendSpacingConfig(
            columnspacing=preset.get("legend2_columnspacing", -1.0),
            handletextpad=preset.get("legend2_handletextpad", -1.0),
            labelspacing=preset.get("legend2_labelspacing", -1.0),
            handlelength=preset.get("legend2_handlelength", -1.0),
            handleheight=preset.get("legend2_handleheight", -1.0),
            borderpad=preset.get("legend2_borderpad", -1.0),
            borderaxespad=preset.get("legend2_borderaxespad", -1.0),
        )
        legend2 = LegendConfig(
            role="secondary",
            font_size=preset.get("font_size_legend2", -1),
            bold=preset.get("bold_legend2", False),
            ncol=preset.get("legend2_ncol", -1),
            spacing=legend2_spacing,
        )

        # Boxed annotation legend (legend3)
        legend3_spacing = LegendSpacingConfig(
            borderpad=preset.get("legend3_borderpad", -1.0),
            labelspacing=preset.get("legend3_labelspacing", -1.0),
        )
        legend3 = LegendConfig(
            role="boxed",
            font_size=preset.get("font_size_legend3", -1),
            bold=preset.get("bold_legend3", False),
            number_fontsize=preset.get("legend3_number_fontsize", -1),
            text_fontsize=preset.get("legend3_text_fontsize", -1),
            spacing=legend3_spacing,
        )

        legends = [primary_legend, legend2, legend3]

        # ── Separator ────────────────────────────────────────────
        separator = SeparatorConfig(
            enabled=preset.get("group_separator", False),
            style=preset.get("group_separator_style", "dash"),
            color=preset.get("group_separator_color", "gray"),
        )

        return FigureConfig(
            dimensions=dims,
            typography=typo,
            axes=axes,
            legends=legends,
            separator=separator,
            font_family=preset.get("font_family", "serif"),
            latex_extra_preamble=preset.get("latex_extra_preamble", ""),
        )


class ConfigSpecBuilder:
    """Build a FigureConfig from a flat config dict (UI widget values).

    This is the **config → spec** bridge: produces a typed, engine-agnostic
    ``FigureConfig`` from the ``Dict[str, Any]`` that UI widgets produce.

    Key design choice: ``dpi`` is set to ``1`` so that pixel values stored
    in the config dict (``width=800``, ``height=500``) round-trip through
    FigureConfig (which stores inches) without loss: ``800 / 1 = 800`` and
    ``800 * 1 = 800``.

    Usage:
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        resolved = resolve_config(spec)
    """

    @staticmethod
    def from_config(
        config: dict[str, Any],
        plot_type: str = "",
    ) -> FigureConfig:
        """Build a FigureConfig from a flat config dictionary.

        Args:
            config: The ``BasePlot.config`` dict produced by UI widgets.
            plot_type: Plot type string for bar-specific defaults.

        Returns:
            A FigureConfig populated from config values.
            Uses ``dpi=1`` so width/height are effectively in pixels.
        """
        is_bar = "bar" in plot_type

        # ── Dimensions (dpi=1 ⇒ px passthrough) ─────────────────
        margins = MarginsConfig(
            top=float(config.get("margin_t", 80)),
            bottom=float(config.get("margin_b", 120)),
            left=float(config.get("margin_l", 100)),
            right=float(config.get("margin_r", 100)),
            pad=float(config.get("margin_pad", 0)),
        )
        dims = DimensionConfig(
            width=float(config.get("width", 800)),
            height=float(config.get("height", 500)),
            dpi=1,  # px passthrough — no conversion
            margins=margins,
            bargap=config.get("bargap", 0.2) if is_bar else 0.0,
            bargroupgap=config.get("bargroupgap", 0.0) if "grouped" in plot_type else 0.0,
        )

        # ── Typography ───────────────────────────────────────────
        typo = TypographyConfig(
            font_size_title=config.get("title_font_size", 18),
            font_size_xlabel=config.get("xaxis_title_font_size", 14),
            font_size_ylabel=config.get("yaxis_title_font_size", 14),
            font_size_ticks=config.get("xaxis_tickfont_size", 12),
            font_size_yticks=config.get("yaxis_tickfont_size", 12),
            font_size_legend=config.get("legend_font_size", 12),
            font_size_annotations=config.get("text_font_size", 12),
        )

        # ── Axes ─────────────────────────────────────────────────
        x_label = str(config.get("xlabel") or config.get("xaxis_title") or "").replace(
            "undefined", ""
        )
        y_label = str(config.get("ylabel") or config.get("yaxis_title") or "").replace(
            "undefined", ""
        )

        x_axis = AxisConfig(
            label=x_label,
            tick_angle=float(config.get("xaxis_tickangle", -45)),
            range=config.get("range_x"),
            category_order=config.get("xaxis_order"),
            label_aliases=config.get("xaxis_labels"),
            automargin=config.get("automargin", True),
            grid_color=config.get("grid_color", "#E5E5E5"),
            show_ticks=config.get("show_xtick_marks", True),
            tick_dash=config.get("xtick_dash", "solid"),
        )
        y_axis = AxisConfig(
            label=y_label,
            range=config.get("range_y"),
            dtick=config.get("yaxis_dtick"),
            automargin=config.get("automargin", True),
            grid_color=config.get("grid_color", "#E5E5E5"),
            label_standoff=config.get("yaxis_title_standoff", -1),
            title_vshift=float(config.get("yaxis_title_vshift", 0.0)),
            show_ticks=config.get("show_ytick_marks", True),
            tick_dash=config.get("ytick_dash", "solid"),
        )

        axes = AxesConfig(x=x_axis, y=y_axis)

        # ── Primary Legend ───────────────────────────────────────
        legend_orient = config.get("legend_orientation", "v")
        primary_legend = LegendConfig(
            role="primary",
            font_size=config.get("legend_font_size", 12),
            font_color=config.get("legend_font_color", "#444"),
            title=config.get("legend_title", ""),
            title_font_size=config.get("legend_title_font_size", 14),
            title_font_color=config.get("legend_title_font_color", "#000000"),
            orientation="horizontal" if legend_orient == "h" else "vertical",
            position_x=float(config.get("legend_x", 1.02)),
            position_y=float(config.get("legend_y", 1.0)),
            anchor_x=config.get("legend_xanchor", "auto"),
            anchor_y=config.get("legend_yanchor", "auto"),
            custom_position=True,
            visible=True,
            bgcolor=config.get("legend_bgcolor", ""),
            border_width=config.get("legend_border_width", 0),
            border_color=config.get("legend_border_color", "#000000"),
            itemsizing=config.get("legend_itemsizing", "constant"),
        )

        legends: list[LegendConfig] = [primary_legend]

        # ── Multi-column secondary legends (if ncols > 1) ───────
        try:
            ncols = int(config.get("legend_ncols") or 0)
        except (ValueError, TypeError):
            ncols = 0

        for col_idx in range(1, ncols):
            key_prefix = f"legend{col_idx + 1}"
            sec = LegendConfig(
                role="secondary",
                font_size=primary_legend.font_size,
                font_color=primary_legend.font_color,
                position_x=float(config.get(f"{key_prefix}_x", -1)),
                position_y=float(config.get(f"{key_prefix}_y", -1)),
                anchor_x=config.get(f"{key_prefix}_xanchor", "auto"),
                anchor_y=config.get(f"{key_prefix}_yanchor", "auto"),
                custom_position=True,
                bgcolor=primary_legend.bgcolor,
            )
            legends.append(sec)

        # ── Backgrounds ──────────────────────────────────────────
        paper_bg = config.get("paper_bgcolor", "white")
        plot_bg = config.get("plot_bgcolor", "white")

        # ── Title ────────────────────────────────────────────────
        title = str(config.get("title") or "").replace("undefined", "")

        # ── Data labels ──────────────────────────────────────────
        data_labels: DataLabelConfig | None = None
        if config.get("show_values"):
            try:
                dl_font_size = int(config.get("text_font_size") or 12)
            except (ValueError, TypeError):
                dl_font_size = 12
            try:
                dl_rotation = int(config.get("text_rotation") or 0)
            except (ValueError, TypeError):
                dl_rotation = 0

            # Normalize color mode to lowercase for Literal match
            raw_color_mode_str = str(config.get("text_color_mode", "auto")).lower()
            if raw_color_mode_str not in ("auto", "contrast", "custom"):
                raw_color_mode_str = "auto"
            raw_color_mode: Literal["auto", "contrast", "custom"] = (
                raw_color_mode_str  # type: ignore[assignment]
            )

            # Position validation
            raw_position = config.get("text_position", "auto")
            valid_positions = ("auto", "inside", "outside")
            if raw_position not in valid_positions:
                raw_position = "auto"

            # Anchor validation
            raw_anchor = config.get("text_anchor", "auto")
            valid_anchors = ("auto", "top", "middle", "bottom")
            if raw_anchor not in valid_anchors:
                raw_anchor = "auto"

            # Constraint mapping: bool config → Literal
            constraint_raw = config.get("text_constraint", False)
            size_constraint: Literal["none", "inside"] = "inside" if constraint_raw else "none"

            data_labels = DataLabelConfig(
                enabled=True,
                color_mode=raw_color_mode,
                custom_color=config.get("text_color", "#000000"),
                font_size=dl_font_size,
                rotation=dl_rotation,
                position=raw_position,
                anchor=raw_anchor,
                format_string=config.get("text_format", ".2f"),
                size_constraint=size_constraint,
            )

        # ── Reference lines ─────────────────────────────────────
        reference_lines: list[ReferenceLineConfig] = []
        if config.get("reference_line_enabled"):
            rl = ReferenceLineConfig(
                enabled=True,
                axis="y",
                value=float(config.get("reference_line_y", 0.0)),
                color=config.get("reference_line_color", "red"),
                width=float(config.get("reference_line_width", 1.5)),
                style=config.get("reference_line_style", "dash"),
                label=config.get("reference_line_label", ""),
            )
            reference_lines.append(rl)

        # ── Series styling (global defaults) ─────────────────────
        series_styles: list[SeriesStyleConfig] = []
        has_series = any(
            config.get(k) is not None for k in ("bar_border_width", "marker_size", "line_width")
        )
        if has_series:
            series_styles.append(
                SeriesStyleConfig(
                    bar_border_width=float(config.get("bar_border_width", 0.0)),
                    marker_size=int(config.get("marker_size") or 6),
                    line_width=float(config.get("line_width") or 2.0),
                )
            )

        # ── Per-trace overrides from UI series_styles dict ───────
        trace_overrides: dict[str, SeriesStyleConfig] = {}
        raw_overrides: dict[str, Any] = config.get("series_styles", {})
        for trace_name_raw, style_dict_raw in raw_overrides.items():
            if not isinstance(style_dict_raw, dict):
                continue
            t_name: str = str(trace_name_raw)
            sd: dict[str, Any] = style_dict_raw  # type: ignore[assignment]
            trace_overrides[t_name] = SeriesStyleConfig(
                color=(str(sd["color"]) if sd.get("use_color") and sd.get("color") else ""),
                symbol=str(sd.get("symbol", "")),
                display_name=str(sd.get("name", "")),
                marker_size=int(sd.get("marker_size") or 0),
                line_width=float(sd.get("line_width") or 0.0),
                hatching_pattern=str(sd.get("pattern", "")),
            )

        # ── Color palette (resolve name → hex list) ─────────────
        color_palette = resolve_palette(config.get("color_palette"))

        # ── Scalar feature flags ─────────────────────────────────
        show_error_bars = bool(config.get("show_error_bars", False))
        enable_stripes = bool(config.get("enable_stripes", False))
        hovermode = config.get("hovermode", "x unified")

        # ── Bar mode ────────────────────────────────────────────
        barmode_raw_str = str(config.get("barmode", "group")).lower()
        if barmode_raw_str not in ("group", "stack", "overlay", "relative"):
            barmode_raw_str = "group"
        barmode_raw: Literal[
            "group", "stack", "overlay", "relative"
        ] = barmode_raw_str  # type: ignore[assignment]

        return FigureConfig(
            dimensions=dims,
            typography=typo,
            axes=axes,
            legends=legends,
            title=title,
            paper_bgcolor=paper_bg,
            plot_bgcolor=plot_bg,
            data_labels=data_labels,
            reference_lines=reference_lines,
            series_styles=series_styles,
            trace_overrides=trace_overrides,
            color_palette=color_palette,
            show_error_bars=show_error_bars,
            enable_stripes=enable_stripes,
            hovermode=hovermode,
            barmode=barmode_raw,
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


def _extract_margins(layout: Any) -> MarginsConfig:
    """Extract margins from Plotly layout."""
    margin = getattr(layout, "margin", None)
    if margin is None:
        return MarginsConfig()
    return MarginsConfig(
        top=float(getattr(margin, "t", 40) or 40),
        bottom=float(getattr(margin, "b", 80) or 80),
        left=float(getattr(margin, "l", 60) or 60),
        right=float(getattr(margin, "r", 30) or 30),
        pad=float(getattr(margin, "pad", 0) or 0),
    )


def _extract_typography(layout: Any, config: dict[str, Any]) -> TypographyConfig:
    """Extract typography settings from Plotly layout and config."""
    # Plotly stores font sizes in various places; config dict is primary
    return TypographyConfig(
        font_size_title=config.get("title_font_size", 10),
        font_size_xlabel=config.get("xaxis_title_font_size", 9),
        font_size_ylabel=config.get("yaxis_title_font_size", 9),
        font_size_ticks=config.get("xaxis_tickfont_size", 7),
        font_size_yticks=config.get("yaxis_tickfont_size", 7),
        font_size_legend=config.get("legend_font_size", 8),
        font_size_annotations=config.get("text_font_size", 6),
    )


def _extract_axes(layout: Any, config: dict[str, Any]) -> AxesConfig:
    """Extract axis configuration from Plotly layout."""
    xaxis = getattr(layout, "xaxis", None)
    yaxis = getattr(layout, "yaxis", None)
    yaxis2 = getattr(layout, "yaxis2", None)

    x = AxisConfig(
        label=config.get("xlabel", "") or _get_axis_title(xaxis),
        tick_angle=float(config.get("xaxis_tickangle", 0)),
        range=config.get("range_x"),
        category_order=config.get("xaxis_order"),
        label_aliases=config.get("xaxis_labels"),
        show_grid=config.get("show_grid", True),
    )

    y = AxisConfig(
        label=config.get("ylabel", "") or _get_axis_title(yaxis),
        range=config.get("range_y"),
        dtick=config.get("yaxis_dtick"),
        show_grid=config.get("show_grid", True),
    )

    y2: AxisConfig | None = None
    if yaxis2 is not None:
        y2 = AxisConfig(
            label=_get_axis_title(yaxis2),
            range=_get_range(yaxis2),
        )

    return AxesConfig(x=x, y=y, y2=y2)


def _extract_legends(layout: Any, config: dict[str, Any]) -> list[LegendConfig]:
    """Extract legend configurations from Plotly layout."""
    legends: list[LegendConfig] = []

    legend = getattr(layout, "legend", None)
    primary = LegendConfig(
        role="primary",
        font_size=config.get("legend_font_size", 8),
        font_color=config.get("legend_font_color", "#444"),
        orientation=("horizontal" if config.get("legend_orientation") == "h" else "vertical"),
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
        sec = LegendConfig(role="secondary")
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


def _extract_annotations(layout: Any) -> list[AnnotationConfig]:
    """Extract annotation objects from Plotly layout."""
    annotations: list[AnnotationConfig] = []
    layout_anns: list[Any] = list(getattr(layout, "annotations", None) or [])

    for ann in layout_anns:
        font = getattr(ann, "font", None)
        spec = AnnotationConfig(
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


def _get_range(axis: Any) -> list[float] | None:
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
