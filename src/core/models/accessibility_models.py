"""Immutable results from auditing a figure configuration for accessibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

AccessibilitySeverity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class AccessibilityFinding:
    """One actionable accessibility issue in a figure configuration."""

    # [impl->req~ring5.figure.accessible-themes~1]

    severity: AccessibilitySeverity
    component: str
    message: str
    contrast_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class AccessibilityReport:
    """Human-readable accessibility outcome for one effective figure theme."""

    # [impl->req~ring5.figure.accessible-themes~1]

    palette_name: str
    palette_colorblind_safe: bool
    non_color_encodings: bool
    minimum_contrast_ratio: float | None
    findings: tuple[AccessibilityFinding, ...] = ()

    @property
    def passed(self) -> bool:
        """Whether no accessibility error remains."""
        return not any(finding.severity == "error" for finding in self.findings)

    @property
    def issue_count(self) -> int:
        """Number of actionable errors and warnings."""
        return len(self.findings)

    def to_frame(self) -> pd.DataFrame:
        """Return one ordered row per finding for display or export."""
        return pd.DataFrame(
            (
                {
                    "severity": finding.severity,
                    "component": finding.component,
                    "contrast_ratio": finding.contrast_ratio,
                    "message": finding.message,
                }
                for finding in self.findings
            ),
            columns=("severity", "component", "contrast_ratio", "message"),
        )
