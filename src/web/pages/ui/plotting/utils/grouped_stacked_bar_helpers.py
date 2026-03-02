"""Pure computation helpers for GroupedStackedBarPlot.

Extracted from GroupedStackedBarPlot to reduce class size.
All functions are stateless — no UI or Streamlit imports.
"""

import math
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.basedatatypes import BaseTraceType

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.web.pages.ui.plotting.utils import GroupedBarUtils


def get_ordered_categories_and_groups(
    data: pd.DataFrame, x_col: str, group_col: str, config: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Get ordered lists of categories and groups."""
    # Categories
    if config.get("xaxis_order"):
        xaxis_order_str = [str(x) for x in config["xaxis_order"]]
        ordered_cats = [c for c in xaxis_order_str if c in data[x_col].unique()]
        missing = [c for c in sorted(data[x_col].unique()) if c not in ordered_cats]
        ordered_cats.extend(missing)
    else:
        ordered_cats = sorted(data[x_col].unique())

    # Groups
    if config.get("group_order"):
        group_order_str = [str(g) for g in config["group_order"]]
        ordered_groups = [g for g in group_order_str if g in data[group_col].unique()]
        missing = [g for g in sorted(data[group_col].unique()) if g not in ordered_groups]
        ordered_groups.extend(missing)
    else:
        ordered_groups = sorted(data[group_col].unique())

    return ordered_cats, ordered_groups


def apply_renames(
    data: pd.DataFrame,
    x_col: str,
    group_col: str,
    categories: list[str],
    groups: list[str],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Apply renames to data and ordered lists."""
    # X-axis renames
    x_renames = config.get("xaxis_labels", {})
    if x_renames:
        data[x_col] = data[x_col].replace(x_renames)

    renamed_categories = [x_renames.get(cat, cat) for cat in categories]

    # Group renames
    group_renames = config.get("group_renames", {})
    if group_renames:
        data[group_col] = data[group_col].replace(group_renames)

    renamed_groups = [group_renames.get(grp, grp) for grp in groups]

    return data, renamed_categories, renamed_groups


def apply_numbered_xaxis(
    tick_text: list[str],
    config: dict[str, Any],
) -> tuple[list[str], dict[str, Any] | None]:
    """Replace tick labels with numbered indices and build legend annotation.

    Supports multiselect modes via ``config["numbered_xaxis_modes"]``:

    - **Numbers** — show numbered ticks (1, 2, 3…)
    - **Number legend** — show annotation box mapping numbers → labels
    - **Labels** — show original X-axis labels

    Combinations:

    - Numbers + Labels → ``"1. genome"``, ``"2. intruder"``
    - Numbers + Legend → numbered ticks + annotation box
    - All three → ``"1. genome"`` ticks + annotation box

    Falls back to old boolean ``config["numbered_xaxis"]`` for compat.

    Args:
        tick_text: Original tick label strings (may repeat across categories).
        config: Plot configuration dict.

    Returns:
        Tuple of (possibly-replaced tick_text, legend annotation dict or None).
    """
    # Determine active modes (new multiselect or old boolean)
    modes: list[str] = config.get("numbered_xaxis_modes", [])
    if not modes:
        # Backward compat: old boolean → legend-only (ticks hidden)
        if not config.get("numbered_xaxis"):
            return tick_text, None
        modes = ["Number legend"]
        if config.get("show_numbered_ticks", False):
            modes.append("Numbers")

    has_numbers: bool = "Numbers" in modes
    has_labels: bool = "Labels" in modes
    has_legend: bool = "Number legend" in modes

    # Unique groups preserving insertion order
    unique_groups: list[str] = list(dict.fromkeys(tick_text))

    # Build numbered tick labels — one per original tick position.
    label_to_num: dict[str, int] = {g: i + 1 for i, g in enumerate(unique_groups)}

    if has_numbers and has_labels:
        # Combined format: "1. genome"
        numbered_text = [f"{label_to_num.get(t, '')}. {t}" for t in tick_text]
    elif has_numbers:
        # Numbers only
        numbered_text = [str(label_to_num.get(t, "")) for t in tick_text]
    elif has_labels:
        # Original labels unchanged
        numbered_text = list(tick_text)
    else:
        # Only "Number legend" — hide tick text
        numbered_text = [""] * len(tick_text)

    # Build legend annotation only when "Number legend" is selected
    if not has_legend:
        return numbered_text, None

    # Build legend text — vertical list inside a bordered box
    legend_parts: list[str] = [f"{i + 1}. {g}" for i, g in enumerate(unique_groups)]

    # Determine prefix for numbered legend controls (secondary or tertiary pill)
    if config.get("dual_axis") and not config.get("unified_legend", True):
        _prefix = "legend3_"
    else:
        _prefix = "legend2_"

    # Column count: prefer legend pill's ncols, fall back to old config key
    max_cols: int = int(config.get(f"{_prefix}ncols", config.get("numbered_legend_columns", 1)))
    # Treat 0 (auto) as 1 for annotation text layout
    if max_cols <= 0:
        max_cols = 1
    if max_cols > 1:
        # Lay out items **column-wise** (top-to-bottom, then next column)
        n_items: int = len(legend_parts)
        n_rows: int = math.ceil(n_items / max_cols)

        col_widths: list[int] = []
        for col in range(max_cols):
            col_items = [
                legend_parts[col * n_rows + r] for r in range(n_rows) if col * n_rows + r < n_items
            ]
            col_widths.append(max(len(p) for p in col_items) if col_items else 0)

        # Use &nbsp; for padding — Plotly renders annotation text as HTML,
        # so regular spaces are collapsed.
        sep = "&nbsp;&nbsp;"
        rows: list[str] = []
        for row_idx in range(n_rows):
            parts: list[str] = []
            for col_idx in range(max_cols):
                item_idx = col_idx * n_rows + row_idx
                if item_idx < n_items:
                    raw = legend_parts[item_idx]
                    pad = col_widths[col_idx] - len(raw)
                    parts.append(raw + "&nbsp;" * pad)
            rows.append(sep.join(parts))
        legend_text: str = "<br>".join(rows)
    else:
        # One entry per line (vertical, like a standard legend)
        legend_text = "<br>".join(legend_parts)

    legend_x: float = float(config.get(f"{_prefix}x", config.get("numbered_legend_x", 1.02)))
    legend_y: float = float(config.get(f"{_prefix}y", config.get("numbered_legend_y", 0.0)))
    bgcolor: str = str(
        config.get(f"{_prefix}bgcolor", config.get("numbered_legend_bgcolor", "#FFFFFF"))
    )
    font_size: int = int(config.get(f"{_prefix}font_size", config.get("numbered_legend_size", 10)))
    font_color: str = str(config.get(f"{_prefix}font_color", "#333333"))
    border_color: str = str(config.get(f"{_prefix}border_color", "#333333"))
    border_width: int = int(config.get(f"{_prefix}border_width", 1))
    xanchor: str = str(config.get(f"{_prefix}xanchor", "left"))
    yanchor: str = str(config.get(f"{_prefix}yanchor", "bottom"))

    # Use monospace font family so that column padding aligns correctly.
    font_family: str = str(config.get(f"{_prefix}font_family", "monospace"))

    legend_annotation: dict[str, Any] = dict(
        x=legend_x,
        y=legend_y,
        xref="paper",
        yref="paper",
        text=legend_text,
        showarrow=False,
        font=dict(size=font_size, color=font_color, family=font_family),
        align="left",
        xanchor=xanchor,
        yanchor=yanchor,
        bordercolor=border_color,
        borderwidth=border_width,
        borderpad=6,
        bgcolor=bgcolor,
    )

    return numbered_text, legend_annotation


def build_category_annotations(
    cat_centers: list[tuple[float, str]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build annotations for category labels (grouped bars only)."""
    stagger_dy = (
        config.get("group_label_alt_spacing", 0.05)
        if config.get("group_label_alternate", True)
        else 0.0
    )
    return GroupedBarUtils.build_category_annotations(
        cat_centers=cat_centers,
        font_size=config.get("major_label_size", 14),
        font_color=config.get("major_label_color", "#000000"),
        y_offset=config.get("major_label_offset", -0.15),
        stagger_dy=stagger_dy,
    )


def apply_dual_axis_titles(fig: go.Figure, config: dict[str, Any]) -> None:
    """Apply Y-axis titles as symmetrical annotations for dual-axis mode.

    When dual-axis is active **both** Y labels are rendered as
    annotations so they look identical (same font family, size and
    colour).  The only differences are:

    * Primary  (left):  ``textangle = -90``  at ``x = 0``
    * Secondary (right): ``textangle =  90`` at ``x = 1``

    Also applies secondary Y-axis tick styling.

    Args:
        fig: Plotly figure (``make_subplots`` with ``secondary_y``).
        config: Full plot configuration.
    """
    # ── Resolve primary settings ─────────────────────────────
    ylabel_left: str = config.get("ylabel", "")
    ylabel_right: str = config.get("ylabel_right", "")

    primary_font_size: int = int(config.get("yaxis_title_font_size", 14))
    primary_standoff: int = int(config.get("yaxis_title_standoff", 0))
    font_color: str = config.get("axis_color", "#444444")

    # ── Resolve secondary settings (fall back to primary) ────
    yaxis2_fs_raw: Any = config.get("yaxis2_title_font_size")
    secondary_font_size: int = (
        int(yaxis2_fs_raw) if yaxis2_fs_raw is not None else primary_font_size
    )
    yaxis2_so_raw: Any = config.get("yaxis2_title_standoff")
    secondary_standoff: int = int(yaxis2_so_raw) if yaxis2_so_raw is not None else primary_standoff

    # ── Secondary Y tick styling (fall back to primary) ────
    primary_tick_size: int = int(config.get("yaxis_tickfont_size", 12))
    primary_tick_color: str = config.get("yaxis_tickfont_color", "#444444")

    y2_tick_size_raw: Any = config.get("yaxis2_tickfont_size")
    secondary_tick_size: int = (
        int(y2_tick_size_raw) if y2_tick_size_raw is not None else primary_tick_size
    )
    y2_tick_color_raw: Any = config.get("yaxis2_tickfont_color")
    secondary_tick_color: str = (
        str(y2_tick_color_raw) if y2_tick_color_raw is not None else primary_tick_color
    )

    fig.update_yaxes(
        tickfont=dict(
            size=secondary_tick_size,
            color=secondary_tick_color,
        ),
        secondary_y=True,
    )

    # ── Primary Y title → annotation (if not already done) ──
    if ylabel_left:
        fig.update_yaxes(title_text="", secondary_y=False)

        fig.add_annotation(
            text=ylabel_left,
            x=0,
            y=0.5,
            xref="paper",
            yref="paper",
            xanchor="right",
            yanchor="middle",
            textangle=-90,
            showarrow=False,
            captureevents=False,
            font=dict(size=primary_font_size, color=font_color),
            xshift=-(primary_standoff + 40),
        )

    # ── Secondary Y title → annotation ──────────────────────
    if ylabel_right:
        fig.update_yaxes(title_text="", secondary_y=True)

        fig.add_annotation(
            text=ylabel_right,
            x=1.0,
            y=0.5,
            xref="paper",
            yref="paper",
            xanchor="left",
            yanchor="middle",
            textangle=90,
            showarrow=False,
            captureevents=False,
            font=dict(size=secondary_font_size, color=font_color),
            xshift=secondary_standoff + 40,
        )
    else:
        fig.update_yaxes(title_text="", secondary_y=True)


def apply_separate_legends(fig: go.Figure, config: dict[str, Any]) -> None:
    """Split traces into separate legends for left and right axis groups.

    Left-axis traces are assigned to ``legend``, right-axis traces to
    ``legend2``.  ``legend2`` uses position/appearance controls from
    the ``legend2_*`` config keys set by the secondary legend UI.

    Args:
        fig: Plotly figure with dual-axis traces.
        config: Plot configuration dict.
    """
    n_left: int = len(config.get("y_columns", []))

    for i, trace in enumerate(fig.data):
        if not isinstance(trace, BaseTraceType):
            continue
        if i < n_left:
            trace.update(legend="legend")
        else:
            trace.update(legend="legend2")

    # Secondary legend config from user controls (fallback to defaults)
    legend2_cfg: dict[str, Any] = {
        "x": config.get("legend2_x", 1.0),
        "y": config.get("legend2_y", 1.0),
        "xanchor": config.get("legend2_xanchor", "right"),
        "yanchor": config.get("legend2_yanchor", "top"),
        "orientation": config.get("legend2_orientation", "v"),
    }

    # Item spacing (tracegroupgap)
    _tracegroupgap = config.get("legend2_tracegroupgap", 10)
    if _tracegroupgap and int(_tracegroupgap) > 0:
        legend2_cfg["tracegroupgap"] = int(_tracegroupgap)

    # Font
    legend2_font: dict[str, Any] = {}
    if config.get("legend2_font_color"):
        legend2_font["color"] = config["legend2_font_color"]
    if config.get("legend2_font_size"):
        legend2_font["size"] = config["legend2_font_size"]

    # Inherit font_family from global config
    if config.get("font_family"):
        legend2_font["family"] = config["font_family"]

    # Fallback: inherit from primary legend if no secondary font set
    if not legend2_font and fig.layout.legend and fig.layout.legend.font:
        font_obj = fig.layout.legend.font
        if font_obj.size is not None:
            legend2_font["size"] = font_obj.size
        if font_obj.color is not None:
            legend2_font["color"] = font_obj.color
        if font_obj.family is not None:
            legend2_font["family"] = font_obj.family

    if legend2_font:
        legend2_cfg["font"] = legend2_font

    # Background & border
    if config.get("legend2_bgcolor"):
        legend2_cfg["bgcolor"] = config["legend2_bgcolor"]
    if config.get("legend2_border_width", 0) > 0:
        legend2_cfg["bordercolor"] = config.get("legend2_border_color", "#000000")
        legend2_cfg["borderwidth"] = config["legend2_border_width"]

    # Sizing — multi-column layout via entrywidth
    _ncols = int(config.get("legend2_ncols", 0))
    _entrywidth = int(config.get("legend2_entrywidth", 0))
    if _ncols > 1 and _entrywidth <= 0:
        # Auto-compute: each entry takes 1/ncols of the plot width
        legend2_cfg["entrywidth"] = round(1.0 / _ncols, 4)
        legend2_cfg["entrywidthmode"] = "fraction"
    elif _ncols == 1 and _entrywidth <= 0:
        # Force single column — each entry takes full width
        legend2_cfg["entrywidth"] = 1.0
        legend2_cfg["entrywidthmode"] = "fraction"
    elif _entrywidth > 0:
        legend2_cfg["entrywidth"] = _entrywidth
        legend2_cfg["entrywidthmode"] = "pixels"

    _itemwidth = int(config.get("legend2_itemwidth", 0))
    if _itemwidth > 0:
        legend2_cfg["itemwidth"] = max(30, _itemwidth)  # Plotly minimum is 30

    _indentation = int(config.get("legend2_indentation", 0))
    if _indentation != 0:
        legend2_cfg["indentation"] = _indentation

    # Title
    legend2_title = config.get("legend2_title")
    if legend2_title:
        legend2_cfg["title"] = dict(text=legend2_title)

    fig.update_layout(
        legend=dict(
            x=0.0,
            y=1.0,
            xanchor="left",
            yanchor="top",
        ),
        legend2=legend2_cfg,
    )


def build_right_axis_traces(
    data: pd.DataFrame,
    x_coord_col: str,
    y_cols: list[str],
    trace_type: str,
    bar_width: float | None,
    config: dict[str, Any],
) -> list[TraceConfig]:
    """Build traces for the secondary (right) Y-axis.

    Args:
        data: DataFrame with ``x_coord_col`` already mapped.
        x_coord_col: Column name holding numeric X coordinates.
        y_cols: Numeric columns to plot on the right axis.
        trace_type: ``"bars"`` or ``"dots"``.
        bar_width: Width for bar traces (may be None).
        config: Full plot configuration.

    Returns:
        List of TraceConfig for the right axis.
    """
    series_styles: dict[str, Any] = config.get("series_styles", {})
    traces: list[TraceConfig] = []

    for y_col in y_cols:
        error_y_vals: list[float] | None = None
        if config.get("show_error_bars"):
            sd_col: str = f"{y_col}.sd"
            if sd_col in data.columns:
                error_y_vals = data[sd_col].tolist()

        style: dict[str, Any] = series_styles.get(y_col, {})
        trace_name: str = style.get("name", y_col)

        if trace_type == "bars":
            traces.append(
                BarTraceConfig(
                    name=trace_name,
                    x_positions=data[x_coord_col].tolist(),
                    y=data[y_col].tolist(),
                    bar_width=bar_width if bar_width is not None else 0.8,
                    color=(style.get("color", "") if style.get("use_color") else ""),
                    pattern=style.get("pattern", ""),
                    error_y=error_y_vals,
                    yaxis="y2",
                )
            )
        else:  # dots
            show_lines: bool = config.get("right_show_lines", True)
            if show_lines:
                traces.append(
                    LineTraceConfig(
                        name=trace_name,
                        x=data[x_coord_col].tolist(),
                        y=data[y_col].tolist(),
                        show_markers=True,
                        marker_symbol=config.get("right_dot_symbol", "circle"),
                        marker_size=config.get("right_dot_size", 10),
                        line_width=float(config.get("right_line_width", 2)),
                        error_y=error_y_vals,
                        yaxis="y2",
                    )
                )
            else:
                traces.append(
                    ScatterTraceConfig(
                        name=trace_name,
                        x=data[x_coord_col].tolist(),
                        y=data[y_col].tolist(),
                        marker_symbol=config.get("right_dot_symbol", "circle"),
                        marker_size=config.get("right_dot_size", 10),
                        error_y=error_y_vals,
                        yaxis="y2",
                    )
                )

    return traces
