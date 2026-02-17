"""
Legend specification — uniform model for all legend instances.

Instead of special-cased ``legend2_x``, ``legend3_borderpad`` etc. scattered
across ``LaTeXPreset``, each legend is a ``LegendSpec`` with identical fields.
A figure holds ``List[LegendSpec]`` — typically 1–3 entries.

This eliminates:
  - Duplicated sentinel resolution for legend2/legend3
  - Asymmetric field names (``legend_columnspacing`` vs ``legend2_columnspacing``)
  - The need to special-case boxed annotations as "legend3"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal

INHERIT_F: float = -1.0


@dataclass
class LegendSpacingSpec:
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

    def to_dict(self) -> Dict[str, float]:
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
    def from_dict(cls, data: Dict[str, float]) -> "LegendSpacingSpec":
        """Reconstruct from serialized dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LegendSpec:
    """Configuration for a single legend instance.

    All legends (primary, secondary, tertiary / boxed-annotation) share
    this same dataclass.  Differences are expressed through field values,
    not through different types.

    Attributes:
        role: Semantic role identifier.
            - ``"primary"``  — main trace legend
            - ``"secondary"``— secondary axis traces
            - ``"boxed"``    — boxed annotation legend (numbered items)
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
        number_fontsize: For boxed legends — size of number digits (-1 = follow font_size).
        text_fontsize: For boxed legends — size of label text (-1 = follow font_size).
    """

    role: Literal["primary", "secondary", "boxed"] = "primary"
    visible: bool = True

    # ── Typography ───────────────────────────────────────────────
    font_size: int = 8  # pts, -1 = inherit from primary
    bold: bool = False

    # ── Layout ───────────────────────────────────────────────────
    ncol: int = 1  # number of columns, -1 = auto
    col_width: float = -1.0  # sentinel: -1 = auto column width
    orientation: Literal["horizontal", "vertical"] = "vertical"
    itemsizing: Literal["constant", "trace"] = "constant"
    order: Literal["normal", "reversed"] = "normal"
    trace_distribution: str = ""  # comma-separated trace indices, empty = all

    # ── Position ─────────────────────────────────────────────────
    position_x: float = INHERIT_F  # -1 = auto
    position_y: float = INHERIT_F  # -1 = auto
    anchor_x: Literal["left", "center", "right", "auto"] = "auto"
    anchor_y: Literal["top", "middle", "bottom", "auto"] = "auto"
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
    spacing: LegendSpacingSpec = field(default_factory=LegendSpacingSpec)

    # ── Boxed-annotation extras ──────────────────────────────────
    number_fontsize: int = -1  # -1 = follow font_size
    text_fontsize: int = -1  # -1 = follow font_size

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary."""
        result: Dict[str, Any] = {
            "role": self.role,
            "visible": self.visible,
            "font_size": self.font_size,
            "bold": self.bold,
            "ncol": self.ncol,
            "col_width": self.col_width,
            "orientation": self.orientation,
            "itemsizing": self.itemsizing,
            "order": self.order,
            "trace_distribution": self.trace_distribution,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "anchor_x": self.anchor_x,
            "anchor_y": self.anchor_y,
            "custom_position": self.custom_position,
            "bgcolor": self.bgcolor,
            "border_width": self.border_width,
            "border_color": self.border_color,
            "font_color": self.font_color,
            "title_font_color": self.title_font_color,
            "title_font_size": self.title_font_size,
            "title": self.title,
            "spacing": self.spacing.to_dict(),
            "number_fontsize": self.number_fontsize,
            "text_fontsize": self.text_fontsize,
        }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegendSpec":
        """Reconstruct from serialized dictionary."""
        spacing_data = data.pop("spacing", {}) if isinstance(data.get("spacing"), dict) else {}
        spacing = LegendSpacingSpec.from_dict(spacing_data) if spacing_data else LegendSpacingSpec()
        filtered = {
            k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "spacing"
        }
        return cls(spacing=spacing, **filtered)
