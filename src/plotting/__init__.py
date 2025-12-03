"""
Modern plotting system with proper architecture.

This module provides a clean, extensible plotting system with:
- Separation of concerns (Plot, Renderer, Styler, Factory)
- Factory pattern for plot creation
- Multiprocessing support via PlotWorkPool integration
- Easy extensibility for new plot types

Main entry points:
- PlotManager: High-level interface for generating plots
- PlotFactory: Create individual plots programmatically
- PlotRenderer: Render plots to files

Example usage:
    >>> from src.plotting import PlotManager
    >>> manager = PlotManager('data.csv', 'output/')
    >>> plot_configs = [{'type': 'bar', 'data': {'x': 'bench', 'y': 'time'}, ...}]
    >>> manager.generate_plots(plot_configs, use_multiprocessing=True)
"""

# Main interfaces
from .plot_manager import PlotManager
from .factory.plot_factory import PlotFactory
from .renderer.plot_renderer import PlotRenderer

# Base classes for extension
from .base.plot import Plot
from .styling.plot_styler import PlotStyler

# Concrete plot types
from .plots import BarPlot, LinePlot, ScatterPlot, BoxPlot, HeatmapPlot

# Work implementation for multiprocessing
from .work.plot_work_impl import PlotWorkImpl

__all__ = [
    # Main interfaces
    'PlotManager',
    'PlotFactory',
    'PlotRenderer',
    
    # Base classes
    'Plot',
    'PlotStyler',
    
    # Plot types
    'BarPlot',
    'LinePlot',
    'ScatterPlot',
    'BoxPlot',
    'HeatmapPlot',
    
    # Multiprocessing
    'PlotWorkImpl',
]

__version__ = '2.0.0'
