"""Immutable contracts for discoverable workspace commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

WorkspaceCommandAction: TypeAlias = Literal["navigate", "focus_workspace_search", "open_external"]
WorkspaceCommandCategory: TypeAlias = Literal["navigation", "search"]


@dataclass(frozen=True, slots=True)
class WorkspaceCommand:
    """One safe command exposed by the web workspace."""

    command_id: str
    title: str
    description: str
    category: WorkspaceCommandCategory
    action: WorkspaceCommandAction
    destination: str
    shortcuts: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkspaceCommandSearchResponse:
    """Bounded command-palette results with transparent truncation metadata."""

    # [impl->req~ring5.workspace.command-palette~1]

    query: str
    commands: tuple[WorkspaceCommand, ...]
    total_matches: int
    returned_matches: int
    results_truncated: bool
