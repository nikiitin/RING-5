"""
Modern plotting system with proper architecture.

This module provides a clean, extensible plotting system with:
- Separation of concerns (Plot, Renderer, Styler, Factory)
- Factory pattern for plot creation
- Easy extensibility for new plot types

Main entry points:
- PlotFactory: Create individual plots programmatically
- PlotRenderer: Render plots with customization
- BasePlot: Base class for all plot types
"""

from .base_plot import BasePlot
from .plot_factory import PlotFactory
from .plot_renderer import PlotRenderer
from .types import (
    BarPlot,
    DualAxisBarDotPlot,
    GroupedBarPlot,
    GroupedStackedBarPlot,
    LinePlot,
    ScatterPlot,
)

__all__ = [
    "BasePlot",
    "BarPlot",
    "DualAxisBarDotPlot",
    "GroupedBarPlot",
    "GroupedStackedBarPlot",
    "LinePlot",
    "ScatterPlot",
    "PlotFactory",
    "PlotRenderer",
]

__version__ = "2.0.0"
