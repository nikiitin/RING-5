"""Plot controls component — renders rename, delete, duplicate buttons."""

from typing import Any

import streamlit as st

from src.web.state.ui_state_manager import WidgetKeyBuilder


class PlotControlsComponent:
    """Renders plot management controls (rename, delete, duplicate).

    All methods are ``@staticmethod`` — no instance state.
    """

    @staticmethod
    def render(
        plot_id: int,
        current_name: str,
    ) -> dict[str, Any]:
        """Render plot control widgets.

        Args:
            plot_id: Unique plot ID (for widget keys).
            current_name: Current plot display name.

        Returns:
            Dict with ``new_name``, ``delete_clicked``, ``duplicate_clicked``.
        """
        col1, col2, col3 = st.columns(3)

        with col1:
            new_name: str = st.text_input(
                "Rename plot",
                value=current_name,
                key=WidgetKeyBuilder.plot_key(plot_id, "widgets.rename"),
            )

        with col2:
            delete_clicked: bool = st.button(
                "Delete",
                key=WidgetKeyBuilder.plot_key(plot_id, "widgets.delete_plot"),
                type="tertiary",
            )

        with col3:
            duplicate_clicked: bool = st.button(
                "Duplicate",
                key=WidgetKeyBuilder.plot_key(plot_id, "widgets.dup_plot"),
                type="tertiary",
            )

        return {
            "new_name": new_name,
            "delete_clicked": delete_clicked,
            "duplicate_clicked": duplicate_clicked,
        }
