---
title: "Services API Reference"
parent: API Reference
grand_parent: Developer Guide
nav_order: 2
---

# Services API Reference

The Services layer is the business-logic tier of RING-5 Unified Engine v2, sitting
between the presentation layer (Streamlit web UI) and the state/persistence layer.
All domain operations are exposed through a protocol-first, composition-based facade.

## Overview

`ServicesAPI` is the unified facade protocol that groups three domain-aligned
sub-APIs behind a single entry point. It defines no methods of its own -- only
three read-only properties. The presentation layer accesses services exclusively
through `ApplicationAPI`, which composes a `ServicesAPI` instance internally.

| Source File | Role |
|---|---|
| `src/core/services/services_api.py` | `ServicesAPI` protocol definition |
| `src/core/services/services_impl.py` | `DefaultServicesAPI` composition root |
| `src/core/services/managers/managers_api.py` | `ManagersAPI` protocol |
| `src/core/services/data_services/data_services_api.py` | `DataServicesAPI` protocol |
| `src/core/services/shapers/shapers_api.py` | `ShapersAPI` protocol |

## ServicesAPI Protocol

```python
@runtime_checkable
class ServicesAPI(Protocol):
    @property
    def managers(self) -> ManagersAPI: ...
    @property
    def data_services(self) -> DataServicesAPI: ...
    @property
    def shapers(self) -> ShapersAPI: ...
```

A `@runtime_checkable` protocol with zero methods and three properties. It is
purely structural, grouping the sub-APIs behind a single composable facade.

| Property | Return Type | Description |
|---|---|---|
| `managers` | `ManagersAPI` | Stateless data transformations (arithmetic, outlier removal, seed reduction). |
| `data_services` | `DataServicesAPI` | Data storage and domain entity management (CSV pool, configs, variables, portfolios). |
| `shapers` | `ShapersAPI` | Pipeline CRUD and shaper transformation execution. |

## DefaultServicesAPI Implementation

```python
class DefaultServicesAPI:
    def __init__(self, state_manager: StateManager) -> None:
```

The composition root that wires all sub-APIs via constructor injection.

| Sub-API | Concrete Class | Injected Dependencies |
|---|---|---|
| `_managers` | `DefaultManagersAPI()` | None (stateless) |
| `_data_services` | `DefaultDataServicesAPI(state_manager)` | `StateManager` for portfolio operations |
| `_shapers` | `DefaultShapersAPI(PathService.get_pipelines_dir())` | Pipelines directory from `PathService` |

Cross-module dependencies (e.g., `ShapersAPI` needing `PathService` from
`data_services`) are resolved at this composition root rather than through
direct imports between sub-packages.

## ManagersAPI Protocol

```python
@runtime_checkable
class ManagersAPI(Protocol):
```

Eight methods across three domains. The default implementation
(`DefaultManagersAPI`) delegates to `ArithmeticService`, `OutlierService`,
and `ReductionService` -- all stateless classes with static methods only.

### Arithmetic Operations

**`list_operators(self) -> list[str]`** -- Return supported binary operator
names: `Division`, `Sum`, `Subtraction`, `Multiplication`.

**`apply_operation(self, df, operation, src1, src2, dest) -> pd.DataFrame`** --
Apply a binary arithmetic operation between two columns. Returns a new
DataFrame with the computed `dest` column. Division replaces zero denominators
with `NaN`. Raises `ValueError` for unknown operators.

| Parameter | Type | Description |
|---|---|---|
| `df` | `pd.DataFrame` | Input DataFrame (not mutated). |
| `operation` | `str` | Operator name (e.g., `"Division"`, `"Sum"`). |
| `src1` | `str` | First source column name. |
| `src2` | `str` | Second source column name. |
| `dest` | `str` | Destination column name for the result. |

**`apply_mixer(self, df, dest_col, source_cols, operation="Sum", separator="_") -> pd.DataFrame`** --
Merge multiple columns into one. Supported operations: `"Sum"`, `"Mean"` /
`"Mean (Average)"`, `"Concatenate"`. Standard deviation columns (`.sd` or
`_stdev` suffix) are automatically propagated using `sqrt(sum(sd_i^2))` for
Sum and `sqrt(sum(sd_i^2)) / n` for Mean.

**`validate_merge_inputs(self, df, columns, operation, new_column_name) -> list[str]`** --
Return an empty list if valid, or error strings describing each problem (fewer
than 2 columns, missing columns, invalid operation, empty/duplicate name).

### Outlier Removal

**`remove_outliers(self, df, outlier_col, group_by_cols) -> pd.DataFrame`** --
Remove rows where `outlier_col` falls outside `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`.
Pass an empty `group_by_cols` list for global (ungrouped) detection.

**`validate_outlier_inputs(self, df, outlier_col, group_by_cols) -> list[str]`** --
Validate column existence and numeric dtype. Returns error strings or empty list.

### Seeds Reduction

**`reduce_seeds(self, df, categorical_cols, statistic_cols) -> pd.DataFrame`** --
Group by `categorical_cols` and compute `mean()` + `std()` for each statistic
column. Standard deviation columns are appended with `.sd` suffix. Output order:
categorical columns first, then interleaved value/`.sd` columns.

**`validate_seeds_reducer_inputs(self, df, categorical_cols, statistic_cols) -> list[str]`** --
Validate presence and types of columns. Returns error strings or empty list.

## DataServicesAPI Protocol

```python
@runtime_checkable
class DataServicesAPI(Protocol):
```

Twenty-nine methods across five domains. `DefaultDataServicesAPI` delegates to
`CsvPoolService`, `ConfigService`, `VariableService`, and `PortfolioService`.
Only `PortfolioService` is stateful (holds a `StateManager` reference).

### CSV Pool

| Method | Signature | Description |
|---|---|---|
| `load_csv_pool` | `() -> list[CsvPoolEntry]` | List pool CSV files sorted by mtime (newest first), enriched with cached metadata. |
| `add_to_csv_pool` | `(file_path: str) -> str` | Copy CSV into pool with timestamp prefix. Returns pool path. |
| `delete_from_csv_pool` | `(file_path: str) -> bool` | Delete from pool (path validated within pool dir). Returns `False` on failure. |
| `load_csv_file` | `(file_path: str) -> pd.DataFrame` | Load CSV with auto separator detection. Cached (10 entries, 5-min TTL). Raises `FileNotFoundError`, `IsADirectoryError`, `ValueError`. |

### Configuration Persistence

| Method | Signature | Description |
|---|---|---|
| `save_configuration` | `(name: str, description: str, shapers_config: list[ShaperStepConfig], csv_path: str \| None = None) -> str` | Serialize pipeline config to JSON. Returns saved file path. |
| `load_configuration` | `(config_path: str) -> SavedConfigData` | Load and parse a JSON configuration file. |
| `load_saved_configs` | `() -> list[SavedConfigEntry]` | List all configs sorted by mtime, each with `name`, `path`, `modified`, `description`. |
| `delete_configuration` | `(config_path: str) -> bool` | Delete a config file. Returns `False` on failure. |

### Cache Management

| Method | Signature | Description |
|---|---|---|
| `get_cache_stats` | `() -> CacheStatsInfo` | Return CSV pool cache statistics (metadata, DataFrame, pool index sizes). |
| `clear_caches` | `() -> None` | Clear all CSV pool caches. |

### Variable Management

All variable operations are immutable -- they return new lists, never mutating inputs.

| Method | Signature | Description |
|---|---|---|
| `generate_variable_id` | `() -> str` | Generate a UUID4 identifier. |
| `add_variable` | `(variables, var_config) -> list[ParseVariableConfig]` | Append variable with auto-generated `_id`. |
| `update_variable` | `(variables, index: int, var_config) -> list[ParseVariableConfig]` | Replace at index. Raises `IndexError`. |
| `delete_variable` | `(variables, index: int) -> list[ParseVariableConfig]` | Remove at index. Raises `IndexError`. |
| `ensure_variable_ids` | `(variables) -> list[ParseVariableConfig]` | Fill missing `_id` fields with UUIDs. |
| `filter_internal_stats` | `(entries: list[str], internal_stats: frozenset[str] \| None = None) -> list[str]` | Remove simulator meta-stats (`total`, `mean`, `gmean`, `stdev`, `samples`, `overflows`, `underflows`). Returns sorted list. |
| `find_variable_by_name` | `(variables, name: str, exact: bool = True) -> ParseVariableConfig \| None` | Exact or ReDoS-safe regex search. |
| `aggregate_discovered_entries` | `(snapshot: list[ScannedVariableDict], var_name: str) -> list[str]` | Union of entries across scanned files. |
| `aggregate_distribution_range` | `(snapshot: list[ScannedVariableDict], var_name: str) -> tuple[float \| None, float \| None]` | Global min/max for a distribution variable. |
| `parse_comma_separated_entries` | `(entries_str: str) -> list[str]` | Split comma-separated string into trimmed list. |
| `format_entries_as_string` | `(entries: list[str]) -> str` | Join entries with `", "`. |
| `find_entries_for_variable` | `(available_variables: list[ScannedVariableDict], var_name: str) -> list[str]` | Search scanned variables for matching entries. |
| `update_scanned_entries` | `(scanned_vars, var_name: str, new_entries: list[str]) -> list[ScannedVariableDict]` | Immutably update entries for a variable. |
| `has_variable_with_name` | `(variables, name: str) -> bool` | Check name existence. |
| `build_statistics_list` | `(selected: dict[str, bool]) -> list[str]` | Filter boolean map to selected names. |

### Portfolio Management

**`list_portfolios(self) -> list[str]`** -- List names of saved portfolios
in `{root}/.ring5/portfolios/`.

**`save_portfolio(self, name, data, plots, config, plot_counter, csv_path=None, parse_variables=None, figure_spec_enricher=None) -> None`** --
Serialize a complete workspace snapshot (Memento pattern).

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Portfolio name (sanitized for filename). Raises `ValueError` if empty. |
| `data` | `pd.DataFrame \| None` | Current working DataFrame. |
| `plots` | `list[PlotProtocol]` | Active plot objects. |
| `config` | `dict[str, Any]` | Application configuration state. |
| `plot_counter` | `int` | Current plot ID counter. |
| `csv_path` | `str \| None` | Original CSV file path. |
| `parse_variables` | `list[str] \| None` | Parser variable configurations. |
| `figure_spec_enricher` | `Callable \| None` | Presentation-layer callback converting plot config dicts to `FigureConfig` dicts. |

**`load_portfolio(self, name: str) -> PortfolioData`** -- Load by name with
V1-to-V2 schema migration via `PortfolioMigrator`. Raises `FileNotFoundError`.

**`delete_portfolio(self, name: str) -> None`** -- Delete a portfolio by name.

## ShapersAPI Protocol

```python
@runtime_checkable
class ShapersAPI(Protocol):
```

Seven methods covering pipeline CRUD and shaper execution. `DefaultShapersAPI`
delegates CRUD to `PipelineService` and creation/execution to `ShaperFactory`.

### Pipeline CRUD

| Method | Signature | Description |
|---|---|---|
| `list_pipelines` | `() -> list[str]` | List saved pipeline names (stem only, no `.json`). |
| `save_pipeline` | `(name: str, pipeline_config: list[PipelineStep], description: str = "") -> None` | Save as JSON with sanitized filename. Raises `ValueError` if name is empty. |
| `load_pipeline` | `(name: str) -> PipelineData` | Load by name. Raises `FileNotFoundError`. |
| `delete_pipeline` | `(name: str) -> None` | Delete pipeline JSON file. |

### Shaper Execution

**`process_pipeline(self, data: pd.DataFrame, pipeline_config: list[ShaperStepConfig]) -> pd.DataFrame`** --
Execute a shaper chain. For each step, creates a shaper via
`ShaperFactory.create_shaper()` and applies it via `DataFrame.pipe()`.
Per-shaper and total times are logged with `PERF:` prefix. Raises
`ValueError("Failed to apply shaper {type}: {e}")` on failure.

**`create_shaper(self, shaper_type: str, params: ShaperStepConfig) -> Shaper`** --
Instantiate a shaper from the factory. Raises `ValueError` if the type is not
registered. The ten registered types are: `mean`, `columnSelector`,
`conditionSelector`, `itemSelector`, `normalize`, `pivotLonger`, `pivotWider`,
`sort`, `splitApply`, `transformer`.

**`get_available_shaper_types(self) -> list[str]`** -- Return all registered
shaper type identifiers.

## ApplicationAPI Delegation to ServicesAPI

`ApplicationAPI` (in `src/core/application_api.py`) is the single entry point
for the presentation layer. It composes a `DefaultServicesAPI` and re-exposes
all three sub-API properties for direct use by UI components:

```python
class ApplicationAPI:
    def __init__(self, plot_deserializer=None, parser=None):
        self.state_manager = RepositoryStateManager(plot_deserializer=plot_deserializer)
        self._services = DefaultServicesAPI(self.state_manager)

    @property
    def managers(self) -> ManagersAPI:
        return self._services.managers

    @property
    def data_services(self) -> DataServicesAPI:
        return self._services.data_services

    @property
    def shapers(self) -> ShapersAPI:
        return self._services.shapers
```

Beyond direct sub-API access, `ApplicationAPI` provides orchestration methods
that coordinate calls across services and state -- for example, `load_data()`
calls `data_services.load_csv_file()` then persists via `state_manager.set_data()`,
and `apply_shapers()` delegates to `shapers.process_pipeline()`. Configuration
management methods forward directly to `data_services`.

`ApplicationAPI` is instantiated once per Streamlit server process via
`@st.cache_resource` and stored in `st.session_state.api`, ensuring all
sub-APIs share a single lifecycle.

## See Also

- **State Management** -- `src/core/state/state_manager.py` defines the
  `StateManager` protocol consumed by `DataServicesAPI`.
- **Shaper Base Classes** -- `src/core/services/shapers/shaper.py` and
  `src/core/services/shapers/uni_df_shaper.py` define the `Shaper` ABC.
- **Shaper Factory** -- `src/core/services/shapers/factory.py` maintains
  the type registry and display-name mapping.
- **Visualization Services** -- `src/core/services/visualization/` provides
  config resolution, palette lookup, and plot interaction as pure functions
  outside the `ServicesAPI` facade.
- **Portfolio Migrator** -- `src/core/services/portfolio_migrator.py` handles
  backward-compatible schema migration for portfolio files.
