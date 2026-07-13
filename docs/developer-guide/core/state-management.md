---
title: "State Management"
parent: Core
grand_parent: Developer Guide
nav_order: 3
---

# State Management

This guide documents the state management architecture of RING-5 Unified Engine
v2. All application state is organized into a two-tier system that separates
persistent domain state from transient UI state.

---

## 1. Overview

RING-5 uses a **Repository pattern** layered over Streamlit's `session_state`.
Rather than scattering data across dozens of ad-hoc `st.session_state` keys, the
project stores all domain state inside seven in-memory repositories coordinated
by a single `SessionRepository` aggregate root.

### Two-Tier Architecture

| Tier | What It Holds | Where It Lives | Streamlit Dependency |
|------|---------------|----------------|----------------------|
| **Domain State** (Tier 1) | Data, plots, config, parser state, previews, history, visualization configs | Seven repositories inside `SessionRepository` | None -- pure Python |
| **UI State** (Tier 2) | Auto-refresh toggles, dialog visibility, widget ordering, pending updates | `st.session_state` via `UIStateManager` | Direct dependency |

Domain state is owned by `RepositoryStateManager`, which wraps the
`SessionRepository` with a flat facade of 46 methods.  `ApplicationAPI` holds
the `RepositoryStateManager` and is instantiated exactly once per browser
session under `st.session_state.api`.

UI state is accessed exclusively through `UIStateManager`, a lightweight class
with four namespaced sub-managers (`plot`, `manager`, `nav`, `export`).

### Why State Survives Reruns

`app.py` creates `ApplicationAPI` only when the current browser session lacks
the `api` key. On every rerun, the same session-state object is returned without
serialization. All repository state lives in plain Python attributes owned by
that session.

### Key Source Files

| File | Role |
|------|------|
| `src/core/state/state_manager.py` | `StateManager` protocol (interface contract) |
| `src/core/state/repository_state_manager.py` | `RepositoryStateManager` (concrete facade) |
| `src/core/state/repositories/session_repository.py` | `SessionRepository` (aggregate root) |
| `src/core/state/repositories/data_repository.py` | `DataRepository` |
| `src/core/state/repositories/plot_repository.py` | `PlotRepository` |
| `src/core/state/repositories/config_repository.py` | `ConfigRepository` |
| `src/core/state/repositories/parser_state_repository.py` | `ParserStateRepository` |
| `src/core/state/repositories/preview_repository.py` | `PreviewRepository` |
| `src/core/state/repositories/history_repository.py` | `HistoryRepository` |
| `src/core/state/repositories/visualization_repository.py` | `VisualizationRepository` |
| `src/web/state/ui_state_manager.py` | `UIStateManager` (transient UI state) |

---

## 2. SessionRepository -- The Aggregate Root

`SessionRepository` is the top-level coordinator.  It instantiates all seven
child repositories on construction and provides session-level lifecycle
operations: initialization, portfolio restoration, and full cleanup.

```python
class SessionRepository:
    def __init__(self, plot_deserializer: PlotDeserializer | None = None) -> None:
        self.data_repo = DataRepository()
        self.plot_repo = PlotRepository()
        self.parser_repo = ParserStateRepository()
        self.config_repo = ConfigRepository()
        self.preview_repo = PreviewRepository()
        self.history_repo = HistoryRepository()
        self.visualization_repo = VisualizationRepository()
        self._plot_deserializer = plot_deserializer
```

### Owned Sub-Repositories

| Attribute | Type | Managed State |
|-----------|------|---------------|
| `data_repo` | `DataRepository` | Raw and processed DataFrames |
| `plot_repo` | `PlotRepository` | Plot objects, counter, active selection |
| `parser_repo` | `ParserStateRepository` | Variables, patterns, strategies, simulator |
| `config_repo` | `ConfigRepository` | Config dict, CSV path, temp dir, CSV pool |
| `preview_repo` | `PreviewRepository` | Temporary preview DataFrames per operation |
| `history_repo` | `HistoryRepository` | Manager history (rolling) + portfolio history (unbounded) |
| `visualization_repo` | `VisualizationRepository` | Per-plot `FigureConfig` objects |

### Constructor Injection

The `plot_deserializer` parameter accepts a callable (`dict -> PlotProtocol`)
that converts serialized plot dictionaries back into plot objects. This is
injected by the application bootstrap so that the core layer never imports
web-layer classes. During portfolio restoration, this callable deserializes each
stored plot.

### Lifecycle Methods

| Method | Description |
|--------|-------------|
| `initialize_session()` | Ensures clean defaults; only writes data fields if no data exists yet |
| `restore_from_portfolio(portfolio_data)` | Restores full session from a `PortfolioData` dict (parser, config, data, plots, history) |
| `clear_all()` | Resets every sub-repository to its pristine initial state |
| `clear_widget_state()` | No-op placeholder (widget state is managed by the UI layer) |

---

## 3. DataRepository

**File**: `src/core/state/repositories/data_repository.py`

Manages two DataFrames: the raw/primary dataset and a post-transformation
processed dataset.

### Internal State

| Field | Type | Default |
|-------|------|---------|
| `_data` | `pd.DataFrame | None` | `None` |
| `_processed_data` | `pd.DataFrame | None` | `None` |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_data` | `() -> DataFrame | None` | Retrieve the primary dataset |
| `set_data` | `(data, on_change?) -> None` | Store primary dataset; optionally fires a callback |
| `get_processed_data` | `() -> DataFrame | None` | Retrieve the processed (post-shaper) dataset |
| `set_processed_data` | `(data) -> None` | Store the processed dataset |
| `has_data` | `() -> bool` | `True` if primary data is non-None and non-empty |
| `clear_data` | `() -> None` | Sets both fields to `None` |

### Data Lifecycle

1. Data enters via `set_data()` from CSV loading, parser finalization, or
   portfolio restore.
2. The `RepositoryStateManager.set_data()` facade adds a defensive copy and
   enforces type constraints: columns marked as `"configuration"` type in
   parser variables are cast to `str`.
3. Data managers (preprocessor, seeds reducer, outlier remover, mixer) read
   the primary data, transform it, and write results back through `set_data()`.
4. The processed dataset is populated by the shaper pipeline and consumed by
   plot rendering.
5. `clear_data()` resets both slots to `None`.

---

## 4. ConfigRepository

**File**: `src/core/state/repositories/config_repository.py`

Stores the application configuration dictionary, file system paths, the CSV
pool registry, and saved configuration entries.

### Internal State

| Field | Type | Default |
|-------|------|---------|
| `_config` | `dict[str, Any]` | `{}` |
| `_temp_dir` | `str | None` | `None` |
| `_csv_path` | `str | None` | `None` |
| `_csv_pool` | `list[CsvPoolEntry]` | `[]` |
| `_saved_configs` | `list[SavedConfigEntry]` | `[]` |

### Methods

| Method | Description |
|--------|-------------|
| `get_config() / set_config(config)` | Full config dictionary access |
| `update_config(key, value)` | Update a single key |
| `get_config_value(key, default?)` | Retrieve a single value with optional default |
| `clear_config()` | Reset to empty dict |
| `get_temp_dir() / set_temp_dir(path)` | Temp directory management (idempotent setter) |
| `get_csv_path() / set_csv_path(path)` | CSV file path (idempotent setter) |
| `get_csv_pool() / set_csv_pool(pool)` | CSV pool registry |
| `get_saved_configs() / set_saved_configs(configs)` | Saved configurations list |

The `set_temp_dir` and `set_csv_path` setters include identity checks and skip
the write entirely when the value has not changed. This prevents unnecessary
log noise during Streamlit reruns.

---

## 5. ParserStateRepository

**File**: `src/core/state/repositories/parser_state_repository.py`

Manages all configuration for the simulator stats parser: which variables to
extract, file paths and patterns, scanning results, the parsing strategy, and
which simulator backend to target.

### Internal State

| Field | Type | Default |
|-------|------|---------|
| `_parse_variables` | `list[ParseVariableConfig]` | 3 defaults (`simTicks`, `benchmark_name`, `config_description`) |
| `_stats_path` | `str` | `"/path/to/stats"` |
| `_stats_pattern` | `str` | `"stats.txt"` |
| `_scanned_variables` | `list[ScannedVariableDict]` | `[]` |
| `_use_parser` | `bool` | `False` |
| `_parser_strategy` | `str` | `"simple"` |
| `_simulator` | `str` | `"gem5"` |

### Methods

| Method | Description |
|--------|-------------|
| `get_parse_variables() / set_parse_variables(vars)` | Variable config list. The setter auto-assigns UUIDs to entries missing an `_id`. |
| `add_parse_variable(var)` | Append a single variable |
| `remove_parse_variable(var_id)` | Remove by UUID; returns `True` on success |
| `get_stats_path() / set_stats_path(path)` | Stats directory (idempotent) |
| `get_stats_pattern() / set_stats_pattern(pattern)` | Filename pattern (idempotent) |
| `get_scanned_variables() / set_scanned_variables(vars)` | Auto-discovered variables |
| `is_using_parser() / set_using_parser(flag)` | Parser enable/disable (idempotent) |
| `get_parser_strategy() / set_parser_strategy(strategy)` | `"simple"` or `"config_aware"` (normalized to lowercase, idempotent) |
| `get_simulator() / set_simulator(simulator)` | Active simulator backend (idempotent) |
| `clear_parser_state()` | Resets scanned variables and the `use_parser` flag (keeps variables and paths) |

---

## 6. PlotRepository

**File**: `src/core/state/repositories/plot_repository.py`

Manages the ordered collection of plot objects, a monotonic counter for ID
generation, and the currently active plot selection.

### Internal State

| Field | Type | Default |
|-------|------|---------|
| `_plots` | `list[PlotProtocol]` | `[]` |
| `_plot_counter` | `int` | `0` |
| `_current_plot_id` | `int | None` | `None` |

### Methods

| Method | Description |
|--------|-------------|
| `get_plots() / set_plots(plots)` | Full list access and replacement |
| `add_plot(plot)` | Append a plot to the collection |
| `remove_plot(plot_id) -> bool` | Remove by ID; returns success status |
| `clear_plots()` | Empty the collection |
| `get_plot_counter() / set_plot_counter(n)` | Counter value for ID generation |
| `increment_plot_counter() -> int` | Returns current counter then increments (used during plot creation) |
| `get_current_plot_id() / set_current_plot_id(id)` | Active plot tracking (None = no selection) |

### Plot Creation Flow

When a new plot is created via `PlotService.create_plot()`:

1. `plot_repo.increment_plot_counter()` returns and advances the counter.
2. `PlotFactory.create(type, id, name)` produces a `BasePlot` instance.
3. `plot_repo.add_plot(plot)` appends to the list.
4. `plot_repo.set_current_plot_id(id)` activates the new plot.

---

## 7. PreviewRepository

**File**: `src/core/state/repositories/preview_repository.py`

Provides temporary storage for "try-then-confirm" preview DataFrames. Each data
manager can store a preview under a unique operation key, display it to the user,
and either commit it to the primary dataset or discard it.

### Internal State

| Field | Type | Default |
|-------|------|---------|
| `_previews` | `dict[str, DataFrame]` | `{}` |

### Known Operation Keys

| Key | Data Manager |
|-----|-------------|
| `"preprocessor"` | PreprocessorManager |
| `"seeds_reduction"` | SeedsReducerManager |
| `"outlier_removal"` | OutlierRemoverManager |
| `"mixer"` | MixerManager |

### Methods

| Method | Description |
|--------|-------------|
| `set_preview(operation_name, data)` | Store a preview (validates non-empty name, non-None data) |
| `get_preview(operation_name) -> DataFrame | None` | Retrieve a preview |
| `has_preview(operation_name) -> bool` | Check existence |
| `clear_preview(operation_name)` | Remove a single preview |
| `clear_all_previews() -> int` | Remove all previews; returns count cleared |
| `list_active_previews() -> list[str]` | List operation keys with active previews |

### Preview Workflow

```
User clicks "Preview"
  -> Manager computes transformed DataFrame
  -> preview_repo.set_preview("preprocessor", result_df)
  -> UI displays preview + "Confirm" button

User clicks "Confirm"
  -> data_repo.set_data(confirmed_df)
  -> preview_repo.clear_preview("preprocessor")
  -> history records added
  -> st.rerun()
```

---

## 8. HistoryRepository

**File**: `src/core/state/repositories/history_repository.py`

Maintains two independent operation audit trails with different retention
policies.

### Internal State

| Field | Type | Cap | Description |
|-------|------|-----|-------------|
| `_manager_history` | `list[OperationRecord]` | 10 (FIFO eviction) | Rolling window of recent operations |
| `_portfolio_history` | `list[OperationRecord]` | Unbounded | Complete audit trail for portfolio save |

Each `OperationRecord` is a `TypedDict` with fields: `source_columns`,
`dest_columns`, `operation`, and `timestamp` (ISO 8601).

### Methods

| Method | Description |
|--------|-------------|
| `get_manager_history() -> list` | Returns a copy of the manager history |
| `add_manager_record(record)` | Append with FIFO eviction when exceeding cap of 10 |
| `set_manager_history(records)` | Bulk-set (used during portfolio restore) |
| `clear_manager_history()` | Clear the rolling window |
| `get_portfolio_history() -> list` | Returns a copy of the portfolio history |
| `add_portfolio_record(record)` | Append (no cap) |
| `set_portfolio_history(records)` | Bulk-set (used during portfolio restore) |
| `clear_portfolio_history()` | Clear the full trail |
| `remove_manager_record(record)` | Remove first matching entry |
| `remove_portfolio_record(record)` | Remove first matching entry |
| `clear_all()` | Clears both lists |

When a data manager confirms an operation, the `ApplicationAPI` writes the
record to both lists simultaneously. The manager history powers a "Load" feature
that lets users replay a recent operation's parameters.

---

## 9. VisualizationRepository

**File**: `src/core/state/repositories/visualization_repository.py`

Stores per-plot `FigureConfig` objects that control how each plot is rendered.
These are keyed by plot ID and are rebuilt from plot configuration whenever the
rendering pipeline runs.

### Internal State

| Field | Type | Default |
|-------|------|---------|
| `_configs` | `dict[int, FigureConfig]` | `{}` |

### Methods

| Method | Description |
|--------|-------------|
| `get_config(plot_id) -> FigureConfig | None` | Retrieve config for a plot |
| `set_config(plot_id, config)` | Store or replace a config |
| `remove_config(plot_id)` | Remove (no-op if absent) |
| `has_config(plot_id) -> bool` | Check existence |
| `get_all() -> dict[int, FigureConfig]` | Shallow copy of the full map |
| `clear()` | Remove all stored configs |

Visualization configs are **not** serialized to portfolio files. They are
transient rendering state that is rebuilt on each render pass.

---

## 10. State Lifecycle

The application session progresses through a series of states as the user
interacts with it:

```
[Empty] --> [Parsed/Loaded] --> [Managed] --> [Plotted] --> [Saved]
```

### Empty

On first load, the session creates its `ApplicationAPI`. All
repositories initialize with defaults: no data, no plots, counter at zero,
parser disabled, empty histories.

### Parsed / Loaded

Data enters the system through one of three paths:

- **CSV file upload or pool selection**: `api.load_data(csv_path)` reads the CSV,
  stores the DataFrame via `data_repo.set_data()`, and records the path in
  `config_repo.set_csv_path()`.
- **Stats parsing**: The user configures parser variables, stats path, and
  pattern, then triggers parsing. The parser writes output to a temp directory,
  and the resulting DataFrame is loaded the same way.
- **Portfolio restore**: `SessionRepository.restore_from_portfolio()` deserializes
  a CSV string from the portfolio JSON into a DataFrame and restores all
  associated state.

### Phase 3: Managed

Data managers transform the raw dataset through a preview-then-confirm workflow:

1. The user configures a transformation in a data manager UI.
2. Clicking "Preview" stores a preview DataFrame in `preview_repo`.
3. Clicking "Confirm" commits the transform: `data_repo.set_data(result)`,
   clears the preview, and writes history records.

### Phase 4: Plotted

Plots are created by `PlotService` and stored in `plot_repo`. Each plot has
a pipeline configuration and rendering settings. The shaper pipeline transforms
data into `processed_data`, which rendering controllers consume to produce
Plotly or Matplotlib figures.

### Phase 5: Saved

The portfolio system serializes the full session state to a JSON file:
DataFrames become CSV strings, plots become dicts via `to_dict()`, and all
configuration and history are included. The inverse operation,
`restore_from_portfolio()`, reverses this process.

### What Is Not Serialized

- UI state (auto-refresh, dialog flags, pending updates)
- Preview DataFrames
- Visualization configs (rebuilt on render)
- Processed data (rebuilt by running the pipeline)
- Matplotlib figure objects (recreated on render)
- Plot figure cache entries (regenerated on demand)

---

## 11. Session State Keys Catalog

### Domain State (RepositoryStateManager)

Domain state is stored in pure Python attributes on repository objects. It is
**not** stored in `st.session_state` directly.  The only `session_state` entry
for domain state is:

| Key | Type | Description |
|-----|------|-------------|
| `api` | `ApplicationAPI` | This browser session's mutable workspace |

### UIStateManager-Managed Keys

All keys below are accessed through `UIStateManager` typed accessors with
namespace prefixes.

#### Plot UI State -- Prefix: `plot.{plot_id}.`

| Key Pattern | Type | Default |
|-------------|------|---------|
| `plot.{id}.auto_refresh` | `bool` | `True` |
| `plot.{id}.dialog.save` | `bool` | `False` |
| `plot.{id}.dialog.load` | `bool` | `False` |
| `plot.{id}.order.{type}` | `list | None` | `None` |
| `plot.{id}.edit_shapes` | `bool` | `False` |
| `plot.pending_updates` | `dict | None` | `None` |

#### Manager UI State -- Prefix: `manager.{name}.`

| Key Pattern | Type | Default |
|-------------|------|---------|
| `manager.{name}.load_trigger` | `dict | None` | `None` |
| `manager.{name}.form.{field}` | `Any` | `None` |

#### Navigation UI State -- Prefix: `nav.`

| Key Pattern | Type | Default |
|-------------|------|---------|
| `nav.current_page` | `str | None` | `None` |
| `nav.current_tab` | `str | None` | `None` |

#### Export UI State -- Prefix: `export.`

| Key Pattern | Type | Default |
|-------------|------|---------|
| `export.last_path` | `str` | `""` |

### Direct `st.session_state` Keys (Outside UIStateManager)

These keys are accessed directly on `st.session_state` without going through
the UIStateManager. They exist in widget sanitization code, component-local
state, and engine management.

#### Application Bootstrap

| Key | Type | Set In |
|-----|------|--------|
| `api` | `ApplicationAPI` | `app.py` |
| `_nav_page` | `str` | `app.py` |

#### Engine Mode

| Key | Type | Set In |
|-----|------|--------|
| `ring5_engine_mode` | `"plotly" | "matplotlib"` | `engine_manager.py` |

#### Chart Display

| Key Pattern | Type | Purpose |
|-------------|------|---------|
| `plot.{id}.mpl_fig` | `Figure | None` | Cached matplotlib figure for download |
| `plot.{id}.last_relayout` | `dict` | Deduplication guard for relayout events |

#### Widget Sanitization

| Key Pattern | Purpose |
|-------------|---------|
| `x_filter_{plot_id}` | X-axis filter multiselect state |
| `group_filter_{plot_id}` | Group filter multiselect state |
| `y_multiselect_{plot_id}` | Y-columns multiselect state |
| `hm_metrics_{plot_id}` | Heatmap metrics multiselect state |

#### Data Manager Widgets (via WidgetKeyBuilder)

| Key Pattern | Purpose |
|-------------|---------|
| `manager.preprocessor.op` | Selected operation |
| `manager.preprocessor.src1` / `src2` | Source columns |
| `manager.preprocessor.name` | New column name |
| `manager.seeds_reducer.categorical` / `numeric` | Selected columns |
| `manager.outlier_remover.col` / `groupby` | Target and group columns |
| `manager.mixer.mode` / `select_cols` / `new_name` / `op` | Mixer configuration |

#### Other Component Keys

| Key Pattern | Purpose |
|-------------|---------|
| `{prefix}_order_{plot_id}` | Reorderable list item ordering |
| `{key}__selections` / `{key}__search` | Filtered selector persistent state |
| `{key_base}_step_count` | Split-apply config sub-step count |
| `dist_range_result_{var_id}` | Variable editor range discovery result |
| `stats_path_input` / `stats_pattern_input` | Data source text inputs |
| `simulator_selector` / `parser_strategy_selector` | Data source selectors |
| `page_num` / `search_col` / `search_term` / `display_cols` / `rows_per_page` | Data table pagination |

---

## 12. See Also

- **Architecture overview**: For a high-level view of the two-tier state model
  and the singleton bootstrap sequence.
- **Parsing system**: For how parser state flows from `ParserStateRepository`
  through the simulator parser pipeline.
- **Shaper pipeline**: For how `processed_data` is produced from raw data using
  per-plot pipeline configurations.
- **Portfolio system**: For the full save/restore serialization flow including
  `PortfolioData`, `PortfolioMigrator`, and the `PortfolioService`.
- **Plotting system**: For how `PlotRepository` and `VisualizationRepository`
  interact with `PlotRenderController` and the rendering engines.
