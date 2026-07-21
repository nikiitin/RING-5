"""Human-first filtering and editing for workspace favorites and tags."""

from __future__ import annotations

import hashlib

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import WorkspaceArtifact, WorkspaceArtifactKind

_KIND_OPTIONS: dict[str, WorkspaceArtifactKind | None] = {
    "Everything": None,
    "Variables": "variable",
    "Datasets": "dataset",
    "Plots": "plot",
    "Pipelines": "pipeline",
    "Portfolios": "portfolio",
}
_KIND_LABELS = {
    "variable": "Variable",
    "dataset": "Dataset",
    "plot": "Plot",
    "pipeline": "Pipeline",
    "portfolio": "Portfolio",
}


class WorkspaceOrganizerComponent:
    """Let people filter, favorite, tag, and reopen discoverable artifacts."""

    @classmethod
    def render(cls, api: ApplicationAPI) -> None:
        """Render one bounded organizer in the persistent application sidebar."""
        # [impl->req~ring5.workspace.favorites-tags~1]
        with st.expander("Favorites & tags", expanded=False):
            kind_label = st.selectbox(
                "Artifact type",
                tuple(_KIND_OPTIONS),
                key="_workspace_organizer_kind",
            )
            kind = _KIND_OPTIONS[kind_label]
            try:
                unfiltered = api.list_workspace_artifacts(kind=kind, limit=100)
            except (OSError, TypeError, ValueError) as exc:
                st.error(f"Workspace organizer is unavailable: {exc}")
                return
            selected_tags = st.multiselect(
                "Filter by tags",
                unfiltered.available_tags,
                key="_workspace_organizer_tags",
                placeholder="Any tag",
            )
            favorites_only = st.checkbox(
                "Favorites only",
                key="_workspace_organizer_favorites_only",
            )
            try:
                response = api.list_workspace_artifacts(
                    kind=kind,
                    tags=tuple(selected_tags),
                    favorites_only=favorites_only,
                    limit=100,
                )
            except (OSError, TypeError, ValueError) as exc:
                st.error(f"Could not apply workspace filters: {exc}")
                return
            if response.index_truncated:
                st.warning(
                    f"Indexed {response.indexed_artifacts:,} of "
                    f"{response.available_artifacts:,} artifacts."
                )
            if not response.artifacts:
                st.info("No artifacts match these filters.")
                return

            artifact = st.selectbox(
                "Artifact",
                response.artifacts,
                format_func=cls._label,
                key="_workspace_organizer_artifact",
            )
            widget_suffix = hashlib.sha256(
                f"{artifact.kind}\0{artifact.identifier}".encode("utf-8")
            ).hexdigest()[:12]
            tags_text = st.text_input(
                "Tags",
                value=", ".join(artifact.tags),
                key=f"_workspace_organizer_edit_tags_{widget_suffix}",
                placeholder="nightly, paper, regression",
                help="Up to 16 tags; letters, numbers, spaces, underscores, and hyphens.",
            )
            favorite = st.checkbox(
                "Favorite",
                value=artifact.favorite,
                key=f"_workspace_organizer_edit_favorite_{widget_suffix}",
            )
            if st.button(
                "Save organization",
                key=f"_workspace_organizer_save_{widget_suffix}",
                use_container_width=True,
                type="primary",
            ):
                tags = tuple(tag.strip() for tag in tags_text.split(",") if tag.strip())
                try:
                    api.set_workspace_artifact_metadata(
                        artifact.kind,
                        artifact.identifier,
                        tags=tags,
                        favorite=favorite,
                    )
                except (KeyError, OSError, TypeError, ValueError) as exc:
                    st.error(f"Could not save organization: {exc}")
                else:
                    st.success("Favorite and tags saved.")
                    st.rerun()
            if st.button(
                "Open selected artifact",
                key=f"_workspace_organizer_open_{widget_suffix}",
                use_container_width=True,
                type="tertiary",
            ):
                try:
                    cls.activate(api, artifact)
                except (KeyError, TypeError, ValueError) as exc:
                    st.error(f"Could not open {artifact.title}: {exc}")
                else:
                    st.rerun()

            shown = f"{response.returned_matches} of {response.total_matches} matches"
            st.caption(shown if response.results_truncated else f"{response.total_matches} matches")

    @staticmethod
    def activate(api: ApplicationAPI, artifact: WorkspaceArtifact) -> None:
        """Open one typed artifact while preserving its useful context."""
        # [impl->req~ring5.workspace.favorites-tags~1]
        if not isinstance(artifact, WorkspaceArtifact):
            raise TypeError("Workspace organizer targets must be WorkspaceArtifact instances.")
        if artifact.kind == "variable":
            st.session_state["var_search_box__search"] = artifact.identifier
            st.session_state["_nav_page"] = "Data Source"
            return
        if artifact.kind == "dataset":
            api.select_dataset(artifact.identifier)
            st.session_state["_nav_page"] = "Data Managers"
            return
        if artifact.kind in {"plot", "pipeline"}:
            try:
                plot_id = int(artifact.identifier.split(":", maxsplit=1)[0])
            except ValueError as exc:
                raise ValueError("Workspace artifact has an invalid plot identifier.") from exc
            if not any(plot.plot_id == plot_id for plot in api.state_manager.get_plots()):
                raise KeyError(f"Plot {plot_id} is no longer available.")
            api.state_manager.set_current_plot_id(plot_id)
            st.session_state.pop("plot_selector", None)
            st.session_state["_nav_page"] = "Manage Plots"
            return
        if artifact.kind == "portfolio":
            st.session_state["_nav_page"] = "Save/Load Portfolio"
            return
        raise ValueError(f"Unsupported workspace artifact kind {artifact.kind!r}.")

    @staticmethod
    def _label(artifact: WorkspaceArtifact) -> str:
        favorite = "★ " if artifact.favorite else ""
        tags = f" · {', '.join(artifact.tags)}" if artifact.tags else ""
        return f"{favorite}{_KIND_LABELS[artifact.kind]} · {artifact.title}{tags}"
