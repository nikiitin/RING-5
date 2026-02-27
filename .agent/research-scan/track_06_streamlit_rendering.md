# Track 6: Streamlit Rendering & Cache Behavior

**Status**: DONE
**Priority**: P6
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_06_streamlit_rendering.md`

---

## Goal

Determine if Streamlit re-renders or cache misses cause perceived slowness.

## Files Analyzed

- `src/web/components/data_source/data_source_components.py`
- `src/web/components/shapers/pivot_config.py`
- `src/web/pages/data_managers.py`
- `src/core/application_api.py`
- `app.py`

---

## Findings

### 1. CRITICAL — Sequential Blocking `f.result()` in Quick Scan

**Location**: `data_source_components.py:204`

```python
scan_results = [f.result() for f in scan_futures]
```

Futures are awaited **sequentially** instead of using `as_completed()`. This blocks the UI thread for each file until completion, preventing progress bar updates. Users see a frozen UI.

**Contrast**: The `_show_parse_dialog()` (line 463) correctly uses `as_completed(futures)` for streaming updates.

**Severity**: CRITICAL (frozen UI during scanning)

### 2. MEDIUM — Pattern Re-Computation in PivotLongerConfig.render()

**Location**: `pivot_config.py:133-143, 176-186`

On every re-render:
- Regex is recompiled: `compiled = re.compile(extract_pattern)` (line 133)
- Pattern labels re-extracted from all value_vars (line 141-143)
- Group values iterated per variable: `for v in value_vars: compiled.search(str(v))` (lines 176-186)
- Selection filter multiselect widgets re-computed for each group (lines 188-207)

With 50+ value_vars and multiple regex groups, this causes noticeable lag on any widget interaction.

**Severity**: MEDIUM

### 3. MEDIUM — Parse Dialog is Synchronous/Blocking (But Acceptable)

**Location**: `data_source_components.py:441-534`

```python
for future in as_completed(futures):
    res = future.result()              # Blocks until one completes
    completed_count += 1
    progress_bar.progress(pct, ...)
```

Uses `as_completed()` for incremental updates (good). However, the dialog remains modal and unresponsive during parsing — no cancel button works. The code acknowledges this with comments at lines 455-459.

**Severity**: MEDIUM (acceptable UX but could be improved)

### 4. MEDIUM — Fragment Re-executes All Internal Logic

**Location**: `data_source_components.py:126-268`

The `@st.fragment` decorator correctly isolates widget interactions from full-page reruns. However, the fragment itself re-runs all internal logic on ANY widget change:
- Variable editor renders (line 240)
- Preview JSON (line 267)
- All widget state recalculation

This is by design (fragments re-run), but expensive reads inside fragments aren't cached.

**Severity**: MEDIUM

### 5. POSITIVE — Session State is Not Bloated

Large DataFrames are stored in `RepositoryStateManager._session_repo.data_repo` (in-memory Python objects), not in `st.session_state`. Session state only holds configuration keys (strings, booleans, small dicts). Architecture is sound.

**Severity**: NONE (good design)

### 6. POSITIVE — Fragment Isolation is Well-Designed

Fragments at `data_source_components.py:126` and `data_managers.py:65-110` correctly scope UI sections. Parse button (line 275) is outside the fragment, triggering full page rerun on success.

**Severity**: NONE (good design)

### 7. LOW — No `@st.cache_data` Decorators Used

No caching decorators found on any compute functions. `submit_parse_async()` and `submit_scan_async()` return `Future` objects which can't be cached. The `@st.cache_resource` on `get_api()` in `app.py:51` is appropriate.

**Severity**: LOW (Future objects can't be cached anyway)

---

## Severity Summary

| Issue | Severity | Impact |
|-------|----------|--------|
| Sequential `f.result()` in scan | CRITICAL | Frozen UI, no progress feedback |
| Pattern re-compilation in pivot config | MEDIUM | Lag on regex-heavy configs |
| Blocking parse dialog loop | MEDIUM | Unresponsive dialog during parse |
| Fragment re-execution overhead | MEDIUM | Variable editor recalc on keystrokes |
| Session state bloat | NONE | Architecture is sound |
| Fragment isolation | NONE | Well-designed |

## Conclusions

**One CRITICAL issue**: Sequential future resolution in scanning blocks the UI. This is likely a major contributor to perceived "freezing" during scans.

**Three MEDIUM issues**: Pattern re-computation, blocking dialog, and fragment overhead cause lag but don't explain the main performance issue.

**Session state and fragment architecture are well-designed** — not contributing to the problem.

## Recommendations

1. Replace sequential `f.result()` with `as_completed()` in scan function (line 204) — add progress bar
2. Memoize regex compilation in `PivotLongerConfig.render()` using widget key or session state
3. Pre-compute group values once per configuration change instead of per-render
