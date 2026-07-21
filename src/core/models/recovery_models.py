"""Immutable contracts for bounded local workspace recovery drafts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecoveryDraftInfo:
    """One owner-isolated integrity-checked local recovery point."""

    # [impl->req~ring5.workspace.autosave-recovery~1]

    draft_id: str
    created_at: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class RecoveryDraftCapture:
    """Result of a recovery capture, including content deduplication."""

    draft: RecoveryDraftInfo
    created: bool
