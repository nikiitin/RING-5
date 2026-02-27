# Track 04: Web/UI Layer Correctness

> **Priority**: HIGH
> **Status**: PENDING
> **Estimated items**: 9
> **Scope**: `src/web/` — components, controllers, pages, rendering

---

## What to Look At

### 4.1 Direct session_state assignments bypassing UIStateManager (13 instances)

**Files**:
- `src/web/components/data_managers/seeds_reducer.py`, lines 110-112
- `src/web/components/data_managers/mixer.py`, lines 50-65
- `src/web/components/data_managers/preprocessor.py`, lines 54-65
- `src/web/components/data_managers/outlier_remover.py`, lines 59-66

**What**: Direct `st.session_state[key] = value` assignments bypass the UIStateManager abstraction. UIStateManager should be the single point of state access for consistency and future refactoring.
**Dependencies**: State management consistency. If UIStateManager adds validation/hooks, these bypass them.

### 4.2 Missing None checks in mixer.py

**File**: `src/web/components/data_managers/mixer.py`
**What**: Possible `None` values from widget returns not checked before use. Need to trace all widget result usage.
**Dependencies**: Runtime crashes on certain UI interactions.

### 4.3 Missing None checks in data_source_components.py

**File**: `src/web/components/data_source/data_source_components.py`
**What**: Functions that return `dict | None` — callers may not check for `None`.
**Dependencies**: Runtime crashes when no data source configured.

### 4.4 Widget pre-initialization anti-pattern

**File**: `src/web/components/common/filtered_selector.py`, line 160
**What**: Setting `st.session_state[key] = widget_default` BEFORE rendering the widget. Streamlit's widget lifecycle means this can override user selections on rerun.
**Dependencies**: Widget state persistence — user selections may be lost on rerun.

### 4.5 Widget key collision risk in filtered_selector.py

**File**: `src/web/components/common/filtered_selector.py`
**What**: Widget keys may collide if the same component is rendered multiple times with similar parameters. Need to verify key uniqueness logic.
**Dependencies**: Streamlit widget state corruption if keys collide.

### 4.6 Widget key collision risk in variable_editor.py

**File**: `src/web/components/data_source/variable_editor.py`
**What**: Similar key collision risk as filtered_selector.py. Need to verify key scoping.
**Dependencies**: Same as 4.5.

### 4.7 Inconsistent function signatures: chart_display vs chart_presenter

**Files**:
- `src/web/components/common/chart_display.py`
- `src/web/presenters/plot/chart_presenter.py`

**What**: Nearly identical implementations with slightly different function signatures. One is likely the canonical version; the other should be deleted (see Track 07 for duplication).
**Dependencies**: Cross-track with Track 07, item 7.1.

### 4.8 Pyright "possibly unbound" errors in pivot_config.py

**File**: `src/web/components/shapers/pivot_config.py`, lines 256-258
**What**: 3 pyright errors flagged by trunk check:
- line 256:34 — `selection_filters` is possibly unbound
- line 257:35 — `strategy` is possibly unbound
- line 258:28 — `merge_label` is possibly unbound

These indicate control flow paths where variables are used without guaranteed initialization.
**Dependencies**: Runtime `UnboundLocalError` crashes on specific UI paths.

### 4.9 `st.rerun(scope="app")` may reset unrelated state

**File**: `src/web/pages/portfolio.py`, line 80
**What**: `scope="app"` triggers a full application rerun. If `scope="fragment"` is viable, narrowing prevents unintended state resets.
**Dependencies**: User experience — data loss if unrelated state is reset by rerun.

---

## How to Investigate

1. **For 4.1**: Read each file. Map all direct `st.session_state` accesses. Check if UIStateManager has equivalent methods. If not, add them.
2. **For 4.2-4.3**: Read each function's return type. Trace all callers. Check for None guards.
3. **For 4.4**: Read the widget rendering code. Check if pre-initialization is actually needed (some widgets require it for initial state). If not, remove it.
4. **For 4.5-4.6**: Read key construction logic. Check if `plot_id` or other discriminators prevent collision.
5. **For 4.8**: Read lines 250-260 of pivot_config.py. Trace all control flow paths to the usage points. Add default initialization before first branch.
6. **For 4.9**: Read the rerun call context. Check if `scope="fragment"` works (requires the code to be inside a `@st.fragment` decorator).

---

## What We Expect to Find

- **4.1**: UIStateManager already has most needed methods. The direct accesses are leftovers from before UIStateManager existed.
- **4.2-4.3**: Some callers DO miss None checks. Fix: add guards or change return types.
- **4.4**: Pre-initialization IS needed for filtered_selector's specific use case (dropdown needs a default) but should use `default=` parameter instead.
- **4.8**: The 3 pyright errors are real — there's a branch where these variables aren't assigned before use.
- **4.9**: `scope="app"` is likely intentional (portfolio loading needs full refresh), but should be documented.

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 4.1 Direct session_state | PENDING | | |
| 4.2 None checks (mixer) | PENDING | | |
| 4.3 None checks (data_source) | PENDING | | |
| 4.4 Widget pre-init | PENDING | | |
| 4.5 Key collision (filter) | PENDING | | |
| 4.6 Key collision (editor) | PENDING | | |
| 4.7 Chart signatures | PENDING | | |
| 4.8 Pyright unbound vars | PENDING | | |
| 4.9 Rerun scope | PENDING | | |
