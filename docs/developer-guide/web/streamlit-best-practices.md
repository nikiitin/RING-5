---
title: "Streamlit Best Practices"
parent: Web Layer
grand_parent: Developer Guide
nav_order: 5
---

# Streamlit Best Practices for RING-5

> **Authoritative Source**: [Streamlit Official Documentation](https://docs.streamlit.io/)
> **Scope**: Principles adapted from Streamlit development literature and official docs, tailored specifically for the RING-5 project architecture.
> **Audience**: All contributors to the RING-5 codebase.

---

## Table of Contents

1. [Execution Model Awareness](#1-execution-model-awareness)
2. [Session State Management](#2-session-state-management)
3. [Widget Discipline](#3-widget-discipline)
4. [Caching Strategy](#4-caching-strategy)
5. [Performance Optimization](#5-performance-optimization)
6. [Layout & UX Patterns](#6-layout--ux-patterns)
7. [Error Handling & User Feedback](#7-error-handling--user-feedback)
8. [Architecture & Code Organization](#8-architecture--code-organization)
9. [Testing Streamlit Code](#9-testing-streamlit-code)
10. [Quick Reference Card](#10-quick-reference-card)

---

## 1. Execution Model Awareness

### The Cardinal Rule

**Streamlit re-executes your entire script from top to bottom on every user interaction.** Every click, every slider drag, every text input triggers a full re-run. This is the single most important concept to internalize — every design decision flows from it.

```text
User interacts with widget
    → st.session_state updated
    → Callback executed (if any)
    → Script re-runs top to bottom
    → UI is re-rendered
```

### Implications for RING-5

| Implication                     | What This Means for Us                                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **No persistent variables**     | Local variables reset on every rerun. All state must live in `st.session_state` or be cached.                                        |
| **Expensive operations repeat** | Parsing gem5 stats, computing shapers, generating Plotly figures — all of these re-execute unless protected by caching or fragments. |
| **Widget values reset**         | Without `key=` parameters and proper state management, widget values revert to defaults on rerun.                                    |
| **Import cost**                 | Module-level code runs every rerun. Keep top-level scope minimal.                                                                    |

### Rules

1. **Never rely on local variable persistence.** If a value must survive a rerun, store it in `st.session_state` or cache it.
2. **Minimize top-level computation.** Move expensive initialization into cached functions or behind conditional guards.
3. **Use `@st.fragment` to isolate independent UI sections.** This prevents a widget in one section from re-running the entire page.
4. **Use `st.form` to batch related inputs.** When multiple widgets collectively produce one action (e.g., creating a plot), wrap them in a form so the script only reruns on submit.

### Fragment Identity

`@st.fragment` is only effective if the decorated function has a **stable identity** across reruns. Streamlit identifies a fragment by the function object it decorates.

```python
# ✅ CORRECT — Define @st.fragment at MODULE level (stable identity)
@st.fragment
def render_outlier_remover(data: pd.DataFrame) -> None:
    ...

# ❌ WRONG — Defining a fragment inside another function creates a NEW
# function object on every rerun, so Streamlit cannot track it and the
# isolation guarantee is lost.
def render_page(data: pd.DataFrame) -> None:
    @st.fragment
    def inner() -> None:  # New identity each rerun — broken isolation
        ...
    inner()
```

**Rule:** Always declare `@st.fragment` functions at module scope, never nested inside another function.

---

## 2. Session State Management

### Architecture: The `UIStateManager` Pattern

RING-5 uses a **centralized typed state manager** (`src/web/state/ui_state_manager.py`) to provide structured access to `st.session_state`. This is the correct pattern — **all new code MUST use `UIStateManager` instead of direct `st.session_state` access.**

#### Why Centralized State

| Direct Access (Anti-Pattern)                    | `UIStateManager` (Correct)                     |
| ----------------------------------------------- | ---------------------------------------------- |
| Typos in key strings cause silent bugs          | Typed methods prevent typos                    |
| No discovery — you don't know what state exists | Central module documents all state keys        |
| Inconsistent naming across files                | Enforced namespace hierarchy                   |
| No validation on reads/writes                   | Can add validation, logging, and type checking |

### Namespace Convention

All state keys MUST follow a **dot-notation namespace hierarchy**:

```text
plot.{plot_id}.auto_refresh      # Per-plot settings
plot.{plot_id}.show_save_dialog  # Per-plot UI state
manager.{name}.load_trigger      # Data manager triggers
nav.current_page                 # Navigation state
export.last_path                 # Export history
```

`UIStateManager` cleanup and scoping rely on these top-level prefixes (`plot.`, `manager.`, `nav.`, `export.`), so keep new keys within this hierarchy.

### Initialization Rules

```python
# ✅ CORRECT — Guard before access
if "my_key" not in st.session_state:
    st.session_state["my_key"] = default_value

# ✅ CORRECT — Safe read with default
value = st.session_state.get("my_key", default_value)

# ❌ WRONG — Unguarded access (KeyError on first run)
value = st.session_state["my_key"]

# ❌ WRONG — Attribute access (inconsistent with dictionary style)
st.session_state.my_key = value
```

### One-Shot Triggers

For actions that should execute once and then be consumed (e.g., "load this saved pipeline"), use the **pop pattern**:

```python
# Producer (e.g., history component)
st.session_state["_outlier_load"] = saved_config

# Consumer (e.g., outlier remover page)
config = st.session_state.pop("_outlier_load", None)
if config is not None:
    apply_config(config)
```

The underscore prefix (`_outlier_load`) signals that this is a transient, one-shot key.

### Session State Rules

1. **All new session state access MUST go through `UIStateManager`.** Do not add new direct `st.session_state` calls in component files.
2. **Use dictionary-style access** (`st.session_state["key"]`), not attribute-style (`st.session_state.key`).
3. **Always initialize before reading.** Use `get()` with a default or an `if key not in` guard.
4. **Namespace all keys.** Use dot notation: `{domain}.{scope}.{property}`.
5. **Use pop for one-shot triggers.** Prefix transient keys with underscore.
6. **Never store Streamlit widgets or figures in session state.** Store only serializable data (strings, numbers, dicts, DataFrames).
7. **Clean up state** when it's no longer needed. The `UIStateManager.cleanup()` method handles this — extend it as new state domains are added.

---

## 3. Widget Discipline

### Key Management

**Every widget MUST have an explicit `key=` parameter.** This is non-negotiable for RING-5.

```python
# ✅ CORRECT — Explicit key
st.selectbox("Plot type", options, key=f"plot_type_{plot_id}")

# ❌ WRONG — No key, identity based on all parameters
st.selectbox("Plot type", options)
```

#### Why Keys Matter

1. **Stable identity**: Widget state survives parameter changes (label text, help text). Without a key, changing the label resets the widget.
2. **Session State access**: Keys allow reading widget values via `st.session_state[key]`.
3. **Uniqueness**: Prevents `DuplicateWidgetID` errors when rendering similar widgets in loops.
4. **Fragment isolation**: Widgets within `@st.fragment` functions need keys for proper state management.

### Namespaced Key Naming Convention

RING-5 widget keys follow a **namespaced `{prefix}_{field}_{id}` convention**: a component/action prefix, the field name, and a scope identifier (typically the plot or step id) to keep keys unique across the whole page.

```python
# Pattern: {prefix}_{field}_{id}
key=f"engine_selector_{plot_id}"
key=f"shaper_mean_method_{step_index}"
key=f"add_shaper_btn_{plot_id}"
key=f"chart_{plot_id}"

# For widgets in loops, include the iteration variable in the id segment:
for i, col in enumerate(columns):
    st.checkbox(col, key=f"col_select_{plot_id}_{i}")
```

This mirrors the `UIStateManager` namespace hierarchy: the `{id}` segment scopes a widget to a specific plot, step, or manager so that repeated controls never collide.

### Callbacks vs. Rerun Model

RING-5 primarily uses the **rerun model** — widgets are read after the full script re-executes, not via callbacks. This is simpler and correct for most cases.

**When to use callbacks (`on_change`/`on_click`):**

- When you need to process a value **before** the UI re-renders (e.g., validation that must happen before layout)
- When a button triggers a one-time action that modifies `session_state` (the callback runs before the rerun)
- In `st.form` — only `st.form_submit_button` supports callbacks inside forms

**When NOT to use callbacks:**

- For reading widget values — just read them after the rerun
- For complex state mutations — prefer explicit state updates in the main script flow
- When you need to render UI elements — callbacks render above the rest of the page

### Widget Value Access

```python
# ✅ CORRECT — Read from the widget's return value
selected = st.selectbox("Select plot", plot_names, key="plot_selector")
# Use `selected` directly

# ✅ CORRECT — Read from session state (e.g., in a different fragment)
selected = st.session_state.get("plot_selector")

# ❌ WRONG — Don't pass widget value via callback args
# The args are captured at widget creation time, not interaction time
st.button("Submit", on_click=process, args=(st.session_state["my_input"],))

# ✅ CORRECT — Read from session state inside the callback
def process():
    value = st.session_state["my_input"]
    # process value
st.button("Submit", on_click=process)
```

### Conditional Widget Rendering

Because the script re-runs top to bottom, you can render widgets conditionally — but be careful: a widget that disappears loses its session-state entry on the next run. Guard validation up front and only render dependent controls once their prerequisites exist.

```python
# ✅ CORRECT — Render dependent widgets only when valid data exists
numeric_cols = data.select_dtypes(include="number").columns.tolist()
if numeric_cols:
    y_col = st.selectbox("Y axis", numeric_cols, key=f"y_col_{plot_id}")
    # Only show error-bar toggle when there is a matching .sd column
    if f"{y_col}.sd" in data.columns:
        st.checkbox("Show error bars", key=f"err_bars_{plot_id}")
else:
    st.warning("No numeric columns available to plot.")
```

### Widget Key Rules

1. **Every widget gets a `key=`.** No exceptions.
2. **Keys must be unique across the entire page** (not just within a function).
3. **Include scope identifiers in keys** (the `{id}` segment) when widgets appear in loops or per-plot contexts.
4. **Prefer the rerun model** over callbacks. Use callbacks only for pre-rerun state mutations.
5. **Never call widget commands inside callbacks.** Callbacks are a prefix to the rerun, not a place for UI rendering.

---

## 4. Caching Strategy

### Current State

RING-5 stores one mutable `ApplicationAPI` workspace per browser session.
Process-global caching is reserved for immutable or explicitly thread-safe
resources such as worker pools.

```python
# app.py
if "api" not in st.session_state:
    st.session_state.api = ApplicationAPI(plot_deserializer=BasePlot.from_dict)
api: ApplicationAPI = st.session_state.api
```

### When to Use Each Decorator

| Decorator            | Use When                                                                                                                                                                               | RING-5 Examples                                                                               |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `@st.cache_data`     | Function returns **serializable data** (DataFrame, dict, list, str, int). Creates a copy on each access — safe from mutations.                                                         | Parsing gem5 stats, loading CSV files, computing shaper transformations, DataFrame operations |
| `@st.cache_resource` | Function returns an **unserializable, thread-safe resource** that may be shared by every session. Returns the same object without mutation protection. | Read-only models or connection pools; not `ApplicationAPI` |

### Key Principle: `@st.cache_data` for DataFrames

**Any function that loads, transforms, or computes a DataFrame should be cached with `@st.cache_data`.**

```python
# ✅ CORRECT — Cache expensive DataFrame operations
@st.cache_data
def apply_shaper_pipeline(
    data: pd.DataFrame,
    pipeline_config: List[Dict[str, Any]]
) -> pd.DataFrame:
    result = data.copy()
    for step in pipeline_config:
        shaper = ShaperFactory.create_shaper(step["type"], step)
        result = shaper(result)
    return result

# ✅ CORRECT — Cache file loading
@st.cache_data
def load_csv_data(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)

# Wrong: caching a mutable workspace as data
@st.cache_data
def get_api():  # API is not serializable!
    return ApplicationAPI()

# Correct: keep mutable workspaces session-owned
if "api" not in st.session_state:
    st.session_state.api = ApplicationAPI()
```

### The Manual, Hash-Based Figure Cache

Plotly figures are **mutated after creation** by RING-5's styling pipeline, so they are *not* safe to cache with `@st.cache_data` (which copies on read but assumes the cached value is treated as immutable). Instead RING-5 uses a **manual, hash-based figure cache**: a stable hash is computed from the plot configuration plus the input data, and a figure is only regenerated when that hash changes. This keeps figure generation off the hot path of every rerun while remaining mutation-aware.

```python
# Conceptual shape of the manual figure cache (mutation-aware)
cache_key = hash_config_and_data(plot_config, data)
if cache_key != cached_key_for_plot:
    figure = generate_figure(plot_config, data)  # expensive
    store_figure(plot_id, cache_key, figure)
else:
    figure = stored_figure(plot_id)
```

The figure cache lives at the controller/component boundary (`PlotRenderController` orchestrates config gathering, figure generation, caching, and chart display). **Do not** wrap figure generation in `@st.cache_data`.

### Caching Rules

1. **Cache all expensive computations** that return data. If a function takes more than ~100ms and returns a DataFrame/dict/list, cache it.
2. **Use `@st.cache_data` by default.** It creates safe copies and prevents mutation bugs.
3. **Use `@st.cache_resource` only for thread-safe shared resources**; mutable
   user workspaces belong in `st.session_state`.
4. **Never mutate cached data in-place.** Always return new DataFrames (this aligns with RING-5's existing immutability rule).
5. **Set `ttl` for external data.** If data can become stale (e.g., file system changes), set a time-to-live.
6. **Use `show_spinner`** for user-visible cached operations: `@st.cache_data(show_spinner="Loading data...")`.
7. **Exclude unhashable parameters** by prefixing with underscore: `def func(_connection, query)`.
8. **Don't cache Plotly figures** with `@st.cache_data`. Use RING-5's manual hash-based figure cache, which is mutation-aware.

### Cache Invalidation

```python
# Clear specific cache
load_csv_data.clear()

# Clear all caches (nuclear option)
st.cache_data.clear()
st.cache_resource.clear()
```

---

## 5. Performance Optimization

### Fragment Isolation (`@st.fragment`)

Fragments are RING-5's **primary performance optimization**. They allow a section of the UI to rerun independently without triggering a full page rerun. (Define them at module level — see [Fragment Identity](#fragment-identity).)

#### Where Fragments Are Used

- **Data managers**: Each tab runs as an independent fragment — changing a setting in the Outlier Remover doesn't re-execute the Seeds Reducer.
- **Plot management**: Pipeline editor and render section are isolated fragments.
- **Data source**: Configuration form runs independently.

#### Fragment Rules

```python
# ✅ CORRECT — Fragment isolates an independent UI section
@st.fragment
def render_outlier_remover(data: pd.DataFrame) -> None:
    method = st.selectbox("Method", ["IQR", "Z-Score"], key="outlier_method")
    threshold = st.slider("Threshold", 1.0, 5.0, 1.5, key="outlier_threshold")
    if st.button("Apply", key="outlier_apply"):
        result = remove_outliers(data, method, threshold)
        st.dataframe(result)

# ❌ WRONG — Fragment returns a value (ignored during fragment reruns)
@st.fragment
def render_outlier_remover(data: pd.DataFrame) -> pd.DataFrame:
    # Return value is silently ignored during fragment reruns!
    return processed_data

# ✅ CORRECT — Fragment communicates via session state
@st.fragment
def render_outlier_remover(data: pd.DataFrame) -> None:
    if st.button("Apply", key="outlier_apply"):
        result = remove_outliers(data, method, threshold)
        st.session_state["outlier_result"] = result
```

#### When to Use Fragments

| Use Fragment                                      | Don't Use Fragment                  |
| ------------------------------------------------- | ----------------------------------- |
| Independent UI sections (tabs, panels)            | Simple pages with few widgets       |
| Sections with expensive computations              | When all widgets affect all outputs |
| Streaming/auto-refreshing components              | When you need return values         |
| Dynamic forms that shouldn't rerun the whole page | When caching is sufficient          |

#### Fragment Pitfalls

1. **Return values are ignored** during fragment reruns. Use `st.session_state` to share data.
2. **Widgets can't be placed in containers created outside the fragment.** All widgets must be in the fragment's main body.
3. **Don't combine `@st.fragment` with `@st.cache_data`** on the same function.
4. **Elements drawn to external containers accumulate** across fragment reruns. Use `st.empty()` to prevent this.

### Lazy Imports

RING-5 implements lazy page imports in `app.py` — each page module is imported only when the user navigates to it. **Continue this pattern for all new pages.**

```python
# ✅ CORRECT — Lazy import
if page == "Manage Plots":
    from src.web.pages.manage_plots import render
    render(api)

# ❌ WRONG — Top-level import (loaded even if page is never visited)
from src.web.pages.manage_plots import render
```

### Minimizing `st.rerun()`

Each `st.rerun()` forces a full script re-execution. **Minimize `st.rerun()` usage:**

```python
# ❌ ANTI-PATTERN — st.rerun() to show updated state
st.session_state["result"] = compute_result()
st.rerun()  # Forces full page rerun just to display result

# ✅ BETTER — Use natural rerun flow or fragments
# If the result will be displayed later in the same script run,
# just set the state and let the script continue.
st.session_state["result"] = compute_result()
# The next widget/display call in this same run will read the updated state

# ✅ ACCEPTABLE — st.rerun() after navigation/mode change
st.session_state["nav.current_page"] = "Manage Plots"
st.rerun()  # Necessary to switch pages
```

**Legitimate uses of `st.rerun()`:**

- After a fragment modifies state that the main page needs to re-render
- After navigation/page switching
- After a dialog/modal is dismissed

**Illegitimate uses (refactor these):**

- To refresh displayed data — use `@st.fragment` or `@st.cache_data` invalidation
- To update a widget value — use callbacks instead
- After every button click — restructure the control flow

### Progress Feedback

Always show progress for operations that take more than ~500ms:

```python
# ✅ For determinate progress (known total steps)
progress = st.progress(0, text="Parsing gem5 stats...")
for i, chunk in enumerate(chunks):
    process(chunk)
    progress.progress((i + 1) / len(chunks), text=f"Parsing {i + 1}/{len(chunks)}...")
progress.empty()  # Clean up when done

# ✅ For indeterminate progress
with st.spinner("Generating LaTeX export..."):
    result = generate_export(figure, config)

# ✅ For multi-step operations
with st.status("Exporting figures...", expanded=True) as status:
    st.write("Extracting layout properties...")
    layout = extract_layout(fig)
    st.write("Converting to matplotlib...")
    mpl_fig = convert(fig, layout)
    st.write("Rendering to PDF...")
    render_pdf(mpl_fig, path)
    status.update(label="Export complete!", state="complete")
```

---

## 6. Layout & UX Patterns

### Column Layouts

```python
# ✅ CORRECT — Semantic column ratios
label_col, input_col = st.columns([1, 3])
label_col.write("**Font Size:**")
font_size = input_col.number_input("Font size", min_value=6, max_value=72,
                                    value=14, key="font_size", label_visibility="collapsed")

# ✅ CORRECT — Equal columns for symmetric layout
col1, col2, col3 = st.columns(3)

# ❌ WRONG — Too many narrow columns (poor UX on mobile)
c1, c2, c3, c4, c5, c6 = st.columns(6)  # Columns become unreadable
```

### Expanders

Use `st.expander` for **advanced/optional settings** that most users won't need:

```python
# ✅ CORRECT — Advanced options hidden by default
with st.expander("Advanced Typography Settings"):
    st.number_input("Title font size", ...)
    st.number_input("Tick font size", ...)
    st.number_input("Title standoff", ...)

# ❌ WRONG — Primary controls hidden in expander
with st.expander("Select your data"):  # This is a primary action!
    st.file_uploader(...)
```

### Tabs

Use `st.tabs` for **parallel content at the same hierarchy level**:

```python
# ✅ CORRECT — Tabs for parallel content
tab_summary, tab_transform, tab_reduce = st.tabs(["Summary", "Transforms", "Reduction"])
with tab_summary:
    render_summary()
with tab_transform:
    render_transforms()

# ❌ WRONG — Tabs for sequential workflow (use numbered steps instead)
tab1, tab2, tab3 = st.tabs(["Step 1: Upload", "Step 2: Configure", "Step 3: Run"])
```

### Forms

Use `st.form` to **batch related inputs** that collectively trigger one action:

```python
# ✅ CORRECT — Create plot form batches name + type
with st.form("create_plot_form"):
    name = st.text_input("Plot name", key="new_plot_name")
    plot_type = st.selectbox("Type", plot_types, key="new_plot_type")
    submitted = st.form_submit_button("Create Plot")
    if submitted:
        create_plot(name, plot_type)

# ❌ WRONG — Form for a single toggle (overkill)
with st.form("toggle_form"):
    st.checkbox("Enable feature")
    st.form_submit_button("Apply")
```

**Form limitations to remember:**

- `st.button` and `st.download_button` cannot be inside a form.
- Only `st.form_submit_button` supports `on_click` callbacks inside forms.
- Interdependent widgets inside a form won't update each other until submit.
- Forms cannot be nested.

### Sidebar

RING-5 uses the sidebar for **navigation only** (via `st.radio`). Keep it clean:

```python
# ✅ CORRECT — Sidebar for navigation
with st.sidebar:
    page = st.radio("Navigation", pages, key="nav_page", label_visibility="collapsed")

# ❌ WRONG — Cluttering sidebar with page-specific controls
with st.sidebar:
    st.selectbox("Plot type", ...)  # This belongs on the page
    st.slider("Threshold", ...)     # Not navigation
```

---

## 7. Error Handling & User Feedback

### Message Hierarchy

RING-5 uses a clear hierarchy of feedback — **maintain this consistently**:

| Function         | Purpose                | When to Use                                           | Duration                                       |
| ---------------- | ---------------------- | ----------------------------------------------------- | ---------------------------------------------- |
| `st.info()`      | Instructional guidance | Explain features, suggest next steps                  | Persistent                                     |
| `st.success()`   | Operation confirmation | After successful parse/export/save                    | Persistent (consider `st.toast` for transient) |
| `st.warning()`   | Soft warning           | Missing optional data, suboptimal config              | Persistent                                     |
| `st.error()`     | Critical error         | Parse failure, missing required data, exceptions      | Persistent                                     |
| `st.toast()`     | Transient notification | Quick confirmations that don't need to persist        | Auto-dismiss (~4s)                             |
| `st.exception()` | Debug traceback        | **Development/debug mode only** — never in production | Persistent                                     |

### Feedback Rules

```python
# ✅ CORRECT — Actionable error messages
st.error("No data loaded. Navigate to **Data Source** to parse gem5 stats files.")

# ❌ WRONG — Vague error
st.error("Error occurred")

# ✅ CORRECT — Exception with context
try:
    result = parse_stats(path)
except FileNotFoundError:
    st.error(f"Stats file not found: `{path}`. Check your data source configuration.")
except ValueError as e:
    st.error(f"Parse error: {e}")

# ❌ WRONG — Bare except
try:
    result = parse_stats(path)
except:
    st.error("Something went wrong")

# ✅ RECOMMENDED — Use st.toast for transient success
st.toast("✓ Plot saved successfully", icon="✅")
# Instead of persistent:
st.success("✓ Plot saved successfully")  # This stays on screen until next rerun
```

### Validation Pattern (Hydrate-then-Render)

RING-5 follows a **Hydrate-then-Render** discipline: first hydrate the state and validate inputs (early-return on failure), *then* render widgets against known-good data. Never render dependent widgets before their preconditions hold.

```python
# ✅ CORRECT — Hydrate-then-Render: validate, then render
def render_plot_config(data: pd.DataFrame, plot_id: str) -> None:
    # 1. Hydrate / validate
    if data.empty:
        st.warning("No data available. Load data first.")
        return

    numeric_cols = data.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        st.error("No numeric columns found in the dataset.")
        return

    # 2. Render against valid data
    selected_col = st.selectbox("Column", numeric_cols, key=f"col_{plot_id}")
```

---

## 8. Architecture & Code Organization

### Page-Controller-Component (PCC) Pattern (Manage Plots)

The **Manage Plots** page implements RING-5's reference **Page-Controller-Component (PCC)** architecture. This is the architecture for new page implementations. There is **no presenter layer** — pages wire controllers to components, controllers orchestrate, and components render widgets.

```text
Page (Layer 1)        -- thin wiring, adapter creation, fragment setup
  ↓
Controller (Layer 2)  -- orchestration, state reads, action dispatch (no widget rendering)
  ↓
Component (Layer 3)   -- widget rendering, returns user selections
  ↓
ApplicationAPI        -- domain operations facade (src/core/application_api.py)
```

#### The Plot Controllers

Three stateless controllers (`src/web/controllers/plot/`) manage the plot lifecycle on the **Manage Plots** page:

| Controller | File | Responsibility |
|---|---|---|
| `PlotCreationController` | `src/web/controllers/plot/creation_controller.py` | Create, select, rename, delete, duplicate plots |
| `PipelineController` | `src/web/controllers/plot/pipeline_controller.py` | Add, remove, reorder shapers; finalize pipeline |
| `PlotRenderController` | `src/web/controllers/plot/render_controller.py` | Config gathering, figure generation, caching, chart display |

Controllers are **stateless** — instantiated fresh on every rerun, receiving dependencies via constructor injection. Persistent state lives in `ApplicationAPI.state_manager` (domain) or `UIStateManager` (transient UI).

#### Key Principles

1. **Controllers never render widgets.** They use Streamlit only for flow control (`st.rerun()`), error display (`st.exception()`), and non-blocking notifications (`st.toast()`). All widget rendering is delegated to components.
2. **Components are passive.** A component renders widgets and returns the user's selections; it holds no domain logic.
3. **The `ApplicationAPI` facade** (`src/core/application_api.py`) is the single entry point to domain operations. Controllers call it; components never do.
4. **`UIStateManager`** owns all transient `st.session_state` access in new code.

```python
# ✅ CORRECT — Controller orchestrates, delegates rendering to a component
class PlotRenderController:
    def __init__(self, api: ApplicationAPI, chart: ChartDisplayComponent) -> None:
        self._api = api
        self._chart = chart

    def render(self, config: PlotConfig, data: pd.DataFrame, plot_id: str) -> None:
        figure = self._api.generate_figure(config, data)  # domain via facade
        self._chart.render_plotly_chart(figure, plot_id)  # widget rendering delegated

# ✅ CORRECT — Component renders the chart widget (no domain logic)
class ChartDisplayComponent:  # src/web/components/common/chart_display.py
    def render_plotly_chart(self, figure: go.Figure, plot_id: str) -> None:
        st.plotly_chart(figure, use_container_width=True, key=f"chart_{plot_id}")

# ✅ CORRECT — Page wires controller + component together
def render(api: ApplicationAPI) -> None:
    controller = PlotRenderController(api=api, chart=ChartDisplayComponent())
    controller.render(config, data, plot_id)
```

> The chart-rendering responsibility lives in `ChartDisplayComponent`
> (`src/web/components/common/chart_display.py`), which exposes `render_plotly_chart`,
> `render_matplotlib_chart`, `render_engine_selector`, `render_refresh_controls`, and
> `render_error`.

### Other UI Components

Reusable components live under `src/web/components/`:

- `src/web/components/common/` — chart display, selectors, history, layout, pipeline editor, plot controls.
- `src/web/components/shapers/` — UI configuration widgets for shapers (mean, normalize, pivot, sort, split-apply, selector/transformer configs).
- `src/web/components/data_managers/`, `src/web/components/data_source/` — data manager and data source UIs.

Shaper UI configs (`src/web/components/shapers/`) only collect parameters; the actual transforms are implemented in the core shaper services (`src/core/services/shapers/`, with `factory.py`, `impl/`, and `shaper.py`).

### File Organization Rules

| Layer             | Directory                          | Allowed Imports                                              |
| ----------------- | ---------------------------------- | ----------------------------------------------------------- |
| **Pages**         | `src/web/pages/`                   | Controllers, components, `UIStateManager`, `ApplicationAPI`  |
| **Controllers**   | `src/web/controllers/`             | `ApplicationAPI`, models, components — **no widget rendering** |
| **Components**    | `src/web/components/`              | `streamlit`, models — **no domain services**                |
| **UI helpers**    | `src/web/pages/ui/`               | `streamlit`, utility functions                              |
| **State (UI)**    | `src/web/state/`                   | `streamlit.session_state`                                   |
| **Domain/Core**   | `src/core/` (incl. `src/core/services/`, `src/core/state/`, `src/parsing/`) | **NEVER import streamlit** |

### The Session Workspace

`ApplicationAPI` (`src/core/application_api.py`) is created once for each
browser session and passed down through the call chain. Do not construct a
second API within the same session; a separate browser session must receive a
separate instance.

```python
if "api" not in st.session_state:
    st.session_state.api = ApplicationAPI(plot_deserializer=BasePlot.from_dict)
api: ApplicationAPI = st.session_state.api
```

---

## 9. Testing Streamlit Code

### Testing Strategy

RING-5 uses `pytest` for all testing. Streamlit UI code presents unique testing challenges because of the execution model. Run the full suite with `make test`.

#### What to Test and How

| Layer                 | Test Approach                                 | Tools                          |
| --------------------- | --------------------------------------------- | ------------------------------ |
| **Domain/Core logic** | Standard unit tests — no Streamlit dependency | `pytest`, mocks                |
| **Controllers**       | Unit tests with a mocked `ApplicationAPI` and mocked components | `pytest`, `unittest.mock`      |
| **Components**        | Integration tests with `AppTest` (if needed)  | `streamlit.testing.v1.AppTest` |
| **State management**  | Unit tests mocking `st.session_state`         | `pytest`, mock dict            |
| **Full page flows**   | Streamlit's `AppTest` framework               | `streamlit.testing.v1.AppTest` |

#### `AppTest` for Streamlit Integration Tests

Streamlit provides `AppTest` for headless testing of apps without a browser:

```python
from streamlit.testing.v1 import AppTest

def test_plot_creation() -> None:
    at = AppTest.from_file("app.py")
    at.run()

    # Interact with widgets by key
    at.text_input(key="new_plot_name").input("My Plot").run()
    at.selectbox(key="new_plot_type").select("Bar Chart").run()
    at.button(key="create_plot_btn").click().run()

    # Assert outcomes
    assert not at.exception
    assert "My Plot" in at.session_state["plots"]
```

#### Mocking Session State

For unit testing code that uses `UIStateManager`:

```python
from unittest.mock import patch

def test_state_manager_reads_plot_config() -> None:
    mock_state: Dict[str, Any] = {
        "plot.abc123.auto_refresh": True,
        "plot.abc123.show_save_dialog": False,
    }
    with patch("streamlit.session_state", mock_state):
        manager = UIStateManager()
        assert manager.get_auto_refresh("abc123") is True
```

### Testing Rules

1. **Domain logic must be testable without Streamlit.** If a test requires `import streamlit`, the code under test has a design problem.
2. **Use `AppTest` for integration tests**, not manual browser testing.
3. **Mock `st.session_state` as a dictionary** for unit tests — it behaves like one.
4. **Test controllers with a mocked `ApplicationAPI` and mocked components**, not real domain services.
5. **Don't test Streamlit widgets themselves** — test the logic that feeds them.

---

## 10. Quick Reference Card

```text
┌──────────────────────────────────────────────────────────┐
│                  STREAMLIT DECISION TREE                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Need to persist data across reruns?                     │
│    → st.session_state (via UIStateManager)               │
│                                                          │
│  Function returns serializable data (DataFrame, etc.)?   │
│    → @st.cache_data                                      │
│                                                          │
│  Function returns a singleton resource (API, pool)?      │
│    → @st.cache_resource                                  │
│                                                          │
│  Plotly figure mutated after creation?                   │
│    → manual hash-based figure cache (NOT @st.cache_data) │
│                                                          │
│  UI section independent from the rest of the page?       │
│    → @st.fragment (defined at module level)              │
│                                                          │
│  Multiple inputs that collectively trigger one action?   │
│    → st.form                                             │
│                                                          │
│  Need a value update before the UI re-renders?           │
│    → on_change / on_click callback                       │
│                                                          │
│  Long operation (>500ms)?                                │
│    → st.spinner / st.progress / st.status               │
│                                                          │
│  Quick confirmation message?                             │
│    → st.toast (transient) or st.success (persistent)     │
│                                                          │
│  Advanced settings most users won't touch?               │
│    → st.expander                                         │
│                                                          │
│  Parallel content at the same level?                     │
│    → st.tabs                                             │
│                                                          │
│  New page? Wire it as Page → Controller → Component.     │
│    (No presenter layer.)                                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Checklist for New Features

Before submitting any new RING-5 feature involving Streamlit UI:

- [ ] All widgets have explicit `key=` parameters using the `{prefix}_{field}_{id}` convention
- [ ] All session state access goes through `UIStateManager`
- [ ] No direct `st.session_state` in new component files
- [ ] Expensive computations are cached (`@st.cache_data`); figures use the manual hash-based cache
- [ ] Independent UI sections are wrapped in `@st.fragment` defined at module level
- [ ] Batch inputs use `st.form` where appropriate
- [ ] New pages follow the Page → Controller → Component pattern (no presenter layer)
- [ ] Error messages are actionable and user-friendly
- [ ] No Streamlit imports in the domain/core layer (`src/core/`)
- [ ] Controllers delegate widget rendering to components
- [ ] Progress indicators shown for operations > 500ms
- [ ] Type hints on all functions (mandatory per project rules)
- [ ] Tests written and passing (`make test`); use `AppTest` for UI flows if needed

---

_Based on Streamlit official documentation at [docs.streamlit.io](https://docs.streamlit.io/)._
