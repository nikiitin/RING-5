"""Plot selector component — renders plot identities with their display labels."""

import streamlit as st


class PlotSelectorComponent:
    """Render the active-plot selector and its empty state."""

    @staticmethod
    def render_no_plots_warning() -> None:
        """Render a warning when no plots exist yet."""
        st.warning("No plots yet. Create a plot to get started!")

    @staticmethod
    def render(plot_labels: dict[int, str], *, key: str) -> int:
        """Return the selected plot ID from a prepared, required selector.

        Args:
            plot_labels: Unique display labels indexed by immutable plot IDs.
            key: Namespaced widget key prepared by the UI state owner.

        Returns:
            The selected plot ID.

        Raises:
            RuntimeError: The required selector has no active plot.
        """
        selected = st.pills(
            "Select Plot",
            list(plot_labels),
            format_func=plot_labels.__getitem__,
            required=True,
            key=key,
        )
        if selected is None:
            raise RuntimeError("The plot selector requires an active plot.")
        return selected
