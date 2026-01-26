# Skill: gem5 Stats Parsing Workflow

**Skill ID**: `parsing-workflow`  
**Domain**: gem5 Statistics Parsing  
**Complexity**: Advanced

## Purpose

Guide the implementation of complete parsing workflows for gem5 simulator statistics, following the async-first architecture.

## Prerequisites

- Understanding of gem5 stats.txt format
- Knowledge of async/await patterns
- Familiarity with BackendFacade API

## Workflow Steps

### 1. Variable Scanning Phase

```python
from src.web.facade import BackendFacade

facade = BackendFacade()

# Submit async scan
scan_futures = facade.submit_scan_async(
    stats_path="/path/to/stats",
    stats_pattern="stats.txt",
    limit=10  # -1 for all files
)

# Wait for completion
scan_results = []
for future in scan_futures:
    try:
        result = future.result(timeout=30)
        if result:
            scan_results.append(result)
    except Exception as e:
        logger.error(f"Scan failed: {e}")

# Aggregate results
discovered_variables = facade.finalize_scan(scan_results)
```

### 2. Variable Selection Phase

```python
# Filter by type
scalar_vars = [v for v in discovered_variables if v["type"] == "scalar"]
vector_vars = [v for v in discovered_variables if v["type"] == "vector"]

# Pattern matching for regex variables
import re
cpu_ipc_pattern = r"system\.cpu\d+\.ipc"
matching_vars = [
    v for v in discovered_variables
    if re.match(cpu_ipc_pattern, v["name"])
]

# Build variable configuration
selected_vars = [
    {"name": "simTicks", "type": "scalar"},
    {"name": "system.cpu0.ipc", "type": "scalar"},
    {
        "name": "system.cpu.op_class",
        "type": "vector",
        "vectorEntries": ["IntAlu", "IntMult", "FloatAdd"]
    }
]
```

### 3. Parsing Phase

```python
import tempfile

output_dir = tempfile.mkdtemp()

# Submit async parse
parse_futures = facade.submit_parse_async(
    stats_path="/path/to/stats",
    stats_pattern="stats.txt",
    variables=selected_vars,
    output_dir=output_dir,
    scanned_vars=discovered_variables  # For regex resolution
)

# Wait for completion
parse_results = []
for future in parse_futures:
    try:
        result = future.result(timeout=60)
        if result:
            parse_results.append(result)
    except Exception as e:
        logger.error(f"Parse failed: {e}")

# Finalize to CSV
csv_path = facade.finalize_parsing(output_dir, parse_results)
```

### 4. Data Loading & Processing

```python
# Load parsed data
data = facade.load_csv_file(csv_path)

# Apply transformations
from src.web.services.shapers.factory import ShaperFactory

shapers_pipeline = [
    {"type": "column_selector", "columns": ["simTicks", "system.cpu0.ipc"]},
    {"type": "filter", "column": "simTicks", "condition": ">", "value": 1000},
    {"type": "normalize", "columns": ["system.cpu0.ipc"], "by": "simTicks"}
]

processed_data = facade.apply_shapers(data, shapers_pipeline)
```

## Error Handling

```python
from pathlib import Path

# Validate paths
stats_path = Path("/path/to/stats")
if not stats_path.exists():
    raise FileNotFoundError(f"Stats path not found: {stats_path}")

# Check for files
files = list(stats_path.rglob("stats.txt"))
if not files:
    raise FileNotFoundError(f"No stats files found in {stats_path}")

# Validate variables
if not selected_vars:
    raise ValueError("At least one variable must be specified")

# Handle parsing failures
if not csv_path or not Path(csv_path).exists():
    raise RuntimeError("Parsing failed to generate CSV")
```

## Testing Pattern

```python
def test_parsing_workflow():
    """Test complete parsing workflow."""
    facade = BackendFacade()

    # 1. Scan
    scan_futures = facade.submit_scan_async(test_path, "stats.txt", limit=5)
    scan_results = [f.result(timeout=10) for f in scan_futures]
    variables = facade.finalize_scan(scan_results)

    assert len(variables) > 0

    # 2. Parse
    selected = [v for v in variables if v["type"] == "scalar"][:3]
    parse_futures = facade.submit_parse_async(
        test_path, "stats.txt", selected, output_dir, scanned_vars=variables
    )
    parse_results = [f.result(timeout=10) for f in parse_futures]
    csv_path = facade.finalize_parsing(output_dir, parse_results)

    assert csv_path is not None
    assert Path(csv_path).exists()

    # 3. Verify
    df = pd.read_csv(csv_path)
    assert len(df) > 0
    assert all(col in df.columns for col in [v["name"] for v in selected])
```

## Common Pitfalls

❌ **DON'T**: Create synchronous wrappers  
✅ **DO**: Use async primitives (submit*\*\_async + finalize*\*)

❌ **DON'T**: Forget to pass scanned_vars for regex resolution  
✅ **DO**: Always pass scanned_vars when using regex patterns

❌ **DON'T**: Ignore timeout exceptions  
✅ **DO**: Set reasonable timeouts and handle failures

❌ **DON'T**: Parse without scanning first (for regex vars)  
✅ **DO**: Scan → Select → Parse

## Integration with Streamlit

```python
import streamlit as st
from src.web.state_manager import StateManager

# In UI code
if st.button("Parse Statistics"):
    with st.spinner("Scanning for variables..."):
        scan_futures = facade.submit_scan_async(stats_path, pattern, limit=10)
        # Show progress
        progress = st.progress(0)
        scan_results = []
        for i, future in enumerate(scan_futures):
            result = future.result()
            if result:
                scan_results.append(result)
            progress.progress((i + 1) / len(scan_futures))

        variables = facade.finalize_scan(scan_results)
        StateManager.set_scanned_variables(variables)
        st.success(f"Found {len(variables)} variables!")
```

## Performance Tips

1. **Limit scan files**: Use `limit` parameter for large directories
2. **Parallel processing**: Futures run in parallel automatically
3. **Cache results**: Store scanned variables in StateManager
4. **Batch variables**: Parse multiple variables in one call
5. **Timeout appropriately**: Longer for large files, shorter for quick scans

## References

- Implementation: `src/parsers/parse_service.py`, `src/parsers/scanner_service.py`
- Tests: `tests/integration/test_gem5_parsing.py`
- UI Example: `src/web/ui/components/data_source_components.py`
