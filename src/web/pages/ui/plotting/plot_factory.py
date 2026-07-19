"""Factory for creating plot instances."""

from __future__ import annotations

from collections.abc import Callable
from io import StringIO
from typing import TYPE_CHECKING, Any, TypedDict

import pandas as pd

if TYPE_CHECKING:
    from .base_plot import BasePlot

from .types import (
    BarPlot,
    DualAxisBarDotPlot,
    GroupedBarPlot,
    GroupedStackedBarPlot,
    HeatmapPlot,
    HistogramPlot,
    LinePlot,
    ScatterPlot,
    StackedBarPlot,
)


class PlotTypeMetadata(TypedDict):
    """Metadata describing a plot type for UI presentation."""

    display_name: str
    icon: str
    category: str  # "basic", "comparison", "distribution"


class PlotFactory:
    """Create plots from a registry that supports runtime extension."""

    _plot_classes: dict[str, Callable[[int, str], BasePlot]] = {
        "bar": BarPlot,
        "dual_axis_bar_dot": DualAxisBarDotPlot,
        "grouped_bar": GroupedBarPlot,
        "heatmap": HeatmapPlot,
        "stacked_bar": StackedBarPlot,
        "grouped_stacked_bar": GroupedStackedBarPlot,
        "histogram": HistogramPlot,
        "line": LinePlot,
        "scatter": ScatterPlot,
    }

    _plot_metadata: dict[str, PlotTypeMetadata] = {
        "bar": {"display_name": "Bar Chart", "icon": "bar_chart", "category": "basic"},
        "line": {"display_name": "Line Chart", "icon": "show_chart", "category": "basic"},
        "scatter": {"display_name": "Scatter Plot", "icon": "scatter_plot", "category": "basic"},
        "grouped_bar": {
            "display_name": "Grouped Bar",
            "icon": "bar_chart",
            "category": "comparison",
        },
        "stacked_bar": {
            "display_name": "Stacked Bar",
            "icon": "stacked_bar_chart",
            "category": "comparison",
        },
        "grouped_stacked_bar": {
            "display_name": "Grouped Stacked Bar",
            "icon": "stacked_bar_chart",
            "category": "comparison",
        },
        "dual_axis_bar_dot": {
            "display_name": "Dual Axis Bar Dot",
            "icon": "waterfall_chart",
            "category": "comparison",
        },
        "heatmap": {"display_name": "Heatmap", "icon": "grid_on", "category": "distribution"},
        "histogram": {"display_name": "Histogram", "icon": "bar_chart", "category": "distribution"},
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
            available = ", ".join(cls.get_available_plot_types())
            raise ValueError(f"Unknown plot type {plot_type!r}. Available types: {available}.")

        # Subclasses add plot_type in their __init__ before calling super()
        # Type checker doesn't know subclass signatures, but we validate at runtime
        return plot_constructor(plot_id, name)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BasePlot:
        """Restore a plot and its state from :meth:`BasePlot.to_dict` output.

        Args:
            data: Serialized plot mapping.

        Returns:
            Restored plot instance.
        """
        plot = cls.create_plot(
            plot_type=data["plot_type"],
            plot_id=data["id"],
            name=data["name"],
        )
        plot.config = data.get("config", {})
        plot.pipeline = data.get("pipeline", [])
        plot.pipeline_counter = data.get("pipeline_counter", 0)
        plot.legend_mappings_by_column = data.get("legend_mappings_by_column", {})
        plot.legend_mappings = data.get("legend_mappings", {})

        processed_data = data.get("processed_data")
        if processed_data:
            plot.replace_processed_data(pd.read_csv(StringIO(processed_data)))
        return plot

    @classmethod
    def get_available_plot_types(cls) -> list[str]:
        """
        Get list of available plot types.

        Returns:
            List of plot type identifiers (e.g., ['bar', 'line', 'scatter'])
        """
        return list(cls._plot_classes.keys())

    @classmethod
    def get_plot_metadata(cls) -> dict[str, PlotTypeMetadata]:
        """
        Get metadata for all registered plot types.

        Returns:
            Dictionary mapping plot type identifiers to their metadata.
        """
        # [impl->req~ring5.extension.plot-registry~1]
        return dict(cls._plot_metadata)

    @classmethod
    def register_plot_type(
        cls,
        plot_type: str,
        plot_class: Callable[[int, str], BasePlot],
        metadata: PlotTypeMetadata | None = None,
    ) -> None:
        """
        Register a new plot type (for extensibility).

        Args:
            plot_type: Identifier for the plot type (e.g., 'heatmap')
            plot_class: Class implementing BasePlot interface (or factory function)
            metadata: Optional metadata for UI presentation

        Raises:
            ValueError: If plot_class is not a subclass of BasePlot.
        """
        # [impl->req~ring5.extension.plot-registry~1]
        if isinstance(plot_class, type):
            from .base_plot import BasePlot

            if not issubclass(plot_class, BasePlot):
                raise ValueError(
                    f"Plot class must be a subclass of BasePlot, got {plot_class.__name__}"
                )
        cls._plot_classes[plot_type] = plot_class  # type: ignore[assignment]
        if metadata is not None:
            cls._plot_metadata[plot_type] = metadata
