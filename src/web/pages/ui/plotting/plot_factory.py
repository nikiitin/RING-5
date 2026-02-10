"""Factory for creating plot instances."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Type

if TYPE_CHECKING:
    from .base_plot import BasePlot

from .types import (
    BarPlot,
    DualAxisBarDotPlot,
    GroupedBarPlot,
    GroupedStackedBarPlot,
    HistogramPlot,
    LinePlot,
    ScatterPlot,
    StackedBarPlot,
)


class PlotFactory:
    """
    Factory for creating plot instances.

    Uses the Factory pattern to centralize plot creation and maintain
    a registry of available plot types. Supports runtime registration
    of new plot types for extensibility.
    """

    _plot_classes: Dict[str, Type[BasePlot]] = {
        "bar": BarPlot,
        "dual_axis_bar_dot": DualAxisBarDotPlot,
        "grouped_bar": GroupedBarPlot,
        "stacked_bar": StackedBarPlot,
        "grouped_stacked_bar": GroupedStackedBarPlot,
        "histogram": HistogramPlot,
        "line": LinePlot,
        "scatter": ScatterPlot,
    }

    @classmethod
    def create_plot(cls, plot_type: str, plot_id: int, name: str) -> BasePlot:
        """
        Create a plot instance of the specified type.

        Args:
            plot_type: Type of plot to create (bar, line, scatter, etc.)
            plot_id: Unique identifier for the plot
            name: Display name for the plot

        Returns:
            Plot instance of the requested type

        Raises:
            ValueError: If plot_type is not recognized
        """
        plot_class: Type[BasePlot] | None = cls._plot_classes.get(plot_type)
        if plot_class is None:
            raise ValueError(f"Unknown plot type: {plot_type}")

        # Subclasses add plot_type in their __init__ before calling super()
        # Type checker doesn't know subclass signatures, but we validate at runtime
        return plot_class(plot_id, name)  # type: ignore[call-arg]

    @classmethod
    def get_available_plot_types(cls) -> List[str]:
        """
        Get list of available plot types.

        Returns:
            List of plot type identifiers (e.g., ['bar', 'line', 'scatter'])
        """
        return list(cls._plot_classes.keys())

    @classmethod
    def register_plot_type(cls, plot_type: str, plot_class: Type[BasePlot]) -> None:
        """
        Register a new plot type (for extensibility).

        Args:
            plot_type: Identifier for the plot type (e.g., 'heatmap')
            plot_class: Class implementing BasePlot interface

        Raises:
            ValueError: If plot_class is not a subclass of BasePlot
        """
        # Deferred import to avoid circular dependency at runtime
        from .base_plot import BasePlot as _BasePlot

        if not issubclass(plot_class, _BasePlot):
            raise ValueError("plot_class must be a subclass of BasePlot")

        cls._plot_classes[plot_type] = plot_class
