"""Immutable contracts for bounded workspace-wide search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

WorkspaceSearchKind: TypeAlias = Literal[
    "variable",
    "dataset",
    "plot",
    "pipeline",
    "portfolio",
    "command",
    "documentation",
]


@dataclass(frozen=True, slots=True)
class WorkspaceSearchEntry:
    """One internal document accepted by the workspace search index."""

    kind: WorkspaceSearchKind
    title: str
    description: str
    location: str
    identifier: str = ""
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkspaceSearchResult:
    """One ranked, actionable workspace search match."""

    # [impl->req~ring5.workspace.global-search~1]

    kind: WorkspaceSearchKind
    title: str
    description: str
    location: str
    identifier: str
    score: int
    matched_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkspaceSearchResponse:
    """Bounded search results plus explicit index and result truncation."""

    # [impl->req~ring5.workspace.global-search~1]

    query: str
    results: tuple[WorkspaceSearchResult, ...]
    total_matches: int
    returned_matches: int
    results_truncated: bool
    available_entries: int
    indexed_entries: int
    index_truncated: bool
