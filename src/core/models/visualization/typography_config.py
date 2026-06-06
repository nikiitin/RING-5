"""
Typography configuration — font sizes and bold flags for every text element.

This replaces the dual vocabulary:
  - ``FontStyleConfig`` (matplotlib-side dataclass with sentinel fields)
  - Scattered font keys in ``PlotDisplayConfig`` (Plotly-side)

All sizes are in **points** (the typographic standard).  Plotly connector
converts to px when needed.  Sentinel value ``-1`` means "inherit from
the nearest parent" and is resolved by ``resolvers.resolve_spec()``.
"""

from __future__ import annotations

from dataclasses import dataclass

# Sentinel: -1 means "inherit from parent"
INHERIT: int = -1
INHERIT_F: float = -1.0


@dataclass(frozen=True)
class TypographyConfig:
    """Per-element font size and weight specification.

    Inheritance chain (resolved top→down):
        font_size_base
        ├── font_size_title
        ├── font_size_xlabel
        ├── font_size_ylabel
        │   └── font_size_y2label  (inherits ylabel if -1)
        ├── font_size_ticks
        │   ├── font_size_yticks   (inherits ticks if -1)
        │   └── font_size_y2ticks  (inherits yticks if -1)
        ├── font_size_annotations
        └── font_size_legend       (primary legend)
            ├── font_size_legend2  (inherits legend if -1)
            └── font_size_legend3  (inherits legend if -1)
                ├── legend3_number_fontsize  (inherits legend3 if -1)
                └── legend3_text_fontsize    (inherits legend3 if -1)
    """

    # ── Base ─────────────────────────────────────────────────────
    font_size_base: int = 10  # root reference for inheritance

    # ── Per-element sizes (pts) ──────────────────────────────────
    font_size_title: int = 10
    font_size_xlabel: int = 9
    font_size_ylabel: int = 9
    font_size_y2label: int = INHERIT  # -1 → follow ylabel
    font_size_ticks: int = 7  # X-tick labels
    font_size_yticks: int = 7  # Y-tick labels
    font_size_y2ticks: int = INHERIT  # -1 → follow yticks
    font_size_annotations: int = 6  # bar value annotations
    font_size_legend: int = 8  # primary legend text
    font_size_legend2: int = INHERIT  # -1 → follow legend
    font_size_legend3: int = INHERIT  # -1 → follow legend
    legend3_number_fontsize: int = INHERIT  # -1 → follow legend3
    legend3_text_fontsize: int = INHERIT  # -1 → follow legend3

    # ── Bold flags ───────────────────────────────────────────────
    bold_title: bool = False
    bold_xlabel: bool = False
    bold_ylabel: bool = False
    bold_y2label: bool = False
    bold_ticks: bool = False
    bold_annotations: bool = True  # bar values bold by default
    bold_group_labels: bool = True  # X-axis grouping labels bold
    bold_legend: bool = False
    bold_legend2: bool = False
    bold_legend3: bool = False
