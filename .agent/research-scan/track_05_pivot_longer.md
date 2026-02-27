# Track 5: Shaper Pipeline — PivotLonger Performance

**Status**: DONE
**Priority**: P5
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_05_pivot_longer.md`

---

## Goal

Determine if pivot/shaper operations are the bottleneck.

## Files Analyzed

- `src/core/services/shapers/impl/pivot.py`
- `src/core/services/shapers/pipeline_service.py`
- `src/core/models/shaper_models.py`

---

## Findings

### 1. CRITICAL — Multiple DataFrame `.copy()` Calls Compound Through Pipeline

**Location**: `pivot.py:82, 202`, `pipeline_service.py:149`, plus other shapers (mean.py:214, sort.py:135, split_apply.py:209,252, normalize.py:220, transformer.py:137)

Each shaper performs a full `data_frame.copy()`. In a pipeline with 5 shapers:
- 1 initial copy (pipeline_service.py:149)
- 1 copy per shaper `__call__()`
- Total: 6 full DataFrame copies

For a 100K-row DataFrame at ~25MB per copy: **~150MB** allocated just for copies.

**Severity**: CRITICAL for large DataFrames, compounding with pipeline length

### 2. HIGH — `DataFrame.apply(process_row)` is Not Vectorizable

**Location**: `pivot.py:150, 167-169`

After `pd.melt()`, the DataFrame expands from K rows x N value_vars to K*N melted rows. `apply()` is called on every cell:

```python
result[var_name] = result[var_name].apply(process_row)       # Line 150
result[var_name] = result[var_name].apply(lambda x: ...)     # Line 167-169
```

Each cell requires: `str()` conversion + `re.search()` + dict lookups. This is pure Python bytecode per element — cannot be vectorized.

**Impact**: For K=1000 rows, N=100 value_vars → 100K `apply()` calls, each with regex.

**Severity**: HIGH (Python loop per element)

### 3. MEDIUM-HIGH — `re.search()` Per Cell (2-3 Regex Per Row with Filters)

**Location**: `pivot.py:36, 123, 168`

- Without filters: 1 regex per cell
- With filters (merge/discard strategy): 2-3 regex operations per cell
- Pattern is compiled once (line 117) but still executed per cell
- No caching of regex match results

**Severity**: MEDIUM-HIGH

### 4. MEDIUM — `groupby().agg()` on Merge Strategy

**Location**: `pivot.py:162-164`

```python
result = result.groupby(id_vars + [var_name], as_index=False).agg({val_name: "sum"})
```

Only triggered with `selection_strategy == "merge"`. Cost: O(k log k) additional pass over data. Compounds with `apply()` overhead.

**Severity**: MEDIUM

### 5. HIGH — PivotWider Missing `aggfunc` Protection

**Location**: `pivot.py:218-226`

```python
result = result.pivot(index=index_cols, columns=columns_col, values=values_col)
```

- No `aggfunc` parameter → crashes on duplicate (index, columns) combinations
- No protection against creating excessively wide DataFrames (1000+ columns)
- `reset_index()` on super-wide DataFrames is slow

**Severity**: HIGH (crash risk + width explosion)

### 6. CRITICAL — Pipeline Chaining Compounds All Issues

**Location**: `pipeline_service.py:141-169`

```python
current_data = data.copy()                          # Copy #1
for i, shaper_config in enumerate(pipeline_config):
    shaper = ShaperFactory.create_shaper(...)
    current_data = shaper(current_data)             # Copy #2, #3, ...
```

No lazy evaluation, no operation fusion, no cost-based reordering. Each shaper operates on the full output of the previous, potentially amplifying size.

**Severity**: CRITICAL at scale

---

## Timing Context

Track 1 measured PivotLonger at **~0.002s for 586 rows**. This is fast because:
- 586 rows is small
- Current value_vars count is low
- No wide distributions triggering regex explosion

However, with 10K+ rows or 100+ value_vars, the `apply()` + regex bottleneck will dominate.

## Conclusions

**Not the current bottleneck** (0.002s per Track 1), but contains serious latent performance issues:
- DataFrame copying compounds through pipelines
- `apply()` with regex is O(rows x vars) Python loops
- PivotWider has crash risk on duplicate keys
- No safeguards on data explosion

**Current status**: Fast for small data, architecturally fragile for scale.

## Recommendations

1. Replace `.apply(process_row)` with vectorized `.str.extract()` / `.str.replace()`
2. Reduce copies: use `inplace=True` or copy-on-write semantics
3. Add cardinality checks before `pivot()` to prevent width explosion
4. Add `aggfunc` parameter to PivotWider for duplicate key handling
5. Consider operation fusion for common pipeline patterns (melt + filter without intermediate copy)
