"""Requirement lifecycle statuses shared by OFT inventory and report tooling."""

from __future__ import annotations

from typing import NamedTuple


class RequirementStatusView(NamedTuple):
    """Human-readable metadata for one inventory lifecycle status."""

    key: str
    label: str
    scope: str
    description: str


def requirement_status_views() -> tuple[RequirementStatusView, ...]:
    """Return every supported status in stable report order."""
    # [impl->req~ring5.trace.future-status-reporting~1]
    return (
        RequirementStatusView("approved", "Approved", "current", "Accepted current behavior"),
        RequirementStatusView("proposed", "Proposed", "future", "Candidate future behavior"),
        RequirementStatusView("draft", "Draft", "future", "Early requirement definition"),
        RequirementStatusView(
            "in-development", "In development", "future", "Implementation in progress"
        ),
        RequirementStatusView("blocked", "Blocked", "future", "Waiting before work can continue"),
    )


def requirement_status_tag(status: str) -> str:
    """Return the OFT word-tag form of a lifecycle status."""
    return f"status_{status.replace('-', '_')}"
