"""
Type definitions for LaTeX export system.

Defines TypedDict structures for type safety and clear API contracts.
All export-related data structures are defined here.
"""

from typing import Any, Optional, TypedDict


class LaTeXPreset(TypedDict):
    """
    LaTeX export preset configuration.

    Defines paper dimensions, font sizes, and styling for publication-ready exports.
    Used by converters to ensure consistent formatting across journal requirements.

    Attributes:
        width_inches: Figure width in inches (e.g., 3.5 for single column)
        height_inches: Figure height in inches (typically 3:4 or 1:1 aspect ratio)
        font_family: Font family name ("serif", "sans-serif", "Computer Modern", etc.)
        font_size_base: Base font size in points (typically 9-10 for papers)
        font_size_labels: Axis label font size in points
        font_size_title: Title font size in points
        font_size_ticks: Tick label font size in points
        line_width: Default line width in points
        marker_size: Default marker size in points
        dpi: Dots per inch for raster fallback (300-600 for publications)

    Example:
        >>> preset: LaTeXPreset = {
        ...     "width_inches": 3.5,
        ...     "height_inches": 2.625,
        ...     "font_family": "serif",
        ...     "font_size_base": 9,
        ...     "font_size_labels": 8,
        ...     "font_size_title": 10,
        ...     "font_size_ticks": 7,
        ...     "line_width": 1.0,
        ...     "marker_size": 4,
        ...     "dpi": 300,
        ... }
    """

    width_inches: float
    height_inches: float
    font_family: str
    font_size_base: int
    font_size_labels: int
    font_size_title: int
    font_size_ticks: int
    line_width: float
    marker_size: int
    dpi: int


class ExportResult(TypedDict):
    """
    Result of a figure export operation.

    Contains export output data or error information. Used to communicate
    conversion results between layers without raising exceptions in normal flows.

    Attributes:
        success: True if export completed successfully
        data: Binary data of exported figure (PDF, PGF, EPS, etc.) or None if failed
        format: Export format identifier ("pdf", "pgf", "eps", "png", "svg")
        error: Error message if export failed, None otherwise
        metadata: Additional information about export (preserved layout, dimensions, etc.)

    Example:
        >>> result: ExportResult = {
        ...     "success": True,
        ...     "data": b"%PDF-1.4...",
        ...     "format": "pdf",
        ...     "error": None,
        ...     "metadata": {
        ...         "preset_applied": "single_column",
        ...         "layout_preserved": {"legend_x": 0.05, "legend_y": 0.95}
        ...     }
        ... }
    """

    success: bool
    data: Optional[bytes]
    format: str
    error: Optional[str]
    metadata: dict[str, Any]
