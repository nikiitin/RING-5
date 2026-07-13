"""
Typography configuration — font sizes and bold flags for every text element.

All sizes are in **points** (the typographic standard); the Plotly connector
converts to px when needed. Sentinel value ``-1`` means "inherit from the
nearest parent" and is resolved by
``services.visualization.config_resolver.resolve_config()`` before any
connector runs.
"""

from __future__ import annotations

from dataclasses import dataclass

# Sentinel: -1 means "inherit from parent"
INHERIT: int = -1
INHERIT_F: float = -1.0


@dataclass(frozen=True)
class TypographyConfig:
    """Per-element font size and weight specification.

    Sentinel ``-1`` means "inherit from parent"; resolved top→down by
    ``config_resolver.resolve_config``:
        font_size_ylabel  →  font_size_y2label
        font_size_ticks   →  font_size_yticks  →  font_size_y2ticks
        font_size_legend  →  font_size_legend2
    Every other size is an independent value (no inheritance).
    """

    # ── Per-element sizes (pts) ──────────────────────────────────
    font_size_title: int = 10
    font_size_xlabel: int = 9
    font_size_ylabel: int = 9
    font_size_y2label: int = INHERIT  # -1 → follow ylabel
    font_size_ticks: int = 7  # X-tick labels
    font_size_yticks: int = 7  # Y-tick labels
    font_size_y2ticks: int = INHERIT  # -1 → follow yticks
    font_size_legend: int = 8  # primary legend text
    font_size_legend2: int = INHERIT  # -1 → follow legend

    # ── Bold flags ───────────────────────────────────────────────
    bold_title: bool = False
    bold_xlabel: bool = False
    bold_ylabel: bool = False
    bold_y2label: bool = False
    bold_ticks: bool = False
