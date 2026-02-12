"""
Chart Presenter — renders refresh controls for the chart area.

Provides the auto-refresh toggle and manual Refresh button that determine
whether the controller should regenerate the Plotly figure.  Actual figure
display is delegated to the ChartDisplay protocol (wired via adapters).
"""

from typing import Any, Dict

import streamlit as st


class ChartPresenter:
    """
    Renders the interactive chart area refresh controls.

    Usage::

        controls = ChartPresenter.render_refresh_controls(
            plot_id=1, auto_refresh=True, config_changed=True
        )
        if controls["should_generate"]:
            chart_display.render_chart(plot, should_generate=True)
    """

    @staticmethod
    def render_refresh_controls(
        plot_id: int,
        auto_refresh: bool,
        config_changed: bool,
    ) -> Dict[str, Any]:
        """
        Render auto-refresh toggle and manual Refresh button.

        Args:
            plot_id: Plot ID for unique keys.
            auto_refresh: Current auto-refresh state.
            config_changed: Whether config changed since last render.

        Returns:
            Dict with:
                - auto_refresh (bool): New toggle state.
                - manual_refresh (bool): Refresh button clicked.
                - should_generate (bool): Whether to regenerate figure.
        """
        r1, r2 = st.columns([1, 3])
        with r1:
            new_auto: bool = st.toggle(
                "Auto-refresh",
                value=auto_refresh,
                key=f"auto_t_{plot_id}",
            )
        with r2:
            manual: bool = st.button("Refresh Plot", key=f"refresh_{plot_id}", width="stretch")

        should_generate: bool = manual or (new_auto and config_changed)

        return {
            "auto_refresh": new_auto,
            "manual_refresh": manual,
            "should_generate": should_generate,
        }
