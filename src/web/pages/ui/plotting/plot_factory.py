"""Factory for creating plot instances."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

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

    _plot_classes: dict[str, Callable[[int, str], BasePlot]] = {
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
        plot_constructor: Callable[[int, str], BasePlot] | None = cls._plot_classes.get(plot_type)
        if plot_constructor is None:
            raise ValueError(f"Unknown plot type: {plot_type}")

        # Subclasses add plot_type in their __init__ before calling super()
        # Type checker doesn't know subclass signatures, but we validate at runtime
        return plot_constructor(plot_id, name)

    @classmethod
    def get_available_plot_types(cls) -> list[str]:
        """
        Get list of available plot types.

        Returns:
            List of plot type identifiers (e.g., ['bar', 'line', 'scatter'])
        """
        return list(cls._plot_classes.keys())

    @classmethod
    def register_plot_type(cls, plot_type: str, plot_class: Callable[[int, str], BasePlot]) -> None:
        """
        Register a new plot type (for extensibility).

        Args:
            plot_type: Identifier for the plot type (e.g., 'heatmap')
            plot_class: Class implementing BasePlot interface (or factory function)

        Raises:
            ValueError: If plot_class is not a subclass of BasePlot.
        """
        if isinstance(plot_class, type):
            from .base_plot import BasePlot

            if not issubclass(plot_class, BasePlot):
                raise ValueError(
                    f"Plot class must be a subclass of BasePlot, got {plot_class.__name__}"
                )
        cls._plot_classes[plot_type] = plot_class  # type: ignore[assignment]
