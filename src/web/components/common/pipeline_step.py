"""Pipeline step component — renders a single shaper step in the pipeline."""

from collections.abc import Callable
from typing import TypedDict

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ShaperStepConfig
from src.web.components.common.pipeline import PipelineComponent


class PipelineStepResult(TypedDict):
    """Result of rendering a single pipeline step."""

    new_config: ShaperStepConfig
    move_up: bool
    move_down: bool
    delete: bool
    preview_data: pd.DataFrame | None
    preview_error: str | None
    step_output: pd.DataFrame | None


class PipelineStepComponent:
    """Renders a single pipeline step (expander with config, controls, preview)."""

    @staticmethod
    def render_step(
        plot_id: int,
        idx: int,
        shaper_type: str,
        shaper_id: int,
        step_input: pd.DataFrame,
        current_config: ShaperStepConfig,
        is_first: bool,
        is_last: bool,
        configure_fn: Callable[
            [str, pd.DataFrame, int, ShaperStepConfig | None, int | None],
            ShaperStepConfig,
        ],
        apply_fn: Callable[
            [pd.DataFrame, list[ShaperStepConfig]],
            pd.DataFrame,
        ],
    ) -> PipelineStepResult:
        """Render a complete pipeline step inside an expander.

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
            apply_fn: Function to apply shapers to data.

        Returns:
            PipelineStepResult with config, actions, and preview data.
        """
        display_name: str = PipelineComponent.REVERSE_MAP.get(shaper_type, shaper_type)

        result: PipelineStepResult = {
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
                    new_config: ShaperStepConfig = configure_fn(
                        shaper_type,
                        step_input,
                        shaper_id,
                        current_config,
                        plot_id,
                    )
                    result["new_config"] = new_config
                except Exception as e:
                    st.exception(e)
                    new_config = current_config

            with c2:
                controls: dict[str, bool] = PipelineComponent.render_shaper_controls(
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
                    st.exception(e)

        return result

    @staticmethod
    def render_finalize_result(processed: pd.DataFrame) -> None:
        """Render the result of a successful pipeline finalization."""
        st.toast(f"Pipeline applied! Shape: {processed.shape}", icon="✅")
        st.dataframe(processed.head(10))

    @staticmethod
    def render_finalize_error(error: str) -> None:
        """Render a pipeline finalization error."""
        st.exception(RuntimeError(error))
