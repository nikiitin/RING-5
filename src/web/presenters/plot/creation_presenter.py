"""
Plot Creation Presenter — renders "Create New Plot" section.

Returns the user's input (name, type, button click) without performing
any creation logic. The controller decides what to do with the result.
"""

from typing import Any, Dict, List, Optional

import streamlit as st


class PlotCreationPresenter:
    """
    Renders the Create Plot form.

    Usage::

        result = PlotCreationPresenter.render("Plot 3", ["bar", "line"])
        if result["create_clicked"] and result["plot_type"]:
            controller.create_plot(result["name"], result["plot_type"])
    """

    @staticmethod
    def render(
        default_name: str,
        available_types: List[str],
    ) -> Dict[str, Any]:
        """
        Render plot creation widgets inside a form.

        Uses ``st.form`` to batch text input changes — keystrokes do NOT
        trigger page reruns. Only the "Create Plot" submit button fires.

        Args:
            default_name: Default name suggestion for the new plot.
            available_types: Available plot type keys.

        Returns:
            Dict with:
                - name (str): Entered plot name.
                - plot_type (Optional[str]): Selected plot type.
                - create_clicked (bool): Whether Create was clicked.
        """
        with st.form("create_plot_form", clear_on_submit=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                name: str = st.text_input("New plot name", value=default_name, key="new_plot_name")
            with col2:
                plot_type: Optional[str] = st.selectbox(
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
