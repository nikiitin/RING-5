"""Plot controls component — renders rename, delete, duplicate buttons."""

from typing import Any

import streamlit as st


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
                "Rename plot", value=current_name, key=f"rename_{plot_id}"
            )

        with col2:
            delete_clicked: bool = st.button(
                "Delete", key=f"delete_plot_{plot_id}", type="tertiary"
            )

        with col3:
            duplicate_clicked: bool = st.button(
                "Duplicate", key=f"dup_plot_{plot_id}", type="tertiary"
            )

        return {
            "new_name": new_name,
            "delete_clicked": delete_clicked,
            "duplicate_clicked": duplicate_clicked,
        }
