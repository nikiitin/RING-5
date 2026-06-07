---
title: "Core Models Reference"
parent: Core
grand_parent: Developer Guide
nav_order: 1
---

# Core Models Reference

> RING-5 Unified Engine v2 -- Exhaustive catalog of every model class, type alias,
> and protocol in `src/core/models/`.

---

## 1. Overview

The core model layer (`src/core/models/`) defines the **common language** shared
across the three architectural layers: Parsing (Layer A), Application API
(Layer B), and Presentation (Layer C). It lives outside any single layer so that
every module can depend on it without circular or upward imports.

### Design Principles

1. **Immutability where possible** -- Parsing models use `frozen=True` dataclasses
   to guarantee reproducibility across threads.
2. **TypedDict for serialization** -- Service-layer data structures use `TypedDict`
   to replace untyped `Dict[str, Any]`.
3. **Discriminated unions** -- Shaper configurations use a `Union` of per-type
   TypedDicts discriminated by the `type` field.
4. **Engine-agnostic visualization** -- The `visualization/` sub-package defines
   dataclass configs consumed by both Plotly and matplotlib connectors; neither
   modifies them.
5. **Protocol-based decoupling** -- `PlotProtocol` uses `typing.Protocol` with
   `runtime_checkable` to decouple core from web-layer concrete implementations.
6. **Sentinel-based inheritance** -- Typography and legend configs use `-1`
   sentinel values to express "inherit from parent," resolved top-down by
   `resolve_spec()`.

### File Layout

```
src/core/models/
    __init__.py                    # Public API re-exports (28 symbols)
    data_models.py                 # TypedDicts: CSV pool, config persistence, pipeline, cache
    parsing_models.py              # Frozen dataclasses: ScannedVariable, StatConfig, ParseBatchResult
    history_models.py              # TypedDict: OperationRecord
    plot_protocol.py               # Protocol: PlotProtocol + PlotDeserializer alias
    plot_config.py                 # TypedDict: ShapeConfig
    portfolio_models.py            # TypedDict: PortfolioData
    shaper_models.py               # TypedDicts: 10 shaper configs + ShaperStepConfig union
    csv_contract.py                # Constants + validate_parser_csv() function
    visualization/
        __init__.py                # Package re-exports
        figure_config.py           # FigureConfig, DimensionConfig, MarginsConfig, SeparatorConfig
        trace_config.py            # TraceConfig + 5 subclasses
        axis_config.py             # AxisConfig, AxesConfig
        legend_config.py           # LegendConfig, LegendSpacingConfig, ColorbarConfig
        typography_config.py       # TypographyConfig
        annotation_config.py       # AnnotationConfig, ReferenceLineConfig
        data_label_config.py       # DataLabelConfig (frozen)
        series_style_config.py     # SeriesStyleConfig (frozen)
        palettes.py                # PALETTE_REGISTRY (18 palettes)
        trace_build_result.py      # TraceBuildResult
```

---

## 2. Data Models

**File**: `src/core/models/data_models.py`

Service-layer TypedDicts defining exact shapes of dictionaries exchanged between
services, protocols, and APIs.

### 2.1 CsvMetadata

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=True) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `columns` | `list[str]` | Yes | -- |
| `rows` | `int` | Yes | -- |
| `dtypes` | `dict[str, str]` | Yes | -- |

### 2.2 CsvPoolEntry

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False, with `Required` markers) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `path` | `str` | **Required** | -- |
| `name` | `str` | **Required** | -- |
| `size` | `int` | **Required** | -- |
| `modified` | `float` | **Required** | -- |
| `columns` | `list[str]` | Optional | -- |
| `rows` | `int` | Optional | -- |
| `dtypes` | `dict[str, str]` | Optional | -- |

The `total=False` with explicit `Required` markers creates a mixed TypedDict
where filesystem fields are always present but metadata fields appear only when
caching succeeds.

### 2.3 SavedConfigEntry

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=True) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `path` | `str` | Yes | -- |
| `name` | `str` | Yes | -- |
| `modified` | `float` | Yes | -- |
| `description` | `str` | Yes | -- |

### 2.4 SavedConfigData

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False, with `Required` markers) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `name` | `str` | **Required** | -- |
| `description` | `str` | Optional | -- |
| `timestamp` | `str` | Optional | -- |
| `shapers` | `list[ShaperStepConfig]` | **Required** | -- |
| `csv_path` | `str \| None` | Optional | -- |

### 2.5 PipelineData

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False, with `Required` markers) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `name` | `str` | **Required** | -- |
| `description` | `str` | Optional | -- |
| `pipeline` | `list[PipelineStep]` | **Required** | -- |
| `timestamp` | `str` | Optional | -- |

### 2.6 ParseVariableConfig

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False, with `Required` markers) |
| **File** | `src/core/models/data_models.py` |

The largest TypedDict in the system (18 fields). Most fields are optional because
they apply only to specific variable types (vector, distribution, histogram).

| Field | Type | Required | Default |
|---|---|---|---|
| `name` | `str` | **Required** | -- |
| `type` | `str` | **Required** | -- |
| `_id` | `str` | **Required** | -- |
| `alias` | `str` | Optional | -- |
| `vectorEntries` | `list[str] \| str` | Optional | -- |
| `useSpecialMembers` | `bool` | Optional | -- |
| `statisticsOnly` | `bool` | Optional | -- |
| `statistics` | `list[str]` | Optional | -- |
| `minimum` | `float` | Optional | -- |
| `maximum` | `float` | Optional | -- |
| `enableRebin` | `bool` | Optional | -- |
| `bins` | `int` | Optional | -- |
| `max_range` | `float` | Optional | -- |
| `onEmpty` | `str` | Optional | -- |
| `repeat` | `str` | Optional | -- |
| `patternSelection` | `list[str]` | Optional | -- |
| `parsed_ids` | `list[str]` | Optional | -- |
| `keepIndices` | `bool` | Optional | -- |

### 2.7 ScannedVariableDict

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False, with `Required` markers) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `name` | `str` | **Required** | -- |
| `type` | `str` | **Required** | -- |
| `entries` | `list[str]` | **Required** | -- |
| `minimum` | `float` | Optional | -- |
| `maximum` | `float` | Optional | -- |
| `pattern_indices` | `list[str]` | Optional | -- |
| `count` | `int` | Optional | -- |

### 2.8 PipelineStep

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=True) |
| **File** | `src/core/models/data_models.py` |

Wraps a `ShaperStepConfig` inside an `id`/`type`/`config` envelope for pipeline
ordering. Distinct from the flat `ShaperStepConfig` format.

| Field | Type | Required | Default |
|---|---|---|---|
| `id` | `int` | Yes | -- |
| `type` | `str` | Yes | -- |
| `config` | `ShaperStepConfig` | Yes | -- |

### 2.9 ColumnInfoResult

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=True) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `total_columns` | `int` | Yes | -- |
| `total_rows` | `int` | Yes | -- |
| `numeric_columns` | `list[str]` | Yes | -- |
| `categorical_columns` | `list[str]` | Yes | -- |
| `columns` | `list[str]` | Yes | -- |

### 2.10 CacheStatsEntry

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `size` | `int` | Optional | -- |
| `maxsize` | `int` | Optional | -- |
| `hits` | `int` | Optional | -- |
| `misses` | `int` | Optional | -- |
| `hit_rate` | `float` | Optional | -- |

### 2.11 CacheStatsInfo

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=True) |
| **File** | `src/core/models/data_models.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `metadata_cache` | `CacheStatsEntry` | Yes | -- |
| `dataframe_cache` | `CacheStatsEntry` | Yes | -- |
| `index_size` | `int` | Yes | -- |

---

## 3. Parsing Models

**File**: `src/core/models/parsing_models.py`

Frozen dataclasses representing the common language shared across all layers.
All models are `frozen=True` for thread-safe sharing across concurrent parsing workers.

### 3.1 StatParamValue (type alias)

```python
StatParamValue = str | int | float | bool | list[str] | None
```

Union type for `StatConfig.params` dictionary values.

### 3.2 ParseBatchResult

| Property | Value |
|---|---|
| **Kind** | `dataclass` (frozen=True) |
| **File** | `src/core/models/parsing_models.py` |

| Field | Type | Default |
|---|---|---|
| `futures` | `list[Future[dict[str, Any]]]` | -- (required) |
| `var_names` | `list[str]` | -- (required) |

Bundles futures with variable names so `construct_final_csv` can guarantee
column ordering without relying on shared mutable state.

### 3.3 ScannedVariable

| Property | Value |
|---|---|
| **Kind** | `dataclass` (frozen=True) |
| **File** | `src/core/models/parsing_models.py` |

| Field | Type | Default |
|---|---|---|
| `name` | `str` | -- (required) |
| `type` | `str` | -- (required) |
| `entries` | `list[str]` | `[]` (factory) |
| `pattern_indices` | `list[str] \| None` | `None` |

**Methods**:

| Method | Signature | Purpose |
|---|---|---|
| `to_dict()` | `() -> ScannedVariableDict` | Serialize to dict. Conditionally includes `pattern_indices` only when not `None`. |
| `from_dict()` | `(cls, data: ScannedVariableDict) -> ScannedVariable` | Class method to reconstruct from dict. |

### 3.4 StatConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (frozen=True) |
| **File** | `src/core/models/parsing_models.py` |

| Field | Type | Default |
|---|---|---|
| `name` | `str` | -- (required) |
| `type` | `str` | -- (required) |
| `repeat` | `int` | `1` |
| `params` | `dict[str, StatParamValue]` | `{}` (factory) |
| `statistics_only` | `bool` | `False` |
| `is_regex` | `bool` | `False` |
| `keep_indices` | `bool` | `False` |

---

## 4. Shaper Models

**File**: `src/core/models/shaper_models.py`

Discriminated union of per-type shaper configurations. Each shaper type has
exactly the fields it needs, replacing the old flat 39-field mega-union.

### 4.1 BaseShaperConfig

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False, with `Required` markers) |
| **Inherited by** | All other shaper configs |

| Field | Type | Required | Default |
|---|---|---|---|
| `type` | `str` | **Required** | -- |
| `id` | `int` | Optional | -- |

### 4.2 MeanShaperConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `meanVars` | `list[str]` | **Required** | -- |
| `meanAlgorithm` | `str` | **Required** | -- |
| `groupingColumns` | `list[str]` | **Required** | -- |
| `replacingColumn` | `str` | **Required** | -- |

### 4.3 NormalizeShaperConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `normalizeVars` | `list[str]` | **Required** | -- |
| `normalizerColumn` | `str` | **Required** | -- |
| `normalizerValue` | `str` | **Required** | -- |
| `groupBy` | `list[str]` | **Required** | -- |
| `normalizerVars` | `list[str]` | Optional | -- |
| `normalizeSd` | `bool` | Optional | -- |

### 4.4 SortShaperConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `order_dict` | `dict[str, list[str]]` | **Required** | -- |

### 4.5 SplitApplyGroupConfig

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False) -- does NOT inherit `BaseShaperConfig` |

| Field | Type | Required | Default |
|---|---|---|---|
| `columns` | `list[str]` | Optional | -- |
| `pipeline` | `list[ShaperStepConfig]` | Optional | -- |

This is a sub-component of `SplitApplyShaperConfig`, not a standalone shaper.
Contains a recursive reference to `ShaperStepConfig` for nested pipeline
composition.

### 4.6 SplitApplyShaperConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `joinColumns` | `list[str]` | **Required** | -- |
| `groups` | `list[SplitApplyGroupConfig]` | **Required** | -- |

### 4.7 TransformerShaperConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `column` | `str` | **Required** | -- |
| `target_type` | `str` | **Required** | -- |
| `order` | `list[str] \| None` | Optional | -- |

### 4.8 ColumnSelectorConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `columns` | `list[str]` | **Required** | -- |

### 4.9 ConditionSelectorConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `column` | `str` | **Required** | -- |
| `mode` | `str` | **Required** | -- |
| `threshold` | `float` | Optional | -- |
| `range` | `list[float]` | Optional | -- |
| `values` | `list[str]` | Optional | -- |

### 4.10 ItemSelectorConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `column` | `str` | **Required** | -- |
| `strings` | `list[str]` | **Required** | -- |
| `mode` | `str` | Optional | -- |

### 4.11 PivotLongerShaperConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `id_vars` | `list[str]` | **Required** | -- |
| `value_vars` | `list[str]` | **Required** | -- |
| `var_name` | `str` | **Required** | -- |
| `value_name` | `str` | **Required** | -- |
| `extract_pattern` | `str` | Optional | -- |
| `extract_group_indices` | `list[int]` | Optional | -- |
| `extract_separator` | `str` | Optional | -- |
| `selection_filters` | `dict[int, list[str]]` | Optional | -- |
| `selection_strategy` | `str` | Optional | -- |
| `merge_label` | `str` | Optional | -- |

### 4.12 PivotWiderShaperConfig (extends BaseShaperConfig)

| Field | Type | Required | Default |
|---|---|---|---|
| `index` | `list[str]` | **Required** | -- |
| `columns` | `str` | **Required** | -- |
| `values` | `str` | **Required** | -- |

### 4.13 ShaperStepConfig (type alias)

```python
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
```

Discriminated union of all shaper configurations. The `type` field from
`BaseShaperConfig` acts as the discriminator. Consumers use `config["type"]`
to determine the specific config shape.

---

## 5. Portfolio Models

**File**: `src/core/models/portfolio_models.py`

### 5.1 PortfolioData

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False) |
| **File** | `src/core/models/portfolio_models.py` |

Complete session state for save/restore. All fields are optional to support
incremental portfolio restoration.

| Field | Type | Required | Default |
|---|---|---|---|
| `parse_variables` | `list[ParseVariableConfig]` | Optional | -- |
| `stats_path` | `str` | Optional | -- |
| `stats_pattern` | `str` | Optional | -- |
| `csv_path` | `str` | Optional | -- |
| `use_parser` | `bool` | Optional | -- |
| `scanned_variables` | `list[ScannedVariableDict]` | Optional | -- |
| `data_csv` | `str` | Optional | -- |
| `plots` | `list[dict[str, Any]]` | Optional | -- |
| `plot_counter` | `int` | Optional | -- |
| `config` | `dict[str, Any]` | Optional | -- |
| `shapers` | `list[ShaperStepConfig]` | Optional | -- |
| `manager_history` | `list[OperationRecord]` | Optional | -- |
| `portfolio_history` | `list[OperationRecord]` | Optional | -- |

This is the highest-connectivity TypedDict in the system, referencing
`ParseVariableConfig`, `ScannedVariableDict`, `ShaperStepConfig`, and
`OperationRecord`.

---

## 6. History Models

**File**: `src/core/models/history_models.py`

### 6.1 OperationRecord

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=True) |
| **File** | `src/core/models/history_models.py` |

Tracks data transformation operations performed by managers (preprocessor,
mixer, outlier remover, seeds reducer).

| Field | Type | Required | Default |
|---|---|---|---|
| `source_columns` | `list[str]` | Yes | -- |
| `dest_columns` | `list[str]` | Yes | -- |
| `operation` | `str` | Yes | -- |
| `timestamp` | `str` | Yes | -- |

---

## 7. Plot Protocol and Config

**File**: `src/core/models/plot_protocol.py`

### 7.1 PlotProtocol

| Property | Value |
|---|---|
| **Kind** | `Protocol` (runtime_checkable) |
| **File** | `src/core/models/plot_protocol.py` |
| **Implemented by** | `BasePlot` (web layer) and its subclasses |

| Attribute | Type |
|---|---|
| `plot_id` | `int` |
| `name` | `str` |
| `plot_type` | `str` |
| `config` | `dict[str, Any]` |
| `pipeline` | `list[PipelineStep]` |
| `pipeline_counter` | `int` |
| `legend_mappings_by_column` | `dict[str, dict[str, str]]` |
| `legend_mappings` | `dict[str, str]` |
| `processed_data` | `pd.DataFrame \| None` |

**Methods**:

| Method | Signature | Purpose |
|---|---|---|
| `to_dict()` | `() -> dict[str, Any]` | Serialize the plot to a dictionary |

Using `@runtime_checkable` enables `isinstance()` checks without requiring
concrete inheritance. This is the key boundary between core and web layers.

### 7.2 PlotDeserializer (type alias)

```python
PlotDeserializer = Callable[[dict[str, Any]], PlotProtocol | None]
```

Injected at startup so the core layer never imports web-layer classes.
Returns `None` when deserialization fails.

### 7.3 ShapeConfig

| Property | Value |
|---|---|
| **Kind** | `TypedDict` (total=False, with `Required` markers) |
| **File** | `src/core/models/plot_config.py` |

| Field | Type | Required | Default |
|---|---|---|---|
| `type` | `str` | **Required** | -- |
| `x0` | `float \| str` | **Required** | -- |
| `y0` | `float \| str` | **Required** | -- |
| `x1` | `float \| str` | **Required** | -- |
| `y1` | `float \| str` | **Required** | -- |
| `line` | `dict[str, str \| float \| int]` | Optional | -- |

---

## 8. Visualization Config Hierarchy

The visualization sub-package (`src/core/models/visualization/`) defines the
engine-agnostic configuration tree consumed by both Plotly and matplotlib
connectors.

### 8.1 MarginsConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/figure_config.py` |

| Field | Type | Default |
|---|---|---|
| `top` | `float` | `40.0` |
| `bottom` | `float` | `80.0` |
| `left` | `float` | `60.0` |
| `right` | `float` | `30.0` |
| `pad` | `float` | `0.0` |

**Methods**: `to_dict() -> dict[str, float]`

### 8.2 DimensionConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/figure_config.py` |

| Field | Type | Default |
|---|---|---|
| `width` | `float` | `7.0` |
| `height` | `float` | `4.0` |
| `dpi` | `int` | `300` |
| `margins` | `MarginsConfig` | `MarginsConfig()` |
| `bar_width_scale` | `float` | `1.0` |
| `bargap` | `float` | `0.15` |
| `bargroupgap` | `float` | `0.1` |

### 8.3 SeparatorConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/figure_config.py` |

| Field | Type | Default |
|---|---|---|
| `enabled` | `bool` | `False` |
| `style` | `Literal["solid", "dash", "dot", "dashdot"]` | `"dash"` |
| `color` | `str` | `"gray"` |

### 8.4 FigureConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/figure_config.py` |

The top-level container and single source of truth for a complete figure
description.

| Field | Type | Default |
|---|---|---|
| `dimensions` | `DimensionConfig` | `DimensionConfig()` |
| `typography` | `TypographyConfig` | `None` -> `TypographyConfig()` via `__post_init__` |
| `axes` | `AxesConfig` | `None` -> `AxesConfig()` via `__post_init__` |
| `legends` | `list[LegendConfig]` | `[]` |
| `traces` | `list[TraceConfig]` | `[]` |
| `annotations` | `list[AnnotationConfig]` | `[]` |
| `separator` | `SeparatorConfig` | `SeparatorConfig()` |
| `data_labels` | `DataLabelConfig \| None` | `None` |
| `series_styles` | `list[SeriesStyleConfig]` | `[]` |
| `trace_overrides` | `dict[str, SeriesStyleConfig]` | `{}` |
| `color_palette` | `list[str]` | Wong 8-color palette |
| `barmode` | `Literal["group", "stack", "overlay", "relative"]` | `"group"` |
| `hatching_sequence` | `list[str]` | `["/", "\\", "\|", "-", "+", "x", "o", "O"]` |
| `reference_lines` | `list[ReferenceLineConfig]` | `[]` |
| `hovermode` | `str` | `"x unified"` |
| `enable_stripes` | `bool` | `False` |
| `show_error_bars` | `bool` | `False` |
| `title` | `str` | `""` |
| `paper_bgcolor` | `str` | `"white"` |
| `plot_bgcolor` | `str` | `"white"` |
| `font_family` | `str` | `"serif"` |
| `latex_extra_preamble` | `str` | `""` |
| `metadata` | `dict[str, str]` | `{}` |

**Methods**:

| Method | Signature | Purpose |
|---|---|---|
| `__post_init__()` | `() -> None` | Lazy-initializes `typography` and `axes` to avoid circular deps |
| `to_dict()` | `() -> dict[str, Any]` | Full recursive serialization via `dataclasses.asdict()` |
| `from_dict()` | `(cls, data) -> FigureConfig` | Full round-trip deserialization with sub-config reconstruction |

**Workflow**:
1. Build from user config (`PlotlyFigureSpecBuilder`)
2. Optionally overlay a preset (`PresetSpecBuilder`)
3. Resolve sentinels (`resolve_spec`)
4. Pass to a connector (`FigureSpecToPlotly` / `FigureSpecToMatplotlib`)

### 8.5 TraceConfig (base)

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/trace_config.py` |

| Field | Type | Default |
|---|---|---|
| `name` | `str` | `""` |
| `trace_type` | `Literal["bar", "line", "scatter", "histogram", "heatmap"]` | `"bar"` |
| `x` | `list[str \| int \| float]` | `[]` |
| `y` | `list[int \| float]` | `[]` |
| `yaxis` | `Literal["y", "y2"]` | `"y"` |
| `color` | `str` | `""` |
| `opacity` | `float` | `1.0` |
| `visible` | `bool` | `True` |
| `show_in_legend` | `bool` | `True` |
| `legendgroup` | `str` | `""` |
| `custom_data` | `dict[str, Any]` | `{}` |

### 8.6 BarTraceConfig (extends TraceConfig)

All 11 base fields inherited, plus:

| Field | Type | Default |
|---|---|---|
| `x_positions` | `list[float]` | `[]` |
| `bar_width` | `float` | `0.8` |
| `offset` | `float` | `0.0` |
| `pattern` | `str` | `""` |
| `border_width` | `float` | `0.0` |
| `border_color` | `str` | `""` |
| `text_values` | `list[str] \| None` | `None` |
| `text_position` | `Literal["inside", "outside", "auto", "none"]` | `"none"` |
| `text_angle` | `float` | `0.0` |
| `text_font_size` | `int` | `6` |
| `error_y` | `list[float] \| None` | `None` |

### 8.7 LineTraceConfig (extends TraceConfig)

All 11 base fields inherited, plus:

| Field | Type | Default |
|---|---|---|
| `line_width` | `float` | `2.0` |
| `line_dash` | `Literal["solid", "dash", "dot", "dashdot", "longdash"]` | `"solid"` |
| `marker_symbol` | `str` | `"circle"` |
| `marker_size` | `int` | `6` |
| `show_markers` | `bool` | `True` |
| `fill` | `Literal["none", "tozeroy", "tonexty"]` | `"none"` |
| `error_y` | `list[float] \| None` | `None` |

### 8.8 ScatterTraceConfig (extends TraceConfig)

All 11 base fields inherited, plus:

| Field | Type | Default |
|---|---|---|
| `marker_symbol` | `str` | `"circle"` |
| `marker_size` | `int` | `8` |
| `marker_line_width` | `float` | `0.0` |
| `marker_line_color` | `str` | `""` |
| `colorscale` | `str \| None` | `None` |
| `size_values` | `list[float] \| None` | `None` |
| `error_y` | `list[float] \| None` | `None` |

### 8.9 HistogramTraceConfig (extends TraceConfig)

All 11 base fields inherited, plus:

| Field | Type | Default |
|---|---|---|
| `nbins` | `int` | `20` |
| `normalization` | `Literal["", "percent", "probability", "density"]` | `""` |
| `cumulative` | `bool` | `False` |

### 8.10 HeatmapTraceConfig (extends TraceConfig)

All 11 base fields inherited, plus:

| Field | Type | Default |
|---|---|---|
| `col_labels` | `list[str]` | `[]` |
| `row_labels` | `list[str]` | `[]` |
| `z` | `list[list[float \| None]]` | `[]` |
| `colorscale` | `str \| list[list[str \| float]]` | `"Viridis"` |
| `show_values` | `bool` | `True` |
| `text` | `list[list[str]] \| None` | `None` |
| `text_font_size` | `int` | `10` |
| `text_color_mode` | `str` | `"contrast"` |
| `text_color` | `str` | `"#000000"` |
| `totals_position` | `str` | `""` |
| `totals_count` | `int` | `0` |

### 8.11 Trace Inheritance Hierarchy

```
TraceConfig (base, 11 fields)
    BarTraceConfig       (trace_type="bar",       +11 fields = 22 total)
    LineTraceConfig      (trace_type="line",       +7 fields  = 18 total)
    ScatterTraceConfig   (trace_type="scatter",    +7 fields  = 18 total)
    HistogramTraceConfig (trace_type="histogram",  +3 fields  = 14 total)
    HeatmapTraceConfig   (trace_type="heatmap",   +11 fields  = 22 total)
```

### 8.12 AxisConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/axis_config.py` |
| **Total fields** | 28 |

**Label fields**:

| Field | Type | Default |
|---|---|---|
| `label` | `str` | `""` |
| `label_pad` | `float` | `10.0` |
| `label_position` | `float` | `0.5` |
| `label_standoff` | `int` | `-1` |
| `title_vshift` | `float` | `0.0` |

**Tick fields**:

| Field | Type | Default |
|---|---|---|
| `tick_angle` | `float` | `0.0` |
| `tick_pad` | `float` | `5.0` |
| `tick_ha` | `Literal["left", "center", "right"]` | `"center"` |
| `tick_offset` | `float` | `0.0` |
| `tick_values` | `list[float \| int \| str] \| None` | `None` |
| `tick_text` | `list[str] \| None` | `None` |
| `tick_font_color` | `str` | `""` |
| `show_ticks` | `bool` | `True` |
| `tick_side` | `str` | `""` |
| `tick_dash` | `str` | `"solid"` |
| `show_tick_labels` | `bool` | `True` |
| `dtick` | `float \| None` | `None` |

**Range and scale fields**:

| Field | Type | Default |
|---|---|---|
| `range` | `list[float] \| None` | `None` |
| `scale` | `Literal["linear", "log"]` | `"linear"` |
| `margin` | `float` | `0.02` |
| `automargin` | `bool` | `True` |

**Grid fields**:

| Field | Type | Default |
|---|---|---|
| `show_grid` | `bool` | `True` |
| `grid_color` | `str` | `"#E5E5E5"` |
| `grid_width` | `float` | `1.0` |
| `axis_color` | `str` | `"#444"` |
| `axis_line_color` | `str` | `""` |
| `axis_line_width` | `float` | `1.0` |

**Ordering fields**:

| Field | Type | Default |
|---|---|---|
| `category_order` | `list[str] \| None` | `None` |
| `label_aliases` | `dict[str, str] \| None` | `None` |

**Methods**: `to_dict()`, `from_dict(cls, data)` -- standard serialization pair.
`from_dict` filters unknown keys via `__dataclass_fields__`.

### 8.13 AxesConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/axis_config.py` |

| Field | Type | Default |
|---|---|---|
| `x` | `AxisConfig` | `AxisConfig()` |
| `y` | `AxisConfig` | `AxisConfig()` |
| `y2` | `AxisConfig \| None` | `None` |
| `group_label_offset` | `float` | `-0.12` |
| `group_label_alternate` | `bool` | `True` |
| `group_label_alt_spacing` | `float` | `0.05` |
| `group_order` | `list[str] \| None` | `None` |
| `top_axis_line_width` | `float` | `0.0` |
| `top_axis_line_color` | `str` | `"#444"` |
| `right_axis_line_width` | `float` | `0.0` |
| `right_axis_line_color` | `str` | `"#444"` |

**Methods**: `to_dict()`, `from_dict(cls, data)` -- reconstructs all sub-axes.

### 8.14 TypographyConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/typography_config.py` |
| **Total fields** | 24 (14 sizes + 10 bold flags) |

**Module constants**: `INHERIT: int = -1`, `INHERIT_F: float = -1.0`

**Inheritance chain** (resolved top-down by `resolve_spec()`):

```
font_size_base (root)
    font_size_title
    font_size_xlabel
    font_size_ylabel
        font_size_y2label  (inherits ylabel if -1)
    font_size_ticks
        font_size_yticks   (inherits ticks if -1)
            font_size_y2ticks  (inherits yticks if -1)
    font_size_annotations
    font_size_legend       (primary legend)
        font_size_legend2  (inherits legend if -1)
        font_size_legend3  (inherits legend if -1)
            legend3_number_fontsize  (inherits legend3 if -1)
            legend3_text_fontsize    (inherits legend3 if -1)
```

**Size fields**:

| Field | Type | Default |
|---|---|---|
| `font_size_base` | `int` | `10` |
| `font_size_title` | `int` | `10` |
| `font_size_xlabel` | `int` | `9` |
| `font_size_ylabel` | `int` | `9` |
| `font_size_y2label` | `int` | `-1` |
| `font_size_ticks` | `int` | `7` |
| `font_size_yticks` | `int` | `7` |
| `font_size_y2ticks` | `int` | `-1` |
| `font_size_annotations` | `int` | `6` |
| `font_size_legend` | `int` | `8` |
| `font_size_legend2` | `int` | `-1` |
| `font_size_legend3` | `int` | `-1` |
| `legend3_number_fontsize` | `int` | `-1` |
| `legend3_text_fontsize` | `int` | `-1` |

**Bold flags**:

| Field | Type | Default |
|---|---|---|
| `bold_title` | `bool` | `False` |
| `bold_xlabel` | `bool` | `False` |
| `bold_ylabel` | `bool` | `False` |
| `bold_y2label` | `bool` | `False` |
| `bold_ticks` | `bool` | `False` |
| `bold_annotations` | `bool` | `True` |
| `bold_group_labels` | `bool` | `True` |
| `bold_legend` | `bool` | `False` |
| `bold_legend2` | `bool` | `False` |
| `bold_legend3` | `bool` | `False` |

### 8.15 LegendConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/legend_config.py` |
| **Total fields** | 33 (the largest dataclass in the visualization sub-package) |

**Role and visibility**:

| Field | Type | Default |
|---|---|---|
| `role` | `Literal["primary", "secondary", "tertiary"]` | `"primary"` |
| `visible` | `bool` | `True` |

**Typography**:

| Field | Type | Default |
|---|---|---|
| `font_size` | `int` | `8` |
| `font_family` | `str` | `""` |
| `bold` | `bool` | `False` |

**Layout**:

| Field | Type | Default |
|---|---|---|
| `ncol` | `int` | `1` |
| `col_width` | `float` | `-1.0` |
| `entrywidth` | `int` | `0` |
| `indentation` | `int` | `0` |
| `orientation` | `Literal["horizontal", "vertical"]` | `"vertical"` |
| `itemsizing` | `Literal["constant", "trace"]` | `"constant"` |
| `itemwidth` | `int` | `30` |
| `tracegroupgap` | `int` | `10` |
| `order` | `Literal["normal", "reversed"]` | `"normal"` |
| `trace_distribution` | `str` | `""` |

**Position**:

| Field | Type | Default |
|---|---|---|
| `position_x` | `float` | `-1.0` |
| `position_y` | `float` | `-1.0` |
| `anchor_x` | `Literal["left", "center", "right", "auto"]` | `"auto"` |
| `anchor_y` | `Literal["top", "middle", "bottom", "auto"]` | `"auto"` |
| `valign` | `Literal["top", "middle", "bottom"]` | `"middle"` |
| `custom_position` | `bool` | `False` |

**Styling**:

| Field | Type | Default |
|---|---|---|
| `bgcolor` | `str` | `""` |
| `border_width` | `float` | `0.0` |
| `border_color` | `str` | `"#444"` |
| `font_color` | `str` | `"#444"` |
| `title_font_color` | `str` | `"#444"` |
| `title_font_size` | `int` | `-1` |
| `title` | `str` | `""` |

**Sub-configs**:

| Field | Type | Default |
|---|---|---|
| `spacing` | `LegendSpacingConfig` | `LegendSpacingConfig()` |
| `colorbar` | `ColorbarConfig` | `ColorbarConfig()` |

**Tertiary-annotation extras**:

| Field | Type | Default |
|---|---|---|
| `number_fontsize` | `int` | `-1` |
| `text_fontsize` | `int` | `-1` |

**Methods**:

| Method | Signature | Purpose |
|---|---|---|
| `derive_anchors()` | `(position_x, position_y) -> tuple[str, str]` | Static. Auto-derives anchor from position. |
| `to_dict()` | `() -> dict[str, Any]` | Full serialization including sub-configs. |
| `from_dict()` | `(cls, data) -> LegendConfig` | Reconstructs with sub-config deserialization. |

### 8.16 LegendSpacingConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/legend_config.py` |

| Field | Type | Default |
|---|---|---|
| `columnspacing` | `float` | `0.5` |
| `handletextpad` | `float` | `0.3` |
| `labelspacing` | `float` | `0.2` |
| `handlelength` | `float` | `1.0` |
| `handleheight` | `float` | `0.7` |
| `borderpad` | `float` | `0.2` |
| `borderaxespad` | `float` | `0.5` |

**Methods**: `to_dict()`, `from_dict(cls, data)` -- standard serialization pair.

### 8.17 ColorbarConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/legend_config.py` |

| Field | Type | Default |
|---|---|---|
| `title_side` | `Literal["top", "right", "bottom", "left"]` | `"top"` |
| `range_mode` | `Literal["auto", "manual"]` | `"auto"` |
| `zmin` | `float \| None` | `None` |
| `zmax` | `float \| None` | `None` |
| `nticks` | `int` | `5` |
| `tick_decimals` | `int` | `2` |
| `shared` | `bool` | `True` |
| `tick_angle` | `float` | `0.0` |
| `tick_side` | `str` | `"right"` |

**Methods**: `to_dict()`, `from_dict(cls, data)` -- standard serialization pair.

### 8.18 AnnotationConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/annotation_config.py` |
| **Total fields** | 20 |

| Field | Type | Default |
|---|---|---|
| `text` | `str` | `""` |
| `annotation_type` | `Literal["text", "bar_value", "group_label", "boxed"]` | `"text"` |
| `x` | `float \| str` | `0.0` |
| `y` | `float \| str` | `0.0` |
| `xref` | `Literal["data", "paper"]` | `"data"` |
| `yref` | `Literal["data", "paper"]` | `"data"` |
| `xanchor` | `Literal["left", "center", "right", "auto"]` | `"auto"` |
| `yanchor` | `Literal["top", "middle", "bottom", "auto"]` | `"auto"` |
| `text_angle` | `float` | `0.0` |
| `show_arrow` | `bool` | `False` |
| `arrow_head` | `int` | `0` |
| `arrow_color` | `str` | `"#444"` |
| `font_size` | `int` | `-1` |
| `font_color` | `str` | `"#444"` |
| `font_bold` | `bool` | `False` |
| `border_width` | `float` | `0.0` |
| `border_color` | `str` | `"#444"` |
| `border_pad` | `float` | `2.0` |
| `bgcolor` | `str` | `""` |
| `align` | `Literal["left", "center", "right"]` | `"left"` |

### 8.19 ReferenceLineConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/annotation_config.py` |

| Field | Type | Default |
|---|---|---|
| `enabled` | `bool` | `False` |
| `axis` | `Literal["x", "y"]` | `"y"` |
| `value` | `float` | `0.0` |
| `color` | `str` | `"red"` |
| `width` | `float` | `1.5` |
| `style` | `Literal["solid", "dash", "dot", "dashdot"]` | `"dash"` |
| `label` | `str` | `""` |

### 8.20 DataLabelConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (frozen=True) |
| **File** | `src/core/models/visualization/data_label_config.py` |
| **Total fields** | 12 |

| Field | Type | Default |
|---|---|---|
| `enabled` | `bool` | `False` |
| `color_mode` | `Literal["auto", "contrast", "custom"]` | `"auto"` |
| `custom_color` | `str` | `"#000000"` |
| `font_size` | `int` | `10` |
| `rotation` | `int` | `0` |
| `position` | `Literal["auto", "inside", "outside"]` | `"auto"` |
| `anchor` | `Literal["auto", "top", "middle", "bottom"]` | `"auto"` |
| `format_string` | `str` | `".2f"` |
| `display_logic` | `Literal["all", "above_threshold", "below_threshold"]` | `"all"` |
| `threshold` | `float` | `0.0` |
| `size_constraint` | `Literal["none", "inside"]` | `"none"` |
| `auto_contrast` | `bool` | `True` |

**Methods**: `to_dict()`, `from_dict(cls, data)` -- explicit field-by-field
serialization with type coercion.

### 8.21 SeriesStyleConfig

| Property | Value |
|---|---|
| **Kind** | `dataclass` (frozen=True) |
| **File** | `src/core/models/visualization/series_style_config.py` |
| **Total fields** | 9 |

| Field | Type | Default |
|---|---|---|
| `line_width` | `float` | `2.0` |
| `marker_size` | `int` | `6` |
| `opacity` | `float` | `1.0` |
| `bar_border_width` | `float` | `0.0` |
| `bar_border_color` | `str` | `""` |
| `hatching_pattern` | `str` | `""` |
| `color` | `str` | `""` |
| `symbol` | `str` | `""` |
| `display_name` | `str` | `""` |

**Methods**: `to_dict()`, `from_dict(cls, data)` -- explicit field-by-field
serialization with type coercion.

### 8.22 TraceBuildResult

| Property | Value |
|---|---|
| **Kind** | `dataclass` (mutable) |
| **File** | `src/core/models/visualization/trace_build_result.py` |

Return type of `BasePlot.create_traces()`. Bundles data traces with
layout-level metadata needed by connectors.

| Field | Type | Default |
|---|---|---|
| `traces` | `Sequence[TraceConfig]` | `[]` |
| `annotations` | `list[AnnotationConfig]` | `[]` |
| `layout_annotations` | `list[dict[str, Any]]` | `[]` |
| `shapes` | `list[ShapeConfig]` | `[]` |
| `barmode` | `str` | `"group"` |
| `custom_x_ticks` | `dict[str, list[float] \| list[str] \| list[bool]] \| None` | `None` |
| `secondary_y` | `bool` | `False` |

---

## 9. CSV Contract Types

**File**: `src/core/models/csv_contract.py`

Defines the mandatory CSV format that all simulator parsers must produce. The CSV
is the common language between Layer A (Parsing) and Layer B (Core).

### 9.1 Module Constants

| Constant | Type | Value | Purpose |
|---|---|---|---|
| `MISSING_VALUE` | `str` | `""` | Representation for missing values |
| `CSV_ENCODING` | `str` | `"utf-8"` | Character encoding for all CSV output |
| `CSV_DIALECT` | `str` | `"excel"` | CSV dialect for Python `csv` module |

### 9.2 validate_parser_csv()

```python
def validate_parser_csv(path: Path) -> list[str]
```

Validates a CSV file against the RING-5 parser contract. Returns a list of
warnings (empty means valid). Raises `FileNotFoundError` if the file does not
exist and `ValueError` if fundamentally invalid.

**Checks performed**:
1. File existence
2. Non-empty header row
3. Duplicate column name detection
4. Empty column name detection
5. Leading/trailing whitespace in column names
6. Data row existence
7. Column count consistency per row

---

## 10. Type Alias Catalog

| Alias | File | Definition |
|---|---|---|
| `StatParamValue` | `parsing_models.py` | `str \| int \| float \| bool \| list[str] \| None` |
| `PlotDeserializer` | `plot_protocol.py` | `Callable[[dict[str, Any]], PlotProtocol \| None]` |
| `ShaperStepConfig` | `shaper_models.py` | `Union[MeanShaperConfig, NormalizeShaperConfig, SortShaperConfig, SplitApplyShaperConfig, TransformerShaperConfig, ColumnSelectorConfig, ConditionSelectorConfig, ItemSelectorConfig, PivotLongerShaperConfig, PivotWiderShaperConfig]` |

---

## 11. See Also

- **State Management** -- `src/core/services/state_manager.py` consumes
  `ParseVariableConfig`, `ScannedVariableDict`, and `OperationRecord`.
- **Shaper Pipeline** -- `src/core/services/shaper/` implements the shapers
  whose configs are defined in `shaper_models.py`.
- **Visualization Connectors** -- `src/core/services/visualization/` translates
  `FigureConfig` trees into Plotly or matplotlib figures.
- **Portfolio Service** -- `src/core/services/portfolio_service.py` serializes
  and restores `PortfolioData`.
- **Palette Service** -- `src/core/services/visualization/palette_service.py`
  resolves palette names from `PALETTE_REGISTRY`.
- **Config Resolver** -- `src/core/services/visualization/config_resolver.py`
  implements `resolve_spec()` for sentinel inheritance in `TypographyConfig` and
  `LegendConfig`.
