"""Public API proof for command discovery and typed validation."""

from __future__ import annotations

import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_session_searches_the_canonical_workspace_commands() -> None:
    # [test->req~ring5.workspace.command-palette~1]
    with ring5.Session() as session:
        response = session.search_workspace_commands("plot export")

    assert ring5.WorkspaceCommandSearchResponse is type(response)
    assert ring5.WorkspaceCommand is type(response.commands[0])
    assert response.commands[0].command_id == "navigate.manage-plots"
    assert response.commands[0].shortcuts == ("Alt+3",)


def test_public_command_validation_is_typed() -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="exceeds 200"):
            session.search_workspace_commands("x" * 201)
        with pytest.raises(ring5.DataValidationError, match="from 1 through 100"):
            session.search_workspace_commands(limit=0)
