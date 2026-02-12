"""
Plot Models — Pure data definitions for plot configuration.

Consolidates scattered TypedDicts (ShapeConfig, SeriesStyle from base_plot.py)
and defines new ones (ShaperStep, PlotDisplayConfig) as the canonical type
vocabulary for the web layer.

These models are **framework-agnostic**: no Streamlit, no Plotly imports.
They can be used in tests, serialization, and domain logic without side effects.

Design Principle:
    - TypedDict for serializable config (JSON-compatible)
    - total=False for optional fields (progressive disclosure)
    - Specific types over Dict[str, Any] wherever possible
"""

from typing import Any, Dict, List, Optional, Union

from typing_extensions import TypedDict

# ─── Annotation Shapes ───────────────────────────────────────────────────────


class AnnotationLineConfig(TypedDict, total=False):
    """Line styling for annotation shapes."""

    color: str
    width: int


class AnnotationShapeConfig(TypedDict, total=False):
    """
    Configuration for a plot annotation shape (line, circle, rect).

    Consolidated from base_plot.py ShapeConfig. Used in the 'shapes' list
    within plot config.
    """

    type: str  # "line", "circle", "rect"
    x0: Union[float, str]
    y0: Union[float, str]
    x1: Union[float, str]
    y1: Union[float, str]
    line: AnnotationLineConfig


# ─── Series Styling ──────────────────────────────────────────────────────────


class SeriesStyleConfig(TypedDict, total=False):
    """
    Per-series visual styling (color, marker, pattern, display name).

    Consolidated from base_plot.py SeriesStyle. Stored in config['series_styles']
    as Dict[str, SeriesStyleConfig] keyed by series value.
    """

    name: str  # Custom display name
    color: str  # Hex color code (e.g., "#FF5733")
    marker_symbol: str  # For scatter plots (circle, square, diamond, ...)
    pattern: str  # For bar charts (/, \\, x, -, |, +, .)


# ─── Relayout Events ────────────────────────────────────────────────────────


class RelayoutEventData(TypedDict, total=False):
    """
    Typed wrapper for Plotly relayout event data.

    Consolidated from base_plot.py RelayoutData. Represents the subset of
    relayout events we track (zoom, legend drag, legend title edit).
    """

    # Axis ranges (zoom/pan)
    xaxis_range: List[float]
    yaxis_range: List[float]
    xaxis_autorange: bool
    yaxis_autorange: bool

    # Legend position (drag)
    legend_x: float
    legend_y: float
    legend_xanchor: str
    legend_yanchor: str
    legend_title_text: str


# ─── Shaper Step ─────────────────────────────────────────────────────────────


class ShaperStep(TypedDict):
    """
    A single step in a data processing pipeline.

    Currently stored as List[Dict[str, Any]] on BasePlot.pipeline.
    This TypedDict formalizes the contract.
    """

    id: int  # Unique step ID within the pipeline
    type: str  # Shaper type key (columnSelector, sort, mean, ...)
    config: Dict[str, Any]  # Shaper-specific configuration


# ─── Layout & Dimensions ────────────────────────────────────────────────────


class MarginsConfig(TypedDict, total=False):
    """Plot margin configuration in pixels."""

    top: int
    bottom: int
    left: int
    right: int


class TypographyConfig(TypedDict, total=False):
    """Font size and color configuration for plot text elements."""

    font_size: int
    title_font_size: int
    xaxis_title_font_size: int
    yaxis_title_font_size: int
    legend_font_size: int
    tick_font_size: int
    title_color: str
    xaxis_title_color: str
    yaxis_title_color: str


class PlotDisplayConfig(TypedDict, total=False):
    """
    Complete display configuration for a plot.

    This is the **canonical schema** for everything that controls how a plot
    looks. It replaces the ad-hoc Dict[str, Any] that BasePlot.config currently
    uses. Fields are optional (total=False) because plots progressively
    accumulate configuration as the user interacts.

    Sections:
        - Identity: x, y, title, labels
        - Appearance: colors, dimensions, margins, typography
        - Interaction: zoom ranges, legend positions
        - Advanced: ordering, shapes, error bars, export
    """

    # ── Identity & Axes ──
    x: str  # X-axis column name
    y: str  # Y-axis column name
    title: str  # Plot title text
    xlabel: str  # X-axis label
    ylabel: str  # Y-axis label
    legend_title: str  # Legend title text

    # ── Grouping ──
    color: Optional[str]  # Color-by column
    group: Optional[str]  # Group-by column (grouped/stacked bars)

    # ── Column Metadata (computed, not user-set) ──
    numeric_cols: List[str]
    categorical_cols: List[str]

    # ── Dimensions & Layout ──
    width: int  # Plot width in pixels
    height: int  # Plot height in pixels
    margins: MarginsConfig
    template: str  # Plotly template name

    # ── Typography ──
    typography: TypographyConfig

    # ── Colors & Background ──
    paper_bgcolor: str
    plot_bgcolor: str
    show_grid: bool
    grid_color: str
    grid_width: int

    # ── Axis Configuration ──
    xaxis_tickangle: int  # Label rotation (-90 to 90)
    xaxis_dtick: Optional[float]  # X-axis step (None = auto)
    yaxis_dtick: Optional[float]  # Y-axis step (None = auto)
    xaxis_labels: Dict[str, str]  # Renamed x-axis tick labels

    # ── Ordering ──
    xaxis_order: Optional[List[str]]  # Custom x-axis category order
    group_order: Optional[List[str]]  # Custom group order
    legend_order: Optional[List[str]]  # Custom legend item order

    # ── Interactive State (from relayout events) ──
    range_x: Optional[List[float]]  # Current zoom range for x-axis
    range_y: Optional[List[float]]  # Current zoom range for y-axis
    legend_x: Optional[float]  # Legend x position
    legend_y: Optional[float]  # Legend y position
    legend_xanchor: Optional[str]  # Legend x anchor
    legend_yanchor: Optional[str]  # Legend y anchor

    # ── Legend Labels ──
    legend_labels: Optional[Dict[str, str]]  # Original → display label

    # ── Series Styling ──
    series_styles: Dict[str, SeriesStyleConfig]

    # ── Annotations ──
    shapes: List[AnnotationShapeConfig]

    # ── Error Bars ──
    show_error_bars: bool

    # ── Bar-specific ──
    bargap: float  # Spacing between bars
    bargroupgap: float  # Spacing between groups
    bar_border_width: float  # Border width for stacked segments

    # ── Export ──
    download_format: str  # "html", "png", "pdf", "svg"
    export_scale: int  # 1, 2, or 3

    # ── Interactivity ──
    enable_editable: bool  # Enable drag/edit on plot
