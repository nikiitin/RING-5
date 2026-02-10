# Skill: Debugging Async Parsing Issues

**Skill ID**: `debug-async-parsing`  
**Domain**: Troubleshooting  
**Complexity**: Intermediate

## Overview

Common issues with async parsing/scanning and how to resolve them.

## Problem 1: Futures Timing Out

### Symptoms

```python
concurrent.futures._base.TimeoutError: Future did not complete within 30 seconds
```

### Diagnosis

```python
# Add logging to see what's happening
import logging
logging.basicConfig(level=logging.DEBUG)

futures = facade.submit_parse_async(stats_path, pattern, variables, output_dir)
print(f"Submitted {len(futures)} parse tasks")

for i, future in enumerate(futures):
    try:
        result = future.result(timeout=60)  # Increase timeout
        print(f"Task {i} completed: {result}")
    except TimeoutError as e:
        print(f"Task {i} timed out!")
        raise
```

### Solutions

1. **Increase timeout**:

   ```python
   result = future.result(timeout=120)  # 2 minutes instead of 30s
   ```

2. **Check Perl script execution**:

   ```bash
   # Test Perl script directly
   perl src/parsers/perl/parse_scalar.pl \
       --stats-file=data/stats.txt \
       --pattern="system.cpu.ipc" \
       --output-csv=test_output.csv
   ```

3. **Verify file paths**:

   ```python
   from pathlib import Path

   stats_path = Path(stats_file)
   if not stats_path.exists():
       raise FileNotFoundError(f"Stats file not found: {stats_path}")

   output_dir = Path(output_directory)
   if not output_dir.exists():
       output_dir.mkdir(parents=True, exist_ok=True)
   ```

4. **Check pool capacity**:

   ```python
   from src.parsers.workers.work_pool import WorkPool

   pool = WorkPool.get_instance()
   print(f"Pool size: {pool.max_workers}")
   print(f"Active tasks: {len(pool.futures)}")

   # If pool is exhausted, wait for completion
   pool.wait_for_completion()
   ```

## Problem 2: Empty Results After Parsing

### Symptoms

```python
csv_path = facade.finalize_parsing(output_dir, parse_results)
data = facade.load_csv(csv_path)
print(len(data))  # 0 rows!
```

### Diagnosis

```python
# Check parse results
for i, result in enumerate(parse_results):
    print(f"Result {i}: {result}")
    if "error" in result:
        print(f"  ERROR: {result['error']}")
    if "csv_path" in result:
        csv_path = result["csv_path"]
        if Path(csv_path).exists():
            df = pd.read_csv(csv_path)
            print(f"  Rows: {len(df)}, Columns: {df.columns.tolist()}")
        else:
            print(f"  CSV not found: {csv_path}")
```

### Solutions

1. **Check regex pattern matches**:

   ```python
   # Test pattern matching
   import re

   pattern = "system\\.cpu\\.ipc"
   test_line = "system.cpu.ipc                        1.500000"

   if re.match(pattern, test_line):
       print("Pattern matches!")
   else:
       print("Pattern does NOT match - adjust regex")
   ```

2. **Verify scanned variables**:

   ```python
   # Ensure scan detected variables
   scan_futures = facade.submit_scan_async(stats_path, pattern, limit=10)
   scan_results = [f.result(timeout=30) for f in scan_futures]
   scanned_vars = facade.finalize_scan(scan_results)

   print(f"Scanned variables: {len(scanned_vars)}")
   for var in scanned_vars:
       print(f"  - {var['name']} ({var['type']})")

   if not scanned_vars:
       raise ValueError("No variables found - check pattern and stats file")
   ```

3. **Check Perl parser output**:

   ```python
   # Run parser manually and inspect output
   import subprocess

   result = subprocess.run([
       "perl", "src/parsers/perl/parse_scalar.pl",
       "--stats-file=data/stats.txt",
       "--pattern=system.cpu.ipc",
       "--output-csv=debug_output.csv"
   ], capture_output=True, text=True)

   print("STDOUT:", result.stdout)
   print("STDERR:", result.stderr)
   print("Return code:", result.returncode)

   if result.returncode != 0:
       print("Perl parser failed!")
   ```

## Problem 3: "Variable Not Found" After Scan

### Symptoms

```python
parse_futures = facade.submit_parse_async(
    stats_path, pattern, variables, output_dir,
    scanned_vars=scanned_vars
)
# Error: Variable 'system.cpu.ipc' not found in scanned variables
```

### Diagnosis

```python
# Check if pattern resolves to actual variables
print(f"Pattern: {pattern}")
print(f"Variables requested: {[v['name'] for v in variables]}")
print(f"Scanned variables: {[v['name'] for v in scanned_vars]}")

# Check for regex pattern
if re.search(r'[.*+?^${}()|[\]\\]', pattern):
    print("Pattern is a regex - must resolve against scanned vars")
```

### Solutions

1. **Use regex resolution**:

   ```python
   # For regex patterns, use scanner results
   pattern = "system\\.cpu\\.\\w+\\.ipc"  # Regex

   # Scan first
   scan_futures = facade.submit_scan_async(stats_path, pattern, limit=100)
   scan_results = [f.result() for f in scan_futures]
   scanned_vars = facade.finalize_scan(scan_results)

   # Parse using resolved variables
   parse_futures = facade.submit_parse_async(
       stats_path,
       pattern,
       scanned_vars,  # Use scanned vars as variables to parse
       output_dir,
       scanned_vars=scanned_vars
   )
   ```

2. **For literal names, wrap in list**:

   ```python
   # For literal (non-regex) variable names
   variables = [
       {"name": "system.cpu0.ipc", "type": "scalar"},
       {"name": "system.cpu1.ipc", "type": "scalar"}
   ]

   # No scan needed for literals
   parse_futures = facade.submit_parse_async(
       stats_path,
       "",  # Empty pattern - using explicit variables
       variables,
       output_dir,
       scanned_vars=None
   )
   ```

## Problem 4: CSV Merge Failures

### Symptoms

```python
csv_path = facade.finalize_parsing(output_dir, parse_results)
# Error: Cannot concatenate DataFrames - column mismatch
```

### Diagnosis

```python
# Check individual CSV files
for result in parse_results:
    csv_path = result.get("csv_path")
    if csv_path and Path(csv_path).exists():
        df = pd.read_csv(csv_path)
        print(f"{csv_path}: {df.columns.tolist()}")
```

### Solutions

1. **Ensure consistent variable types**:

   ```python
   # Don't mix variable types in one parse
   # BAD: mixing scalar and vector
   variables = [
       {"name": "system.cpu.ipc", "type": "scalar"},
       {"name": "system.cpu.opcodes", "type": "vector"}  # Different columns!
   ]

   # GOOD: separate by type
   scalar_vars = [{"name": "system.cpu.ipc", "type": "scalar"}]
   vector_vars = [{"name": "system.cpu.opcodes", "type": "vector"}]

   # Parse separately
   scalar_futures = facade.submit_parse_async(stats_path, "", scalar_vars, output_dir)
   vector_futures = facade.submit_parse_async(stats_path, "", vector_vars, output_dir)
   ```

2. **Use type-specific output directories**:

   ```python
   from pathlib import Path

   base_dir = Path("output")
   scalar_dir = base_dir / "scalar"
   vector_dir = base_dir / "vector"

   scalar_dir.mkdir(parents=True, exist_ok=True)
   vector_dir.mkdir(parents=True, exist_ok=True)

   # Parse with separate directories
   scalar_futures = facade.submit_parse_async(
       stats_path, pattern, scalar_vars, str(scalar_dir)
   )
   vector_futures = facade.submit_parse_async(
       stats_path, pattern, vector_vars, str(vector_dir)
   )
   ```

## Problem 5: Memory Issues with Large Files

### Symptoms

```python
MemoryError: Unable to allocate array
# or
Process killed (OOM)
```

### Solutions

1. **Limit scan results**:

   ```python
   # Don't scan everything
   scan_futures = facade.submit_scan_async(
       stats_path,
       pattern,
       limit=100  # Limit to first 100 matches
   )
   ```

2. **Process in batches**:

   ```python
   # Parse in smaller batches
   batch_size = 50
   all_results = []

   for i in range(0, len(variables), batch_size):
       batch = variables[i:i+batch_size]
       futures = facade.submit_parse_async(
           stats_path, "", batch, output_dir
       )
       results = [f.result() for f in futures]
       all_results.extend(results)

       # Clean up between batches
       WorkPool.get_instance().wait_for_completion()
   ```

3. **Use chunked CSV reading**:

   ```python
   # For huge CSV files
   chunks = []
   for chunk in pd.read_csv(csv_path, chunksize=10000):
       # Process chunk
       processed = process(chunk)
       chunks.append(processed)

   result = pd.concat(chunks, ignore_index=True)
   ```

## Debugging Checklist

When async parsing fails:

- [ ] Check file paths exist
- [ ] Verify regex pattern matches expected lines
- [ ] Confirm scan found variables
- [ ] Test Perl scripts directly
- [ ] Check parse result errors
- [ ] Verify CSV files were created
- [ ] Inspect CSV column names
- [ ] Check pool status and capacity
- [ ] Review timeout values
- [ ] Test with smaller dataset first

## Useful Debug Snippets

### Enable verbose logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now all facade operations will log details
```

### Inspect pool state

```python
from src.parsers.workers.work_pool import WorkPool
from src.parsers.workers.scan_work_pool import ScanWorkPool

parse_pool = WorkPool.get_instance()
scan_pool = ScanWorkPool.get_instance()

print(f"Parse pool: {parse_pool.max_workers} workers, {len(parse_pool.futures)} active")
print(f"Scan pool: {scan_pool.max_workers} workers, {len(scan_pool.futures)} active")
```

### Test pattern matching

```python
import re

def test_pattern(pattern, test_lines):
    \"\"\"Test if pattern matches test lines.\"\"\"
    for line in test_lines:
        if re.match(pattern, line):
            print(f"✓ MATCH: {line}")
        else:
            print(f"✗ NO MATCH: {line}")

# Example
test_lines = [
    "system.cpu.ipc                        1.500000",
    "system.cpu0.ipc                       1.600000",
    "system.cpu1.ipc                       1.400000"
]

test_pattern(r"system\.cpu\d*\.ipc", test_lines)
```

## References

- Async API Documentation: `src/web/facade.py`
- Work Pool Implementation: `src/parsers/workers/work_pool.py`
- Perl Parsers: `src/parsers/perl/`
- Integration Tests: `tests/integration/test_gem5_parsing.py`
