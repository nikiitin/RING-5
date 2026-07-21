"""Public outcomes for stable-input scheduled report runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

ScheduledReportOutcome: TypeAlias = Literal[
    "generated",
    "unchanged",
    "waiting_for_stability",
]


@dataclass(frozen=True)
class ScheduledReportResult:
    # [impl->req~ring5.automation.scheduled-reporting~1]
    """Outcome of one scheduled report source check.

    Attributes:
        recipe_name: Recipe selected for the report.
        outcome: Whether a report was generated, already current, or waiting.
        source_fingerprint: SHA-256 identity of the observed source, when stable.
        configuration_fingerprint: SHA-256 identity of the recipe and report settings.
        source_files: Ordered files included in the source identity.
        report_path: Configured HTML or PDF destination.
        state_path: Durable change-state document used across processes.
        stable_for_seconds: Required unchanged observation window.
    """

    recipe_name: str
    outcome: ScheduledReportOutcome
    source_fingerprint: str | None
    configuration_fingerprint: str
    source_files: tuple[str, ...]
    report_path: str
    state_path: str
    stable_for_seconds: float

    @property
    def generated(self) -> bool:
        """Whether this check atomically published a new report."""
        return self.outcome == "generated"
