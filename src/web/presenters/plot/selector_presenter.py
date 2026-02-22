"""
Plot Selector Presenter — renders plot selection UI.

Pure rendering: takes data in, renders widgets, returns selection.
No state reads, no API calls, no side effects beyond widget rendering.
"""

import streamlit as st


class PlotSelectorPresenter:
    """
    Renders plot selection radio buttons.

    Usage::

        presenter = PlotSelectorPresenter()
        selected_name = presenter.render(["Plot 1", "Plot 2"], default_index=0)
    """

    @staticmethod
    def render_no_plots_warning() -> None:
        """Render a warning when no plots exist yet."""
        st.warning("No plots yet. Create a plot to get started!")

    @staticmethod
    def render(
        plot_names: list[str],
        default_index: int = 0,
    ) -> str:
        """
        Render a horizontal radio selector for available plots.

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
