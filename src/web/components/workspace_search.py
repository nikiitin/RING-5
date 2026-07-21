"""Human-first sidebar search across every workspace artifact."""

from __future__ import annotations

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import WorkspaceSearchResult

_NAVIGATION_PAGES = frozenset(
    {"Data Source", "Data Managers", "Manage Plots", "Save/Load Portfolio", "Documentation"}
)
_KIND_LABELS = {
    "variable": "Variable",
    "dataset": "Dataset",
    "plot": "Plot",
    "pipeline": "Pipeline",
    "portfolio": "Portfolio",
    "command": "Command",
    "documentation": "Guide",
}


class WorkspaceSearchComponent:
    """Render bounded search results and apply their typed destinations."""

    @classmethod
    def render(cls, api: ApplicationAPI) -> None:
        """Render the unified search index in the application sidebar."""
        # [impl->req~ring5.workspace.global-search~1]
        requested = bool(st.session_state.pop("_workspace_search_requested", False))
        with st.expander("Search workspace", expanded=requested):
            query = st.text_input(
                "Search variables, data, plots, commands, and guides",
                key="_workspace_search_query",
                placeholder="Type two or more letters…",
                label_visibility="collapsed",
            )
            if not query.strip():
                st.caption("Find anything without leaving your current work.")
                return
            if len(query.strip()) < 2:
                st.caption("Type at least two letters to search.")
                return
            try:
                response = api.search_workspace(query, limit=12)
            except (OSError, TypeError, ValueError) as exc:
                st.error(f"Workspace search is unavailable: {exc}")
                return

            if not response.results:
                st.info("No workspace matches. Try a name, type, task, or guide topic.")
                return
            shown = f"{response.returned_matches} of {response.total_matches} matches"
            st.caption(shown if response.results_truncated else f"{response.total_matches} matches")
            if response.index_truncated:
                st.warning(
                    f"Indexed {response.indexed_entries:,} of "
                    f"{response.available_entries:,} available items. Refine your query."
                )

            for index, result in enumerate(response.results):
                label = f"{_KIND_LABELS[result.kind]} · {result.title}"
                if result.kind == "documentation":
                    st.link_button(
                        label,
                        result.location,
                        use_container_width=True,
                    )
                elif st.button(
                    label,
                    key=f"workspace_search_result_{index}_{result.kind}",
                    use_container_width=True,
                    type="tertiary",
                ):
                    try:
                        cls.activate(api, result)
                    except (KeyError, TypeError, ValueError) as exc:
                        st.error(f"Could not open {result.title}: {exc}")
                    else:
                        st.rerun()
                st.caption(result.description)

    @staticmethod
    def activate(api: ApplicationAPI, result: WorkspaceSearchResult) -> None:
        """Apply one non-document search destination and preserve its context."""
        # [impl->req~ring5.workspace.global-search~1]
        if result.kind == "documentation":
            raise ValueError("Documentation results open as external links.")
        if result.kind == "command" and result.identifier == "search.focus":
            st.session_state["_workspace_search_requested"] = True
            st.session_state["_workspace_search_focus_pending"] = True
            return
        if result.location not in _NAVIGATION_PAGES:
            raise ValueError(f"Unsupported workspace destination {result.location!r}.")
        if result.kind == "dataset":
            api.select_dataset(result.identifier)
        elif result.kind in {"plot", "pipeline"}:
            try:
                plot_id = int(result.identifier.split(":", maxsplit=1)[0])
            except ValueError as exc:
                raise ValueError("Search result has an invalid plot identifier.") from exc
            if not any(plot.plot_id == plot_id for plot in api.state_manager.get_plots()):
                raise KeyError(f"Plot {plot_id} is no longer available.")
            api.state_manager.set_current_plot_id(plot_id)
            st.session_state.pop("plot_selector", None)
        elif result.kind == "variable":
            st.session_state["var_search_box__search"] = result.identifier

        st.session_state["_nav_page"] = result.location
