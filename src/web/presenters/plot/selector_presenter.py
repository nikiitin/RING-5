"""
Plot Selector Presenter — renders plot selection UI.

Pure rendering: takes data in, renders widgets, returns selection.
No state reads, no API calls, no side effects beyond widget rendering.
"""

from typing import List

import streamlit as st


class PlotSelectorPresenter:
    """
    Renders plot selection radio buttons.

    Usage::

        presenter = PlotSelectorPresenter()
        selected_name = presenter.render(["Plot 1", "Plot 2"], default_index=0)
    """

    @staticmethod
    def render(
        plot_names: List[str],
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
        selected: str = st.radio(
            "Select Plot",
            plot_names,
            horizontal=True,
            index=default_index,
            key="plot_selector",
        )
        return selected  # type: ignore[return-value]
