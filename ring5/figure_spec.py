"""Immutable figure settings and their canonical editable configuration projection.

Typed fields cover common publication settings. ``extra`` owns supported flat
configuration keys and overrides typed fields when ``to_config()`` produces a
fresh mutable mapping. The value models have no renderer or Streamlit dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any, cast

from src.core.common.numbered_axis import numbered_axis_modes, numbered_legend_prefix


def _immutable_values(value: Any, active: set[int], memo: dict[int, Any]) -> Any:
    """Own supported configuration values without retaining mutable aliases."""
    if value is None or type(value) in (str, int, float, bool):
        return value
    if type(value) in (LegendOpts, ReferenceLineOpts, DualAxisOpts):
        return value
    if not isinstance(value, (Mapping, list, tuple)):
        raise TypeError(f"Unsupported mutable figure value: {type(value).__name__}.")
    identity = id(value)
    if identity in active:
        raise ValueError("Cyclic figure configuration values are unsupported.")
    if identity in memo:
        return memo[identity]
    active.add(identity)
    try:
        if isinstance(value, Mapping):
            owned = {
                _immutable_values(key, active, memo): _immutable_values(item, active, memo)
                for key, item in value.items()
            }
            result: Any = MappingProxyType(owned)
        else:
            result = tuple(_immutable_values(item, active, memo) for item in value)
        memo[identity] = result
        return result
    finally:
        active.remove(identity)


def _own_fields(value: Any) -> None:
    """Freeze each dataclass field while retaining shared immutable values."""
    memo: dict[int, Any] = {}
    for item in fields(value):
        object.__setattr__(
            value, item.name, _immutable_values(getattr(value, item.name), set(), memo)
        )


def _mutable_values(value: Any, memo: dict[int, Any] | None = None) -> Any:
    """Project immutable values into an independently owned editable configuration."""
    if memo is None:
        memo = {}
    if not isinstance(value, (Mapping, tuple, list)):
        return value
    identity = id(value)
    if identity in memo:
        return memo[identity]
    if isinstance(value, Mapping):
        result: Any = {}
        memo[identity] = result
        for key, item in value.items():
            result[key] = _mutable_values(item, memo)
    else:
        result = []
        memo[identity] = result
        result.extend(_mutable_values(item, memo) for item in value)
    return result


@dataclass(frozen=True)
class LegendOpts:
    """Styling for one legend. Fields left ``None`` fall back to renderer defaults.

    Used both for the primary (trace/series) legend and, optionally, for the
    numbered "legend box" that maps ``1, 2, 3...`` to the minor-group names.
    """

    position: tuple[float, float] | None = None  # (x, y), axes/paper fraction
    anchor: tuple[str, str] | None = None  # (x-anchor, y-anchor): left/right/center, top/bottom
    ncols: int | None = None
    font_size: float | None = None
    item_width: int | None = None  # swatch length proxy (smaller -> shorter swatches)
    bgcolor: str | None = None
    bgalpha: float | None = None  # background opacity 0..1 (0 = transparent box)
    border_color: str | None = None
    border_width: int | None = None
    tracegroupgap: int | None = None  # row spacing proxy (smaller -> tighter rows)
    column_spacing: float | None = None
    handletextpad: float | None = None

    def __post_init__(self) -> None:
        """Retain immutable owned option values."""
        _own_fields(self)


@dataclass(frozen=True)
class ReferenceLineOpts:
    """A horizontal reference line (e.g. a normalized baseline at y=1.0)."""

    y: float = 1.0
    color: str = "red"
    width: float = 1.4
    style: str = "dash"  # solid / dash / dot / dashdot
    label: str = ""

    def __post_init__(self) -> None:
        """Retain immutable owned option values."""
        _own_fields(self)


@dataclass(frozen=True)
class DualAxisOpts:
    """A secondary (right) Y-axis overlay on a grouped(-stacked) bar figure.

    The right axis plots ``columns`` either as more bars or as a dot/line series
    over the same grouped bars (positioned at the bars' own coordinates). With
    ``per_group=True`` the connecting line is drawn *per x-category* (a separate
    polyline for each group, gaps between) rather than one continuous line.
    """

    columns: Sequence[str] = field(default_factory=tuple)  # right-axis data column(s)
    kind: str = "dots"  # "dots" (dot/line) or "bars"
    show_lines: bool = True  # connect the dots (dots kind only)
    per_group: bool = False  # one polyline per x-category instead of continuous
    dot_size: int = 10
    dot_symbol: str = "circle"  # circle/square/diamond/cross/x/triangle-up/-down/star
    line_width: float = 2.0
    color: str | None = None  # single colour for the right series (e.g. a hex)
    ylabel: str = ""
    y_range: tuple[float, float] | None = None
    unified_legend: bool = True  # keep right series in the same legend as the bars
    # Position the separate right-axis legend when legends are not unified.
    legend: "LegendOpts | None" = None

    def __post_init__(self) -> None:
        """Retain immutable owned option values."""
        _own_fields(self)


@dataclass(frozen=True)
class FigureSpec:
    # [impl->req~ring5.api.figure-spec~1]
    """Immutable common publication settings with owned nested values.

    Pass the specification to :meth:`ring5.Session.create_plot` or
    :meth:`ring5.Session.plot`. :meth:`to_config` returns a fresh editable mapping
    with publication defaults and supported plot-specific keys from :attr:`extra`.
    Sequences and mappings are retained as immutable snapshots.
    """

    # Data mapping
    x: str | None = None  # major-group / x column
    group: str | None = None  # minor-group column (grouped / grouped_stacked)
    y_columns: Sequence[str] = field(default_factory=tuple)  # series / stack segments

    # Dimensions (px @ 96 dpi -> inches; margins in px, t/b/l/r)
    width: float = 800.0
    height: float = 480.0
    margins: tuple[float, float, float, float] = (24.0, 60.0, 62.0, 18.0)

    # Title / fonts
    title: str = ""
    font_family: str = "serif"
    title_font_size: int = 13

    # Axes
    xlabel: str = ""
    ylabel: str = ""
    ylabel_font_size: int = 11
    tick_font_size: int = 9
    y_range: tuple[float, float] | None = None
    y_dtick: float | None = None
    x_order: Sequence[str] | None = None
    group_order: Sequence[str] | None = None

    # Grid / tick marks
    show_y_grid: bool = True
    y_grid_dash: str = "dash"
    y_grid_alpha: float = 0.30
    y_grid_color: str = "#B4B4B4"
    show_x_grid: bool = False
    show_x_tick_marks: bool = True
    show_y_tick_marks: bool = True

    # Bars
    barmode: str = "group"  # ignored by grouped_stacked (forced to "stack")
    bargap: float = 0.2
    bargroupgap: float = 0.0
    bar_border_width: float = 0.0
    bar_border_color: str = ""  # "" -> connector default; e.g. "white" for separators
    palette: str | Sequence[str] | None = None  # registry name OR explicit hex list

    # Grouped separators
    show_separators: bool = False
    separator_color: str = "#D9D9D9"
    isolate_last_group: bool = False  # bold divider before the last group
    isolation_gap: float = 0.5

    # Major (category) labels
    major_label_size: int = 11
    major_label_offset: float = -0.12
    major_label_rotation: float = 0.0
    # per-label rotation, keyed by displayed category (e.g. {"arithmean": 90})
    major_label_rotation_overrides: Mapping[str, float] | None = None
    group_label_alternate: bool = True  # stagger labels on two rows
    group_label_alt_spacing: float = 0.05

    # Category super-groups use bold boundaries and centered labels.
    category_groups: Mapping[str, str] | None = None  # category -> super-group label
    category_group_label_size: int = 12
    category_group_label_offset: float = -0.28  # below major_label_offset
    category_group_label_color: str = "#000000"
    category_group_separator_color: str = "#444444"
    category_group_separator_width: float = 1.6
    category_group_separator_dash: str = "solid"
    category_group_rule: bool = True  # \cmidrule-style span rule above each label
    category_group_rule_color: str = "#444444"
    category_group_rule_width: float = 1.0
    category_group_rule_y: float | None = None  # default: just above the label
    category_group_rule_inset: float = 0.35  # x-units trimmed at each rule end

    # Grouped-stacked numbering: None is unspecified; [] explicitly disables it.
    numbered_xaxis_modes: Sequence[str] | None = None
    number_legend: LegendOpts | None = None  # styles the "1. .. / 2. .." box
    legend: LegendOpts = field(default_factory=LegendOpts)
    reference_line: ReferenceLineOpts | None = None

    # Dual axis (secondary right Y-axis overlay)
    dual_axis: DualAxisOpts | None = None

    # Escape hatch (merged last; can override anything above)
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Light validation of the most error-prone fields."""
        if len(self.margins) != 4:
            raise ValueError("margins must be a 4-tuple (top, bottom, left, right) in px")
        if self.y_range is not None and len(self.y_range) != 2:
            raise ValueError("y_range must be a 2-tuple (min, max)")
        if self.numbered_xaxis_modes is not None:
            numbered_axis_modes({"numbered_xaxis_modes": list(self.numbered_xaxis_modes)})
        numbered_axis_modes(self.extra)
        _own_fields(self)

    def to_config(self) -> dict[str, Any]:
        """Emit the flat config dict consumed by ``ConfigSpecBuilder.from_config``."""
        t, b, lft, r = self.margins
        cfg: dict[str, Any] = {
            # data mapping
            "y_columns": list(self.y_columns),
            # dimensions / margins
            "width": self.width,
            "height": self.height,
            "margin_t": t,
            "margin_b": b,
            "margin_l": lft,
            "margin_r": r,
            # title / fonts
            "title": self.title,
            "font_family": self.font_family,
            "title_font_size": self.title_font_size,
            # axes
            "xlabel": self.xlabel,
            "ylabel": self.ylabel,
            "yaxis_title_font_size": self.ylabel_font_size,
            "yaxis_tickfont_size": self.tick_font_size,
            "xaxis_tickfont_size": self.tick_font_size,
            # grid / ticks
            "show_y_grid": self.show_y_grid,
            "y_grid_dash": self.y_grid_dash,
            "y_grid_alpha": self.y_grid_alpha,
            "y_grid_color": self.y_grid_color,
            "show_x_grid": self.show_x_grid,
            "show_xtick_marks": self.show_x_tick_marks,
            "show_ytick_marks": self.show_y_tick_marks,
            # bars
            "barmode": self.barmode,
            "bargap": self.bargap,
            "bargroupgap": self.bargroupgap,
            "bar_border_width": self.bar_border_width,
            "bar_border_color": self.bar_border_color,
            # grouped separators
            "show_separators": self.show_separators,
            "separator_color": self.separator_color,
            "isolate_last_group": self.isolate_last_group,
            "isolation_gap": self.isolation_gap,
            # major (category) labels
            "major_label_size": self.major_label_size,
            "major_label_offset": self.major_label_offset,
            "major_label_rotation": self.major_label_rotation,
            "group_label_alternate": self.group_label_alternate,
            "group_label_alt_spacing": self.group_label_alt_spacing,
        }
        if self.y_columns:
            cfg["y"] = self.y_columns[0]  # the simple-bar path reads config["y"]
        if self.x is not None:
            cfg["x"] = self.x
        if self.group is not None:
            cfg["group"] = self.group
        if self.palette is not None:
            cfg["color_palette"] = self.palette
        if self.y_range is not None:
            cfg["range_y"] = [float(self.y_range[0]), float(self.y_range[1])]
        if self.y_dtick is not None:
            cfg["yaxis_dtick"] = self.y_dtick
        if self.x_order is not None:
            cfg["xaxis_order"] = list(self.x_order)
        if self.group_order is not None:
            cfg["group_order"] = list(self.group_order)
        if self.numbered_xaxis_modes is not None:
            cfg["numbered_xaxis_modes"] = list(self.numbered_xaxis_modes)
        if self.major_label_rotation_overrides is not None:
            cfg["major_label_rotation_overrides"] = dict(self.major_label_rotation_overrides)
        if self.category_groups is not None:
            cfg.update(
                {
                    "category_groups": dict(self.category_groups),
                    "category_group_label_size": self.category_group_label_size,
                    "category_group_label_offset": self.category_group_label_offset,
                    "category_group_label_color": self.category_group_label_color,
                    "category_group_separator_color": self.category_group_separator_color,
                    "category_group_separator_width": self.category_group_separator_width,
                    "category_group_separator_dash": self.category_group_separator_dash,
                    "category_group_rule": self.category_group_rule,
                    "category_group_rule_color": self.category_group_rule_color,
                    "category_group_rule_width": self.category_group_rule_width,
                    "category_group_rule_inset": self.category_group_rule_inset,
                }
            )
            if self.category_group_rule_y is not None:
                cfg["category_group_rule_y"] = self.category_group_rule_y

        _emit_legend(cfg, self.legend, "legend_", anchor_keys=("anchor_x", "anchor_y"))

        if self.reference_line is not None:
            rl = self.reference_line
            cfg.update(
                {
                    "reference_line_enabled": True,
                    "reference_line_y": rl.y,
                    "reference_line_color": rl.color,
                    "reference_line_width": rl.width,
                    "reference_line_style": rl.style,
                    "reference_line_label": rl.label,
                }
            )

        if self.dual_axis is not None:
            self._emit_dual_axis(cfg, self.dual_axis)

        if self.number_legend is not None:
            prefix = numbered_legend_prefix({**cfg, **self.extra})
            _emit_legend(cfg, self.number_legend, prefix, anchor_keys=("xanchor", "yanchor"))
        cfg.update(self.extra)  # escape hatch wins
        cfg = cast(dict[str, Any], _mutable_values(cfg))
        numbered_axis_modes(cfg)
        return cfg

    @staticmethod
    def _emit_dual_axis(cfg: dict[str, Any], opts: "DualAxisOpts") -> None:
        """Emit the flat dual-axis keys read by ``GroupedStackedBarPlot``."""
        cfg.update(
            {
                "dual_axis": True,
                "y_columns_right": list(opts.columns),
                "right_axis_type": opts.kind,
                "right_show_lines": opts.show_lines,
                "right_line_per_group": opts.per_group,
                "right_dot_size": opts.dot_size,
                "right_dot_symbol": opts.dot_symbol,
                "right_line_width": opts.line_width,
                "ylabel_right": opts.ylabel,
                "unified_legend": opts.unified_legend,
            }
        )
        if opts.y_range is not None:
            cfg["range_y2"] = [float(opts.y_range[0]), float(opts.y_range[1])]
        if opts.color:
            # One colour for every right-axis series (bar fill or dot/line colour).
            styles = dict(cfg.get("series_styles", {}))
            for col in opts.columns:
                styles[col] = {**styles.get(col, {}), "color": opts.color, "use_color": True}
            cfg["series_styles"] = styles
        if opts.legend is not None:
            # Style/place the separate twin (right-axis) legend (read by apply_dual_axis).
            _emit_legend(cfg, opts.legend, "dual_legend_", anchor_keys=("xanchor", "yanchor"))


def _emit_legend(
    cfg: dict[str, Any],
    opts: LegendOpts,
    prefix: str,
    *,
    anchor_keys: tuple[str, str],
) -> None:
    """Write a LegendOpts into *cfg* under *prefix*, only for fields that are set.

    ``anchor_keys`` differs by legend: the primary legend reads
    ``legend_anchor_x/anchor_y`` while the numbered box reads
    ``legend2_xanchor/yanchor`` — this helper hides that asymmetry.
    """
    if opts.position is not None:
        cfg[f"{prefix}x"] = opts.position[0]
        cfg[f"{prefix}y"] = opts.position[1]
    if opts.anchor is not None:
        cfg[f"{prefix}{anchor_keys[0]}"] = opts.anchor[0]
        cfg[f"{prefix}{anchor_keys[1]}"] = opts.anchor[1]
    if opts.ncols is not None:
        cfg[f"{prefix}ncols"] = opts.ncols
    if opts.font_size is not None:
        cfg[f"{prefix}font_size"] = opts.font_size
    if opts.item_width is not None:
        cfg[f"{prefix}itemwidth"] = opts.item_width
    if opts.bgcolor is not None:
        cfg[f"{prefix}bgcolor"] = opts.bgcolor
    if opts.bgalpha is not None:
        cfg[f"{prefix}bgalpha"] = opts.bgalpha
    if opts.border_color is not None:
        cfg[f"{prefix}border_color"] = opts.border_color
    if opts.border_width is not None:
        cfg[f"{prefix}border_width"] = opts.border_width
    if opts.tracegroupgap is not None:
        cfg[f"{prefix}tracegroupgap"] = opts.tracegroupgap
    if opts.column_spacing is not None:
        cfg[f"{prefix}column_spacing"] = opts.column_spacing
    if opts.handletextpad is not None:
        cfg[f"{prefix}handletextpad"] = opts.handletextpad
