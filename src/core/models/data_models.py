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
    - Pipeline persistence: PipelineData
    - Cache monitoring: CacheStatsEntry, CacheStatsInfo
"""

from typing import Required, TypedDict

# Re-export shaper models from their canonical module so existing imports
# like ``from src.core.models.data_models import ShaperStepConfig`` keep
# working. New code should import directly from ``shaper_models``.
from src.core.models.shaper_models import (  # noqa: F401
    BaseShaperConfig,
    ColumnSelectorConfig,
    ConditionSelectorConfig,
    ItemSelectorConfig,
    MeanShaperConfig,
    NormalizeShaperConfig,
    ShaperStepConfig,
    SortShaperConfig,
    SplitApplyGroupConfig,
    SplitApplyShaperConfig,
    TransformerShaperConfig,
)

# ──────────────────────────────────────────────────────────────────────
# CSV Pool
# ──────────────────────────────────────────────────────────────────────


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


# ──────────────────────────────────────────────────────────────────────
# Configuration Persistence
# ──────────────────────────────────────────────────────────────────────


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
    description: str
    timestamp: str
    shapers: Required[list["ShaperStepConfig"]]
    csv_path: str | None


# ──────────────────────────────────────────────────────────────────────
# Pipeline Persistence
# ──────────────────────────────────────────────────────────────────────


class PipelineData(TypedDict, total=False):
    """Full content of a saved pipeline file.

    Serialized to/from JSON by ``PipelineService``.
    Uses the **nested** ``PipelineStep`` format.
    """

    name: Required[str]
    description: str
    pipeline: Required[list["PipelineStep"]]
    timestamp: str


# ──────────────────────────────────────────────────────────────────────
# Parse Variable Configuration
# ──────────────────────────────────────────────────────────────────────


class ParseVariableConfig(TypedDict, total=False):
    """Configuration for a simulator variable to parse.

    Created by the variable editor UI and stored in
    ``StateManager.get_parse_variables()``.  Consumed by the parser
    layer and by portfolio serialization.

    ``name``, ``type``, and ``_id`` are always set when created through
    the UI.
    """

    # Required (always present)
    name: Required[str]
    type: Required[str]
    _id: Required[str]

    # Optional: alias
    alias: str

    # Optional: vector / histogram entries
    vectorEntries: list[str] | str
    useSpecialMembers: bool
    statisticsOnly: bool

    # Optional: distribution / histogram statistics
    statistics: list[str]

    # Optional: distribution range
    minimum: float
    maximum: float

    # Optional: histogram rebinning
    enableRebin: bool
    bins: int
    max_range: float

    # Optional: configuration type
    onEmpty: str

    # Optional: Perl parser repeat count
    repeat: str

    # Optional: pattern index selection
    patternSelection: list[str]
    parsed_ids: list[str]
    keepIndices: bool


# ──────────────────────────────────────────────────────────────────────
# Scanned Variable (dict form)
# ──────────────────────────────────────────────────────────────────────


class ScannedVariableDict(TypedDict, total=False):
    """Dictionary form of a ``ScannedVariable`` dataclass.

    Produced by ``ScannedVariable.to_dict()``; consumed by state
    management, variable service, and portfolio serialization.

    ``name``, ``type``, and ``entries`` are always present.
    """

    name: Required[str]
    type: Required[str]
    entries: Required[list[str]]
    minimum: float
    maximum: float
    pattern_indices: list[str]
    count: int


# ──────────────────────────────────────────────────────────────────────
# Pipeline Steps (stored in plots)
# ──────────────────────────────────────────────────────────────────────


class PipelineStep(TypedDict):
    """A single step in a plot's data processing pipeline.

    This is the **nested** format stored in ``BasePlot.pipeline``,
    where the shaper parameters are inside a ``config`` sub-dict.

    Distinct from ``ShaperStepConfig`` which is the **flat** format
    used by ``PipelineService`` for JSON persistence.
    """

    id: int
    type: str
    config: ShaperStepConfig


# ──────────────────────────────────────────────────────────────────────
# Column Info (DataFrame summary for UI)
# ──────────────────────────────────────────────────────────────────────


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


# ──────────────────────────────────────────────────────────────────────
# Cache Statistics
# ──────────────────────────────────────────────────────────────────────


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
