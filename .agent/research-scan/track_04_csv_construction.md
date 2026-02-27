# Track 4: CSV Construction Bottleneck

**Status**: DONE
**Priority**: P2
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_04_csv_construction.md`

---

## Goal

Verify `construct_final_csv()` isn't the slow path and analyze its algorithmic complexity.

## Files Analyzed

- `src/parsing/gem5/impl/gem5_parser.py` — lines 241-317 (`construct_final_csv()`)
- `src/parsing/gem5/types/vector.py` — `balance_content()`, `reduce_duplicates()`
- `src/parsing/gem5/types/histogram.py` — `balance_content()`, `reduce_duplicates()`, `_reduce_with_rebinning()`
- `src/parsing/gem5/types/distribution.py` — `balance_content()`, `reduce_duplicates()`
- `src/parsing/gem5/types/scalar.py` — `reduce_duplicates()`

---

## Findings

### 1. Overall Complexity — O(F x V x D x R)

**Location**: `gem5_parser.py:285-311`

The outer loop iterates `files x variables`:

```python
for file_stats in results:              # F files
    for var_name in ordered_names:      # V variables
        var.balance_content()           # O(entries x repeat)
        var.reduce_duplicates()         # O(entries x repeat)
```

**Overall**: `O(F x V x max(E, D, B) x R)` where:
- F = files, V = variables
- E = vector entries, D = distribution range, B = histogram buckets
- R = repeat count (dump factors)

**Severity**: CRITICAL at scale — with large distributions this can reach billions of operations.

### 2. CRITICAL — Distribution `reduce_duplicates()` with Unbounded Range

**Location**: `distribution.py:225-238`

Distribution `balance_content()` iterates over `(max - min + 1)` buckets. If a distribution has range 0-100,000, that's 100K buckets. With repeat=4:
- Per-variable cost: 100,000 x 4 = 400K operations
- For 50 files x 20 distribution vars: 400M operations

**Severity**: CRITICAL (can explode with wide distributions)

### 3. HIGH — Histogram Rebinning is O(B^2 x R)

**Location**: `histogram.py:204-306`

When `_bins > 0 and _max_range > 0`, `reduce_duplicates()` calls `_reduce_with_rebinning()` which has quadratic complexity in bucket count due to proportion-based redistribution.

**Severity**: HIGH (quadratic for rebinned histograms)

### 4. MEDIUM — `hasattr()` Called Per Cell

**Location**: `gem5_parser.py:295`

```python
if hasattr(var, "balance_content"):
```

Called once per (file x variable) pair. While O(1) per call, `StatType.__getattribute__` has guard logic for `reduced_content` that adds overhead. Total: O(F x V) lookups.

**Severity**: MEDIUM (thousands of calls, each with attribute guard)

### 5. LOW — NaN String Allocation

**Location**: `gem5_parser.py:288-290`

Each missing variable appends `"NaN"` string. For sparse data (many missing vars across many files), generates O(F x M) string objects. Negligible memory impact but indicates incomplete data.

**Severity**: LOW

### 6. INFO — CSV I/O is Unbuffered

**Location**: `gem5_parser.py:280-313`

Each `writer.writerow()` is a separate I/O call. For 500+ files this means 500+ syscalls. Buffered batch writing would be faster but this is not the bottleneck per Track 1 timing (~0.005s).

---

## Worst-Case Scaling Example

```
50 files x 100 variables x 100,000 buckets x 4 repeats
= 200,000,000,000 operations (200 BILLION)
```

This is a time bomb for distributions with large ranges.

## Conclusions

**Track 1 showed ~0.005s for CSV construction with 586 files.** This means the current dataset's variables are NOT distributions with large ranges. However, the algorithmic complexity is a latent risk — if users configure distribution variables with wide ranges (e.g., latency distributions from 0 to 100K), this phase will become the dominant bottleneck.

**Current status**: Not the bottleneck for the profiled workload, but architecturally risky.

## Recommendations

1. Pre-compute distribution range and reject/warn for oversized ranges
2. Cache `balance_content()`/`reduce_duplicates()` results per variable
3. Consider batch CSV writing (buffer rows before I/O)
4. Replace `hasattr()` with isinstance check or protocol
