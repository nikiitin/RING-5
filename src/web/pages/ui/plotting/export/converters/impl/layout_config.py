"""
Configuration dataclasses for layout application.

These classes encapsulate configuration parameters extracted from LaTeX presets,
making them explicit, type-safe, and reusable across different layout appliers.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class FontStyleConfig:
    """
    Font size and bold styling configuration.

    All font sizes are in points. Bold flags control fontweight='bold' application.
    """

    font_size_title: int = 10
    font_size_xlabel: int = 9
    font_size_ylabel: int = 9
    font_size_ticks: int = 7
    font_size_annotations: int = 6
    bold_title: bool = False
    bold_xlabel: bool = False
    bold_ylabel: bool = False
    bold_ticks: bool = False
    bold_annotations: bool = True  # Bar values bold by default


@dataclass
class PositioningConfig:
    """
    Element positioning and spacing configuration.

    Controls padding, rotation, alignment, and positioning of various elements.
    All padding values are in points, rotation in degrees, positions in 0-1 range.
    """

    # Y-axis label positioning
    ylabel_pad: float = 10.0  # Distance from tick labels (points)
    ylabel_y_position: float = 0.5  # Vertical position (0=bottom, 0.5=center, 1=top)

    # Tick padding and formatting
    xtick_pad: float = 5.0  # Distance from axis (points)
    ytick_pad: float = 5.0  # Distance from axis (points)
    xtick_rotation: float = 45.0  # Rotation angle (degrees)
    xtick_ha: Literal["left", "center", "right"] = "right"  # Horizontal alignment
    xtick_offset: float = 0.0  # Horizontal offset (points)

    # Axis margins
    xaxis_margin: float = 0.02  # Margin as fraction of data range

    # Grouping label positioning (for grouped-stacked bars)
    group_label_offset: float = -0.12  # Vertical offset below axis (axes fraction)
    group_label_alternate: bool = True  # Alternate up/down positioning


@dataclass
class SeparatorConfig:
    """
    Group separator line configuration.

    Controls vertical separator lines drawn between groups in grouped-stacked bar charts.
    """

    enabled: bool = False
    style: Literal["solid", "dashed", "dotted", "dashdot"] = "dashed"
    color: str = "gray"
