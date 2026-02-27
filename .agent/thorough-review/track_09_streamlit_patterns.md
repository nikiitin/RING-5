# Track 09: Streamlit Best Practices

> **Priority**: MEDIUM
> **Status**: PENDING
> **Estimated items**: 7
> **Scope**: `src/web/` — caching, session state, widget patterns, reruns

---

## What to Look At

### 9.1 Widget value pre-initialization anti-pattern

**File**: `src/web/components/common/filtered_selector.py`, line 160
**What**: Setting `st.session_state[key] = widget_default` BEFORE rendering the widget. This is a known Streamlit anti-pattern because:
- On first render: the pre-set value is immediately overwritten by the widget's own default
- On rerun: the pre-set value OVERWRITES the user's selection
**Fix**: Use the widget's `default=` / `value=` parameter instead. Remove all pre-initialization.

### 9.2 Add `st.status()` to plot generation

**File**: `src/web/controllers/plot/render_controller.py`, line ~192
**What**: Plot generation shows no progress feedback. Long-running plot generation (complex grouped stacked bars with many traces) leaves the user waiting with no indication.
**Fix**: Wrap figure generation in `with st.status("Generating plot..."):` with step progress.

### 9.3 ZERO `@st.cache_data` / `@st.cache_resource` decorators — HIGH

**Scope**: Entire `src/web/` directory
**What**: Deep audit found ZERO instances of `@st.cache_data` or `@st.cache_resource` anywhere in the codebase. This means:
- CSV files are re-parsed on every Streamlit rerun
- Trace generation is recomputed on every rerun
- Figure spec building is recomputed on every rerun
**Opportunities**:
- CSV file loading → `@st.cache_data(ttl=3600)`
- Trace generation for unchanged data+config → `@st.cache_data`
- Figure spec building → `@st.cache_data`
- WorkPool singletons → `@st.cache_resource`
**Note**: This was identified as overlapping in the original DEEP_DIVE_PLAN.md (Phase 3.4 + Phase 7.3). Now consolidated here as single item.

### 9.4 Standardize empty state messaging

**Scope**: All components that show "no data" or "no items" messages
**What**: Inconsistent empty state messages across components. Some say "No data available", others say "No items found", others show nothing.
**Convention**: `"No [items] available. [Action to resolve]."`

### 9.5 Evaluate `st.write_stream()` for scanner output

**File**: `src/web/components/data_source/data_source_components.py`
**What**: Manual loop with `as_completed()` for file scanning progress. `st.write_stream()` (Streamlit 1.32+) may provide cleaner streaming output.

### 9.6 Audit all `st.rerun()` calls — narrow scope

**Files**: All files in `src/web/` that call `st.rerun()`
**What**: `scope="app"` triggers full app rerun and may reset unrelated state. Use `scope="fragment"` where the code is inside a `@st.fragment`.
**Key file**: `src/web/pages/portfolio.py`, line 80

### 9.7 Evaluate Streamlit multipage app API

**File**: `src/web/app.py`, lines 75-87
**What**: Manual SPA navigation implementation. Streamlit's built-in `st.navigation` / `st.page` API may simplify this and provide better URL routing.
**Caveat**: Migration is significant. Evaluate cost vs benefit.

---

## How to Investigate

1. **For 9.1**: Read filtered_selector.py around line 160. Search for all `st.session_state[` assignments that occur BEFORE widget renders. Count instances.
2. **For 9.2**: Read render_controller.py. Find the plot generation code path. Measure time for complex plots.
3. **For 9.3**: Confirm zero cache decorators: `grep -rn "@st.cache" src/`. Identify top 5 most expensive functions that would benefit from caching. Design caching strategy with hash functions for custom objects.
4. **For 9.4**: Search for all `st.info(`, `st.warning(`, `st.write("No ` patterns. List all empty state messages. Standardize.
5. **For 9.5**: Read the scanner UI code. Compare current `as_completed()` approach with `st.write_stream()` API.
6. **For 9.6**: `grep -rn "st.rerun" src/web/`. For each call, check if it's inside a `@st.fragment`.
7. **For 9.7**: Read app.py navigation code. Evaluate `st.navigation` API compatibility.

---

## What We Expect to Find

- **9.1**: 3-5 instances of pre-initialization. All fixable with `default=`/`value=` parameters.
- **9.3**: CSV loading and trace generation are the biggest wins. @st.cache_data with TTL will dramatically reduce reruns. Need custom `__hash__` methods for domain objects used as cache keys.
- **9.6**: Most `st.rerun()` calls can be narrowed to `scope="fragment"`.
- **9.7**: Migration to `st.navigation` is likely too disruptive for this phase. Flag for future.

---

## Outcome

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 9.1 Widget pre-init | **NOT A BUG** — Pre-initialization at line 160 is intentional Streamlit workaround. Without it, multiselect raises "value not in options" when filtering changes visible items. Intersection computed at line 159 ensures only valid options kept. Well-documented. | N/A | Keep as-is. Documented workaround for Streamlit limitation. |
| 9.2 st.status() progress | **NOT A BUG** — Plot generation uses manual cache; renders are fast. Scanner already uses `st.status()` exemplarily (data_source_components.py:200-221 with `as_completed` progress). Plot side doesn't need it yet. | LOW | Add only if complex plots become slow. Scanner pattern is a good template. |
| 9.3 @st.cache decorators | **NOT A BUG** — `@st.cache_resource` IS used for ApplicationAPI singleton (app.py:54-56). Figure generation uses a custom cache (manual hash-based). User-triggered operations (scan, parse, transform) intentionally uncached. Zero `@st.cache_data` usage is design choice, not oversight. | LOW | Consider migrating manual figure cache to `@st.cache_data` if maintenance burden grows. |
| 9.4 Empty state messages | **GOOD PRACTICE** — 36+ messages consistent across app. Three severity levels used appropriately: error (data missing), warning (feature unavailable), caption (no matches). Actionable guidance consistent. | N/A | No action needed. Messages are consistent. |
| 9.5 st.write_stream() | **NOT APPLICABLE** — `st.write_stream()` is for LLM/text streaming, not progress tracking. Scanner uses `st.write()` + `st.status()` which is the correct pattern for discrete progress updates with futures. | N/A | No action needed. Current pattern optimal. |
| 9.6 st.rerun() scope | **SCOPE MISMATCHES CONFIRMED** — 47 total calls: 46 default scope, 1 scope="app". 3-4 calls should use scope="app" but don't: app.py:87 (navigation), app.py:100 (clear data), app.py:109 (reset all), portfolio.py:53 (save). These affect global state but use fragment-scoped rerun. | MEDIUM | Change navigation and global-state rerun calls to `st.rerun(scope="app")`. |
| 9.7 Multipage API | **INTENTIONAL DESIGN** — Manual SPA via session_state with custom button styling (primary/tertiary). Lazy page imports for performance. st.navigation (1.26+) would lose custom styling and lazy loading. | LOW | Optional modernization. Current approach provides more control. |

### Corrections from Initial Hypotheses
- **9.1 was NOT an anti-pattern** — it's a documented Streamlit workaround
- **9.3 was NOT missing caching** — ApplicationAPI uses `@st.cache_resource`, figure generation has custom cache
- **9.5 was NOT applicable** — st.write_stream for LLM streaming, not progress tracking

### Critical Findings Summary (items requiring fix)
1. **st.rerun() scope mismatches** — MEDIUM: 3-4 navigation/global rerun calls missing `scope="app"`
