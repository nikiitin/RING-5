# Track 8: Scanning Performance (Deep Scan Specific)

**Status**: DONE
**Priority**: P8
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_08_scanning.md`

---

## Goal

Verify scanning itself is fast and identify deep-scan specific issues.

## Files Analyzed

- `src/parsing/gem5/impl/scanning/scanner.py` — `Gem5StatsScanner` singleton
- `src/parsing/gem5/impl/scanning/gem5_scan_work.py` — `Gem5ScanWork` callable
- `src/parsing/gem5/impl/scanning/pattern_aggregator.py` — `PatternAggregator`
- `src/parsing/gem5/impl/pool/pool.py` — `ScanWorkPool`
- `src/parsing/gem5/impl/gem5_scanner.py` — `submit_scan_async()`

---

## Findings

### 1. GREEN — Gem5StatsScanner Singleton is Correct

**Location**: `scanner.py:32-67`

True singleton pattern. `get_instance()` creates one instance per process. Caches Perl executable path (line 42) and script path (line 50). Does NOT cache scan results — each `scan_file()` spawns a new Perl subprocess.

**Severity**: NONE (correct implementation)

### 2. GREEN — PatternAggregator is O(n log n), No Cartesian Product

**Location**: `pattern_aggregator.py:35-100`

Algorithm: extract numeric patterns per variable → group by signature → consolidate. Uses UNION of entries (lines 189-195), not cartesian product. For 1000 variables: ~15-20K operations (milliseconds).

**Severity**: NONE (efficient algorithm)

### 3. YELLOW — `limit=0` Deep Scan Can Be Catastrophic

**Location**: `gem5_scanner.py:52-56`

```python
files_to_sample: list[Path] = files[:limit] if limit > 0 else files
```

| limit | Files Processed | Risk |
|-------|----------------|------|
| 5 (default) | 5 | Low |
| 0 (deep scan) | ALL found | HIGH if 1000+ files |

With `limit=0` on 1000+ files: 1000 / 16 threads × 300ms ≈ 19s scanning alone.

**Severity**: YELLOW (safe at default, dangerous at limit=0)

### 4. GREEN — ScanWorkPool Chunking is Correct

**Location**: `pool.py:56-94`

Chunk size: `max(1, len(works) // 8)`. `_futures.clear()` prevents memory leak (line 74). Uses `ThreadPoolExecutor` (I/O-bound — correct). Thread pool: `num_workers × 2`.

**Severity**: NONE (correctly implemented)

### 5. GREEN — Per-File Scan Cost is Bounded

**Location**: `scanner.py:89-116`

Each scan: `subprocess.run([perl, statsScanner.pl, file_path], timeout=60)`. 60-second timeout. Error handling returns `[]` on failure (gem5_scan_work.py:40-42).

Parallelism benefit: 100 files, 16 threads → ceil(100/16) × 200ms ≈ 1.3s (7-8x speedup).

**Severity**: NONE

---

## Severity Summary

| Component | Status | Severity |
|-----------|--------|----------|
| Singleton pattern | Correct | GREEN |
| PatternAggregator | Efficient O(n log n) | GREEN |
| `limit=0` behavior | Dangerous at scale | YELLOW |
| ScanWorkPool chunking | Correct, leak fixed | GREEN |
| Per-file scan cost | Bounded (60s timeout) | GREEN |

## Conclusions

**Scanning is well-implemented.** Singleton is correct, pattern aggregation is efficient, chunking works, error handling is proper.

**Only risk**: `limit=0` on directories with 1000+ files. The parallel thread pool mitigates this (7-8x speedup).

**Not the main bottleneck** — scanning precedes parsing. The 5.9s from Track 1 is parsing time, not scanning time.

## Recommendations

1. Add documentation warning about `limit=0` on large datasets
2. Implement early-stop `rglob()` to avoid full tree traversal (see Track 7)
3. Consider caching scan results by file path + modification time
