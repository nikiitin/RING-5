"""
Plot Configuration Type Definitions for RING-5.

Defines TypedDicts for plot configuration data structures used across
the application. These belong in the core/models layer because they are
pure data definitions with no UI dependencies.

- ShapeConfig: Annotation shape configuration (lines, circles, rectangles)
"""

from typing import Any, Dict, TypedDict, Union


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
