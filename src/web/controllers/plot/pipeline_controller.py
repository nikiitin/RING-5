"""
Pipeline Controller — orchestrates the shaper pipeline editor.

Handles:
    - Adding/removing/reordering shapers in the pipeline
    - Computing intermediate data at each step
    - Previewing shaper output
    - Finalizing the pipeline (applying all shapers to raw data)

Dependencies are injected via protocols (no concrete imports from pages.ui).
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.models.plot_protocols import PipelineExecutor, PlotHandle
from src.web.presenters.plot.pipeline_presenter import PipelinePresenter
from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


class PipelineController:
    """
    Orchestrates the shaper pipeline: add, remove, reorder, preview, finalize.

    Single Responsibility: managing the data transformation pipeline for a plot.
    Does NOT handle plot creation, config, or rendering.

    Dependencies are injected via protocols — no concrete imports from
    ``pages.ui.plotting.*`` or ``pages.ui.shaper_config``.
    """

    def __init__(
        self,
        api: ApplicationAPI,
        ui_state: UIStateManager,
        pipeline_executor: PipelineExecutor,
    ) -> None:
        """
        Initialize with dependency injection.

        Args:
            api: Application API for data access.
            ui_state: UI state manager (currently unused but available).
            pipeline_executor: Pipeline operations (apply/configure shapers).
        """
        self._api: ApplicationAPI = api
        self._ui: UIStateManager = ui_state
        self._pipeline: PipelineExecutor = pipeline_executor

    def render(self, plot: PlotHandle) -> None:
        """
        Render the complete pipeline editor for a plot.

        Steps:
            1. Show "Add transformation" selector
            2. Show current pipeline steps with config/preview
            3. Show "Finalize" button

        Args:
            plot: The plot whose pipeline to edit.
        """
        PipelinePresenter.render_section_header()

        raw_data: Optional[pd.DataFrame] = self._api.state_manager.get_data()
        if raw_data is None:
            st.warning("Please upload data first!")
            return

        # 1. Add shaper (via presenter)
        add_result: Dict[str, Any] = PipelinePresenter.render_add_shaper(plot.plot_id)
        if add_result["add_clicked"]:
            plot.pipeline.append(
                {
                    "id": plot.pipeline_counter,
                    "type": add_result["shaper_type"],
                    "config": {},
                }
            )
            plot.pipeline_counter += 1
            st.rerun()

        # 2. Pipeline steps (via PipelineStepPresenter)
        if plot.pipeline:
            PipelinePresenter.render_pipeline_label()
            self._handle_pipeline_steps(plot, raw_data)

        # 3. Finalize (via presenter)
        if plot.pipeline:
            if PipelinePresenter.render_finalize_button(plot.plot_id):
                self._handle_finalize(plot, raw_data)

    def _handle_pipeline_steps(self, plot: PlotHandle, raw_data: pd.DataFrame) -> None:
        """
        Render and handle each pipeline step via PipelineStepPresenter.

        Uses incremental computation: each step's output becomes the next
        step's input, avoiding the O(n²) re-computation of applying all
        previous shapers from scratch at each step.

        Args:
            plot: The plot holding the pipeline.
            raw_data: The original uploaded data (before any shapers).
        """
        step_input: pd.DataFrame = raw_data
        for idx, shaper in enumerate(plot.pipeline):
            try:
                # Render step via presenter
                result: Dict[str, Any] = PipelineStepPresenter.render_step(
                    plot_id=plot.plot_id,
                    idx=idx,
                    shaper_type=shaper["type"],
                    shaper_id=shaper["id"],
                    step_input=step_input,
                    current_config=shaper.get("config", {}),
                    is_first=(idx == 0),
                    is_last=(idx == len(plot.pipeline) - 1),
                    configure_fn=self._pipeline.configure_shaper,
                    apply_fn=self._pipeline.apply_shapers,
                )
            except Exception as e:
                # Show error but keep rendering subsequent steps
                st.error(f"Step {idx + 1} error: {e}")
                logger.error(
                    "PIPELINE: Step %d crashed in plot %r: %s",
                    idx,
                    str(plot.name).replace("\n", ""),
                    e,
                    exc_info=True,
                )
                # Don't advance step_input — next step gets last good data
                continue

            # Update config from presenter
            shaper["config"] = result["new_config"]

            # Handle actions (orchestration stays in controller)
            if result["move_up"]:
                plot.pipeline[idx], plot.pipeline[idx - 1] = (
                    plot.pipeline[idx - 1],
                    plot.pipeline[idx],
                )
                st.rerun()
            if result["move_down"]:
                plot.pipeline[idx], plot.pipeline[idx + 1] = (
                    plot.pipeline[idx + 1],
                    plot.pipeline[idx],
                )
                st.rerun()
            if result["delete"]:
                plot.pipeline.pop(idx)
                st.rerun()

            # Advance step_input for next step using already-computed output
            if result.get("step_output") is not None:
                step_input = result["step_output"]

            # Log preview errors
            if result["preview_error"]:
                logger.error(
                    "PIPELINE: Preview failure for shaper index %d " "in plot %r: %s",
                    idx,
                    str(plot.name).replace("\n", ""),
                    result["preview_error"],
                )

    def _handle_finalize(self, plot: PlotHandle, raw_data: pd.DataFrame) -> None:
        """
        Apply the full pipeline to raw data and store the result.

        Args:
            plot: The plot to finalize.
            raw_data: Original uploaded data.
        """
        try:
            confs: List[Dict[str, Any]] = [s["config"] for s in plot.pipeline if s["config"]]
            processed: pd.DataFrame = self._pipeline.apply_shapers(raw_data, confs)
            plot.processed_data = processed
            PipelineStepPresenter.render_finalize_result(processed)
        except Exception as e:
            PipelineStepPresenter.render_finalize_error(str(e))
