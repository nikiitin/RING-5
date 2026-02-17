"""
Annotation specifications — text labels, boxed annotations, reference lines.

Covers:
  - Bar value labels (data annotations)
  - Grouping labels (below x-axis)
  - Boxed/numbered annotations (legend3 items)
  - Free-form text annotations
  - Reference lines (horizontal baselines, thresholds)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class AnnotationSpec:
    """Engine-agnostic description of a text annotation.

    The ``annotation_type`` discriminator tells connectors how to render:
      - ``"text"``      — free-form text at (x, y)
      - ``"bar_value"`` — data label on a bar (auto-positioned)
      - ``"group_label"``— category grouping label below x-axis
      - ``"boxed"``     — monospace boxed annotation (legend3 item)

    Coordinates:
      - ``xref`` / ``yref`` control the coordinate system:
        ``"data"`` = data coordinates, ``"paper"`` = figure fraction (0–1).
    """

    # ── Content ──────────────────────────────────────────────────
    text: str = ""
    annotation_type: Literal["text", "bar_value", "group_label", "boxed"] = "text"

    # ── Position ─────────────────────────────────────────────────
    x: float = 0.0
    y: float = 0.0
    xref: Literal["data", "paper"] = "data"
    yref: Literal["data", "paper"] = "data"
    xanchor: Literal["left", "center", "right", "auto"] = "auto"
    yanchor: Literal["top", "middle", "bottom", "auto"] = "auto"
    text_angle: float = 0.0  # rotation in degrees

    # ── Arrow ────────────────────────────────────────────────────
    show_arrow: bool = False
    arrow_head: int = 0
    arrow_color: str = "#444"

    # ── Font ─────────────────────────────────────────────────────
    font_size: int = -1  # -1 = use element default from TypographySpec
    font_color: str = "#444"
    font_bold: bool = False

    # ── Box styling (for boxed annotations) ──────────────────────
    border_width: float = 0.0
    border_color: str = "#444"
    border_pad: float = 2.0
    bgcolor: str = ""
    align: Literal["left", "center", "right"] = "left"


@dataclass
class ReferenceLineSpec:
    """A horizontal or vertical reference line across the plot.

    Examples: baseline at y=1.0, threshold at y=100, mean line.
    """

    enabled: bool = False
    axis: Literal["x", "y"] = "y"
    value: float = 0.0
    color: str = "red"
    width: float = 1.5
    style: Literal["solid", "dash", "dot", "dashdot"] = "dash"
    label: str = ""
