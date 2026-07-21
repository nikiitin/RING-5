"""Immutable contracts for favorites and validated workspace tags."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

WorkspaceArtifactKind: TypeAlias = Literal[
    "variable",
    "dataset",
    "plot",
    "pipeline",
    "portfolio",
]


@dataclass(frozen=True, slots=True)
class WorkspaceArtifact:
    """One discoverable artifact enriched with organizational metadata."""

    # [impl->req~ring5.workspace.favorites-tags~1]

    kind: WorkspaceArtifactKind
    identifier: str
    title: str
    tags: tuple[str, ...] = ()
    favorite: bool = False


@dataclass(frozen=True, slots=True)
class WorkspaceArtifactResponse:
    """Bounded filtered artifacts and the tags available in the workspace."""

    kind: WorkspaceArtifactKind | None
    tags: tuple[str, ...]
    favorites_only: bool
    artifacts: tuple[WorkspaceArtifact, ...]
    available_tags: tuple[str, ...]
    total_matches: int
    returned_matches: int
    results_truncated: bool
    available_artifacts: int
    indexed_artifacts: int
    index_truncated: bool
