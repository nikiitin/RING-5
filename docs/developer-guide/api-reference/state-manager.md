---
title: "StateManager API Reference"
parent: API Reference
grand_parent: Developer Guide
nav_order: 3
---

# StateManager API Reference

## Overview

The `StateManager` protocol is the foundational contract for all state operations in RING-5
Unified Engine v2. It defines a flat, category-organized API surface that the `ApplicationAPI`
depends on -- never a concrete implementation. This follows the Dependency Inversion Principle:
high-level modules (services, controllers) program against the protocol, while the concrete
`RepositoryStateManager` is wired at application bootstrap.

All domain state -- raw data, plots, configuration, parser settings, previews, and operation
history -- flows through this single interface. The protocol contains 46 methods organized into
seven logical categories, each mapping to a dedicated in-memory repository behind the scenes.

**Source files:**

| File | Role |
|------|------|
| `src/core/state/state_manager.py` | `StateManager` protocol definition |
| `src/core/state/repository_state_manager.py` | `RepositoryStateManager` concrete implementation |
| `src/core/state/repositories/session_repository.py` | `SessionRepository` aggregate root |

---

## StateManager Protocol

Defined in `src/core/state/state_manager.py` as a `typing.Protocol` decorated with
`@runtime_checkable`. Any class that implements all of the methods below satisfies the
protocol at both static analysis time and runtime (`isinstance` checks).

```python
from src.core.state.state_manager import StateManager
```

### Data Methods

Methods for managing the primary and processed DataFrames.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_data` | `() -> DataFrame | None` | Current raw DataFrame or `None` | Retrieve the primary dataset loaded from CSV or parser output. |
| `set_data` | `(data: DataFrame | None, on_change: Callable[[], None] | None = None) -> None` | `None` | Store the primary dataset. An optional `on_change` callback fires after the value is written. Configuration-type columns are automatically cast to `str` based on parser variable definitions. |
| `get_processed_data` | `() -> DataFrame | None` | Processed DataFrame or `None` | Retrieve the post-pipeline transformed dataset used for rendering. |
| `set_processed_data` | `(data: DataFrame | None) -> None` | `None` | Store the pipeline-transformed dataset. |
| `has_data` | `() -> bool` | `bool` | Returns `True` if the primary dataset is non-`None` and non-empty. |
| `clear_data` | `() -> None` | `None` | Clears raw data, processed data, CSV path, temp directory, and all plots. Also removes the temp directory from disk if it exists. |

### Config Methods

Methods for application configuration, file paths, the CSV pool, and saved configurations.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_config` | `() -> dict[str, Any]` | Configuration dict | Get the full application configuration dictionary. |
| `set_config` | `(config: dict[str, Any]) -> None` | `None` | Replace the entire configuration dictionary. |
| `update_config` | `(key: str, value: object) -> None` | `None` | Update a single key within the configuration dictionary. |
| `get_temp_dir` | `() -> str | None` | Path string or `None` | Get the temporary directory used by the parser for intermediate files. |
| `set_temp_dir` | `(path: str) -> None` | `None` | Set the temporary directory path. Idempotent -- skips writes when the value is unchanged. |
| `get_csv_path` | `() -> str | None` | Path string or `None` | Get the file path of the currently loaded CSV. |
| `set_csv_path` | `(path: str) -> None` | `None` | Set the CSV file path. Idempotent. |
| `get_csv_pool` | `() -> list[CsvPoolEntry]` | List of pool entries | Retrieve the list of available CSV files registered in the pool. |
| `set_csv_pool` | `(pool: list[CsvPoolEntry]) -> None` | `None` | Replace the CSV pool content. |
| `get_saved_configs` | `() -> list[SavedConfigEntry]` | List of saved configs | Retrieve persisted configuration snapshots. |
| `set_saved_configs` | `(configs: list[SavedConfigEntry]) -> None` | `None` | Replace the list of saved configurations. |

### Parser State Methods

Methods for managing simulator parser settings, variable definitions, and scanning state.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `is_using_parser` | `() -> bool` | `bool` | Check whether parser mode is active (as opposed to direct CSV loading). |
| `set_use_parser` | `(use: bool) -> None` | `None` | Enable or disable parser mode. Idempotent. |
| `get_parse_variables` | `() -> list[ParseVariableConfig]` | Variable config list | Get the list of variable extraction configurations. Each entry is a `TypedDict` with `name`, `type`, and `_id` fields. |
| `set_parse_variables` | `(variables: list[ParseVariableConfig]) -> None` | `None` | Replace all parse variable configurations. Auto-assigns UUIDs to entries missing an `_id`. |
| `get_stats_path` | `() -> str` | Directory path | Get the base directory path for stats file scanning. |
| `set_stats_path` | `(path: str) -> None` | `None` | Set the stats directory. Idempotent. |
| `get_stats_pattern` | `() -> str` | Filename pattern | Get the filename glob pattern for stats files (e.g., `"stats.txt"`). |
| `set_stats_pattern` | `(pattern: str) -> None` | `None` | Set the filename pattern. Idempotent. |
| `get_scanned_variables` | `() -> list[ScannedVariableDict]` | Scanned variable list | Retrieve variables discovered during the last scan operation. |
| `set_scanned_variables` | `(variables: list[ScannedVariableDict]) -> None` | `None` | Store scanned variable results. |
| `get_parser_strategy` | `() -> str` | `"simple"` or `"config_aware"` | Get the active parser strategy. |
| `set_parser_strategy` | `(strategy: str) -> None` | `None` | Set the parser strategy. Input is normalized to lowercase. Idempotent. |
| `get_simulator` | `() -> str` | Simulator name | Get the active simulator backend (e.g., `"gem5"`). |
| `set_simulator` | `(simulator: str) -> None` | `None` | Set the simulator backend. Idempotent. |

### Plot Methods

Methods for managing the plot collection, ID generation, and active plot selection.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_plots` | `() -> list[PlotProtocol]` | List of plots | Retrieve all active plot objects. |
| `set_plots` | `(plots: list[PlotProtocol]) -> None` | `None` | Replace the entire plot list (used during portfolio restoration). |
| `add_plot` | `(plot_obj: PlotProtocol) -> None` | `None` | Append a single plot to the collection. |
| `get_plot_counter` | `() -> int` | Current counter | Get the monotonic counter used for plot ID generation. |
| `set_plot_counter` | `(counter: int) -> None` | `None` | Set the plot counter (used during portfolio restoration). |
| `start_next_plot_id` | `() -> int` | New plot ID | Atomically return the current counter value and increment it. This is the primary ID allocation mechanism. |
| `get_current_plot_id` | `() -> int | None` | Plot ID or `None` | Get the ID of the currently selected/active plot. |
| `set_current_plot_id` | `(plot_id: int | None) -> None` | `None` | Set which plot is currently active in the UI. |

### Visualization Methods

Methods for per-plot rendering configuration. These are used by `RepositoryStateManager`
but are not part of the `StateManager` protocol itself -- they are accessed through the
concrete implementation only.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_visualization_config` | `(plot_id: int) -> FigureConfig | None` | Figure config or `None` | Retrieve the `FigureConfig` for a specific plot. |
| `set_visualization_config` | `(plot_id: int, config: FigureConfig) -> None` | `None` | Store or replace the `FigureConfig` for a plot. |
| `remove_visualization_config` | `(plot_id: int) -> None` | `None` | Remove visualization config when a plot is deleted. |

### Preview Methods

Methods for the "try-then-confirm" preview workflow used by data managers.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `set_preview` | `(operation_name: str, data: DataFrame) -> None` | `None` | Store a preview DataFrame keyed by operation name. Validates that the name is non-empty and data is non-`None`. |
| `get_preview` | `(operation_name: str) -> DataFrame | None` | Preview DataFrame or `None` | Retrieve a stored preview for inspection before confirmation. |
| `has_preview` | `(operation_name: str) -> bool` | `bool` | Check whether a preview exists for the given operation. |
| `clear_preview` | `(operation_name: str) -> None` | `None` | Remove a preview after the user confirms or discards the operation. |

Standard operation keys: `"preprocessor"`, `"seeds_reduction"`, `"outlier_removal"`, `"mixer"`.

### History Methods

Methods for the dual-list operation audit trail.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `add_manager_history_record` | `(record: OperationRecord) -> None` | `None` | Append to the rolling manager history (FIFO eviction at 10 entries). |
| `get_manager_history` | `() -> list[OperationRecord]` | List of records (copy) | Retrieve a copy of the manager history. |
| `remove_manager_history_record` | `(record: OperationRecord) -> None` | `None` | Remove the first matching record from manager history. |
| `add_portfolio_history_record` | `(record: OperationRecord) -> None` | `None` | Append to the unbounded portfolio history. |
| `get_portfolio_history` | `() -> list[OperationRecord]` | List of records (copy) | Retrieve a copy of the complete portfolio history. |
| `remove_portfolio_history_record` | `(record: OperationRecord) -> None` | `None` | Remove the first matching record from portfolio history. |

### Session Methods

Top-level lifecycle operations.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `initialize` | `() -> None` | `None` | Re-initialize the session to clean defaults without constructing a new instance. Writes defaults only if no data currently exists. |
| `clear_all` | `() -> None` | `None` | Clear every repository to pristine state. Resets data, plots, parser state, config, history, and visualization configs. |
| `restore_session` | `(portfolio_data: PortfolioData) -> None` | `None` | Restore full session state from a serialized portfolio snapshot. See [SessionRepository](#sessionrepository-aggregate-root) for restoration order. |

---

## RepositoryStateManager Implementation

Defined in `src/core/state/repository_state_manager.py`, the `RepositoryStateManager` is the
sole concrete implementation of the `StateManager` protocol. It acts as a thin facade that
delegates every method call to the appropriate child repository through the `SessionRepository`
aggregate root.

### Constructor

```python
RepositoryStateManager(plot_deserializer: PlotDeserializer | None = None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `plot_deserializer` | `PlotDeserializer | None` | Callable that converts a serialized `dict` into a `PlotProtocol` instance. Forwarded to `SessionRepository` so that portfolio restoration never requires importing web-layer classes. At bootstrap, `BasePlot.from_dict` is injected. |

### Delegation Pattern

Every facade method follows the same pattern -- access the `SessionRepository`, reach the
appropriate child repository, and call the corresponding method:

```python
def get_data(self) -> pd.DataFrame | None:
    return self._session_repo.data_repo.get_data()
```

### Added Behavior

While most methods are pure pass-throughs, two methods add logic beyond simple delegation:

**`set_data`** -- Before storing the DataFrame, the implementation:
1. Performs an identity check (`data is current_data`) to skip redundant writes on Streamlit reruns.
2. Copies the DataFrame to prevent external mutations from propagating to stored state.
3. Reads parser variable definitions and casts any column marked as `"configuration"` type to `str`.

**`clear_data`** -- In addition to clearing repositories, this method:
1. Removes the temporary directory from disk via `shutil.rmtree` if it exists.
2. Resets the CSV path and temp dir on the config repository.
3. Clears all plots and resets the plot counter to zero.

---

## SessionRepository (Aggregate Root)

Defined in `src/core/state/repositories/session_repository.py`, the `SessionRepository` owns
all seven child repository instances and provides session-level lifecycle operations. It is the
single point of coordination for initialization, restoration, and teardown.

### Constructor

```python
SessionRepository(plot_deserializer: PlotDeserializer | None = None)
```

On construction, all seven child repositories are instantiated with their default values:

| Attribute | Type | Initial State |
|-----------|------|---------------|
| `data_repo` | `DataRepository` | `_data=None`, `_processed_data=None` |
| `plot_repo` | `PlotRepository` | `_plots=[]`, `_plot_counter=0`, `_current_plot_id=None` |
| `parser_repo` | `ParserStateRepository` | 3 default variables, `"gem5"`, `"simple"` strategy |
| `config_repo` | `ConfigRepository` | Empty dict, `None` paths, empty pool/configs |
| `preview_repo` | `PreviewRepository` | Empty dict |
| `history_repo` | `HistoryRepository` | Empty lists for both manager and portfolio history |
| `visualization_repo` | `VisualizationRepository` | Empty dict |

### Methods

**`initialize_session()`** -- Ensures clean defaults exist. Only writes data fields when no data
is currently loaded. Repository-specific defaults are established by each repository's own
`__init__` method.

**`clear_widget_state()`** -- A no-op placeholder. With domain repositories being pure Python
and UI-agnostic, widget state cleanup is handled by the web layer independently.

**`clear_all()`** -- Resets every repository to its pristine state:
- Clears data and processed data
- Clears all plots, resets counter to 0, sets current plot ID to `None`
- Clears parser state (scanned variables, use_parser flag)
- Clears config, CSV path, and temp directory
- Clears both history lists
- Clears all visualization configs

**`restore_from_portfolio(portfolio_data)`** -- Restores the entire session from a serialized
`PortfolioData` dictionary. The restoration follows a strict ordering:

1. Parser state (variables, path, pattern, scanned variables, use_parser flag)
2. Config state (CSV path, config dictionary)
3. Data (deserialize CSV string via `pd.read_csv(io.StringIO(...))`)
4. Plots (deserialize each dict via the injected `plot_deserializer` callable)
5. Plot counter
6. Manager and portfolio history lists

If no `plot_deserializer` was injected, plot restoration is skipped with a warning.

---

## Repository Hierarchy

The following table maps every `StateManager` facade method to the child repository that
ultimately handles the call.

| Category | Facade Method | Target Repository | Repository Method |
|----------|--------------|-------------------|-------------------|
| Data | `get_data` | `DataRepository` | `get_data` |
| Data | `set_data` | `DataRepository` | `set_data` |
| Data | `get_processed_data` | `DataRepository` | `get_processed_data` |
| Data | `set_processed_data` | `DataRepository` | `set_processed_data` |
| Data | `has_data` | `DataRepository` | `has_data` |
| Data | `clear_data` | `DataRepository` + `ConfigRepository` + `PlotRepository` | `clear_data` + path resets + `clear_plots` |
| Config | `get_config` | `ConfigRepository` | `get_config` |
| Config | `set_config` | `ConfigRepository` | `set_config` |
| Config | `update_config` | `ConfigRepository` | `update_config` |
| Config | `get_temp_dir` / `set_temp_dir` | `ConfigRepository` | `get_temp_dir` / `set_temp_dir` |
| Config | `get_csv_path` / `set_csv_path` | `ConfigRepository` | `get_csv_path` / `set_csv_path` |
| Config | `get_csv_pool` / `set_csv_pool` | `ConfigRepository` | `get_csv_pool` / `set_csv_pool` |
| Config | `get_saved_configs` / `set_saved_configs` | `ConfigRepository` | `get_saved_configs` / `set_saved_configs` |
| Parser | `is_using_parser` / `set_use_parser` | `ParserStateRepository` | `is_using_parser` / `set_using_parser` |
| Parser | `get_parse_variables` / `set_parse_variables` | `ParserStateRepository` | `get_parse_variables` / `set_parse_variables` |
| Parser | `get_stats_path` / `set_stats_path` | `ParserStateRepository` | `get_stats_path` / `set_stats_path` |
| Parser | `get_stats_pattern` / `set_stats_pattern` | `ParserStateRepository` | `get_stats_pattern` / `set_stats_pattern` |
| Parser | `get_scanned_variables` / `set_scanned_variables` | `ParserStateRepository` | `get_scanned_variables` / `set_scanned_variables` |
| Parser | `get_parser_strategy` / `set_parser_strategy` | `ParserStateRepository` | `get_parser_strategy` / `set_parser_strategy` |
| Parser | `get_simulator` / `set_simulator` | `ParserStateRepository` | `get_simulator` / `set_simulator` |
| Plot | `get_plots` / `set_plots` | `PlotRepository` | `get_plots` / `set_plots` |
| Plot | `add_plot` | `PlotRepository` | `add_plot` |
| Plot | `get_plot_counter` / `set_plot_counter` | `PlotRepository` | `get_plot_counter` / `set_plot_counter` |
| Plot | `start_next_plot_id` | `PlotRepository` | `increment_plot_counter` |
| Plot | `get_current_plot_id` / `set_current_plot_id` | `PlotRepository` | `get_current_plot_id` / `set_current_plot_id` |
| Visualization | `get_visualization_config` | `VisualizationRepository` | `get_config` |
| Visualization | `set_visualization_config` | `VisualizationRepository` | `set_config` |
| Visualization | `remove_visualization_config` | `VisualizationRepository` | `remove_config` |
| Preview | `set_preview` / `get_preview` | `PreviewRepository` | `set_preview` / `get_preview` |
| Preview | `has_preview` | `PreviewRepository` | `has_preview` |
| Preview | `clear_preview` | `PreviewRepository` | `clear_preview` |
| History | `add_manager_history_record` | `HistoryRepository` | `add_manager_record` |
| History | `get_manager_history` | `HistoryRepository` | `get_manager_history` |
| History | `remove_manager_history_record` | `HistoryRepository` | `remove_manager_record` |
| History | `add_portfolio_history_record` | `HistoryRepository` | `add_portfolio_record` |
| History | `get_portfolio_history` | `HistoryRepository` | `get_portfolio_history` |
| History | `remove_portfolio_history_record` | `HistoryRepository` | `remove_portfolio_record` |
| Session | `initialize` | `SessionRepository` | `initialize_session` |
| Session | `clear_all` | `SessionRepository` | `clear_all` |
| Session | `restore_session` | `SessionRepository` | `restore_from_portfolio` |

---

## Session State Backing Store

All seven repositories are pure Python objects with zero Streamlit dependency. They store
state in private instance attributes (lists, dicts, scalars) rather than in
`st.session_state`. State survives Streamlit reruns because the entire repository tree is
held by the session-owned `ApplicationAPI` stored under `st.session_state.api`.

```
if "api" not in st.session_state:
    st.session_state.api = ApplicationAPI()
```

On each Streamlit rerun, session state returns the same Python object. Because the
`RepositoryStateManager` (and therefore all repositories) live as attributes of this object,
their in-memory state is preserved without any serialization or deserialization.

### What this means in practice

- **No serialization overhead**: DataFrames, plot objects, and history records remain as
  native Python objects across reruns.
- **No key collisions**: Repository state is namespaced by object identity, not by string
  keys in a shared dictionary.
- **Single source of truth**: The session-owned `ApplicationAPI` guarantees exactly one
  repository tree per Streamlit session.
- **Idempotent setters**: Many setters include identity/equality checks to skip redundant
  writes and reduce log noise during Streamlit reruns.

---

## See Also

- [ApplicationAPI Reference](./application-api.md) -- The public API layer that wraps `StateManager`
- [Portfolio System](../web/portfolio-system.md) -- Save/restore flows that use `restore_session`
- [State Management](../core/state-management.md) -- How repositories coordinate session state
- [Plotting System](../visualization/plotting-system.md) -- Plot lifecycle and rendering
