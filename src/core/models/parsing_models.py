"""
Core data models for the Parser ↔ Application ↔ UI boundary.

These frozen dataclasses represent the "common language" shared across all
layers of RING-5. They were originally in ``src.parsing.models`` and
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

# Type alias for StatConfig parameter values
StatParamValue = str | int | float | bool | list[str] | None


@dataclass(frozen=True)
class ParseBatchResult:
    """
    Thread-safe result of a parse submission.

    Bundles the futures returned by the worker pool together with the
    variable names that were submitted, so that ``construct_final_csv``
    can guarantee column ordering without relying on shared class-level
    mutable state.
    """

    futures: list[Future[dict[str, Any]]]
    var_names: list[str]


@dataclass(frozen=True)
class ScannedVariable:
    """
    Base metadata for a variable discovered by a simulator parser.

    This is the simulator-agnostic base class.  Simulator-specific
    subclasses may add extra fields such as distribution min/max ranges.
    """

    name: str
    type: str  # Simulator-specific type string (e.g. "scalar", "vector")
    entries: list[str] = field(default_factory=lambda: list[str]())
    pattern_indices: list[str] | None = None

    def to_dict(self) -> ScannedVariableDict:
        """Serialize to dictionary for JSON-compatible output."""
        result: ScannedVariableDict = ScannedVariableDict(
            name=self.name,
            type=self.type,
            entries=self.entries,
        )
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
            pattern_indices=data.get("pattern_indices"),
        )


@dataclass(frozen=True)
class ScanFileResult:
    """Outcome of scanning a single stats file.

    On success ``variables`` holds the discovered variables and ``error`` is
    ``None``; on failure ``error`` holds the message and ``variables`` is empty.
    This lets aggregation distinguish "scanned: empty" from "scan failed"
    instead of masking failures as zero variables.
    """

    file_path: str
    variables: list[ScannedVariable] = field(default_factory=lambda: list[ScannedVariable]())
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when the file scanned without error."""
        return self.error is None


@dataclass(frozen=True)
class ScanResult:
    """Aggregated outcome of a scan across multiple files.

    ``variables`` is the merged, deduplicated list from files that scanned
    successfully; ``failures`` lists per-file failures so the UI can surface
    them instead of silently showing "no variables".
    """

    variables: list[ScannedVariable] = field(default_factory=lambda: list[ScannedVariable]())
    failures: list[ScanFileResult] = field(default_factory=lambda: list[ScanFileResult]())


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
    params: dict[str, StatParamValue] = field(default_factory=lambda: dict[str, StatParamValue]())
    statistics_only: bool = False
    is_regex: bool = False
    keep_indices: bool = False
