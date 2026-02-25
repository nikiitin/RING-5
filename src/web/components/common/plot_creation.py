"""Plot creation component — renders 'Create New Plot' form."""

from typing import Any

import streamlit as st


class PlotCreationComponent:
    """Renders the Create Plot form.

    Uses ``st.form`` to batch text input changes — keystrokes do NOT
    trigger page reruns. Only the submit button fires.
    """

    @staticmethod
    def render(
        default_name: str,
        available_types: list[str],
    ) -> dict[str, Any]:
        """Render plot creation widgets inside a form.

        Args:
            default_name: Default name suggestion for the new plot.
            available_types: Available plot type keys.

        Returns:
            Dict with ``name``, ``plot_type``, ``create_clicked``.
        """
        with st.form("create_plot_form", clear_on_submit=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                name: str = st.text_input("New plot name", value=default_name, key="new_plot_name")
            with col2:
                plot_type: str | None = st.selectbox(
                    "Plot type", options=available_types, key="new_plot_type"
                )
            with col3:
                create_clicked: bool = st.form_submit_button(
                    "Create Plot", use_container_width=True
                )

        return {
            "name": name,
            "plot_type": plot_type,
            "create_clicked": create_clicked,
        }
