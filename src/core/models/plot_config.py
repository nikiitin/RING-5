"""
Plot Configuration Type Definitions for RING-5.

Defines editable plot mappings and annotation-shape data shared across layers.
Resolved figure styling uses the visualization FigureConfig models.

- PlotConfig: Editable plot-specific mappings, including registered extension fields.
- ShapeConfig: Native annotation shape fields retained by the web editor.
"""

from typing import Any, TypedDict

PlotConfig = dict[str, Any]


class ShapeConfig(TypedDict, total=False):
    """Type definition for annotation shape configuration.

    UI-created lines, circles and rectangles specify their type and coordinates.
    Native defaults, omitted coordinates and SVG paths remain intact when edited.
    Text coordinates retain exact category labels and date strings.
    """

    type: str | None
    x0: float | str | None
    y0: float | str | None
    x1: float | str | None
    y1: float | str | None
    path: str
    xref: str
    yref: str
    line: dict[str, str | float | int]  # Contains color (str), width (float/int)
