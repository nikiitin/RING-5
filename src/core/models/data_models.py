"""
Data Models -- TypedDicts for service-layer data structures.

Defines the exact shapes of dictionaries exchanged between services,
protocols, and APIs. These replace ``Dict[str, Any]`` in protocol
definitions so that implementers and consumers have full visibility
into the expected data contracts.

Categories:
    - CSV pool management: CsvPoolEntry, CsvMetadata
    - Configuration persistence: SavedConfigEntry, SavedConfigData
    - Parse variable configuration: ParseVariableConfig
    - Scanned variable serialization: ScannedVariableDict
    - Cache monitoring: CacheStatsEntry, CacheStatsInfo
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Required, TypedDict

# CSV Pool


class CsvMetadata(TypedDict):
    """Metadata for a single CSV file (columns, row count, dtypes).

    Produced by ``CsvPoolService._get_csv_metadata()``.
    All fields are always present.
    """

    columns: list[str]
    rows: int
    dtypes: dict[str, str]


class CsvPoolEntry(TypedDict, total=False):
    """A single entry in the CSV file pool.

    Always has ``path``, ``name``, ``size``, ``modified``.
    Metadata fields (``columns``, ``rows``, ``dtypes``) are present
    only when metadata caching succeeds.

    Produced by ``CsvPoolService.load_pool()``.
    """

    # Always present
    path: Required[str]
    name: Required[str]
    size: Required[int]
    modified: Required[float]

    # From CsvMetadata (optional)
    columns: list[str]
    rows: int
    dtypes: dict[str, str]


# Configuration Persistence


class SavedConfigEntry(TypedDict):
    """Summary of a saved configuration file.

    All fields are always present. Produced by
    ``ConfigService.load_saved_configs()``.
    """

    path: str
    name: str
    modified: float
    description: str


class SavedConfigData(TypedDict, total=False):
    """Full content of a saved configuration file.

    Serialized to/from JSON by ``ConfigService``.
    ``name`` and ``shapers`` are always present when saving.
    """

    name: Required[str]
    format: str
    schema_version: int
    description: str
    timestamp: str
    shapers: Required[list[Mapping[str, object]]]
    csv_path: str | None


PipelineConfigConflictPolicy = Literal["error", "rename", "replace"]
PipelineConfigConflictResolution = Literal["none", "renamed", "replaced"]


@dataclass(frozen=True)
class PipelineConfigImportResult:
    """Outcome of importing a portable shaper-pipeline configuration.

    Attributes:
        path: Path of the saved local configuration record.
        name: Final saved name after conflict handling.
        original_name: Name declared by the imported document.
        description: Human-readable configuration description.
        shapers: Validated ordered shaper configurations.
        csv_path: Optional source CSV association carried by the document.
        schema_version: Current portable document schema version.
        conflict_resolution: Conflict action actually taken.
    """

    path: str
    name: str
    original_name: str
    description: str
    shapers: tuple[Mapping[str, object], ...]
    csv_path: str | None
    schema_version: int
    conflict_resolution: PipelineConfigConflictResolution


# Parse Variable Configuration


class ParseVariableConfig(TypedDict, total=False):
    """Editable StatConfig fields with UI identity and incomplete current values.

    All statistic options use the nested params dictionary. Missing fields and
    empty text are allowed while editing; runnable compilation validates them.
    """

    name: str
    type: str
    _id: str
    source_name: str | None
    params: dict[str, str | int | float | bool | list[str] | None]
    repeat: int
    statistics_only: bool
    keep_indices: bool
    is_regex: bool


# Scanned Variable (dict form)


class SourceInstanceDict(TypedDict):
    """One concrete statistic source and its numeric display coordinates."""

    source_name: str
    indices: list[str]


class ScannedVariableDict(TypedDict):
    """Current owned scanner payload; ambiguous sources have no output suggestion."""

    name: str
    type: str | None
    entries: list[str]
    source_evidence: dict[str, object]
    instances: list[SourceInstanceDict]


# Pipeline Steps (stored in plots)


class PipelineStep(TypedDict):
    """A single step in a plot's data processing pipeline.

    This is the **nested** format stored in ``BasePlot.pipeline``,
    where draft shaper parameters are inside a ``config`` mapping. Drafts may be incomplete;
    execution and standalone pipeline exchange validate the complete runnable contract.

    The config mapping contains the **flat** current operation format
    used by ``PipelineService`` for JSON persistence.
    """

    id: int
    type: str
    config: Mapping[str, object]


# Column Info (DataFrame summary for UI)


class ColumnInfoResult(TypedDict):
    """Summary information about DataFrame columns.

    Returned by ``ApplicationAPI.get_column_info()``.
    All fields are always present.
    """

    total_columns: int
    total_rows: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    columns: list[str]


# Cache Statistics


class CacheStatsEntry(TypedDict, total=False):
    """Statistics for a single cache instance.

    Returned by ``SimpleCache.stats()``.
    """

    size: int
    maxsize: int
    hits: int
    misses: int
    hit_rate: float


class CacheStatsInfo(TypedDict):
    """Aggregated cache statistics.

    Returned by ``CsvPoolService.get_cache_stats()``.
    """

    metadata_cache: CacheStatsEntry
    dataframe_cache: CacheStatsEntry
    index_size: int
