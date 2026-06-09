"""
Legend configuration — uniform model for all legend instances.

Instead of special-cased ``legend2_x``, ``legend3_borderpad`` etc., each legend
is a ``LegendConfig`` with identical fields. A figure holds
``List[LegendConfig]`` — typically 1–3 entries.

This eliminates:
  - Duplicated sentinel resolution for legend2/legend3
  - Asymmetric field names (``legend_columnspacing`` vs ``legend2_columnspacing``)
  - The need to special-case tertiary annotations as "legend3"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

INHERIT_F: float = -1.0


@dataclass(frozen=True)
class ColorbarConfig:
    """Colorbar-specific settings for heatmap plots.

    These settings only apply when the figure contains heatmap traces.
    For non-heatmap plots, connectors ignore this config.
    """

    title_side: Literal["top", "right", "bottom", "left"] = "top"
    range_mode: Literal["auto", "manual"] = "auto"
    zmin: float | None = None
    zmax: float | None = None
    nticks: int = 5
    tick_decimals: int = 2
    shared: bool = True
    tick_angle: float = 0.0  # rotation for colorbar tick labels (degrees)
    tick_side: str = "right"  # "right" (default) or "left"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "title_side": self.title_side,
            "range_mode": self.range_mode,
            "zmin": self.zmin,
            "zmax": self.zmax,
            "nticks": self.nticks,
            "tick_decimals": self.tick_decimals,
            "shared": self.shared,
            "tick_angle": self.tick_angle,
            "tick_side": self.tick_side,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ColorbarConfig:
        """Reconstruct from serialized dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class LegendSpacingConfig:
    """Fine-grained spacing parameters for a legend box.

    ``-1.0`` = inherit from the primary legend's value.
    """

    columnspacing: float = 0.5
    handletextpad: float = 0.3
    labelspacing: float = 0.2
    handlelength: float = 1.0
    handleheight: float = 0.7
    borderpad: float = 0.2
    borderaxespad: float = 0.5

    def to_dict(self) -> dict[str, float]:
        """Serialize to a plain dictionary."""
        return {
            "columnspacing": self.columnspacing,
            "handletextpad": self.handletextpad,
            "labelspacing": self.labelspacing,
            "handlelength": self.handlelength,
            "handleheight": self.handleheight,
            "borderpad": self.borderpad,
            "borderaxespad": self.borderaxespad,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> LegendSpacingConfig:
        """Reconstruct from serialized dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class LegendConfig:
    """Configuration for a single legend instance.

    All legends (primary, secondary, tertiary) share
    this same dataclass.  Differences are expressed through field values,
    not through different types.

    Attributes:
        role: Semantic role identifier.
            - ``"primary"``   — main trace legend
            - ``"secondary"`` — secondary axis traces
            - ``"tertiary"``  — tertiary annotation legend (numbered items)
        visible: Whether this legend is rendered.
        font_size: Text size in points (-1 = inherit from primary).
        bold: Whether legend text is bold.
        ncol: Number of columns (-1 = auto).
        position_x: X position as fraction of figure (0–1, -1 = auto).
        position_y: Y position as fraction of figure (0–1, -1 = auto).
        anchor_x: Horizontal anchor ("left", "center", "right", "auto").
        anchor_y: Vertical anchor ("top", "middle", "bottom", "auto").
        bgcolor: Background color (empty = transparent).
        border_width: Border line width (0 = no border).
        border_color: Border line color.
        orientation: Layout direction.
        itemsizing: How to size legend markers.
        spacing: Fine-grained spacing parameters.
        number_fontsize: For tertiary legends — size of number digits (-1 = follow font_size).
        text_fontsize: For tertiary legends — size of label text (-1 = follow font_size).
    """

    role: Literal["primary", "secondary", "tertiary"] = "primary"
    visible: bool = True

    # ── Typography ───────────────────────────────────────────────
    font_size: int = 8  # pts, -1 = inherit from primary
    font_family: str = ""  # empty = inherit from global font_family
    bold: bool = False

    # ── Layout ───────────────────────────────────────────────────
    ncol: int = 1  # number of columns, -1 = auto
    col_width: float = -1.0  # sentinel: -1 = auto column width
    entrywidth: int = 0  # Plotly entrywidth in pixels, 0 = auto
    indentation: int = 0  # horizontal indentation of grouped items in px
    orientation: Literal["horizontal", "vertical"] = "vertical"
    itemsizing: Literal["constant", "trace"] = "constant"
    itemwidth: int = 30
    tracegroupgap: int = 10
    order: Literal["normal", "reversed"] = "normal"
    trace_distribution: str = ""  # comma-separated trace indices, empty = all

    # ── Position ─────────────────────────────────────────────────
    position_x: float = INHERIT_F  # -1 = auto
    position_y: float = INHERIT_F  # -1 = auto
    anchor_x: Literal["left", "center", "right", "auto"] = "auto"
    anchor_y: Literal["top", "middle", "bottom", "auto"] = "auto"
    valign: Literal["top", "middle", "bottom"] = "middle"  # vertical text alignment
    custom_position: bool = False  # whether to use position_x/y

    # ── Styling ──────────────────────────────────────────────────
    bgcolor: str = ""  # empty = transparent
    border_width: float = 0.0
    border_color: str = "#444"
    font_color: str = "#444"
    title_font_color: str = "#444"
    title_font_size: int = -1  # -1 = follow font_size
    title: str = ""

    # ── Spacing ──────────────────────────────────────────────────
    spacing: LegendSpacingConfig = field(default_factory=LegendSpacingConfig)

    # ── Colorbar (heatmap-specific) ──────────────────────────────
    colorbar: ColorbarConfig = field(default_factory=ColorbarConfig)

    # ── Tertiary-annotation extras ──────────────────────────────
    number_fontsize: int = -1  # -1 = follow font_size
    text_fontsize: int = -1  # -1 = follow font_size

    @staticmethod
    def derive_anchors(
        position_x: float,
        position_y: float,
    ) -> tuple[str, str]:
        """Auto-derive anchor from position for intuitive placement.

        When x > 0.8, the legend box anchors on the left so it extends inward.
        When x < 0.2, it anchors on the right.  Middle zone uses center.
        Same logic applies vertically.
        """
        ax = "left" if position_x > 0.8 else ("right" if position_x < 0.2 else "center")
        ay = "bottom" if position_y > 0.8 else ("top" if position_y < 0.2 else "middle")
        return ax, ay

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        result: dict[str, Any] = {
            "role": self.role,
            "visible": self.visible,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "bold": self.bold,
            "ncol": self.ncol,
            "col_width": self.col_width,
            "entrywidth": self.entrywidth,
            "indentation": self.indentation,
            "orientation": self.orientation,
            "itemsizing": self.itemsizing,
            "itemwidth": self.itemwidth,
            "tracegroupgap": self.tracegroupgap,
            "order": self.order,
            "trace_distribution": self.trace_distribution,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "anchor_x": self.anchor_x,
            "anchor_y": self.anchor_y,
            "valign": self.valign,
            "custom_position": self.custom_position,
            "bgcolor": self.bgcolor,
            "border_width": self.border_width,
            "border_color": self.border_color,
            "font_color": self.font_color,
            "title_font_color": self.title_font_color,
            "title_font_size": self.title_font_size,
            "title": self.title,
            "spacing": self.spacing.to_dict(),
            "colorbar": self.colorbar.to_dict(),
            "number_fontsize": self.number_fontsize,
            "text_fontsize": self.text_fontsize,
        }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegendConfig:
        """Reconstruct from serialized dictionary."""
        # Use .get() (not .pop()) so we never mutate the caller's input dict;
        # the `filtered` comprehension below already excludes these keys.
        spacing_data = data.get("spacing", {}) if isinstance(data.get("spacing"), dict) else {}
        spacing = (
            LegendSpacingConfig.from_dict(spacing_data) if spacing_data else LegendSpacingConfig()
        )
        colorbar_data = data.get("colorbar", {}) if isinstance(data.get("colorbar"), dict) else {}
        colorbar = ColorbarConfig.from_dict(colorbar_data) if colorbar_data else ColorbarConfig()
        filtered = {
            k: v
            for k, v in data.items()
            if k in cls.__dataclass_fields__ and k not in ("spacing", "colorbar")
        }
        return cls(spacing=spacing, colorbar=colorbar, **filtered)
