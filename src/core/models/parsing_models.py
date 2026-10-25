"""Typed parser/application boundary models shared by scanning, jobs, and UI drafts.

Frozen models own their input containers. Runnable requests declare raw source metadata;
source instances keep concrete identities separate from their numeric display coordinates.
"""

from concurrent.futures import Future
import math
from dataclasses import dataclass, field
from typing import cast

from src.core.models.data_models import ScannedVariableDict, SourceInstanceDict
from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import (
    MAX_DISCOVERED_FILES,
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSE_FILES,
    MAX_PARSE_VARIABLES,
    MAX_PARSER_PLAYGROUND_CELLS,
    MAX_PARSER_PLAYGROUND_FILES,
    MAX_PARSER_PLAYGROUND_VARIABLES,
)
from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput, ParsedValue

# Shared by durable parse requests and incremental rows; bump on semantic changes.
PARSER_RESULT_VERSION = 10

# Type alias for StatConfig parameter values
StatParamValue = str | int | float | bool | list[str] | None


def _batch_names(value: tuple[str, ...], field: str, limit: int, *, empty: bool = False) -> None:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an immutable tuple.")
    if len(value) > limit or (not empty and not value):
        raise ValueError(f"{field} requires a bounded non-empty plan.")
    if any(type(item) is not str or not item or len(item) > MAX_INPUT_LENGTH for item in value):
        raise ValueError(f"{field} requires bounded non-empty strings.")
    if len(set(value)) != len(value):
        raise ValueError(f"{field} must be unique.")


def _batch_context(output_dir: str, strategy_type: str) -> None:
    for name, value in (("output_dir", output_dir), ("strategy_type", strategy_type)):
        if type(value) is not str or not value or len(value) > MAX_INPUT_LENGTH:
            raise ValueError(f"Parse batch {name} requires bounded non-empty text.")


def _batch_futures(futures: tuple[Future[ParsedFileResult], ...], count: int) -> None:
    if type(futures) is not tuple or any(not isinstance(future, Future) for future in futures):
        raise TypeError("Parse futures must be an immutable tuple of Future values.")
    if len(futures) != count:
        raise ValueError("Parse futures must match the planned worker source count.")


@dataclass(frozen=True)
class ParseBatchResult:
    """Owned asynchronous full-parse work with the complete finalization plan.

    Futures return finalized typed file results. The exact source paths, logical
    variable order, output directory and strategy are required by finalization;
    a backend never recovers this context from mutable instance state.
    """

    futures: tuple[Future[ParsedFileResult], ...]
    var_names: tuple[str, ...]
    source_paths: tuple[str, ...]
    output_dir: str
    strategy_type: str

    def __post_init__(self) -> None:
        _batch_names(self.var_names, "Logical variables", MAX_PARSE_VARIABLES)
        _batch_names(self.source_paths, "Source paths", MAX_PARSE_FILES)
        _batch_context(self.output_dir, self.strategy_type)
        _batch_futures(self.futures, len(self.source_paths))


@dataclass(frozen=True)
class IncrementalParseBatchResult:
    """Changed-file work and immutable typed reuse records for one exact input plan."""

    # [impl->req~ring5.ingestion.incremental-parsing~1]

    futures: tuple[Future[ParsedFileResult], ...]
    var_names: tuple[str, ...]
    output_dir: str
    strategy_type: str
    cache_path: str
    configuration_hash: str
    fingerprints: tuple[tuple[str, str], ...]
    cached_results: tuple[ParsedFileResult, ...]
    changed_files: tuple[str, ...]
    removed_files: tuple[str, ...]

    def __post_init__(self) -> None:
        _batch_names(self.var_names, "Logical variables", MAX_PARSE_VARIABLES)
        _batch_names(self.changed_files, "Changed source paths", MAX_PARSE_FILES, empty=True)
        _batch_names(self.removed_files, "Removed source paths", MAX_PARSE_FILES, empty=True)
        _batch_context(self.output_dir, self.strategy_type)
        _batch_futures(self.futures, len(self.changed_files))
        if (
            type(self.fingerprints) is not tuple
            or not self.fingerprints
            or len(self.fingerprints) > MAX_PARSE_FILES
        ):
            raise ValueError("Incremental fingerprints require a bounded immutable input plan.")
        for pair in self.fingerprints:
            if type(pair) is not tuple or len(pair) != 2:
                raise TypeError("Incremental fingerprints require source/digest pairs.")
            _sha256(pair[1])
        paths = tuple(path for path, _ in self.fingerprints)
        _batch_names(paths, "Incremental source paths", MAX_PARSE_FILES)
        if type(self.cached_results) is not tuple or any(
            type(result) is not ParsedFileResult for result in self.cached_results
        ):
            raise TypeError("Incremental reuse requires immutable typed file results.")
        cached_paths = tuple(result.source_path for result in self.cached_results)
        _batch_names(cached_paths, "Cached source paths", MAX_PARSE_FILES, empty=True)
        if set(cached_paths) & set(self.changed_files) or set(paths) != set(cached_paths) | set(
            self.changed_files
        ):
            raise ValueError("Cached and changed sources must partition the exact input plan.")
        if set(paths) & set(self.removed_files):
            raise ValueError("Removed sources must not occur in the current input plan.")
        _batch_context(self.cache_path, self.strategy_type)
        _sha256(self.configuration_hash)

    @property
    def parsed_file_count(self) -> int:
        """Return the number of new or changed files submitted to workers."""
        return len(self.changed_files)

    @property
    def reused_file_count(self) -> int:
        """Return the number of unchanged typed file results available for reuse."""
        return len(self.cached_results)

    @property
    def removed_file_count(self) -> int:
        """Return the number of cached files absent from the input tree."""
        return len(self.removed_files)

    @property
    def total_file_count(self) -> int:
        """Return the number of source rows planned for complete output."""
        return len(self.fingerprints)


def _sha256(value: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("Incremental identities require lowercase SHA-256 digests.")


@dataclass(frozen=True)
class IncrementalParseResult:
    """Typed published output and accepted incremental counts.

    Total files is the planned input count and can exceed accepted rows for a
    partial result. Only a complete result promotes the success cache.
    """

    output: ParsedOutput
    parsed_files: int
    reused_files: int
    removed_files: int
    total_files: int

    def __post_init__(self) -> None:
        if type(self.output) is not ParsedOutput:
            raise TypeError("Incremental results require a typed output descriptor.")
        for value in (self.parsed_files, self.reused_files, self.removed_files, self.total_files):
            if type(value) is not int or value < 0 or value > MAX_PARSE_FILES:
                raise ValueError("Incremental counts must be bounded non-negative integers.")
        if self.parsed_files + self.reused_files > self.total_files:
            raise ValueError("Accepted incremental rows exceed the planned input count.")

    @property
    def csv_path(self) -> str:
        """Return the CSV exchange path from this result's typed descriptor."""
        return self.output.csv_path


@dataclass(frozen=True)
class ParserPlaygroundBatchResult:
    """Bounded asynchronous work and immutable source context for a parser test."""

    # [impl->req~ring5.ingestion.parser-playground~1]

    futures: tuple[Future[ParsedFileResult], ...]
    var_names: tuple[str, ...]
    output_dir: str
    strategy_type: str
    matched_file_count: int
    sampled_files: tuple[str, ...]
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _batch_names(self.var_names, "Logical variables", MAX_PARSER_PLAYGROUND_VARIABLES)
        _batch_names(self.sampled_files, "Sampled source paths", MAX_PARSER_PLAYGROUND_FILES)
        _batch_context(self.output_dir, self.strategy_type)
        _batch_futures(self.futures, len(self.sampled_files))
        if (
            type(self.matched_file_count) is not int
            or not len(self.sampled_files) <= self.matched_file_count <= MAX_DISCOVERED_FILES
        ):
            raise ValueError("Matched files must include the entire sampled source plan.")
        if type(self.diagnostics) is not tuple or any(
            type(value) is not str for value in self.diagnostics
        ):
            raise TypeError("Playground diagnostics must be immutable text.")


@dataclass(frozen=True)
class ParserPlaygroundResult:
    """Literal-text and numeric preview cells with explicit schema column order."""

    # [impl->req~ring5.ingestion.parser-playground~1]

    matched_file_count: int
    sampled_files: tuple[str, ...]
    columns: tuple[str, ...]
    rows: tuple[tuple[ParsedValue, ...], ...]
    missing_variables: tuple[str, ...]
    diagnostics: tuple[str, ...]
    ready_for_full_parse: bool

    def __post_init__(self) -> None:
        _batch_names(self.sampled_files, "Sampled source paths", MAX_PARSER_PLAYGROUND_FILES)
        _batch_names(self.columns, "Preview columns", MAX_INCREMENTAL_CACHE_COLUMNS, empty=True)
        _batch_names(
            self.missing_variables,
            "Missing preview variables",
            MAX_PARSER_PLAYGROUND_VARIABLES,
            empty=True,
        )
        if type(self.rows) is not tuple or len(self.rows) != len(self.sampled_files):
            raise ValueError("Preview rows must own the exact immutable sampled row set.")
        if len(self.rows) * len(self.columns) > MAX_PARSER_PLAYGROUND_CELLS:
            raise ValueError("Preview exceeds the matrix cell limit.")
        for row in self.rows:
            if type(row) is not tuple or len(row) != len(self.columns):
                raise ValueError("Preview rows must match the explicit column width.")
            if any(type(value) not in (float, str) for value in row):
                raise TypeError("Preview cells require exact float or literal text values.")
        if (
            type(self.matched_file_count) is not int
            or not len(self.sampled_files) <= self.matched_file_count <= MAX_DISCOVERED_FILES
        ):
            raise ValueError("Matched preview files must include the bounded sampled plan.")
        if type(self.diagnostics) is not tuple or any(
            type(value) is not str for value in self.diagnostics
        ):
            raise TypeError("Preview diagnostics must be immutable text.")
        if type(self.ready_for_full_parse) is not bool:
            raise TypeError("Preview readiness must be a boolean.")


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
