"""In-memory repository for plots and active selection."""

from __future__ import annotations

import logging

from src.core.models import PlotProtocol

logger = logging.getLogger(__name__)


class PlotRepository:
    """Store plots, allocate IDs, and track the active plot."""

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._plots: list[PlotProtocol] = []
        self._plot_counter: int = 0
        self._current_plot_id: int | None = None

    def get_plots(self) -> list[PlotProtocol]:
        """
        Retrieve all plot objects.

        Returns:
            A shallow copy of the plot list (defensive copy-on-read) — callers
            may reorder/filter it freely and persist via ``set_plots``.
        """
        return list(self._plots)

    def set_plots(self, plots: list[PlotProtocol]) -> None:
        """
        Replace the entire plot list.

        Args:
            plots: New list of plot objects
        """
        self._plots = plots
        logger.info("PLOT_REPO: Plots updated - %d total plots", len(plots))

    def add_plot(self, plot: PlotProtocol) -> None:
        """
        Add a new plot to the collection.

        Args:
            plot: Plot instance to add
        """
        self._plots.append(plot)
        logger.info("PLOT_REPO: Plot added - ID %s, Type %s", plot.plot_id, plot.plot_type)

    def remove_plot(self, plot_id: int) -> bool:
        """
        Remove a plot by its ID.

        Args:
            plot_id: ID of plot to remove

        Returns:
            True if plot was found and removed, False otherwise
        """
        initial_count = len(self._plots)
        self._plots = [p for p in self._plots if p.plot_id != plot_id]

        if len(self._plots) < initial_count:
            logger.info("PLOT_REPO: Plot removed - ID %s", plot_id)
            return True

        logger.warning(f"PLOT_REPO: Plot not found for removal - ID {plot_id}")
        return False

    def clear_plots(self) -> None:
        """Clear all plots from the collection."""
        self._plots = []
        logger.info("PLOT_REPO: All plots cleared")

    def get_plot_counter(self) -> int:
        """
        Get the current plot counter (for ID generation).

        Returns:
            Current counter value
        """
        return self._plot_counter

    def set_plot_counter(self, counter: int) -> None:
        """
        Set the plot counter value.

        Args:
            counter: New counter value
        """
        self._plot_counter = counter

    def increment_plot_counter(self) -> int:
        """Allocate and return the next plot identifier."""
        current = self._plot_counter
        self._plot_counter += 1
        return current

    def get_current_plot_id(self) -> int | None:
        """
        Get the currently active plot ID.

        Returns:
            Active plot ID or None if no plot is active
        """
        return self._current_plot_id

    def set_current_plot_id(self, plot_id: int | None) -> None:
        """
        Set the currently active plot ID.

        Args:
            plot_id: Plot ID to set as active (None to clear)
        """
        self._current_plot_id = plot_id
        if plot_id is not None:
            logger.debug(f"PLOT_REPO: Current plot set to ID {plot_id}")
