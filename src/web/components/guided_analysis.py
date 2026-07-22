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
        cls._render_progress(progress)

    @classmethod
    def render_fragmented(cls, api: ApplicationAPI) -> None:
        """Render guidance and briefly poll while an export is outstanding."""
        # [impl->req~ring5.workspace.guided-analysis~1]
        initial_progress = api.guided_analysis_progress(
            exported=bool(st.session_state.get(cls.EXPORT_STATE_KEY, False))
        )
        poll_for_export = initial_progress.current_stage == "export"
        first_progress = [initial_progress]

        def _render_guide() -> None:
            progress = (
                first_progress.pop()
                if first_progress
                else api.guided_analysis_progress(
                    exported=bool(st.session_state.get(cls.EXPORT_STATE_KEY, False))
                )
            )
            if poll_for_export and progress.complete:
                # Stop the polling fragment by rebuilding the full app. The new
                # guide is complete and therefore has no automatic interval.
                st.rerun(scope="app")
            cls._render_progress(progress)

        st.fragment(_render_guide, run_every=1 if poll_for_export else None)()

    @classmethod
    def _render_progress(cls, progress: GuidedAnalysisProgress) -> None:
        """Render one assessed workflow state."""
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
