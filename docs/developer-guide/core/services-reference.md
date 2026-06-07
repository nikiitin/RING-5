---
title: "Core Services Reference"
parent: Core
grand_parent: Developer Guide
nav_order: 2
---

# Core Services Reference

This document catalogs every service class in the RING-5 Unified Engine v2
core layer. Each entry lists the source file, statefulness, public methods,
and key behavioral notes.

---

## 1. Overview

The service layer sits between the presentation tier (Streamlit web UI) and
the state/persistence tier. Its purpose is to encapsulate all business logic
so that the UI remains thin and the state layer remains a pure data store.

**Architectural principles:**

- **Stateless by default.** The overwhelming majority of services expose only
  `@staticmethod` or `@classmethod` methods and hold no instance state. This
  makes them safe to call from any context without lifecycle management.
- **Protocol-first design.** Every sub-API is defined as a
  `@runtime_checkable` `Protocol`, enabling alternative implementations and
  test doubles.
- **Facade + Composition Root.** `DefaultServicesAPI` is the composition root
  that wires all sub-APIs together via constructor injection.
- **Immutable operations.** Services that transform data return new objects
  (copied DataFrames, new lists) rather than mutating inputs.

**Package layout:**

```
src/core/services/
    config_validation_service.py
    portfolio_migrator.py
    services_api.py
    services_impl.py
    managers/
        managers_api.py
        managers_impl.py
        arithmetic_service.py
        outlier_service.py
        reduction_service.py
    data_services/
        data_services_api.py
        data_services_impl.py
        csv_pool_service.py
        config_service.py
        path_service.py
        variable_service.py
        portfolio_service.py
        pattern_index_service.py
    shapers/
        shapers_api.py
        shapers_impl.py
        factory.py
        pipeline_service.py
        shaper.py
        uni_df_shaper.py
        validation.py
        impl/          (concrete shaper classes)
    visualization/
        __init__.py
        config_resolver.py
        palette_service.py
        plot_interaction.py
```

---

## 2. Manager Services

Manager services perform stateless data transformations -- arithmetic between
columns, outlier removal, and multi-seed aggregation. All methods are static;
no instance state exists.

### 2.1 ArithmeticService

| | |
|---|---|
| **File** | `src/core/services/managers/arithmetic_service.py` |
| **Stateless** | Yes -- all methods are `@staticmethod` |
| **Lines** | 172 |

Performs column-based mathematical operations on DataFrames, including binary
arithmetic and multi-column merge with standard-deviation propagation.

#### Public methods

```python
@staticmethod
def list_operators() -> list[str]
```
Returns `["Division", "Sum", "Subtraction", "Multiplication"]`.

```python
@staticmethod
def apply_operation(
    df: pd.DataFrame, operation: str, src1: str, src2: str, dest: str
) -> pd.DataFrame
```
Applies a binary operation between columns `src1` and `src2`, storing the
result in column `dest`. Creates a copy of the input DataFrame. Accepted
operation aliases:

| Operation | Aliases |
|---|---|
| Division | `divide`, `/` |
| Sum | `add`, `+` |
| Subtraction | `subtract`, `minus`, `-` |
| Multiplication | `multiply`, `*` |

Division replaces zero denominators with `np.nan`. Raises `ValueError` for
unknown operations.

```python
@staticmethod
def apply_mixer(
    df: pd.DataFrame,
    dest_col: str,
    source_cols: list[str],
    operation: str = "Sum",
    separator: str = "_",
) -> pd.DataFrame
```
Merges multiple columns into a single destination column. Supported operations
are `Sum`, `Mean` / `Mean (Average)`, and `Concatenate`. For numeric
operations, automatically propagates standard deviation when `.sd` or `_stdev`
companion columns exist (sum of variances for Sum; divided by count for Mean).

```python
@staticmethod
def merge_columns(
    df: pd.DataFrame,
    columns: list[str],
    operation: str,
    new_column_name: str,
    separator: str = "_",
) -> pd.DataFrame
```
Convenience wrapper around `apply_mixer`.

```python
@staticmethod
def validate_merge_inputs(
    df: pd.DataFrame,
    columns: list[str],
    operation: str,
    new_column_name: str,
) -> list[str]
```
Returns a list of error strings (empty means valid). Checks: at least two
columns selected, columns exist, operation is valid, column name is non-empty
and does not already exist.

---

### 2.2 OutlierService

| | |
|---|---|
| **File** | `src/core/services/managers/outlier_service.py` |
| **Stateless** | Yes -- all methods are `@staticmethod` |
| **Lines** | 74 |

Detects and removes statistical outliers using the IQR (Interquartile Range)
method.

#### Public methods

```python
@staticmethod
def remove_outliers(
    df: pd.DataFrame,
    outlier_col: str,
    group_by_cols: list[str],
    multiplier: float = 1.5,
) -> pd.DataFrame
```
Removes rows where `outlier_col` falls outside
`[Q1 - multiplier*IQR, Q3 + multiplier*IQR]`. Two modes:

- **Global** (empty `group_by_cols`): IQR computed across the entire column.
- **Grouped**: IQR computed per group via `groupby().transform()`.

Default multiplier 1.5 targets mild outliers; use 3.0 for extreme outliers
only. Returns the input unchanged when the DataFrame is empty or the column
is missing.

```python
@staticmethod
def validate_outlier_inputs(
    df: pd.DataFrame, outlier_col: str, group_by_cols: list[str]
) -> list[str]
```
Returns error list. Validates: column exists, column is numeric, group-by
columns exist.

#### Class attributes

| Attribute | Value | Purpose |
|---|---|---|
| `IQR_MULTIPLIER` | `1.5` | Default multiplier constant |

---

### 2.3 ReductionService

| | |
|---|---|
| **File** | `src/core/services/managers/reduction_service.py` |
| **Stateless** | Yes -- all methods are `@staticmethod` |
| **Lines** | 58 |

Aggregates multi-seed simulation results by grouping on categorical columns
and computing mean and standard deviation.

#### Public methods

```python
@staticmethod
def reduce_seeds(
    df: pd.DataFrame, categorical_cols: list[str], statistic_cols: list[str]
) -> pd.DataFrame
```
Groups by `categorical_cols`, computes `mean()` and `std()` for each column
in `statistic_cols`. Standard deviation columns are appended with a `.sd`
suffix (e.g., `ipc` produces `ipc.sd`). The returned DataFrame orders
columns as: categorical first, then interleaved value/sd pairs.

```python
@staticmethod
def validate_seeds_reducer_inputs(
    df: pd.DataFrame, categorical_cols: list[str], statistic_cols: list[str]
) -> list[str]
```
Returns error list. Validates: at least one categorical column, at least one
statistic column, all columns exist, statistic columns are numeric.

---

## 3. Data Services

Data services manage file I/O, caching, parser variables, configuration
persistence, and portfolio snapshots.

### 3.1 CsvPoolService

| | |
|---|---|
| **File** | `src/core/services/data_services/csv_pool_service.py` |
| **Stateless** | Static methods only, but maintains class-level caches |
| **Lines** | 320 |

Manages CSV file storage, retrieval, and metadata caching in the data pool
directory (`{root}/.ring5/csv_pool/`).

#### Caching strategy (Cache-Aside pattern)

| Cache | Type | Max size | TTL | Purpose |
|---|---|---|---|---|
| `_metadata_cache` | `SimpleCache` | 100 | 10 min | Column names, row counts, dtypes |
| `_dataframe_cache` | `SimpleCache` | 10 | 5 min | Parsed DataFrame (LRU) |
| `_pool_index` | `dict` | unbounded | -- | Filename-to-entry O(1) lookup |

Cache keys are computed as the first 16 characters of
`MD5("{file_path}_{mtime}")`.

#### Public methods

```python
@staticmethod
def get_pool_dir() -> Path
```
Returns the CSV pool directory, creating it on first access.

```python
@staticmethod
def load_pool() -> list[CsvPoolEntry]
```
Scans `*.csv` in the pool directory, sorted by modification time (newest
first). Enriches each entry with cached metadata (columns, rows, dtypes).

```python
@staticmethod
def add_to_pool(csv_path: str) -> str
```
Copies a CSV file into the pool with a timestamp prefix
(`parsed_YYYYMMDD_HHMMSS.csv`). Returns the path within the pool. Uses
`validate_path_within()` for path traversal prevention.

```python
@staticmethod
def delete_from_pool(csv_path: str) -> bool
```
Validates the path is within the pool directory, then unlinks. Returns
`False` on failure (graceful degradation).

```python
@staticmethod
def load_csv_file(csv_path: str) -> pd.DataFrame
```
Loads a CSV with automatic separator detection (`sep=None, engine="python"`).
Checks the DataFrame cache first. Raises `ValueError` for empty paths,
`FileNotFoundError` if the file does not exist, and `IsADirectoryError` if
the path points to a directory.

```python
@staticmethod
def clear_caches() -> None
```
Clears all three caches and resets the pool directory path.

```python
@staticmethod
def get_cache_stats() -> CacheStatsInfo
```
Returns cache hit/miss statistics for monitoring.

---

### 3.2 ConfigService

| | |
|---|---|
| **File** | `src/core/services/data_services/config_service.py` |
| **Stateless** | Yes -- all methods are `@staticmethod` |
| **Lines** | 144 |

Manages JSON configuration files in `{root}/.ring5/saved_configs/`.

#### Public methods

```python
@staticmethod
def reset_caches() -> None
```
Resets the cached config directory path (for testing).

```python
@staticmethod
def get_config_dir() -> Path
```
Returns the configuration directory, creating it on first access.

```python
@staticmethod
def load_saved_configs() -> list[SavedConfigEntry]
```
Lists all `.json` configuration files, sorted by modification time (newest
first). Each entry contains `path`, `name`, `modified`, and `description`.
Silently skips files that cannot be read or parsed.

```python
@staticmethod
def save_configuration(
    name: str,
    description: str,
    shapers_config: list[ShaperStepConfig],
    csv_path: str | None = None,
) -> str
```
Serializes a configuration to JSON with a timestamped filename
(`{safe_name}_{YYYYMMDD_HHMMSS}.json`). Returns the saved file path.

```python
@staticmethod
def load_configuration(config_path: str) -> SavedConfigData
```
Loads and returns the parsed JSON configuration. Path is validated within the
config directory.

```python
@staticmethod
def delete_configuration(config_path: str) -> bool
```
Validates path, unlinks file. Returns `False` on failure.

---

### 3.3 PathService

| | |
|---|---|
| **File** | `src/core/services/data_services/path_service.py` |
| **Stateless** | Yes -- all methods are `@staticmethod` with class-level path caches |
| **Lines** | 58 |

Centralized file-system navigation. All directories are created with
`mkdir(parents=True, exist_ok=True)` on first access.

#### Public methods

```python
@staticmethod
def reset_caches() -> None
```
Resets all cached directory paths (for testing).

```python
@staticmethod
def get_root_dir() -> Path
```
Returns the project root directory (computed as five parents up from this
file).

```python
@staticmethod
def get_data_dir() -> Path
```
Returns `{root}/.ring5/`.

```python
@staticmethod
def get_pipelines_dir() -> Path
```
Returns `{root}/.ring5/pipelines/`.

```python
@staticmethod
def get_portfolios_dir() -> Path
```
Returns `{root}/.ring5/portfolios/`.

---

### 3.4 VariableService

| | |
|---|---|
| **File** | `src/core/services/data_services/variable_service.py` |
| **Stateless** | Yes -- all methods are `@staticmethod` or `@classmethod` |
| **Lines** | 542 |

The largest service by line count. Manages parser variable configurations
with CRUD operations for scalar, vector, distribution, histogram, and
configuration variable types. All operations are immutable -- they return new
lists rather than mutating inputs.

#### Security: ReDoS protection

All regex operations go through `_compile_safe_pattern()` which rejects
patterns longer than 500 characters, validates against a character allowlist,
and returns `None` on compilation failure (triggering a fallback to exact
match).

#### Class attributes

| Attribute | Value | Purpose |
|---|---|---|
| `DEFAULT_INTERNAL_STATS` | `frozenset({"total", "mean", "gmean", "stdev", "samples", "overflows", "underflows"})` | Simulator meta-statistics to exclude |

#### Public methods

```python
@staticmethod
def generate_variable_id() -> str
```
Returns a UUID4 string.

```python
@classmethod
def add_variable(
    cls, variables: list[ParseVariableConfig], var_config: ParseVariableConfig
) -> list[ParseVariableConfig]
```
Appends a variable with an auto-generated `_id` if not present.

```python
@classmethod
def update_variable(
    cls, variables: list[ParseVariableConfig], index: int,
    var_config: ParseVariableConfig
) -> list[ParseVariableConfig]
```
Replaces the variable at `index`. Raises `IndexError` if out of bounds.

```python
@classmethod
def delete_variable(
    cls, variables: list[ParseVariableConfig], index: int
) -> list[ParseVariableConfig]
```
Removes the variable at `index`. Raises `IndexError` if out of bounds.

```python
@classmethod
def ensure_variable_ids(
    cls, variables: list[ParseVariableConfig]
) -> list[ParseVariableConfig]
```
Fills missing `_id` fields with generated UUIDs.

```python
@classmethod
def filter_internal_stats(
    cls, entries: list[str],
    internal_stats: frozenset[str] | None = None,
) -> list[str]
```
Removes simulator meta-statistics from the entry list and returns the
remainder sorted alphabetically. Falls back to `DEFAULT_INTERNAL_STATS`
when `internal_stats` is not provided.

```python
@classmethod
def find_variable_by_name(
    cls, variables: list[ParseVariableConfig], name: str, exact: bool = True
) -> ParseVariableConfig | None
```
Finds a variable by name. When `exact=False`, uses safe regex pattern
matching.

```python
@classmethod
def aggregate_discovered_entries(
    cls, snapshot: list[ScannedVariableDict], var_name: str
) -> list[str]
```
Union of all entries for a variable across scanned files, with internal
stats filtered out.

```python
@classmethod
def aggregate_distribution_range(
    cls, snapshot: list[ScannedVariableDict], var_name: str
) -> tuple[float | None, float | None]
```
Returns the global `(min, max)` range across scanned files for a
distribution variable.

```python
@classmethod
def parse_comma_separated_entries(cls, entries_str: str) -> list[str]
```
Splits a comma-separated string into a list of trimmed, non-empty strings.

```python
@classmethod
def format_entries_as_string(cls, entries: list[str]) -> str
```
Joins a list with `", "`.

```python
@classmethod
def find_entries_for_variable(
    cls, available_variables: list[ScannedVariableDict], var_name: str
) -> list[str]
```
Searches scanned variables by exact name or regex pattern, aggregating
entries and filtering out internal statistics.

```python
@classmethod
def update_scanned_entries(
    cls, scanned_vars: list[ScannedVariableDict],
    var_name: str, new_entries: list[str],
) -> list[ScannedVariableDict]
```
Immutable update: replaces the entries for an existing variable or appends
a new vector variable.

```python
@classmethod
def has_variable_with_name(
    cls, variables: list[ParseVariableConfig], name: str
) -> bool
```
Returns `True` if any variable in the list has the given name.

```python
@classmethod
def build_statistics_list(cls, selected: dict[str, bool]) -> list[str]
```
Filters a `{name: bool}` mapping to only the selected names.

---

### 3.5 PortfolioService

| | |
|---|---|
| **File** | `src/core/services/data_services/portfolio_service.py` |
| **Stateful** | Yes -- holds a reference to `StateManager` |
| **Lines** | 199 |

Manages complete workspace snapshots (Memento pattern). This is the only data
service that is stateful; it requires a `StateManager` reference to access
parser state during serialization.

#### Portfolio schema (V2)

```json
{
    "schema_version": 2,
    "version": "2.0",
    "timestamp": "<ISO-8601>",
    "data_csv": "<CSV string>",
    "csv_path": "<original path>",
    "plots": [{"config": {}, "figure_spec": {}}],
    "plot_counter": 5,
    "config": {},
    "parse_variables": [],
    "stats_path": "...",
    "stats_pattern": "...",
    "scanned_variables": [],
    "manager_history": [],
    "portfolio_history": []
}
```

#### Constructor

```python
def __init__(self, state_manager: StateManager) -> None
```

#### Public methods

```python
def list_portfolios(self) -> list[str]
```
Returns the stem names of all `.json` files in the portfolios directory.

```python
def save_portfolio(
    self,
    name: str,
    data: pd.DataFrame | None,
    plots: list[PlotProtocol],
    config: dict[str, Any],
    plot_counter: int,
    csv_path: str | None = None,
    parse_variables: list[str] | None = None,
    figure_spec_enricher: Callable | None = None,
) -> None
```
Serializes and saves the current workspace state. Raises `ValueError` for
empty names. The optional `figure_spec_enricher` callback is injected from
the presentation layer to convert plot configs into `FigureConfig` dicts
without the core importing web-layer classes.

```python
def load_portfolio(self, name: str) -> PortfolioData
```
Loads a portfolio JSON by name. Runs `PortfolioMigrator.migrate()` for
backward compatibility. Raises `FileNotFoundError` if not found.

```python
def delete_portfolio(self, name: str) -> None
```
Deletes the portfolio file if it exists.

---

### 3.6 PatternIndexService

| | |
|---|---|
| **File** | `src/core/services/data_services/pattern_index_service.py` |
| **Stateless** | Yes -- all methods are `@staticmethod` |
| **Lines** | 269 |

Handles regex pattern variables (e.g., `system.ruby.l\d+_cntrl\d+.stat`)
that match multiple hardware components. Uses string splitting (not regex)
for index extraction to avoid ReDoS.

#### Public methods

```python
@staticmethod
def is_pattern_variable(var_name: str) -> bool
```
Returns `True` if the variable name contains `\d+`.

```python
@staticmethod
def extract_index_positions(var_name: str) -> list[str]
```
Extracts position labels from the pattern name.
Example: `r"system.ruby.l\d+_cntrl\d+.stat"` returns `["l", "cntrl"]`.

```python
@staticmethod
def parse_entry_indices(entries: list[str]) -> dict[int, set[str]]
```
Maps position index to the set of unique values found across entries.
Example: `["0_0", "0_1", "1_0"]` returns `{0: {"0","1"}, 1: {"0","1"}}`.

```python
@staticmethod
def filter_entries(entries: list[str], selections: dict[int, list[str]]) -> list[str]
```
Filters entries to only those matching the selected values at each position.

```python
@staticmethod
def format_entry_display(entry: str, positions: list[str]) -> str
```
Formats an entry for display. Example: `"0_1"` with `["l","cntrl"]` becomes
`"l{0}_cntrl{1}"`.

```python
@staticmethod
def reconstruct_concrete_name(pattern_name: str, numeric_id: str) -> str
```
Inverse operation: substitutes numeric parts into a pattern.
Example: `r"system.cpu\d+.ipc"` + `"3"` becomes `"system.cpu3.ipc"`.
Raises `ValueError` if placeholder count does not match part count.

---

## 4. Shaper Services

Shaper services handle the dynamic construction and execution of data
transformation pipelines.

### 4.1 ShaperFactory

| | |
|---|---|
| **File** | `src/core/services/shapers/factory.py` |
| **Stateless** | Yes -- class-level registry, all `@classmethod` |
| **Lines** | 141 |

Factory pattern with a class-level registry of shaper implementations.

#### Registered shaper types

| Registry key | Class | Display name |
|---|---|---|
| `mean` | `Mean` | Mean Calculator |
| `columnSelector` | `ColumnSelector` | Column Selector |
| `conditionSelector` | `ConditionSelector` | Filter |
| `itemSelector` | `ItemSelector` | Item Selector |
| `normalize` | `Normalize` | Normalize |
| `pivotLonger` | `PivotLonger` | Pivot Longer (Melt) |
| `pivotWider` | `PivotWider` | Pivot Wider |
| `sort` | `Sort` | Sort |
| `splitApply` | `SplitApply` | Split-Apply (Per-Axis) |
| `transformer` | `Transformer` | Transformer |

#### Public methods

```python
@classmethod
def register(cls, shaper_type: str, shaper_class: type[Shaper]) -> None
```
Registers a new shaper type at runtime (Open/Closed Principle).

```python
@classmethod
def get_available_types(cls) -> list[str]
```
Returns all registered type identifiers.

```python
@classmethod
def get_display_name_map(cls) -> dict[str, str]
```
Returns `{display_name: type_id}` for UI dropdowns.

```python
@classmethod
def get_display_name(cls, shaper_type: str) -> str
```
Returns the human-readable name for a type, or the type itself if none is
registered.

```python
@classmethod
def create_shaper(cls, shaper_type: str, params: ShaperStepConfig) -> Shaper
```
Instantiates a shaper of the given type. Raises `ValueError` with a list
of available types if the type is not found.

---

### 4.2 PipelineService

| | |
|---|---|
| **File** | `src/core/services/shapers/pipeline_service.py` |
| **Stateful** | Instance methods require `pipelines_dir`; `process_pipeline` is static |
| **Lines** | 214 |

Manages shaper pipeline CRUD and executes pipeline processing.

#### Constructor

```python
def __init__(self, pipelines_dir: Path) -> None
```
Creates the directory if it does not exist.

#### Instance methods (CRUD)

```python
def list_pipelines(self) -> list[str]
```
Returns the stem names of all `.json` files in the pipelines directory.

```python
def save_pipeline(
    self, name: str, pipeline_config: list[PipelineStep],
    description: str = ""
) -> None
```
Validates a non-empty name, sanitizes the filename, writes JSON with a
timestamp. Raises `ValueError` for empty names.

```python
def load_pipeline(self, name: str) -> PipelineData
```
Loads pipeline JSON with path validation. Raises `FileNotFoundError` if
the pipeline does not exist.

```python
def delete_pipeline(self, name: str) -> None
```
Unlinks the pipeline JSON file if it exists.

#### Static methods (execution)

```python
@staticmethod
def process_pipeline(
    data: pd.DataFrame, pipeline_config: list[ShaperStepConfig]
) -> pd.DataFrame
```
Core execution engine. Iterates over the config list, creates shapers via
`ShaperFactory.create_shaper()`, and applies each via `DataFrame.pipe()`.
Includes per-shaper and total performance timing via `time.perf_counter()`.
Errors are wrapped as `ValueError(f"Failed to apply shaper {type}: {e}")`.
No initial DataFrame copy is made -- each shaper is expected to handle
copying internally.

```python
@staticmethod
def prepare_loaded_pipeline(
    pipeline_data: PipelineData,
) -> tuple[list[PipelineStep], int]
```
Deep-copies the pipeline steps and computes the next counter value based
on the maximum step ID. Returns `(steps, next_counter)`.

---

### 4.3 Shaper Validation

| | |
|---|---|
| **File** | `src/core/services/shapers/validation.py` |
| **Stateless** | Yes -- module-level functions |
| **Lines** | 75 |

Pre-flight validation for shaper configurations before construction.

#### Required parameters per shaper type

| Shaper type | Required parameters |
|---|---|
| `mean` | `groupingColumns`, `meanVars` |
| `normalize` | `normalizeVars`, `normalizerColumn`, `normalizerValue`, `groupBy` |
| `pivotLonger` | `id_vars`, `value_vars`, `var_name`, `value_name` |
| `pivotWider` | `index`, `columns`, `values` |
| `sort` | `order_dict` |
| `splitApply` | `joinColumns`, `groups` |
| `columnSelector` | `columns` |
| `conditionSelector` | `column` |
| `transformer` | `column` |
| `itemSelector` | `column`, `strings` |

#### Public functions

```python
def validate_shaper_config(
    shaper_type: str, config: ShaperStepConfig
) -> tuple[bool, list[str] | None]
```
Returns `(True, None)` if all required parameters are present and non-empty.
Returns `(False, missing_fields)` listing the missing or empty fields. Empty
strings and empty lists are treated as missing.

```python
def get_required_params(shaper_type: str) -> list[str]
```
Returns the list of required parameter names for a shaper type, or an empty
list for unknown types.

---

## 5. Visualization Services

Visualization services provide pure-function logic for config resolution,
palette lookup, and plot interaction handling. None of these depend on UI
frameworks.

### 5.1 ConfigResolver

| | |
|---|---|
| **File** | `src/core/services/visualization/config_resolver.py` |
| **Stateless** | Yes -- pure functions |
| **Lines** | 185 |

Resolves sentinel values (`-1` for int, `-1.0` for float) in a
`FigureConfig` tree so that downstream rendering connectors never see raw
sentinel markers.

#### Constants

| Constant | Value | Meaning |
|---|---|---|
| `SENTINEL_INT` | `-1` | "inherit from parent" for integer fields |
| `SENTINEL_FLOAT` | `-1.0` | "inherit from parent" for float fields |

#### Inheritance chains

**Typography:**

```
font_size_base
+-- font_size_title
+-- font_size_xlabel
+-- font_size_ylabel
|   +-- font_size_y2label
+-- font_size_ticks
|   +-- font_size_yticks
|   +-- font_size_y2ticks
+-- font_size_annotations
+-- font_size_legend
    +-- font_size_legend2
    +-- font_size_legend3
        +-- legend3_number_fontsize
        +-- legend3_text_fontsize
```

**Legends:** Secondary and tertiary legends inherit `font_size`,
`title_font_size`, `number_fontsize`, `text_fontsize`, and all
`LegendSpacingConfig` fields from the primary legend.

**Axes:** Y2 axis inherits `label_pad` and `tick_pad` from the Y axis.

#### Public functions

```python
def resolve_config(spec: FigureConfig) -> FigureConfig
```
Entry point. Returns a deep copy with all sentinels replaced by inherited
values. Calls `_resolve_typography()`, `_resolve_legends()`, and
`_resolve_axes()` internally.

---

### 5.2 PaletteService

| | |
|---|---|
| **File** | `src/core/services/visualization/palette_service.py` |
| **Stateless** | Yes -- pure functions |
| **Lines** | 78 |

Logic layer for palette operations. Palette data (color hex values) resides
in `src/core/models/visualization/palettes.py`.

The registry includes 5 colorblind-safe palettes (`wong`, `okabe_ito`,
`tol_bright`, `viridis_8`, `seaborn_cb`) and 13 Plotly qualitative palettes
(`Alphabet`, `Bold`, `D3`, `Dark24`, `G10`, `Light24`, `Pastel`, `Plotly`,
`Safe`, `Set1`, `Set2`, `Set3`, `T10`, `Vivid`). The fallback palette for
any invalid input is always `"wong"`.

#### Public functions

```python
def resolve_palette(name: object) -> list[str]
```
Resolves a palette name to a list of hex color strings. Tries exact match,
then case-insensitive match, then falls back to `"wong"`. Returns a copy.

```python
def get_palette_names() -> list[str]
```
Returns ordered names with colorblind-safe palettes listed first, then Plotly
palettes alphabetically.

```python
def is_colorblind_safe(name: str) -> bool
```
Returns `True` if the palette is in the colorblind-safe set.

---

### 5.3 PlotInteraction

| | |
|---|---|
| **File** | `src/core/services/visualization/plot_interaction.py` |
| **Stateless** | Yes -- pure functions |
| **Lines** | 261 |

Handles interactive plot state changes from Plotly client-side events.

#### Public functions

```python
def try_float(value: str) -> float | str
```
Attempts float conversion; returns the original string on failure.

```python
def try_float_edit(value: Any) -> float | str
```
Broader type handling (handles `None`, `int`, etc.). Returns `str(value)` on
failure.

```python
def update_config_from_relayout(
    config: dict[str, Any], relayout_data: dict[str, Any]
) -> tuple[dict[str, Any], bool]
```
Processes Plotly relayout events. Handles:

1. **Zoom/pan** -- `xaxis.range[0]`/`[1]` and `yaxis.range[0]`/`[1]` mapped
   to `range_x` and `range_y`.
2. **Reset zoom** -- `xaxis.autorange` / `yaxis.autorange` set ranges to
   `None`.
3. **Legend drag** -- `legend.x`, `legend.y`, `legend2.x`, etc. mapped to
   `legend_x`, `legend_y`, etc. Auto-sets `xanchor="left"` and
   `yanchor="top"` when position changes.
4. **Legend title edit** -- `legend.title.text` mapped to `legend_title`.

Returns `(updated_config, changed)`. Uses `math.isclose(rel_tol=1e-9)` for
float comparison to avoid unnecessary reruns from floating-point noise.

```python
def resolve_item_order(
    items: list[str],
    default_order: list[str] | None = None,
    current_order: list[str] | None = None,
) -> list[str]
```
Synchronizes display ordering for reorderable lists:

- No existing order: uses `default_order` if provided, else natural order.
- Items unchanged: returns `current_order` as-is.
- Items changed: preserves existing order for common items, appends new items
  at end, removes absent items.

---

## 6. Config Validation Service

| | |
|---|---|
| **File** | `src/core/services/config_validation_service.py` |
| **Lines** | 378 |

Contains two classes for JSON-based pipeline configuration management.

### 6.1 ConfigValidator

**Stateful** -- holds a loaded JSON schema and a `Draft7Validator` instance.

#### Constructor

```python
def __init__(self, schema_path: str | None = None) -> None
```
Loads the JSON schema from `src/core/models/config/schemas/pipeline_schema.json`
(default) or a custom path. The schema path is validated within the schemas
directory.

#### Public methods

```python
def validate(self, config: RingConfig | dict[str, Any]) -> bool
```
Validates a configuration dict against the schema. Returns `True` if valid;
raises `ValidationError` on failure.

```python
def validate_file(self, config_path: str) -> bool
```
Loads and validates a JSON configuration file.

```python
def get_errors(self, config: dict[str, Any]) -> list[str]
```
Returns all validation errors as a list of `"{path}: {message}"` strings.

### 6.2 ConfigTemplateGenerator

**Stateless** -- all methods are `@staticmethod`.

Generates configuration templates with guided prompts. Contains reference
dictionaries for plot types, aggregate methods, and themes.

#### Supported plot types

`bar`, `line`, `heatmap`, `grouped_bar`, `stacked_bar`, `box`, `violin`,
`scatter`.

#### Public methods

```python
@staticmethod
def create_minimal_config(output_path: str, stats_path: str) -> RingConfig
```
Returns a minimal configuration with required fields only.

```python
@staticmethod
def create_plot_config(
    plot_type: str, x: str, y: str, filename: str, **kwargs: Any
) -> PlotConfig
```
Returns a plot configuration dict. Accepts optional `hue`, `title`, `xlabel`,
`ylabel`, `ylim`, `grid`, `legend`, `format`, `dpi`, `width`, `height`,
`theme`, `filters`, and `aggregate` keyword arguments.

```python
@staticmethod
def add_variable(
    config: RingConfig | dict, name: str, var_type: str,
    rename: str | None = None
) -> RingConfig | dict
```
Appends a variable to `config["parseConfig"]["variables"]`.

```python
@staticmethod
def enable_seeds_reducer(config: RingConfig | dict) -> RingConfig | dict
```
Sets `config["dataManagers"]["seedsReducer"]` to `True`.

```python
@staticmethod
def enable_outlier_removal(
    config: dict, column: str, method: str = "iqr", threshold: float = 1.5
) -> dict
```
Configures outlier removal in the data managers section.

```python
@staticmethod
def enable_normalizer(
    config: dict, baseline: dict[str, str], columns: list[str],
    group_by: list[str]
) -> dict
```
Configures data normalization in the data managers section.

```python
@staticmethod
def save_config(config: dict, output_path: str) -> None
```
Writes configuration to a JSON file.

### 6.3 Module-level convenience function

```python
def create_simple_bar_plot_config(
    output_path: str, stats_path: str,
    x_var: str, y_var: str, hue_var: str | None = None,
) -> RingConfig
```
Creates a complete configuration for a simple bar plot with seeds reduction
enabled.

---

## 7. Portfolio Migrator

| | |
|---|---|
| **File** | `src/core/services/portfolio_migrator.py` |
| **Stateless** | Yes -- all methods are `@staticmethod` |
| **Lines** | 72 |

Handles schema version migration for backward compatibility. All migrations
are idempotent.

#### Schema versions

| Version | Description |
|---|---|
| V1 (original) | Flat config dicts, `export_*` keys for LaTeX output |
| V2 (current) | `engine` field per plot, no `export_*` keys |

#### Class attribute

| Attribute | Value |
|---|---|
| `CURRENT_VERSION` | `2` |

#### Public methods

```python
@staticmethod
def migrate(portfolio_data: dict[str, Any]) -> dict[str, Any]
```
Migrates a portfolio dict to the current schema version. Reads
`schema_version` (defaults to 1 if absent). If below 2, runs V1-to-V2
migration (deep copy, add `engine` defaults, remove `export_*` keys). Sets
`schema_version` to `CURRENT_VERSION` before returning.

---

## 8. See Also

- **Application API** -- the public facade that delegates to all services
  listed here: `src/core/application_api.py`.
- **Services facade and protocols** -- `src/core/services/services_api.py`
  (Protocol) and `src/core/services/services_impl.py` (DefaultServicesAPI
  composition root).
- **Sub-API protocols** --
  `src/core/services/managers/managers_api.py`,
  `src/core/services/data_services/data_services_api.py`,
  `src/core/services/shapers/shapers_api.py`.
- **Shaper base classes** -- `src/core/services/shapers/shaper.py` (ABC) and
  `src/core/services/shapers/uni_df_shaper.py`.
- **Concrete shaper implementations** --
  `src/core/services/shapers/impl/` directory.
- **State management** -- `src/core/state/state_manager.py` (StateManager
  Protocol).
- **Palette data** -- `src/core/models/visualization/palettes.py`.
- **Visualization config models** -- `src/core/models/visualization/` package
  (FigureConfig, LegendConfig, TypographyConfig, AxesConfig).
