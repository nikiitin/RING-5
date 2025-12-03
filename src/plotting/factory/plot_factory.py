"""
PlotFactory creates appropriate plot instances based on configuration.
Implements Factory Pattern for plot creation.
"""
import pandas as pd
from typing import Dict, Any

from src.plotting.base.plot import Plot
from src.plotting.plots.bar_plot import BarPlot
from src.plotting.plots.line_plot import LinePlot
from src.plotting.plots.scatter_plot import ScatterPlot
from src.plotting.plots.box_plot import BoxPlot
from src.plotting.plots.heatmap_plot import HeatmapPlot


class PlotFactory:
    """
    Factory for creating plot instances.
    
    Follows Factory Pattern: centralizes object creation logic.
    Follows Open/Closed Principle: easy to add new plot types without modifying existing code.
    """
    
    # Registry of available plot types
    PLOT_TYPES = {
        'bar': BarPlot,
        'line': LinePlot,
        'scatter': ScatterPlot,
        'box': BoxPlot,
        'heatmap': HeatmapPlot,
        # Aliases
        'barplot': BarPlot,
        'lineplot': LinePlot,
        'scatterplot': ScatterPlot,
        'boxplot': BoxPlot,
    }
    
    @staticmethod
    def create_plot(data: pd.DataFrame, config: Dict[str, Any]) -> Plot:
        """
        Create a plot instance based on configuration.
        
        Args:
            data: DataFrame containing plot data
            config: Plot configuration dictionary (must include 'type' field)
            
        Returns:
            Plot instance of appropriate type
            
        Raises:
            ValueError: If plot type is unknown or configuration is invalid
        """
        if 'type' not in config:
            raise ValueError("Plot configuration must include 'type' field")
        
        plot_type = config['type'].lower()
        
        if plot_type not in PlotFactory.PLOT_TYPES:
            available_types = ', '.join(sorted(PlotFactory.PLOT_TYPES.keys()))
            raise ValueError(
                f"Unknown plot type: '{plot_type}'. "
                f"Available types: {available_types}"
            )
        
        # Get the appropriate plot class
        plot_class = PlotFactory.PLOT_TYPES[plot_type]
        
        # Create and return plot instance
        return plot_class(data, config)
    
    @classmethod
    def register_plot_type(cls, name: str, plot_class: type) -> None:
        """
        Register a new plot type.
        
        Allows extending the factory with custom plot types.
        
        Args:
            name: Name for the plot type
            plot_class: Class that inherits from Plot
            
        Raises:
            TypeError: If plot_class doesn't inherit from Plot
        """
        if not issubclass(plot_class, Plot):
            raise TypeError(f"{plot_class} must inherit from Plot base class")
        
        cls.PLOT_TYPES[name.lower()] = plot_class
    
    @classmethod
    def get_available_types(cls) -> list:
        """
        Get list of available plot types.
        
        Returns:
            List of registered plot type names
        """
        return sorted(set(cls.PLOT_TYPES.keys()))
