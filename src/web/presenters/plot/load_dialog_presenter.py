"""
Load Dialog Presenter — renders the "Load Pipeline" dialog UI.

Pure rendering: renders widgets, returns user selection.
The controller handles the actual load operation.
"""

from typing import Any, Dict, List, Optional

import streamlit as st


class LoadDialogPresenter:
    """
    Renders the Load Pipeline dialog.

    Usage::

        result = LoadDialogPresenter.render(
            plot_id=1, available_pipelines=["pipe1", "pipe2"]
        )
        if result["load_clicked"]:
            api.load_pipeline(result["selected_pipeline"])
    """

    @staticmethod
    def render_empty(plot_id: int) -> Dict[str, Any]:
        """
        Render the dialog when no pipelines are available.

        Args:
            plot_id: Plot ID for widget key uniqueness.

        Returns:
            Dict with:
                - close_clicked (bool): Close button clicked.
        """
        st.markdown("---")
        st.markdown("### Load Pipeline")
        st.warning("No saved pipelines found.")
        close_clicked: bool = st.button("Close", key=f"close_load_{plot_id}")
        return {"close_clicked": close_clicked}

    @staticmethod
    def render(
        plot_id: int,
        available_pipelines: List[str],
    ) -> Dict[str, Any]:
        """
        Render load pipeline dialog widgets.

        Args:
            plot_id: Plot ID for widget key uniqueness.
            available_pipelines: List of saved pipeline names.

        Returns:
            Dict with:
                - selected_pipeline (Optional[str]): Selected pipeline name.
                - load_clicked (bool): Load button clicked.
                - cancel_clicked (bool): Cancel button clicked.
        """
        st.markdown("---")
        st.markdown("### Load Pipeline")

        selected: Optional[str] = st.selectbox(
            "Select Pipeline",
            available_pipelines,
            key=f"load_p_sel_{plot_id}",
        )

        load_clicked: bool = st.button("Load", type="primary", key=f"load_p_btn_{plot_id}")
        cancel_clicked: bool = st.button("Cancel", key=f"cancel_load_{plot_id}")

        return {
            "selected_pipeline": selected,
            "load_clicked": load_clicked,
            "cancel_clicked": cancel_clicked,
        }
