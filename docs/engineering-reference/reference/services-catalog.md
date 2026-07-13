---
title: "RING-5 Services Catalog"
parent: Reference
grand_parent: Engineering Reference
nav_order: 2
---

# RING-5 Services Catalog

> AI-optimized reference. All services under `src/core/services/`.

## Architecture Overview

```
ApplicationAPI (src/core/application_api.py)
  +-- DefaultServicesAPI (src/core/services/services_impl.py)
        +-- DefaultManagersAPI   -> ArithmeticService, OutlierService, ReductionService
        +-- DefaultDataServicesAPI -> CsvPoolService, ConfigService, PathService,
        |                            VariableService, PortfolioService, PatternIndexService
        +-- DefaultShapersAPI    -> ShaperFactory, PipelineService
  +-- Visualization (standalone) -> ConfigResolver, PaletteService, plot_interaction helpers
  +-- Other (standalone)         -> PortfolioMigrator
```

- Every sub-API is a `@runtime_checkable Protocol` with a single `Default*` implementation
- Composition root: `DefaultServicesAPI.__init__` wires all dependencies
- Session lifecycle: one `ApplicationAPI` is stored under `st.session_state.api`

---

## 1. Manager Services

Stateless services for DataFrame transformations. All methods are `@staticmethod`.
Accessed via `api.managers.*`.

### ArithmeticService

- **File**: `src/core/services/managers/arithmetic_service.py`
- **Stateless**: Yes (all `@staticmethod`)
- **Methods**:
  - `list_operators() -> list[str]` -- returns `["Division", "Sum", "Subtraction", "Multiplication"]`
  - `apply_operation(df: DataFrame, operation: str, src1: str, src2: str, dest: str) -> DataFrame`
  - `apply_mixer(df: DataFrame, dest_col: str, source_cols: list[str], operation: str = "Sum", separator: str = "_") -> DataFrame`
  - `merge_columns(df: DataFrame, columns: list[str], operation: str, new_column_name: str, separator: str = "_") -> DataFrame`
  - `validate_merge_inputs(df: DataFrame, columns: list[str], operation: str, new_column_name: str) -> list[str]`
- **Key behavior**:
  - `apply_operation`: division replaces zero denominators with `np.nan`
  - `apply_mixer` supports `Sum`, `Mean`, `Mean (Average)`, `Concatenate`
  - SD propagation: auto-detects `{col}.sd` / `{col}_stdev` columns; Sum: `sqrt(sum(sd^2))`, Mean: `sqrt(sum(sd^2)) / n`
  - `merge_columns` is a convenience wrapper around `apply_mixer`
  - All methods return a copy; input DataFrame is never mutated
  - Validation returns `list[str]` errors (empty = valid)

**Operator alias table**:

| Canonical | Aliases |
|---|---|
| `Division` | `divide`, `/` |
| `Sum` | `add`, `+` |
| `Subtraction` | `subtract`, `minus`, `-` |
| `Multiplication` | `multiply`, `*` |

---

### OutlierService

- **File**: `src/core/services/managers/outlier_service.py`
- **Stateless**: Yes (all `@staticmethod`)
- **Methods**:
  - `remove_outliers(df: DataFrame, outlier_col: str, group_by_cols: list[str], multiplier: float = 1.5) -> DataFrame`
  - `validate_outlier_inputs(df: DataFrame, outlier_col: str, group_by_cols: list[str]) -> list[str]`
- **Key behavior**:
  - IQR method: values outside `[Q1 - m*IQR, Q3 + m*IQR]` removed
  - Default multiplier `1.5` (mild outliers); use `3.0` for extreme only
  - Empty `group_by_cols` = global mode; non-empty = per-group via `groupby().transform()`
  - Returns input DataFrame unchanged if empty or column missing
  - Class constant: `IQR_MULTIPLIER = 1.5`

---

### ReductionService

- **File**: `src/core/services/managers/reduction_service.py`
- **Stateless**: Yes (all `@staticmethod`)
- **Methods**:
  - `reduce_seeds(df: DataFrame, categorical_cols: list[str], statistic_cols: list[str]) -> DataFrame`
  - `validate_seeds_reducer_inputs(df: DataFrame, categorical_cols: list[str], statistic_cols: list[str]) -> list[str]`
- **Key behavior**:
  - Groups by `categorical_cols`, computes `mean()` and `std()` for `statistic_cols`
  - SD columns named with `.sd` suffix (e.g., `ipc` -> `ipc.sd`)
  - Column order: categorical first, then interleaved value/sd pairs
  - Returns input unchanged if empty

---

## 2. Data Services

File I/O and domain entity management. Accessed via `api.data_services.*`.

### CsvPoolService

- **File**: `src/core/services/data_services/csv_pool_service.py`
- **Stateless**: No (class-level caches, but no instance state -- all `@staticmethod`)
- **Methods**:
  - `get_pool_dir() -> Path`
  - `load_pool() -> list[CsvPoolEntry]`
  - `add_to_pool(csv_path: str) -> str`
  - `delete_from_pool(csv_path: str) -> bool`
  - `load_csv_file(csv_path: str) -> DataFrame`
  - `clear_caches() -> None`
  - `get_cache_stats() -> CacheStatsInfo`
- **Key behavior**:
  - Cache-aside pattern with three class-level caches:

    | Cache | Type | Max Size | TTL |
    |---|---|---|---|
    | `_metadata_cache` | `SimpleCache` | 100 | 10 min |
    | `_dataframe_cache` | `SimpleCache` | 10 | 5 min |
    | `_pool_index` | `dict` | unbounded | -- |

  - Cache key: MD5 of `"{file_path}_{mtime}"` (first 16 chars)
  - `load_csv_file` uses `pd.read_csv(sep=None, engine="python")` for auto-separator detection
  - `add_to_pool` copies file with timestamp prefix `parsed_YYYYMMDD_HHMMSS.csv`
  - Path traversal prevention via `validate_path_within()` on all file ops
  - Thread-safe pool index via `threading.Lock`
  - `delete_from_pool` returns `False` on failure (graceful degradation)
  - `load_csv_file` raises `ValueError`, `FileNotFoundError`, `IsADirectoryError`

---

### ConfigService

- **File**: `src/core/services/data_services/config_service.py`
- **Stateless**: Yes (all `@staticmethod`, class-level path cache only)
- **Methods**:
  - `get_config_dir() -> Path`
  - `reset_caches() -> None`
  - `load_saved_configs() -> list[SavedConfigEntry]`
  - `save_configuration(name: str, description: str, shapers_config: list[ShaperStepConfig], csv_path: str | None = None) -> str`
  - `load_configuration(config_path: str) -> SavedConfigData`
  - `delete_configuration(config_path: str) -> bool`
- **Key behavior**:
  - Storage dir: `{root}/.ring5/saved_configs/`
  - Filename format: `{sanitized_name}_{YYYYMMDD_HHMMSS}.json`
  - `load_saved_configs` sorts by mtime descending, skips unreadable files with debug log
  - Path validation via `validate_path_within()` for save/load/delete
  - Filename sanitization via `sanitize_filename()`
  - `delete_configuration` returns `False` on failure

---

### PathService

- **File**: `src/core/services/data_services/path_service.py`
- **Stateless**: Yes (all `@staticmethod`, class-level caches)
- **Methods**:
  - `get_root_dir() -> Path`
  - `get_data_dir() -> Path`
  - `get_pipelines_dir() -> Path`
  - `get_portfolios_dir() -> Path`
  - `reset_caches() -> None`
- **Key behavior**:
  - All paths lazy-initialized and cached at class level
  - All directories created with `mkdir(parents=True, exist_ok=True)` on first access

  | Method | Returns |
  |---|---|
  | `get_root_dir()` | Project root (5 parents up from file) |
  | `get_data_dir()` | `{root}/.ring5/` |
  | `get_pipelines_dir()` | `{root}/.ring5/pipelines/` |
  | `get_portfolios_dir()` | `{root}/.ring5/portfolios/` |

---

### VariableService

- **File**: `src/core/services/data_services/variable_service.py`
- **Stateless**: Yes (all `@staticmethod` / `@classmethod`)
- **Methods**:
  - `generate_variable_id() -> str` -- UUID4
  - `add_variable(variables: list, var_config: dict) -> list`
  - `update_variable(variables: list, index: int, var_config: dict) -> list`
  - `delete_variable(variables: list, index: int) -> list`
  - `ensure_variable_ids(variables: list) -> list`
  - `filter_internal_stats(entries: list[str], internal_stats: frozenset[str] | None = None) -> list[str]`
  - `find_variable_by_name(variables: list, name: str, exact: bool = True) -> dict | None`
  - `aggregate_discovered_entries(snapshot: list, var_name: str) -> list[str]`
  - `aggregate_distribution_range(snapshot: list, var_name: str) -> tuple[float | None, float | None]`
  - `parse_comma_separated_entries(entries_str: str) -> list[str]`
  - `format_entries_as_string(entries: list[str]) -> str`
  - `find_entries_for_variable(available_variables: list, var_name: str) -> list[str]`
  - `update_scanned_entries(scanned_vars: list, var_name: str, new_entries: list[str]) -> list`
  - `has_variable_with_name(variables: list, name: str) -> bool`
  - `build_statistics_list(selected: dict[str, bool]) -> list[str]`
- **Key behavior**:
  - Largest service by line count (542 lines)
  - All CRUD operations are **immutable** -- return new lists, never mutate input
  - `update_variable` / `delete_variable` raise `IndexError` on out-of-bounds
  - ReDoS protection: `_compile_safe_pattern()` enforces max 500 char length + character allowlist
  - Regex fallback: invalid patterns fall back to exact-match
  - Default internal stats exclusion set:
    ```python
    DEFAULT_INTERNAL_STATS = frozenset({
        "total", "mean", "gmean", "stdev", "samples", "overflows", "underflows"
    })
    ```

---

### PortfolioService

- **File**: `src/core/services/data_services/portfolio_service.py`
- **Stateless**: No (holds `StateManager` reference)
- **Methods**:
  - `__init__(state_manager: StateManager) -> None`
  - `list_portfolios() -> list[str]`
  - `save_portfolio(name: str, data: DataFrame | None, plots: list[PlotProtocol], config: dict, plot_counter: int, csv_path: str | None = None, parse_variables: list | None = None, figure_spec_enricher: Callable | None = None) -> None`
  - `load_portfolio(name: str) -> PortfolioData`
  - `delete_portfolio(name: str) -> None`
- **Key behavior**:
  - Memento pattern: captures complete workspace state
  - Storage dir: `{root}/.ring5/portfolios/`
  - Schema V2 format (JSON with embedded CSV string)
  - `save_portfolio` accepts optional `figure_spec_enricher` callback from presentation layer
  - `load_portfolio` runs `PortfolioMigrator.migrate()` for backward compatibility
  - Raises `ValueError` for empty name, `FileNotFoundError` for missing portfolio
  - Reads parser state from `StateManager` during save (stats_path, scanned_variables, history)
  - Path security: `validate_path_within()` + `sanitize_filename()`

**Portfolio JSON schema (V2)**:
```json
{
  "schema_version": 2,
  "version": "2.0",
  "timestamp": "ISO-8601",
  "data_csv": "CSV string",
  "csv_path": "original/path.csv",
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

---

### PatternIndexService

- **File**: `src/core/models/pattern_index_service.py`
- **Stateless**: Yes (all `@staticmethod`)
- **Methods**:
  - `is_pattern_variable(var_name: str) -> bool`
  - `extract_index_positions(var_name: str) -> list[str]`
  - `parse_entry_indices(entries: list[str]) -> dict[int, set[str]]`
  - `filter_entries(entries: list[str], selections: dict[int, list[str]]) -> list[str]`
  - `format_entry_display(entry: str, positions: list[str]) -> str`
  - `reconstruct_concrete_name(pattern_name: str, numeric_id: str) -> str`
- **Key behavior**:
  - Handles regex pattern variables (e.g., `system.ruby.l\d+_cntrl\d+.stat`)
  - `is_pattern_variable`: checks for `\d+` substring
  - `extract_index_positions`: uses string splitting (not regex) to avoid ReDoS
  - `reconstruct_concrete_name`: inverse of pattern extraction; raises `ValueError` on placeholder/ID mismatch
  - Example: `reconstruct_concrete_name(r"system.cpu\d+.ipc", "3")` -> `"system.cpu3.ipc"`

---

## 3. Shaper Services

Pipeline management and transformation factory. Accessed via `api.shapers.*`.

### ShaperFactory

- **File**: `src/core/services/shapers/factory.py`
- **Stateless**: Yes (class-level registry, all `@classmethod`)
- **Methods**:
  - `register(shaper_type: str, shaper_class: type[Shaper]) -> None`
  - `get_available_types() -> list[str]`
  - `get_display_name_map() -> dict[str, str]`
  - `get_display_name(shaper_type: str) -> str`
  - `create_shaper(shaper_type: str, params: ShaperStepConfig) -> Shaper`
- **Key behavior**:
  - Factory pattern with 10 registered shaper types
  - `create_shaper` raises `ValueError` with available-types listing if type is unknown
  - Supports runtime registration via `register()` (Open/Closed Principle)

**Registry**:

| Key | Class | Display Name |
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

---

### PipelineService

- **File**: `src/core/services/shapers/pipeline_service.py`
- **Stateless**: No (holds `pipelines_dir` Path)
- **Methods**:
  - `__init__(pipelines_dir: Path) -> None`
  - `list_pipelines() -> list[str]`
  - `save_pipeline(name: str, pipeline_config: list[PipelineStep], description: str = "") -> None`
  - `load_pipeline(name: str) -> PipelineData`
  - `delete_pipeline(name: str) -> None`
  - `process_pipeline(data: DataFrame, pipeline_config: list[ShaperStepConfig]) -> DataFrame` [static]
  - `prepare_loaded_pipeline(pipeline_data: PipelineData) -> tuple[list[PipelineStep], int]` [static]
- **Key behavior**:
  - CRUD operations are instance methods (require `pipelines_dir`)
  - `process_pipeline` and `prepare_loaded_pipeline` are `@staticmethod`
  - Pipeline execution flow:
    ```
    for step in pipeline_config:
        shaper = ShaperFactory.create_shaper(step["type"], step)
        current_data = current_data.pipe(shaper)
    ```
  - No initial DataFrame copy -- each shaper creates its own copy internally
  - Per-shaper and total timing logged with `PERF:` prefix
  - Errors wrapped as `ValueError(f"Failed to apply shaper {type}: {e}")`
  - `prepare_loaded_pipeline`: deep-copies steps, computes next ID counter from max step ID
  - Raises `ValueError` for empty name, `FileNotFoundError` for missing pipeline
  - Path security: `validate_path_within()` + `sanitize_filename()`

### Shaper Validation (module-level functions)

- **File**: `src/core/services/shapers/validation.py`
- **Stateless**: Yes (module-level functions)
- **Methods**:
  - `validate_shaper_config(shaper_type: str, config: ShaperStepConfig) -> tuple[bool, list[str] | None]`
  - `get_required_params(shaper_type: str) -> list[str]`
- **Key behavior**:
  - Pre-flight validation before shaper construction
  - Returns `(True, None)` if valid; `(False, missing_fields)` if invalid
  - Empty strings and empty lists treated as "missing"
  - Never raises exceptions

**Required params per shaper type**:

| Type | Required Params |
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

---

## 4. Visualization Services

Pure functions. No class instances. Accessed via direct import from `src/core/services/visualization/`.

### ConfigResolver

- **File**: `src/core/services/visualization/config_resolver.py`
- **Stateless**: Yes (pure function)
- **Methods**:
  - `resolve_config(spec: FigureConfig) -> FigureConfig`
- **Key behavior**:
  - Sentinel value: `-1` (int) or `-1.0` (float) means "inherit from parent"
  - Returns deep copy; never mutates input
  - Resolves three domains in one pass: typography, legends, axes
  - Typography inheritance chain:
    ```
    font_size_ylabel -> font_size_y2label
    font_size_ticks  -> font_size_yticks -> font_size_y2ticks
    font_size_legend -> font_size_legend2
    ```
  - Legend inheritance: secondary/tertiary inherit font_size, title_font_size, spacing from primary
  - Axes inheritance: y2.label_pad and y2.tick_pad inherit from y axis (when y2 present)

**Sentinel constants**:
```python
SENTINEL_INT = -1
SENTINEL_FLOAT = -1.0
```

---

### PaletteService

- **File**: `src/core/services/visualization/palette_service.py`
- **Stateless**: Yes (pure functions)
- **Methods**:
  - `resolve_palette(name: object) -> list[str]`
  - `get_palette_names() -> list[str]`
  - `is_colorblind_safe(name: str) -> bool`
- **Key behavior**:
  - `resolve_palette`: exact match -> case-insensitive match -> fallback to `"wong"`
  - Always returns a **copy** of the color list (safe to mutate)
  - Never raises exceptions; invalid/None input returns Wong palette
  - 18 registered palettes: 5 colorblind-safe + 13 Plotly qualitative
  - `get_palette_names` returns colorblind-safe first, then Plotly alphabetical

**Colorblind-safe palettes**: `wong`, `okabe_ito`, `tol_bright`, `viridis_8`, `seaborn_cb`

**Plotly palettes**: `Alphabet`, `Bold`, `D3`, `Dark24`, `G10`, `Light24`, `Pastel`, `Plotly`, `Safe`, `Set1`, `Set2`, `Set3`, `T10`, `Vivid`

---

### Plot Interaction Helpers

- **File**: `src/core/services/visualization/plot_interaction.py`
- **Stateless**: Yes (pure functions)
- **Functions**:
  - `try_float(value: str) -> float | str`
  - `try_float_edit(value: Any) -> float | str`
  - `resolve_item_order(items: list[str], default_order: list[str] | None = None, current_order: list[str] | None = None) -> list[str]`
- **Relayout sync** -- `src/web/rendering/relayout.py::update_config_from_relayout(config: dict, relayout_data: dict) -> tuple[dict, bool]`:
  - Zoom/pan: `xaxis.range[0/1]` -> `range_x`
  - Reset zoom: `xaxis.autorange` -> `range_x = None`
  - Legend drag: `legend.x/y` -> `legend_x/y` + auto-set anchors (`xanchor="left"`, `yanchor="top"`)
  - Legend title: `legend.title.text` -> `legend_title`
  - Change detection uses `math.isclose(rel_tol=1e-9)` to avoid float noise
  - Returns `(config, False)` for empty relayout data
  - `resolve_item_order`: preserves existing order for common items, appends new items at end

---

## 5. Other Services

### PortfolioMigrator

- **File**: `src/core/services/portfolio_migrator.py`
- **Stateless**: Yes (all `@staticmethod`)
- **Methods**:
  - `migrate(portfolio_data: dict) -> dict`
- **Key behavior**:
  - Idempotent schema migration
  - Current version: `CURRENT_VERSION = 2`
  - V1 -> V2 changes:
    - Adds `config["engine"] = "plotly"` as default per plot
    - Removes all `export_*` keys from plot configs
    - Uses `copy.deepcopy()` for safety
  - Reads `schema_version` (defaults to 1 if absent)

---

## Cross-Cutting Patterns

### Error Handling Summary

| Service | Pattern |
|---|---|
| ArithmeticService | `ValueError` for unknown ops; division by zero -> `NaN` |
| OutlierService | Early return for empty/missing; validates numeric dtype |
| ReductionService | Early return for empty; error list from validation |
| CsvPoolService | `FileNotFoundError` / `IsADirectoryError` / `ValueError` for load; `False` for delete |
| ConfigService | `False` for delete; skips corrupt files with debug log |
| VariableService | `IndexError` for OOB CRUD; safe regex -> `None` fallback |
| PortfolioService | `ValueError` empty name; `FileNotFoundError` missing portfolio |
| ShaperFactory | `ValueError` with available-types listing |
| PipelineService | `ValueError` empty name / wrapped shaper errors |
| ConfigResolver | No error handling (pure, operates on deep copy) |
| PaletteService | Never raises; falls back to `"wong"` palette |
| `relayout.update_config_from_relayout` | Returns `(config, False)` for empty data |

### Security Measures

- **Path traversal**: `validate_path_within(path, base_dir)` used by CsvPoolService, ConfigService, PipelineService, PortfolioService
- **Filename sanitization**: `sanitize_filename(name)` on all user-supplied filenames before path construction
- **ReDoS protection**: `VariableService._compile_safe_pattern()` -- max 500 chars, character allowlist, compilation failure -> exact-match fallback
- **Glob sanitization**: `sanitize_glob_pattern()` in `ApplicationAPI.find_stats_files()`

### Immutability

- All Manager services: `df.copy()` before modification
- VariableService: returns new lists, never mutates input
- ConfigResolver: `deepcopy()` on input FigureConfig
- PaletteService: returns copy of color list
- PortfolioMigrator: `deepcopy()` during migration

## Protocol / Implementation Map

| Protocol File | Implementation File | Stateful |
|---|---|---|
| `src/core/services/services_api.py` | `src/core/services/services_impl.py` | Yes (composes sub-APIs) |
| `src/core/services/managers/managers_api.py` | `src/core/services/managers/managers_impl.py` | No |
| `src/core/services/data_services/data_services_api.py` | `src/core/services/data_services/data_services_impl.py` | Yes (PortfolioService) |
| `src/core/services/shapers/shapers_api.py` | `src/core/services/shapers/shapers_impl.py` | Yes (PipelineService holds dir) |

---

## Instantiation Flow

```
app.py -> st.session_state.api -> ApplicationAPI(plot_deserializer=BasePlot.from_dict)
  +-- RepositoryStateManager(plot_deserializer)
  +-- DefaultServicesAPI(state_manager)
  |     +-- DefaultManagersAPI()                         [stateless]
  |     |     delegates to ArithmeticService              [static methods]
  |     |     delegates to OutlierService                 [static methods]
  |     |     delegates to ReductionService               [static methods]
  |     +-- DefaultDataServicesAPI(state_manager)
  |     |     delegates to CsvPoolService                 [static methods, class caches]
  |     |     delegates to ConfigService                  [static methods]
  |     |     delegates to VariableService                [static/class methods]
  |     |     creates    PortfolioService(state_manager)  [stateful]
  |     +-- DefaultShapersAPI(PathService.get_pipelines_dir())
  |           creates    PipelineService(pipelines_dir)   [instance-based]
  |           delegates to ShaperFactory                  [class-level registry]
  +-- SimulatorRegistry.get_parser("gem5")
```

---

## Summary Statistics

| Metric | Count |
|---|---|
| Total service files | 42 |
| Sub-packages | 4 (`managers/`, `data_services/`, `shapers/`, `visualization/`) |
| Protocol definitions | 4 |
| Concrete service classes | 14 |
| Registered shaper types | 10 |
| Registered palettes | 18 |
| ApplicationAPI public methods | 35 |
| ManagersAPI methods | 8 |
| DataServicesAPI methods | 29 |
| ShapersAPI methods | 7 |
| Visualization functions | 7 |
