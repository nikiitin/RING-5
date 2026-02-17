"""Validate FigureSpec for publication quality.

Checks a :class:`FigureSpec` against venue-specific requirements
(font sizes, DPI, figure dimensions) and returns a list of human-readable
warnings.  These warnings are surfaced as ``st.warning()`` in the
download section so authors can fix issues before submission.

Usage::

    warnings = validate_for_publication(spec, "isca")
    for w in warnings:
        st.warning(w)
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.core.visualization.figure_spec import FigureSpec

# Venue requirements keyed by lowercase venue name.
# All dimension values are in inches; font sizes in points.
VENUE_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "isca": {
        "min_font": 7,
        "min_dpi": 300,
        "max_width": 3.5,
        "max_height": 5.0,
        "description": "ISCA single-column",
    },
    "micro": {
        "min_font": 7,
        "min_dpi": 300,
        "max_width": 3.5,
        "max_height": 5.0,
        "description": "MICRO single-column",
    },
    "asplos": {
        "min_font": 7,
        "min_dpi": 300,
        "max_width": 3.5,
        "max_height": 5.0,
        "description": "ASPLOS single-column",
    },
    "hpca": {
        "min_font": 7,
        "min_dpi": 300,
        "max_width": 3.5,
        "max_height": 5.0,
        "description": "HPCA single-column",
    },
    "nature": {
        "min_font": 6,
        "min_dpi": 600,
        "max_width": 3.5,
        "max_height": 10.0,
        "description": "Nature single-column",
    },
    "science": {
        "min_font": 6,
        "min_dpi": 600,
        "max_width": 3.5,
        "max_height": 9.0,
        "description": "Science single-column",
    },
    "ieee_single": {
        "min_font": 7,
        "min_dpi": 300,
        "max_width": 3.5,
        "max_height": 5.0,
        "description": "IEEE single-column",
    },
    "acm": {
        "min_font": 7,
        "min_dpi": 300,
        "max_width": 3.5,
        "max_height": 5.0,
        "description": "ACM single-column",
    },
    "poster": {
        "min_font": 18,
        "min_dpi": 150,
        "max_width": 48.0,
        "max_height": 36.0,
        "description": "Conference poster",
    },
    "slides": {
        "min_font": 14,
        "min_dpi": 150,
        "max_width": 13.33,
        "max_height": 7.5,
        "description": "Presentation slides",
    },
}


def validate_for_publication(
    spec: FigureSpec,
    target: str,
) -> List[str]:
    """Check spec against venue requirements.

    Args:
        spec: The figure specification to validate.
        target: Venue name (e.g. ``"isca"``, ``"nature"``). Case-insensitive.

    Returns:
        List of warning strings. Empty list means all checks passed.
    """
    target_lower = target.lower()
    reqs = VENUE_REQUIREMENTS.get(target_lower)
    if reqs is None:
        return [f"Unknown venue '{target}'. Available: {', '.join(VENUE_REQUIREMENTS.keys())}"]

    warnings: List[str] = []
    venue_desc: str = reqs.get("description", target)

    # ── Font size checks ──
    min_font: int = reqs.get("min_font", 7)
    if spec.typography is not None:
        tick_size = spec.typography.font_size_ticks
        if tick_size > 0 and tick_size < min_font:
            warnings.append(
                f"Tick font size ({tick_size}pt) below {venue_desc} minimum ({min_font}pt)"
            )
        axis_label_size = spec.typography.font_size_xlabel
        if axis_label_size > 0 and axis_label_size < min_font:
            warnings.append(
                f"Axis label font size ({axis_label_size}pt) below "
                f"{venue_desc} minimum ({min_font}pt)"
            )
        legend_size = spec.typography.font_size_legend
        if legend_size > 0 and legend_size < min_font:
            warnings.append(
                f"Legend font size ({legend_size}pt) below {venue_desc} minimum ({min_font}pt)"
            )

    # ── DPI check ──
    min_dpi: int = reqs.get("min_dpi", 300)
    if spec.dimensions.dpi > 0 and spec.dimensions.dpi < min_dpi:
        warnings.append(f"DPI ({spec.dimensions.dpi}) below {venue_desc} minimum ({min_dpi})")

    # ── Dimension checks (only meaningful when dpi > 1, i.e. inches) ──
    max_width: float = reqs.get("max_width", 99.0)
    max_height: float = reqs.get("max_height", 99.0)
    if spec.dimensions.dpi > 1:
        width_inches = spec.dimensions.width / spec.dimensions.dpi
        height_inches = spec.dimensions.height / spec.dimensions.dpi
        if width_inches > max_width:
            warnings.append(
                f"Figure width ({width_inches:.1f}in) exceeds {venue_desc} max ({max_width}in)"
            )
        if height_inches > max_height:
            warnings.append(
                f"Figure height ({height_inches:.1f}in) exceeds {venue_desc} max ({max_height}in)"
            )

    return warnings
