"""Persistent, workspace-derived guidance for a complete analysis."""

from __future__ import annotations

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import GuidedAnalysisProgress, GuidedAnalysisStage


class GuidedAnalysisComponent:
    """Show the next useful workflow action without replacing advanced controls."""

    EXPORT_STATE_KEY = "_guided_analysis_exported"

    @classmethod
    def render(cls, api: ApplicationAPI) -> None:
        """Render current progress and direct navigation in the application sidebar."""
        # [impl->req~ring5.workspace.guided-analysis~1]
        progress = api.guided_analysis_progress(
            exported=bool(st.session_state.get(cls.EXPORT_STATE_KEY, False))
        )
        with st.expander(f"Guided analysis · {progress.percent_complete}%", expanded=False):
            st.progress(progress.percent_complete, text=cls._progress_text(progress))
            if progress.complete:
                st.success("Analysis workflow complete. You can keep refining it with any control.")
            else:
                stage = next(item for item in progress.stages if item.status == "current")
                stage_number = progress.stages.index(stage) + 1
                st.markdown(f"**Step {stage_number} of {progress.total_stages}: {stage.title}**")
                st.caption(stage.description)
                st.info(stage.detail)
                if st.button(
                    stage.action_label,
                    key=f"guided_analysis_action_{stage.stage_id}",
                    type="primary",
                    width="stretch",
                ):
                    cls.activate(stage)
                    st.rerun()

            with st.expander("All steps", expanded=False):
                cls._render_checklist(progress)
            st.caption("The full workspace and advanced controls remain available at every step.")

    @staticmethod
    def activate(stage: GuidedAnalysisStage) -> None:
        """Navigate to the validated page associated with one workflow stage."""
        # [impl->req~ring5.workspace.guided-analysis~1]
        destinations = {"Data Source", "Data Managers", "Manage Plots"}
        if not isinstance(stage, GuidedAnalysisStage):
            raise TypeError("Guided analysis actions require a GuidedAnalysisStage.")
        if stage.destination not in destinations:
            raise ValueError(f"Unsupported guided destination {stage.destination!r}.")
        st.session_state["_nav_page"] = stage.destination

    @classmethod
    def mark_exported(cls) -> None:
        """Record that this browser workflow initiated a figure download."""
        # [impl->req~ring5.workspace.guided-analysis~1]
        st.session_state[cls.EXPORT_STATE_KEY] = True

    @staticmethod
    def _progress_text(progress: GuidedAnalysisProgress) -> str:
        """Return a concise textual progress equivalent for the progress bar."""
        return f"{progress.completed_stages} of {progress.total_stages} steps complete"

    @staticmethod
    def _render_checklist(progress: GuidedAnalysisProgress) -> None:
        """Render all stages with redundant text status rather than color alone."""
        labels = {"complete": "Complete", "current": "Next", "blocked": "Waiting"}
        for index, stage in enumerate(progress.stages, start=1):
            st.markdown(f"**{index}. {stage.title} — {labels[stage.status]}**")
            st.caption(stage.detail)
