# Manage Plots System Reference

> **Purpose**: Complete reference for the Manage Plots page architecture,
> covering all files, widgets, and interaction flows needed for E2E testing.

---

## 1. Architecture Overview

```
manage_plots.py (104 lines — orchestrator)
    │
    ├── PlotCreationController (252 lines)
    │    ├── PlotCreationPresenter  → create form
    │    ├── PlotSelectorPresenter  → plot pills
    │    ├── PlotControlsPresenter  → rename/delete/duplicate
    │    ├── SaveDialogPresenter    → save pipeline dialog
    │    └── LoadDialogPresenter    → load pipeline dialog
    │
    ├── PipelineController (200 lines)
    │    ├── PipelinePresenter      → shaper add/remove/reorder
    │    └── PipelineStepPresenter  → per-step config + preview
    │
    └── PlotRenderController (316 lines)
         ├── ConfigPresenter        → type selector + settings pills
         └── ChartPresenter         → engine selector + chart display + download
```

**Total**: ~50 files, ~13,500 lines

---

## 2. Widget Map (Interactive Elements)

### 2.1 Create Plot Section

| Widget | Type | Key | Selector Strategy |
|--------|------|-----|-------------------|
| Plot name | `st.text_input` | `new_plot_name` | `get_by_label("New plot name")` |
| Plot type | `st.selectbox` | `new_plot_type` | `_by_label("stSelectbox", "Plot type")` |
| Create button | `st.form_submit_button` | inside `create_plot_form` | `get_by_role("button", name="Create Plot")` |

**Available plot types** (selectbox options):
1. `bar` — "Bar Chart"
2. `dual_axis_bar_dot` — "Dual Axis Bar & Dot"
3. `grouped_bar` — "Grouped Bar Chart"
4. `stacked_bar` — "Stacked Bar Chart"
5. `grouped_stacked_bar` — "Grouped Stacked Bar"
6. `histogram` — "Histogram"
7. `line` — "Line Plot"
8. `scatter` — "Scatter Plot"

### 2.2 Plot Selector

| Widget | Type | Key | Selector Strategy |
|--------|------|-----|-------------------|
| Plot selector pills | `st.pills` | `plot_selector` | `get_by_text("Select Plot")` area, then pills |

### 2.3 Controls Row

| Widget | Type | Key | Selector Strategy |
|--------|------|-----|-------------------|
| Rename | `st.text_input` | `rename_{plot_id}` | `get_by_label("Rename plot")` |
| Save Pipe | `st.button` | `save_plot_{plot_id}` | `get_by_role("button", name="Save Pipe")` |
| Load Pipe | `st.button` | `load_plot_{plot_id}` | `get_by_role("button", name="Load Pipe")` |
| Delete | `st.button` | `delete_plot_{plot_id}` | `get_by_role("button", name="Delete")` |
| Duplicate | `st.button` | `dup_plot_{plot_id}` | `get_by_role("button", name="Duplicate")` |

### 2.4 Pipeline Editor (`@st.fragment`)

| Widget | Type | Key | Selector Strategy |
|--------|------|-----|-------------------|
| Add transformation | `st.selectbox` | `shaper_add_{plot_id}` | `_by_label("stSelectbox", "Add transformation")` |
| Add to Pipeline | `st.button` | `add_shaper_btn_{plot_id}` | `get_by_role("button", name="Add to Pipeline")` |
| Step expanders | `st.expander` | dynamic | `locator("[data-testid='stExpander']")` in pipeline section |
| Up/Down/Del buttons | `st.button` | `up_/down_/del_{id}_{idx}` | `get_by_role("button", name="Up/Down/Del")` |
| Finalize | `st.button` (primary) | `finalize_{plot_id}` | `get_by_role("button", name="Finalize Pipeline for Plotting")` |

**Available shapers** (selectbox options):
1. Column Selector — `columnSelector`
2. Sort — `sort`
3. Mean Calculator — `mean`
4. Normalize — `normalize`
5. Filter — `conditionSelector`
6. Split-Apply (Per-Axis) — `splitApply`
7. Transformer — `transformer`

### 2.5 Visualization Section (`@st.fragment`)

| Widget | Type | Key | Selector Strategy |
|--------|------|-----|-------------------|
| Plot Type selector | `st.selectbox` | `plot_type_sel_{id}` | `_by_label("stSelectbox", "Plot Type")` |
| X-axis | `st.selectbox` | `x_{id}` | `_by_label("stSelectbox", "X-axis")` |
| Y-axis | `st.selectbox` | `y_{id}` | `_by_label("stSelectbox", "Y-axis")` |
| Title | `st.text_input` | dynamic | `_by_label("stTextInput", "Title")` |
| X-label | `st.text_input` | dynamic | `_by_label("stTextInput", "X-axis label")` |
| Y-label | `st.text_input` | dynamic | `_by_label("stTextInput", "Y-axis label")` |
| Color by | `st.selectbox` | dynamic | `_by_label("stSelectbox", "Color by")` |
| Group by | `st.selectbox` | dynamic | `_by_label("stSelectbox", "Group by")` |
| Stack by | `st.selectbox` | dynamic | `_by_label("stSelectbox", "Stack by")` |
| Auto-refresh | `st.toggle` | `auto_t_{id}` | `get_by_text("Auto-refresh")` |
| Refresh Plot | `st.button` | `refresh_{id}` | `get_by_role("button", name="Refresh Plot")` |
| Engine selector | `st.pills` | `engine_selector_{id}` | pills containing "plotly" / "matplotlib" |
| Show advanced | `st.toggle` | `show_advanced_{id}` | `get_by_text("Show advanced settings")` |
| Settings pills | `st.pills` | `settings_nav` | Settings section navigation |
| Plotly chart | `interactive_plotly_chart` | — | `[data-testid='stPlotlyChart']` |
| Matplotlib chart | `st.pyplot` | — | canvas/image element |

### 2.6 Download Section (inside expander)

| Widget | Type | Key | Selector Strategy |
|--------|------|-----|-------------------|
| Download expander | `st.expander` | — | `locator("[data-testid='stExpander']").filter(has_text="Download")` |
| Format pills | `st.pills` | `dl_fmt_{id}` | pills with format options |
| Download button | `st.download_button` | `dl_btn_{id}` | `get_by_role("button", name="Download")` |

### 2.7 Workspace Management

| Widget | Type | Key | Selector Strategy |
|--------|------|-----|-------------------|
| Export path | `st.text_input` | `export_path_input` | `get_by_label("Local Download Path")` |
| Force format | `st.selectbox` | `export_fmt_override` | `_by_label("stSelectbox", "Force Format")` |
| Download All | `st.button` | `export_all_btn` | `get_by_role("button", name="Download All")` |
| Process All | `st.button` | — | `get_by_role("button", name="Process All Plots in Parallel")` |
| Save Workspace | `st.button` | — | `get_by_role("button", name="Save Entire Workspace")` |

---

## 3. Plot Type Configuration Widgets

Each plot type extends `BasePlot.render_common_config()` with additional widgets:

### 3.1 Bar Chart (`bar`)
| Widget | Type | Label |
|--------|------|-------|
| X-axis | selectbox | "X-axis" |
| Y-axis | selectbox | "Y-axis" |
| Color by | selectbox | "Color by (optional)" |

### 3.2 Line Plot (`line`)
| Widget | Type | Label |
|--------|------|-------|
| X-axis | selectbox | "X-axis" |
| Y-axis | selectbox | "Y-axis" |
| Color by | selectbox | "Color by (optional)" |

### 3.3 Scatter Plot (`scatter`)
| Widget | Type | Label |
|--------|------|-------|
| X-axis | selectbox | "X-axis" |
| Y-axis | selectbox | "Y-axis" |
| Color by | selectbox | "Color by (optional)" |
| Size by | selectbox | "Size by (optional)" |

### 3.4 Grouped Bar Chart (`grouped_bar`)
| Widget | Type | Label |
|--------|------|-------|
| X-axis | selectbox | "X-axis" |
| Y-axis | selectbox | "Y-axis" |
| Group by | selectbox | "Group by" |

### 3.5 Stacked Bar Chart (`stacked_bar`)
| Widget | Type | Label |
|--------|------|-------|
| X-axis | selectbox | "X-axis" |
| Y-axis | selectbox | "Y-axis" |
| Stack by | selectbox | "Stack by" |

### 3.6 Grouped Stacked Bar (`grouped_stacked_bar`) — 1400 lines
Complex multi-column configuration. Most complex plot type.

### 3.7 Histogram (`histogram`)
Custom bins/range widgets, different from standard X/Y pattern.

### 3.8 Dual Axis Bar & Dot (`dual_axis_bar_dot`)
Dual-axis configuration, primary + secondary axis selectors.

---

## 4. Rendering Engines

### 4.1 Plotly (default)
- Renders via custom Streamlit component `interactive_plotly_chart()`
- Captures relayout events (zoom/pan) back to Python via JS→Streamlit bridge
- Download formats: PNG, SVG, PDF

### 4.2 Matplotlib
- Renders via `st.pyplot(mpl_fig)`
- Used for publication-quality exports
- Download formats: PDF, PGF, PNG, SVG
- PGF export uses XeLaTeX/pdflatex/lualatex

---

## 5. Preconditions for Testing

### 5.1 Data Must Be Loaded
Without data, the page shows `st.warning("No data loaded")` or similar.
The pipeline editor and viz sections are not rendered.

### 5.2 Pipeline Must Be Finalized
After adding shapers, user must click "Finalize Pipeline for Plotting"
to process the data. Until finalized, the visualization section shows
"No processed data available."

### 5.3 Plot Configuration Must Be Set
X/Y axis selectors must have valid column selections before the chart
can render. Otherwise, error messages appear.

---

## 6. Minimal Happy Path (E2E)

```
1. Data Source page: scan + add variable + parse → data loaded
2. Navigate to Manage Plots
3. Type plot name → Select type → Create Plot
4. Add "Column Selector" shaper → Configure columns
5. Click "Finalize Pipeline for Plotting"
6. Select X-axis column
7. Select Y-axis column
8. Click "Refresh Plot" (or enable Auto-refresh)
9. → Plotly chart visible ✓
```

**Estimated time**: ~40-60s total (30s for parse + 10s for plot creation/config)

---

## 7. Shaper Configuration Reference

### 7.1 Column Selector
- `st.multiselect("Select columns")` — choose which columns to keep
- Quick action buttons: "Select All", "Clear All", "Numeric Only"

### 7.2 Sort
- `st.selectbox("Sort by column")`
- `st.selectbox("Order")` — Ascending / Descending

### 7.3 Mean Calculator
- `st.multiselect("Group by columns")`
- `st.multiselect("Calculate mean for")`

### 7.4 Normalize
- `st.selectbox("Column to normalize")`
- `st.selectbox("Normalization method")`

### 7.5 Filter (conditionSelector)
- `st.selectbox("Column")`
- `st.selectbox("Operator")` — ==, !=, >, <, >=, <=, contains, not contains
- `st.text_input("Value")`

### 7.6 Split-Apply (Per-Axis)
Most complex shaper — multi-step configuration with axis bindings.
- `st.selectbox("Split column")`
- `st.selectbox("Apply function")`
- Multiple sub-configuration options

### 7.7 Transformer
- `st.selectbox("Source column")`
- `st.selectbox("Transformation")`
- `st.text_input("New column name")`

---

## 8. Session State Key Map

All session state keys use `plot_id` as suffix for per-plot isolation:

| Pattern | Example | Purpose |
|---------|---------|---------|
| `new_plot_name` | — | Create form: name input |
| `new_plot_type` | — | Create form: type selectbox |
| `plot_selector` | — | Currently selected plot |
| `rename_{id}` | `rename_abc123` | Rename input |
| `shaper_add_{id}` | `shaper_add_abc123` | Shaper type selectbox |
| `finalize_{id}` | `finalize_abc123` | Finalize button |
| `plot_type_sel_{id}` | `plot_type_sel_abc123` | Viz plot type |
| `x_{id}` | `x_abc123` | X-axis column |
| `y_{id}` | `y_abc123` | Y-axis column |
| `auto_t_{id}` | `auto_t_abc123` | Auto-refresh toggle |
| `refresh_{id}` | `refresh_abc123` | Manual refresh |
| `engine_selector_{id}` | `engine_selector_abc123` | Engine pills |
| `show_advanced_{id}` | `show_advanced_abc123` | Advanced toggle |
| `settings_nav` | — | Settings section pills (shared!) |
| `dl_fmt_{id}` | `dl_fmt_abc123` | Download format |
| `dl_btn_{id}` | `dl_btn_abc123` | Download button |
