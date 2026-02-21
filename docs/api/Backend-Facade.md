---
title: "Application API"
nav_order: 22
---

## Application API

Complete API reference for RING-5's unified backend interface.

## Overview

The `ApplicationAPI` provides a single entry point to all backend services. It implements the **Facade Pattern**, orchestrating the interaction between Core Services, StateManager, and the Presentation Layer.

**Location**: `src/core/application_api.py`

## ApplicationAPI Class

### Initialization

```python
from src.core.application_api import ApplicationAPI

api = ApplicationAPI()
```

The API is typically instantiated once and accessed through the UI layer.

### Sub-API Access

```python
# Stateless data transformation operations
api.managers.apply_operation(data, operator, columns)

# Data storage, retrieval, and domain entity management
api.data_services.load_csv_pool()

# Pipeline and shaper operations
api.shapers.process_pipeline(data, pipeline_steps)
```

## Scanning Methods

### `submit_scan_async(stats_path, stats_pattern, limit=None)`

Submit asynchronous variable scanning jobs.

**Parameters**:

- `stats_path` (str | Path): Directory containing stats files
- `stats_pattern` (str): Filename pattern (e.g., "stats.txt")
- `limit` (int | None): Maximum variables to discover

**Returns**: `List[Future]` - Future objects for scan results

**Example**:

```python
futures = api.submit_scan_async(
    "/path/to/results",
    "stats.txt",
    limit=100
)
results = [f.result() for f in futures]
```

### `finalize_scan(scan_results)`

Aggregate scan results into unified variable list.

**Parameters**:

- `scan_results` (List[List]): Results from scan futures

**Returns**: `List[Any]` - Aggregated variable information

## Parsing Methods

### `submit_parse_async(stats_path, stats_pattern, variables, output_dir, ...)`

Submit asynchronous parsing jobs.

**Parameters**:

- `stats_path` (str | Path): Stats directory
- `stats_pattern` (str): Filename pattern
- `variables` (List[Dict]): Variables to parse
- `output_dir` (str | Path): Output directory
- `scanned_vars` (List | None): Pre-scanned variable info

**Returns**: `List[Future]` - Future objects for parse results

### `finalize_parsing(output_dir, parse_results)`

Consolidate parsed CSVs into single file.

**Parameters**:

- `output_dir` (str | Path): Output directory
- `parse_results` (List[Dict]): Results from parse futures

**Returns**: `str` - Path to consolidated CSV

## Data Access Methods

### `load_csv_file(file_path)`

Load CSV file into DataFrame.

**Parameters**:

- `file_path` (str): Path to CSV file

**Returns**: `DataFrame` - Loaded data

### `load_csv_pool()`

List CSV files in the pool.

**Returns**: `List[Dict]` - Pool entries

### `add_to_csv_pool(file_path)`

Add CSV file to pool.

### `delete_from_csv_pool(file_path)`

Remove CSV file from pool.

### `get_column_info(df)`

Get detailed column metadata for a DataFrame.

**Returns**: `Dict[str, Any]` with `total_columns`, `numeric_columns`, `string_columns`, etc.

## Configuration Methods

### `save_configuration(config, name, description)`

Save configuration to disk.

### `load_configuration(config_path)`

Load configuration from disk.

### `load_saved_configs()`

List all saved configurations.

### `delete_configuration(config_path)`

Delete a saved configuration.

## Visualization Config Methods

### `get_visualization_config(plot_id)`

Get the FigureConfig for a specific plot.

**Parameters**:

- `plot_id` (int): Plot identifier

**Returns**: `FigureConfig | None`

### `set_visualization_config(plot_id, config)`

Store a FigureConfig for a specific plot.

**Parameters**:

- `plot_id` (int): Plot identifier
- `config` (FigureConfig): Visualization configuration

### `remove_visualization_config(plot_id)`

Remove stored visualization config for a plot.

## Preview Methods

### `set_preview(operation_name, data)` / `get_preview(operation_name)`

Store and retrieve preview data for data manager operations.

### `has_preview(operation_name)` / `clear_preview(operation_name)`

Check and clear preview state.

## History Methods

### `add_manager_history_record(record)`

Add an operation record to manager history.

### `get_manager_history()` / `get_portfolio_history()`

Retrieve operation histories.

## Complete Workflow Example

```python
from src.core.application_api import ApplicationAPI

api = ApplicationAPI()

# Step 1: Scan for variables
scan_futures = api.submit_scan_async("/path/to/results", "stats.txt", limit=100)
scan_results = [f.result() for f in scan_futures]
variables = api.finalize_scan(scan_results)

# Step 2: Parse selected variables
selected_vars = [{"name": "system.cpu.ipc", "type": "scalar"}]
parse_futures = api.submit_parse_async(
    "/path/to/results", "stats.txt", selected_vars, "/output",
    scanned_vars=variables
)
parse_results = [f.result() for f in parse_futures]
csv_path = api.finalize_parsing("/output", parse_results)

# Step 3: Load and transform
data = api.load_csv_file(csv_path)
pipeline_steps = [{"type": "sort", "column": "system.cpu.ipc", "ascending": False}]
data = api.apply_shapers(data, pipeline_steps)

# Step 4: Visualize
config = api.get_visualization_config(plot_id=1)
```

## Error Handling

```python
try:
    futures = api.submit_scan_async(stats_path, pattern)
    results = [f.result() for f in futures]
    variables = api.finalize_scan(results)
except FileNotFoundError:
    st.error("Stats directory not found")
except Exception as e:
    st.error(f"Scan failed: {e}")
```

## Next Steps

- [Parsing API](Parsing-API.md)
- [Plotting API](Plotting-API.md)
- [Shaper API](Shaper-API.md)
- [Architecture](../Architecture.md)
