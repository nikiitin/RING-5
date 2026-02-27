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

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 3.1 Broad except (pivot) | **PARTIALLY CONFIRMED** — `except Exception` at line 49 catches `re.error` and `TypeError`. Broad but functional. Nested try-except for IndexError already specific. Missing error logging. | MEDIUM | Narrow to `except (re.error, TypeError) as e:` + `logger.warning`. |
| 3.2 Broad except (portfolio) | **NOT A BUG** — `except Exception` at line 139 is intentionally broad for injected presentation-layer callback. Silent failure is acceptable (saves without figure spec). Logged at debug level. | N/A | No action needed. Add clarifying comment at most. |
| 3.3 Unnecessary DataFrame wraps | **CONFIRMED** — 12+ instances across 5 files: outlier_service.py (2), reduction_service.py (2), column_selector.py (1), item_selector.py (2), condition_selector.py (6+). All boolean-index or column-select already return DataFrame. | MEDIUM | Remove all `pd.DataFrame()` wrappers. Direct return of subset. |
| 3.4 Off-by-one CSV | **PARTIALLY CONFIRMED** — `sum(1 for _ in f) - 1` returns -1 for empty files (0 lines). Normal CSVs always have headers so impact is edge-case only. | LOW | Add `max(0, total_lines - 1)` guard. |
| 3.5 Dict mutation | **CONFIRMED** — `_migrate_v1_to_v2` mutates input dict via `config.setdefault()` and `del config[k]`. Input comes from `json.load()` so fresh dict, but pattern is fragile. | MEDIUM | Add `data = data.copy()` at top or document mutation intent. |
| 3.6 Normalize performance | **CONFIRMED** — `.values` at line 189 returns all values including duplicates for membership check. `.unique()` would be more efficient for large datasets. | LOW | Replace `.values` with `.unique()`. Micro-optimization. |
| 3.7 Silent type coercion | **CONFIRMED** — Exception caught at line 83, logged, but `set_data()` called with potentially partial-typed data. If coercion fails mid-loop, some columns typed and some not. | MEDIUM | Consider re-raising or ensuring full coercion before proceeding. |
| 3.8 Config validation safety | **NOT A BUG** — Nested dicts `plot_config["data"]` and `plot_config["style"]` are always initialized in the dict literal. Optional fields use `if key in kwargs` guard. | N/A | No action needed. |

### NEW Issues Discovered During Investigation

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 3.9 Data copy inconsistency in repository_state_manager.py | **CONFIRMED HIGH** — DataFrame at line 68 is only `.copy()`-ed if type casting is needed (cols_to_cast non-empty). When no casting needed, stored as reference. External mutations propagate to stored data. | HIGH | Always copy DataFrame before storing: `data = data.copy()` before try block. |
| 3.10 numpy reference in normalize.py line 318 | **CONFIRMED** — `result[col] = data_frame[col].values` uses numpy array reference instead of copy. Could share memory with original DataFrame. | LOW | Use `data_frame[col].copy()` instead of `.values`. |

### Corrections from Initial Hypotheses
- **3.2 was NOT a bug** — broad except justified for injected callback
- **3.8 was NOT a bug** — nested dicts always initialized before access
- **3.4 was PARTIALLY confirmed** — only affects truly empty files (no header), very unlikely in practice

### Critical Findings Summary (items requiring fix)
1. **repository_state_manager.py line 68: DataFrame stored by reference** — Data integrity risk when no type casting needed
2. **outlier_service.py, reduction_service.py, column/item/condition_selector.py: redundant pd.DataFrame() wrapping** — 12+ unnecessary copies
3. **portfolio_migrator.py line 64: input dict mutation** — Fragile mutation pattern
