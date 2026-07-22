"""Independent readiness signals for human OFT requirement reports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

EXECUTION_STATUSES = frozenset({"passed", "failed", "not-run", "not-recorded"})


@dataclass(frozen=True)
class ReadinessCheck:
    """One labeled readiness dimension and its honest state."""

    key: str
    label: str
    state: str
    detail: str


def _evidence_count(feature: Mapping[str, Any], kind: str) -> int:
    evidence = feature.get("evidence", {})
    if not isinstance(evidence, Mapping):
        return 0
    values = evidence.get(kind, [])
    return len(values) if isinstance(values, list) else 0


def assess_requirement_readiness(
    feature: Mapping[str, Any],
    *,
    native_covered: bool,
    execution_status: str = "not-recorded",
) -> tuple[ReadinessCheck, ...]:
    """Assess six independent readiness dimensions without inferring test execution."""
    # [impl->req~ring5.trace.readiness-checklist~1]
    if execution_status not in EXECUTION_STATUSES:
        raise ValueError(f"Unknown execution status {execution_status!r}.")
    specified = all(
        isinstance(feature.get(field), str) and bool(str(feature[field]).strip())
        for field in ("title", "description")
    )
    evidence_checks = (
        ("implementation", "Implementation", "implementation"),
        ("test", "Test", "tests"),
        ("documentation", "Documentation", "documentation"),
    )
    checks = [
        ReadinessCheck(
            "specification",
            "Specification",
            "ready" if specified else "missing",
            "Requirement text present" if specified else "Requirement text missing",
        )
    ]
    for key, label, evidence_key in evidence_checks:
        count = _evidence_count(feature, evidence_key)
        checks.append(
            ReadinessCheck(
                key,
                label,
                "ready" if count else "missing",
                f"{count} exact origin{'s' if count != 1 else ''}" if count else "No exact origin",
            )
        )
    checks.append(
        ReadinessCheck(
            "native-trace",
            "Native OFT trace",
            "covered" if native_covered else "uncovered",
            "Covered by OFT" if native_covered else "Uncovered in OFT",
        )
    )
    execution_details = {
        "passed": "Latest recorded run passed",
        "failed": "Latest recorded run failed",
        "not-run": "Recorded as not run",
        "not-recorded": "No execution result supplied",
    }
    checks.append(
        ReadinessCheck(
            "execution", "Execution", execution_status, execution_details[execution_status]
        )
    )
    return tuple(checks)
