"""Typed portfolio revision and field-difference records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PortfolioDiffSection = Literal["data_sources", "pipelines", "plots", "figure_settings"]
PortfolioChangeKind = Literal["added", "removed", "changed"]


@dataclass(frozen=True)
class PortfolioRevisionInfo:
    # [impl->req~ring5.portfolio.history-diff~1]
    """One immutable saved version of a named portfolio.

    Attributes:
        portfolio_name: Logical portfolio name.
        revision_id: SHA-256 identity of the exact saved JSON bytes.
        sequence: One-based save order within this portfolio.
        created_at: Timestamp recorded by the portfolio.
        active: Whether this revision matches the current saved portfolio.
        size_bytes: Exact revision file size.
        source: Human-readable source mode.
        plot_count: Number of saved plots.
    """

    portfolio_name: str
    revision_id: str
    sequence: int
    created_at: str
    active: bool
    size_bytes: int
    source: str
    plot_count: int


@dataclass(frozen=True)
class PortfolioDiffEntry:
    """One leaf-level difference between two portfolio revisions.

    Attributes:
        section: Human-facing comparison area.
        path: Stable field path within that area.
        change: Whether the value was added, removed, or changed.
        before: Earlier value, or ``None`` when added.
        after: Later value, or ``None`` when removed.
    """

    section: PortfolioDiffSection
    path: str
    change: PortfolioChangeKind
    before: Any
    after: Any


@dataclass(frozen=True)
class PortfolioDiff:
    """Bounded field comparison between two immutable portfolio revisions.

    Attributes:
        portfolio_name: Logical portfolio name.
        before_revision: Earlier revision identity.
        after_revision: Later revision identity.
        entries: Ordered field-level changes.
        section_counts: Change counts in the four comparison areas.
        truncated: Whether the safety ceiling omitted later changes.
    """

    portfolio_name: str
    before_revision: str
    after_revision: str
    entries: tuple[PortfolioDiffEntry, ...]
    section_counts: tuple[tuple[PortfolioDiffSection, int], ...]
    truncated: bool = False

    @property
    def change_count(self) -> int:
        """Return the number of reported field changes."""
        return len(self.entries)
