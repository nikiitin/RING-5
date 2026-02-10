---
title: "Parsing API"
nav_order: 23
---

# Parsing API

<!-- markdownlint-disable MD024 -->

Complete API reference for RING-5's parsing and scanning services.

## Overview

The parsing system consists of two main services:

- **ScannerService**: Discovers available variables in gem5 stats
- **ParseService**: Extracts data from matched variables

Both services use asynchronous processing via `concurrent.futures` for parallel file processing.

## ScannerService

### Class: `ScannerService`

Discovers gem5 variables in stats files.

**Location**: `src/core/parsing/scanner_service.py`

#### Methods

##### `submit_scan_async(stats_path, stats_pattern, limit=None)`

Submit asynchronous scan jobs.

**Parameters**:

- `stats_path` (str | Path): Directory containing stats files
- `stats_pattern` (str): Filename pattern (e.g., "stats.txt")
- `limit` (int | None): Maximum variables to return (None = all)

**Returns**: `List[Future]` - List of Future objects for scan results

**Example**:

```python
from src.core.parsing.scanner_service import ScannerService

scanner = ScannerService()
futures = scanner.submit_scan_async(
    "/path/to/results",
    "stats.txt",
    limit=100
)

# Wait for completion
results = [f.result() for f in futures]
```

##### `finalize_scan(scan_results)`

Aggregate scan results from multiple futures.

**Parameters**:

- `scan_results` (List[Dict]): List of scan result dictionaries

**Returns**: `Dict[str, VariableInfo]` - Consolidated variables map

**Structure of VariableInfo**:

```python
{
    "name": str,          # Variable name
    "type": str,          # "scalar", "vector", "distribution", "histogram"
    "entries": List[str], # For vectors: entry names
    "min_value": float,   # For distributions: minimum
    "max_value": float,   # For distributions: maximum
    "num_bins": int,      # For histograms: bin count
}
```

**Example**:

```python
variables = scanner.finalize_scan(results)

# Access variable info
ipc_info = variables["system.cpu.ipc"]
print(f"Type: {ipc_info['type']}")
print(f"Name: {ipc_info['name']}")
```

## ParseService

### Class: `ParseService`

Extracts data from gem5 stats files.

**Location**: `src/core/parsing/parse_service.py`

#### Methods

##### `submit_parse_async(stats_path, stats_pattern, variables, output_dir, scanned_vars=None)`

Submit asynchronous parse jobs.

**Parameters**:

- `stats_path` (str | Path): Directory containing stats files
- `stats_pattern` (str): Filename pattern
- `variables` (List[str]): Variable names to parse
- `output_dir` (str | Path): Directory for output CSVs
- `scanned_vars` (Dict | None): Pre-scanned variable info (for regex variables)

**Returns**: `List[Future]` - List of Future objects for parse results

**Example**:

```python
from src.core.parsing.parse_service import ParseService

parser = ParseService()
futures = parser.submit_parse_async(
    stats_path="/path/to/results",
    stats_pattern="stats.txt",
    variables=["system.cpu.ipc", "system.cpu.numCycles"],
    output_dir="/path/to/output",
    scanned_vars=scanned_variables  # From scanner
)

# Wait for completion
results = [f.result() for f in futures]
```

##### `finalize_parsing(output_dir, parse_results)`

Consolidate individual CSV files into single DataFrame.

**Parameters**:

- `output_dir` (str | Path): Output directory
- `parse_results` (List[Dict]): List of parse result dictionaries

**Returns**: `str` - Path to consolidated CSV file

**Example**:

```python
csv_path = parser.finalize_parsing("/path/to/output", results)

# Load consolidated data
import pandas as pd
data = pd.read_csv(csv_path)
```

## Complete Workflow

### Scan → Parse → Load

```python
from src.core.parsing.scanner_service import ScannerService
from src.core.parsing.parse_service import ParseService
import pandas as pd

# Initialize services
scanner = ScannerService()
parser = ParseService()

# Step 1: Scan for variables
scan_futures = scanner.submit_scan_async(
    "/path/to/results",
    "stats.txt",
    limit=100
)
scan_results = [f.result() for f in scan_futures]
variables = scanner.finalize_scan(scan_results)

# Step 2: Select variables to parse
selected = ["system.cpu.ipc", "system.cpu\d+.numCycles"]

# Step 3: Parse selected variables
parse_futures = parser.submit_parse_async(
    "/path/to/results",
    "stats.txt",
    selected,
    "/output",
    scanned_vars=variables  # Important for regex variables!
)
parse_results = [f.result() for f in parse_futures]
csv_path = parser.finalize_parsing("/output", parse_results)

# Step 4: Load data
data = pd.read_csv(csv_path)
print(data.head())
```

## Pattern Aggregation

The scanner automatically aggregates repeated variables into regex patterns.

**Example**:

```text
Input variables:
  system.cpu0.ipc
  system.cpu1.ipc
  system.cpu2.ipc
  system.cpu3.ipc

Output (aggregated):
  system.cpu\d+.ipc [vector]
    entries: ["0", "1", "2", "3"]
```

**Usage**:

```python
# Scan discovers pattern
variables = scanner.finalize_scan(scan_results)

# Parse with regex pattern
futures = parser.submit_parse_async(
    ...,
    variables=["system.cpu\d+.ipc"],  # Pattern matches all cpus
    scanned_vars=variables  # Required!
)
```

## Worker Pool Management

### Class: `WorkPool`

Manages thread pool for async operations (singleton).

**Location**: `src/core/parsing/gem5/impl/pool/pool.py`

#### Methods

##### `get_instance()`

Get singleton WorkPool instance.

**Returns**: `WorkPool`

##### `submit_task(func, *args, **kwargs)`

Submit task to thread pool.

**Parameters**:

- `func` (Callable): Function to execute
- `*args`: Positional arguments
- `**kwargs`: Keyword arguments

**Returns**: `Future`

**Example**:

```python
from src.core.parsing.gem5.impl.pool.pool import ParseWorkPool

pool = ParseWorkPool.get_instance()
future = pool.submit_task(my_function, arg1, arg2, kwarg=value)
result = future.result()
```

## Error Handling

### Common Exceptions

**FileNotFoundError**:

```python
try:
    futures = scanner.submit_scan_async("/invalid/path", "stats.txt")
except FileNotFoundError as e:
    print(f"Stats directory not found: {e}")
```

**ValueError** (invalid variable type):

```python
try:
    variables = scanner.finalize_scan(results)
except ValueError as e:
    print(f"Invalid variable configuration: {e}")
```

**KeyError** (missing variable):

```python
try:
    futures = parser.submit_parse_async(
        ...,
        variables=["nonexistent.variable"],
        ...
    )
except KeyError as e:
    print(f"Variable not found: {e}")
```

## Type Definitions

### VariableInfo (TypedDict)

```python
from typing import TypedDict, List, Optional

class VariableInfo(TypedDict, total=False):
    name: str
    type: str  # "scalar" | "vector" | "distribution" | "histogram"
    entries: Optional[List[str]]  # For vectors
    min_value: Optional[float]    # For distributions
    max_value: Optional[float]    # For distributions
    num_bins: Optional[int]       # For histograms
```

## Best Practices

1. **Always pass scanned_vars to parser**: Required for regex variables
2. **Use finalize methods**: Don't access futures directly
3. **Handle errors**: Check for FileNotFoundError, ValueError
4. **Limit scan results**: Use `limit` parameter for large directories
5. **Clean up output**: Remove intermediate CSVs after consolidation

## Performance

**Parallel Processing**:

- Both services use thread pools
- Each stats file processed in parallel
- Scales linearly with CPU cores

**Memory Usage**:

- Scanner: O(variables) - stores variable metadata
- Parser: O(data points) - loads all parsed data

**Optimization Tips**:

- Limit scanned variables with `limit` parameter
- Parse only needed variables
- Use pattern aggregation to reduce variable count

## Next Steps

- Backend Facade: [Backend-Facade.md](Backend-Facade.md)
- Plotting API: [Plotting-API.md](Plotting-API.md)
- Architecture: [../Architecture.md](../Architecture.md)
