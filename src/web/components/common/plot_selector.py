"""Plot selector component — renders plot selection pills."""

import streamlit as st


class PlotSelectorComponent:
    """Renders plot selection pills and no-plots warning."""

    @staticmethod
    def render_no_plots_warning() -> None:
        """Render a warning when no plots exist yet."""
        st.warning("No plots yet. Create a plot to get started!")

    @staticmethod
    def render(
        plot_names: list[str],
        default_index: int = 0,
    ) -> str:
        """Render a horizontal pills selector for available plots.

        Args:
            plot_names: List of plot display names.
            default_index: Index of the pre-selected plot.

        Returns:
            Name of the selected plot.
        """
        default_name = plot_names[default_index] if plot_names else None
        selected = st.pills(
            "Select Plot",
            plot_names,
            default=default_name,
            key="plot_selector",
        )
        return selected if selected is not None else (plot_names[0] if plot_names else "")
