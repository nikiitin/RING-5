"""
Bidirectional builders — construct FigureConfig from various sources.

  - ``PlotlyFigureSpecBuilder`` — extract spec from Plotly figure + config dict
  - ``ConfigSpecBuilder`` — build spec from a flat config dict (UI widgets)
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
)
from src.core.models.visualization.legend_config import (
    ColorbarConfig,
    LegendConfig,
    LegendSpacingConfig,
)
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.typography_config import TypographyConfig
from src.core.services.visualization.palette_service import resolve_palette


def should_show_x_tick_labels(config: dict[str, Any]) -> bool:
    """Whether x-axis tick LABELS are shown — the single rule shared by the mpl
    (``ConfigSpecBuilder.from_config``) and plotly (``grouped_stacked_bar``) paths so they
    can't drift.

    With the ``numbered_xaxis_modes`` multiselect, labels show iff "Numbers" or "Labels" is
    selected (a sole "Number legend" hides them). The legacy ``numbered_xaxis`` boolean
    hides labels unless ``show_numbered_ticks`` is set.
    """
    modes = config.get("numbered_xaxis_modes")
    if modes:
        return "Numbers" in modes or "Labels" in modes
    if config.get("numbered_xaxis") and not config.get("show_numbered_ticks", False):
        return False
    return bool(config.get("show_x_tick_labels", True))


class PlotlyFigureSpecBuilder:
    """Enrich a FigureConfig with metadata that only exists on a *styled* Plotly figure.

    The spec itself is built by :class:`ConfigSpecBuilder` from the flat config dict; this
    class supplies the one piece that isn't in the config — layout state computed inside
    ``create_figure`` (tick vals/labels, annotations, barmode, legend3) — via
    :meth:`enrich_from_plotly`. (The engine-agnostic counterpart is
    :func:`enrich_from_traces`, used by the matplotlib path.)
    """

    @staticmethod
    def enrich_from_plotly(spec: FigureConfig, fig: go.Figure) -> None:
        """Merge layout metadata from a Plotly figure into an existing spec.

        Transfers computed layout data (tick positions/labels, annotations,
        legend3 items) that ``ConfigSpecBuilder.from_config()`` cannot
        capture because the data is set programmatically in
        ``create_figure()`` methods rather than stored in the config dict.

        Modifies *spec* in place. The FigureConfig tree is frozen, but this
        method is only ever handed a freshly-built, caller-owned spec (see
        ``ChartDisplayComponent`` — built, enriched, then resolved), so the
        in-place fill via ``object.__setattr__`` is private to that build step.
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
                object.__setattr__(spec.axes.x, "tick_values", raw)
            if tt is not None:
                raw_t = tt.tolist() if hasattr(tt, "tolist") else list(tt)
                object.__setattr__(spec.axes.x, "tick_text", [str(t) for t in raw_t])

        yaxis = getattr(layout, "yaxis", None)
        if yaxis is not None:
            tv = getattr(yaxis, "tickvals", None)
            tt = getattr(yaxis, "ticktext", None)
            if tv is not None:
                raw = tv.tolist() if hasattr(tv, "tolist") else list(tv)
                object.__setattr__(spec.axes.y, "tick_values", raw)
            if tt is not None:
                raw_t = tt.tolist() if hasattr(tt, "tolist") else list(tt)
                object.__setattr__(spec.axes.y, "tick_text", [str(t) for t in raw_t])

        # ── Annotations ─────────────────────────────────────────
        # Only merge if spec has none (avoid duplicating config-based ones)
        if not spec.annotations:
            object.__setattr__(spec, "annotations", _extract_annotations(layout))

        # ── Barmode ─────────────────────────────────────────────
        plotly_barmode = getattr(layout, "barmode", None)
        if plotly_barmode is not None:
            barmode_str = str(plotly_barmode)
            if barmode_str in ("group", "stack", "overlay", "relative"):
                object.__setattr__(spec, "barmode", barmode_str)

        # ── Legend3 (tertiary legend items) ─────────────────────────
        legend3 = getattr(layout, "legend3", None)
        if legend3 is not None:
            from src.core.models.visualization.legend_config import LegendConfig

            box_kwargs: dict[str, Any] = {"role": "tertiary"}
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
        )

        # ── Axes ─────────────────────────────────────────────────
        x_label = str(config.get("xlabel") or config.get("xaxis_title") or "").replace(
            "undefined", ""
        )
        y_label = str(config.get("ylabel") or config.get("yaxis_title") or "").replace(
            "undefined", ""
        )

        # Determine X-axis tick label visibility (shared rule — see should_show_x_tick_labels).
        _show_x_tick_labels: bool = should_show_x_tick_labels(config)
        _numbered_modes: list[str] = config.get("numbered_xaxis_modes", [])

        # When numbered x-axis "Numbers" mode is active, short numeric labels
        # don't need rotation — override angle to 0 for readability.
        _x_tick_angle = float(config.get("xaxis_tickangle", -45))
        if _numbered_modes and "Numbers" in _numbered_modes:
            _x_tick_angle = 0.0

        x_axis = AxisConfig(
            label=x_label,
            tick_angle=_x_tick_angle,
            range=config.get("range_x"),
            category_order=config.get("xaxis_order"),
            label_aliases=config.get("xaxis_labels"),
            automargin=config.get("automargin", True),
            show_grid=config.get("show_x_grid", True),
            grid_color=config.get("x_grid_color", config.get("grid_color", "#E5E5E5")),
            grid_width=float(config.get("x_grid_width", 1.0)),
            grid_dash=config.get("x_grid_dash", "solid"),
            grid_alpha=float(config.get("x_grid_alpha", 1.0)),
            show_ticks=config.get("show_xtick_marks", True),
            show_tick_labels=_show_x_tick_labels,
            tick_dash=config.get("xtick_dash", "solid"),
            tick_font_color=config.get("xaxis_tickfont_color", ""),
            tick_pad=float(config.get("xtick_pad", 5.0)),
            tick_side=config.get("xaxis_tick_side", ""),
            axis_color=config.get("axis_color", "#444"),
            axis_line_color=config.get("x_axis_line_color", ""),
            axis_line_width=float(config.get("x_axis_line_width", 1.0)),
        )
        y_axis = AxisConfig(
            label=y_label,
            tick_angle=float(config.get("yaxis_tickangle", 0)),
            range=config.get("range_y"),
            dtick=config.get("yaxis_dtick"),
            automargin=config.get("automargin", True),
            show_grid=config.get("show_y_grid", True),
            grid_color=config.get("y_grid_color", config.get("grid_color", "#E5E5E5")),
            grid_width=float(config.get("y_grid_width", 1.0)),
            grid_dash=config.get("y_grid_dash", "solid"),
            grid_alpha=float(config.get("y_grid_alpha", 1.0)),
            label_standoff=config.get("yaxis_title_standoff", -1),
            title_vshift=float(config.get("yaxis_title_vshift", 0.0)),
            show_ticks=config.get("show_ytick_marks", True),
            tick_dash=config.get("ytick_dash", "solid"),
            tick_font_color=config.get("yaxis_tickfont_color", ""),
            tick_side=config.get("yaxis_tick_side", ""),
            axis_color=config.get("axis_color", "#444"),
            axis_line_color=config.get("y_axis_line_color", ""),
            axis_line_width=float(config.get("y_axis_line_width", 1.0)),
        )

        axes = AxesConfig(
            x=x_axis,
            y=y_axis,
            group_label_alternate=config.get("group_label_alternate", True),
            group_label_alt_spacing=float(config.get("group_label_alt_spacing", 0.05)),
            group_label_offset=float(config.get("group_label_offset", -0.12)),
            top_axis_line_width=float(config.get("top_axis_line_width", 0.0)),
            top_axis_line_color=config.get("top_axis_line_color", "#444"),
            right_axis_line_width=float(config.get("right_axis_line_width", 0.0)),
            right_axis_line_color=config.get("right_axis_line_color", "#444"),
        )

        # ── Primary Legend ───────────────────────────────────────
        primary_legend = _build_legend_from_config(config, "legend_", "primary")
        legends: list[LegendConfig] = [primary_legend]

        # ── Secondary legend from UI (dual-axis) ────────────────
        if any(config.get(f"legend2_{k}") is not None for k in ("font_size", "x", "ncols")):
            legends.append(_build_legend_from_config(config, "legend2_", "secondary"))

        # ── Boxed legend from UI ─────────────────────────────────
        if any(config.get(f"legend3_{k}") is not None for k in ("font_size", "x", "ncols")):
            legends.append(_build_legend_from_config(config, "legend3_", "tertiary"))

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
            # Carry ONLY explicitly-set values; leave the rest 0 so the per-trace
            # styling step skips them (it treats 0 as "unset"). Hard defaults here
            # (e.g. line_width=2.0) would otherwise be stamped onto every trace —
            # clobbering a dual-axis line's own width / a plot type's marker size.
            series_styles.append(
                SeriesStyleConfig(
                    bar_border_width=float(config.get("bar_border_width") or 0.0),
                    bar_border_color=str(config.get("bar_border_color", "")),
                    marker_size=int(config["marker_size"]) if config.get("marker_size") else 0,
                    line_width=float(config["line_width"]) if config.get("line_width") else 0.0,
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
# Helper: build LegendConfig from prefixed config keys
# ────────────────────────────────────────────────────────────────────


def _build_legend_from_config(
    config: dict[str, Any],
    prefix: str,
    role: str,
) -> LegendConfig:
    """Build a LegendConfig from a flat config dict with the given key prefix.

    Args:
        config: Flat configuration dictionary from UI widgets.
        prefix: Key prefix, e.g. ``"legend_"``, ``"legend2_"``, ``"legend3_"``.
        role: Semantic role — ``"primary"``, ``"secondary"``, or ``"tertiary"``.

    Returns:
        Fully populated LegendConfig.
    """
    tracegroupgap_px = int(config.get(f"{prefix}tracegroupgap", 10))
    font_size = int(config.get(f"{prefix}font_size", 12))
    # Convert tracegroupgap (Plotly px) → labelspacing (Matplotlib, in
    # multiples of font size).  Clamp to sensible range.
    label_spacing = max(0.0, tracegroupgap_px / max(font_size, 1))

    # Convert itemwidth (px) → handlelength (font-size multiples) for
    # Matplotlib.  When 0, fall back to default handlelength.
    itemwidth_px = int(config.get(f"{prefix}itemwidth", 30))
    handlelength = float(itemwidth_px) / max(font_size, 1) if itemwidth_px > 0 else 1.0

    spacing = LegendSpacingConfig(
        columnspacing=float(config.get(f"{prefix}column_spacing", 0.5)),
        handletextpad=float(config.get(f"{prefix}handletextpad", 0.3)),
        labelspacing=label_spacing,
        handlelength=handlelength,
    )
    # All legends inherit the global font_family; primary uses the global
    # config key, secondary/tertiary fall back to the same value.
    font_family: str = config.get("font_family", "")

    # Colorbar settings (heatmap-specific, stored on legend for config flow)
    range_mode_raw = str(config.get(f"{prefix}colorbar_range_mode", "auto")).lower()
    if range_mode_raw not in ("auto", "manual"):
        range_mode_raw = "auto"
    colorbar = ColorbarConfig(
        range_mode=range_mode_raw,  # type: ignore[arg-type]
        zmin=config.get(f"{prefix}colorbar_zmin"),
        zmax=config.get(f"{prefix}colorbar_zmax"),
        nticks=int(config.get(f"{prefix}colorbar_nticks", 5)),
        tick_decimals=int(config.get(f"{prefix}colorbar_tick_decimals", 2)),
        shared=bool(config.get(f"{prefix}colorbar_shared", True)),
        tick_angle=float(config.get(f"{prefix}colorbar_tick_angle", 0.0)),
        tick_side=config.get(f"{prefix}colorbar_tick_side", "right"),
    )

    # Orientation (horizontal / vertical)
    _orient_raw = str(config.get(f"{prefix}orientation", "vertical")).lower()
    if _orient_raw not in ("horizontal", "vertical"):
        _orient_raw = "vertical"

    # Position and anchor derivation
    pos_x = float(config.get(f"{prefix}x", 1.02 if role == "primary" else -1.0))
    pos_y = float(config.get(f"{prefix}y", 1.0 if role == "primary" else -1.0))

    raw_anchor_x = config.get(f"{prefix}anchor_x", "auto")
    raw_anchor_y = config.get(f"{prefix}anchor_y", "auto")

    if raw_anchor_x == "auto" and raw_anchor_y == "auto" and pos_x >= 0 and pos_y >= 0:
        anchor_x, anchor_y = LegendConfig.derive_anchors(pos_x, pos_y)
    else:
        anchor_x, anchor_y = raw_anchor_x, raw_anchor_y

    return LegendConfig(
        role=role,  # type: ignore[arg-type]
        font_size=font_size,
        font_family=font_family,
        font_color=config.get(f"{prefix}font_color", "#444"),
        title=config.get(f"{prefix}title", ""),
        title_font_size=config.get(f"{prefix}title_font_size", 14),
        title_font_color=config.get(f"{prefix}title_font_color", "#000000"),
        ncol=int(config.get(f"{prefix}ncols", 0)),
        position_x=pos_x,
        position_y=pos_y,
        col_width=float(config.get(f"{prefix}col_width", -1.0)),
        entrywidth=int(config.get(f"{prefix}entrywidth", 0)),
        itemwidth=int(config.get(f"{prefix}itemwidth", 30)),
        indentation=int(config.get(f"{prefix}indentation", 0)),
        custom_position=True,
        visible=True,
        bgcolor=config.get(f"{prefix}bgcolor", ""),
        bgalpha=float(config.get(f"{prefix}bgalpha", -1.0)),
        border_width=float(config.get(f"{prefix}border_width", 0)),
        border_color=config.get(f"{prefix}border_color", "#000000"),
        tracegroupgap=tracegroupgap_px,
        spacing=spacing,
        colorbar=colorbar,
        anchor_x=anchor_x,  # type: ignore[arg-type]
        anchor_y=anchor_y,  # type: ignore[arg-type]
        orientation=_orient_raw,  # type: ignore[arg-type]
    )


# ────────────────────────────────────────────────────────────────────
# Helper functions for PlotlyFigureSpecBuilder
# ────────────────────────────────────────────────────────────────────


def _extract_annotations(layout: Any) -> list[AnnotationConfig]:
    """Extract annotation objects from Plotly layout."""
    annotations: list[AnnotationConfig] = []
    layout_anns: list[Any] = list(getattr(layout, "annotations", None) or [])

    for ann in layout_anns:
        font = getattr(ann, "font", None)
        raw_x = getattr(ann, "x", 0)
        raw_y = getattr(ann, "y", 0)
        try:
            x_val: float | str = float(raw_x)
        except (ValueError, TypeError):
            x_val = str(raw_x) if raw_x is not None else 0.0
        try:
            y_val: float | str = float(raw_y)
        except (ValueError, TypeError):
            y_val = str(raw_y) if raw_y is not None else 0.0
        anchor_kwargs: dict[str, Any] = {}
        xanchor = getattr(ann, "xanchor", None)
        if xanchor:
            anchor_kwargs["xanchor"] = xanchor
        yanchor = getattr(ann, "yanchor", None)
        if yanchor:
            anchor_kwargs["yanchor"] = yanchor
        annotations.append(
            AnnotationConfig(
                text=getattr(ann, "text", ""),
                x=x_val,
                y=y_val,
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
                **anchor_kwargs,
            )
        )

    return annotations


def _annotation_from_dict(ann: dict[str, Any]) -> AnnotationConfig:
    """Build an ``AnnotationConfig`` from a raw layout-annotation dict.

    The engine-agnostic counterpart of :func:`_extract_annotations` (which reads the very
    same fields back off a Plotly annotation object). Kept field-for-field identical — and
    matching Plotly's "unset property is ``None``" semantics — so the direct matplotlib
    path produces the same spec as the old plotly-round-trip path, byte-for-byte.
    """
    raw_x = ann.get("x", 0)
    raw_y = ann.get("y", 0)
    try:
        x_val: float | str = float(raw_x)
    except (ValueError, TypeError):
        x_val = str(raw_x) if raw_x is not None else 0.0
    try:
        y_val: float | str = float(raw_y)
    except (ValueError, TypeError):
        y_val = str(raw_y) if raw_y is not None else 0.0

    # Plotly builds a Font object iff the "font" key is present (truthy even when empty);
    # absent/None font ⇒ the (-1, "#444") sentinels _extract_annotations uses.
    font = ann.get("font")
    if "font" in ann and font is not None:
        font_size = int((font.get("size") or 0))
        font_color = str(font.get("color") or "#444")
    else:
        font_size = -1
        font_color = "#444"

    anchor_kwargs: dict[str, Any] = {}
    xanchor = ann.get("xanchor")
    if xanchor:
        anchor_kwargs["xanchor"] = xanchor
    yanchor = ann.get("yanchor")
    if yanchor:
        anchor_kwargs["yanchor"] = yanchor

    return AnnotationConfig(
        text=ann.get("text", ""),
        x=x_val,
        y=y_val,
        xref="paper" if ann.get("xref", "") == "paper" else "data",
        yref="paper" if ann.get("yref", "") == "paper" else "data",
        show_arrow=bool(ann.get("showarrow", False)),
        font_size=font_size,
        font_color=font_color,
        text_angle=float(ann.get("textangle", 0) or 0),
        border_width=float(ann.get("borderwidth", 0) or 0),
        border_color=str(ann.get("bordercolor", "") or ""),
        border_pad=float(ann.get("borderpad", 0) or 0),
        bgcolor=str(ann.get("bgcolor", "") or ""),
        align=ann.get("align", "left") or "left",
        **anchor_kwargs,
    )


def enrich_from_traces(spec: FigureConfig, result: TraceBuildResult) -> None:
    """Fill *spec* from the engine-agnostic trace-build result — the Plotly-free twin of
    :meth:`PlotlyFigureSpecBuilder.enrich_from_plotly`.

    The matplotlib path uses this so it never has to construct a Plotly figure. It captures
    the same data ``enrich_from_plotly`` does — x-axis tick values/labels, barmode, and
    annotations — directly from ``TraceBuildResult`` (where ``create_traces`` already put
    them). ``legend3`` (tertiary legend) has no engine-agnostic source — it is produced
    only during Plotly styling — so it is intentionally not handled here; a plot that needs
    a programmatic legend3 must keep the Plotly-enriched build path. Modifies *spec* in
    place (a freshly-built, caller-owned spec, exactly like ``enrich_from_plotly``).
    """
    ticks = result.custom_x_ticks
    if ticks:
        vals = ticks.get("vals")
        if vals is not None:
            object.__setattr__(spec.axes.x, "tick_values", list(vals))
        text = ticks.get("text")
        if text is not None:
            object.__setattr__(spec.axes.x, "tick_text", [str(t) for t in text])

    barmode_str = str(result.barmode)
    if barmode_str in ("group", "stack", "overlay", "relative"):
        object.__setattr__(spec, "barmode", barmode_str)

    # Only merge if the spec has none (mirror enrich_from_plotly's guard). Order matches
    # traces_to_plotly: result.annotations first, then the raw layout_annotations.
    if not spec.annotations:
        anns: list[AnnotationConfig] = list(result.annotations)
        anns.extend(_annotation_from_dict(d) for d in result.layout_annotations)
        object.__setattr__(spec, "annotations", anns)


def build_figure_spec_dict(config: dict[str, Any], plot_type: str) -> dict[str, Any] | None:
    """Plot-config dict → serialized FigureConfig dict (portfolio enricher).

    The one canonical ``figure_spec_enricher`` for portfolio saves — used by
    the web portfolio page and the public ring5 package alike, so portfolios
    saved from either surface carry the same per-plot ``figure_spec`` block.
    """
    return ConfigSpecBuilder.from_config(config, plot_type).to_dict()
