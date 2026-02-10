---
title: "Parsing Guide"
nav_order: 6
---

# Parsing gem5 Statistics

Complete guide to parsing gem5 simulator output with RING-5.

## Overview

RING-5 provides a powerful async-first parsing system for gem5 stats.txt files:

- **Parallel Processing** - Parse multiple files simultaneously
- **Type Detection** - Automatic variable type recognition
- **Pattern Aggregation** - Consolidate repeated variables (cpu0, cpu1 → cpu\d+)
- **Progress Tracking** - Real-time feedback during parsing

## Parsing Workflow

### 1. Scan for Variables

Discover all available statistics in your gem5 output:

```python
from src.web.facade import BackendFacade

facade = BackendFacade()

# Submit async scan
scan_futures = facade.submit_scan_async(
 stats_path="/path/to/gem5/output",
 stats_pattern="stats.txt",
 limit=10 # Number of files to scan (-1 for all)
)

# Wait for completion
scan_results = []
for future in scan_futures:
 try:
 result = future.result(timeout=30)
 if result:
 scan_results.append(result)
 except Exception as e:
 print(f"Scan failed: {e}")

# Aggregate discovered variables
variables = facade.finalize_scan(scan_results)
print(f"Found {len(variables)} variables")
```

**What Scanning Does**:

- Reads gem5 stats files
- Detects variable types (scalar, vector, histogram, etc.)
- Identifies vector entries
- Aggregates repeated patterns
- Returns structured variable list

### 2. Select Variables

Choose which variables to parse:

```python
# Filter by type
scalar_vars = [v for v in variables if v["type"] == "scalar"]
vector_vars = [v for v in variables if v["type"] == "vector"]

# Select specific variables
selected = [
 {"name": "simTicks", "type": "scalar"},
 {"name": "system.cpu.ipc", "type": "scalar"},
 {
 "name": "system.cpu.op_class",
 "type": "vector",
 "vectorEntries": ["IntAlu", "IntMult", "FloatAdd"]
 }
]
```

**Variable Structure**:

```python
{
 "name": "system.cpu.ipc",
 "type": "scalar", # or vector, histogram, distribution, configuration
 "entries": [], # For vectors: list of entry names
 "min": 0.0, # For histograms: minimum value
 "max": 100.0, # For histograms: maximum value
}
```

### 3. Parse Data

Extract actual values:

```python
import tempfile

output_dir = tempfile.mkdtemp()

# Submit async parse
parse_futures = facade.submit_parse_async(
 stats_path="/path/to/gem5/output",
 stats_pattern="stats.txt",
 variables=selected,
 output_dir=output_dir,
 scanned_vars=variables # REQUIRED for pattern variables
)

# Wait for completion
parse_results = []
for future in parse_futures:
 try:
 result = future.result(timeout=60)
 if result:
 parse_results.append(result)
 except Exception as e:
 print(f"Parse failed: {e}")

# Finalize to consolidated CSV
csv_path = facade.finalize_parsing(output_dir, parse_results)
print(f"Data saved to: {csv_path}")
```

### 4. Load Data

```python
import pandas as pd

# Load parsed data
data = pd.read_csv(csv_path)
print(data.head())
```

## gem5 Variable Types

### Scalar

Single numeric values:

```text
simTicks 123456789 # Total simulation ticks
system.cpu.ipc 1.23 # Instructions per cycle
```

Parse as:

```python
{"name": "simTicks", "type": "scalar"}
```

### Vector

Arrays with named entries:

```text
system.cpu.op_class::IntAlu 1234
system.cpu.op_class::IntMult 567
system.cpu.op_class::FloatAdd 890
```

Parse as:

```python
{
 "name": "system.cpu.op_class",
 "type": "vector",
 "vectorEntries": ["IntAlu", "IntMult", "FloatAdd"]
}
```

### Histogram

Distribution with buckets:

```text
system.cpu.latency::histogram
 0-10: 45
 10-20: 123
 20-30: 67
```

Parse as:

```python
{
 "name": "system.cpu.latency",
 "type": "histogram",
 "min": 0,
 "max": 30
}
```

### Distribution

Statistical distribution with min/max:

```text
system.mem.latency
 min: 10
 max: 500
 mean: 45.6
```

Parse as:

```python
{"name": "system.mem.latency", "type": "distribution"}
```

### Configuration

gem5 configuration values:

```text
system.cpu.type AtomicSimpleCPU
system.mem.size 2GB
```

Parse as:

```python
{"name": "system.cpu.type", "type": "configuration"}
```

## Pattern Aggregation

RING-5 automatically consolidates repeated variables:

### Before Aggregation

```text
system.cpu0.numCycles
system.cpu1.numCycles
system.cpu2.numCycles
...
system.cpu15.numCycles
```

### After Aggregation

```text
system.cpu\d+.numCycles [vector]
 entries: ["0", "1", "2", ..., "15"]
```

**Benefit**: Reduces 12,000+ variables to ~700 manageable patterns.

### Using Pattern Variables

When parsing pattern variables, always pass `scanned_vars`:

```python
# Pattern variable with regex
pattern_var = {
 "name": r"system.cpu\d+.ipc",
 "type": "scalar"
}

# MUST pass scanned_vars to resolve patterns
parse_futures = facade.submit_parse_async(
 stats_path=path,
 stats_pattern="stats.txt",
 variables=[pattern_var],
 output_dir=output_dir,
 scanned_vars=variables # Critical!
)
```

## Advanced Parsing

### Limit Files

For large directories, parse subset first:

```python
scan_futures = facade.submit_scan_async(
 stats_path=path,
 stats_pattern="stats.txt",
 limit=5 # Only scan 5 files
)
```

### Multiple Patterns

Parse different file patterns:

```python
# Scan all .txt files
scan_futures = facade.submit_scan_async(
 stats_path=path,
 stats_pattern="*.txt",
 limit=-1
)
```

### Error Handling

```python
scan_results = []
failed = []

for future in scan_futures:
 try:
 result = future.result(timeout=30)
 if result:
 scan_results.append(result)
 except TimeoutError:
 failed.append("Timeout")
 except Exception as e:
 failed.append(str(e))

if failed:
 print(f"Failed scans: {len(failed)}")
 for err in failed:
 print(f" - {err}")
```

## Performance Tips

1. **Limit scans** for testing: `limit=5`
2. **Parallel processing** is automatic
3. **Cache scanned variables** in StateManager
4. **Batch parse** multiple variables at once
5. **Monitor memory** with large datasets

## Common Issues

### No Variables Found

- Verify stats.txt files exist
- Check file pattern matches
- Ensure files are not empty
- Verify file permissions

### Parsing Timeouts

- Increase timeout value
- Reduce number of files
- Check for corrupted files
- Verify sufficient memory

### Pattern Variables Not Resolving

- Always pass `scanned_vars` parameter
- Verify patterns match variable names
- Check entries are correct

### Memory Issues

- Parse fewer files at once
- Clear data between analyses
- Use CSV pooling
- Increase system RAM

## UI Workflow

In the Streamlit interface:

1. **Data Sources** tab → **Browse** directory
2. Enter pattern: `stats.txt`
3. Click **Scan for Variables**
4. Filter/search variables
5. Select desired variables
6. Click **Parse Statistics**
7. Monitor progress bar
8. Data loads automatically

## Best Practices

**DO**:

- Scan before parsing
- Start with small limits for testing
- Cache scanned variables
- Handle timeouts gracefully
- Validate data after parsing

  **DON'T**:

- Skip scanning step
- Parse without selecting variables
- Forget scanned_vars for patterns
- Ignore error handling
- Parse entire large directories without testing

## Next Steps

- [Data Transformations](Data-Transformations) - Process parsed data
- [Creating Plots](Creating-Plots) - Visualize results
- [Pattern Aggregation](Pattern-Aggregation) - Deep dive into patterns

**Need help?** [Debugging Guide](Debugging) or [Open an issue](https://github.com/vnicolas/RING-5/issues)
