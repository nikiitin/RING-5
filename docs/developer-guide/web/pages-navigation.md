---
title: "Web Pages and Navigation"
parent: Web Layer
grand_parent: Developer Guide
nav_order: 1
---

# Web Pages and Navigation

This guide describes the five pages of the RING-5 Unified Engine v2 web
application, how sidebar navigation works, how each page composes its UI from
components, and how session state flows between pages.

## Overview

The application is a single-entry Streamlit app (`app.py`) that presents five
logical pages through a custom sidebar navigation system. It does **not** use
Streamlit's native `st.navigation` / `st.Page` multi-page API. Instead, the
active page name is stored in `st.session_state["_nav_page"]` and only the
active page module is imported on each rerun (lazy loading).

The five pages form a linear analysis workflow:

| Page                | Module                             | Entry Point                        |
|---------------------|------------------------------------|------------------------------------|
| Data Source         | `src/web/pages/data_source.py`     | `DataSourcePage(api).render()`     |
| Data Managers       | `src/web/pages/data_managers.py`   | `show_data_managers_page(api)`     |
| Manage Plots        | `src/web/pages/manage_plots.py`    | `show_manage_plots_page(api)`      |
| Save/Load Portfolio | `src/web/pages/portfolio.py`       | `show_portfolio_page(api)`         |
| Documentation       | `src/web/pages/documentation.py`   | `show_documentation_page()`        |

All pages share a wide layout (`layout="wide"`) and an expanded sidebar
(`initial_sidebar_state="expanded"`). A cached `ApplicationAPI` instance,
created once via `@st.cache_resource`, is injected into every page except
Documentation.

## Navigation System

### Sidebar Buttons

Navigation is rendered entirely inside `st.sidebar` within `app.py`. Each page
is represented by an `st.button`:

```python
_NAV_OPTIONS = [
    "Data Source",
    "Data Managers",
    "Manage Plots",
    "Save/Load Portfolio",
    "Documentation",
]

for _nav_item in _NAV_OPTIONS:
    _is_active = st.session_state["_nav_page"] == _nav_item
    if st.button(
        _nav_item,
        key=f"nav_{_nav_item}",
        use_container_width=True,
        type="primary" if _is_active else "tertiary",
    ):
        st.session_state["_nav_page"] = _nav_item
        st.rerun()
```

The active page button receives `type="primary"` (visually highlighted); all
others use `type="tertiary"`. Clicking a button writes the new page name into
`st.session_state["_nav_page"]` and triggers `st.rerun()`.

Below the navigation buttons two utility buttons appear:

- **Clear Data** (`type="tertiary"`) -- calls `api.reset_session()` and reruns.
- **Reset All** (`type="secondary"`) -- also calls `api.reset_session()` and reruns.

### Lazy Page Dispatch

After the sidebar is rendered, `app.py` dispatches to the active page through
conditional imports:

```python
if page == "Data Source":
    from src.web.pages.data_source import DataSourcePage
    DataSourcePage(api).render()
elif page == "Data Managers":
    from src.web.pages.data_managers import show_data_managers_page
    show_data_managers_page(api)
elif page == "Manage Plots":
    from src.web.pages.manage_plots import show_manage_plots_page
    show_manage_plots_page(api)
elif page == "Save/Load Portfolio":
    from src.web.pages.portfolio import show_portfolio_page
    show_portfolio_page(api)
elif page == "Documentation":
    from src.web.pages.documentation import show_documentation_page
    show_documentation_page()
```

Only the active page module is imported on any given rerun. This avoids loading
UI and plotting modules in multiprocessing workers and reduces rerun latency.

### Global Data Preview

Before page dispatch, a fragment-wrapped data preview shows summary metrics
(row count, column count, source filename) when data is loaded. Because it is
wrapped with `@st.fragment`, interacting with its widgets only reruns the
preview itself, not the full page.

## Data Source Page

**File:** `src/web/pages/data_source.py`

**Purpose:** Ingest simulation data into the application. This is the starting
point of every analysis workflow.

### Components and Workflow

The page is implemented as a `DataSourcePage` class that receives the
`ApplicationAPI` and delegates rendering to `DataSourceComponents`. A segmented
control (`st.segmented_control`) lets the user choose one of three ingestion
methods:

1. **Parse Stats** (default) -- Parse raw simulator output files (e.g., gem5
   `stats.txt`). The parser configuration section is wrapped in an
   `@st.fragment` and includes simulator selection (pills), file path inputs,
   parsing strategy selector, a variable editor, scan and parse buttons.
   Two `@st.dialog` decorators provide modal UIs for adding variables and
   showing parse progress.

2. **Load from Recent** -- Browse a list of previously parsed CSV files with
   Load, Preview, and Delete actions. Delegates to
   `DataSourceComponents.render_csv_pool()`.

3. **I already have CSV data** -- Switches the parser flag off and shows a
   confirmation message.

### Key State Interactions

The page reads parser-related state (simulator, paths, pattern, strategy,
variables, CSV pool) via `api.state_manager` getters. On successful parse or
load, it writes loaded data via `api.state_manager.set_data()` and records the
CSV path and pool entries.

### Services Called

`ApplicationAPI.available_simulators()`, `api.submit_scan_async()`,
`api.finalize_scan()`, `api.submit_parse_async()`, `api.finalize_parsing()`,
`api.load_csv_file()`, `api.add_to_csv_pool()`, `api.load_csv_pool()`,
`api.delete_from_csv_pool()`.

## Data Managers Page

**File:** `src/web/pages/data_managers.py`

**Purpose:** Clean and transform loaded data through four specialized managers,
with summary and visualization tabs for inspection.

### The Seven Tabs

The page uses `st.tabs` to present seven tabs, six of which are individually
wrapped with `@st.fragment` so that interactions within one tab only rerun that
tab:

| Tab                | Fragment | Component / Manager                        | Purpose                          |
|--------------------|----------|--------------------------------------------|----------------------------------|
| Summary            | Yes      | `DataManagerComponents.render_summary_tab` | Data shape, types, statistics    |
| Data Visualization | Yes      | `DataManagerComponents.render_visualization_tab` | Interactive data exploration |
| Seeds Reducer      | Yes      | `SeedsReducerManager(api).render()`        | Aggregate over seeds             |
| Outlier Remover    | Yes      | `OutlierRemoverManager(api).render()`      | Remove statistical outliers      |
| Preprocessor       | Yes      | `PreprocessorManager(api).render()`        | Derive/rename columns            |
| Mixer              | Yes      | `MixerManager(api).render()`              | Merge/mix datasets               |
| Operations History | No       | `HistoryComponents.render_portfolio_history` | View operation log             |

### The Four Managers

Each transformation manager follows a shared pattern: it receives the `api`,
reads the current data, renders configuration widgets, applies the
transformation through `api.managers.*`, and writes the result back via
`api.state_manager.set_data()`. Manager-specific UI state is namespaced using
`WidgetKeyBuilder.manager_key(...)`.

### Prerequisites

The page requires loaded data. If none is present it shows a warning directing
the user to the Data Source page and returns early.

## Manage Plots Page

**File:** `src/web/pages/manage_plots.py`

**Purpose:** Create, configure, and render plots with independent per-plot
shaper pipelines.

### Architecture

The page is a thin composition layer that wires three controllers with
dependency-injected adapters:

```
show_manage_plots_page(api)
    |
    +-- PlotCreationController(api, ui_state, lifecycle, registry)
    +-- PipelineController(api, ui_state, pipeline_executor)
    +-- PlotRenderController(api, ui_state, lifecycle, registry)
```

Three adapter classes bridge old static methods to protocol contracts:

- `PlotLifecycleAdapter` -- wraps `PlotService` (create, delete, duplicate, change type).
- `PlotTypeRegistryAdapter` -- wraps `PlotFactory.get_available_plot_types()`.
- `PipelineExecutorAdapter` -- wraps `apply_shapers()` and `configure_shaper()`.

Controllers receive these adapters through their constructors and never import
concrete plotting classes directly.

### Plot Lifecycle

1. **Create** -- The user provides a name and selects a plot type from a
   selectbox. `PlotCreationController.render_create_section()` calls
   `PlotService.create_plot()` through the lifecycle adapter.
2. **Select** -- A selectbox lets the user switch between existing plots.
3. **Control** -- Rename, delete, and duplicate buttons operate on the selected
   plot.

### Pipeline and Visualization Fragments

The page uses `st.fragment(fn)(args)` (the programmatic form) to isolate two
sections:

- **Pipeline fragment** (`_pipeline_fragment`) -- Renders the shaper pipeline
  editor. Users add transformation steps (column selector, condition selector,
  normalize, mean, split-apply, transformer, sort, pivot longer/wider),
  configure each step, preview intermediate results, and finalize the pipeline.
  The finalized data is stored in `plot.processed_data`.

- **Render fragment** (`_render_fragment`) -- Renders the visualization section.
  This includes the plot type selector, type-specific configuration UI, a
  settings pills navigation for styling (layout, typography, legends, axes,
  data labels, colors, advanced), engine selection (Plotly or Matplotlib),
  chart display, and a download section for exporting figures.

### Prerequisites

Data must be loaded, and the pipeline must be finalized before the
visualization section can render a chart.

## Portfolio Page

**File:** `src/web/pages/portfolio.py`

**Purpose:** Save and restore complete analysis snapshots (data, plots, all
configurations) as portfolio files.

### Layout

The page is split into three sections, all wrapped in a single
`st.fragment(_portfolio_fragment)(api)`:

1. **Save Portfolio** (left column) -- A text input for the portfolio name and a
   save button. On save, the current data, plots, config, plot counter, CSV
   path, and parse variables are gathered from `api.state_manager` and passed
   to `api.data_services.save_portfolio()`.

2. **Load Portfolio** (right column) -- A selectbox listing saved portfolios and
   a load button. Loading calls `api.data_services.load_portfolio()` followed
   by `api.state_manager.restore_session()`. After restoring state, the page
   calls `st.rerun(scope="app")` to force a full application rerun so that
   all pages reflect the restored session.

3. **Manage Saved Portfolios** -- An expander per saved portfolio with a delete
   button that calls `api.data_services.delete_portfolio()`.

### Fragment Isolation

The entire portfolio UI is wrapped in a single fragment. Text input changes,
selectbox selections, and button clicks only rerun the fragment, not the full
app. The exception is the load action, which explicitly uses
`st.rerun(scope="app")` to propagate the restored state globally.

## Documentation Page

**File:** `src/web/pages/documentation.py`

**Purpose:** Serve as an in-app documentation hub that links to external
Markdown guide files.

The page renders link cards organized into three sections using two-column
grids:

- **WebApp Guide** -- Quick Start, Data Source, Manage Plots, First Analysis,
  Data Managers, Plot Settings, Downloads, and Portfolios.
- **API Reference** -- Backend Facade, Plotting API, Parsing API, Shaper API.
- **Developer Guides** -- Architecture, Testing Guide, Development Setup,
  Adding Plot Types.

Each card is rendered by `_link_card()`, which checks whether the target
Markdown file exists on disk and appends "(coming soon)" if it does not. The
page reads no state and calls no services.

## Page Composition Pattern

Every page follows a consistent composition pattern:

1. **Receive `api`** -- The `ApplicationAPI` instance is passed as a function
   argument (or constructor parameter for `DataSourcePage`).
2. **Check prerequisites** -- Pages that require data (Data Managers, Manage
   Plots) verify `api.state_manager.has_data()` and show a warning if missing.
3. **Delegate to components** -- Pages do not render widgets directly. They
   compose pre-built component classes and manager objects (e.g.,
   `DataSourceComponents`, `SeedsReducerManager`, `PlotCreationController`).
4. **Wrap in fragments** -- Independent UI sections are wrapped with
   `@st.fragment` (decorator form for zero-argument locals) or
   `st.fragment(fn)(args)` (programmatic form when arguments are needed) to
   isolate reruns.
5. **Use adapters for decoupling** -- The Manage Plots page injects adapter
   instances so that controllers depend on protocols, not concrete classes.

## Session State Flow Across Pages

Session state in RING-5 is divided into two categories managed by distinct
systems:

### Domain State (RepositoryStateManager)

Persistent analytical data owned by `api.state_manager`. This is the data that
flows between pages:

| State              | Written By      | Read By                                   |
|--------------------|-----------------|-------------------------------------------|
| Raw data           | Data Source      | Data Managers, Manage Plots, Portfolio    |
| Plots list         | Manage Plots     | Manage Plots, Portfolio                   |
| Current plot ID    | Manage Plots     | Manage Plots                              |
| Plot counter       | Manage Plots     | Manage Plots, Portfolio                   |
| CSV path           | Data Source      | Data Source, Portfolio                     |
| Parser config      | Data Source      | Data Source                               |
| Parse variables    | Data Source      | Data Source, Portfolio                     |
| CSV pool           | Data Source      | Data Source                               |
| Config             | Multiple         | Portfolio                                 |

### Transient UI State (UIStateManager)

Ephemeral widget state owned by `UIStateManager` (`src/web/state/ui_state_manager.py`).
Keys are namespaced to prevent collisions:

- `plot.{id}.*` -- Per-plot auto-refresh, dialog visibility, ordering, shape editing.
- `manager.{name}.*` -- Per-manager load triggers and form field values.
- `nav.*` -- Current page and tab (available but not the primary navigation mechanism).
- `export.*` -- Last export path.

`WidgetKeyBuilder` centralizes key construction. Scoped cleanup methods
(`ui_state.plot.cleanup(id)`, `ui_state.manager.cleanup(name)`) remove all keys
for a deleted entity, preventing state leaks across page transitions.

### Cross-Page Rerun Scopes

- `st.rerun()` inside a fragment reruns only that fragment.
- `st.rerun(scope="app")` forces a full application rerun. This is used by the
  Portfolio page after loading a portfolio to ensure every page picks up the
  restored domain state.

## See Also

- `src/web/pages/plot_adapters.py` -- Adapter classes bridging static services to protocol contracts.
- `src/web/state/ui_state_manager.py` -- Centralized typed UI state management.
- `src/web/controllers/plot/` -- Controller implementations for plot creation, pipeline editing, and rendering.
- `src/web/components/` -- Reusable UI component classes used by all pages.
- `src/core/application_api.py` -- The backend facade injected into every page.
- `app.py` -- Application entry point containing navigation and page dispatch.
