"""
Plot Configuration Type Definitions for RING-5.

Defines TypedDicts for plot configuration data structures used across
the application. These belong in the core/models layer because they are
pure data definitions with no UI dependencies.

- ShapeConfig: Annotation shape configuration (lines, circles, rectangles)
"""

from typing import Any, Required, TypedDict


class ShapeConfig(TypedDict, total=False):
    """Type definition for annotation shape configuration.

    Used for horizontal/vertical reference lines, circles, and rectangles
    drawn on plots via Plotly's layout.shapes mechanism.
    """

    type: Required[str]  # "line", "circle", "rect"
    x0: Required[float | str]
    y0: Required[float | str]
    x1: Required[float | str]
    y1: Required[float | str]
    line: dict[str, Any]  # Contains color, width
