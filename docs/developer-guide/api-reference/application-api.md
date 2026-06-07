---
title: "ApplicationAPI Reference"
parent: API Reference
grand_parent: Developer Guide
nav_order: 1
---

# ApplicationAPI Reference

## Overview

`ApplicationAPI` is the **single entry point** through which the entire presentation layer
(Streamlit web UI) accesses business logic, state management, and parsing services. It is
the Layer B orchestrator in the RING-5 clean-architecture stack: no web page or component
should import core services directly -- every call must flow through this facade.

The class is defined in `src/core/application_api.py` (429 lines). It composes three
internal collaborators:

| Collaborator | Type | Role |
|---|---|---|
| `state_manager` | `RepositoryStateManager` | Single source of truth for application state |
| `_services` | `DefaultServicesAPI` | Unified facade over all domain services |
| `_parser` | `SimulationParser` | Simulator-specific parse/scan backend |

`ApplicationAPI` performs almost no computation itself. It orchestrates delegation to the
collaborators above, enforces the boundary between UI and domain, and provides semantic
action names that map to user-visible operations.

### Singleton Instantiation

A single `ApplicationAPI` instance is created via Streamlit's `@st.cache_resource`
decorator in `app.py:54-58`:

```python
@st.cache_resource(show_spinner="Initializing RING-5...")
def get_api() -> ApplicationAPI:
    return ApplicationAPI(plot_deserializer=BasePlot.from_dict)

api = get_api()
st.session_state.api = api
```

The `@st.cache_resource` decorator guarantees:

- Exactly one instance per Streamlit server process.
- The instance survives across reruns (page navigations, widget interactions).
- All sub-services share the same lifecycle as the `ApplicationAPI`.
- `BasePlot.from_dict` is injected as the plot deserializer so the core layer never
  imports web-layer classes.

---

## Constructor

```python
class ApplicationAPI:
    def __init__(
        self,
        plot_deserializer: PlotDeserializer | None = None,
        parser: SimulationParser | None = None,
    ) -> None
```

**Source:** `src/core/application_api.py:72-96`

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `plot_deserializer` | `PlotDeserializer \| None` | `None` | Callable that converts a `dict` into a `PlotProtocol` instance. Injected into the `RepositoryStateManager` so portfolio restoration can reconstruct plot objects without importing web-layer classes. In production this is `BasePlot.from_dict`. |
| `parser` | `SimulationParser \| None` | `None` | Simulator parser backend. When `None`, defaults to `SimulatorRegistry.get_parser("gem5")`. |

### Initialization Sequence

1. Creates `RepositoryStateManager(plot_deserializer=plot_deserializer)` -- the single
   source of truth for all application state.
2. Creates `DefaultServicesAPI(self.state_manager)` -- the composition root that wires
   `ManagersAPI`, `DataServicesAPI`, and `ShapersAPI` together.
3. Sets `self._parser` to the provided parser or lazily fetches the gem5 parser from the
   `SimulatorRegistry`.

---

## Properties

Three properties expose the `ServicesAPI` sub-APIs for direct use by UI components.

```python
@property
def managers(self) -> ManagersAPI
```
**Source:** `src/core/application_api.py:102-105`

Access stateless data transformation operations (arithmetic, outlier removal, seed
reduction). All methods on the returned object are stateless -- they accept DataFrames and
return new DataFrames without side effects.

---

```python
@property
def data_services(self) -> DataServicesAPI
```
**Source:** `src/core/application_api.py:107-109`

Access data storage, retrieval, and domain entity management (CSV pool, configurations,
variables, portfolios).

---

```python
@property
def shapers(self) -> ShapersAPI
```
**Source:** `src/core/application_api.py:111-115`

Access pipeline and shaper operations (create, list, execute, delete shaper pipelines).

---

## Public Attribute

| Attribute | Type | Description |
|---|---|---|
| `state_manager` | `RepositoryStateManager` | The central state repository. Public so that controllers and pages can call state-level methods (e.g., `get_data()`, `set_processed_data()`, `get_plots()`) that are not wrapped by `ApplicationAPI`. |

---

## Method Groups

### 1. Data Loading and Session Management

#### `load_data`

```python
def load_data(self, csv_path: str) -> None
```

**Source:** `src/core/application_api.py:117-135`

Orchestrates loading a CSV file and persisting the result into application state.

| Parameter | Type | Description |
|---|---|---|
| `csv_path` | `str` | Absolute or user-relative path to the CSV file. |

**Behavior:**
1. Calls `data_services.load_csv_file(csv_path)` to parse the CSV into a DataFrame.
2. Stores the raw DataFrame via `state_manager.set_data(df)`.
3. Resets processed data to `None` via `state_manager.set_processed_data(None)`.
4. Records the CSV path via `state_manager.set_csv_path(csv_path)`.

**Raises:** Re-raises any exception from the underlying load operation after logging.

---

#### `load_from_pool`

```python
def load_from_pool(self, csv_path: str) -> None
```

**Source:** `src/core/application_api.py:137-140`

Convenience alias that loads a dataset from the CSV pool. Delegates directly to
`self.load_data(csv_path)`.

---

#### `get_current_view`

```python
def get_current_view(self) -> dict[str, Any]
```

**Source:** `src/core/application_api.py:142-148`

Assembles the current data pipeline state for UI consumption.

**Returns:** A dictionary with three keys:

| Key | Type | Description |
|---|---|---|
| `"raw_data"` | `pd.DataFrame \| None` | The unmodified loaded dataset. |
| `"processed_data"` | `pd.DataFrame \| None` | The dataset after manager operations. |
| `"config"` | `dict` | Current application configuration. |

---

#### `reset_session`

```python
def reset_session(self) -> None
```

**Source:** `src/core/application_api.py:150-153`

Clears all session data by calling `state_manager.clear_data()` followed by
`state_manager.clear_all()`. This is the full session reset used when users navigate
away or explicitly reset.

---

#### `load_csv_file`

```python
def load_csv_file(self, file_path: str) -> pd.DataFrame
```

**Source:** `src/core/application_api.py:320-322`

Loads a CSV file directly, returning the parsed DataFrame without persisting it into
state. Useful when a component needs to inspect data before committing to a load.

| Parameter | Type | Description |
|---|---|---|
| `file_path` | `str` | Path to the CSV file. |

**Returns:** `pd.DataFrame` -- the parsed contents.
**Raises:** `FileNotFoundError`, `IsADirectoryError`, or `ValueError` if the path is
invalid.

---

#### `get_column_info`

```python
def get_column_info(self, df: pd.DataFrame | None) -> ColumnInfoResult
```

**Source:** `src/core/application_api.py:324-344`

Returns summary metadata about DataFrame columns. This is one of only two methods
that perform logic directly rather than delegating.

| Parameter | Type | Description |
|---|---|---|
| `df` | `pd.DataFrame \| None` | The DataFrame to inspect, or `None`. |

**Returns:** A `ColumnInfoResult` TypedDict with fields:

| Field | Type | Description |
|---|---|---|
| `total_columns` | `int` | Number of columns (0 if `df` is `None`). |
| `total_rows` | `int` | Number of rows (0 if `df` is `None`). |
| `numeric_columns` | `list[str]` | Columns with numeric dtypes. |
| `categorical_columns` | `list[str]` | Columns with non-numeric dtypes. |
| `columns` | `list[str]` | All column names. |

---

### 2. Scanning Methods

#### `find_stats_files`

```python
def find_stats_files(
    self, search_path: str, pattern: str = "stats.txt"
) -> list[str]
```

**Source:** `src/core/application_api.py:159-165`

Finds simulator statistics files within a directory tree.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `search_path` | `str` | -- | Root directory to search. Resolved via `normalize_user_path`. |
| `pattern` | `str` | `"stats.txt"` | Glob pattern for matching filenames. Sanitized via `sanitize_glob_pattern` before use. |

**Returns:** List of absolute file path strings. Returns an empty list if the path does
not exist.

---

#### `submit_scan_async`

```python
def submit_scan_async(
    self,
    stats_path: str,
    stats_pattern: str = "stats.txt",
    limit: int = 5,
) -> list[Future[list[ScannedVariable]]]
```

**Source:** `src/core/application_api.py:244-248`

Submits an asynchronous scanning job to the parser backend.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `stats_path` | `str` | -- | Root path containing stats files. |
| `stats_pattern` | `str` | `"stats.txt"` | Filename pattern to find stats files. |
| `limit` | `int` | `5` | Maximum number of files to scan. |

**Returns:** A list of `Future` objects, each resolving to a `list[ScannedVariable]`.
The UI layer is responsible for polling these futures for completion.

---

#### `finalize_scan`

```python
def finalize_scan(
    self, results: list[list[ScannedVariable]]
) -> list[ScannedVariable]
```

**Source:** `src/core/application_api.py:250-252`

Aggregates raw scan results into a unified list of discovered variables.

| Parameter | Type | Description |
|---|---|---|
| `results` | `list[list[ScannedVariable]]` | Resolved future results from `submit_scan_async`. |

**Returns:** Deduplicated `list[ScannedVariable]` representing all variables found across
all scanned files.

---

#### `get_scanner_status`

```python
def get_scanner_status(self) -> str
```

**Source:** `src/core/application_api.py:262-264`

Returns the static string `"idle"`. Actual scanner status tracking is handled by the
UI layer via `st.session_state`.

---

#### `cancel_pending_scans`

```python
@staticmethod
def cancel_pending_scans() -> None
```

**Source:** `src/core/application_api.py:423-428`

Cancels all pending scan futures to release thread-pool resources and memory. Delegates
to `ScanWorkPool.get_instance().cancel_all()`. The `ScanWorkPool` import is deferred
(inline) to avoid loading parsing modules at import time.

---

### 3. Parsing Methods

#### `submit_parse_async`

```python
def submit_parse_async(
    self,
    stats_path: str,
    stats_pattern: str,
    variables: Sequence[ParseVariableConfig | StatConfig],
    output_dir: str,
    strategy_type: str = "simple",
    scanned_vars: list[ScannedVariable] | list[ScannedVariableDict] | None = None,
) -> ParseBatchResult
```

**Source:** `src/core/application_api.py:167-230`

Submits an asynchronous parsing job to the parser backend. This method performs
significant input normalization before delegating:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `stats_path` | `str` | -- | Root path containing stats files. |
| `stats_pattern` | `str` | -- | Filename pattern to find stats files. |
| `variables` | `Sequence[ParseVariableConfig \| StatConfig]` | -- | Variable configurations to parse. Accepts both UI-layer dicts and core-layer `StatConfig` objects. |
| `output_dir` | `str` | -- | Directory for intermediate parse output. |
| `strategy_type` | `str` | `"simple"` | Parsing strategy (e.g., `"simple"`, `"multisim"`). |
| `scanned_vars` | `list[ScannedVariable] \| list[ScannedVariableDict] \| None` | `None` | Previously scanned variable metadata used for regex expansion. |

**Variable normalization logic** (lines 182-219):

- **Dict variables** (`ParseVariableConfig`): Converted to `StatConfig` with type
  normalization, alias handling (sets `parsed_ids`), and automatic `is_regex` detection
  when the name contains `\d+`.
- **ScannedVariable objects** (duck-typed via `hasattr`): Converted to `StatConfig` with
  entries passed through `params`.
- **StatConfig objects**: Passed through unchanged.

**Returns:** `ParseBatchResult` -- a frozen dataclass bundling `futures` and `var_names`.

---

#### `finalize_parsing`

```python
def finalize_parsing(
    self,
    output_dir: str,
    results: list[dict[str, Any]],
    strategy_type: str = "simple",
    var_names: list[str] | None = None,
) -> str | None
```

**Source:** `src/core/application_api.py:232-242`

Finalizes parse results into a CSV file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `output_dir` | `str` | -- | Directory containing intermediate parse output. |
| `results` | `list[dict[str, Any]]` | -- | Resolved future results from `submit_parse_async`. |
| `strategy_type` | `str` | `"simple"` | Parsing strategy used during submission. |
| `var_names` | `list[str] \| None` | `None` | Variable names to guarantee column ordering. |

**Returns:** The path to the generated CSV file, or `None` if finalization fails.

---

#### `get_parse_status`

```python
def get_parse_status(self) -> str
```

**Source:** `src/core/application_api.py:254-260`

Returns the static string `"idle"`. Actual parse status tracking is handled by the
UI layer via `st.session_state`.

---

### 4. Data Management Methods

These methods delegate to `DataServicesAPI` via `self._services.data_services`.

#### `load_csv_pool`

```python
def load_csv_pool(self) -> list[CsvPoolEntry]
```

**Source:** `src/core/application_api.py:296-298`

Lists all available CSV files in the pool directory (`{root}/.ring5/csv_pool/`).
Entries are sorted by modification time (newest first) and enriched with cached
metadata.

**Returns:** A list of `CsvPoolEntry` TypedDicts, each containing `path`, `name`,
`size`, `modified`, and optional metadata fields (`columns`, `rows`, `dtypes`).

---

#### `add_to_csv_pool`

```python
def add_to_csv_pool(self, file_path: str) -> str
```

**Source:** `src/core/application_api.py:308-310`

Copies a CSV file into the pool directory with a timestamp-prefixed filename.

| Parameter | Type | Description |
|---|---|---|
| `file_path` | `str` | Source file path to copy into the pool. |

**Returns:** The path to the copied file in the pool directory.

---

#### `delete_from_pool`

```python
def delete_from_pool(self, file_path: str) -> bool
```

**Source:** `src/core/application_api.py:312-314`

Deletes a file from the CSV pool. Validates that the path is within the pool directory
before unlinking.

**Returns:** `True` on success, `False` on failure (graceful degradation).

---

#### `delete_from_csv_pool`

```python
def delete_from_csv_pool(self, file_path: str) -> bool
```

**Source:** `src/core/application_api.py:316-318`

Alias for `delete_from_pool`. Exists to match the `DataServicesAPI` protocol method
name.

---

### 5. Configuration Methods

#### `save_configuration`

```python
def save_configuration(
    self,
    name: str,
    description: str,
    shapers_config: list[ShaperStepConfig],
    csv_path: str | None = None,
) -> str
```

**Source:** `src/core/application_api.py:280-289`

Saves the current pipeline configuration to disk as a JSON file in the
`{root}/.ring5/saved_configs/` directory.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | -- | Human-readable configuration name. |
| `description` | `str` | -- | Description text for the configuration. |
| `shapers_config` | `list[ShaperStepConfig]` | -- | The shaper pipeline steps to persist. |
| `csv_path` | `str \| None` | `None` | Optional path to the associated CSV file. |

**Returns:** The absolute path to the saved JSON configuration file.

---

#### `load_configuration`

```python
def load_configuration(self, config_path: str) -> SavedConfigData
```

**Source:** `src/core/application_api.py:292-294`

Loads a saved configuration from its JSON file.

| Parameter | Type | Description |
|---|---|---|
| `config_path` | `str` | Path to the configuration JSON file. |

**Returns:** `SavedConfigData` TypedDict with `name`, `description`, `timestamp`,
`shapers`, and optional `csv_path`.

---

#### `load_saved_configs`

```python
def load_saved_configs(self) -> list[SavedConfigEntry]
```

**Source:** `src/core/application_api.py:300-302`

Lists all saved configurations sorted by modification time (newest first).

**Returns:** List of `SavedConfigEntry` TypedDicts, each with `path`, `name`,
`modified`, and `description`.

---

#### `delete_configuration`

```python
def delete_configuration(self, config_path: str) -> bool
```

**Source:** `src/core/application_api.py:304-306`

Deletes a saved configuration file.

**Returns:** `True` on success, `False` on failure.

---

### 6. Pipeline and Shaper Methods

#### `apply_shapers`

```python
def apply_shapers(
    self,
    data: pd.DataFrame,
    pipeline_config: list[ShaperStepConfig],
) -> pd.DataFrame
```

**Source:** `src/core/application_api.py:270-274`

Executes a sequence of shaper transformations on a DataFrame. Each step in the
pipeline is instantiated via `ShaperFactory.create_shaper()` and applied in order
using `DataFrame.pipe()`.

| Parameter | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | Input DataFrame to transform. |
| `pipeline_config` | `list[ShaperStepConfig]` | Ordered list of shaper step configurations. Each step must include a `"type"` key matching a registered shaper. |

**Returns:** The transformed DataFrame after all pipeline steps have been applied.
**Raises:** `ValueError` if any shaper type is unknown or a shaper step fails.

---

### 7. Visualization Config Methods

These methods delegate directly to `RepositoryStateManager` for per-plot visualization
configuration storage.

#### `get_visualization_config`

```python
def get_visualization_config(self, plot_id: int) -> FigureConfig | None
```

**Source:** `src/core/application_api.py:350-352`

Retrieves the `FigureConfig` for a specific plot.

**Returns:** The `FigureConfig` dataclass instance, or `None` if no configuration has
been stored for this plot.

---

#### `set_visualization_config`

```python
def set_visualization_config(
    self, plot_id: int, config: FigureConfig
) -> None
```

**Source:** `src/core/application_api.py:354-356`

Stores or replaces the visualization configuration for a plot.

---

#### `remove_visualization_config`

```python
def remove_visualization_config(self, plot_id: int) -> None
```

**Source:** `src/core/application_api.py:358-360`

Removes the visualization configuration for a plot (typically called when a plot is
deleted).

---

### 8. Preview Methods

Preview DataFrames are temporary snapshots stored in state for UI preview panels (e.g.,
showing the effect of an outlier-removal operation before the user confirms it).

#### `set_preview`

```python
def set_preview(self, operation_name: str, data: pd.DataFrame) -> None
```

**Source:** `src/core/application_api.py:366-368`

Stores a preview DataFrame keyed by operation name.

---

#### `get_preview`

```python
def get_preview(self, operation_name: str) -> pd.DataFrame | None
```

**Source:** `src/core/application_api.py:370-372`

Retrieves a previously stored preview. Returns `None` if no preview exists.

---

#### `has_preview`

```python
def has_preview(self, operation_name: str) -> bool
```

**Source:** `src/core/application_api.py:374-376`

Checks whether a preview exists for the given operation.

---

#### `clear_preview`

```python
def clear_preview(self, operation_name: str) -> None
```

**Source:** `src/core/application_api.py:378-380`

Removes a preview from state.

---

### 9. History Methods

Operation history records are stored in two parallel lists: a rolling manager history
(last 20 entries) and a full portfolio history (unbounded). Every write operation
records into both lists.

#### `add_manager_history_record`

```python
def add_manager_history_record(self, record: OperationRecord) -> None
```

**Source:** `src/core/application_api.py:386-389`

Records an operation in both the manager rolling history and the portfolio history.

| Parameter | Type | Description |
|---|---|---|
| `record` | `OperationRecord` | TypedDict with `source_columns`, `dest_columns`, `operation`, and `timestamp`. |

---

#### `get_manager_history`

```python
def get_manager_history(self) -> list[OperationRecord]
```

**Source:** `src/core/application_api.py:391-393`

Returns the rolling manager operation history (capped at 20 entries).

---

#### `get_portfolio_history`

```python
def get_portfolio_history(self) -> list[OperationRecord]
```

**Source:** `src/core/application_api.py:395-397`

Returns the full, unbounded portfolio operation history.

---

#### `remove_manager_history_record`

```python
def remove_manager_history_record(self, record: OperationRecord) -> None
```

**Source:** `src/core/application_api.py:399-402`

Removes a specific record from both the manager and portfolio histories.

---

### 10. Simulator Registry Facades

These static methods expose the `SimulatorRegistry` so the web layer does not need to
import parsing modules directly.

#### `available_simulators`

```python
@staticmethod
def available_simulators() -> list[str]
```

**Source:** `src/core/application_api.py:408-411`

Returns the list of registered simulator names (e.g., `["gem5"]`).

---

#### `available_simulator_info`

```python
@staticmethod
def available_simulator_info() -> list[SimulatorInfo]
```

**Source:** `src/core/application_api.py:413-416`

Returns metadata for all registered simulators. Each `SimulatorInfo` is a frozen
dataclass containing `name`, `display_name`, `description`, `file_pattern`,
`variable_types`, `internal_stats`, and `parsing_strategies`.

---

#### `get_simulator_info`

```python
@staticmethod
def get_simulator_info(name: str) -> SimulatorInfo
```

**Source:** `src/core/application_api.py:418-421`

Returns metadata for a specific simulator by name.

**Raises:** `KeyError` if the simulator is not registered.

---

## Usage Examples

### Accessing the API from a Streamlit page

All pages receive the API through `st.session_state`:

```python
import streamlit as st

api = st.session_state.api

# Load data from the CSV pool
pool_entries = api.load_csv_pool()
if pool_entries:
    api.load_from_pool(pool_entries[0]["path"])

# Inspect loaded data
view = api.get_current_view()
raw_df = view["raw_data"]
info = api.get_column_info(raw_df)
```

### Running a shaper pipeline

```python
pipeline = [
    {"type": "columnSelector", "columns": ["benchmark", "ipc", "cache_misses"]},
    {"type": "normalize", "normalizeVars": ["ipc"], "normalizerColumn": "benchmark",
     "normalizerValue": "baseline", "groupBy": ["config"]},
]
result_df = api.apply_shapers(raw_df, pipeline)
```

### Using sub-APIs directly

```python
# Outlier removal via managers sub-API
errors = api.managers.validate_outlier_inputs(df, "ipc", ["benchmark"])
if not errors:
    cleaned_df = api.managers.remove_outliers(df, "ipc", ["benchmark"])

# Save a pipeline via shapers sub-API
api.shapers.save_pipeline("my-pipeline", pipeline, "Normalize IPC by baseline")
```

### Scanning and parsing simulator output

```python
# Step 1: Find stats files
files = api.find_stats_files("/path/to/gem5/output")

# Step 2: Scan for variables
futures = api.submit_scan_async("/path/to/gem5/output", "stats.txt", limit=5)
raw_results = [f.result() for f in futures]
variables = api.finalize_scan(raw_results)

# Step 3: Parse selected variables
batch = api.submit_parse_async(
    stats_path="/path/to/gem5/output",
    stats_pattern="stats.txt",
    variables=selected_vars,
    output_dir="/tmp/ring5_parse",
)
results = [f.result() for f in batch.futures]
csv_path = api.finalize_parsing("/tmp/ring5_parse", results, var_names=batch.var_names)

# Step 4: Load parsed data
if csv_path:
    api.load_data(csv_path)
```

---

## Error Handling Patterns

`ApplicationAPI` follows consistent error handling conventions:

| Pattern | Methods | Behavior |
|---|---|---|
| Try-catch and re-raise | `load_data` | Catches `Exception`, logs the error, then re-raises so the UI can display it. |
| Graceful empty return | `find_stats_files` | Returns `[]` if the search path does not exist. |
| Static status | `get_parse_status`, `get_scanner_status` | Always return `"idle"`. The UI layer tracks real status via `st.session_state`. |
| Null safety | `get_column_info` | Accepts `None` and returns a zero-count `ColumnInfoResult`. |
| Boolean success/failure | `delete_configuration`, `delete_from_pool` | Return `False` on failure rather than raising. |

---

## See Also

- **Architecture overview:** `docs/developer-guide/architecture/` -- layer boundaries and
  design principles.
- **State management:** `src/core/state/repository_state_manager.py` -- the
  `RepositoryStateManager` that `ApplicationAPI` composes.
- **ServicesAPI protocol:** `src/core/services/services_api.py` -- the protocol definition
  for the three sub-APIs.
- **Services implementation:** `src/core/services/services_impl.py` -- the composition
  root (`DefaultServicesAPI`) that wires all sub-APIs.
- **ManagersAPI:** `src/core/services/managers/managers_api.py` -- arithmetic, outlier,
  and reduction operations.
- **DataServicesAPI:** `src/core/services/data_services/data_services_api.py` -- CSV pool,
  configuration, variable, and portfolio services.
- **ShapersAPI:** `src/core/services/shapers/shapers_api.py` -- pipeline and shaper
  operations.
- **Parsing protocol:** `src/parsing/parser_protocol.py` -- the `SimulationParser`
  protocol that parsing backends implement.
- **Data models:** `src/core/models/data_models.py` -- TypedDicts used across the API
  surface (`CsvPoolEntry`, `SavedConfigData`, `ColumnInfoResult`, etc.).
- **Visualization models:** `src/core/models/visualization/` -- `FigureConfig` and
  related dataclasses.
