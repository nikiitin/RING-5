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
10. [RING-5 Current State & Migration Path](#10-ring-5-current-state--migration-path)

---

## 1. Execution Model Awareness

### The Cardinal Rule

**Streamlit re-executes your entire script from top to bottom on every user interaction.** Every click, every slider drag, every text input triggers a full re-run. This is the single most important concept to internalize — every design decision flows from it.

```
User interacts with widget
    → st.session_state updated
    → Callback executed (if any)
    → Script re-runs top to bottom
    → UI is re-rendered
```

### Implications for RING-5

| Implication | What This Means for Us |
|---|---|
| **No persistent variables** | Local variables reset on every rerun. All state must live in `st.session_state` or be cached. |
| **Expensive operations repeat** | Parsing gem5 stats, computing shapers, generating Plotly figures — all of these re-execute unless protected by caching or fragments. |
| **Widget values reset** | Without `key=` parameters and proper state management, widget values revert to defaults on rerun. |
| **Import cost** | Module-level code runs every rerun. Keep top-level scope minimal. |

### Rules

1. **Never rely on local variable persistence.** If a value must survive a rerun, store it in `st.session_state` or cache it.
2. **Minimize top-level computation.** Move expensive initialization into cached functions or behind conditional guards.
3. **Use `@st.fragment` to isolate independent UI sections.** This prevents a widget in one section from re-running the entire page.
4. **Use `st.form` to batch related inputs.** When multiple widgets collectively produce one action (e.g., creating a plot), wrap them in a form so the script only reruns on submit.

---

## 2. Session State Management

### Architecture: The `UIStateManager` Pattern

RING-5 uses a **centralized typed state manager** (`src/web/state/ui_state_manager.py`) to provide structured access to `st.session_state`. This is the correct pattern — **all new code MUST use `UIStateManager` instead of direct `st.session_state` access.**

#### Why Centralized State

| Direct Access (Anti-Pattern) | `UIStateManager` (Correct) |
|---|---|
| Typos in key strings cause silent bugs | Typed methods prevent typos |
| No discovery — you don't know what state exists | Central module documents all state keys |
| Inconsistent naming across files | Enforced namespace hierarchy |
| No validation on reads/writes | Can add validation, logging, and type checking |

### Namespace Convention

All state keys MUST follow a **dot-notation namespace hierarchy**:

```
plot.{plot_id}.auto_refresh      # Per-plot settings
plot.{plot_id}.show_save_dialog  # Per-plot UI state
manager.{name}.load_trigger      # Data manager triggers
nav.current_page                 # Navigation state
export.last_path                 # Export history
```

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

### Rules

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

### Key Naming Convention

```python
# Pattern: {component}_{widget_type}_{scope_id}
key=f"style_color_picker_{plot_id}"
key=f"shaper_mean_method_{step_index}"
key=f"datasource_stats_path_input"

# For widgets in loops, include the iteration variable:
for i, col in enumerate(columns):
    st.checkbox(col, key=f"col_select_{plot_id}_{i}")
```

### Callbacks vs. Rerun Model

RING-5 currently uses the **rerun model** — widgets are read after the full script re-executes, not via callbacks. This is simpler and correct for most cases.

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

### Rules

1. **Every widget gets a `key=`.** No exceptions.
2. **Keys must be unique across the entire page** (not just within a function).
3. **Include scope identifiers in keys** when widgets appear in loops or per-plot contexts.
4. **Prefer the rerun model** over callbacks. Use callbacks only for pre-rerun state mutations.
5. **Never call widget commands inside callbacks.** Callbacks are a prefix to the rerun, not a place for UI rendering.

---

## 4. Caching Strategy

### Current State

RING-5 uses a single `@st.cache_resource` to cache the `ApplicationAPI` singleton. This is correct — the API object is an unserializable resource that manages domain state and should exist as a singleton across all reruns.

### When to Use Each Decorator

| Decorator | Use When | RING-5 Examples |
|---|---|---|
| `@st.cache_data` | Function returns **serializable data** (DataFrame, dict, list, str, int). Creates a copy on each access — safe from mutations. | Parsing gem5 stats, loading CSV files, computing shaper transformations, DataFrame operations |
| `@st.cache_resource` | Function returns **unserializable resources** that should be shared as singletons (connections, models, API objects). Returns the **same object** — not thread-safe against mutations. | `ApplicationAPI` instance, potentially `WorkPool` singleton |

### Key Principle: `@st.cache_data` for DataFrames

**Any function that loads, transforms, or computes a DataFrame should be cached with `@st.cache_data`.** This is currently missing in RING-5 for shaper operations and is a performance improvement opportunity.

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

# ❌ WRONG — Caching a mutable resource as data
@st.cache_data
def get_api():  # API is not serializable!
    return ApplicationAPI()

# ✅ CORRECT — Use cache_resource for the API
@st.cache_resource
def get_api() -> ApplicationAPI:
    return ApplicationAPI()
```

### Caching Rules

1. **Cache all expensive computations** that return data. If a function takes more than ~100ms and returns a DataFrame/dict/list, cache it.
2. **Use `@st.cache_data` by default.** It creates safe copies and prevents mutation bugs.
3. **Use `@st.cache_resource` only for singletons** (API objects, connection pools, WorkPool).
4. **Never mutate cached data in-place.** Always return new DataFrames (this aligns with RING-5's existing immutability rule).
5. **Set `ttl` for external data.** If data can become stale (e.g., file system changes), set a time-to-live.
6. **Use `show_spinner`** for user-visible cached operations: `@st.cache_data(show_spinner="Loading data...")`.
7. **Exclude unhashable parameters** by prefixing with underscore: `def func(_connection, query)`.
8. **Don't cache Plotly figures** with `@st.cache_data` if your code mutates them after creation. Instead, use RING-5's existing custom figure cache which is mutation-aware.

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

Fragments are RING-5's **primary performance optimization**. They allow a section of the UI to rerun independently without triggering a full page rerun.

#### Current Usage (12 fragments)

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

| Use Fragment | Don't Use Fragment |
|---|---|
| Independent UI sections (tabs, panels) | Simple pages with few widgets |
| Sections with expensive computations | When all widgets affect all outputs |
| Streaming/auto-refreshing components | When you need return values |
| Dynamic forms that shouldn't rerun the whole page | When caching is sufficient |

#### Fragment Pitfalls

1. **Return values are ignored** during fragment reruns. Use `st.session_state` to share data.
2. **Widgets can't be placed in containers created outside the fragment.** All widgets must be in the fragment's main body.
3. **Don't combine `@st.fragment` with `@st.cache_data`** on the same function.
4. **Elements drawn to external containers accumulate** across fragment reruns. Use `st.empty()` to prevent this.

### Lazy Imports

RING-5 already implements lazy page imports in `app.py` — each page module is imported only when the user navigates to it. **Continue this pattern for all new pages.**

```python
# ✅ CORRECT — Lazy import
if page == "Manage Plots":
    from src.web.pages.manage_plots import render
    render(api)

# ❌ WRONG — Top-level import (loaded even if page is never visited)
from src.web.pages.manage_plots import render
```

### Minimizing `st.rerun()`

RING-5 currently has ~55 `st.rerun()` calls. Each `st.rerun()` forces a full script re-execution. **Minimize `st.rerun()` usage:**

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

# ✅ For multi-step operations (currently unused in RING-5 but recommended)
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

| Function | Purpose | When to Use | Duration |
|---|---|---|---|
| `st.info()` | Instructional guidance | Explain features, suggest next steps | Persistent |
| `st.success()` | Operation confirmation | After successful parse/export/save | Persistent (consider `st.toast` for transient) |
| `st.warning()` | Soft warning | Missing optional data, suboptimal config | Persistent |
| `st.error()` | Critical error | Parse failure, missing required data, exceptions | Persistent |
| `st.toast()` | Transient notification | Quick confirmations that don't need to persist | Auto-dismiss (~4s) |
| `st.exception()` | Debug traceback | **Development/debug mode only** — never in production | Persistent |

### Rules

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

# ✅ RECOMMENDED — Use st.toast for transient success (currently underused in RING-5)
st.toast("✓ Plot saved successfully", icon="✅")
# Instead of persistent:
st.success("✓ Plot saved successfully")  # This stays on screen until next rerun
```

### Validation Pattern

```python
# ✅ CORRECT — Early return on validation failure
def render_plot_config(data: pd.DataFrame, plot_id: str) -> None:
    if data.empty:
        st.warning("No data available. Load data first.")
        return

    numeric_cols = data.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        st.error("No numeric columns found in the dataset.")
        return

    # Proceed with valid data...
    selected_col = st.selectbox("Column", numeric_cols, key=f"col_{plot_id}")
```

---

## 8. Architecture & Code Organization

### MVP Pattern (Manage Plots)

The **Manage Plots** page implements a clean **Model-View-Presenter (MVP)** architecture. This is the reference architecture for new page implementations.

```
Controller (Business Logic)     → No st.* imports
    ↕ uses protocols
Presenter (Rendering)           → Only st.* calls, no domain logic
    ↕ adapters (dependency injection)
Models & Protocols              → Pure Python data classes and Protocol definitions
```

#### Key Principles

1. **Controllers never import Streamlit.** They orchestrate domain logic and return data models.
2. **Presenters never import domain code directly.** They receive data through protocol-compatible adapters.
3. **Dependency injection** via protocol adapters (`src/web/pages/plot_adapters.py`) decouples controllers from concrete implementations.
4. **UIStateManager** is the only module allowed to touch `st.session_state` in new architectures.

```python
# ✅ CORRECT — Controller (no Streamlit)
class RenderController:
    def __init__(self, service: PlotServiceProtocol) -> None:
        self._service = service

    def generate_figure(self, config: PlotConfig, data: pd.DataFrame) -> go.Figure:
        return self._service.create(config, data)

# ✅ CORRECT — Presenter (only Streamlit rendering)
class ChartPresenter:
    def render_chart(self, figure: go.Figure, plot_id: str) -> None:
        st.plotly_chart(figure, use_container_width=True, key=f"chart_{plot_id}")

# ✅ CORRECT — Wiring in the page file
def render(api: ApplicationAPI) -> None:
    adapter = PlotAdapter(api)
    controller = RenderController(service=adapter)
    presenter = ChartPresenter()
    figure = controller.generate_figure(config, data)
    presenter.render_chart(figure, plot_id)
```

### Legacy Component Pattern (Data Managers)

Older pages use a **component-based pattern** where UI and logic are partially mixed. When modifying these pages, **refactor toward MVP** when practical, but don't force a rewrite for small changes.

### File Organization Rules

| Layer | Directory | Allowed Imports |
|---|---|---|
| **Pages** | `src/web/pages/` | Controllers, presenters, adapters, `UIStateManager` |
| **Controllers** | `src/web/controllers/` | Domain models, protocols, core services — **no `st.*`** |
| **Presenters** | `src/web/presenters/` | `streamlit`, models — **no domain services** |
| **UI Components** | `src/web/pages/ui/` | `streamlit`, utility functions |
| **State** | `src/web/state/` | `streamlit.session_state` |
| **Models** | `src/web/models/` | Standard library, typing — **no `st.*`** |
| **Domain/Core** | `src/core/` | **NEVER import streamlit** |

### The `ApplicationAPI` Singleton

The `ApplicationAPI` instance is created once via `@st.cache_resource` in `app.py` and passed down through the call chain. **Never create a second instance.**

```python
# app.py — The only place ApplicationAPI is instantiated
@st.cache_resource
def get_api() -> ApplicationAPI:
    return ApplicationAPI()

api = get_api()
```

---

## 9. Testing Streamlit Code

### Testing Strategy

RING-5 uses `pytest` for all testing. Streamlit UI code presents unique testing challenges because of the execution model.

#### What to Test and How

| Layer | Test Approach | Tools |
|---|---|---|
| **Domain/Core logic** | Standard unit tests — no Streamlit dependency | `pytest`, mocks |
| **Controllers** | Unit tests with mocked protocol adapters | `pytest`, `unittest.mock` |
| **Presenters** | Integration tests with `AppTest` (if needed) | `streamlit.testing.v1.AppTest` |
| **State management** | Unit tests mocking `st.session_state` | `pytest`, mock dict |
| **Full page flows** | Streamlit's `AppTest` framework | `streamlit.testing.v1.AppTest` |

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

For unit testing components that use `UIStateManager`:

```python
from unittest.mock import patch, MagicMock

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
4. **Test controllers with protocol mocks**, not real domain services.
5. **Don't test Streamlit widgets themselves** — test the logic that feeds them.

---

## 10. RING-5 Current State & Migration Path

### Audit Summary

| Area | Current State | Target State | Priority |
|---|---|---|---|
| **Session State centralization** | 11 files bypass `UIStateManager` | All state through `UIStateManager` | Medium |
| **Widget keys** | ~95% coverage, ~20 widgets missing keys | 100% coverage | High |
| **Caching** | 1 `@st.cache_resource`, 0 `@st.cache_data` | Cache expensive computations | Medium |
| **`st.rerun()` usage** | ~55 calls | Reduce by 50%+ | Low |
| **Fragment coverage** | 12 fragments | Evaluate adding more | Low |
| **Navigation** | Manual `st.radio` dispatch | Consider `st.navigation` (Streamlit 1.36+) | Low |
| **`st.toast` usage** | 2 calls | Use for transient success messages | Low |
| **Presenter key coverage** | Some presenters lack widget keys | All presenter widgets keyed | High |

### Migration Guidelines

#### Phase 1: Quick Wins (Do Now)
- Add `key=` to all widgets missing keys (especially in presenters).
- Replace `st.session_state.attr = val` with `st.session_state["attr"] = val` (1 instance in `app.py`).
- Use `st.toast()` for transient success messages instead of `st.success()` where appropriate.

#### Phase 2: State Consolidation (Next Sprint)
- Migrate remaining 11 direct `st.session_state` files to use `UIStateManager`.
- Remove legacy key naming (`show_save_for_plot_{id}` → `plot.{id}.show_save_dialog`).
- Add `@st.cache_data` to expensive DataFrame computations in shaper pipeline.

#### Phase 3: Architecture Alignment (Future)
- Refactor Data Manager pages toward MVP pattern.
- Evaluate `st.navigation` / `st.Page` for multipage app (requires Streamlit 1.36+).
- Audit and reduce `st.rerun()` calls by restructuring control flow.
- Add `st.status` for multi-step operations (parsing, exporting).

### Checklist for New Features

Before submitting any new RING-5 feature involving Streamlit UI:

- [ ] All widgets have explicit `key=` parameters
- [ ] All session state access goes through `UIStateManager`
- [ ] No direct `st.session_state` in new component files
- [ ] Expensive computations are cached (`@st.cache_data`)
- [ ] Independent UI sections are wrapped in `@st.fragment`
- [ ] Batch inputs use `st.form` where appropriate
- [ ] Error messages are actionable and user-friendly
- [ ] No Streamlit imports in domain/core layer
- [ ] Controllers have no `st.*` imports
- [ ] Progress indicators shown for operations > 500ms
- [ ] Type hints on all functions (mandatory per project rules)
- [ ] Tests written (unit for logic, `AppTest` for UI flows if needed)

---

## Quick Reference Card

```
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
│  UI section independent from the rest of the page?       │
│    → @st.fragment                                        │
│                                                          │
│  Multiple inputs that collectively trigger one action?   │
│    → st.form                                             │
│                                                          │
│  Need a value update before the UI re-renders?           │
│    → on_change / on_click callback                       │
│                                                          │
│  Long operation (>500ms)?                                │
│    → st.spinner / st.progress / st.status                │
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
└──────────────────────────────────────────────────────────┘
```

---

*Last updated: 2025. Based on Streamlit 1.53.1 and official documentation at [docs.streamlit.io](https://docs.streamlit.io/).*
