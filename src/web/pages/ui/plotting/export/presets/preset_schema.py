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
    # Font sizes for different text elements
    font_size_title: int  # Title font size
    font_size_xlabel: int  # X-axis label font size
    font_size_ylabel: int  # Y-axis label font size
    font_size_legend: int  # Legend text font size
    font_size_ticks: int  # Tick labels font size (X-axis)
    font_size_yticks: int  # Y-axis tick labels font size (separate from X)
    font_size_annotations: int  # Annotations (bar totals, etc.) font size
    # Bold styling controls for text elements
    bold_title: bool  # Title in bold (default False)
    bold_xlabel: bool  # X-axis label in bold (default False)
    bold_ylabel: bool  # Y-axis label in bold (default False)
    bold_legend: bool  # Legend text in bold (default False)
    bold_ticks: bool  # Tick labels in bold (default False)
    bold_annotations: bool  # Annotations in bold (default True for bar values)
    bold_group_labels: bool  # X-axis grouping labels in bold (default True)
    line_width: float
    marker_size: int
    dpi: int
    # Legend spacing parameters (all relative to font size)
    legend_columnspacing: float  # Space between columns (default 2.0)
    legend_handletextpad: float  # Space between color box and text (default 0.8)
    legend_labelspacing: float  # Vertical space between items (default 0.5)
    legend_handlelength: float  # Length of color box (default 2.0)
    legend_handleheight: float  # Height of color box (default 0.7)
    legend_borderpad: float  # Space inside legend border (default 0.4)
    legend_borderaxespad: float  # Space between legend and axes (default 0.5)
    legend_ncol: int  # Number of legend columns (0 = auto, default 0)
    # Positioning parameters for fine-grained control
    ylabel_pad: float  # Padding between Y-axis label and tick labels (default 10)
    ylabel_y_position: float  # Vertical position of Y-axis label (0=bottom, 0.5=center, 1=top)
    xtick_pad: float  # Padding between X-axis tick labels and axis (default 5)
    ytick_pad: float  # Padding between Y-axis tick labels and axis (default 5)
    group_label_offset: float  # Vertical offset for grouping labels (default -0.12)
    group_label_alternate: bool  # Alternate grouping labels up/down (default True)
    group_label_alt_spacing: float  # Distance between up/down levels (default 0.05)
    # Axis and bar spacing parameters
    xaxis_margin: float  # Left/right margin on X-axis as fraction (default 0.02)
    bar_width_scale: float  # Scale factor for bar widths (default 1.0, >1 = wider)
    xtick_rotation: float  # Rotation angle for X-axis tick labels (default 45)
    xtick_ha: str  # Horizontal alignment for X-tick labels ("left", "center", "right")
    xtick_offset: float  # Horizontal offset for X-tick labels in points (default 0)
    # Legend position (for export)
    legend_custom_pos: bool  # Enable custom legend position (default False = auto)
    legend_x: float  # X position of legend (0=left, 1=right, default 0.0)
    legend_y: float  # Y position of legend (0=bottom, 1=top, default 1.0)
    # Group separator for final group (e.g., arithmetic mean)
    group_separator: bool  # Draw vertical separator before last group (default False)
    group_separator_style: str  # Line style: "dashed", "dotted", "solid" (default "dashed")
    group_separator_color: str  # Color of separator line (default "gray")
    # LaTeX preamble for font matching
    latex_extra_preamble: str  # Extra LaTeX preamble packages (default "")


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
