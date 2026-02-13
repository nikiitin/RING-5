"""
Plot Configuration Type Definitions for RING-5.

Defines TypedDicts for plot configuration data structures used across
the application. These belong in the core/models layer because they are
pure data definitions with no UI dependencies.

- ShapeConfig: Annotation shape configuration (lines, circles, rectangles)
- SeriesStyle: Per-series styling (color, marker, pattern, display name)
- RelayoutData: Plotly relayout event data (zoom, pan, legend drag)
"""

from typing import Any, Dict, List, TypedDict, Union


class ShapeConfig(TypedDict, total=False):
    """Type definition for annotation shape configuration.

    Used for horizontal/vertical reference lines, circles, and rectangles
    drawn on plots via Plotly's layout.shapes mechanism.
    """

    type: str  # "line", "circle", "rect"
    x0: Union[float, str]
    y0: Union[float, str]
    x1: Union[float, str]
    y1: Union[float, str]
    line: Dict[str, Any]  # Contains color, width


class SeriesStyle(TypedDict, total=False):
    """Type definition for series styling (color, shape, name).

    Each series in a plot can have individual styling overrides.
    Keys in the series_styles config dict map trace names to SeriesStyle.
    """

    name: str  # Display name
    color: str  # Hex color code
    marker_symbol: str  # For scatter plots
    pattern_shape: str  # For bars


class RelayoutData(TypedDict, total=False):
    """Type definition for Plotly relayout event data.

    Captures user interactions with the plot such as zoom, pan,
    and legend repositioning. Used by update_from_relayout() to
    preserve interactive state across Streamlit reruns.
    """

    # Axis ranges
    xaxis_range: List[float]
    yaxis_range: List[float]
    xaxis_autorange: bool
    yaxis_autorange: bool
    # Legend position
    legend_x: float
    legend_y: float
    legend_xanchor: str
    legend_yanchor: str
    legend_title_text: str
