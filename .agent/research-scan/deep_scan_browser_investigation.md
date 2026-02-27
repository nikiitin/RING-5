# Deep Scan Browser-Side Performance Investigation

**Status**: DONE
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/deep_scan_browser_investigation.md`

---

## Problem Statement

When performing a **deep scan** (limit=-1), the application becomes drastically slow and memory consumption increases — **on the client/browser side**, not the server. Quick scan (limit=10) works fine.

---

## Root Cause: Three-Part Problem

### Part 1: Entries Lists Grow Unbounded with Deep Scan

**Location**: `gem5_scanner.py:108`, `pattern_aggregator.py:190-195`

Scan results are merged using **SET UNION** of entries across all files:

```python
new_entries = sorted(list(set(existing.entries) | set(var.entries)))
```

And in pattern aggregation:
```python
all_entries: set[str] = set()
for _, var in instances:
    all_entries.update(var.entries)  # UNION — grows with each file
```

| Scan Type | Files | Entries per Vector |
|-----------|-------|--------------------|
| Quick (limit=10) | 10 | ~50 |
| Deep (limit=-1) | 100+ | **500+** |

### Part 2: Full Entries Lists Serialized to Browser

**Location**: `data_source_components.py:209-210`, `variable_editor.py:486`

```python
scanned_vars_dicts = [v.to_dict() for v in scanned_vars_result]
api.state_manager.set_scanned_variables(scanned_vars_dicts)
```

`to_dict()` includes the **full entries list**:
```python
def to_dict(self) -> ScannedVariableDict:
    result = ScannedVariableDict(
        name=self.name, type=self.type,
        entries=self.entries,  # FULL LIST — no truncation
    )
```

This entire data structure is:
1. Stored in the state repository
2. Retrieved on every Streamlit rerun
3. Passed as `available_variables` to the variable editor
4. Serialized via Streamlit's WebSocket protocol to the browser

### Part 3: Browser DOM Explodes with Large Option Lists

**Critical Widget 1 — "Add Variable" Selectbox** (`variable_editor.py:823-829`):
```python
options = [f"{v['name']} ({v['type']})" for v in available_variables]
selected_option = st.selectbox(
    "Search available variables",
    options=[""] + options,  # ALL 1000+ variables as options
)
```

**Critical Widget 2 — Vector Entries Multiselect** (`variable_editor.py:558-563`):
```python
selected_entries = st.multiselect(
    "Select entries to extract:",
    options=filtered_entries,  # 500+ entries for deep-scanned vectors
)
```

**Critical Widget 3 — Pattern Index Multiselects** (`pattern_index_selector.py:115-122`):
```python
selected = st.multiselect(
    f"Indices for {pos_label}",
    options=available,  # 100+ indices per position
)
```

Streamlit renders ALL options into the browser DOM. No virtualization, no pagination, no server-side filtering.

---

## Data Size Comparison

| Metric | Quick Scan (10 files) | Deep Scan (100+ files) |
|--------|----------------------|----------------------|
| Raw variables found | ~2,000 | ~20,000 |
| After pattern aggregation | ~200 | ~1,000+ |
| Entries per vector | ~50 | ~500+ |
| Entries per histogram | ~20 | ~200+ |
| Pattern indices per var | ~4 | ~50+ |
| Total JSON payload (est.) | ~50 KB | **~2-5 MB** |
| Browser DOM nodes for selectbox | ~200 | **~1,000+** |
| Browser DOM nodes for multiselects | ~200 | **~2,000+** |
| Session state keys | ~50 | ~100+ |

---

## Why Browser Freezes

1. **WebSocket payload**: Streamlit sends the full widget state (including all options for every selectbox/multiselect) over WebSocket on every rerun. With deep scan, this is **2-5 MB per rerun**.

2. **DOM rendering**: Browser must parse and render 1,000+ `<option>` elements per selectbox and 500+ per multiselect. With 5 multiselects open, that's 3,000+ DOM nodes just for options.

3. **JavaScript filtering**: When user types in the selectbox to search, Streamlit's JS frontend filters through ALL options in real-time — O(n) per keystroke with n=1,000+.

4. **Session state serialization**: On every Streamlit rerun, ALL widget values are serialized browser→server. With multiselect selections containing lists of 100+ items, this adds serialization overhead.

---

## Affected Files

| File | Lines | Issue |
|------|-------|-------|
| `variable_editor.py` | 823-829 | Selectbox with all scanned variables |
| `variable_editor.py` | 558-563 | Multiselect with all vector entries |
| `pattern_index_selector.py` | 115-122 | Multiselect with all pattern indices |
| `data_source_components.py` | 209-210 | Full serialization of scan results |
| `variable_editor.py` | 486 | Deep scan results converted without truncation |
| `gem5_scanner.py` | 108 | Entries union grows unbounded |
| `pattern_aggregator.py` | 190-195 | Entries union in aggregation |

---

## Recommended Fix Strategy

### Fix 1: Limit entries list size
Truncate entries to a reasonable max (e.g., 200) during aggregation or before storage. The full list is rarely needed for UI configuration.

### Fix 2: Replace selectbox with text input + server-side search
Instead of rendering 1,000+ options in a selectbox, use `st.text_input` for variable search and filter on the server side, rendering only the top 20-50 matches.

### Fix 3: Paginate or virtualize entry multiselects
For vector entries, show only first 50 and add a "Show all" expander, or use `st.text_input` with a "Select All Matching" pattern.

### Fix 4: Lazy-load entries data
Don't include full entries lists in the stored scanned variables. Load entries on demand when a user clicks to configure a specific variable.
