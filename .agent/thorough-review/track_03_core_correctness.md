# Track 03: Core Layer Correctness

> **Priority**: HIGH
> **Status**: PENDING
> **Estimated items**: 8
> **Scope**: `src/core/` — services, models, common utilities

---

## What to Look At

### 3.1 Broad `except Exception` in pivot.py

**File**: `src/core/services/shapers/impl/pivot.py`, line 49
**What**: `extract_with_pattern()` catches `except Exception` and returns a fallback value. Should catch specific: `re.error`, `IndexError`.
**Dependencies**: PivotLonger extraction — incorrect fallback may produce wrong pivot results.

### 3.2 Broad `except Exception` in portfolio_service.py

**File**: `src/core/services/portfolio_service.py`, line 139
**What**: Portfolio save/load catches `except Exception`. Should catch specific: `TypeError`, `KeyError`, `ValueError`, `json.JSONDecodeError`.
**Dependencies**: Portfolio persistence reliability.

### 3.3 Unnecessary `pd.DataFrame()` wrapping (12 instances)

**Files**:
- `src/core/services/shapers/impl/outlier_service.py`, lines 24, 27
- `src/core/services/shapers/impl/reduction_service.py`, line 31
- `src/core/services/shapers/impl/column_selector.py`
- `src/core/services/shapers/impl/item_selector.py`
- `src/core/services/shapers/impl/condition_selector.py`

**What**: `pd.DataFrame(df[boolean_mask])` is redundant — boolean indexing already returns a DataFrame. This creates unnecessary copies.
**Dependencies**: Performance at scale.

### 3.4 Off-by-one in csv_pool_service.py

**File**: `src/core/services/csv_pool_service.py`, line 277
**What**: Row count calculation for empty files may be off by one. Need to trace the exact logic.
**Dependencies**: CSV file status reporting accuracy.

### 3.5 Dictionary mutation in portfolio_migrator.py

**File**: `src/core/services/portfolio_migrator.py`, line 64 (`_migrate_v1_to_v2`)
**What**: Direct mutation of input dictionary during migration. If the same dict is referenced elsewhere, mutations propagate unexpectedly.
**Dependencies**: Portfolio migration correctness when called multiple times.

### 3.6 Performance issue in normalize.py

**File**: `src/core/services/shapers/impl/normalize.py`, line 189
**What**: Uses `.values` instead of `.unique()` — processes all values including duplicates when only unique values are needed.
**Dependencies**: Normalization performance on large datasets with many duplicate values.

### 3.7 Silent type coercion failure in repository_state_manager.py

**File**: `src/core/state/repository_state_manager.py`, lines 74-82
**What**: Type coercion that silently falls back on failure. Need to verify what happens when coercion fails and whether the fallback value is correct.
**Dependencies**: State persistence correctness.

### 3.8 Dictionary access safety in config_validation_service.py

**File**: `src/core/services/config_validation_service.py`, lines 198-223
**What**: Direct dict access `plot_config["data"]["hue"]` without validation. `KeyError` if `"data"` key missing.
**Dependencies**: Plot config validation — errors here surface as cryptic crashes in the plot pipeline.

---

## How to Investigate

1. **For 3.1-3.2**: Read the exception handlers. List all possible exception types from the guarded code. Narrow to specific exceptions.
2. **For 3.3**: Read each file. Confirm that the inner expression always returns a DataFrame. Remove wrapping and verify type annotations still hold.
3. **For 3.4**: Read the CSV row count logic. Test with empty file, single-row file, and multi-row file.
4. **For 3.5**: Read `_migrate_v1_to_v2`. Check if input dict is used after migration call. Add `.copy()` if needed.
5. **For 3.6**: Read the normalize logic. Profile `.values` vs `.unique()` on sample data.
6. **For 3.7**: Read the type coercion code. Check what the fallback value is and whether it's semantically correct.
7. **For 3.8**: Read the config validation logic. Trace all nested dict accesses. Add `.get()` with appropriate defaults.

---

## What We Expect to Find

- **3.1-3.2**: Exception types can be narrowed without losing coverage. Will need to verify all code paths within each try block.
- **3.3**: All 12 instances are confirmed redundant. Removing them saves memory and CPU.
- **3.4**: Likely an off-by-one when file has header but no data rows.
- **3.5**: Input dict IS mutated and may be referenced elsewhere. Fix: `.copy()` before mutation.
- **3.6**: `.unique()` could be significantly faster for columns with high duplication ratios.
- **3.8**: Multiple nested accesses are unguarded. Fix: defensive `.get()` chain.

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 3.1 Broad except (pivot) | PENDING | | |
| 3.2 Broad except (portfolio) | PENDING | | |
| 3.3 Unnecessary DataFrame wraps | PENDING | | |
| 3.4 Off-by-one CSV | PENDING | | |
| 3.5 Dict mutation | PENDING | | |
| 3.6 Normalize performance | PENDING | | |
| 3.7 Silent type coercion | PENDING | | |
| 3.8 Config validation safety | PENDING | | |
