# Step 04 -- State Management & Repositories Analysis

> **Objective**: Document the complete state management architecture including
> all repositories, session state keys, state lifecycle, caching strategy, and
> serialization flows.

---

## 1. Executive Summary

RING-5 Unified Engine v2 employs a **two-tier state architecture** that cleanly
separates **persistent domain state** (data, plots, config, history) from
**transient UI state** (auto-refresh flags, dialog visibility, widget ordering).

### Tier 1 -- Domain State (Core Layer)

Domain state lives inside **seven in-memory repositories** coordinated by a
single `SessionRepository` aggregate root.  The `RepositoryStateManager` facade
exposes a flat API surface that the `ApplicationAPI` delegates through.  All
repositories are pure Python with zero Streamlit dependency.

### Tier 2 -- UI State (Web Layer)

Transient, presentation-only state lives in Streamlit `session_state` and is
accessed exclusively through the `UIStateManager` class, which provides typed,
namespaced accessors organized into four sub-managers (`plot`, `manager`, `nav`,
`export`).

### Singleton Bootstrap

`ApplicationAPI` is instantiated exactly once per Streamlit session via
`@st.cache_resource` in `app.py` and stored at `st.session_state.api`.  Because
`ApplicationAPI` holds the `RepositoryStateManager`, all domain state survives
Streamlit reruns without serialization into `session_state`.

### Key Quantities

| Metric | Count |
|--------|-------|
| Core repositories | 7 (+ SessionRepository aggregate) |
| RepositoryStateManager facade methods | 46 |
| UIStateManager namespaced sub-managers | 4 |
| Direct `st.session_state` access points (outside UIStateManager) | ~45 locations across 16 files |
| `@st.cache_resource` usages | 1 (`get_api()` in `app.py`) |
| `@st.cache_data` usages | 0 |

---

## 2. Repository Inventory

| Repository | File | Managed State | Purpose |
|---|---|---|---|
| `SessionRepository` | `src/core/state/repositories/session_repository.py` | All sub-repos; lifecycle | **Aggregate root**: coordinates all repositories, handles initialization and session restore |
| `DataRepository` | `src/core/state/repositories/data_repository.py` | `_data`, `_processed_data` | Primary and processed DataFrames |
| `PlotRepository` | `src/core/state/repositories/plot_repository.py` | `_plots`, `_plot_counter`, `_current_plot_id` | Plot objects, counter, active selection |
| `ConfigRepository` | `src/core/state/repositories/config_repository.py` | `_config`, `_temp_dir`, `_csv_path`, `_csv_pool`, `_saved_configs` | Application config, file paths, CSV pool |
| `ParserStateRepository` | `src/core/state/repositories/parser_state_repository.py` | `_parse_variables`, `_stats_path`, `_stats_pattern`, `_scanned_variables`, `_use_parser`, `_parser_strategy`, `_simulator` | Parser configuration and scanned variables |
| `PreviewRepository` | `src/core/state/repositories/preview_repository.py` | `_previews` (dict[str, DataFrame]) | Temporary preview DataFrames for manager operations |
| `HistoryRepository` | `src/core/state/repositories/history_repository.py` | `_manager_history`, `_portfolio_history` | Operation audit trail (rolling + unbounded) |
| `VisualizationRepository` | `src/core/state/repositories/visualization_repository.py` | `_configs` (dict[int, FigureConfig]) | Per-plot FigureConfig for rendering |

---

## 3. Repository Detail Catalog

### 3.1 SessionRepository (Aggregate Root)

- **File**: `src/core/state/repositories/session_repository.py`
- **Purpose**: Owns all sub-repository instances; provides session-level lifecycle operations.
- **Storage**: Holds references to all other repositories as public attributes.

**Owned Sub-Repositories:**

| Attribute | Type |
|---|---|
| `data_repo` | `DataRepository` |
| `plot_repo` | `PlotRepository` |
| `parser_repo` | `ParserStateRepository` |
| `config_repo` | `ConfigRepository` |
| `preview_repo` | `PreviewRepository` |
| `history_repo` | `HistoryRepository` |
| `visualization_repo` | `VisualizationRepository` |

**Constructor Injection:**

| Parameter | Type | Purpose |
|---|---|---|
| `plot_deserializer` | `PlotDeserializer \| None` | Callable to convert dict -> PlotProtocol during portfolio restore (avoids core->web import) |

**Methods:**

| Method | Parameters | Return | Description |
|---|---|---|---|
| `initialize_session` | `()` | `None` | Ensures clean defaults; only writes data if no data exists |
| `clear_widget_state` | `()` | `None` | No-op placeholder (widget state no longer managed here) |
| `restore_from_portfolio` | `(portfolio_data: PortfolioData)` | `None` | Restores full session from portfolio JSON data |
| `clear_all` | `()` | `None` | Clears every sub-repository to pristine state |

**`restore_from_portfolio` Flow:**
1. Calls `clear_widget_state()` (no-op)
2. Restores parser state (variables, path, pattern, scanned vars, use_parser flag)
3. Restores config state (csv_path, config dict)
4. Deserializes `data_csv` string -> DataFrame via `pd.read_csv(io.StringIO(...))`
5. Deserializes plots via injected `plot_deserializer` callable
6. Restores plot counter
7. Restores both manager and portfolio history lists

---

### 3.2 DataRepository

- **File**: `src/core/state/repositories/data_repository.py`
- **Purpose**: Primary and processed dataset storage.
- **Storage**: Two private `pd.DataFrame | None` attributes.

**Internal State:**

| Field | Type | Default | Description |
|---|---|---|---|
| `_data` | `pd.DataFrame \| None` | `None` | Raw/primary dataset |
| `_processed_data` | `pd.DataFrame \| None` | `None` | Post-shaper/transformation dataset |

**Methods:**

| Method | Parameters | Return | Description |
|---|---|---|---|
| `get_data` | `()` | `DataFrame \| None` | Retrieve primary dataset |
| `set_data` | `(data, on_change?)` | `None` | Store primary dataset; executes optional callback |
| `get_processed_data` | `()` | `DataFrame \| None` | Retrieve processed dataset |
| `set_processed_data` | `(data)` | `None` | Store processed dataset |
| `has_data` | `()` | `bool` | True if primary data is non-None and non-empty |
| `clear_data` | `()` | `None` | Sets both to None |

**Written By**: `ApplicationAPI.load_data()`, `DataSourceComponents`, all DataManagers (via `DataManager.set_data()`), `SessionRepository.restore_from_portfolio()`
**Read By**: `ApplicationAPI.get_current_view()`, all DataManagers (via `DataManager.get_data()`), `PlotRenderController`, pipeline controllers

---

### 3.3 PlotRepository

- **File**: `src/core/state/repositories/plot_repository.py`
- **Purpose**: Plot collection and lifecycle tracking.
- **Storage**: List of PlotProtocol instances + counter + current ID.

**Internal State:**

| Field | Type | Default | Description |
|---|---|---|---|
| `_plots` | `list[PlotProtocol]` | `[]` | All active plot objects |
| `_plot_counter` | `int` | `0` | Monotonic counter for plot ID generation |
| `_current_plot_id` | `int \| None` | `None` | Currently selected/active plot |

**Methods:**

| Method | Parameters | Return | Description |
|---|---|---|---|
| `get_plots` | `()` | `list[PlotProtocol]` | Get all plots |
| `set_plots` | `(plots)` | `None` | Replace entire plot list |
| `add_plot` | `(plot)` | `None` | Append a plot |
| `remove_plot` | `(plot_id: int)` | `bool` | Remove by ID; returns success |
| `clear_plots` | `()` | `None` | Empty the list |
| `get_plot_counter` | `()` | `int` | Current counter value |
| `set_plot_counter` | `(counter)` | `None` | Set counter |
| `increment_plot_counter` | `()` | `int` | Returns current then increments |
| `get_current_plot_id` | `()` | `int \| None` | Active plot ID |
| `set_current_plot_id` | `(plot_id)` | `None` | Set active plot |

**Written By**: `PlotService.create_plot()`, `PlotService.delete_plot()`, `PlotService.duplicate_plot()`, `SessionRepository.restore_from_portfolio()`, `RepositoryStateManager.clear_data()`
**Read By**: `PlotCreationController`, `PortfolioService.save_portfolio()`

---

### 3.4 ConfigRepository

- **File**: `src/core/state/repositories/config_repository.py`
- **Purpose**: Application configuration, file paths, CSV pool, saved configs.
- **Storage**: Dict + strings + two lists.

**Internal State:**

| Field | Type | Default | Description |
|---|---|---|---|
| `_config` | `dict[str, Any]` | `{}` | Generic configuration dictionary |
| `_temp_dir` | `str \| None` | `None` | Temporary directory for parsing output |
| `_csv_path` | `str \| None` | `None` | Path to current CSV file |
| `_csv_pool` | `list[CsvPoolEntry]` | `[]` | List of available CSV files |
| `_saved_configs` | `list[SavedConfigEntry]` | `[]` | Saved configuration entries |

**Methods:**

| Method | Parameters | Return | Description |
|---|---|---|---|
| `get_config` | `()` | `dict[str, Any]` | Full config dict |
| `set_config` | `(config)` | `None` | Replace config |
| `update_config` | `(key, value)` | `None` | Update single key |
| `get_config_value` | `(key, default?)` | `object` | Get single value |
| `clear_config` | `()` | `None` | Reset to empty dict |
| `get_temp_dir` / `set_temp_dir` | `(path)` | `str \| None / None` | Temp dir management (idempotent set) |
| `get_csv_path` / `set_csv_path` | `(path)` | `str \| None / None` | CSV path management (idempotent set) |
| `get_csv_pool` / `set_csv_pool` | `(pool)` | `list / None` | CSV pool registry |
| `get_saved_configs` / `set_saved_configs` | `(configs)` | `list / None` | Saved configs list |

**Written By**: `ApplicationAPI.load_data()`, `DataSourceComponents`, `SessionRepository.restore_from_portfolio()`, `RepositoryStateManager.clear_data()`
**Read By**: `ApplicationAPI.get_current_view()`, `DataSourceComponents.render_csv_pool()`, `PortfolioService.save_portfolio()`

---

### 3.5 ParserStateRepository

- **File**: `src/core/state/repositories/parser_state_repository.py`
- **Purpose**: Simulator parser configuration and scanning state.
- **Storage**: Multiple typed private attributes with defaults.

**Internal State:**

| Field | Type | Default | Description |
|---|---|---|---|
| `_parse_variables` | `list[ParseVariableConfig]` | 3 default vars (simTicks, benchmark_name, config_description) | Variables to extract from stats |
| `_stats_path` | `str` | `"/path/to/stats"` | Base directory for stats files |
| `_stats_pattern` | `str` | `"stats.txt"` | Filename pattern |
| `_scanned_variables` | `list[ScannedVariableDict]` | `[]` | Auto-discovered variables |
| `_use_parser` | `bool` | `False` | Parser mode enabled flag |
| `_parser_strategy` | `str` | `"simple"` | Strategy: "simple" or "config_aware" |
| `_simulator` | `str` | `"gem5"` | Active simulator backend |

**Default Parse Variables:**
```python
[
    {"name": "simTicks", "type": "scalar", "_id": "<uuid>"},
    {"name": "benchmark_name", "type": "configuration", "_id": "<uuid>"},
    {"name": "config_description", "type": "configuration", "_id": "<uuid>"},
]
```

**Methods:**

| Method | Parameters | Return | Description |
|---|---|---|---|
| `get_parse_variables` / `set_parse_variables` | `(variables)` | `list / None` | Variable configs (auto-assigns UUIDs) |
| `add_parse_variable` | `(variable)` | `None` | Append single variable |
| `remove_parse_variable` | `(variable_id)` | `bool` | Remove by UUID |
| `get_stats_path` / `set_stats_path` | `(path)` | `str / None` | Stats directory (idempotent) |
| `get_stats_pattern` / `set_stats_pattern` | `(pattern)` | `str / None` | Filename pattern (idempotent) |
| `get_scanned_variables` / `set_scanned_variables` | `(variables)` | `list / None` | Scanned vars |
| `is_using_parser` / `set_using_parser` | `(use_parser)` | `bool / None` | Parser flag (idempotent) |
| `get_parser_strategy` / `set_parser_strategy` | `(strategy)` | `str / None` | Strategy (normalized to lowercase, idempotent) |
| `get_simulator` / `set_simulator` | `(simulator)` | `str / None` | Simulator backend (idempotent) |
| `clear_parser_state` | `()` | `None` | Resets scanned vars and use_parser flag |

**Written By**: `DataSourceComponents.render_parser_config()`, `VariableEditor`, `SessionRepository.restore_from_portfolio()`
**Read By**: `DataSourceComponents`, `RepositoryStateManager.set_data()` (reads variables for type enforcement), `PortfolioService.save_portfolio()`

---

### 3.6 PreviewRepository

- **File**: `src/core/state/repositories/preview_repository.py`
- **Purpose**: Temporary preview DataFrames for "try-then-confirm" workflow.
- **Storage**: `dict[str, DataFrame]` keyed by operation name.

**Internal State:**

| Field | Type | Default | Description |
|---|---|---|---|
| `_previews` | `dict[str, DataFrame]` | `{}` | Operation name -> preview data |

**Known Operation Keys:**
- `"preprocessor"` -- PreprocessorManager preview
- `"seeds_reduction"` -- SeedsReducerManager preview
- `"outlier_removal"` -- OutlierRemoverManager preview
- `"mixer"` -- MixerManager preview

**Methods:**

| Method | Parameters | Return | Description |
|---|---|---|---|
| `set_preview` | `(operation_name, data)` | `None` | Store preview (validates non-empty name, non-None data) |
| `get_preview` | `(operation_name)` | `DataFrame \| None` | Retrieve preview |
| `has_preview` | `(operation_name)` | `bool` | Check existence |
| `clear_preview` | `(operation_name)` | `None` | Remove single preview |
| `clear_all_previews` | `()` | `int` | Remove all; returns count |
| `list_active_previews` | `()` | `list[str]` | List active operation keys |

**Written By**: All four DataManagers (preprocessor, seeds_reducer, outlier_remover, mixer)
**Read By**: Same DataManagers (to check if preview exists and to retrieve for confirmation)

---

### 3.7 HistoryRepository

- **File**: `src/core/state/repositories/history_repository.py`
- **Purpose**: Operation audit trail in two independent lists.
- **Storage**: Two `list[OperationRecord]` with different retention policies.

**Internal State:**

| Field | Type | Default | Cap | Description |
|---|---|---|---|---|
| `_manager_history` | `list[OperationRecord]` | `[]` | 10 (FIFO eviction) | Rolling window of recent operations |
| `_portfolio_history` | `list[OperationRecord]` | `[]` | Unbounded | Complete audit trail |

**OperationRecord TypedDict Fields:**
- `source_columns: list[str]`
- `dest_columns: list[str]`
- `operation: str`
- `timestamp: str` (ISO 8601)

**Methods:**

| Method | Parameters | Return | Description |
|---|---|---|---|
| `get_manager_history` | `()` | `list[OperationRecord]` | Returns copy |
| `add_manager_record` | `(record)` | `None` | Append with FIFO eviction at 10 |
| `set_manager_history` | `(records)` | `None` | Bulk-set (portfolio restore) |
| `clear_manager_history` | `()` | `None` | Clear all |
| `get_portfolio_history` | `()` | `list[OperationRecord]` | Returns copy |
| `add_portfolio_record` | `(record)` | `None` | Append (no cap) |
| `set_portfolio_history` | `(records)` | `None` | Bulk-set (portfolio restore) |
| `clear_portfolio_history` | `()` | `None` | Clear all |
| `remove_manager_record` | `(record)` | `None` | Remove first match |
| `remove_portfolio_record` | `(record)` | `None` | Remove first match |
| `clear_all` | `()` | `None` | Clears both lists |

**Written By**: `ApplicationAPI.add_manager_history_record()` (writes to both lists simultaneously), each DataManager on confirm
**Read By**: `HistoryComponents.render_manager_history()`, `HistoryComponents.render_global_history()`, `PortfolioService.save_portfolio()`

---

### 3.8 VisualizationRepository

- **File**: `src/core/state/repositories/visualization_repository.py`
- **Purpose**: Per-plot FigureConfig storage for rendering pipeline.
- **Storage**: `dict[int, FigureConfig]` keyed by plot ID.

**Internal State:**

| Field | Type | Default | Description |
|---|---|---|---|
| `_configs` | `dict[int, FigureConfig]` | `{}` | Plot ID -> FigureConfig |

**Methods:**

| Method | Parameters | Return | Description |
|---|---|---|---|
| `get_config` | `(plot_id)` | `FigureConfig \| None` | Retrieve config for plot |
| `set_config` | `(plot_id, config)` | `None` | Store/replace config |
| `remove_config` | `(plot_id)` | `None` | Remove config (no-op if absent) |
| `has_config` | `(plot_id)` | `bool` | Check existence |
| `get_all` | `()` | `dict[int, FigureConfig]` | Shallow copy of all configs |
| `clear` | `()` | `None` | Remove all configs |

**Written By**: `ApplicationAPI.set_visualization_config()`
**Read By**: `ApplicationAPI.get_visualization_config()`

---

## 4. Session State Key Registry

### 4.1 UIStateManager-Managed Keys (Namespaced)

All keys below are accessed through `UIStateManager` typed accessors. The
namespace prefix system prevents collisions.

#### Plot UI State (`_PlotUIState`) -- Prefix: `plot.{plot_id}.`

| Key Pattern | Type | Default | Read By | Written By |
|---|---|---|---|---|
| `plot.{id}.auto_refresh` | `bool` | `True` | `PlotRenderController` | `PlotRenderController` |
| `plot.{id}.dialog.save` | `bool` | `False` | -- | -- |
| `plot.{id}.dialog.load` | `bool` | `False` | -- | -- |
| `plot.{id}.order.{type}` | `list[Any] \| None` | `None` | Ordering components | Ordering components |
| `plot.{id}.edit_shapes` | `bool` | `False` | `ShapesSettings` | `ShapesSettings` |
| `plot.pending_updates` | `dict[str, Any] \| None` | `None` | `manage_plots.py` | `PlotRenderController` (relayout events) |

#### Manager UI State (`_ManagerUIState`) -- Prefix: `manager.{name}.`

| Key Pattern | Type | Default | Read By | Written By |
|---|---|---|---|---|
| `manager.{name}.load_trigger` | `dict[str, Any] \| None` | `None` | Each DataManager's `render()` | `HistoryComponents.render_manager_history()` |
| `manager.{name}.form.{field}` | `Any` | `None` | -- | -- |

#### Navigation UI State (`_NavUIState`) -- Prefix: `nav.`

| Key Pattern | Type | Default | Read By | Written By |
|---|---|---|---|---|
| `nav.current_page` | `str \| None` | `None` | -- | -- |
| `nav.current_tab` | `str \| None` | `None` | -- | -- |

#### Export UI State (`_ExportUIState`) -- Prefix: `export.`

| Key Pattern | Type | Default | Read By | Written By |
|---|---|---|---|---|
| `export.last_path` | `str` | `""` | -- | -- |

### 4.2 Direct `st.session_state` Keys (Outside UIStateManager)

These keys are accessed directly on `st.session_state` without going through
`UIStateManager`. They fall into several categories:

#### Application Bootstrap Keys

| Key | Type | Default | File | Purpose |
|---|---|---|---|---|
| `api` | `ApplicationAPI` | (set by `app.py`) | `app.py:59` | Global API singleton reference |
| `_nav_page` | `str` | `"Data Source"` | `app.py:76` | Current navigation page |

#### Engine Manager Key

| Key | Type | Default | File | Purpose |
|---|---|---|---|---|
| `ring5_engine_mode` | `Literal["plotly","matplotlib"]` | `"plotly"` | `src/web/rendering/engine_manager.py` | Active visualization engine |

#### Chart Display / Rendering Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `plot.{id}.mpl_fig` | `matplotlib.Figure \| None` | `chart_display.py` | Cached matplotlib figure for download |
| `plot.{id}.last_relayout` | `dict[str, Any]` | `render_controller.py` | Last relayout event (dedup guard) |

#### Plot Config Widget Sanitization Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `x_filter_{plot_id}` | `list[str]` | `plot_config_components.py` | X-axis filter multiselect state |
| `group_filter_{plot_id}` | `list[str]` | `plot_config_components.py` | Group filter multiselect state |
| `y_multiselect_{plot_id}` | `list[str]` | `plot_config_components.py` | Y-columns multiselect state |
| `hm_metrics_{plot_id}` | `list[str]` | `heatmap_config.py` | Heatmap metrics multiselect state |

#### Color/Shape Editing Widget Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `{prefix}clr_{plot_id}_{hash}` | `str` (hex color) | `colors_settings.py`, `base_ui.py` | Color picker state |
| `{prefix}ov_{plot_id}_{hash}` | `bool` | `colors_settings.py`, `base_ui.py` | Color override toggle |
| `edit_shapes_{plot_id}` | `bool` | `shapes_settings.py` | Legacy shape editing flag |

#### Data Manager Widget Keys (via WidgetKeyBuilder)

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `manager.preprocessor.op` | `str` | `preprocessor.py` | Selected operation |
| `manager.preprocessor.src1` | `str` | `preprocessor.py` | Source column 1 |
| `manager.preprocessor.src2` | `str` | `preprocessor.py` | Source column 2 |
| `manager.preprocessor.name` | `str` | `preprocessor.py` | New column name |
| `manager.seeds_reducer.categorical` | `list[str]` | `seeds_reducer.py` | Selected categorical columns |
| `manager.seeds_reducer.numeric` | `list[str]` | `seeds_reducer.py` | Selected numeric columns |
| `manager.outlier_remover.col` | `str` | `outlier_remover.py` | Outlier target column |
| `manager.outlier_remover.groupby` | `list[str]` | `outlier_remover.py` | Group-by columns |
| `manager.mixer.mode` | `str` | `mixer.py` | Mixer mode selection |
| `manager.mixer.select_cols` | `list[str]` | `mixer.py` | Selected columns to merge |
| `manager.mixer.new_name` | `str` | `mixer.py` | New column name |
| `manager.mixer.op` | `str` | `mixer.py` | Selected operation |

#### Reorderable List Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `{prefix}_order_{plot_id}` | `list[str]` | `reorderable_list.py` | Item ordering state |

#### Filtered Selector Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `{key}__selections` | `set[str]` | `filtered_selector.py` | Persistent multiselect selections |
| `{key}__search` | `str` | `filtered_selector.py` | Search filter text |

#### Split-Apply Config Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `{key_base}_step_count` | `int` | `split_apply_config.py` | Number of shaper sub-steps |

#### Variable Editor Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `dist_range_result_{var_id}` | `dict` (minimum, maximum) | `variable_editor.py` | Distribution range discovery result |

#### Data Source Widget Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `stats_path_input` | `str` | `data_source_components.py` | Stats path text input value |
| `stats_pattern_input` | `str` | `data_source_components.py` | Stats pattern text input value |
| `simulator_selector` | `str` | `data_source_components.py` | Simulator pills selection |
| `parser_strategy_selector` | `str` | `data_source_components.py` | Strategy segmented control |

#### Data Visualization/Table Keys

| Key Pattern | Type | File | Purpose |
|---|---|---|---|
| `page_num` | `int` | `data_manager_components.py` | Current page number for pagination |
| `search_col` | `str` | `data_manager_components.py` | Search-in-column selection |
| `search_term` | `str` | `data_manager_components.py` | Search text |
| `display_cols` | `list[str]` | `data_manager_components.py` | Selected display columns |
| `rows_per_page` | `int \| str` | `data_manager_components.py` | Rows per page setting |

---

## 5. State Initialization Flow

### 5.1 Application Bootstrap Sequence

```
User opens browser -> Streamlit executes app.py:run_app()
   |
   +-- st.set_page_config(...)          # Page metadata
   |
   +-- @st.cache_resource get_api()     # SINGLETON: created once per session
   |     |
   |     +-- ApplicationAPI.__init__()
   |           |
   |           +-- RepositoryStateManager.__init__()
   |           |     |
   |           |     +-- SessionRepository.__init__(plot_deserializer=BasePlot.from_dict)
   |           |           |
   |           |           +-- DataRepository()          -> _data=None, _processed_data=None
   |           |           +-- PlotRepository()          -> _plots=[], _counter=0, _current=None
   |           |           +-- ParserStateRepository()   -> defaults (3 vars, gem5, simple)
   |           |           +-- ConfigRepository()        -> empty dict, None paths
   |           |           +-- PreviewRepository()       -> empty dict
   |           |           +-- HistoryRepository()       -> empty lists
   |           |           +-- VisualizationRepository() -> empty dict
   |           |
   |           +-- DefaultServicesAPI(state_manager)     # Wire services
   |           +-- SimulatorRegistry.get_parser("gem5")  # Default parser
   |
   +-- st.session_state.api = api       # Store reference for direct access
   |
   +-- st.session_state["_nav_page"] = "Data Source"  (if not already set)
   |
   +-- Render sidebar navigation
   |
   +-- Render active page (lazy import)
```

### 5.2 Per-Rerun Flow

On every Streamlit rerun:
1. `get_api()` returns the cached `ApplicationAPI` (no re-creation)
2. `st.session_state.api = api` re-assigns the same object reference
3. Navigation state read from `st.session_state["_nav_page"]`
4. Active page module is lazily imported and rendered
5. Page creates `UIStateManager()` (lightweight; just instantiates sub-manager objects)
6. Pages/controllers read domain state via `api.state_manager.*` methods

### 5.3 Why State Survives Reruns

The `ApplicationAPI` (and its entire `RepositoryStateManager` tree) is created
via `@st.cache_resource`.  Streamlit's cache_resource stores the object
reference in a global cache keyed by function signature.  On reruns, the same
Python object is returned, preserving all in-memory repository state without
any serialization.

---

## 6. State Lifecycle Patterns

### 6.1 Data Lifecycle

```
[No Data]
    |
    v
  Load CSV (file or pool)  -or-  Parse Stats Files  -or-  Restore Portfolio
    |                              |                        |
    v                              v                        v
  api.load_data(csv_path)    DataSourceComponents     api.state_manager.restore_session()
    |                         finalize_parsing()          |
    v                              |                      v
  data_repo.set_data(df)          v                  data_repo.set_data(df)
  config_repo.set_csv_path()   api.load_csv_file()     (from data_csv string)
    |                         data_repo.set_data()
    v                              |
  [Data Loaded] <------------------+
    |
    v (Data Managers apply transformations)
  PreprocessorManager.render() -> preview_repo.set_preview("preprocessor", df)
    |                                         |
    v (user confirms)                         v
  data_repo.set_data(confirmed_df)      preview_repo.clear_preview("preprocessor")
  history_repo.add_manager_record()
  history_repo.add_portfolio_record()
    |
    v
  [Data Transformed]
    |
    v (Clear Data button in sidebar)
  api.reset_session() -> state_manager.clear_data() + clear_all()
    |
    v
  [No Data]
```

### 6.2 Plot Lifecycle

```
[No Plots]
    |
    v
  PlotCreationController.render_create_section()
    |
    v
  PlotService.create_plot(name, type, state_manager)
    |
    +-- plot_repo.increment_plot_counter()   -> returns new ID
    +-- PlotFactory.create(type, id, name)   -> BasePlot instance
    +-- plot_repo.add_plot(plot)
    +-- plot_repo.set_current_plot_id(id)
    |
    v
  [Plot Created]
    |
    v (User configures pipeline + config)
  PipelineController.render() -> plot.pipeline updated
  PlotRenderController.render() -> plot.config updated
    |
    v (User deletes)
  PlotService.delete_plot(id, state_manager)
    +-- plot_repo.remove_plot(id)
    +-- visualization_repo.remove_config(id)
    +-- ui_state.plot.cleanup(id)   <- removes all plot.{id}.* session_state keys
    |
    v
  [Plot Deleted]
```

### 6.3 Preview Lifecycle (Try-Then-Confirm)

```
  User clicks "Preview" in a DataManager
    |
    v
  Manager computes result DataFrame
  preview_repo.set_preview("manager_name", result_df)
    |
    v
  [Preview Active] -- UI shows preview + "Confirm" button
    |
    +-- User clicks "Confirm":
    |     data_repo.set_data(confirmed_df)
    |     preview_repo.clear_preview("manager_name")
    |     history_repo.add_*_record(...)
    |     st.rerun()
    |
    +-- User navigates away: preview persists in memory
    |     but is not applied to data
```

### 6.4 History Lifecycle

```
  DataManager confirms an operation
    |
    v
  api.add_manager_history_record(record)
    |
    +-- history_repo.add_manager_record(record)   # FIFO cap at 10
    +-- history_repo.add_portfolio_record(record)  # Unbounded
    |
    v
  [Record in both lists]
    |
    +-- User clicks "Load" in history:
    |     st.session_state[manager.{name}.load_trigger] = record
    |     -> next rerun: manager.consume_load_trigger() reads & pops it
    |     -> manager pre-fills widgets from record data
    |
    +-- User clicks "Delete":
    |     api.remove_manager_history_record(record)
    |     -> removes from BOTH manager and portfolio history
    |
    +-- Session clear:
    |     history_repo.clear_all()
```

---

## 7. Caching Strategy

### 7.1 Streamlit Cache Decorators

| Decorator | Location | What is Cached | Scope | TTL |
|---|---|---|---|---|
| `@st.cache_resource` | `app.py:54-56` `get_api()` | `ApplicationAPI` singleton (and entire repository tree) | Per-session (until session ends or server restart) | Infinite |

There are **zero** uses of `@st.cache_data` in the entire codebase.

### 7.2 Custom In-Memory Caches

| Cache | Location | Type | Max Size | TTL | Purpose |
|---|---|---|---|---|---|
| `_plot_cache` | `src/core/performance.py:97` | `SimpleCache` | 32 entries | 300s (5 min) | Caches generated Plotly figures by config+data hash |

**Plot Cache Key Generation** (`PlotRenderController._compute_figure_cache_key`):
- Input: `plot_id`, `config` (excluding transient axis ranges), `data_hash`
- `data_hash` uses shape + first/last row + column list (fast O(1) check)
- Key format: `"plot_{id}_{config_md5_8chars}_{data_md5_12chars}"`

**Cache Hit Path**:
1. On render, if `should_generate=False` and `plot.last_generated_fig is None`:
   - Try `cache.get(cache_key)` -- if hit, assign to `plot.last_generated_fig`
2. If still None or `should_generate=True`: regenerate and `cache.set(cache_key, fig)`

### 7.3 Cached Shaper Decorator

The `@cached` decorator from `src/core/performance.py` is available for use
by shaper services (e.g., mean, normalize transformations) using
`compute_data_fingerprint()` as the key function.  This avoids re-running
expensive DataFrame transformations when input data and params are unchanged.

---

## 8. State Serialization (Portfolio Save/Restore)

### 8.1 PortfolioData TypedDict

Defined in `src/core/models/portfolio_models.py`:

```python
class PortfolioData(TypedDict, total=False):
    parse_variables: list[ParseVariableConfig]
    stats_path: str
    stats_pattern: str
    csv_path: str
    use_parser: bool
    scanned_variables: list[ScannedVariableDict]
    data_csv: str                               # CSV string
    plots: list[dict[str, Any]]                 # Serialized plot dicts
    plot_counter: int
    config: dict[str, Any]
    shapers: list[ShaperStepConfig]
    manager_history: list[OperationRecord]
    portfolio_history: list[OperationRecord]
```

### 8.2 Save Flow

```
portfolio.py -> "Save Portfolio" button
  |
  v
PortfolioService.save_portfolio(
    name, data, plots, config, plot_counter, csv_path, parse_variables,
    figure_spec_enricher=_build_figure_spec   # Injected from web layer
)
  |
  +-- For each plot:
  |     plot.to_dict()                         # Serialize plot
  |     figure_spec_enricher(config, type)     # Build FigureConfig dict
  |     plot_dict["figure_spec"] = spec_dict   # Attach to plot
  |
  +-- data.to_csv(index=False) -> data_csv     # DataFrame -> CSV string
  |
  +-- Read from state_manager:
  |     stats_path, stats_pattern, scanned_variables
  |     manager_history, portfolio_history
  |
  +-- Assemble portfolio_data dict
  |     schema_version, version, timestamp, ...
  |
  +-- json.dump(portfolio_data, file)          # Write to disk
  |     Location: <portfolios_dir>/<sanitized_name>.json
```

### 8.3 Restore Flow

```
portfolio.py -> "Load Portfolio" button
  |
  v
PortfolioService.load_portfolio(name)
  +-- json.load(file)                          # Raw dict from disk
  +-- PortfolioMigrator.migrate(raw)           # Schema migration
  +-- return PortfolioData
  |
  v
api.state_manager.restore_session(data)
  -> SessionRepository.restore_from_portfolio(portfolio_data)
      |
      +-- parser_repo.set_parse_variables(...)
      +-- parser_repo.set_stats_path(...)
      +-- parser_repo.set_stats_pattern(...)
      +-- parser_repo.set_scanned_variables(...)
      +-- parser_repo.set_using_parser(...)
      |
      +-- config_repo.set_csv_path(...)
      +-- config_repo.set_config(...)
      |
      +-- pd.read_csv(io.StringIO(data_csv)) -> df
      +-- data_repo.set_data(df)
      |
      +-- For each plot dict:
      |     plot_deserializer(plot_data) -> PlotProtocol
      +-- plot_repo.set_plots(loaded_plots)
      +-- plot_repo.set_plot_counter(...)
      |
      +-- history_repo.set_manager_history(...)
      +-- history_repo.set_portfolio_history(...)
  |
  v
st.rerun(scope="app")   <- Full page rerun to reflect restored state
```

### 8.4 What is NOT Serialized

- **UI State** (`plot.*.auto_refresh`, `manager.*.load_trigger`, etc.) -- transient
- **Preview DataFrames** -- temporary
- **Visualization configs** (`VisualizationRepository`) -- rebuilt from plot config on render
- **Processed data** -- rebuilt by running the pipeline
- **Matplotlib figure objects** -- recreated on render
- **Plot figure cache** (`_plot_cache`) -- regenerated on demand

---

## 9. Cross-Component State Access

### 9.1 Pages and Their State Access Patterns

| Page / Component | Domain State Read (via API) | Domain State Written (via API) | UI State (session_state) |
|---|---|---|---|
| `app.py` | `api.get_current_view()` | `api.reset_session()` | `_nav_page`, `api` |
| `data_source.py` | data, csv_pool, parser config, scanned vars | data, csv_path, parser config, scanned vars, temp_dir | `stats_path_input`, `stats_pattern_input`, `simulator_selector`, `parser_strategy_selector` |
| `data_managers.py` | data (via DataManager.get_data()) | data (via DataManager.set_data()), previews, history | `manager.{name}.*` keys |
| `manage_plots.py` | plots, current_plot_id, processed_data, config | plots, current_plot_id, visualization config | `plot.{id}.*`, `plot.pending_updates`, `ring5_engine_mode`, filter keys |
| `portfolio.py` | data, plots, config, plot_counter, csv_path, parse_variables, history | full session restore | `portfolio_save_name`, `portfolio_load_select` |

### 9.2 Controller State Access

| Controller | Domain State Read | Domain State Written | UI State |
|---|---|---|---|
| `PlotCreationController` | plots, plot_counter, current_plot_id | plots, current_plot_id (via lifecycle adapter) | -- |
| `PipelineController` | plot.pipeline, data | plot.processed_data, plot.pipeline | -- |
| `PlotRenderController` | processed_data, config, visualization_config | config, visualization_config, figure cache | `plot.{id}.auto_refresh`, `plot.{id}.last_relayout`, `ring5_engine_mode` |

### 9.3 Component State Access

| Component | session_state Keys Written | session_state Keys Read |
|---|---|---|
| `ChartDisplayComponent` | `plot.{id}.mpl_fig` | `plot.{id}.mpl_fig` |
| `EngineManager` | `ring5_engine_mode` | `ring5_engine_mode` |
| `filtered_selector` | `{key}__selections`, `{key}__search`, `{key}` | Same |
| `reorderable_list` | `{prefix}_order_{plot_id}` | Same |
| `HistoryComponents` | `{load_session_key}` (via on_click) | -- |
| `PreprocessorManager` | `manager.preprocessor.*` | `manager.preprocessor.load_trigger` |
| `SeedsReducerManager` | `manager.seeds_reducer.*` | `manager.seeds_reducer.load_trigger` |
| `OutlierRemoverManager` | `manager.outlier_remover.*` | `manager.outlier_remover.load_trigger` |
| `MixerManager` | `manager.mixer.*` | `manager.mixer.load_trigger` |
| `SplitApplyConfig` | `{key_base}_step_count` | Same |
| `PlotConfigComponents` | `x_filter_*`, `group_filter_*`, `y_multiselect_*` | Same (sanitization) |
| `HeatmapConfig` | `hm_metrics_*` | Same (sanitization) |
| `ColorsSettings` / `base_ui` | color picker/override keys | Same |
| `ShapesSettings` | -- | `edit_shapes_{plot_id}` |
| `VariableEditor` | `dist_range_result_{var_id}` | Same |
| `DataSourceComponents` | -- | `stats_path_input`, `stats_pattern_input` |
| `DataManagerComponents` | -- | `page_num`, `search_col`, `search_term`, `display_cols`, `rows_per_page` |

---

## 10. State Dependency Graph

```
+--------------------------------------------------------------------------+
|                         STREAMLIT SESSION                                 |
|                                                                          |
|  st.session_state.api  ───────────────────────────────────────┐          |
|  st.session_state["_nav_page"]                                |          |
|  st.session_state["ring5_engine_mode"]                        |          |
|  st.session_state["plot.{id}.*"]    (UIStateManager)          |          |
|  st.session_state["manager.{name}.*"]                         |          |
|  st.session_state["nav.*"]                                    |          |
|  st.session_state["export.*"]                                 |          |
|  st.session_state[widget keys...]                             |          |
+--------------------------------------------------------------|----------+
                                                                |
              +-------------------------------------------------+
              |
              v
+----------------------------+         +---------------------------+
|      ApplicationAPI        |-------->|   DefaultServicesAPI      |
|  (Singleton via            |         |   .managers -> ManagersAPI|
|   @st.cache_resource)      |         |   .data_services          |
|                            |         |   .shapers -> ShapersAPI  |
|  .state_manager -----------+----+    +---------------------------+
|  ._services                |    |
|  ._parser (SimulationParser)|    |
+----------------------------+    |
                                  |
              +-------------------+
              |
              v
+----------------------------+
| RepositoryStateManager     |
|  (Facade - 46 methods)     |
|                            |
|  ._session_repo -----------+---+
+----------------------------+   |
                                 |
              +------------------+
              |
              v
+----------------------------+
|    SessionRepository       |
|    (Aggregate Root)        |
|                            |
|  .data_repo ───────────────+──> DataRepository
|  .plot_repo ───────────────+──> PlotRepository
|  .parser_repo ─────────────+──> ParserStateRepository
|  .config_repo ─────────────+──> ConfigRepository
|  .preview_repo ────────────+──> PreviewRepository
|  .history_repo ────────────+──> HistoryRepository
|  .visualization_repo ──────+──> VisualizationRepository
|  ._plot_deserializer           (injected callable)
+----------------------------+

+----------------------------+
|  UIStateManager            |
|  (Web Layer Only)          |
|                            |
|  .plot     -> _PlotUIState |----> st.session_state["plot.*"]
|  .manager  -> _ManagerUIState|--> st.session_state["manager.*"]
|  .nav      -> _NavUIState  |---> st.session_state["nav.*"]
|  .export   -> _ExportUIState|--> st.session_state["export.*"]
+----------------------------+

+----------------------------+
|  EngineManager             |
|  (Static, Web Layer)       |
|                            |----> st.session_state["ring5_engine_mode"]
+----------------------------+

+----------------------------+
|  SimpleCache (_plot_cache)  |
|  (Global, Core Layer)      |
|  maxsize=32, ttl=300s      |
+----------------------------+
```

---

## 11. Downstream Dependencies

This analysis feeds into:

| Downstream Document | What It Needs From This Analysis |
|---|---|
| `DEVELOPER_GUIDE_PLAN.md` -> `core/state-management.md` | Full repository catalog, state manager architecture, key registry |
| `AI_KNOWLEDGE_BASE_PLAN.md` -> `architecture/system-overview.md` | Two-tier state overview, singleton bootstrap, dependency graph |
| Step 08 (Web Pages Analysis) | Cross-component state access map (Section 9) |
| Step 15 (Portfolio Analysis) | Save/restore flow details (Section 8) |
| Step 18 (Data Flow Analysis) | State lifecycle patterns (Section 6), initialization flow (Section 5) |
| Step 05 (Services Analysis) | How services interact with state_manager facade |

### Key Architectural Findings

1. **Clean separation**: Domain state (repositories) has zero Streamlit dependency.
   UI state (UIStateManager) is the only layer touching `st.session_state` in a
   structured way.

2. **Residual direct access**: Approximately 45 locations across 16 files still
   access `st.session_state` directly (outside UIStateManager). These are
   primarily in widget sanitization code, component-local state, and the
   `EngineManager`.

3. **Singleton guarantee**: The `@st.cache_resource` on `get_api()` ensures
   exactly one `ApplicationAPI` (and thus one repository tree) per Streamlit
   session. State persists across reruns because the same Python objects are
   reused.

4. **No `@st.cache_data`**: The project does not use Streamlit's data caching
   decorator. DataFrame caching is handled by the repository layer's in-memory
   storage and the custom `SimpleCache` for plot figures.

5. **Idempotent setters**: Many repository setters (csv_path, temp_dir,
   parser_strategy, simulator, etc.) include identity checks to skip writes
   and logging when the value has not changed, reducing noise during Streamlit
   reruns.
