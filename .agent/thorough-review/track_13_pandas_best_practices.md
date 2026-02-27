# Track 13: Pandas Best Practices

> **Priority**: MEDIUM
> **Status**: PENDING
> **Estimated items**: 5
> **Scope**: `src/core/services/shapers/`, `src/parsing/`, data pipeline

---

## What to Look At

### 13.1 Use `.pipe()` for shaper pipeline

**File**: `src/core/services/shapers/pipeline_service.py`
**What**: Current shaper pipeline uses a manual `for` loop:
```python
for shaper in shapers:
    current_data = shaper(current_data)
```
The pandas `.pipe()` method provides a more composable and introspectable pattern:
```python
result = data.pipe(shaper1).pipe(shaper2).pipe(shaper3)
```
**Caveat**: Requires that shaper `apply()` methods accept and return DataFrames in a `.pipe()`-compatible signature: `def apply(self, df: pd.DataFrame) -> pd.DataFrame`.

### 13.2 Use `pd.CategoricalDtype` consistently

**Scope**: `src/core/services/shapers/impl/` — shapers that convert columns to categorical
**What**: Several shapers convert using `.astype("category")` without preserving order. This loses the natural order of categories (e.g., benchmark names should stay in input order, not be sorted alphabetically).
**Fix**: Use `pd.CategoricalDtype(categories=order, ordered=True)` to explicitly preserve the category order.

### 13.3 DataFrame.iterrows() performance in stacked_bar_plot.py

**File**: `src/web/pages/ui/plotting/stacked_bar_plot.py`, line ~162
**What**: `iterrows()` is one of the slowest DataFrame iteration methods. For large datasets with many groups, this becomes a bottleneck. Vectorized operations or `.groupby().apply()` are significantly faster.

### 13.4 Use `pd.StringDtype()` for string columns

**Scope**: `src/web/components/data_source/data_source_components.py` (CSV loading), shapers
**What**: String columns default to `object` dtype, which is a Python object array. `pd.StringDtype()` (pandas 1.0+) provides:
- Better memory efficiency (nullable string array)
- Faster string operations
- Clearer type semantics
**Fix**: Convert string columns at CSV load time: `df[col] = df[col].astype(pd.StringDtype())`

### 13.5 Remove unnecessary `pd.DataFrame()` wrapping (12 instances)

**Files**:
- `src/core/services/shapers/impl/outlier_service.py`, lines 24, 27
- `src/core/services/shapers/impl/reduction_service.py`, line 31
- Various selector implementations

**What**: `pd.DataFrame(df[boolean_mask])` is redundant — boolean indexing already returns a DataFrame. Each unnecessary wrap creates a full copy, wasting memory.
**Note**: Cross-referenced with Track 03, item 3.3. Listed here as the Pandas-specific perspective.

---

## How to Investigate

1. **For 13.1**: Read `pipeline_service.py`. Check if all shapers have compatible signatures. Test `.pipe()` with a sample pipeline.
2. **For 13.2**: `grep -rn "astype.*category" src/`. For each instance, check if order matters. If yes, replace with `CategoricalDtype`.
3. **For 13.3**: Read the iterrows loop. Determine if it can be vectorized. Profile with sample data.
4. **For 13.4**: Identify string columns at load time. Add `pd.StringDtype()` conversion. Profile memory impact.
5. **For 13.5**: Confirm each instance returns DataFrame without wrapping. Remove wrappers.

---

## What We Expect to Find

- **13.1**: `.pipe()` is compatible with 8 of 10 shapers. The 2 exceptions need minor signature adjustments.
- **13.2**: 3-5 instances where category order is lost. Users may have noticed alphabetical reordering.
- **13.3**: `iterrows()` can be replaced with vectorized groupby. ~10x speedup for large datasets.
- **13.4**: String dtype conversion saves 20-30% memory on string-heavy datasets.
- **13.5**: All 12 instances are confirmed redundant.

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 13.1 .pipe() pipeline | PENDING | | |
| 13.2 CategoricalDtype | PENDING | | |
| 13.3 iterrows() perf | PENDING | | |
| 13.4 StringDtype | PENDING | | |
| 13.5 Redundant wrapping | PENDING | | |
