# Backend Facade

Complete API reference for RING-5's unified backend interface.

## Overview

The `BackendFacade` provides a single entry point to all backend services. It implements the **Facade Pattern**, simplifying interactions with parsing, scanning, CSV management, and configuration.

**Location**: `src/web/facade.py`

## BackendFacade Class

### Initialization

```python
from src.web.facade import BackendFacade

facade = BackendFacade()
```

The facade is typically instantiated once and accessed through the UI layer.

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
futures = facade.submit_scan_async(
    "/path/to/results",
    "stats.txt",
    limit=100
)

# Wait for completion
results = [f.result() for f in futures]
```

### `finalize_scan(scan_results)`

Aggregate scan results into unified variable map.

**Parameters**:
- `scan_results` (List[Dict]): Results from scan futures

**Returns**: `Dict[str, VariableInfo]` - Variable information map

**Example**:
```python
variables = facade.finalize_scan(results)

# Iterate variables
for name, info in variables.items():
    print(f"{name}: {info['type']}")
```

## Parsing Methods

### `submit_parse_async(stats_path, stats_pattern, variables, output_dir, scanned_vars=None)`

Submit asynchronous parsing jobs.

**Parameters**:
- `stats_path` (str | Path): Stats directory
- `stats_pattern` (str): Filename pattern
- `variables` (List[str]): Variables to parse
- `output_dir` (str | Path): Output directory
- `scanned_vars` (Dict | None): Pre-scanned variable info

**Returns**: `List[Future]` - Future objects for parse results

**Example**:
```python
futures = facade.submit_parse_async(
    stats_path="/path/to/results",
    stats_pattern="stats.txt",
    variables=["system.cpu.ipc", "system.cpu\d+.numCycles"],
    output_dir="/output",
    scanned_vars=scanned_variables
)

results = [f.result() for f in futures]
```

### `finalize_parsing(output_dir, parse_results)`

Consolidate parsed CSVs into single file.

**Parameters**:
- `output_dir` (str | Path): Output directory
- `parse_results` (List[Dict]): Results from parse futures

**Returns**: `str` - Path to consolidated CSV

**Example**:
```python
csv_path = facade.finalize_parsing("/output", results)
```

## CSV Management Methods

### `load_csv_file(csv_path)`

Load CSV file into DataFrame.

**Parameters**:
- `csv_path` (str | Path): Path to CSV file

**Returns**: `pd.DataFrame` - Loaded data

**Raises**: `FileNotFoundError` - If file doesn't exist

**Example**:
```python
data = facade.load_csv_file("/output/consolidated.csv")
print(data.head())
```

### `get_csv_columns(csv_path)`

Get column names from CSV without loading full data.

**Parameters**:
- `csv_path` (str | Path): Path to CSV

**Returns**: `List[str]` - Column names

**Example**:
```python
columns = facade.get_csv_columns("/output/data.csv")
print(f"Available columns: {columns}")
```

### `list_csv_files(directory)`

List all CSV files in directory.

**Parameters**:
- `directory` (str | Path): Directory to search

**Returns**: `List[Path]` - List of CSV file paths

**Example**:
```python
csv_files = facade.list_csv_files("/output")
for csv in csv_files:
    print(csv.name)
```

## Configuration Methods

### `get_config(key, default=None)`

Get configuration value.

**Parameters**:
- `key` (str): Configuration key
- `default` (Any): Default value if key not found

**Returns**: Configuration value

**Example**:
```python
max_workers = facade.get_config("max_workers", default=4)
output_dir = facade.get_config("output_directory")
```

### `set_config(key, value)`

Set configuration value.

**Parameters**:
- `key` (str): Configuration key
- `value` (Any): Configuration value

**Example**:
```python
facade.set_config("max_workers", 8)
facade.set_config("output_directory", "/custom/output")
```

## Complete Workflow Example

### Scan → Parse → Load → Transform → Plot

```python
import streamlit as st
import pandas as pd
from src.web.facade import BackendFacade
from src.web.services.shapers.shaper_factory import ShaperFactory
from src.plotting.plot_factory import PlotFactory

# Initialize
facade = BackendFacade()

# Step 1: Scan for variables
st.write("Scanning variables...")
scan_futures = facade.submit_scan_async(
    "/path/to/results",
    "stats.txt",
    limit=100
)
scan_results = [f.result() for f in scan_futures]
variables = facade.finalize_scan(scan_results)
st.success(f"Found {len(variables)} variables")

# Step 2: Select and parse
selected_vars = ["system.cpu.ipc", "system.cpu.numCycles"]
st.write(f"Parsing {len(selected_vars)} variables...")

parse_futures = facade.submit_parse_async(
    "/path/to/results",
    "stats.txt",
    selected_vars,
    "/output",
    scanned_vars=variables
)
parse_results = [f.result() for f in parse_futures]
csv_path = facade.finalize_parsing("/output", parse_results)
st.success("Parsing complete")

# Step 3: Load and transform
data = facade.load_csv_file(csv_path)

# Apply shapers
sort_shaper = ShaperFactory.create_shaper("sort", {
    "column": "system.cpu.ipc",
    "ascending": False
})
data = sort_shaper(data)

# Step 4: Plot
plot = PlotFactory.create_plot("bar", plot_id=1, name="IPC Comparison")
plot.config = {
    "x_column": "benchmark",
    "y_column": "system.cpu.ipc",
    "title": "IPC by Benchmark"
}
fig = plot.create_figure(data)
st.plotly_chart(fig, use_container_width=True)
```

## Integration with State Management

The facade integrates with `StateManager` for Streamlit state:

```python
from src.web.state_manager import StateManager

# After scanning
variables = facade.finalize_scan(scan_results)
StateManager.set_scanned_variables(variables)

# After parsing
csv_path = facade.finalize_parsing(output_dir, parse_results)
StateManager.set_csv_path(csv_path)

# Loading data
data = facade.load_csv_file(StateManager.get_csv_path())
StateManager.set_current_data(data)
```

## Error Handling

### Common Patterns

**Scanning errors**:
```python
try:
    futures = facade.submit_scan_async(stats_path, pattern)
    results = [f.result() for f in futures]
    variables = facade.finalize_scan(results)
except FileNotFoundError:
    st.error("Stats directory not found")
except Exception as e:
    st.error(f"Scan failed: {e}")
```

**Parsing errors**:
```python
try:
    futures = facade.submit_parse_async(...)
    results = [f.result() for f in futures]
    csv_path = facade.finalize_parsing(output_dir, results)
except KeyError as e:
    st.error(f"Variable not found: {e}")
except ValueError as e:
    st.error(f"Invalid configuration: {e}")
```

**CSV loading errors**:
```python
try:
    data = facade.load_csv_file(csv_path)
except FileNotFoundError:
    st.error("CSV file not found")
except pd.errors.ParserError:
    st.error("Invalid CSV format")
```

## Performance Considerations

**Async Operations**:
- Scanning and parsing use thread pools
- Number of workers: `facade.get_config("max_workers", default=4)`
- Scales with CPU cores

**Memory Usage**:
- CSV loading loads full DataFrame into memory
- For large files, use chunked reading or filtering

**Optimization Tips**:
1. Limit scan results: `limit=100` parameter
2. Parse only needed variables
3. Apply column selection shaper early
4. Use pattern aggregation to reduce variable count

## Best Practices

1. **Single Facade Instance**: Create once, reuse throughout session
2. **Always finalize**: Call `finalize_scan()` and `finalize_parsing()`
3. **Pass scanned_vars**: Required for regex variable parsing
4. **Handle errors**: Wrap facade calls in try/except
5. **Use State Manager**: Integrate with Streamlit state for UI consistency

## Next Steps

- Parsing API: [Parsing-API.md](Parsing-API.md)
- Plotting API: [Plotting-API.md](Plotting-API.md)
- Shaper API: [Shaper-API.md](Shaper-API.md)
- Architecture: [../Architecture.md](../Architecture.md)
