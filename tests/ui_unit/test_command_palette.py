"""Presentation tests for command-palette rendering and activation."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import (
    WorkspaceCommand,
    WorkspaceCommandAction,
    WorkspaceCommandSearchResponse,
)
from src.core.services.workspace_command_catalog import WORKSPACE_COMMANDS


def _command(
    command_id: str = "navigate.manage-plots",
    *,
    action: str = "navigate",
    destination: str = "Manage Plots",
) -> WorkspaceCommand:
    """Build a command fixture with a category matching its action."""
    return WorkspaceCommand(
        command_id=command_id,
        title="Go to Manage Plots",
        description="Open plots and pipelines.",
        category="search" if action == "focus_workspace_search" else "navigation",
        action=cast(WorkspaceCommandAction, action),
        destination=destination,
        shortcuts=("Alt+3",),
        keywords=("plot",),
    )


@patch("src.web.components.command_palette.st")
def test_render_dialog_lists_shortcuts_and_searches_commands(
    mock_st: MagicMock,
) -> None:
    """Render trusted command matches as actionable buttons."""
    from src.web.components.command_palette import CommandPaletteComponent

    mock_st.text_input.return_value = "plot"
    mock_st.button.return_value = False
    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    api = MagicMock()
    api.search_workspace_commands.return_value = WorkspaceCommandSearchResponse(
        query="plot",
        commands=(_command(),),
        total_matches=1,
        returned_matches=1,
        results_truncated=False,
    )

    CommandPaletteComponent.render_dialog(api)

    api.search_workspace_commands.assert_called_once_with("plot", limit=20)
    assert mock_st.button.call_args.args[0] == "Go to Manage Plots · Alt+3"
    mock_st.markdown.assert_called_once()
    mock_st.iframe.assert_not_called()


@patch("src.web.components.command_palette.st")
def test_render_dialog_uses_a_link_for_external_documentation(mock_st: MagicMock) -> None:
    """Render the canonical documentation command as an external link."""
    # [test->req~ring5.workspace.documentation-hub~2]
    from src.web.components.command_palette import CommandPaletteComponent

    documentation = next(
        command for command in WORKSPACE_COMMANDS if command.command_id == "navigate.documentation"
    )
    mock_st.text_input.return_value = "documentation"
    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    api = MagicMock()
    api.search_workspace_commands.return_value = WorkspaceCommandSearchResponse(
        query="documentation",
        commands=(documentation,),
        total_matches=1,
        returned_matches=1,
        results_truncated=False,
    )

    CommandPaletteComponent.render_dialog(api)

    mock_st.link_button.assert_called_once_with(
        "Open Documentation · Alt+5",
        "https://nikiitin.github.io/RING-5/",
        width="stretch",
        help="Open the published RING-5 documentation in a new browser tab.",
    )
    mock_st.button.assert_not_called()


@patch("src.web.components.command_palette.st")
def test_activate_navigates_focuses_search_and_rejects_untrusted_actions(
    mock_st: MagicMock,
) -> None:
    """Apply internal actions and reject destinations outside the catalog."""
    # [test->req~ring5.workspace.command-palette~1]
    from src.web.components.command_palette import CommandPaletteComponent

    mock_st.session_state = {}
    CommandPaletteComponent.activate(_command())
    assert mock_st.session_state["_nav_page"] == "Manage Plots"

    CommandPaletteComponent.activate(
        _command(
            "search.focus",
            action="focus_workspace_search",
            destination="Search workspace",
        )
    )
    assert mock_st.session_state["_workspace_search_requested"] is True
    assert mock_st.session_state["_workspace_search_focus_pending"] is True

    with pytest.raises(ValueError, match="rendered link"):
        CommandPaletteComponent.activate(_command(action="open_external"))

    with pytest.raises(ValueError, match="Unsupported workspace destination"):
        CommandPaletteComponent.activate(_command(destination="Unknown"))
    with pytest.raises(ValueError, match="Unsupported workspace command action"):
        CommandPaletteComponent.activate(_command(action="unknown"))
    with pytest.raises(TypeError, match="WorkspaceCommand instances"):
        CommandPaletteComponent.activate(object())  # type: ignore[arg-type]


@patch("src.web.components.command_palette.st")
def test_launcher_installs_one_bridge_with_pending_focus(
    mock_st: MagicMock,
) -> None:
    """Install one keyboard bridge and consume pending focus requests."""
    from src.web.components.command_palette import CommandPaletteComponent

    mock_st.button.return_value = False
    mock_st.session_state = {
        "_workspace_search_focus_pending": True,
        "_command_palette_focus_pending": True,
    }

    CommandPaletteComponent.render(MagicMock())

    html = mock_st.iframe.call_args.args[0]
    assert "__ring5ShortcutHandler" in html
    assert 'querySelectorAll("button, a")' in html
    assert "Alt+1" not in html
    assert "if (true)" in html
    assert mock_st.iframe.call_args.kwargs == {"height": 1}
    assert mock_st.session_state == {}
