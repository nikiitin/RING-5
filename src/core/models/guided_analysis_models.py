"""Immutable progress contracts for the guided analysis workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

GuidedAnalysisStageId: TypeAlias = Literal[
    "source",
    "validation",
    "comparison",
    "visualization",
    "export",
]
GuidedAnalysisStageStatus: TypeAlias = Literal["complete", "current", "blocked"]


@dataclass(frozen=True, slots=True)
class GuidedAnalysisStage:
    """One ordered milestone and its current workspace-derived status."""

    stage_id: GuidedAnalysisStageId
    title: str
    description: str
    status: GuidedAnalysisStageStatus
    detail: str
    action_label: str
    destination: str


@dataclass(frozen=True, slots=True)
class GuidedAnalysisProgress:
    """Deterministic progress through source, analysis, figure, and export work."""

    # [impl->req~ring5.workspace.guided-analysis~1]

    stages: tuple[GuidedAnalysisStage, ...]
    completed_stages: int
    total_stages: int
    percent_complete: int
    current_stage: GuidedAnalysisStageId | None
    complete: bool
