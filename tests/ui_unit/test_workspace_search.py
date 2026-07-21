"""Presentation tests for workspace search rendering and activation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.models import WorkspaceSearchResponse, WorkspaceSearchResult


def _result(
    kind: str,
    title: str,
    location: str,
    identifier: str = "",
) -> WorkspaceSearchResult:
    return WorkspaceSearchResult(
        kind=kind,  # type: ignore[arg-type]
        title=title,
        description=f"Description for {title}",
        location=location,
        identifier=identifier,
        score=100,
        matched_terms=("match",),
    )


@patch("src.web.components.workspace_search.st")
def test_render_shows_bounded_actions_and_documentation_links(mock_st: MagicMock) -> None:
    from src.web.components.workspace_search import WorkspaceSearchComponent

    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    mock_st.text_input.return_value = "plot"
    mock_st.button.return_value = False
    api = MagicMock()
    api.search_workspace.return_value = WorkspaceSearchResponse(
        query="plot",
        results=(
            _result("command", "Go to Manage Plots", "Manage Plots"),
            _result(
                "documentation",
                "Plot types",
                "https://nikiitin.github.io/RING-5/user-guide/reference/plot-types/",
                "user-guide/reference/plot-types",
            ),
        ),
        total_matches=20,
        returned_matches=2,
        results_truncated=True,
        available_entries=30,
        indexed_entries=25,
        index_truncated=True,
    )

    WorkspaceSearchComponent.render(api)

    api.search_workspace.assert_called_once_with("plot", limit=12)
    assert mock_st.button.call_args.args[0] == "Command · Go to Manage Plots"
    assert mock_st.link_button.call_args.args[:2] == (
        "Guide · Plot types",
        "https://nikiitin.github.io/RING-5/user-guide/reference/plot-types/",
    )
    mock_st.warning.assert_called_once()


@patch("src.web.components.workspace_search.st")
def test_activate_selects_entities_and_rejects_stale_targets(mock_st: MagicMock) -> None:
    # [test->req~ring5.workspace.global-search~1]
    from src.web.components.workspace_search import WorkspaceSearchComponent

    mock_st.session_state = {"plot_selector": "old"}
    api = MagicMock()
    plot = MagicMock(plot_id=7)
    api.state_manager.get_plots.return_value = [plot]

    WorkspaceSearchComponent.activate(
        api,
        _result("dataset", "Nightly", "Data Managers", "Nightly"),
    )
    api.select_dataset.assert_called_once_with("Nightly")

    WorkspaceSearchComponent.activate(
        api,
        _result("pipeline", "Sort", "Manage Plots", "7"),
    )
    api.state_manager.set_current_plot_id.assert_called_once_with(7)
    assert "plot_selector" not in mock_st.session_state

    WorkspaceSearchComponent.activate(
        api,
        _result("variable", "system.cpu.ipc", "Data Source", "system.cpu.ipc"),
    )
    assert mock_st.session_state["var_search_box__search"] == "system.cpu.ipc"
    assert mock_st.session_state["_nav_page"] == "Data Source"

    with pytest.raises(ValueError, match="external links"):
        WorkspaceSearchComponent.activate(
            api,
            _result("documentation", "Guide", "https://example.test"),
        )
    with pytest.raises(ValueError, match="Unsupported workspace destination"):
        WorkspaceSearchComponent.activate(api, _result("command", "Bad", "Unknown"))
    with pytest.raises(ValueError, match="invalid plot identifier"):
        WorkspaceSearchComponent.activate(
            api,
            _result("plot", "Bad plot", "Manage Plots", "nope"),
        )
    with pytest.raises(KeyError, match="no longer available"):
        WorkspaceSearchComponent.activate(
            api,
            _result("plot", "Gone", "Manage Plots", "99"),
        )
