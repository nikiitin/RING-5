---
title: "Protocol Catalog"
parent: Reference
grand_parent: Engineering Reference
nav_order: 3
---

# Protocol Catalog

> 19 Python `Protocol` classes across 3 architectural layers.
> All protocols use `typing.Protocol` (structural subtyping / duck typing).

---

## Summary Table

| # | Protocol | Layer | File | Line | Methods | Implementations |
|---|----------|-------|------|------|---------|-----------------|
| 1 | `StateManager` | Core | `src/core/state/state_manager.py` | 28 | 42 | `RepositoryStateManager` |
| 2 | `PlotProtocol` | Core | `src/core/models/plot_protocol.py` | 18 | 1 + 8 attrs | `BasePlot` |
| 3 | `PlotDeserializer` | Core | `src/core/models/plot_protocol.py` | 41 | 1 (`__call__`) | `BasePlot.from_dict` |
| 4 | `ServicesAPI` | Core | `src/core/services/services_api.py` | 25 | 3 properties | `DefaultServicesAPI` |
| 5 | `DataServicesAPI` | Core | `src/core/services/data_services/data_services_api.py` | 31 | 25 | `DefaultDataServicesAPI` |
| 6 | `ManagersAPI` | Core | `src/core/services/managers/managers_api.py` | 15 | 8 | `DefaultManagersAPI` |
| 7 | `ShapersAPI` | Core | `src/core/services/shapers/shapers_api.py` | 17 | 7 | `DefaultShapersAPI` |
| 8 | `SimulationParser` | Parsing | `src/parsing/parser_protocol.py` | 8 | 4 | `Gem5Parser` |
| 9 | `FileParserStrategy` | Parsing | `src/parsing/gem5/impl/strategies/file_parser_strategy.py` | 25 | 3 | `SimpleStatsStrategy`, `ConfigAwareStrategy` |
| 10 | `PlotHandle` | Web | `src/web/models/plot_protocols.py` | 37 | 0 (6 attrs) | `BasePlot` |
| 11 | `ConfigRenderer` | Web | `src/web/models/plot_protocols.py` | 58 | 4 + 1 attr | `BasePlot` |
| 12 | `RenderablePlot` | Web | `src/web/models/plot_protocols.py` | 87 | 3 + 2 attrs | `BasePlot` |
| 13 | `PlotLifecycleService` | Web | `src/web/models/plot_protocols.py` | 111 | 4 | `PlotLifecycleAdapter` |
| 14 | `PlotTypeRegistry` | Web | `src/web/models/plot_protocols.py` | 134 | 1 | `PlotTypeRegistryAdapter` |
| 15 | `PipelineExecutor` | Web | `src/web/models/plot_protocols.py` | 145 | 2 | `PipelineExecutorAdapter` |
| 16 | `SpecificOptionsRenderer` | Web | `src/web/components/plotting/settings/axes_settings.py` | 51 | 1 (`__call__`) | `BasePlot` bound methods |
| 17 | `OrderingRenderer` | Web | `src/web/components/plotting/settings/axes_settings.py` | 61 | 1 (`__call__`) | `BasePlot` bound methods |
| 18 | `ReferenceLineRenderer` | Web | `src/web/components/plotting/settings/advanced_settings.py` | 33 | 1 (`__call__`) | `BasePlot` bound methods |
| 19 | `ShapesRenderer` | Web | `src/web/components/plotting/settings/advanced_settings.py` | 44 | 1 (`__call__`) | `BasePlot` bound methods |
| -- | `EngineControlsRenderer` | Web | `src/web/components/plotting/settings/advanced_settings.py` | 53 | 1 (`__call__`) | `BasePlot` bound methods |

**Note**: The user request listed 10 Web protocols. The file `plot_protocols.py` contains 7 distinct protocol classes. `axes_settings.py` adds 2 and `advanced_settings.py` adds 3, totaling 12 Web-layer protocols. `EngineControlsRenderer` is listed as a bonus 20th entry.

---

## Core Layer Protocols (7)

### 1. StateManager

- **File**: `src/core/state/state_manager.py` line 28
- **Decorator**: `@runtime_checkable`
- **Purpose**: Defines the complete contract for application state management (data, config, parser, plots, previews, history).
- **Implementation**: `RepositoryStateManager` in `src/core/state/repository_state_manager.py` line 36

| Method | Signature |
|--------|-----------|
| `initialize` | `() -> None` |
| `get_data` | `() -> pd.DataFrame \| None` |
| `set_data` | `(data: pd.DataFrame \| None, on_change: Callable[[], None] \| None = None) -> None` |
| `get_processed_data` | `() -> pd.DataFrame \| None` |
| `set_processed_data` | `(data: pd.DataFrame \| None) -> None` |
| `has_data` | `() -> bool` |
| `clear_data` | `() -> None` |
| `get_config` | `() -> dict[str, Any]` |
| `set_config` | `(config: dict[str, Any]) -> None` |
| `update_config` | `(key: str, value: object) -> None` |
| `get_temp_dir` | `() -> str \| None` |
| `set_temp_dir` | `(path: str) -> None` |
| `get_csv_path` | `() -> str \| None` |
| `set_csv_path` | `(path: str) -> None` |
| `get_csv_pool` | `() -> list[CsvPoolEntry]` |
| `set_csv_pool` | `(pool: list[CsvPoolEntry]) -> None` |
| `get_saved_configs` | `() -> list[SavedConfigEntry]` |
| `set_saved_configs` | `(configs: list[SavedConfigEntry]) -> None` |
| `is_using_parser` | `() -> bool` |
| `set_use_parser` | `(use: bool) -> None` |
| `get_parse_variables` | `() -> list[ParseVariableConfig]` |
| `set_parse_variables` | `(variables: list[ParseVariableConfig]) -> None` |
| `get_stats_path` | `() -> str` |
| `set_stats_path` | `(path: str) -> None` |
| `get_stats_pattern` | `() -> str` |
| `set_stats_pattern` | `(pattern: str) -> None` |
| `get_scanned_variables` | `() -> list[ScannedVariableDict]` |
| `set_scanned_variables` | `(variables: list[ScannedVariableDict]) -> None` |
| `get_parser_strategy` | `() -> str` |
| `set_parser_strategy` | `(strategy: str) -> None` |
| `get_simulator` | `() -> str` |
| `set_simulator` | `(simulator: str) -> None` |
| `get_plots` | `() -> list[PlotProtocol]` |
| `set_plots` | `(plots: list[PlotProtocol]) -> None` |
| `add_plot` | `(plot_obj: PlotProtocol) -> None` |
| `get_plot_counter` | `() -> int` |
| `set_plot_counter` | `(counter: int) -> None` |
| `start_next_plot_id` | `() -> int` |
| `get_current_plot_id` | `() -> int \| None` |
| `set_current_plot_id` | `(plot_id: int \| None) -> None` |
| `set_preview` | `(operation_name: str, data: pd.DataFrame) -> None` |
| `get_preview` | `(operation_name: str) -> pd.DataFrame \| None` |
| `has_preview` | `(operation_name: str) -> bool` |
| `clear_preview` | `(operation_name: str) -> None` |
| `add_manager_history_record` | `(record: OperationRecord) -> None` |
| `get_manager_history` | `() -> list[OperationRecord]` |
| `add_portfolio_history_record` | `(record: OperationRecord) -> None` |
| `get_portfolio_history` | `() -> list[OperationRecord]` |
| `remove_manager_history_record` | `(record: OperationRecord) -> None` |
| `remove_portfolio_history_record` | `(record: OperationRecord) -> None` |
| `clear_all` | `() -> None` |
| `restore_session` | `(portfolio_data: PortfolioData) -> None` |

### 2. PlotProtocol

- **File**: `src/core/models/plot_protocol.py` line 18
- **Decorator**: `@runtime_checkable`
- **Purpose**: Decouples Core layer from Web layer's `BasePlot` concrete class.
- **Implementation**: `BasePlot` in `src/web/pages/ui/plotting/base_plot.py`

| Member | Kind | Type / Signature |
|--------|------|------------------|
| `plot_id` | attribute | `int` |
| `name` | attribute | `str` |
| `plot_type` | attribute | `str` |
| `config` | attribute | `dict[str, Any]` |
| `pipeline` | attribute | `list[PipelineStep]` |
| `pipeline_counter` | attribute | `int` |
| `legend_mappings_by_column` | attribute | `dict[str, dict[str, str]]` |
| `legend_mappings` | attribute | `dict[str, str]` |
| `processed_data` | attribute | `pd.DataFrame \| None` |
| `to_dict` | method | `() -> dict[str, Any]` |

### 3. PlotDeserializer (Type Alias)

- **File**: `src/core/models/plot_protocol.py` line 41
- **Kind**: `Callable` type alias (not a `Protocol` class)
- **Purpose**: Callback type for dictionary-to-PlotProtocol deserialization, injected at startup.
- **Implementation**: `BasePlot.from_dict` injected via `ApplicationAPI.__init__`

```python
PlotDeserializer = Callable[[dict[str, Any]], PlotProtocol | None]
```

### 4. ServicesAPI

- **File**: `src/core/services/services_api.py` line 25
- **Decorator**: `@runtime_checkable`
- **Purpose**: Unified facade providing hierarchical access to managers, data_services, and shapers sub-APIs.
- **Implementation**: `DefaultServicesAPI` in `src/core/services/services_impl.py` line 18

| Member | Kind | Return Type |
|--------|------|-------------|
| `managers` | property | `ManagersAPI` |
| `data_services` | property | `DataServicesAPI` |
| `shapers` | property | `ShapersAPI` |

### 5. DataServicesAPI

- **File**: `src/core/services/data_services/data_services_api.py` line 31
- **Decorator**: `@runtime_checkable`
- **Purpose**: Contract for CSV pool management, config persistence, variable CRUD, and portfolio operations.
- **Implementation**: `DefaultDataServicesAPI` in `src/core/services/data_services/data_services_impl.py` line 30

| Method | Signature |
|--------|-----------|
| `load_csv_pool` | `() -> list[CsvPoolEntry]` |
| `add_to_csv_pool` | `(file_path: str) -> str` |
| `delete_from_csv_pool` | `(file_path: str) -> bool` |
| `load_csv_file` | `(file_path: str) -> pd.DataFrame` |
| `save_configuration` | `(name: str, description: str, shapers_config: list[ShaperStepConfig], csv_path: str \| None = None) -> str` |
| `load_configuration` | `(config_path: str) -> SavedConfigData` |
| `load_saved_configs` | `() -> list[SavedConfigEntry]` |
| `delete_configuration` | `(config_path: str) -> bool` |
| `get_cache_stats` | `() -> CacheStatsInfo` |
| `clear_caches` | `() -> None` |
| `generate_variable_id` | `() -> str` |
| `add_variable` | `(variables: list[ParseVariableConfig], var_config: ParseVariableConfig) -> list[ParseVariableConfig]` |
| `update_variable` | `(variables: list[ParseVariableConfig], index: int, var_config: ParseVariableConfig) -> list[ParseVariableConfig]` |
| `delete_variable` | `(variables: list[ParseVariableConfig], index: int) -> list[ParseVariableConfig]` |
| `ensure_variable_ids` | `(variables: list[ParseVariableConfig]) -> list[ParseVariableConfig]` |
| `filter_internal_stats` | `(entries: list[str], internal_stats: frozenset[str] \| None = None) -> list[str]` |
| `find_variable_by_name` | `(variables: list[ParseVariableConfig], name: str, exact: bool = True) -> ParseVariableConfig \| None` |
| `aggregate_discovered_entries` | `(snapshot: list[ScannedVariableDict], var_name: str) -> list[str]` |
| `aggregate_distribution_range` | `(snapshot: list[ScannedVariableDict], var_name: str) -> tuple[float \| None, float \| None]` |
| `parse_comma_separated_entries` | `(entries_str: str) -> list[str]` |
| `format_entries_as_string` | `(entries: list[str]) -> str` |
| `find_entries_for_variable` | `(available_variables: list[ScannedVariableDict], var_name: str) -> list[str]` |
| `update_scanned_entries` | `(scanned_vars: list[ScannedVariableDict], var_name: str, new_entries: list[str]) -> list[ScannedVariableDict]` |
| `has_variable_with_name` | `(variables: list[ParseVariableConfig], name: str) -> bool` |
| `build_statistics_list` | `(selected: dict[str, bool]) -> list[str]` |
| `list_portfolios` | `() -> list[str]` |
| `save_portfolio` | `(name: str, data: pd.DataFrame \| None, plots: list[PlotProtocol], config: dict[str, Any], plot_counter: int, csv_path: str \| None = None, parse_variables: list[str] \| None = None, figure_spec_enricher: Callable \| None = None) -> None` |
| `load_portfolio` | `(name: str) -> PortfolioData` |
| `delete_portfolio` | `(name: str) -> None` |

### 6. ManagersAPI

- **File**: `src/core/services/managers/managers_api.py` line 15
- **Decorator**: `@runtime_checkable`
- **Purpose**: Contract for stateless data transformation operations (arithmetic, outlier removal, seed reduction).
- **Implementation**: `DefaultManagersAPI` in `src/core/services/managers/managers_impl.py` line 14

| Method | Signature |
|--------|-----------|
| `list_operators` | `() -> list[str]` |
| `apply_operation` | `(df: pd.DataFrame, operation: str, src1: str, src2: str, dest: str) -> pd.DataFrame` |
| `apply_mixer` | `(df: pd.DataFrame, dest_col: str, source_cols: list[str], operation: str = "Sum", separator: str = "_") -> pd.DataFrame` |
| `validate_merge_inputs` | `(df: pd.DataFrame, columns: list[str], operation: str, new_column_name: str) -> list[str]` |
| `remove_outliers` | `(df: pd.DataFrame, outlier_col: str, group_by_cols: list[str]) -> pd.DataFrame` |
| `validate_outlier_inputs` | `(df: pd.DataFrame, outlier_col: str, group_by_cols: list[str]) -> list[str]` |
| `reduce_seeds` | `(df: pd.DataFrame, categorical_cols: list[str], statistic_cols: list[str]) -> pd.DataFrame` |
| `validate_seeds_reducer_inputs` | `(df: pd.DataFrame, categorical_cols: list[str], statistic_cols: list[str]) -> list[str]` |

### 7. ShapersAPI

- **File**: `src/core/services/shapers/shapers_api.py` line 17
- **Decorator**: `@runtime_checkable`
- **Purpose**: Contract for pipeline CRUD and shaper transformation chain execution.
- **Implementation**: `DefaultShapersAPI` in `src/core/services/shapers/shapers_impl.py` line 17

| Method | Signature |
|--------|-----------|
| `list_pipelines` | `() -> list[str]` |
| `save_pipeline` | `(name: str, pipeline_config: list[PipelineStep], description: str = "") -> None` |
| `load_pipeline` | `(name: str) -> PipelineData` |
| `delete_pipeline` | `(name: str) -> None` |
| `process_pipeline` | `(data: pd.DataFrame, pipeline_config: list[ShaperStepConfig]) -> pd.DataFrame` |
| `create_shaper` | `(shaper_type: str, params: ShaperStepConfig) -> Shaper` |
| `get_available_shaper_types` | `() -> list[str]` |

---

## Parsing Layer Protocols (2)

### 8. SimulationParser

- **File**: `src/parsing/parser_protocol.py` line 8
- **Decorator**: `@runtime_checkable`
- **Purpose**: Unified contract for simulation data parsing and variable scanning, decoupling app from gem5 specifics.
- **Implementations**:
  - `Gem5Parser` in `src/parsing/gem5/impl/gem5_parser.py` line 94
  - `Gem5Parser` in `src/parsing/gem5/impl/gem5_parser.py` line 17

| Method | Signature |
|--------|-----------|
| `submit_parse_async` | `(stats_path: str, stats_pattern: str, variables: list[StatConfig], output_dir: str, strategy_type: str = "simple", scanned_vars: list[ScannedVariable] \| None = None) -> ParseBatchResult` |
| `finalize_parsing` | `(output_dir: str, results: list[dict[str, Any]], strategy_type: str = "simple", var_names: list[str] \| None = None) -> str \| None` |
| `submit_scan_async` | `(stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5) -> list[Future[list[ScannedVariable]]]` |
| `aggregate_scan_results` | `(results: list[list[ScannedVariable]]) -> list[ScannedVariable]` |

### 9. FileParserStrategy

- **File**: `src/parsing/gem5/impl/strategies/file_parser_strategy.py` line 25
- **Decorator**: none (plain `Protocol`)
- **Purpose**: Strategy contract for individual file parsing workflows (discover, execute, post-process).
- **Implementations**:
  - `SimpleStatsStrategy` in `src/parsing/gem5/impl/strategies/simple.py` line 41
  - `ConfigAwareStrategy` in `src/parsing/gem5/impl/strategies/config_aware.py` line 25 (extends `SimpleStatsStrategy`)

| Method | Signature |
|--------|-----------|
| `execute` | `(stats_path: str, stats_pattern: str, variables: list[StatConfig]) -> list[dict[str, Any]]` |
| `get_work_items` | `(stats_path: str, stats_pattern: str, variables: list[StatConfig]) -> Sequence[ParseWork]` |
| `post_process` | `(results: list[dict[str, Any]]) -> list[dict[str, Any]]` |

---

## Web Layer Protocols (10+)

### 10. PlotHandle

- **File**: `src/web/models/plot_protocols.py` line 37
- **Decorator**: `@runtime_checkable`
- **Purpose**: Read-only data attributes every controller needs from a plot object.
- **Implementation**: `BasePlot` in `src/web/pages/ui/plotting/base_plot.py`

| Member | Kind | Type |
|--------|------|------|
| `plot_id` | attribute | `int` |
| `name` | attribute | `str` |
| `plot_type` | attribute | `str` |
| `config` | attribute | `dict[str, Any]` |
| `processed_data` | attribute | `pd.DataFrame \| None` |
| `pipeline` | attribute | `list[PipelineStep]` |
| `pipeline_counter` | attribute | `int` |

### 11. ConfigRenderer

- **File**: `src/web/models/plot_protocols.py` line 58
- **Decorator**: none
- **Purpose**: Contract for plot-type-specific config UI rendering.
- **Implementation**: `BasePlot` in `src/web/pages/ui/plotting/base_plot.py`

| Method | Signature |
|--------|-----------|
| `render_config_ui` | `(data: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]` |
| `render_display_options` | `(config: dict[str, Any]) -> dict[str, Any]` |
| `render_theme_options` | `(config: dict[str, Any]) -> dict[str, Any]` |
| `render_settings_section` | `(section: str \| None, saved_config: dict[str, Any], data: pd.DataFrame \| None = None) -> dict[str, Any]` |

### 12. RenderablePlot

- **File**: `src/web/models/plot_protocols.py` line 87
- **Decorator**: `@runtime_checkable`
- **Purpose**: Combined `PlotHandle + ConfigRenderer` for controllers needing both data access and rendering.
- **Implementation**: `BasePlot` in `src/web/pages/ui/plotting/base_plot.py`
- **Inherits from**: `PlotHandle`, `ConfigRenderer`, `Protocol`

| Member | Kind | Type / Signature |
|--------|------|------------------|
| `last_generated_fig` | attribute | `go.Figure \| None` |
| `last_traces` | attribute | `TraceBuildResult \| None` |
| `create_figure` | method | `(data: pd.DataFrame, config: dict[str, Any]) -> go.Figure` |
| `apply_common_layout` | method | `(fig: go.Figure, config: dict[str, Any]) -> go.Figure` |
| `update_from_relayout` | method | `(relayout_data: dict[str, Any]) -> bool` |

### 13. PlotLifecycleService

- **File**: `src/web/models/plot_protocols.py` line 111
- **Decorator**: none
- **Purpose**: Contract for plot CRUD operations (create, delete, duplicate, change type).
- **Implementation**: `PlotLifecycleAdapter` in `src/web/pages/plot_adapters.py` line 44

| Method | Signature |
|--------|-----------|
| `create_plot` | `(name: str, plot_type: str, state_manager: RepositoryStateManager) -> PlotHandle` |
| `delete_plot` | `(plot_id: int, state_manager: RepositoryStateManager) -> None` |
| `duplicate_plot` | `(plot: PlotHandle, state_manager: RepositoryStateManager) -> PlotHandle` |
| `change_plot_type` | `(plot: PlotHandle, new_type: str, state_manager: RepositoryStateManager) -> PlotHandle` |

### 14. PlotTypeRegistry

- **File**: `src/web/models/plot_protocols.py` line 134
- **Decorator**: none
- **Purpose**: Contract for querying available plot types from the factory.
- **Implementation**: `PlotTypeRegistryAdapter` in `src/web/pages/plot_adapters.py` line 74

| Method | Signature |
|--------|-----------|
| `get_available_types` | `() -> list[str]` |

### 15. PipelineExecutor

- **File**: `src/web/models/plot_protocols.py` line 145
- **Decorator**: none
- **Purpose**: Contract for applying shaper pipelines and rendering shaper configuration UI.
- **Implementation**: `PipelineExecutorAdapter` in `src/web/pages/plot_adapters.py` line 86

| Method | Signature |
|--------|-----------|
| `apply_shapers` | `(data: pd.DataFrame, configs: list[ShaperStepConfig]) -> pd.DataFrame` |
| `configure_shaper` | `(shaper_type: str, data: pd.DataFrame, shaper_id: int, config: ShaperStepConfig \| None, owner_id: int \| None = None) -> ShaperStepConfig` |

### 16. SpecificOptionsRenderer

- **File**: `src/web/components/plotting/settings/axes_settings.py` line 51
- **Decorator**: none
- **Purpose**: Callable protocol for rendering plot-type-specific advanced axis options.
- **Implementation**: `BasePlot.render_specific_advanced_options` (bound method injected as callback)

```python
def __call__(self, saved_config: PlotConfig, data: pd.DataFrame | None) -> PlotConfig: ...
```

### 17. OrderingRenderer

- **File**: `src/web/components/plotting/settings/axes_settings.py` line 61
- **Decorator**: none
- **Purpose**: Callable protocol for rendering ordering/sorting controls on axes.
- **Implementation**: `BasePlot._render_ordering_ui` (bound method injected as callback)

```python
def __call__(self, saved_config: PlotConfig, data: pd.DataFrame, config: PlotConfig) -> None: ...
```

### 18. ReferenceLineRenderer

- **File**: `src/web/components/plotting/settings/advanced_settings.py` line 33
- **Decorator**: none
- **Purpose**: Callable protocol for rendering reference/threshold line UI widgets.
- **Implementation**: `BasePlot._render_reference_line_ui` (bound method injected as callback)

```python
def __call__(self, saved_config: PlotConfig, data: pd.DataFrame | None, config: PlotConfig) -> None: ...
```

### 19. ShapesRenderer

- **File**: `src/web/components/plotting/settings/advanced_settings.py` line 44
- **Decorator**: none
- **Purpose**: Callable protocol for rendering annotation/shape configuration UI.
- **Implementation**: `BasePlot._render_shapes_ui` (bound method injected as callback)

```python
def __call__(self, saved_config: PlotConfig) -> list[ShapeConfig]: ...
```

### 20. EngineControlsRenderer

- **File**: `src/web/components/plotting/settings/advanced_settings.py` line 53
- **Decorator**: none
- **Purpose**: Callable protocol for rendering engine-specific control widgets (Plotly vs Matplotlib).
- **Implementation**: `BasePlot._render_engine_specific_controls` (bound method injected as callback)

```python
def __call__(self, saved_config: PlotConfig, config: PlotConfig) -> None: ...
```

---

## Protocols by Pattern

### Facade Protocols (hierarchical service access)

| Protocol | Sub-protocols |
|----------|---------------|
| `ServicesAPI` | `ManagersAPI`, `DataServicesAPI`, `ShapersAPI` |

### Boundary Protocols (cross-layer decoupling)

| Protocol | Decouples |
|----------|-----------|
| `PlotProtocol` | Core from Web (`BasePlot`) |
| `PlotDeserializer` | Core from Web (`BasePlot.from_dict`) |
| `StateManager` | `ApplicationAPI` from `RepositoryStateManager` |
| `SimulationParser` | Core from Parsing (`Gem5Parser`) |

### Adapter Protocols (controller-to-service bridge)

| Protocol | Adapter Class | Wraps |
|----------|---------------|-------|
| `PlotLifecycleService` | `PlotLifecycleAdapter` | `PlotService` static methods |
| `PlotTypeRegistry` | `PlotTypeRegistryAdapter` | `PlotFactory.get_available_plot_types()` |
| `PipelineExecutor` | `PipelineExecutorAdapter` | `apply_shapers()`, `configure_shaper()` |

### Callable Protocols (single-method UI callbacks)

| Protocol | Injected As |
|----------|-------------|
| `SpecificOptionsRenderer` | `BasePlot.render_specific_advanced_options` |
| `OrderingRenderer` | `BasePlot._render_ordering_ui` |
| `ReferenceLineRenderer` | `BasePlot._render_reference_line_ui` |
| `ShapesRenderer` | `BasePlot._render_shapes_ui` |
| `EngineControlsRenderer` | `BasePlot._render_engine_specific_controls` |

---

## Key Type Imports Used in Protocols

```
src/core/models/data_models.py      -> CsvPoolEntry, ParseVariableConfig, SavedConfigEntry,
                                        ScannedVariableDict, ShaperStepConfig, PipelineStep,
                                        PipelineData, SavedConfigData, CacheStatsInfo
src/core/models/history_models.py   -> OperationRecord
src/core/models/plot_protocol.py    -> PlotProtocol, PlotDeserializer
src/core/models/portfolio_models.py -> PortfolioData
src/core/models/parsing_models.py   -> StatConfig, ScannedVariable, ParseBatchResult
src/core/models/plot_config.py      -> ShapeConfig
src/web/models/plot_models.py       -> PlotConfig (TypeAlias = dict[str, Any])
src/core/services/shapers/shaper.py -> Shaper (ABC)
```
