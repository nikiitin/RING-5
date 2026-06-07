---
title: "Shaper Pipeline System"
parent: Visualization
grand_parent: Developer Guide
nav_order: 3
---

# Shaper Pipeline System

## Overview

The shaper pipeline is a composable data transformation system that converts
parsed simulation DataFrames into plot-ready datasets. Each **shaper** is a
single-responsibility transformation -- filtering, sorting, normalizing,
aggregating, pivoting, or type-converting -- and shapers are chained into an
ordered **pipeline** where the output of one step becomes the input of the
next.

The system is built on the Strategy and Factory design patterns. Users
assemble pipelines through the UI by selecting shaper types from a registry,
configuring each step, and reordering steps as needed. The pipeline is then
executed sequentially against a `pd.DataFrame`, producing the final dataset
consumed by the plotting subsystem.

Key source locations:

| Component | Path |
|-----------|------|
| Base class | `src/core/services/shapers/shaper.py` |
| Intermediate ABC | `src/core/services/shapers/uni_df_shaper.py` |
| Factory | `src/core/services/shapers/factory.py` |
| Pipeline service | `src/core/services/shapers/pipeline_service.py` |
| Validation | `src/core/services/shapers/validation.py` |
| Config models | `src/core/models/shaper_models.py` |
| Implementations | `src/core/services/shapers/impl/` |

---

## Shaper ABC

**File:** `src/core/services/shapers/shaper.py`

All shapers inherit from the abstract `Shaper` class, which defines the
lifecycle contract every implementation must follow:

```python
class Shaper(ABC):
    def __init__(self, params: dict[str, Any]) -> None:
        # Validates params is a dict, stores self.params, calls _verify_params()

    @abstractmethod
    def _verify_params(self) -> bool:
        # Subclasses validate their specific required parameters

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        # Rejects None or empty DataFrames

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        # Calls _verify_preconditions(), then returns the DataFrame
```

**Lifecycle:**

1. **Construction** -- `__init__(params)` stores the config dict and
   immediately calls `_verify_params()`. Invalid parameters raise
   `ValueError` before the shaper can be used.
2. **Execution** -- `__call__(df)` checks preconditions, then performs
   the transformation and returns a new DataFrame.
3. **Immutability** -- shapers must not mutate the input DataFrame. Most
   implementations call `.copy()` before modifying data.

### UniDfShaper (Intermediate ABC)

**File:** `src/core/services/shapers/uni_df_shaper.py`

`UniDfShaper` extends `Shaper` with a strict `isinstance(data_frame,
pd.DataFrame)` check in `__call__`. Most concrete shapers inherit from this
class. `PivotLonger` and `PivotWider` extend `Shaper` directly because they
handle their own DataFrame validation.

```
Shaper (ABC)
  +-- UniDfShaper (ABC)
  |     +-- Mean, Normalize, Sort, Transformer
  |     +-- Selector (ABC) -> ConditionSelector, ItemSelector
  |     +-- ColumnSelector, SplitApply
  +-- PivotLonger, PivotWider
```

---

## ShaperFactory

**File:** `src/core/services/shapers/factory.py`

The `ShaperFactory` maintains a class-level registry mapping string type
identifiers to shaper classes. It is the single creation point for all
shapers.

### Registry (10 registered types)

| Registry Key | Class | Display Name |
|-------------|-------|-------------|
| `"mean"` | `Mean` | Mean Calculator |
| `"columnSelector"` | `ColumnSelector` | Column Selector |
| `"conditionSelector"` | `ConditionSelector` | Filter |
| `"itemSelector"` | `ItemSelector` | Item Selector |
| `"normalize"` | `Normalize` | Normalize |
| `"pivotLonger"` | `PivotLonger` | Pivot Longer (Melt) |
| `"pivotWider"` | `PivotWider` | Pivot Wider |
| `"sort"` | `Sort` | Sort |
| `"splitApply"` | `SplitApply` | Split-Apply (Per-Axis) |
| `"transformer"` | `Transformer` | Transformer |

### Class Methods

- `create_shaper(shaper_type, params)` -- Look up the class in `_registry`
  and instantiate it. Config is shallow-copied via `dict(params)` to protect
  the original. Raises `ValueError` for unknown types.
- `register(shaper_type, shaper_class)` -- Add a new type at runtime.
- `get_available_types()` -- Return all registered type identifiers.
- `get_display_name_map()` -- Return `{display_name: type_id}` for UI
  dropdowns.
- `get_display_name(shaper_type)` -- Return the human-readable name.

---

## Shaper Type Catalog

| Type | Key | Category | Effect |
|------|-----|----------|--------|
| Column Selector | `columnSelector` | Selection | Keeps listed columns, drops the rest |
| Item Selector | `itemSelector` | Filtering | Keeps rows matching a value list |
| Condition Selector | `conditionSelector` | Filtering | Keeps rows matching numeric/categorical conditions |
| Sort | `sort` | Ordering | Reorders rows by user-defined category order |
| Mean | `mean` | Aggregation | Appends arithmetic/geometric/harmonic mean rows |
| Normalize | `normalize` | Scaling | Divides metric columns by a baseline reference |
| Pivot Longer | `pivotLonger` | Reshape | Wide to long (unpivot/melt) |
| Pivot Wider | `pivotWider` | Reshape | Long to wide (pivot table) |
| Split-Apply | `splitApply` | Composite | Splits columns into groups, applies sub-pipelines, merges |
| Transformer | `transformer` | Conversion | Converts column dtype (scalar/factor) |

---

## Pipeline Execution

### PipelineService.process\_pipeline()

**File:** `src/core/services/shapers/pipeline_service.py`

Core execution method. Accepts a DataFrame and an ordered list of
`ShaperStepConfig` dicts, applies each shaper sequentially:

```python
@staticmethod
def process_pipeline(data, pipeline_config):
    current_data = data
    for i, shaper_config in enumerate(pipeline_config):
        shaper_type = shaper_config.get("type")
        if not shaper_type:
            continue
        shaper = ShaperFactory.create_shaper(shaper_type, shaper_config)
        current_data = current_data.pipe(shaper)
    return current_data
```

- **No initial copy** -- each shaper copies internally.
- **Uses `DataFrame.pipe()`** which calls `shaper.__call__(df)`.
- **Performance instrumented** -- logs elapsed time per step and total.
- **Error wrapping** -- exceptions re-raised as `ValueError` with shaper
  type context.

### Step Ordering

Steps execute in list order (index 0 first). The UI provides up/down
controls. There is no dependency resolution or automatic reordering.

### Web-Layer Execution

`apply_shapers()` in `src/web/pages/ui/shaper_config.py` adds an initial
`data.copy()`, pre-validates each step with `validate_shaper_config()`,
skips incomplete configs with a warning, and surfaces errors via
`st.error()`.

---

## ShaperStepConfig and PipelineStep Models

**File:** `src/core/models/shaper_models.py`

### BaseShaperConfig

```python
class BaseShaperConfig(TypedDict, total=False):
    type: Required[str]   # Factory registry key (discriminator)
    id: int               # Pipeline step ID for ordering
```

### ShaperStepConfig (Discriminated Union)

`ShaperStepConfig` is a `Union` of all 10 per-type config TypedDicts,
discriminated by the `"type"` field.

### PipelineStep (Nested Format)

**File:** `src/core/models/data_models.py`

When stored inside a plot, pipeline steps use a nested wrapper:

```python
class PipelineStep(TypedDict):
    id: int                    # Unique step identifier
    type: str                  # Shaper type (factory key)
    config: ShaperStepConfig   # Shaper-specific parameters
```

### PipelineData (Persistence Format)

Saved pipelines are serialized to JSON:

```python
class PipelineData(TypedDict, total=False):
    name: Required[str]
    description: str
    pipeline: Required[list[PipelineStep]]
    timestamp: str
```

---

## Per-Shaper Documentation

### ColumnSelector

**File:** `src/core/services/shapers/impl/selector_algorithms/column_selector.py`

Retains only specified columns. **Required:** `columns` (`list[str]`).
Transform: `data_frame[self.columns]`. Raises `ValueError` if any column
does not exist.

### ItemSelector

**File:** `src/core/services/shapers/impl/selector_algorithms/item_selector.py`

Filters rows where a column's values match a string list. **Required:**
`column` (`str`), `strings` (`list[str]`). **Optional:** `mode` --
`"exact"` (default, uses `isin()`) or `"contains"` (uses
`str.contains()`).

### ConditionSelector

**File:** `src/core/services/shapers/impl/selector_algorithms/condition_selector.py`

Filters rows using numeric or categorical conditions. **Required:** `column`,
`mode`. **Conditional:** `threshold` (for `greater_than`/`less_than`),
`range` (`[min, max]`), `values` (categorical list).

Modes evaluated in priority order: `values`, `range`, `greater_than`,
`less_than`, `equals`, `contains`. A legacy operator/value pair is also
supported.

### Sort

**File:** `src/core/services/shapers/impl/sort.py`

Reorders rows by custom categorical orderings. **Required:** `order_dict`
(`dict[str, list[str]]` -- column name to ordered value list).

Columns are temporarily cast to `pd.Categorical(ordered=True)`, sorted
with `kind="stable"`, then converted back to `str`. Values not in the
order list sort after all specified values.

### Normalize

**File:** `src/core/services/shapers/impl/normalize.py`

Divides metric columns by a baseline reference within each group.
**Required:** `normalizeVars` (`list[str]`), `normalizerColumn` (`str`),
`normalizerValue` (`str`), `groupBy` (`list[str]`). **Optional:**
`normalizerVars` (defaults to `normalizeVars`), `normalizeSd` (defaults
to `True`).

For each group, finds the baseline row, computes the denominator, and
divides all rows' metrics. Division by zero produces `0.0`. Uses
`@cached(ttl=300, maxsize=32)` with MD5 fingerprinting.

### Mean

**File:** `src/core/services/shapers/impl/mean.py`

Calculates group means and **appends** summary rows. **Required:**
`meanVars` (`list[str]`), `meanAlgorithm` (`"arithmean"`, `"geomean"`,
or `"hmean"`), `groupingColumns` (`list[str]`), `replacingColumn` (`str`).

Groups by `groupingColumns`, aggregates `meanVars`, labels new rows in
`replacingColumn` with the algorithm name. Helper functions `_safe_gmean()`
and `_safe_hmean()` handle NaN and non-positive inputs. Uses
`@cached(ttl=300, maxsize=16)`.

### PivotLonger

**File:** `src/core/services/shapers/impl/pivot.py`

Wide to long transformation (unpivot/melt). **Required:** `id_vars`,
`value_vars`, `var_name`, `value_name`. **Optional:** `extract_pattern`
(regex with capture groups), `extract_group_indices` (1-based),
`extract_separator`, `selection_filters`, `selection_strategy`
(`"discard"`/`"merge"`), `merge_label`.

Calls `pd.melt()`, then optionally applies regex extraction to decompose
column names into structured components with per-group filtering.

### PivotWider

**File:** `src/core/services/shapers/impl/pivot.py`

Long to wide transformation. **Required:** `index` (`list[str]`),
`columns` (`str`), `values` (`str`).

Calls `pivot_table(aggfunc="first")` followed by `reset_index()`. Using
`aggfunc="first"` handles duplicate key combinations gracefully.

### SplitApply

**File:** `src/core/services/shapers/impl/split_apply.py`

Splits a DataFrame into independent column groups, applies a separate
sub-pipeline to each, then merges results on shared join columns. Designed
for dual-axis plots where each axis needs its own transformations.

**Required:** `joinColumns` (`list[str]`), `groups`
(`list[SplitApplyGroupConfig]`). Each group has `columns` (`list[str]`)
and `pipeline` (`list[ShaperStepConfig]`).

Constraints: 2--4 groups, no column overlap, auto-includes `.sd` columns.

### Transformer

**File:** `src/core/services/shapers/impl/transformer.py`

Converts a column's dtype. **Required:** `column` (`str`), `target_type`
(`"scalar"` or `"factor"`). **Optional:** `order` (`list[str]`).

Scalar: `pd.to_numeric(errors="coerce")`. Factor: `astype(str)` then
optionally `pd.Categorical(categories=order, ordered=True)`.

---

## Pipeline Validation Rules

**File:** `src/core/services/shapers/validation.py`

Before instantiation, `validate_shaper_config()` checks that all required
parameters are present and non-empty. Required fields per type:

| Shaper Type | Required Parameters |
|-------------|-------------------|
| `mean` | `groupingColumns`, `meanVars` |
| `normalize` | `normalizeVars`, `normalizerColumn`, `normalizerValue`, `groupBy` |
| `pivotLonger` | `id_vars`, `value_vars`, `var_name`, `value_name` |
| `pivotWider` | `index`, `columns`, `values` |
| `sort` | `order_dict` |
| `splitApply` | `joinColumns`, `groups` |
| `columnSelector` | `columns` |
| `conditionSelector` | `column` |
| `itemSelector` | `column`, `strings` |
| `transformer` | `column` |

Returns `(is_valid, missing_fields)`. A field is missing if absent, an empty
string, or an empty list. The web layer uses this to skip incomplete steps
with a warning rather than crashing.

Note that `conditionSelector` and `transformer` only universally require
`column`; additional requirements depend on the selected mode and are
validated within the shaper's own `_verify_params()`.

---

## See Also

- **Adding a New Shaper** -- Six-step process: create a config TypedDict in
  `shaper_models.py`, implement the class in `impl/`, register in
  `factory.py`, add validation in `validation.py`, build the UI component,
  and register in the UI dispatcher at `shaper_config.py`.
- **State Management** -- Pipeline steps are stored in Streamlit session state
  per plot. See `src/core/services/state/`.
- **Plotting System** -- Shaper output feeds directly into the plotting
  pipeline.
- **Performance Caching** -- `Mean` and `Normalize` use `@cached` with
  `compute_data_fingerprint()` from `src/core/performance/`.
- **Portfolio System** -- Saved pipeline configurations can be stored and
  restored as part of portfolio presets.
