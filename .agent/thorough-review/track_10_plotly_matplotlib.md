# Track 10: Plotly & Matplotlib Patterns

> **Priority**: MEDIUM
> **Status**: PENDING
> **Estimated items**: 6
> **Scope**: `src/web/rendering/`, `src/web/pages/ui/plotting/`
> **Project Rule**: NO Plotly Express in production (from `.github/copilot-instructions.md`)

---

## What to Look At

### 10.1 Batch `fig.update_layout()` calls in plotly_connector.py

**File**: `src/web/rendering/plotly_connector.py`
**What**: 11 scattered `fig.update_layout()` calls throughout the connector. Each call triggers Plotly's internal validation. Batching into a single call with all parameters is both faster and cleaner.
**Example**:
```python
# Current (11 separate calls):
fig.update_layout(title="...")
fig.update_layout(xaxis=dict(...))
fig.update_layout(yaxis=dict(...))
...

# Better (single call):
fig.update_layout(
    title="...",
    xaxis=dict(...),
    yaxis=dict(...),
    ...
)
```

### 10.2 Ensure Matplotlib figure cleanup — NO `plt.close()` anywhere

**Scope**: All files using `matplotlib`
**What**: Deep audit found ZERO `plt.close()` calls in the entire codebase. Matplotlib figures are created but never explicitly closed, causing memory leaks. Each unclosed figure retains all its data in matplotlib's global state.
**Files**: `src/web/rendering/matplotlib_connector.py`, any file calling `plt.figure()` or `fig, ax = plt.subplots()`.

### 10.3 Matplotlib figures stored in `session_state`

**File**: `src/web/components/common/chart_display.py`, line ~172
**What**: `matplotlib.figure.Figure` objects stored in `st.session_state`. These objects:
- Cannot be serialized (breaks session state persistence)
- Hold large amounts of memory
- Can't be garbage collected while referenced in session state
**Fix**: Don't store figures. Re-render on demand or cache the rendered image bytes.

### 10.4 `st.pyplot()` usage without figure cleanup

**Scope**: All `st.pyplot()` calls
**What**: `st.pyplot(fig)` renders the figure but doesn't close it. Must explicitly call `plt.close(fig)` after `st.pyplot()`.

### 10.5 Grouped stacked bar bypasses centralized FigureSpecToPlotly pipeline

**File**: `src/web/pages/ui/plotting/grouped_stacked_bar_plot.py`
**What**: This plot type builds its figure directly using `go.Figure()` instead of going through the `FigureSpecToPlotly` pipeline that all other plot types use. This means:
- Config builder features don't apply
- Layout settings may be inconsistent
- Any future pipeline enhancements won't benefit this plot type

### 10.6 Standardize figure export approach

**Scope**: All export code paths
**What**: Export may use different methods across Plotly vs Matplotlib. Standardize on:
- Plotly: `fig.write_image()` with kaleido backend
- Matplotlib: `fig.savefig()` with `bbox_inches='tight'`

---

## How to Investigate

1. **For 10.1**: Read plotly_connector.py. Find all `fig.update_layout()` calls. Group by the function they're in. Batch.
2. **For 10.2**: `grep -rn "plt.close\|plt.clf" src/` — confirm zero results. Then find all figure creation: `grep -rn "plt.figure\|plt.subplots\|Figure(" src/`. Add `plt.close(fig)` in `finally` blocks.
3. **For 10.3**: Read chart_display.py line 172. Trace how the figure is used. Replace with re-render or image bytes.
4. **For 10.4**: Find all `st.pyplot(` calls. Add `plt.close(fig)` immediately after each.
5. **For 10.5**: Read grouped_stacked_bar_plot.py. Compare with other plot types' rendering path. Evaluate if migration to FigureSpec pipeline is feasible.
6. **For 10.6**: Search for all export/save code. Standardize approach.

---

## What We Expect to Find

- **10.1**: 11 calls can be consolidated into 3-4 batched calls (one per logical section).
- **10.2**: Confirmed zero `plt.close()` calls. All matplotlib figure creation sites need cleanup.
- **10.3**: Confirmed figure stored in session state. Replace with image bytes or re-render.
- **10.5**: Grouped stacked bar can be partially migrated. Some custom layout logic must stay.

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 10.1 Batch update_layout | PENDING | | |
| 10.2 plt.close() cleanup | PENDING | | |
| 10.3 Figure in session_state | PENDING | | |
| 10.4 st.pyplot cleanup | PENDING | | |
| 10.5 Grouped stacked bar | PENDING | | |
| 10.6 Export standardization | PENDING | | |
