"""Factory for creating plot instances."""

from typing import Dict

from .base_plot import BasePlot
from .types import (
    BarPlot,
    GroupedBarPlot,
    GroupedStackedBarPlot,
    LinePlot,
    ScatterPlot,
)


class PlotFactory:
    """Factory for creating plot instances."""

    _plot_classes: Dict[str, type] = {
        "bar": BarPlot,
        "grouped_bar": GroupedBarPlot,
        "grouped_stacked_bar": GroupedStackedBarPlot,
        "line": LinePlot,
        "scatter": ScatterPlot,
    }

    @classmethod
    def create_plot(cls, plot_type: str, plot_id: int, name: str) -> BasePlot:
        """
        Create a plot instance of the specified type.

        Args:
            plot_type: Type of plot to create
            plot_id: Unique identifier for the plot
            name: Display name for the plot

        Returns:
            Plot instance

        Raises:
            ValueError: If plot_type is not recognized
        """
        plot_class = cls._plot_classes.get(plot_type)
        if plot_class is None:
            raise ValueError(f"Unknown plot type: {plot_type}")

        return plot_class(plot_id, name)

    @classmethod
    def get_available_plot_types(cls) -> list:
        """
        Get list of available plot types.

        Returns:
            List of plot type identifiers
        """
        return list(cls._plot_classes.keys())

    @classmethod
    def register_plot_type(cls, plot_type: str, plot_class: type):
        """
        Register a new plot type (for extensibility).

        Args:
            plot_type: Identifier for the plot type
            plot_class: Class implementing BasePlot
        """
        if not issubclass(plot_class, BasePlot):
            raise ValueError("plot_class must be a subclass of BasePlot")

        cls._plot_classes[plot_type] = plot_class
