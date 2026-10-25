"""Typed parser/application boundary models shared by scanning, jobs, and UI drafts.

Frozen models own their input containers. Runnable requests declare raw source metadata;
source instances keep concrete identities separate from their numeric display coordinates.
"""

from concurrent.futures import Future
import math
from dataclasses import dataclass, field
from typing import Any, cast

from src.core.models.data_models import ScannedVariableDict, SourceInstanceDict
from src.core.common.safe_regex import MAX_INPUT_LENGTH

# Shared by durable parse requests and incremental rows; bump on semantic changes.
PARSER_RESULT_VERSION = 9

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
    """Published CSV and incremental update counts.

    Attributes:
        csv_path: CSV containing accepted changed and reused rows.
        parsed_files: Accepted changed-file results included in this output.
        reused_files: Unchanged rows accepted from the submitted reuse plan.
        removed_files: Previous input files removed from the current plan.
        total_files: Planned input count; may exceed parsed plus reused for partial output.
    """

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
class SourceInstance:
    """A concrete statistic source with numeric coordinates for display.

    Attributes:
        source_name: Exact source statistic name, independent of an output alias.
        indices: Ordered ASCII digit strings; an empty tuple denotes a literal source.
    """

    source_name: str
    indices: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name:
            raise ValueError("A source instance requires a non-empty source_name.")
        if len(self.source_name) > MAX_INPUT_LENGTH:
            raise ValueError("Source instance name exceeds the matching input limit.")
        if not isinstance(self.indices, tuple):
            raise TypeError("Source instance indices must be an immutable tuple.")
        if any(
            not isinstance(index, str) or not index or not index.isascii() or not index.isdecimal()
            for index in self.indices
        ):
            raise ValueError("Source instance indices must contain ASCII digit strings.")
        if sum(map(len, self.indices)) > MAX_INPUT_LENGTH:
            raise ValueError("Source instance indices exceed the matching input limit.")

    def to_dict(self) -> SourceInstanceDict:
        """Return the exact current JSON representation with independently owned indices."""
        return {"source_name": self.source_name, "indices": list(self.indices)}

    @classmethod
    def from_dict(cls, value: SourceInstanceDict) -> "SourceInstance":
        """Decode one complete current source instance without numeric reconstruction."""
        if not isinstance(value, dict) or set(value) != {"source_name", "indices"}:
            raise ValueError("Source instances require exactly source_name and indices fields.")
        if not isinstance(value["indices"], list):
            raise TypeError("Serialized source instance indices must be a list.")
        return cls(source_name=value["source_name"], indices=tuple(value["indices"]))


def validate_scanned_bounds(minimum: object, maximum: object) -> None:
    """Validate optional observed bounds without coercion or inferred defaults.

    Args:
        minimum: Finite numeric lower bound, or None when unknown.
        maximum: Finite numeric upper bound, or None when unknown.

    Raises:
        TypeError: A known bound is not an actual int or float.
        ValueError: A bound is nonfinite or the known range is reversed.
    """
    for field_name, value in (("minimum", minimum), ("maximum", maximum)):
        if value is None:
            continue
        if type(value) not in (int, float):
            raise TypeError(f"Scanned variable {field_name} must be a finite number or unknown.")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"Scanned variable {field_name} must be finite.")
    if (
        minimum is not None
        and maximum is not None
        and cast(int | float, minimum) > cast(int | float, maximum)
    ):
        raise ValueError("Scanned variable minimum must not exceed maximum.")


@dataclass(frozen=True)
class ScannedVariable:
    """Current metadata for a statistic discovered by a simulator parser.

    Attributes:
        name: Literal source name or scanner-generated numeric pattern.
        type: Output representation suggested by the scanner.
        entries: Actual measurement entries below each concrete source.
        source_type: Explicit raw source kind before pattern aggregation.
        instances: Concrete sources with numeric display coordinates.
    """

    name: str
    type: str
    entries: list[str] = field(default_factory=list)
    source_type: str = field(kw_only=True)
    instances: tuple[SourceInstance, ...] = field(kw_only=True)

    def __post_init__(self) -> None:
        for field_name in ("name", "type", "source_type"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"Scanned variable {field_name} must be non-empty text.")
        if not isinstance(self.entries, list) or any(not isinstance(e, str) for e in self.entries):
            raise TypeError("Scanned variable entries must be a list of text values.")
        if not isinstance(self.instances, tuple) or not self.instances:
            raise ValueError("Scanned variables require explicit immutable source instances.")
        if any(not isinstance(instance, SourceInstance) for instance in self.instances):
            raise TypeError("Scanned variable instances must be SourceInstance values.")
        names = [instance.source_name for instance in self.instances]
        if len(set(names)) != len(names):
            raise ValueError("Scanned variable source instances must be unique.")
        object.__setattr__(self, "entries", list(self.entries))

    def to_dict(self) -> ScannedVariableDict:
        """Serialize current metadata without exposing caller-owned mutable lists."""
        return {
            "name": self.name,
            "type": self.type,
            "entries": list(self.entries),
            "source_type": self.source_type,
            "instances": [instance.to_dict() for instance in self.instances],
        }

    @classmethod
    def from_dict(cls, data: ScannedVariableDict) -> "ScannedVariable":
        """Decode mandatory source metadata; retired or incomplete payloads fail."""
        if not isinstance(data, dict):
            raise TypeError("Scanned variable metadata must be an object.")
        allowed = set(ScannedVariableDict.__annotations__)
        if set(data) - allowed:
            raise ValueError(f"Unsupported scanned variable fields: {sorted(set(data) - allowed)}.")
        required = {"name", "type", "entries", "source_type", "instances"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"Missing required scanned variable fields: {sorted(missing)}.")
        for field_name in ("minimum", "maximum"):
            if field_name in data and data[field_name] is None:
                raise TypeError("Serialized unknown scan bounds must be omitted.")
        validate_scanned_bounds(data.get("minimum"), data.get("maximum"))
        if not isinstance(data["instances"], list):
            raise TypeError("Serialized source instances must be a list.")
        return cls(
            name=data["name"],
            type=data["type"],
            entries=data["entries"],
            source_type=data["source_type"],
            instances=tuple(SourceInstance.from_dict(value) for value in data["instances"]),
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
        repeat: Positive integer count of expected dump repetitions.
        params: Current snake_case type options. Vector/histogram entries and
            summary statistics use separate text lists; distribution bounds use
            minimum/maximum; histogram rebinning uses bins/max_range;
            configuration fallback uses on_empty. Every runnable value requires
            source_type for the raw source kind. selected_sources contains exact
            concrete source names for a numeric pattern; numeric display labels
            belong only to SourceInstance metadata.
        statistics_only: If True, parse only statistical summaries.
        keep_indices: Keep concrete pattern instances as distinct output variables.
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


def default_parse_configs() -> tuple[StatConfig, ...]:
    """Create the explicit current parser presets without sharing mutable options."""
    return (
        StatConfig(name="simTicks", type="scalar", params={"source_type": "scalar"}),
        StatConfig(
            name="benchmark_name", type="configuration", params={"source_type": "configuration"}
        ),
        StatConfig(
            name="config_description", type="configuration", params={"source_type": "configuration"}
        ),
    )
