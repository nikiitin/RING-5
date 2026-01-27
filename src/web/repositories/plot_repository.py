"""
Plot Repository
Single Responsibility: Manage plot objects and plot counter state.
"""

import logging
from typing import List, Optional

import streamlit as st

from src.plotting import BasePlot

logger = logging.getLogger(__name__)


class PlotRepository:
    """
    Repository for managing plot objects and plot lifecycle.

    Responsibilities:
    - Store and retrieve plot objects
    - Manage plot counter for ID generation
    - Track current active plot
    - Plot list operations (add, remove, clear)

    Adheres to SRP: Only manages plot state, nothing else.
    """

    # State keys
    PLOTS_KEY = "plots_objects"
    PLOT_COUNTER_KEY = "plot_counter"
    CURRENT_PLOT_ID_KEY = "current_plot_id"

    @staticmethod
    def get_plots() -> List[BasePlot]:
        """
        Retrieve all plot objects.

        Returns:
            List of BasePlot instances (empty list if none exist)
        """
        plots = st.session_state.get(PlotRepository.PLOTS_KEY, [])
        return plots if plots else []

    @staticmethod
    def set_plots(plots: List[BasePlot]) -> None:
        """
        Replace the entire plot list.

        Args:
            plots: New list of plot objects
        """
        st.session_state[PlotRepository.PLOTS_KEY] = plots
        logger.info(f"PLOT_REPO: Plots updated - {len(plots)} total plots")

    @staticmethod
    def add_plot(plot: BasePlot) -> None:
        """
        Add a new plot to the collection.

        Args:
            plot: Plot instance to add
        """
        plots = PlotRepository.get_plots()
        plots.append(plot)
        PlotRepository.set_plots(plots)
        logger.info(f"PLOT_REPO: Plot added - ID {plot.plot_id}, Type {plot.plot_type}")

    @staticmethod
    def remove_plot(plot_id: int) -> bool:
        """
        Remove a plot by its ID.

        Args:
            plot_id: ID of plot to remove

        Returns:
            True if plot was found and removed, False otherwise
        """
        plots = PlotRepository.get_plots()
        initial_count = len(plots)
        plots = [p for p in plots if p.plot_id != plot_id]

        if len(plots) < initial_count:
            PlotRepository.set_plots(plots)
            logger.info(f"PLOT_REPO: Plot removed - ID {plot_id}")
            return True

        logger.warning(f"PLOT_REPO: Plot not found for removal - ID {plot_id}")
        return False

    @staticmethod
    def clear_plots() -> None:
        """Clear all plots from the collection."""
        st.session_state[PlotRepository.PLOTS_KEY] = []
        logger.info("PLOT_REPO: All plots cleared")

    @staticmethod
    def get_plot_counter() -> int:
        """
        Get the current plot counter (for ID generation).

        Returns:
            Current counter value (0 if not initialized)
        """
        return st.session_state.get(PlotRepository.PLOT_COUNTER_KEY, 0)

    @staticmethod
    def set_plot_counter(counter: int) -> None:
        """
        Set the plot counter value.

        Args:
            counter: New counter value
        """
        st.session_state[PlotRepository.PLOT_COUNTER_KEY] = counter

    @staticmethod
    def increment_plot_counter() -> int:
        """
        Increment and return the next plot ID.

        Returns:
            Next available plot ID
        """
        current = PlotRepository.get_plot_counter()
        PlotRepository.set_plot_counter(current + 1)
        logger.debug(f"PLOT_REPO: Plot counter incremented to {current + 1}")
        return current

    @staticmethod
    def get_current_plot_id() -> Optional[int]:
        """
        Get the currently active plot ID.

        Returns:
            Active plot ID or None if no plot is active
        """
        return st.session_state.get(PlotRepository.CURRENT_PLOT_ID_KEY)

    @staticmethod
    def set_current_plot_id(plot_id: Optional[int]) -> None:
        """
        Set the currently active plot ID.

        Args:
            plot_id: Plot ID to set as active (None to clear)
        """
        st.session_state[PlotRepository.CURRENT_PLOT_ID_KEY] = plot_id
        if plot_id is not None:
            logger.debug(f"PLOT_REPO: Current plot set to ID {plot_id}")
