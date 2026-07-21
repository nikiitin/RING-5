"""Presentation tests for editing and opening organized workspace artifacts."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.models import WorkspaceArtifact, WorkspaceArtifactResponse


def _response(artifact: WorkspaceArtifact) -> WorkspaceArtifactResponse:
    return WorkspaceArtifactResponse(
        kind=None,
        tags=(),
        favorites_only=False,
        artifacts=(artifact,),
        available_tags=artifact.tags,
        total_matches=1,
        returned_matches=1,
        results_truncated=False,
        available_artifacts=1,
        indexed_artifacts=1,
        index_truncated=False,
    )


@patch("src.web.components.workspace_organizer.st")
def test_render_filters_and_saves_canonical_metadata(mock_st: MagicMock) -> None:
    # [test->req~ring5.workspace.favorites-tags~1]
    from src.web.components.workspace_organizer import WorkspaceOrganizerComponent

    artifact = WorkspaceArtifact("variable", "system.cpu.ipc", "system.cpu.ipc")
    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    mock_st.selectbox.side_effect = ["Everything", artifact]
    mock_st.multiselect.return_value = []
    mock_st.checkbox.side_effect = [False, True]
    mock_st.text_input.return_value = "Nightly, paper"
    mock_st.button.side_effect = [True, False]
    api = MagicMock()
    api.list_workspace_artifacts.side_effect = [_response(artifact), _response(artifact)]

    WorkspaceOrganizerComponent.render(api)

    assert api.list_workspace_artifacts.call_count == 2
    api.set_workspace_artifact_metadata.assert_called_once_with(
        "variable",
        "system.cpu.ipc",
        tags=("Nightly", "paper"),
        favorite=True,
    )
    mock_st.success.assert_called_once()
    mock_st.rerun.assert_called_once()


@patch("src.web.components.workspace_organizer.st")
def test_activate_opens_each_artifact_kind_and_rejects_stale_plots(mock_st: MagicMock) -> None:
    from src.web.components.workspace_organizer import WorkspaceOrganizerComponent

    mock_st.session_state = {"plot_selector": "old"}
    api = MagicMock()
    api.state_manager.get_plots.return_value = [MagicMock(plot_id=7)]

    WorkspaceOrganizerComponent.activate(
        api, WorkspaceArtifact("variable", "system.cpu.ipc", "IPC")
    )
    assert mock_st.session_state["_nav_page"] == "Data Source"
    WorkspaceOrganizerComponent.activate(api, WorkspaceArtifact("dataset", "nightly", "Nightly"))
    api.select_dataset.assert_called_once_with("nightly")
    WorkspaceOrganizerComponent.activate(api, WorkspaceArtifact("pipeline", "7:11", "Sort"))
    api.state_manager.set_current_plot_id.assert_called_once_with(7)
    assert "plot_selector" not in mock_st.session_state
    WorkspaceOrganizerComponent.activate(api, WorkspaceArtifact("portfolio", "paper", "Paper"))
    assert mock_st.session_state["_nav_page"] == "Save/Load Portfolio"

    with pytest.raises(ValueError, match="invalid plot identifier"):
        WorkspaceOrganizerComponent.activate(api, WorkspaceArtifact("plot", "bad", "Bad"))
    with pytest.raises(KeyError, match="no longer available"):
        WorkspaceOrganizerComponent.activate(api, WorkspaceArtifact("plot", "99", "Gone"))
    with pytest.raises(TypeError, match="WorkspaceArtifact instances"):
        WorkspaceOrganizerComponent.activate(api, object())  # type: ignore[arg-type]
