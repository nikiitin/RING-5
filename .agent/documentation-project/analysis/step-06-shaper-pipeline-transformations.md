# Step 06 — Shaper Pipeline & Transformations Analysis

> **Objective**: Document the complete shaper pipeline architecture, every shaper
> implementation, the factory/registry pattern, and data transformation flow.

---

## 1. Executive Summary

The RING-5 Unified Engine v2 shaper system is a **pluggable, composable data
transformation pipeline** built on the Strategy and Factory design patterns. It
allows users to construct ordered sequences of DataFrame transformations --
filtering, sorting, normalizing, aggregating, pivoting, and type-converting --
through a Streamlit UI, then execute those transformations against parsed
simulation data before plotting.

**Key architectural facts:**

- **10 registered shaper types** in the factory: `mean`, `columnSelector`,
  `conditionSelector`, `itemSelector`, `normalize`, `pivotLonger`, `pivotWider`,
  `sort`, `splitApply`, `transformer`.
- **3-tier class hierarchy**: `Shaper` (ABC) -> `UniDfShaper` -> concrete
  implementations; pivot shapers extend `Shaper` directly.
- **Discriminated union config model**: 10 TypedDict subtypes of
  `BaseShaperConfig`, unified as `ShaperStepConfig`.
- **Two execution paths**: (1) `PipelineService.process_pipeline()` for
  core-layer batch execution; (2) `shaper_config.apply_shapers()` for
  web-layer execution with UI error reporting.
- **Fingerprint-based caching** on computationally expensive shapers (Mean,
  Normalize) via `@cached` decorator and `compute_data_fingerprint()`.
- **Validation layer** in `validation.py` with per-type required-parameter
  checks, invoked before shaper instantiation.

---

## 2. Shaper Architecture Overview

```
UI (Layer C)                 Core (Layer B)                      Shaper Impl
+---------------------+      +--------------------+             +------------------+
| PipelineComponent   |      | ShapersAPI         |             | Mean             |
| ShaperConfig UIs    |----->| (Protocol)         |             | Normalize        |
| (mean_config.py,    |      |   - process_pipeline             | Sort             |
|  sort_config.py,    |      |   - create_shaper  |             | ColumnSelector   |
|  normalize_config,  |      |   - list/save/load |             | ConditionSelector|
|  pivot_config, ...) |      +--------+-----------+             | ItemSelector     |
+---------------------+               |                         | PivotLonger      |
       |                               |                         | PivotWider       |
       |  ShaperStepConfig (dict)      v                         | SplitApply       |
       +----------------------> DefaultShapersAPI                | Transformer      |
                                       |                         +------------------+
                                       |  delegates to                    ^
                                       v                                  |
                                PipelineService                           |
                                  .process_pipeline()                     |
                                       |                                  |
                                       v                                  |
                                ShaperFactory.create_shaper(type, cfg) ---+
                                       |
                                       v
                                shaper(data_frame: pd.DataFrame)
                                       |
                                       v
                                Transformed DataFrame
```

**Pipeline execution model (simplified):**

1. UI creates a `list[ShaperStepConfig]` (each dict has `"type"` discriminator).
2. For each step, `ShaperFactory.create_shaper(type, config)` looks up the
   class in `_registry` and instantiates it.
3. The shaper's `__call__(df)` validates preconditions and transforms the
   DataFrame.
4. The output DataFrame is piped into the next shaper.
5. The final DataFrame is returned for plotting.

---

## 3. File Inventory

### 3.1 Shaper Framework

| File | Classes / Functions | Purpose |
|------|-------------------|---------|
| `src/core/services/shapers/__init__.py` | Re-exports `ShapersAPI`, `DefaultShapersAPI`, `PipelineService`, `ShaperFactory`, `Shaper` | Package public API |
| `src/core/services/shapers/shaper.py` | `Shaper` (ABC) | Abstract base class for all shapers |
| `src/core/services/shapers/uni_df_shaper.py` | `UniDfShaper` | Intermediate ABC adding DataFrame type-check |
| `src/core/services/shapers/factory.py` | `ShaperFactory` | Factory + registry for shaper instantiation |
| `src/core/services/shapers/pipeline_service.py` | `PipelineService` | Pipeline CRUD (save/load/delete) + `process_pipeline()` execution |
| `src/core/services/shapers/shapers_api.py` | `ShapersAPI` (Protocol) | Protocol defining the shapers interface contract |
| `src/core/services/shapers/shapers_impl.py` | `DefaultShapersAPI` | Default implementation delegating to `PipelineService` + `ShaperFactory` |
| `src/core/services/shapers/validation.py` | `validate_shaper_config()`, `get_required_params()` | Pre-flight config validation |

### 3.2 Shaper Implementations

| File | Classes | Purpose |
|------|---------|---------|
| `src/core/services/shapers/impl/mean.py` | `Mean`, `_safe_gmean()`, `_safe_hmean()` | Arithmetic/geometric/harmonic mean aggregation |
| `src/core/services/shapers/impl/normalize.py` | `Normalize` | Baseline normalization (divide by reference row) |
| `src/core/services/shapers/impl/sort.py` | `Sort` | Custom categorical column ordering |
| `src/core/services/shapers/impl/transformer.py` | `Transformer` | Type conversion (scalar/factor) |
| `src/core/services/shapers/impl/pivot.py` | `PivotLonger`, `PivotWider`, `extract_with_pattern()` | Wide-to-long and long-to-wide reshaping |
| `src/core/services/shapers/impl/selector.py` | `Selector` (abstract) | Base class for all selector/filter shapers |
| `src/core/services/shapers/impl/split_apply.py` | `SplitApply` | Split-apply-combine with sub-pipelines |

### 3.3 Selector Algorithms

| File | Classes | Purpose |
|------|---------|---------|
| `src/core/services/shapers/impl/selector_algorithms/column_selector.py` | `ColumnSelector` | Keep only specified columns |
| `src/core/services/shapers/impl/selector_algorithms/condition_selector.py` | `ConditionSelector` | Row filtering by numeric/categorical conditions |
| `src/core/services/shapers/impl/selector_algorithms/item_selector.py` | `ItemSelector` | Row filtering by value membership |

### 3.4 Configuration Models

| File | Types | Purpose |
|------|-------|---------|
| `src/core/models/shaper_models.py` | `BaseShaperConfig`, `MeanShaperConfig`, `NormalizeShaperConfig`, `SortShaperConfig`, `SplitApplyShaperConfig`, `SplitApplyGroupConfig`, `TransformerShaperConfig`, `ColumnSelectorConfig`, `ConditionSelectorConfig`, `ItemSelectorConfig`, `PivotLongerShaperConfig`, `PivotWiderShaperConfig`, `ShaperStepConfig` (union) | TypedDict configs for every shaper type |
| `src/core/models/data_models.py` | `PipelineStep`, `PipelineData` (+ re-exports all shaper models) | Pipeline persistence types, re-export bridge |

### 3.5 Web Layer (UI)

| File | Classes | Purpose |
|------|---------|---------|
| `src/web/pages/ui/shaper_config.py` | `configure_shaper()`, `apply_shapers()` | Shaper config orchestrator + web-layer pipeline runner |
| `src/web/components/shapers/mean_config.py` | `MeanConfig` | Mean shaper config UI |
| `src/web/components/shapers/normalize_config.py` | `NormalizeConfig` | Normalize shaper config UI |
| `src/web/components/shapers/sort_config.py` | `SortConfig` | Sort shaper config UI |
| `src/web/components/shapers/pivot_config.py` | `PivotLongerConfig`, `PivotWiderConfig` | Pivot shaper config UIs |
| `src/web/components/shapers/selector_transformer_configs.py` | `ColumnSelectorConfig`, `ConditionSelectorConfig`, `TransformerConfig` | Selector and transformer config UIs |
| `src/web/components/shapers/split_apply_config.py` | `SplitApplyConfig` | SplitApply composite shaper config UI |
| `src/web/components/common/pipeline.py` | `PipelineComponent` | Pipeline editor UI (add/reorder/delete/finalize) |

---

## 4. Shaper ABC (Base Class)

**File:** `src/core/services/shapers/shaper.py`

```python
class Shaper(ABC):
    """Abstract base class for all data shapers."""

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Validates params is a dict, stores it as self.params,
        then calls self._verify_params().
        Raises ValueError if params is not a dict.
        """

    @abstractmethod
    def _verify_params(self) -> bool:
        """
        Abstract. Verify initialization parameters are valid.
        Base implementation checks self.params is not None.
        Returns True if valid; raises ValueError otherwise.
        """

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """
        Verify DataFrame is not None and not empty.
        Returns True if valid; raises ValueError otherwise.
        """

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Entry point for transformation. Calls _verify_preconditions(),
        then returns data_frame (subclasses override to transform).
        """
```

**Lifecycle contract:**

1. `__init__(params)` -> stores params, calls `_verify_params()`
2. `__call__(df)` -> calls `_verify_preconditions(df)`, returns transformed df
3. Immutability: shapers must not mutate the input DataFrame (enforced by convention; most call `.copy()`)

### 4.1 UniDfShaper (Intermediate ABC)

**File:** `src/core/services/shapers/uni_df_shaper.py`

```python
class UniDfShaper(Shaper):
    """ABC for shapers operating on a single DataFrame."""

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Adds isinstance(data_frame, pd.DataFrame) check.
        Raises ValueError if None or not a DataFrame.
        Then delegates to super().__call__().
        """
```

**Inheritance tree:**

```
Shaper (ABC)
 +-- UniDfShaper (ABC)
 |    +-- Mean
 |    +-- Normalize
 |    +-- Sort
 |    +-- Transformer
 |    +-- Selector (ABC)
 |    |    +-- ConditionSelector
 |    |    +-- ItemSelector
 |    +-- ColumnSelector
 |    +-- SplitApply
 +-- PivotLonger
 +-- PivotWider
```

`PivotLonger` and `PivotWider` extend `Shaper` directly (not `UniDfShaper`)
because they handle their own DataFrame validation within `__call__`.

---

## 5. ShaperFactory & Registry

**File:** `src/core/services/shapers/factory.py`

### 5.1 Registry

```python
class ShaperFactory:
    _registry: dict[str, type[Shaper]] = {
        "mean":              Mean,
        "columnSelector":    ColumnSelector,
        "conditionSelector": ConditionSelector,
        "itemSelector":      ItemSelector,
        "normalize":         Normalize,
        "pivotLonger":       PivotLonger,
        "pivotWider":        PivotWider,
        "sort":              Sort,
        "splitApply":        SplitApply,
        "transformer":       Transformer,
    }

    _display_names: dict[str, str] = {
        "columnSelector":    "Column Selector",
        "sort":              "Sort",
        "mean":              "Mean Calculator",
        "normalize":         "Normalize",
        "pivotLonger":       "Pivot Longer (Melt)",
        "pivotWider":        "Pivot Wider",
        "conditionSelector": "Filter",
        "itemSelector":      "Item Selector",
        "splitApply":        "Split-Apply (Per-Axis)",
        "transformer":       "Transformer",
    }
```

### 5.2 Class Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `register` | `(cls, shaper_type: str, shaper_class: type[Shaper]) -> None` | Add a new shaper type to `_registry` at runtime |
| `get_available_types` | `(cls) -> list[str]` | Return list of all registered type identifiers |
| `get_display_name_map` | `(cls) -> dict[str, str]` | Return `{display_name: type_id}` mapping for UI dropdowns |
| `get_display_name` | `(cls, shaper_type: str) -> str` | Return human-readable name for a single type |
| `create_shaper` | `(cls, shaper_type: str, params: ShaperStepConfig) -> Shaper` | Instantiate a shaper; raises `ValueError` if type unknown |

### 5.3 Instantiation Flow

```python
# ShaperFactory.create_shaper("mean", config)
shaper_class = cls._registry.get("mean")          # -> Mean
if shaper_class is None: raise ValueError(...)
return shaper_class(dict(params))                  # -> Mean({"meanVars": [...], ...})
```

Key detail: `dict(params)` creates a shallow copy of the TypedDict, ensuring
the original config is not mutated by the shaper constructor.

---

## 6. Shaper Implementations -- Detailed Catalog

### 6.1 ColumnSelector

**File:** `src/core/services/shapers/impl/selector_algorithms/column_selector.py`
**Registry key:** `"columnSelector"` | **Display name:** `"Column Selector"`
**Extends:** `UniDfShaper` (directly, not via `Selector`)

**Purpose:** Subsets a DataFrame to keep only specified columns.

**Config TypedDict:** `ColumnSelectorConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"columnSelector"` |
| `id` | `int` | No | Pipeline step ID |
| `columns` | `list[str]` | Yes | Column names to retain |

**Key methods:**

```python
def __init__(self, params: dict[str, Any]) -> None:
    # Extracts self.columns from config["columns"]

def _verify_params(self) -> bool:
    # Checks "columns" is present, is a list, all elements are non-empty strings

def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
    # Checks all requested columns exist in data_frame.columns

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # Returns data_frame[self.columns] (no copy needed -- bracket indexing creates a view/copy)
```

**Transform logic:** `return data_frame[self.columns]`

---

### 6.2 ItemSelector

**File:** `src/core/services/shapers/impl/selector_algorithms/item_selector.py`
**Registry key:** `"itemSelector"` | **Display name:** `"Item Selector"`
**Extends:** `Selector` -> `UniDfShaper`

**Purpose:** Filters rows where a column's values match a list of strings
(exact match or substring).

**Config TypedDict:** `ItemSelectorConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"itemSelector"` |
| `id` | `int` | No | Pipeline step ID |
| `column` | `str` | Yes | Column to match against |
| `strings` | `list[str]` | Yes | Values to keep |
| `mode` | `str` | No | `"exact"` (default) or `"contains"` |

**Key methods:**

```python
def __init__(self, params: dict[str, Any]) -> None:
    # Extracts self.strings (cast all to str), self.mode (default "exact")
    # Calls super().__init__() which sets self.column via Selector

def _verify_params(self) -> bool:
    # Checks "strings" present and is a list

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # mode == "exact": data_frame[col].astype(str).isin(self.strings)
    # mode == "contains": data_frame[col].astype(str).str.contains(pattern)
    # Logs warning if result is empty
```

**Transform logic:**
- **Exact mode:** `data_frame[data_frame[col].astype(str).isin(self.strings)]`
- **Contains mode:** `data_frame[data_frame[col].astype(str).str.contains("|".join(strings))]`

---

### 6.3 ConditionSelector

**File:** `src/core/services/shapers/impl/selector_algorithms/condition_selector.py`
**Registry key:** `"conditionSelector"` | **Display name:** `"Filter"`
**Extends:** `Selector` -> `UniDfShaper`

**Purpose:** Filters rows based on numeric or categorical conditions.
Most flexible selector with 6 filter modes.

**Config TypedDict:** `ConditionSelectorConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"conditionSelector"` |
| `id` | `int` | No | Pipeline step ID |
| `column` | `str` | Yes | Column to filter on |
| `mode` | `str` | Yes | Filter mode (see below) |
| `threshold` | `float` | Conditional | For `"greater_than"` / `"less_than"` modes |
| `range` | `list[float]` | Conditional | `[min, max]` for `"range"` mode |
| `values` | `list[str]` | Conditional | Allowed values for categorical mode |

**Supported modes (priority order in `__call__`):**

1. **Categorical inclusion** (`values` is set): `df[col].isin(values)`
2. **Numeric range** (`range` is set): `df[col] >= min & df[col] <= max`
3. **greater_than**: `df[col] > threshold`
4. **less_than**: `df[col] < threshold`
5. **equals**: `df[col] == value`
6. **contains**: `df[col].astype(str).str.contains(value)`
7. **Legacy operator/value pair**: `condition` in `["<", ">", "<=", ">=", "==", "!="]` with `value`

**Key methods:**

```python
def __init__(self, params: dict[str, Any]) -> None:
    # Extracts: self.mode, self.condition, self.value, self.threshold,
    #           self.range, self.values
    # All optional fields with defaults; calls Selector.__init__()

def _verify_params(self) -> bool:
    # Validates based on mode: ensures threshold/range/value/values
    # are present for their respective modes. Validates legacy operator.

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # Falls through priority chain (values -> range -> mode match -> legacy)
    # Returns filtered DataFrame
```

---

### 6.4 Sort

**File:** `src/core/services/shapers/impl/sort.py`
**Registry key:** `"sort"` | **Display name:** `"Sort"`
**Extends:** `UniDfShaper`

**Purpose:** Reorders DataFrame rows by applying custom categorical orderings
to one or more columns. Uses pandas `CategoricalDtype` for stable sorting.

**Config TypedDict:** `SortShaperConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"sort"` |
| `id` | `int` | No | Pipeline step ID |
| `order_dict` | `dict[str, list[str]]` | Yes | Column name -> ordered list of category values |

**Key methods:**

```python
def __init__(self, params: dict[str, Any]) -> None:
    # Extracts self.order_dict from config

def _verify_params(self) -> bool:
    # Checks order_dict is a dict, keys are strings, values are lists

def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
    # All order_dict keys must exist in data_frame.columns

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # 1. result = data_frame.copy()
    # 2. For each column, convert to pd.Categorical with specified order
    # 3. result.sort_values(by=list(order_dict.keys()), kind="stable")
    # 4. Convert categoricals back to str (prevents downstream issues)
    # 5. Return result
```

**Transform logic summary:**
- Columns are temporarily converted to `pd.Categorical(ordered=True)` with
  the user-specified category order.
- Sorting uses `kind="stable"` to preserve relative order for equal categories.
- After sorting, columns are converted back to `str` dtype.
- Values not in the specified order list sort after all specified values.

---

### 6.5 Normalize

**File:** `src/core/services/shapers/impl/normalize.py`
**Registry key:** `"normalize"` | **Display name:** `"Normalize"`
**Extends:** `UniDfShaper`

**Purpose:** Divides metric columns by a baseline reference value within each
group, producing relative performance numbers (e.g., speedup over baseline).

**Config TypedDict:** `NormalizeShaperConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"normalize"` |
| `id` | `int` | No | Pipeline step ID |
| `normalizeVars` | `list[str]` | Yes | Columns to normalize (numerator metrics) |
| `normalizerColumn` | `str` | Yes | Column containing the reference category (e.g., `"config"`) |
| `normalizerValue` | `str` | Yes | The specific baseline value (e.g., `"baseline"`) |
| `groupBy` | `list[str]` | Yes | Columns defining normalization groups (e.g., `["benchmark"]`) |
| `normalizerVars` | `list[str]` | No | Columns summed for the denominator; defaults to `normalizeVars` |
| `normalizeSd` | `bool` | No | Whether to also normalize `.sd` columns; defaults to `True` |

**Key methods:**

```python
def __init__(self, params: dict[str, Any]) -> None:
    # Extracts: _normalize_vars, _normalizer_column, _normalizer_value,
    #           _group_by, _normalizer_vars, _normalize_sd
    # Also stores _params for fingerprinting

def _verify_params(self) -> bool:
    # Checks all 4 required keys present in config

def _validate_init_types(self) -> None:
    # Type-checks: lists are lists, str is str, bool is bool

def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
    # 1. All numeric columns exist and are numeric dtype
    # 2. normalizerColumn exists
    # 3. normalizerValue exists in the column's unique values
    # 4. Each group has exactly 1 baseline row

def _normalize_group(self, group: pd.DataFrame) -> pd.DataFrame:
    # 1. Find baseline row where normalizerColumn == normalizerValue
    # 2. Compute denominator = sum of baseline[normalizerVars]
    # 3. For each normalizeVar: result[var] = result[var] / denominator
    # 4. If normalizeSd: also normalize .sd columns
    # 5. Handle division by zero (set to 0.0)

@cached(ttl=300, maxsize=32, key_func=lambda self, df, fp: fp)
def _normalize_with_cache(self, data_frame, fingerprint) -> pd.DataFrame:
    # Applies _normalize_group via groupby().apply()

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # 1. _verify_preconditions()
    # 2. Compute fingerprint via compute_data_fingerprint()
    # 3. Call _normalize_with_cache() (cache-aside pattern)
```

**Caching:** Uses `@cached(ttl=300, maxsize=32)` with an MD5 fingerprint of
the relevant columns and params as the cache key.

---

### 6.6 Mean

**File:** `src/core/services/shapers/impl/mean.py`
**Registry key:** `"mean"` | **Display name:** `"Mean Calculator"`
**Extends:** `UniDfShaper`

**Purpose:** Calculates group means (arithmetic, geometric, or harmonic) for
selected numeric variables and **appends** summary rows to the DataFrame.

**Config TypedDict:** `MeanShaperConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"mean"` |
| `id` | `int` | No | Pipeline step ID |
| `meanVars` | `list[str]` | Yes | Columns to aggregate |
| `meanAlgorithm` | `str` | Yes | `"arithmean"`, `"geomean"`, or `"hmean"` |
| `groupingColumns` | `list[str]` | Yes | Columns defining groups |
| `replacingColumn` | `str` | Yes | Column where the mean label is stored in new rows |

**Helper functions:**

```python
def _safe_gmean(series: pd.Series) -> float:
    """Geometric mean that skips NaN and handles non-positive values."""
    # Returns np.nan if series has non-positive values or is empty

def _safe_hmean(series: pd.Series) -> float:
    """Harmonic mean that skips NaN and handles non-positive values."""
    # Returns np.nan if series has non-positive values or is empty
```

**Key methods:**

```python
def __init__(self, params: dict[str, Any]) -> None:
    # Extracts: mean_vars, mean_algorithm, replacing_column, grouping_columns
    # Supports legacy "groupingColumn" (singular) config key

def _verify_params(self) -> bool:
    # meanAlgorithm must be in ["arithmean", "geomean", "hmean"]
    # meanVars must be a list

def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
    # All required columns exist; mean_vars columns are numeric

@cached(ttl=300, maxsize=16, key_func=lambda self, df, fp: fp)
def _calculate_mean_with_cache(self, data_frame, fingerprint) -> pd.DataFrame:
    # 1. result = data_frame.copy()
    # 2. grouped = result.groupby(grouping_columns)
    # 3. Apply appropriate aggregation:
    #    - arithmean: grouped[mean_vars].mean()
    #    - geomean:   grouped[mean_vars].agg(_safe_gmean)
    #    - hmean:     grouped[mean_vars].agg(_safe_hmean)
    # 4. Label new rows: mean_df[replacing_column] = mean_algorithm
    # 5. Carry over other columns (first value in each group)
    # 6. pd.concat([result, mean_df]) -- appends mean rows

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # 1. _verify_preconditions()
    # 2. Compute fingerprint
    # 3. Call _calculate_mean_with_cache()
```

**Output behavior:** The Mean shaper does NOT replace data -- it **appends**
new rows. For example, with `meanAlgorithm="geomean"`, a new row with
`benchmark="geomean"` is appended for each group.

**Caching:** Uses `@cached(ttl=300, maxsize=16)` with fingerprint keying.

---

### 6.7 SplitApply

**File:** `src/core/services/shapers/impl/split_apply.py`
**Registry key:** `"splitApply"` | **Display name:** `"Split-Apply (Per-Axis)"`
**Extends:** `UniDfShaper`

**Purpose:** Splits a DataFrame into independent column groups, applies a
separate sub-pipeline to each group, then merges results back on shared join
columns. Designed for dual-axis plots where each axis variable needs its own
Mean/Normalize transformations without cross-contamination.

**Config TypedDict:** `SplitApplyShaperConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"splitApply"` |
| `id` | `int` | No | Pipeline step ID |
| `joinColumns` | `list[str]` | Yes | Categorical columns shared across groups (used for merging) |
| `groups` | `list[SplitApplyGroupConfig]` | Yes | 2-4 group definitions |

**`SplitApplyGroupConfig`:**

| Field | Type | Description |
|-------|------|-------------|
| `columns` | `list[str]` | Numeric columns for this group |
| `pipeline` | `list[ShaperStepConfig]` | Sub-pipeline to apply to this group |

**Key methods:**

```python
def __init__(self, params: dict[str, Any]) -> None:
    # Extracts: _join_columns, _groups

def _verify_params(self) -> bool:
    # joinColumns must be non-empty list
    # groups must contain 2-4 groups
    # Each group must have non-empty columns list
    # No overlapping columns across groups

def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
    # All join columns and group columns must exist in DataFrame

@staticmethod
def _apply_sub_pipeline(data, pipeline) -> pd.DataFrame:
    # Iterates pipeline configs, creates shapers via ShaperFactory,
    # applies sequentially. Uses late import to avoid circular deps.

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # 1. For each group:
    #    a. select_cols = join_columns + group.columns + matching .sd columns
    #    b. slice_df = data_frame[select_cols].copy()
    #    c. Apply sub-pipeline to slice_df
    # 2. Merge all group results:
    #    a. Start with first group result
    #    b. Outer-join subsequent groups on join_columns
    # 3. Return merged DataFrame
```

**Important constraints:**
- Minimum 2 groups, maximum 4 groups
- No column overlap between groups (each numeric column belongs to exactly one group)
- Automatically includes `.sd` columns matching group columns
- Sub-pipeline errors propagate with group context information

---

### 6.8 Transformer

**File:** `src/core/services/shapers/impl/transformer.py`
**Registry key:** `"transformer"` | **Display name:** `"Transformer"`
**Extends:** `UniDfShaper`

**Purpose:** Converts a column's data type between scalar (numeric) and
factor (categorical), optionally applying a custom categorical ordering.

**Config TypedDict:** `TransformerShaperConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"transformer"` |
| `id` | `int` | No | Pipeline step ID |
| `column` | `str` | Yes | Target column to transform |
| `target_type` | `str` | Yes | `"scalar"` or `"factor"` |
| `order` | `list[str] \| None` | No | Explicit category ordering (for factor type) |

**Key methods:**

```python
def __init__(self, params: dict[str, Any]) -> None:
    # Extracts: self.column, self.target_type, self.order

def _verify_params(self) -> bool:
    # column must be non-empty string
    # target_type must be "scalar" or "factor"

def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
    # Column must exist in data_frame

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # df = data_frame.copy()
    # if target_type == "factor":
    #     df[col] = df[col].astype(str)
    #     if self.order: apply pd.Categorical with ordered categories
    # elif target_type == "scalar":
    #     df[col] = pd.to_numeric(df[col], errors="coerce")
    # return df
```

**Type conversion rules:**
- `"scalar"`: `pd.to_numeric(errors="coerce")` -- non-convertible values become `NaN`
- `"factor"`: `astype(str)` then optionally `pd.Categorical(categories=order, ordered=True)`

---

### 6.9 PivotLonger

**File:** `src/core/services/shapers/impl/pivot.py`
**Registry key:** `"pivotLonger"` | **Display name:** `"Pivot Longer (Melt)"`
**Extends:** `Shaper` (directly)

**Purpose:** Transforms data from wide format to long format (unpivot/melt).
Optionally applies regex-based extraction to transform column names into
structured variable values.

**Config TypedDict:** `PivotLongerShaperConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"pivotLonger"` |
| `id` | `int` | No | Pipeline step ID |
| `id_vars` | `list[str]` | Yes | Identifier columns to keep as-is |
| `value_vars` | `list[str]` | Yes | Columns to unpivot |
| `var_name` | `str` | Yes | Name for the new variable column |
| `value_name` | `str` | Yes | Name for the new value column |
| `extract_pattern` | `str` | No | Regex with capture groups for column name extraction |
| `extract_group_indices` | `list[int]` | No | Which capture groups to keep (1-based); default `[1]` |
| `extract_separator` | `str` | No | Separator when joining multiple groups; default `"_"` |
| `selection_filters` | `dict[int, list[str]]` | No | Per-group value filters |
| `selection_strategy` | `str` | No | `"discard"` (default) or `"merge"` for non-matching values |
| `merge_label` | `str` | No | Label for merged "other" rows; default `"other"` |

**Helper function:**

```python
def extract_with_pattern(value: str, pattern: str,
                         group_indices: list[int], separator: str = "_") -> str:
    """Extract specific capture groups from a string using a regex pattern."""
```

**Key methods:**

```python
def __init__(self, params) -> None:
    # Stores self.config as PivotLongerShaperConfig cast

def _verify_params(self) -> bool:
    # id_vars, value_vars, var_name, value_name all required

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # 1. Validate columns exist
    # 2. pd.melt(id_vars, value_vars, var_name, value_name)
    # 3. If extract_pattern provided:
    #    a. If selection_filters: Apply per-row filtering with process_row()
    #       - "discard" strategy: drop non-matching rows
    #       - "merge" strategy: aggregate non-matching rows under merge_label
    #    b. Else: Vectorized extraction via str.extract()
    #       - Keep original values where regex doesn't match
    # 4. Return result
```

**Advanced extraction pipeline:**
The PivotLonger supports a sophisticated regex extraction system where column
names like `cpu0_l1_cntrl0.hits` can be decomposed into structured components
(e.g., extracting `"0"` from `cpu(\d+)`), with per-group filtering to select
specific indices.

---

### 6.10 PivotWider

**File:** `src/core/services/shapers/impl/pivot.py`
**Registry key:** `"pivotWider"` | **Display name:** `"Pivot Wider"`
**Extends:** `Shaper` (directly)

**Purpose:** Transforms data from long format to wide format using
`pivot_table()`.

**Config TypedDict:** `PivotWiderShaperConfig`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Always `"pivotWider"` |
| `id` | `int` | No | Pipeline step ID |
| `index` | `list[str]` | Yes | Columns for the new frame's index |
| `columns` | `str` | Yes | Column whose values become new column names |
| `values` | `str` | Yes | Column whose values populate the new cells |

**Key methods:**

```python
def __init__(self, params) -> None:
    # Stores self.config as PivotWiderShaperConfig cast

def _verify_params(self) -> bool:
    # index, columns, values all required and non-empty

def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
    # 1. Validate all columns exist
    # 2. pivot_table(index, columns, values, aggfunc="first")
    # 3. reset_index() + clear columns.name
    # 4. Return result
```

**Duplicate handling:** Uses `aggfunc="first"` in `pivot_table()` to handle
duplicate `(index, columns)` combinations gracefully instead of raising an
error.

---

### 6.11 Selector (Abstract Base)

**File:** `src/core/services/shapers/impl/selector.py`
**Extends:** `UniDfShaper`
**Not directly registered** in the factory -- serves as base for
`ConditionSelector` and `ItemSelector`.

**Purpose:** Provides common `column` parameter validation for all
filtering shapers.

```python
class Selector(UniDfShaper):
    def __init__(self, params):
        super().__init__(params)
        self.column = params["column"]

    def _verify_params(self) -> bool:
        # "column" must be present and non-empty

    def _verify_preconditions(self, data_frame) -> bool:
        # self.column must exist in data_frame.columns

    def __call__(self, data_frame) -> pd.DataFrame:
        return super().__call__(data_frame)
```

---

## 7. Pipeline Execution Model

### 7.1 Data Types

**`PipelineStep`** (stored in plot state, nested format):
```python
class PipelineStep(TypedDict):
    id: int                    # Unique step identifier
    type: str                  # Shaper type (factory key)
    config: ShaperStepConfig   # Nested shaper config dict
```

**`PipelineData`** (persisted to JSON file):
```python
class PipelineData(TypedDict, total=False):
    name: Required[str]
    description: str
    pipeline: Required[list[PipelineStep]]
    timestamp: str
```

### 7.2 Core Execution: `PipelineService.process_pipeline()`

```python
@staticmethod
def process_pipeline(
    data: pd.DataFrame,
    pipeline_config: list[ShaperStepConfig],
) -> pd.DataFrame:
    """Apply a sequence of shapers to a DataFrame."""
    current_data = data  # No initial copy; shapers copy internally
    for i, shaper_config in enumerate(pipeline_config):
        shaper_type = shaper_config.get("type")
        if not shaper_type:
            continue
        try:
            shaper = ShaperFactory.create_shaper(shaper_type, shaper_config)
            current_data = current_data.pipe(shaper)  # Uses __call__
        except Exception as e:
            raise ValueError(f"Failed to apply shaper {shaper_type}: {e}") from e
    return current_data
```

**Key behaviors:**
- No initial DataFrame copy (each shaper is responsible for its own copy).
- Uses `DataFrame.pipe()` which calls `shaper.__call__(df)`.
- Performance-instrumented: logs elapsed time per step and total.
- On error: wraps in `ValueError` with shaper type context, propagates.

### 7.3 Web-Layer Execution: `apply_shapers()`

```python
def apply_shapers(
    data: pd.DataFrame | None,
    shapers_config: list[ShaperStepConfig],
) -> pd.DataFrame:
```

**Additional behaviors over core execution:**
1. Creates an initial `data.copy()` before iteration.
2. Pre-validates each step via `validate_shaper_config()` before construction.
3. Incomplete configs are **skipped with a warning** (not raised).
4. Errors are surfaced via `st.error()` / `st.warning()` / `st.exception()`.
5. Different exception types get different UI treatment:
   - `ValueError` -> "Configuration error"
   - `KeyError` -> "Data error - Missing column"
   - Other `Exception` -> "Transformation failed" + full traceback

### 7.4 Pipeline Persistence

**Save:** `PipelineService.save_pipeline(name, pipeline_config, description)`
- Sanitizes filename, validates path within pipeline dir.
- Serializes `PipelineData` to JSON.

**Load:** `PipelineService.load_pipeline(name) -> PipelineData`
- Sanitizes filename, validates path, deserializes JSON.

**Prepare loaded:** `PipelineService.prepare_loaded_pipeline(pipeline_data)`
- Deep-copies steps (isolates from stored version).
- Computes `next_counter = max(step.id) + 1` for new step IDs.
- Returns `(steps, next_counter)`.

**Delete:** `PipelineService.delete_pipeline(name)` -- removes JSON file.

**List:** `PipelineService.list_pipelines() -> list[str]` -- globs `*.json`.

---

## 8. Config-to-Shaper Mapping

The `ShaperStepConfig` discriminated union maps to shapers via the `"type"` field:

| `type` value | Config TypedDict | Shaper Class | Factory Key |
|-------------|-----------------|-------------|------------|
| `"mean"` | `MeanShaperConfig` | `Mean` | `"mean"` |
| `"normalize"` | `NormalizeShaperConfig` | `Normalize` | `"normalize"` |
| `"sort"` | `SortShaperConfig` | `Sort` | `"sort"` |
| `"columnSelector"` | `ColumnSelectorConfig` | `ColumnSelector` | `"columnSelector"` |
| `"conditionSelector"` | `ConditionSelectorConfig` | `ConditionSelector` | `"conditionSelector"` |
| `"itemSelector"` | `ItemSelectorConfig` | `ItemSelector` | `"itemSelector"` |
| `"pivotLonger"` | `PivotLongerShaperConfig` | `PivotLonger` | `"pivotLonger"` |
| `"pivotWider"` | `PivotWiderShaperConfig` | `PivotWider` | `"pivotWider"` |
| `"splitApply"` | `SplitApplyShaperConfig` | `SplitApply` | `"splitApply"` |
| `"transformer"` | `TransformerShaperConfig` | `Transformer` | `"transformer"` |

**Union definition** (from `src/core/models/shaper_models.py`):
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

### 8.1 Validation Layer

**File:** `src/core/services/shapers/validation.py`

Required parameters per shaper type:

```python
_REQUIRED_PARAMS: dict[str, list[str]] = {
    "mean":              ["groupingColumns", "meanVars"],
    "normalize":         ["normalizeVars", "normalizerColumn", "normalizerValue", "groupBy"],
    "pivotLonger":       ["id_vars", "value_vars", "var_name", "value_name"],
    "pivotWider":        ["index", "columns", "values"],
    "sort":              ["order_dict"],
    "splitApply":        ["joinColumns", "groups"],
    "columnSelector":    ["columns"],
    "conditionSelector": ["column"],
    "transformer":       ["column"],
    "itemSelector":      ["column", "strings"],
}
```

**Functions:**

```python
def validate_shaper_config(shaper_type: str, config: ShaperStepConfig
) -> tuple[bool, list[str] | None]:
    """Returns (is_valid, missing_fields). Checks each required param
    is present and non-empty (for strings and lists)."""

def get_required_params(shaper_type: str) -> list[str]:
    """Returns the required parameter names for a given type."""
```

---

## 9. UI Integration Points

### 9.1 Pipeline Editor (`PipelineComponent`)

**File:** `src/web/components/common/pipeline.py`

The `PipelineComponent` renders the pipeline editor UI:

- **`SHAPER_DISPLAY_MAP`**: Built from `ShaperFactory.get_display_name_map()`
  -- single source of truth. Maps display names to type identifiers:
  `{"Column Selector": "columnSelector", "Sort": "sort", ...}`
- **`render_add_shaper(plot_id)`**: Selectbox dropdown + "Add to Pipeline"
  button. Returns selected shaper type.
- **`render_shaper_controls(plot_id, idx, ...)`**: Up/Down/Delete buttons
  per step.
- **`render_finalize_button(plot_id)`**: "Finalize Pipeline for Plotting".

### 9.2 Shaper Config Orchestrator (`shaper_config.py`)

**File:** `src/web/pages/ui/shaper_config.py`

Two main functions:

**`configure_shaper(shaper_type, data, shaper_id, existing_config, owner_id)`:**
- Dispatches to the appropriate config UI component via `config_dispatch` dict.
- Each component's `render()` is called with `(data, existing_config, key_prefix, shaper_id)`.
- Returns `ShaperStepConfig` with `"type"` always set.
- On error: returns minimal `{"type": shaper_type}` to prevent UI breakage.

**Config dispatch mapping:**
```python
config_dispatch = {
    "columnSelector":    ColumnSelectorConfig.render,
    "normalize":         NormalizeConfig.render,
    "mean":              MeanConfig.render,
    "conditionSelector": ConditionSelectorConfig.render,
    "splitApply":        SplitApplyConfig.render,
    "transformer":       TransformerConfig.render,
    "sort":              SortConfig.render,
    "pivotLonger":       PivotLongerConfig.render,
    "pivotWider":        PivotWiderConfig.render,
}
```

**`apply_shapers(data, shapers_config)`:**
- Web-layer pipeline execution with validation and error display (see Section 7.3).

### 9.3 UI Config Components

Each shaper has a dedicated UI component class with a `render()` static method:

| Component | Shaper | Key UI Elements |
|-----------|--------|----------------|
| `ColumnSelectorConfig.render()` | `columnSelector` | Multiselect of column names |
| `ConditionSelectorConfig.render()` | `conditionSelector` | Column select + mode-dependent inputs (slider for range, number input for threshold, multiselect for categorical) |
| `TransformerConfig.render()` | `transformer` | Column select + segmented control (Factor/Scalar) + optional order multiselect |
| `MeanConfig.render()` | `mean` | Algorithm selectbox + variables multiselect + group-by multiselect + replacing column select |
| `NormalizeConfig.render()` | `normalize` | Normalizer vars + normalize vars + normalizer column/value + group-by + normalize SD checkbox |
| `SortConfig.render()` | `sort` | Column multiselect + per-column order multiselect (with expander for high cardinality) |
| `SplitApplyConfig.render()` | `splitApply` | Join columns multiselect + group count slider (2-4) + per-group expanders with column select + nested sub-pipeline editor |
| `PivotLongerConfig.render()` | `pivotLonger` | id_vars/value_vars multiselect + output names + advanced regex extraction with preview |
| `PivotWiderConfig.render()` | `pivotWider` | Index columns multiselect + columns-from select + values-from select |

### 9.4 SplitApply Sub-Pipeline UI

The `SplitApplyConfig` component is notable for supporting **nested sub-pipelines**.
Each group has its own mini pipeline editor that reuses the same config components
(Mean, Normalize, Sort, ConditionSelector) via lazy `_SUB_SHAPER_DISPATCH`.

Allowed inner types: `{"mean", "normalize", "sort", "conditionSelector"}`

---

## 10. Data Transformation Patterns

### 10.1 Filter Pattern (Row Reduction)
**Shapers:** `ConditionSelector`, `ItemSelector`

- Input: DataFrame with N rows
- Output: DataFrame with M rows (M <= N)
- No new columns added, no column modification
- Common use: select specific benchmarks, filter by performance threshold

### 10.2 Select Pattern (Column Reduction)
**Shaper:** `ColumnSelector`

- Input: DataFrame with C columns
- Output: DataFrame with K columns (K <= C)
- No row modification
- Common use: strip unnecessary columns before plotting

### 10.3 Sort Pattern (Row Reordering)
**Shaper:** `Sort`

- Input: DataFrame with arbitrary row order
- Output: DataFrame with user-defined categorical order
- Same rows and columns, different order
- Common use: ensure baseline config appears first in plots

### 10.4 Normalize Pattern (Value Scaling)
**Shaper:** `Normalize`

- Input: DataFrame with absolute metric values
- Output: DataFrame with values divided by baseline reference
- Same rows and columns, modified values
- Common use: speedup/slowdown relative to baseline configuration

### 10.5 Aggregate Pattern (Row Addition)
**Shaper:** `Mean`

- Input: DataFrame with N data rows
- Output: DataFrame with N + G rows (G = number of groups)
- Appended rows contain aggregated values (arithmetic/geometric/harmonic mean)
- Common use: add GEOMEAN summary row for benchmark suites

### 10.6 Reshape Pattern (Format Transformation)
**Shapers:** `PivotLonger`, `PivotWider`

- PivotLonger: Wide -> Long (fewer columns, more rows)
- PivotWider: Long -> Wide (more columns, fewer rows)
- Common use: restructure data for specific plot types

### 10.7 Type Conversion Pattern
**Shaper:** `Transformer`

- Converts between numeric (scalar) and categorical (factor) types
- Common use: ensure a numeric column is treated as categorical for grouping

### 10.8 Composite Pattern (Sub-Pipeline)
**Shaper:** `SplitApply`

- Splits data into independent column groups
- Applies separate transformation sub-pipelines per group
- Merges results back
- Common use: dual-axis plots where each axis needs different Mean/Normalize

---

## 11. Extension Points

### 11.1 How to Add a New Shaper Type

**Step 1: Create the config TypedDict** in `src/core/models/shaper_models.py`:
```python
class MyShaperConfig(BaseShaperConfig, total=False):
    my_param: Required[str]
    optional_param: int
```
Add it to the `ShaperStepConfig` union.

**Step 2: Create the shaper implementation** in
`src/core/services/shapers/impl/my_shaper.py`:
```python
class MyShaper(UniDfShaper):
    def __init__(self, params: dict[str, Any]) -> None:
        config = cast(MyShaperConfig, params)
        self.my_param = config["my_param"]
        super().__init__(params)

    def _verify_params(self) -> bool:
        super()._verify_params()
        # Validate params
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        self._verify_preconditions(data_frame)
        result = data_frame.copy()
        # Transform result
        return result
```

**Step 3: Register in the factory** -- add to `_registry` and `_display_names`
in `src/core/services/shapers/factory.py`:
```python
_registry = {
    ...,
    "myShaper": MyShaper,
}
_display_names = {
    ...,
    "myShaper": "My Shaper",
}
```

**Step 4: Add validation** -- add required params to `_REQUIRED_PARAMS` in
`src/core/services/shapers/validation.py`:
```python
_REQUIRED_PARAMS = {
    ...,
    "myShaper": ["my_param"],
}
```

**Step 5: Create the UI config component** in
`src/web/components/shapers/my_shaper_config.py`:
```python
class MyShaperConfig:
    @staticmethod
    def render(data, existing_config, key_prefix, shaper_id) -> ShaperStepConfig:
        # Streamlit widgets
        return cast(ShaperStepConfig, {"my_param": ...})
```

**Step 6: Register in the UI orchestrator** -- add to `config_dispatch` in
`src/web/pages/ui/shaper_config.py`:
```python
config_dispatch = {
    ...,
    "myShaper": MyShaperConfig.render,
}
```

### 11.2 Runtime Registration

The factory supports runtime registration via `ShaperFactory.register()`:
```python
ShaperFactory.register("myCustomShaper", MyCustomShaperClass)
```
This enables plugins or test extensions without modifying factory source.

---

## 12. Downstream Dependencies

This analysis feeds into:

- `DEVELOPER_GUIDE_PLAN.md`:
  - `data-pipeline/shaper-architecture.md` -- Sections 2, 4, 5, 7
  - `data-pipeline/shaper-implementations.md` -- Section 6 (full catalog)
  - `data-pipeline/adding-a-new-shaper.md` -- Section 11
- `AI_KNOWLEDGE_BASE_PLAN.md`:
  - `development/adding-a-shaper.md` -- Section 11
- `USER_GUIDE_PLAN.md`:
  - `data-transformations/shaper-user-guide.md` -- Sections 6, 9, 10
- Step 18 (End-to-End Data Flow): Shapers are the transformation step between
  parsing and plotting.
- Step 19 (Extension Points): `ShaperFactory` is one of the primary extension
  points in the architecture.

### 12.1 Key Integration Points with Other Subsystems

| Subsystem | Integration | Details |
|-----------|------------|---------|
| **Parser** | Input data | Shapers receive DataFrames produced by the parser subsystem |
| **Plotting** | Output data | Shaper output feeds directly into the plotting pipeline |
| **Portfolio** | Pipeline persistence | Saved configs reference pipeline steps; portfolios can store/restore pipelines |
| **State Management** | Session state | Pipeline steps stored in Streamlit session state per plot |
| **Performance** | Caching | Mean and Normalize use `@cached` + `compute_data_fingerprint()` from `src/core/performance` |
| **Services API** | Facade delegation | `DefaultServicesAPI.shapers` exposes `ShapersAPI` to the web layer |
