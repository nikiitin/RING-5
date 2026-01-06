from typing import List, Optional, Any
import copy
import streamlit as st
from src.plotting import PlotFactory, BasePlot
from src.web.state_manager import StateManager

class PlotService:
    """Service to handle plot lifecycle and management."""

    @staticmethod
    def create_plot(name: str, plot_type: str) -> BasePlot:
        """Create a new plot and add it to the session state."""
        plot_id = StateManager.start_next_plot_id()
        plot = PlotFactory.create_plot(
            plot_type=plot_type,
            plot_id=plot_id,
            name=name
        )
        
        plots = StateManager.get_plots()
        plots.append(plot)
        StateManager.set_plots(plots)
        StateManager.set_current_plot_id(plot_id)
        
        return plot

    @staticmethod
    def delete_plot(plot_id: int) -> None:
        """Delete a plot by ID."""
        plots = StateManager.get_plots()
        # Filter out the plot to delete
        new_plots = [p for p in plots if p.plot_id != plot_id]
        StateManager.set_plots(new_plots)
        
        # If deleted current plot, reset selection
        if StateManager.get_current_plot_id() == plot_id:
            StateManager.set_current_plot_id(None if not new_plots else new_plots[0].plot_id)

    @staticmethod
    def duplicate_plot(plot: BasePlot) -> BasePlot:
        """Duplicate an existing plot."""
        new_plot = copy.deepcopy(plot)
        new_plot.plot_id = StateManager.start_next_plot_id()
        new_plot.name = f"{plot.name} (copy)"
        # Clear non-serializable data
        new_plot.last_generated_fig = None
        
        plots = StateManager.get_plots()
        plots.append(new_plot)
        StateManager.set_plots(plots)
        
        return new_plot

    @staticmethod
    def change_plot_type(plot: BasePlot, new_type: str) -> BasePlot:
        """Change the type of an existing plot, preserving configuration where possible."""
        if plot.plot_type == new_type:
            return plot

        new_plot = PlotFactory.create_plot(new_type, plot.plot_id, plot.name)
        new_plot.pipeline = plot.pipeline
        new_plot.pipeline_counter = plot.pipeline_counter
        new_plot.processed_data = plot.processed_data
        new_plot.config = {}  # Reset config when type changes
        
        # Replace in session state
        plots = StateManager.get_plots()
        try:
            # Find index by object identity or ID
            idx = next(i for i, p in enumerate(plots) if p.plot_id == plot.plot_id)
            plots[idx] = new_plot
            StateManager.set_plots(plots)
        except StopIteration:
            # Should not happen if checking logic is correct
            pass
            
        return new_plot


