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

from typing import TypedDict

# ──────────────────────────────────────────────────────────────────────
# CSV Pool
# ──────────────────────────────────────────────────────────────────────


class CsvMetadata(TypedDict, total=False):
    """Metadata for a single CSV file (columns, row count, dtypes).

    Produced by ``CsvPoolService._get_csv_metadata()``.
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
    path: str
    name: str
    size: int
    modified: float

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

    name: str
    description: str
    timestamp: str
    shapers: list["ShaperStepConfig"]
    csv_path: str | None


# ──────────────────────────────────────────────────────────────────────
# Pipeline Persistence
# ──────────────────────────────────────────────────────────────────────


class ShaperStepConfig(TypedDict, total=False):
    """Configuration for a single shaper step in a pipeline.

    The ``type`` field identifies the shaper (factory registry key).
    All other keys are shaper-specific parameters passed directly
    to the shaper constructor.

    This is the **flat** form used in pipeline JSON and config files,
    where ``type`` coexists with the shaper's own parameters at the
    same dict level.
    """

    # Shaper identification
    type: str
    id: int

    # ── Mean params ──
    meanVars: list[str]
    meanAlgorithm: str
    groupingColumns: list[str]
    groupingColumn: str
    replacingColumn: str

    # ── Normalize params ──
    normalizeVars: list[str]
    normalizerColumn: str
    normalizerValue: str
    groupBy: list[str]
    normalizerVars: list[str]
    normalizeSd: bool

    # ── Sort params ──
    order_dict: dict[str, list[str]]

    # ── SplitApply params ──
    joinColumns: list[str]
    groups: list["SplitApplyGroupConfig"]

    # ── Transformer params ──
    column: str
    target_type: str
    order: list[str] | None

    # ── ColumnSelector params ──
    columns: list[str]

    # ── ConditionSelector params ──
    mode: str
    threshold: float
    range: list[float]
    values: list[str]
    condition: str
    value: str | float | int

    # ── ItemSelector params ──
    strings: list[str]


class SplitApplyGroupConfig(TypedDict, total=False):
    """Configuration for a single group within a SplitApply shaper."""

    columns: list[str]
    pipeline: list[ShaperStepConfig]


class PipelineData(TypedDict, total=False):
    """Full content of a saved pipeline file.

    Serialized to/from JSON by ``PipelineService``.
    Uses the **nested** ``PipelineStep`` format.
    """

    name: str
    description: str
    pipeline: list["PipelineStep"]
    timestamp: str


# ──────────────────────────────────────────────────────────────────────
# Parse Variable Configuration
# ──────────────────────────────────────────────────────────────────────


class ParseVariableConfig(TypedDict, total=False):
    """Configuration for a gem5 variable to parse.

    Created by the variable editor UI and stored in
    ``StateManager.get_parse_variables()``.  Consumed by the parser
    layer (``Gem5Parser``) and by portfolio serialization.

    ``name``, ``type``, and ``_id`` are always set when created through
    the UI.
    """

    # Required (always present)
    name: str
    type: str
    _id: str

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

    name: str
    type: str
    entries: list[str]
    minimum: float
    maximum: float
    pattern_indices: list[str]


# ──────────────────────────────────────────────────────────────────────
# Pipeline Steps (stored in plots)
# ──────────────────────────────────────────────────────────────────────


class PipelineStep(TypedDict, total=False):
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
