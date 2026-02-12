"""
Pipeline Presenter — renders the shaper pipeline editor UI.

Renders the list of shapers with config, preview, reorder, and
add/remove controls. Returns user actions without performing them.
"""

from typing import Any, Dict, Optional

import streamlit as st


class PipelinePresenter:
    """
    Renders the data processing pipeline editor.

    Responsible for:
        - "Add transformation" selector + button
        - Per-shaper config widgets (delegates to configure_shaper)
        - Per-shaper preview tables
        - Reorder (up/down) and delete buttons
        - "Finalize Pipeline" button

    Does NOT:
        - Apply shapers
        - Modify pipeline state
        - Trigger reruns
    """

    SHAPER_DISPLAY_MAP: Dict[str, str] = {
        "Column Selector": "columnSelector",
        "Sort": "sort",
        "Mean Calculator": "mean",
        "Normalize": "normalize",
        "Filter": "conditionSelector",
        "Transformer": "transformer",
    }

    REVERSE_MAP: Dict[str, str] = {v: k for k, v in SHAPER_DISPLAY_MAP.items()}

    @staticmethod
    def render_section_header() -> None:
        """Render the pipeline section header."""
        st.markdown("### Data Processing Pipeline")

    @staticmethod
    def render_pipeline_label() -> None:
        """Render the 'Current Pipeline' label."""
        st.markdown("**Current Pipeline:**")

    @staticmethod
    def render_add_shaper(plot_id: int) -> Dict[str, Any]:
        """
        Render the "Add transformation" selector and Add button.

        Args:
            plot_id: Plot ID for widget key uniqueness.

        Returns:
            Dict with:
                - add_clicked (bool): Whether Add was clicked.
                - shaper_type (str): Internal shaper type key.
        """
        col1, col2 = st.columns([3, 1])
        with col1:
            display_type: Optional[str] = st.selectbox(
                "Add transformation",
                list(PipelinePresenter.SHAPER_DISPLAY_MAP.keys()),
                key=f"shaper_add_{plot_id}",
            )
        with col2:
            add_clicked: bool = st.button(
                "Add to Pipeline",
                width="stretch",
                key=f"add_shaper_btn_{plot_id}",
            )

        shaper_type: str = PipelinePresenter.SHAPER_DISPLAY_MAP.get(
            display_type or "", "columnSelector"
        )
        return {"add_clicked": add_clicked, "shaper_type": shaper_type}

    @staticmethod
    def render_shaper_controls(
        plot_id: int,
        idx: int,
        shaper_type: str,
        is_first: bool,
        is_last: bool,
    ) -> Dict[str, bool]:
        """
        Render up/down/delete controls for a single shaper step.

        Args:
            plot_id: Plot ID for key uniqueness.
            idx: Step index in the pipeline.
            shaper_type: Internal shaper type key.
            is_first: Whether this is the first step.
            is_last: Whether this is the last step.

        Returns:
            Dict with:
                - move_up (bool): Up button clicked.
                - move_down (bool): Down button clicked.
                - delete (bool): Delete button clicked.
        """
        result: Dict[str, bool] = {
            "move_up": False,
            "move_down": False,
            "delete": False,
        }

        c2, c3, c4 = st.columns([1, 1, 1])
        with c2:
            if not is_first:
                result["move_up"] = st.button("Up", key=f"up_{plot_id}_{idx}")
        with c3:
            if not is_last:
                result["move_down"] = st.button("Down", key=f"down_{plot_id}_{idx}")
        with c4:
            result["delete"] = st.button("Del", key=f"del_{plot_id}_{idx}")

        return result

    @staticmethod
    def render_finalize_button(plot_id: int) -> bool:
        """
        Render the "Finalize Pipeline for Plotting" button.

        Args:
            plot_id: Plot ID for key uniqueness.

        Returns:
            True if button was clicked.
        """
        clicked: bool = st.button(
            "Finalize Pipeline for Plotting",
            type="primary",
            width="stretch",
            key=f"finalize_{plot_id}",
        )
        return clicked
