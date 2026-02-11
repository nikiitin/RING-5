"""
Pipeline Step Presenter — renders a single shaper step in the pipeline.

Combines the step expander, shaper config widget, reorder/delete controls,
and data preview into a single presenter. Returns user actions without
performing them.

This presenter replaces the inline rendering that was in
PipelineController._render_pipeline_steps.
"""

from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.web.presenters.plot.pipeline_presenter import PipelinePresenter


class PipelineStepPresenter:
    """
    Renders a single pipeline step (expander with config, controls, preview).

    Usage::

        result = PipelineStepPresenter.render_step(
            plot_id=1, idx=0, shaper_type="sort",
            step_input=df, config={}, is_first=True, is_last=False,
            configure_fn=configure_shaper, apply_fn=apply_shapers,
        )
        if result["move_up"]: ...
    """

    @staticmethod
    def render_step(
        plot_id: int,
        idx: int,
        shaper_type: str,
        shaper_id: int,
        step_input: pd.DataFrame,
        current_config: Dict[str, Any],
        is_first: bool,
        is_last: bool,
        configure_fn: Callable[
            [str, pd.DataFrame, int, Dict[str, Any], Optional[int]],
            Dict[str, Any],
        ],
        apply_fn: Callable[
            [pd.DataFrame, List[Dict[str, Any]]],
            pd.DataFrame,
        ],
    ) -> Dict[str, Any]:
        """
        Render a complete pipeline step inside an expander.

        Args:
            plot_id: Plot ID for widget key uniqueness.
            idx: Step index in the pipeline.
            shaper_type: Internal shaper type key.
            shaper_id: Unique shaper instance ID.
            step_input: DataFrame input for this step.
            current_config: Current shaper configuration.
            is_first: Whether this is the first step.
            is_last: Whether this is the last step.
            configure_fn: Function to render shaper-specific config UI.
                Signature: (type, data, id, config, owner_id=) -> config
            apply_fn: Function to apply shapers to data.
                Signature: (data, [config]) -> DataFrame

        Returns:
            Dict with:
                - new_config (Dict): Updated shaper configuration.
                - move_up (bool): Up button clicked.
                - move_down (bool): Down button clicked.
                - delete (bool): Delete button clicked.
                - preview_data (Optional[DataFrame]): Preview output (head) or None.
                - preview_error (Optional[str]): Preview error message or None.
                - step_output (Optional[DataFrame]): Full output for incremental
                  computation. Used by the controller as the next step's input
                  to avoid O(n²) re-computation.
        """
        display_name: str = PipelinePresenter.REVERSE_MAP.get(shaper_type, shaper_type)

        result: Dict[str, Any] = {
            "new_config": current_config,
            "move_up": False,
            "move_down": False,
            "delete": False,
            "preview_data": None,
            "preview_error": None,
            "step_output": None,
        }

        with st.expander(f"{idx + 1}. {display_name}", expanded=True):
            c1, c2 = st.columns([3, 1])

            with c1:
                try:
                    new_config: Dict[str, Any] = configure_fn(
                        shaper_type,
                        step_input,
                        shaper_id,
                        current_config,
                        plot_id,
                    )
                    result["new_config"] = new_config
                except Exception as e:
                    st.error(f"Configuration error: {e}")
                    new_config = current_config

            with c2:
                controls: Dict[str, bool] = PipelinePresenter.render_shaper_controls(
                    plot_id=plot_id,
                    idx=idx,
                    shaper_type=shaper_type,
                    is_first=is_first,
                    is_last=is_last,
                )
                result["move_up"] = controls["move_up"]
                result["move_down"] = controls["move_down"]
                result["delete"] = controls["delete"]

            # Preview
            if new_config:
                try:
                    output: pd.DataFrame = apply_fn(step_input, [new_config])
                    result["step_output"] = output
                    result["preview_data"] = output.head(5)
                    st.dataframe(result["preview_data"])
                except Exception as e:
                    result["preview_error"] = str(e)
                    st.error(f"Preview error: {e}")

        return result

    @staticmethod
    def render_finalize_result(
        processed: pd.DataFrame,
    ) -> None:
        """
        Render the result of a successful pipeline finalization.

        Args:
            processed: The finalized DataFrame.
        """
        st.success(f"Pipeline applied! Shape: {processed.shape}")
        st.dataframe(processed.head(10))

    @staticmethod
    def render_finalize_error(error: str) -> None:
        """
        Render a pipeline finalization error.

        Args:
            error: Error message string.
        """
        st.error(f"Error: {error}")
