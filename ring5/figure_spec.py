"""Typed, ergonomic description of a publication figure.

``FigureSpec`` is a small typed front-end over the flat ``dict[str, Any]`` config
that ``ConfigSpecBuilder.from_config`` consumes. It exists so callers get
autocomplete + light validation for the **common** publication knobs (the ones
needed for bar / stacked / grouped-stacked figures) instead of having to discover
~80 string keys by grepping :mod:`src.web.rendering.config_builder`.

The typed fields cover the frequent cases; anything not modelled stays reachable
through :attr:`FigureSpec.extra` (a raw dict merged last, so it can also override).
``to_config()`` emits the exact flat keys the renderer expects, hiding two RING-5
quirks: the primary legend uses ``legend_anchor_x/anchor_y`` while the numbered
"legend box" uses ``legend2_xanchor/yanchor``; and headless figures want small
margins (the flat-config defaults of 80/120/100/100 px squash short figures).

Pure data + mapping — no Streamlit, no rendering imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Valid modes for the numbered x-axis multiselect (see grouped_stacked_bar_helpers).
_NUMBERED_MODES = frozenset({"Numbers", "Labels", "Number legend"})


@dataclass
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


@dataclass
class ReferenceLineOpts:
    """A horizontal reference line (e.g. a normalized baseline at y=1.0)."""

    y: float = 1.0
    color: str = "red"
    width: float = 1.4
    style: str = "dash"  # solid / dash / dot / dashdot
    label: str = ""


@dataclass
class DualAxisOpts:
    """A secondary (right) Y-axis overlay on a grouped(-stacked) bar figure.

    The right axis plots ``columns`` either as more bars or as a dot/line series
    over the same grouped bars (positioned at the bars' own coordinates). With
    ``per_group=True`` the connecting line is drawn *per x-category* (a separate
    polyline for each group, gaps between) rather than one continuous line.
    """

    columns: list[str] = field(default_factory=list)  # right-axis data column(s)
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
    # Style and position the separate right-axis legend when legends are not unified.
    # this the twin legend falls back to loc="upper right". Lets a dual-axis figure
    # position its second-axis legend the same way the primary legend is positioned.
    legend: "LegendOpts | None" = None


@dataclass
class FigureSpec:
    """Typed description of a (grouped/stacked) bar figure for headless rendering.

    Build one, call :meth:`to_config`, and pass the result as the ``config`` to
    :meth:`ring5.Session.create_plot` (then :func:`ring5.render_figure`). Only the
    knobs you set matter; everything else uses sensible publication defaults. Reach
    the long tail of flat-config keys via :attr:`extra`.
    """

    # Data mapping
    x: str | None = None  # major-group / x column
    group: str | None = None  # minor-group column (grouped / grouped_stacked)
    y_columns: list[str] = field(default_factory=list)  # series / stack segments

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
    x_order: list[str] | None = None
    group_order: list[str] | None = None

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
    palette: str | list[str] | None = None  # registry name OR explicit hex list

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
    major_label_rotation_overrides: dict[str, float] | None = None
    group_label_alternate: bool = True  # stagger labels on two rows
    group_label_alt_spacing: float = 0.05

    # Category super-groups use bold boundaries and centered labels.
    category_groups: dict[str, str] | None = None  # category -> super-group label
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

    # Numbered x-axis + legends + reference line
    numbered_xaxis_modes: list[str] | None = None
    number_legend: LegendOpts | None = None  # styles the "1. .. / 2. .." box
    legend: LegendOpts = field(default_factory=LegendOpts)
    reference_line: ReferenceLineOpts | None = None

    # Dual axis (secondary right Y-axis overlay)
    dual_axis: DualAxisOpts | None = None

    # Escape hatch (merged last; can override anything above)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Light validation of the most error-prone fields."""
        if len(self.margins) != 4:
            raise ValueError("margins must be a 4-tuple (top, bottom, left, right) in px")
        if self.y_range is not None and len(self.y_range) != 2:
            raise ValueError("y_range must be a 2-tuple (min, max)")
        if self.numbered_xaxis_modes is not None:
            bad = [m for m in self.numbered_xaxis_modes if m not in _NUMBERED_MODES]
            if bad:
                raise ValueError(f"numbered_xaxis_modes {bad} not in {sorted(_NUMBERED_MODES)}")

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
        if self.number_legend is not None:
            _emit_legend(cfg, self.number_legend, "legend2_", anchor_keys=("xanchor", "yanchor"))

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

        cfg.update(self.extra)  # escape hatch wins
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


class FigureSpecBuilder:
    """Fluent builder for :class:`FigureSpec` — set knobs in cohesive groups.

    Mirrors RING-5's ``*SpecBuilder`` convention and avoids one giant constructor
    call: each method sets a related slice of the figure and returns ``self``, so
    calls chain and read top-to-bottom. Only arguments you pass are applied;
    everything else keeps the :class:`FigureSpec` defaults. ``build()`` produces the
    immutable spec (validated in ``FigureSpec.__post_init__``)::

        spec = (
            FigureSpecBuilder()
            .data(x="benchmark", group="policy", y_columns=regions)
            .size(width=820, height=372, margins=(28, 50, 58, 14))
            .palette(["#66c2a5", "#fc8d62", "#a6d854"])
            .axes(ylabel="Norm. cycles", y_range=(0.0, 1.4), y_dtick=0.2)
            .grid(dash="dash", alpha=0.3).tick_marks(x=False)
            .separators(show=True, isolate_last=True)
            .category_labels(rotation=30, alternate=False)
            .numbered_xaxis("Number legend")
            .legend(position=(0.61, 1.0), anchor=("left", "top"), ncols=3, item_width=5)
            .number_legend(position=(0.62, 0.84), anchor=("left", "top"), ncols=2)
            .reference_line(y=1.0)
            .build()
        )
    """

    def __init__(self) -> None:
        self._kw: dict[str, Any] = {}

    def _set(self, **kw: Any) -> "FigureSpecBuilder":
        for key, value in kw.items():
            if value is not None:
                self._kw[key] = value
        return self

    def data(
        self,
        x: str | None = None,
        group: str | None = None,
        y_columns: list[str] | None = None,
    ) -> "FigureSpecBuilder":
        """Configure data columns.

        Args:
            x: Major category column.
            group: Minor group column.
            y_columns: Value or stacked-series columns.

        Returns:
            This builder.
        """
        return self._set(x=x, group=group, y_columns=y_columns)

    def size(
        self,
        width: float | None = None,
        height: float | None = None,
        margins: tuple[float, float, float, float] | None = None,
    ) -> "FigureSpecBuilder":
        """Configure figure dimensions.

        Args:
            width: Figure width in pixels.
            height: Figure height in pixels.
            margins: Top, bottom, left, and right margins in pixels.

        Returns:
            This builder.
        """
        return self._set(width=width, height=height, margins=margins)

    def title(
        self,
        text: str | None = None,
        font_size: int | None = None,
        font_family: str | None = None,
    ) -> "FigureSpecBuilder":
        """Configure the title and font family.

        Args:
            text: Figure title.
            font_size: Title font size.
            font_family: Global font family.

        Returns:
            This builder.
        """
        return self._set(title=text, title_font_size=font_size, font_family=font_family)

    def axes(
        self,
        xlabel: str | None = None,
        ylabel: str | None = None,
        y_range: tuple[float, float] | None = None,
        y_dtick: float | None = None,
        x_order: list[str] | None = None,
        group_order: list[str] | None = None,
        label_font_size: int | None = None,
        tick_font_size: int | None = None,
    ) -> "FigureSpecBuilder":
        """Configure axes.

        Args:
            xlabel: Horizontal-axis title.
            ylabel: Primary vertical-axis title.
            y_range: Primary vertical-axis minimum and maximum.
            y_dtick: Primary vertical-axis major tick interval.
            x_order: Explicit category order.
            group_order: Explicit minor-group order.
            label_font_size: Axis-title font size.
            tick_font_size: Axis tick-label font size.

        Returns:
            This builder.
        """
        return self._set(
            xlabel=xlabel,
            ylabel=ylabel,
            y_range=y_range,
            y_dtick=y_dtick,
            x_order=x_order,
            group_order=group_order,
            ylabel_font_size=label_font_size,
            tick_font_size=tick_font_size,
        )

    def grid(
        self,
        y: bool | None = None,
        dash: str | None = None,
        alpha: float | None = None,
        color: str | None = None,
        x: bool | None = None,
    ) -> "FigureSpecBuilder":
        """Configure grid lines.

        Args:
            y: Show horizontal grid lines.
            dash: Horizontal grid-line style.
            alpha: Horizontal grid-line opacity.
            color: Horizontal grid-line color.
            x: Show vertical grid lines.

        Returns:
            This builder.
        """
        return self._set(
            show_y_grid=y,
            y_grid_dash=dash,
            y_grid_alpha=alpha,
            y_grid_color=color,
            show_x_grid=x,
        )

    def tick_marks(self, x: bool | None = None, y: bool | None = None) -> "FigureSpecBuilder":
        """Configure axis tick marks.

        Args:
            x: Show horizontal-axis tick marks.
            y: Show vertical-axis tick marks.

        Returns:
            This builder.
        """
        return self._set(show_x_tick_marks=x, show_y_tick_marks=y)

    def bars(
        self,
        mode: str | None = None,
        gap: float | None = None,
        group_gap: float | None = None,
        border_width: float | None = None,
    ) -> "FigureSpecBuilder":
        """Configure bar layout.

        Args:
            mode: Bar arrangement mode.
            gap: Gap between category groups.
            group_gap: Gap between bars inside a group.
            border_width: Bar outline width.

        Returns:
            This builder.
        """
        return self._set(
            barmode=mode, bargap=gap, bargroupgap=group_gap, bar_border_width=border_width
        )

    def palette(self, palette: str | list[str]) -> "FigureSpecBuilder":
        """Configure the color palette.

        Args:
            palette: Registry name or explicit color list.

        Returns:
            This builder.
        """
        return self._set(palette=palette)

    def separators(
        self,
        show: bool | None = None,
        color: str | None = None,
        isolate_last: bool | None = None,
        isolation_gap: float | None = None,
    ) -> "FigureSpecBuilder":
        """Configure separators between groups.

        Args:
            show: Draw standard separators.
            color: Separator color.
            isolate_last: Emphasize the boundary before the last group.
            isolation_gap: Additional spacing before the isolated group.

        Returns:
            This builder.
        """
        return self._set(
            show_separators=show,
            separator_color=color,
            isolate_last_group=isolate_last,
            isolation_gap=isolation_gap,
        )

    def category_labels(
        self,
        size: int | None = None,
        offset: float | None = None,
        rotation: float | None = None,
        rotation_overrides: dict[str, float] | None = None,
        alternate: bool | None = None,
        alt_spacing: float | None = None,
    ) -> "FigureSpecBuilder":
        """Configure category labels.

        Args:
            size: Label font size.
            offset: Vertical label offset.
            rotation: Default label rotation in degrees.
            rotation_overrides: Rotation by displayed category.
            alternate: Stagger labels across two rows.
            alt_spacing: Vertical spacing between staggered rows.

        Returns:
            This builder.
        """
        return self._set(
            major_label_size=size,
            major_label_offset=offset,
            major_label_rotation=rotation,
            major_label_rotation_overrides=rotation_overrides,
            group_label_alternate=alternate,
            group_label_alt_spacing=alt_spacing,
        )

    def category_groups(
        self,
        mapping: dict[str, str],
        label_size: int | None = None,
        label_offset: float | None = None,
        label_color: str | None = None,
        separator_color: str | None = None,
        separator_width: float | None = None,
        separator_dash: str | None = None,
        rule: bool | None = None,
        rule_color: str | None = None,
        rule_width: float | None = None,
        rule_y: float | None = None,
        rule_inset: float | None = None,
    ) -> "FigureSpecBuilder":
        """Configure category super-groups.

        Args:
            mapping: Category names mapped to super-group labels.
            label_size: Super-group label font size.
            label_offset: Vertical label offset.
            label_color: Label color.
            separator_color: Boundary separator color.
            separator_width: Boundary separator width.
            separator_dash: Boundary separator style.
            rule: Draw a span rule above each label.
            rule_color: Span-rule color.
            rule_width: Span-rule width.
            rule_y: Explicit span-rule vertical position.
            rule_inset: Space trimmed from both ends of each span rule.

        Returns:
            This builder.
        """
        return self._set(
            category_groups=mapping,
            category_group_label_size=label_size,
            category_group_label_offset=label_offset,
            category_group_label_color=label_color,
            category_group_separator_color=separator_color,
            category_group_separator_width=separator_width,
            category_group_separator_dash=separator_dash,
            category_group_rule=rule,
            category_group_rule_color=rule_color,
            category_group_rule_width=rule_width,
            category_group_rule_y=rule_y,
            category_group_rule_inset=rule_inset,
        )

    def numbered_xaxis(self, *modes: str) -> "FigureSpecBuilder":
        """Enable numbered x-axis modes.

        Args:
            *modes: Any of ``"Numbers"``, ``"Labels"``, and ``"Number legend"``.

        Returns:
            This builder.
        """
        return self._set(numbered_xaxis_modes=list(modes))

    def legend(self, **opts: Any) -> "FigureSpecBuilder":
        """Configure the primary series legend.

        Args:
            **opts: :class:`LegendOpts` field values.

        Returns:
            This builder.
        """
        return self._set(legend=LegendOpts(**opts))

    def number_legend(self, **opts: Any) -> "FigureSpecBuilder":
        """Configure the numbered group legend.

        Args:
            **opts: :class:`LegendOpts` field values.

        Returns:
            This builder.
        """
        return self._set(number_legend=LegendOpts(**opts))

    def reference_line(self, **opts: Any) -> "FigureSpecBuilder":
        """Configure a horizontal reference line.

        Args:
            **opts: :class:`ReferenceLineOpts` field values.

        Returns:
            This builder.
        """
        return self._set(reference_line=ReferenceLineOpts(**opts))

    def dual_axis(self, **opts: Any) -> "FigureSpecBuilder":
        """Configure a secondary vertical axis.

        Args:
            **opts: :class:`DualAxisOpts` field values.

        Returns:
            This builder.
        """
        return self._set(dual_axis=DualAxisOpts(**opts))

    def extra(self, **kw: Any) -> "FigureSpecBuilder":
        """Set unmodelled flat configuration keys.

        Args:
            **kw: Flat configuration values merged after typed fields.

        Returns:
            This builder.
        """
        merged = dict(self._kw.get("extra", {}))
        merged.update(kw)
        self._kw["extra"] = merged
        return self

    def build(self) -> FigureSpec:
        """Produce the validated :class:`FigureSpec`."""
        return FigureSpec(**self._kw)
