"""
Modern plotting system with proper architecture.

This module provides a clean, extensible plotting system with:
- Factory pattern for plot creation
- Easy extensibility for new plot types

Main entry points:
- PlotFactory: Create individual plots programmatically
- BasePlot: Base class for all plot types
"""

from .base_plot import BasePlot
from .plot_factory import PlotFactory
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
]

__version__ = "2.0.0"
