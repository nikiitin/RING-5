"""Immutable contracts for portable analysis review conversations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

AnalysisReviewTargetKind: TypeAlias = Literal["plot", "portfolio_revision"]
AnalysisReviewStatus: TypeAlias = Literal[
    "not-reviewed",
    "in-review",
    "changes-requested",
    "approved",
]


@dataclass(frozen=True, slots=True)
class AnalysisReviewTarget:
    """One plot or immutable portfolio revision that can be reviewed."""

    # [impl->req~ring5.workspace.collaborative-review~1]

    kind: AnalysisReviewTargetKind
    identifier: str
    title: str
    portfolio_name: str | None = None

    @property
    def identity(self) -> tuple[AnalysisReviewTargetKind, str, str]:
        """Return the unambiguous target key used by persisted threads."""
        return (self.kind, self.portfolio_name or "", self.identifier)


@dataclass(frozen=True, slots=True)
class AnalysisReviewEvent:
    """One append-only authored comment or review-status decision."""

    event_id: str
    author_id: str
    created_at: str
    status: AnalysisReviewStatus
    comment: str = ""


@dataclass(frozen=True, slots=True)
class AnalysisReviewThread:
    """Portable review history attached to one exact analysis target."""

    kind: AnalysisReviewTargetKind
    identifier: str
    title: str
    portfolio_name: str | None
    status: AnalysisReviewStatus
    events: tuple[AnalysisReviewEvent, ...]
    available: bool = True

    @property
    def identity(self) -> tuple[AnalysisReviewTargetKind, str, str]:
        """Return the unambiguous target key shared with discovery targets."""
        return (self.kind, self.portfolio_name or "", self.identifier)


@dataclass(frozen=True, slots=True)
class AnalysisReviewTargetResponse:
    """Bounded review targets with transparent discovery totals."""

    targets: tuple[AnalysisReviewTarget, ...]
    total_targets: int
    returned_targets: int
    truncated: bool
    available_targets: int
    indexed_targets: int
    index_truncated: bool


@dataclass(frozen=True, slots=True)
class AnalysisReviewResponse:
    """Bounded portable review threads and status totals."""

    threads: tuple[AnalysisReviewThread, ...]
    total_threads: int
    returned_threads: int
    truncated: bool
    status_counts: tuple[tuple[AnalysisReviewStatus, int], ...]
