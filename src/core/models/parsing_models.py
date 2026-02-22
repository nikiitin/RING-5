"""
Core data models for the Parser ↔ Application ↔ UI boundary.

These frozen dataclasses represent the "common language" shared across all
layers of RING-5. They were originally in ``src.core.parsing.models`` and
were externalised so that:

    • Layer A (Parsing) can produce them
    • Layer B (Application API) can pass them through
    • Layer C (Presentation / UI) can consume them

…without any layer depending on another's internals.

All models are **immutable** (``frozen=True``) to guarantee reproducibility.
"""

from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any

from src.core.models.data_models import ScannedVariableDict


@dataclass(frozen=True)
class ParseBatchResult:
    """
    Thread-safe result of a parse submission.

    Bundles the futures returned by the worker pool together with the
    variable names that were submitted, so that ``construct_final_csv``
    can guarantee column ordering without relying on shared class-level
    mutable state.
    """

    futures: list[Future[Any]]
    var_names: list[str]


@dataclass(frozen=True)
class ScannedVariable:
    """
    Metadata for a variable discovered in a gem5 stats file.
    Output of Layer A (Ingestion).
    """

    name: str
    type: str  # "scalar", "vector", "distribution", "histogram", "configuration"
    entries: list[str] = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    pattern_indices: list[str] | None = None

    def to_dict(self) -> ScannedVariableDict:
        """Serialize to dictionary for JSON-compatible output."""
        result: ScannedVariableDict = ScannedVariableDict(
            name=self.name,
            type=self.type,
            entries=self.entries,
        )
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.pattern_indices is not None:
            result["pattern_indices"] = self.pattern_indices
        return result

    @classmethod
    def from_dict(cls, data: ScannedVariableDict) -> "ScannedVariable":
        """Reconstruct model from dictionary."""
        return cls(
            name=data["name"],
            type=data["type"],
            entries=data.get("entries", []),
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
            pattern_indices=data.get("pattern_indices"),
        )


@dataclass(frozen=True)
class StatConfig:
    r"""
    Configuration for a specific statistic extraction.
    Input to the FileParserStrategy implementations.

    Attributes:
        name: Variable name or regex pattern (e.g., ``system.cpu\d+.ipc``).
        type: One of ``scalar``, ``vector``, ``distribution``, ``histogram``,
              ``configuration``.
        repeat: Number of dump repetitions expected.
        params: Type-specific parameters (entries, min/max, etc.).
        statistics_only: If True, parse only statistical summaries.
        is_regex: Explicit flag indicating that *name* is a regex pattern
                  requiring expansion against scanned variables.  Set
                  automatically when the name contains ``\d+``.
    """

    name: str
    type: str
    repeat: int = 1
    params: dict[str, Any] = field(default_factory=dict)
    statistics_only: bool = False
    is_regex: bool = False
    keep_indices: bool = False
