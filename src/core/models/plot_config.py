"""
Plot Configuration Type Definitions for RING-5.

Defines editable plot mappings and annotation-shape data shared across layers.
Resolved figure styling uses the visualization FigureConfig models.

- PlotConfig: Editable plot-specific mappings, including registered extension fields.
- ShapeConfig: Annotation shape configuration (lines, circles, rectangles)
"""

from typing import Any, Required, TypedDict

PlotConfig = dict[str, Any]


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
    line: dict[str, str | float | int]  # Contains color (str), width (float/int)
