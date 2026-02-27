# Track 7: Data Volume & File Discovery

**Status**: DONE
**Priority**: P1
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_07_data_volume.md`

---

## Goal

Quantify the workload scale and understand how data volume multiplies through the pipeline.

## Files Analyzed

- `src/parsing/gem5/impl/gem5_parser.py` — lines 113-183 (regex expansion)
- `src/parsing/gem5/impl/strategies/simple.py` — lines 110-176 (`_get_files()`, `_map_variables()`)
- `src/parsing/gem5/impl/gem5_scanner.py` — lines 30-62 (file sampling)

---

## Findings

### 1. CRITICAL — `rglob()` ALWAYS Scans Entire Tree Regardless of Limit

**Location**: `gem5_scanner.py:52-56`

```python
files: list[Path] = sorted(search_path.rglob(safe_pattern))  # Full tree scan
files_to_sample: list[Path] = files[:limit] if limit > 0 else files  # Then slice
```

`rglob()` traverses the entire directory tree BEFORE the limit is applied. For a directory with 66,000 entries, only 5 are used (default `limit=5`).

- Efficiency: 5/66,000 = 0.0076% (99.99% wasted I/O)
- Same issue in `simple.py:128-141` with `base.glob(f"**/{safe_pattern}")`

**Severity**: CRITICAL (full filesystem traversal even for small samples)

### 2. CRITICAL — Regex Config Multiplication

**Location**: `gem5_parser.py:113-177`

One regex config can expand to N concrete configs:

```python
for config in variables:
    if config.is_regex:
        for sv in scanned_vars:
            if pattern.fullmatch(sv.name):
                matched_ids.append(sv_name)
        if config.keep_indices:
            for cname in concrete_names:
                individual = replace(config, name=cname, ...)
                processed_configs.append(individual)  # 1 input → N outputs!
```

**Expansion example**: `system.cpu.*` with 32 CPUs → 32 separate configs.

**Severity**: CRITICAL (exponential config growth with CPU/controller count)

### 3. CRITICAL — Repeat Count Compounding

**Location**: `simple.py:160-166`

```python
if parsed_ids:
    stat_obj = TypeMapper.create_stat(
        replace(var, repeat=len(parsed_ids))  # Repeat = number of matched IDs
    )
```

The `repeat` count directly controls `balance_content()` and `reduce_duplicates()` inner loop iterations. With 32 CPUs: `repeat=32` means 32x work per variable per file in CSV construction.

**Scaling with CPU/Controller Count**:
```
system.cpu.*        (C CPUs)          → repeat = C
system.cpu.*.thread.* (C × T threads) → repeat = C×T
system.cache.*      (K caches)        → repeat = K

Example (4-core x 2-thread, 4 caches):
  base=50 variables → ~850 effective configs
  each with repeat=8-32
```

**Severity**: CRITICAL

### 4. CRITICAL — Variable Aliasing Shares Object State

**Location**: `simple.py:172-174`

```python
for pid in parsed_ids:
    if pid != name:
        var_map[pid] = stat_obj  # Same object referenced multiple times!
```

All aliases point to the same `StatType` object. When `balance_content()` is called on one alias, it mutates state for ALL aliases. This is safe in the current serial post-processing, but dangerous if accessed concurrently.

**Severity**: CRITICAL (shared mutable state, currently safe by accident)

### 5. HIGH — Deepcopy Cost Scales with Variable Count

**Location**: `simple.py:115-120`

```python
works = [
    Gem5ParseWork(str(file_path), copy.deepcopy(template_map))
    for file_path in files
]
```

Each file gets a full deepcopy of the template_map. With 850 variable configs × 50 files = 42,500 object copies. Measured at ~0.04s for 586 files (Track 1), so currently fast, but scales linearly.

**Severity**: HIGH (linear scaling, acceptable for now)

### 6. INFO — File Discovery Pattern

**Location**: `simple.py:128-141`

```python
safe_pattern = sanitize_glob_pattern(stats_pattern)
pattern = f"**/{safe_pattern}"  # Recursive glob
files = [str(f) for f in base.glob(pattern)]
```

The `**` makes this recursive through entire directory tree. Typical patterns: `stats.txt`. No depth limit.

---

## Workload Multiplication Pipeline

```
Step 1: File Discovery
  Input: directory path + "stats.txt"
  Output: N files (could be 5 to 10,000+)
  Cost: O(total_directory_entries) regardless of N

Step 2: Regex Expansion (per user-configured variable)
  Input: M user configs (e.g., 10 regex patterns)
  Output: M × avg_matches configs (e.g., 10 × 20 = 200 configs)

Step 3: Variable Mapping (per file)
  Input: 200 expanded configs
  Output: 200 StatType objects with repeat=20+
  Cost: deepcopy per file = O(200 × N_files)

Step 4: Parsing (per file × per variable)
  Input: N files × 200 variables × repeat=20
  Cost: N × 200 Perl operations

Step 5: CSV Construction (post-parse)
  Input: N files × 200 variables × repeat=20 × entries
  Cost: O(N × 200 × entries × 20)
```

## Conclusions

**Data volume multiplies through 5 pipeline stages.** A seemingly modest request (10 regex configs on a 32-core simulation with 50 output directories) can explode to:
- 200+ concrete variable configs
- 10,000+ file-variable parse operations
- Millions of reduce operations in CSV construction

**The main bottleneck is parsing (Track 1)**, but data volume explains WHY parsing takes 5.9s for 586 files — it's not just 586 serial file reads, it's 586 files × N variables × Perl processing.

## Recommendations

1. Implement early-stop file discovery (stop after limit files found, don't traverse full tree)
2. Pre-compute expansion count and warn users about large configurations
3. Cap repeat count or bucket count to prevent explosion
4. Consider lazy variable expansion (expand on demand, not upfront)
