"""
Shaper Models — Discriminated union of per-type shaper configurations.

Replaces the flat 39-field ``ShaperStepConfig`` mega-union with type-safe,
per-shaper TypedDicts. Each shaper type has exactly the fields it needs.

The ``ShaperStepConfig`` type alias is a Union of all per-type configs,
enabling type narrowing via the ``type`` discriminator field.

Categories:
    - Base: ``BaseShaperConfig`` — shared fields (``type``, ``id``)
    - Aggregation: ``MeanShaperConfig``
    - Normalization: ``NormalizeShaperConfig``
    - Ordering: ``SortShaperConfig``
    - Selection: ``ColumnSelectorConfig``, ``ConditionSelectorConfig``,
      ``ItemSelectorConfig``
    - Transformation: ``TransformerShaperConfig``
    - Composition: ``SplitApplyShaperConfig``, ``SplitApplyGroupConfig``
"""

from __future__ import annotations

from typing import Required, TypedDict, Union

# ──────────────────────────────────────────────────────────────────────
# Base Config (shared across all shapers)
# ──────────────────────────────────────────────────────────────────────


class BaseShaperConfig(TypedDict, total=False):
    """Fields shared by every shaper step.

    Attributes:
        type: Shaper identifier (factory registry key). Always present.
        id: Step ID for pipeline ordering. Present when stored in pipeline.
    """

    type: Required[str]
    id: int


# ──────────────────────────────────────────────────────────────────────
# Mean
# ──────────────────────────────────────────────────────────────────────


class MeanShaperConfig(BaseShaperConfig, total=False):
    """Configuration for the Mean aggregation shaper.

    Calculates arithmetic, geometric, or harmonic means for selected
    variables across groups and appends summary rows.

    Attributes:
        meanVars: Columns to aggregate (e.g., ``["ipc", "cpi"]``).
        meanAlgorithm: Algorithm name (``"arithmean"``, ``"geomean"``,
            ``"hmean"``).
        groupingColumns: Columns defining groups (e.g., ``["config"]``).
        replacingColumn: Column that will hold the mean label
            (e.g., ``"benchmark"`` → ``"geomean"``).
    """

    meanVars: Required[list[str]]
    meanAlgorithm: Required[str]
    groupingColumns: Required[list[str]]
    replacingColumn: Required[str]


# ──────────────────────────────────────────────────────────────────────
# Normalize
# ──────────────────────────────────────────────────────────────────────


class NormalizeShaperConfig(BaseShaperConfig, total=False):
    """Configuration for the Normalize shaper.

    Divides metric columns by a reference row's values to produce
    relative performance numbers (e.g., speedup over baseline).

    Attributes:
        normalizeVars: Columns to normalize (the numerator metrics).
        normalizerColumn: Column containing the reference category
            (e.g., ``"config"``).
        normalizerValue: The specific reference value within
            ``normalizerColumn`` (e.g., ``"baseline"``).
        groupBy: Columns defining normalization groups.
        normalizerVars: Additional variable columns for normalization
            context.
        normalizeSd: Whether to normalize standard deviation columns
            as well.
    """

    normalizeVars: Required[list[str]]
    normalizerColumn: Required[str]
    normalizerValue: Required[str]
    groupBy: Required[list[str]]
    normalizerVars: list[str]
    normalizeSd: bool


# ──────────────────────────────────────────────────────────────────────
# Sort
# ──────────────────────────────────────────────────────────────────────


class SortShaperConfig(BaseShaperConfig, total=False):
    """Configuration for the Sort shaper.

    Reorders DataFrame rows based on explicit category orderings.

    Attributes:
        order_dict: Mapping of column name → ordered list of values.
            E.g., ``{"benchmark": ["mcf", "omnetpp", "xalancbmk"]}``.
    """

    order_dict: Required[dict[str, list[str]]]


# ──────────────────────────────────────────────────────────────────────
# SplitApply
# ──────────────────────────────────────────────────────────────────────


class SplitApplyGroupConfig(TypedDict, total=False):
    """Configuration for a single group within a SplitApply shaper.

    Attributes:
        columns: Column values that define this group.
        pipeline: Sub-pipeline to apply to this group's data.
    """

    columns: list[str]
    pipeline: list[ShaperStepConfig]


class SplitApplyShaperConfig(BaseShaperConfig, total=False):
    """Configuration for the SplitApply (Per-Axis) shaper.

    Splits data by join columns, applies independent sub-pipelines
    to each group, and merges results back together.

    Attributes:
        joinColumns: Columns to split on (e.g., ``["benchmark"]``).
        groups: List of group definitions, each with its own pipeline.
    """

    joinColumns: Required[list[str]]
    groups: Required[list[SplitApplyGroupConfig]]


# ──────────────────────────────────────────────────────────────────────
# Transformer
# ──────────────────────────────────────────────────────────────────────


class TransformerShaperConfig(BaseShaperConfig, total=False):
    """Configuration for the Transformer shaper.

    Converts column types or reorders categorical values.

    Attributes:
        column: Target column to transform.
        target_type: Desired output type (e.g., ``"categorical"``,
            ``"numeric"``).
        order: Explicit category ordering (None = infer from data).
    """

    column: Required[str]
    target_type: Required[str]
    order: list[str] | None


# ──────────────────────────────────────────────────────────────────────
# ColumnSelector
# ──────────────────────────────────────────────────────────────────────


class ColumnSelectorConfig(BaseShaperConfig, total=False):
    """Configuration for the Column Selector shaper.

    Keeps only specified columns, dropping the rest.

    Attributes:
        columns: List of column names to retain.
    """

    columns: Required[list[str]]


# ──────────────────────────────────────────────────────────────────────
# ConditionSelector
# ──────────────────────────────────────────────────────────────────────


class ConditionSelectorConfig(BaseShaperConfig, total=False):
    """Configuration for the Condition Selector (Filter) shaper.

    Filters rows based on conditions applied to a column.

    Attributes:
        column: Column to filter on.
        mode: Filter mode (``"values"``, ``"range"``, ``"threshold"``,
            ``"top_n"``, ``"bottom_n"``).
        threshold: Numeric threshold for ``"threshold"`` mode.
        range: ``[min, max]`` for ``"range"`` mode.
        values: Allowed values for ``"values"`` mode.
    """

    column: Required[str]
    mode: Required[str]
    threshold: float
    range: list[float]
    values: list[str]


# ──────────────────────────────────────────────────────────────────────
# ItemSelector
# ──────────────────────────────────────────────────────────────────────


class ItemSelectorConfig(BaseShaperConfig, total=False):
    """Configuration for the Item Selector shaper.

    Selects rows where a column contains specific string values.

    Attributes:
        column: Column to match against.
        strings: Values to keep (include) or remove (exclude).
        mode: ``"include"`` or ``"exclude"``.
    """

    column: Required[str]
    strings: Required[list[str]]
    mode: str


# ──────────────────────────────────────────────────────────────────────
# Pivot
# ──────────────────────────────────────────────────────────────────────


class PivotLongerShaperConfig(BaseShaperConfig, total=False):
    """Configuration for the Pivot Longer (Melt) shaper.

    Pivots data from wide to long format.

    Attributes:
        id_vars: Columns to use as identifier variables.
        value_vars: Columns to unpivot.
        var_name: Name to use for the 'variable' column.
        value_name: Name to use for the 'value' column.
        extract_pattern: Regex pattern with a capture group to extract the variable part.
    """

    id_vars: Required[list[str]]
    value_vars: Required[list[str]]
    var_name: Required[str]
    value_name: Required[str]
    extract_pattern: str
    extract_group_indices: list[int]
    extract_separator: str
    selection_filters: dict[int, list[str]]
    selection_strategy: str  # "discard" or "merge"
    merge_label: str  # e.g. "other" or "9+"


class PivotWiderShaperConfig(BaseShaperConfig, total=False):
    """Configuration for the Pivot Wider shaper.

    Pivots data from long to wide format.

    Attributes:
        index: Columns to use to make new frame's index.
        columns: Column to use to make new frame's columns.
        values: Column(s) to use for populating new frame's values.
    """

    index: Required[list[str]]
    columns: Required[str]
    values: Required[str]


# ──────────────────────────────────────────────────────────────────────
# Discriminated Union Type Alias
# ──────────────────────────────────────────────────────────────────────
# Discriminated union of all shaper configurations.
#
# The ``type`` field in ``BaseShaperConfig`` acts as the discriminator.
# Use ``config["type"]`` to determine which specific config shape
# to expect.
#
# This replaces the old flat ``ShaperStepConfig`` mega-union from
# ``data_models.py``.
ShaperStepConfig = Union[
    MeanShaperConfig,
    NormalizeShaperConfig,
    SortShaperConfig,
    SplitApplyShaperConfig,
    TransformerShaperConfig,
    ColumnSelectorConfig,
    ConditionSelectorConfig,
    ItemSelectorConfig,
    PivotLongerShaperConfig,
    PivotWiderShaperConfig,
]
