# Seeds Reducer → Generic Reducer Refactoring Plan

> **Purpose**: Step-by-step plan to transform the `random_seed`-locked
> Seeds Reducer into a generic Column Reducer.

---

## 1. Current State

### The Problem

The Seeds Reducer UI (`seeds_reducer.py` L43-52) has a **hard gate**:

```python
if "random_seed" not in data.columns:
    st.warning("⚠️ No `random_seed` column found...")
    st.info("If your seed column has a different name...")
    return  # ← BLOCKS entire feature
```

Users whose data uses column names like `seed`, `run_id`, `iteration`,
or any other categorical dimension **cannot use this feature at all**.

### What's Already Generic

The backend `ReductionService` (62 lines) is **fully generic**:

- `reduce_seeds(df, categorical_cols, statistic_cols)` — no `random_seed` knowledge
- `validate_seeds_reducer_inputs(df, categorical_cols, statistic_cols)` — validates any columns
- The `.sd` suffix convention is the only seeds-specific thing (but applies generically)

---

## 2. Files to Modify

### File 1: `src/web/pages/ui/data_managers/impl/seeds_reducer.py` (PRIMARY)

**Scope**: UI layer only — the only file with `random_seed` hard-coding

#### Change 1: Replace Hard Gate with Column Selector (L43-63)

**Before**:

```python
if "random_seed" not in data.columns:
    st.warning("No `random_seed` column...")
    return

categorical_cols = [c for c in data.columns if data[c].dtype == "object"]
numeric_cols = [c for c in data.columns if pd.api.types.is_numeric_dtype(data[c])]
categorical_cols = [c for c in categorical_cols if c != "random_seed"]
numeric_cols = [c for c in numeric_cols if c != "random_seed"]
```

**After**:

```python
# Identify candidate reduction columns (any column with ≤20 unique values)
all_columns = list(data.columns)
candidate_cols = [c for c in all_columns
                  if data[c].nunique() <= 20 or data[c].dtype == "object"]

if not candidate_cols:
    st.warning("No suitable columns found for reduction.")
    st.info("Reduction works best with categorical columns...")
    return

# Let user pick which column to reduce over
reduce_col = st.selectbox(
    "Column to reduce over",
    options=candidate_cols,
    help="Select the column whose values will be aggregated (e.g., random_seed, iteration, run_id)",
    key="reducer_target_column",
)

# Split remaining columns into categorical and numeric,
# excluding the reduction column
categorical_cols = [c for c in data.columns
                    if data[c].dtype == "object" and c != reduce_col]
numeric_cols = [c for c in data.columns
                if pd.api.types.is_numeric_dtype(data[c]) and c != reduce_col]
```

#### Change 2: Update Info/Help Text (L26-36)

**Before**: Text references "random_seed" specifically
**After**: Generic description about reducing over any categorical column

#### Change 3: Update Naming (L15, etc.)

- Class name: `SeedsReducerManager` → `ReducerManager` (or keep for backward compat)
- `name` property: `"Seeds Reducer"` → `"Reducer"` (or `"Column Reducer"`)
- Preview key: `"seeds_reduction"` → `"column_reduction"` (internal)
- Button text: `"Apply Seeds Reducer"` → `"Apply Reducer"`
- Button text: `"Confirm and Apply Seeds Reducer"` → `"Confirm and Apply Reducer"`

### File 2: `src/web/pages/data_managers.py` (MINOR)

- L18: `from ... import SeedsReducerManager` → `from ... import ReducerManager`
- L39: Tab label `"Seeds Reducer"` → `"Reducer"` (or `"Column Reducer"`)
- L83: `SeedsReducerManager(api).render()` → `ReducerManager(api).render()`

### File 3: `src/web/pages/ui/data_managers/impl/outlier_remover.py` (MINOR)

- L81-86: Smart default excludes `random_seed` from group-by — generalize
- L104: Warning text references `random_seed` — make it generic

### File 4: `tests/visual/pages/data_managers_page.py` (POM UPDATE)

Update locators and methods:

- `seeds_no_random_seed_warning` → replace with `reducer_no_columns_warning`
- `seeds_apply_button` → `reducer_apply_button`
- `seeds_confirm_button` → `reducer_confirm_button`
- `seeds_categorical_multiselect` → `reducer_groupby_multiselect`
- `seeds_numeric_multiselect` → `reducer_stats_multiselect`
- Add new: `reducer_target_column_selectbox` — for the column selector
- `assert_seeds_requires_random_seed()` → `assert_reducer_shows_no_columns_warning()`

### File 5: `tests/visual/test_e2e_parse_workflow.py` (TEST UPDATE)

- `TestSeedsReducerNoSeedColumn` → adapt to new generic warning
- Update assertion to check for generic "No suitable columns" message

### File 6: `src/core/models/config/config_manager.py` (OPTIONAL)

- `enable_seeds_reducer()` → optionally accept column parameter
- Low priority — config toggle works regardless of column name

---

## 3. Files That Need NO Changes

| File                                              | Reason                      |
| ------------------------------------------------- | --------------------------- |
| `src/core/services/managers/reduction_service.py` | Already fully generic       |
| `src/core/services/managers/managers_api.py`      | Generic protocol            |
| `src/core/services/managers/managers_impl.py`     | Pass-through                |
| `src/core/application_api.py`                     | Facade — no reduction logic |
| `src/core/models/history_models.py`               | Generic operation records   |
| `src/web/pages/ui/data_managers/data_manager.py`  | Base class — unchanged      |

---

## 4. Test Impact

### Existing Tests to Update

| Test File                                 | Test Name                      | Change                        |
| ----------------------------------------- | ------------------------------ | ----------------------------- |
| `tests/visual/test_e2e_parse_workflow.py` | `TestSeedsReducerNoSeedColumn` | Update warning text assertion |
| `tests/unit/test_data_managers_ui/`       | Any seeds reducer unit tests   | Update widget keys/labels     |
| `tests/ui/`                               | AppTest seeds reducer tests    | Update widget matching        |

### New Tests to Write

| Test                                      | Description                                  |
| ----------------------------------------- | -------------------------------------------- |
| `test_reducer_shows_column_selector`      | Verify the new column selectbox appears      |
| `test_reducer_with_custom_column`         | Reduce by non-random_seed column             |
| `test_reducer_no_candidate_columns`       | All-numeric data shows warning               |
| `test_reducer_preserves_column_exclusion` | Selected column excluded from group-by/stats |

---

## 5. Implementation Order

1. **Update UI** (`seeds_reducer.py`) — Replace hard gate with selectbox
2. **Update page registration** (`data_managers.py`) — Tab label + import
3. **Update POM** (`data_managers_page.py`) — New locators
4. **Update E2E tests** (`test_e2e_parse_workflow.py`) — New assertions
5. **Update unit tests** — Widget key changes
6. **Update outlier remover** — Generalize `random_seed` defaults
7. **Run quality gate** — All checks must pass

---

## 6. Backward Compatibility

### Auto-Detection Heuristic

For users who DO have `random_seed`, pre-select it in the dropdown:

```python
# Default to random_seed if present, else first candidate
default_idx = 0
if "random_seed" in candidate_cols:
    default_idx = candidate_cols.index("random_seed")

reduce_col = st.selectbox(
    "Column to reduce over",
    options=candidate_cols,
    index=default_idx,
    ...
)
```

This preserves the original workflow while enabling generic use.

---

## 7. Risk Assessment

| Risk                               | Likelihood | Mitigation                             |
| ---------------------------------- | ---------- | -------------------------------------- |
| Naming confusion (Seeds → Reducer) | Medium     | Keep familiar name in tab, add tooltip |
| Users lose auto-detection          | Low        | Pre-select `random_seed` when present  |
| UI tests break                     | Certain    | Update POM + test assertions together  |
| Backend breaks                     | None       | Backend is already generic             |
| Performance impact                 | None       | No new computation                     |
