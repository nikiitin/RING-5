"""
Save Dialog Presenter — renders the "Save Pipeline" dialog UI.

Pure rendering: renders widgets, returns user input.
The controller handles the actual save operation.
"""

from typing import Any, Dict

import streamlit as st


class SaveDialogPresenter:
    """
    Renders the Save Pipeline dialog.

    Usage::

        result = SaveDialogPresenter.render(plot_id=1, plot_name="My Plot")
        if result["save_clicked"]:
            api.save_pipeline(result["pipeline_name"], ...)
    """

    @staticmethod
    def render(
        plot_id: int,
        plot_name: str,
    ) -> Dict[str, Any]:
        """
        Render save pipeline dialog widgets inside a form.

        Uses ``st.form`` to batch text input — keystrokes do NOT trigger
        page reruns. Only Save/Cancel buttons fire.

        Args:
            plot_id: Plot ID for widget key uniqueness.
            plot_name: Current plot name (used as default pipeline name).

        Returns:
            Dict with:
                - pipeline_name (str): Entered pipeline name.
                - save_clicked (bool): Save button clicked.
                - cancel_clicked (bool): Cancel button clicked.
        """
        st.markdown("---")
        st.markdown(f"### Save Pipeline for '{plot_name}'")

        with st.form(f"save_pipeline_form_{plot_id}", clear_on_submit=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                pipeline_name: str = st.text_input(
                    "Pipeline Name",
                    value=f"{plot_name}_pipeline",
                    key=f"save_p_name_{plot_id}",
                )
            with col2:
                st.write("")
                st.write("")
                save_clicked: bool = st.form_submit_button(
                    "Save", type="primary", use_container_width=True
                )

        # Cancel outside the form (forms can only have one submit button)
        cancel_clicked: bool = st.button("Cancel", key=f"cancel_save_{plot_id}")

        return {
            "pipeline_name": pipeline_name,
            "save_clicked": save_clicked,
            "cancel_clicked": cancel_clicked,
        }
