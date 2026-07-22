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
class IncrementalParseBatchResult:
    """Submitted changed-file work plus the immutable reuse plan needed to finalize it.

    ``cached_rows`` stores finalized scalar CSV cells, never parser objects or executable
    serialization.  This keeps the on-disk cache inspectable and safe to load as JSON.
    """

    # [impl->req~ring5.ingestion.incremental-parsing~1]

    futures: list[Future[dict[str, Any]]]
    var_names: list[str]
    output_dir: str
    strategy_type: str
    cache_path: str
    configuration_hash: str
    fingerprints: tuple[tuple[str, str], ...]
    cached_rows: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
    changed_files: tuple[str, ...]
    removed_files: tuple[str, ...]

    @property
    def parsed_file_count(self) -> int:
        """Number of new or changed files submitted to workers."""
        return len(self.changed_files)

    @property
    def reused_file_count(self) -> int:
        """Number of unchanged files whose finalized row can be reused."""
        return len(self.cached_rows)

    @property
    def removed_file_count(self) -> int:
        """Number of cached files no longer present in the input tree."""
        return len(self.removed_files)

    @property
    def total_file_count(self) -> int:
        """Number of rows expected in the updated parser output."""
        return len(self.fingerprints)


@dataclass(frozen=True)
class IncrementalParseResult:
    """Final CSV and human-readable incremental update counts."""

    csv_path: str
    parsed_files: int
    reused_files: int
    removed_files: int
    total_files: int


@dataclass(frozen=True)
class ParserPlaygroundBatchResult:
    """Bounded real-parser work and discovery context for a configuration test."""

    # [impl->req~ring5.ingestion.parser-playground~1]

    futures: list[Future[dict[str, Any]]]
    var_names: list[str]
    output_dir: str
    strategy_type: str
    matched_file_count: int
    sampled_files: tuple[str, ...]
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParserPlaygroundResult:
    """Human-readable result of testing parser settings against a bounded sample."""

    # [impl->req~ring5.ingestion.parser-playground~1]

    matched_file_count: int
    sampled_files: tuple[str, ...]
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    missing_variables: tuple[str, ...]
    diagnostics: tuple[str, ...]
    ready_for_full_parse: bool


@dataclass(frozen=True)
class ScannedVariable:
    """
    Base metadata for a variable discovered by a simulator parser.

    This is the simulator-agnostic base class.  Simulator-specific
    subclasses may add extra fields such as distribution min/max ranges.
    """

    name: str
    type: str  # Simulator-specific type string (e.g. "scalar", "vector")
    entries: list[str] = field(default_factory=list)
    pattern_indices: list[str] | None = None

    def to_dict(self) -> ScannedVariableDict:
        """Serialize to dictionary for JSON-compatible output.

        Copies the mutable list members so the returned dict cannot mutate this
        (frozen, reproducibility-guaranteeing) model's internal lists by reference.
        """
        result: ScannedVariableDict = ScannedVariableDict(
            name=self.name,
            type=self.type,
            entries=list(self.entries),
        )
        if self.pattern_indices is not None:
            result["pattern_indices"] = list(self.pattern_indices)
        return result

    @classmethod
    def from_dict(cls, data: ScannedVariableDict) -> "ScannedVariable":
        """Reconstruct model from dictionary.

        Copies the incoming lists so the model and the caller's dict don't share
        mutable references.
        """
        pattern_indices = data.get("pattern_indices")
        return cls(
            name=data["name"],
            type=data["type"],
            entries=list(data.get("entries", [])),
            pattern_indices=list(pattern_indices) if pattern_indices is not None else None,
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
    variables: list[ScannedVariable] = field(default_factory=list)
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
    them instead of silently showing "no variables". ``scanned_files`` records
    the full batch size, including failed files, so callers can distinguish a
    complete scan from a partial result.
    """

    variables: list[ScannedVariable] = field(default_factory=list)
    failures: list[ScanFileResult] = field(default_factory=list)
    scanned_files: int = 0

    @property
    def successful_files(self) -> int:
        """Number of files whose scanner completed successfully."""
        return max(self.scanned_files - len(self.failures), 0)

    @property
    def complete(self) -> bool:
        """True when every submitted file scanned successfully."""
        return not self.failures


@dataclass(frozen=True)
class StatConfig:
    r"""
    Configuration for a specific statistic extraction.
    Input to the FileParserStrategy implementations.

    Attributes:
        name: Logical output name. This is the source statistic when no alias
            is configured.
        source_name: Source statistic or regex pattern. ``None`` means it is
            identical to ``name``.
        type: One of ``scalar``, ``vector``, ``distribution``, ``histogram``,
              ``configuration``.
        repeat: Number of dump repetitions expected.
        params: Type-specific parameters (entries, min/max, etc.).
        statistics_only: If True, parse only statistical summaries.
        is_regex: Whether ``source_name`` is a pattern that must be expanded
            against scanned variables.
    """

    name: str
    type: str
    repeat: int = 1
    params: dict[str, StatParamValue] = field(default_factory=dict)
    statistics_only: bool = False
    is_regex: bool = False
    keep_indices: bool = False
    source_name: str | None = None
