"""
Plot Service - Plot Lifecycle Management.

Handles creation, rendering, and management of plot objects in the web UI.
Coordinates plot factory, state persistence, and configuration updates.
"""

import copy
import logging
from typing import TYPE_CHECKING
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory

if TYPE_CHECKING:
    from src.core.state.state_manager import StateManager

logger = logging.getLogger(__name__)


class PlotService:
    """Service to handle plot lifecycle and management."""

    @staticmethod
    def create_plot(name: str, plot_type: str, state_manager: "StateManager") -> BasePlot:
        """Create a new plot and add it to the session state."""
        plot_id = state_manager.start_next_plot_id()
        plot = PlotFactory.create_plot(plot_type=plot_type, plot_id=plot_id, name=name)

        state_manager.add_plot(plot)
        state_manager.set_current_plot_id(plot_id)

        return plot

    @staticmethod
    def delete_plot(plot_id: int, state_manager: "StateManager") -> None:
        """Delete a plot by ID."""
        plots = state_manager.get_plots()
        plots = [p for p in plots if p.plot_id != plot_id]
        state_manager.set_plots(plots)

        # If deleted current plot, reset selection
        if state_manager.get_current_plot_id() == plot_id:
            state_manager.set_current_plot_id(None if not plots else plots[0].plot_id)

    @staticmethod
    def duplicate_plot(plot: BasePlot, state_manager: "StateManager") -> BasePlot:
        """Duplicate an existing plot."""
        new_plot = copy.deepcopy(plot)
        new_plot.plot_id = state_manager.start_next_plot_id()
        new_plot.name = f"{plot.name} (copy)"
        new_plot.invalidate_figure()

        state_manager.add_plot(new_plot)

        return new_plot

    @staticmethod
    def change_plot_type(plot: BasePlot, new_type: str, state_manager: "StateManager") -> BasePlot:
        """Change the type of an existing plot, preserving configuration where possible."""
        if plot.plot_type == new_type:
            return plot

        new_plot = PlotFactory.create_plot(new_type, plot.plot_id, plot.name)
        new_plot.pipeline = plot.pipeline
        new_plot.pipeline_counter = plot.pipeline_counter
        new_plot.replace_processed_data(plot.processed_data)
        new_plot.config = {}  # Reset config when type changes

        # Replace in session state
        plots = state_manager.get_plots()
        try:
            # Find index by object identity or ID
            idx = next(i for i, p in enumerate(plots) if p.plot_id == plot.plot_id)
            plots[idx] = new_plot
        except StopIteration:
            # Old plot not in the list (unexpected): still persist the new plot so
            # the returned object isn't orphaned outside session state.
            logger.warning(
                "Plot ID %d not found during type change; appending the new plot",
                plot.plot_id,
            )
            plots.append(new_plot)
        state_manager.set_plots(plots)

        return new_plot
