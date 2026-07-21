"""Unit coverage for the safe searchable workspace command registry."""

from __future__ import annotations

import pytest

from src.core.services.workspace_command_catalog import WORKSPACE_COMMANDS
from src.core.services.workspace_command_service import WorkspaceCommandService


def test_empty_query_lists_every_safe_command_in_discoverable_order() -> None:
    # [test->req~ring5.workspace.command-palette~1]
    response = WorkspaceCommandService.search_commands()

    assert response.commands == WORKSPACE_COMMANDS
    assert response.returned_matches == response.total_matches == 6
    assert response.results_truncated is False
    assert len({command.command_id for command in response.commands}) == 6
    assert all(command.shortcuts for command in response.commands)
    assert {command.action for command in response.commands} == {
        "navigate",
        "focus_workspace_search",
    }
    assert not any(
        forbidden in command.title.casefold()
        for command in response.commands
        for forbidden in ("delete", "reset", "clear")
    )


def test_search_uses_and_matching_ranking_and_explicit_bounds() -> None:
    plots = WorkspaceCommandService.search_commands("plot pipeline")
    limited = WorkspaceCommandService.search_commands("go", limit=2)

    assert [command.command_id for command in plots.commands] == ["navigate.manage-plots"]
    assert limited.returned_matches == 2
    assert limited.total_matches == 5
    assert limited.results_truncated is True


@pytest.mark.parametrize(
    ("query", "limit", "message"),
    [
        ("x" * 201, 20, "exceeds 200"),
        ("bad\x00query", 20, "control characters"),
        ("valid", True, "from 1 through 100"),
        ("valid", 0, "from 1 through 100"),
        ("valid", 101, "from 1 through 100"),
    ],
)
def test_invalid_queries_and_limits_are_rejected(query: str, limit: object, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        WorkspaceCommandService.search_commands(query, limit=limit)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="query must be text"):
        WorkspaceCommandService.search_commands(3)  # type: ignore[arg-type]
