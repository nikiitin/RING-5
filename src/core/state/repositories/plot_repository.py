"""In-memory repository for plots and active selection."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from src.core.common.plot_render_state import PlotRenderBinding, PlotRenderState

from src.core.models.plot_protocol import PlotProtocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PlotRetirement:
    """Retain the admitted object's exact render generation for later disposal."""

    plot: PlotProtocol
    state: PlotRenderState[Any]
    binding: PlotRenderBinding[Any] | None

    @classmethod
    def capture(cls, plot: PlotProtocol) -> "PlotRetirement":
        """Capture ownership without running foreign plot lifecycle methods."""
        state = plot.render_state
        return cls(plot, state, state.snapshot())

    def detach(self) -> PlotRenderBinding[Any] | None:
        """Detach the captured binding while leaving newer generations untouched."""
        return self.state.detach(self.binding)


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

    def set_plots(self, plots: list[PlotProtocol]) -> tuple[PlotRetirement, ...]:
        """
        Replace the entire plot list.

        Args:
            plots: New list of plot objects.

        Returns:
            Captured removals for the state transaction owner's deferred cleanup.
        """
        replacement = list(plots)
        removed = self.removed_bindings(replacement)
        self._plots = replacement
        logger.info("PLOT_REPO: Plots updated - %d total plots", len(plots))
        return removed

    def removed_bindings(self, retained: list[PlotProtocol]) -> tuple[PlotRetirement, ...]:
        """Capture removed identities for the transaction owner's post-publication cleanup."""
        # [impl->req~ring5.plots.delete~1]
        retained_ids = {id(plot) for plot in retained}
        removed = {id(plot): plot for plot in self._plots if id(plot) not in retained_ids}
        return tuple(PlotRetirement.capture(plot) for plot in removed.values())

    def add_plot(self, plot: PlotProtocol) -> None:
        """
        Add a new plot to the collection.

        Args:
            plot: Plot instance to add
        """
        self._plots.append(plot)
        logger.info("PLOT_REPO: Plot added - ID %s, Type %s", plot.plot_id, plot.plot_type)

    def clear_plots(self) -> tuple[PlotRetirement, ...]:
        """Clear the collection and return exact bindings to retire after publication."""
        removed = self.set_plots([])
        logger.info("PLOT_REPO: All plots cleared")
        return removed

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
