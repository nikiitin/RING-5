# Step 08 -- Web Pages & Navigation Flow Analysis

> **Objective**: Document every Streamlit page, its purpose, UI components,
> state access, and navigation flow.

---

## 1. Executive Summary

The RING-5 Unified Engine v2 web application is a single-page Streamlit app (`app.py`)
that implements custom sidebar navigation to switch between five logical "pages."
It does **not** use Streamlit's native `st.navigation` / `st.Page` multi-page API.
Instead, it stores the active page name in `st.session_state["_nav_page"]` and
uses conditional imports to lazy-load only the active page module on each rerun.

The five top-level pages form a linear workflow:

1. **Data Source** -- ingest simulation data (parse gem5 stats, upload CSV, load recent)
2. **Data Managers** -- clean and transform data (seeds reduction, outlier removal, preprocessing, mixing)
3. **Manage Plots** -- create plots, build per-plot shaper pipelines, configure and render visualizations
4. **Save/Load Portfolio** -- persist and restore complete analysis sessions
5. **Documentation** -- in-app documentation hub linking to external Markdown guides

The application enforces `layout="wide"` and `initial_sidebar_state="expanded"` globally.
A global `ApplicationAPI` instance is cached via `@st.cache_resource` and injected
into every page. Fragment isolation (`@st.fragment` or `st.fragment(fn)`) is used
extensively on the Data Managers, Manage Plots, and Portfolio pages to minimize
unnecessary reruns. Two `@st.dialog` decorators are used on the Data Source page
for variable addition and parse-progress dialogs, plus one in the Variable Editor
for deep scanning.

---

## 2. Page Inventory

| # | Page Name           | File                                  | Nav Key              | Entry Function / Class            | Purpose                                      |
|---|---------------------|---------------------------------------|----------------------|-----------------------------------|----------------------------------------------|
| 1 | Data Source          | `src/web/pages/data_source.py`        | `"Data Source"`      | `DataSourcePage(api).render()`    | Ingest data: parse stats, upload CSV, recent |
| 2 | Data Managers        | `src/web/pages/data_managers.py`      | `"Data Managers"`    | `show_data_managers_page(api)`    | Transform data: reduce, filter, preprocess   |
| 3 | Manage Plots         | `src/web/pages/manage_plots.py`       | `"Manage Plots"`     | `show_manage_plots_page(api)`     | Create, configure, and render plots          |
| 4 | Save/Load Portfolio  | `src/web/pages/portfolio.py`          | `"Save/Load Portfolio"` | `show_portfolio_page(api)`     | Save/load complete analysis snapshots        |
| 5 | Documentation        | `src/web/pages/documentation.py`      | `"Documentation"`    | `show_documentation_page()`       | In-app documentation hub                     |

**Supporting module (not a page):**

| Module               | File                                    | Purpose                                                |
|----------------------|-----------------------------------------|--------------------------------------------------------|
| Plot Adapters        | `src/web/pages/plot_adapters.py`        | Bridge old static methods to protocol contracts        |
| Shaper Config        | `src/web/pages/ui/shaper_config.py`     | Orchestrate shaper configuration UI + apply shapers    |

---

## 3. Navigation Architecture

### 3.1 How `app.py` Configures the Application

```
app.py:run_app()
```

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/app.py`

1. **Page config**: `st.set_page_config(page_title="RING-5 Interactive Analyzer", page_icon="R5", layout="wide", initial_sidebar_state="expanded")`
2. **Custom CSS**: Injects a gradient header style via `st.markdown(..., unsafe_allow_html=True)`
3. **API initialization**: `ApplicationAPI` is created once via `@st.cache_resource` with `BasePlot.from_dict` as the plot deserializer, then stored in `st.session_state.api`
4. **Sidebar navigation**: Custom button-based navigation (see below)
5. **Global data preview**: A `@st.fragment`-wrapped function shows row/column/source metrics when data is loaded
6. **Lazy page dispatch**: Conditional imports load only the active page module
7. **Performance logging**: Logs slow reruns (> 0.5s) via `ring5.perf` logger

### 3.2 Sidebar Navigation Implementation

The navigation does **not** use `st.navigation` or `st.Page`. Instead:

```python
# Session state key for current page
st.session_state["_nav_page"]  # default: "Data Source"

# Navigation options (ordered)
_NAV_OPTIONS = [
    "Data Source",
    "Data Managers",
    "Manage Plots",
    "Save/Load Portfolio",
    "Documentation",
]
```

Each option is rendered as an `st.button` inside `st.sidebar`:
- Active page gets `type="primary"` (highlighted)
- Inactive pages get `type="tertiary"`
- Clicking a button sets `st.session_state["_nav_page"]` and calls `st.rerun()`

Below the navigation buttons, two additional sidebar buttons:
- **Clear Data** (`type="tertiary"`): Calls `api.reset_session()` and reruns
- **Reset All** (`type="secondary"`): Calls `api.reset_session()` and reruns

### 3.3 Page Dispatch (Lazy Imports)

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

Key design: Only the active page's module is imported on each rerun. This avoids
loading UI/plotting modules for workers (multiprocessing) and reduces rerun latency.

### 3.4 Global Data Preview Fragment

Before page dispatch, `app.py` renders a data preview fragment:

```python
@st.fragment
def _data_preview_fragment():
    current_view = api.get_current_view()
    if current_view["raw_data"] is not None and not current_view["raw_data"].empty:
        col1, col2, col3 = st.columns(3)
        # Metrics: Rows, Columns, Source filename
```

This fragment is isolated -- its widgets only rerun itself, not the full page.

---

## 4. Page Detail Catalog

### 4.1 Data Source Page

- **File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/web/pages/data_source.py`
- **Class**: `DataSourcePage`
- **Entry**: `DataSourcePage(api).render()`
- **Purpose**: Select and configure data ingestion method

#### Layout

```
## Step 1: Choose Data Source
[Info box with three methods]
[Segmented control: Parse Stats | I already have CSV data | Load from Recent]

(conditional content based on selection)
```

#### UI Components

| Component                  | Streamlit Widget      | Key                     |
|----------------------------|-----------------------|-------------------------|
| Data source selector       | `st.segmented_control`| `"data_source_choice"`  |
| Info box                   | `st.info`             | --                      |

#### Conditional Sections

1. **Parse Stats** (default): Delegates to `DataSourceComponents.render_parser_config(api)`
   - Sets `state_manager.set_use_parser(True)`
   - Renders simulator selector (pills), file path inputs, strategy selector, variable editor, scan button, parse button
   - Contains `@st.fragment` for parser config section
   - Contains `@st.dialog("Add Variable")` for variable addition
   - Contains `@st.dialog("Parsing Stats")` for parse progress

2. **Load from Recent**: Delegates to `DataSourceComponents.render_csv_pool(api)`
   - Shows list of recent CSV files with Load/Preview/Delete actions

3. **I already have CSV data**: Shows success message, sets `use_parser(False)`

#### State Read

| Key / Method                          | Source                     |
|---------------------------------------|----------------------------|
| `api.state_manager.get_simulator()`   | RepositoryStateManager     |
| `api.state_manager.is_using_parser()` | RepositoryStateManager     |
| `api.state_manager.get_stats_path()`  | RepositoryStateManager     |
| `api.state_manager.get_stats_pattern()`| RepositoryStateManager    |
| `api.state_manager.get_parser_strategy()` | RepositoryStateManager |
| `api.state_manager.get_parse_variables()` | RepositoryStateManager |
| `api.state_manager.get_scanned_variables()` | RepositoryStateManager |
| `api.state_manager.get_csv_pool()`    | RepositoryStateManager     |

#### State Written

| Key / Method                               | Trigger               |
|--------------------------------------------|-----------------------|
| `api.state_manager.set_use_parser(bool)`   | Segmented control     |
| `api.state_manager.set_simulator(str)`     | Simulator pills       |
| `api.state_manager.set_stats_path(str)`    | Text input            |
| `api.state_manager.set_stats_pattern(str)` | Text input            |
| `api.state_manager.set_parser_strategy()`  | Strategy selector     |
| `api.state_manager.set_scanned_variables()`| After scan            |
| `api.state_manager.set_parse_variables()`  | Variable editor       |
| `api.state_manager.set_data(df)`           | After parse/load      |
| `api.state_manager.set_csv_path(str)`      | After parse/load      |
| `api.state_manager.set_csv_pool(list)`     | Pool load             |

#### Services Called

| Service Method                | When                        |
|-------------------------------|-----------------------------|
| `ApplicationAPI.available_simulators()` | On render            |
| `ApplicationAPI.get_simulator_info()`   | On render            |
| `api.submit_scan_async()`     | Quick scan button           |
| `api.finalize_scan()`         | After scan futures complete |
| `api.submit_parse_async()`    | Parse button                |
| `api.finalize_parsing()`      | After parse futures         |
| `api.add_to_csv_pool()`       | After successful parse      |
| `api.load_csv_file()`         | Load from pool or parse     |
| `api.load_csv_pool()`         | On pool section render      |
| `api.delete_from_csv_pool()`  | Delete button               |

#### Fragments

| Fragment                         | Scope                          |
|----------------------------------|--------------------------------|
| `_parser_config_fragment`        | Entire parser configuration section (file inputs, strategy, variables, scan) |

#### Dialogs

| Dialog                          | Trigger                        | Purpose                        |
|---------------------------------|--------------------------------|--------------------------------|
| `variable_config_dialog`        | "Add Variable" button          | Add variable manually or from scan |
| `_show_parse_dialog`            | "Parse Stats" button           | Show parsing progress with futures |
| `deep_scan_dialog` (VariableEditor) | Deep scan button in editor | Run deep scan for a single variable |

#### Prerequisites

None (this is the entry point of the workflow).

---

### 4.2 Data Managers Page

- **File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/web/pages/data_managers.py`
- **Function**: `show_data_managers_page(api)`
- **Purpose**: Visualize and configure data transformations

#### Layout

```
## Data Managers & Transformations
[Info box]
[7 tabs: Summary | Data Visualization | Seeds Reducer | Outlier Remover | Preprocessor | Mixer | Operations History]
```

#### UI Components

| Component          | Streamlit Widget | Content                          |
|--------------------|------------------|----------------------------------|
| Info box           | `st.info`        | Description of capabilities      |
| Tab container      | `st.tabs`        | 7 tabs for different operations  |

#### Tab Details

| Tab                 | Fragment?     | Component / Manager                    | Purpose                            |
|---------------------|---------------|----------------------------------------|------------------------------------|
| Summary             | `@st.fragment`| `DataManagerComponents.render_summary_tab(data)` | Data shape, types, statistics |
| Data Visualization  | `@st.fragment`| `DataManagerComponents.render_visualization_tab(data)` | Interactive data exploration |
| Seeds Reducer       | `@st.fragment`| `SeedsReducerManager(api).render()`    | Reduce data by seed aggregation    |
| Outlier Remover     | `@st.fragment`| `OutlierRemoverManager(api).render()`  | Remove statistical outliers        |
| Preprocessor        | `@st.fragment`| `PreprocessorManager(api).render()`    | Column operations (derive, rename) |
| Mixer               | `@st.fragment`| `MixerManager(api).render()`           | Merge/mix datasets                 |
| Operations History  | None          | `HistoryComponents.render_portfolio_history(...)` | View operation log      |

#### State Read

| Key / Method                       | Source                     |
|------------------------------------|----------------------------|
| `api.state_manager.has_data()`     | RepositoryStateManager     |
| `api.state_manager.get_data()`     | RepositoryStateManager     |
| `api.get_portfolio_history()`      | ApplicationAPI             |

#### State Written

Each sub-manager (SeedsReducer, OutlierRemover, Preprocessor, Mixer) writes:
- `api.state_manager.set_data(transformed_df)` -- after applying transformation
- Manager-specific UI state via `WidgetKeyBuilder.manager_key(...)` in session_state

#### Services Called

| Service                          | Tab                 |
|----------------------------------|---------------------|
| `api.managers.reduce_seeds()`    | Seeds Reducer       |
| `api.managers.remove_outliers()` | Outlier Remover     |
| `api.managers.preprocess()`      | Preprocessor        |
| `api.managers.mix()`             | Mixer               |

#### Fragments

All six content tabs (Summary, Data Visualization, Seeds Reducer, Outlier Remover,
Preprocessor, Mixer) are individually wrapped with `@st.fragment`. This means
interacting with widgets inside one tab only reruns that tab's fragment, not the
entire page. The Operations History tab is not fragmented.

#### Prerequisites

Data must be loaded via the Data Source page. If no data exists, the page shows
a warning: "No data loaded. Please load data from the Data Source page."

---

### 4.3 Manage Plots Page

- **File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/web/pages/manage_plots.py`
- **Function**: `show_manage_plots_page(api)`
- **Purpose**: Create, configure, and render plots with independent pipelines
- **Architecture**: Controller/Component/Adapter pattern with dependency injection

#### Layout

```
## Manage Plots
[Create New Plot section]
[Plot Selector (selectbox)]
[Plot Controls: rename, delete, duplicate]
---
[Pipeline Editor (fragmented)]
[Visualization (fragmented)]
```

#### Architecture

The page is a thin composition layer that wires three controllers:

1. **PlotCreationController** -- plot lifecycle (create, select, rename, delete, duplicate)
2. **PipelineController** -- shaper pipeline editing per plot
3. **PlotRenderController** -- config gathering, figure generation, chart display

Three adapter classes bridge old static methods to protocol contracts:
- `PlotLifecycleAdapter` -- wraps `PlotService` static methods
- `PlotTypeRegistryAdapter` -- wraps `PlotFactory.get_available_plot_types()`
- `PipelineExecutorAdapter` -- wraps `apply_shapers()` and `configure_shaper()`

#### UI Components

| Component              | Widget / Controller                  | Key                        |
|------------------------|--------------------------------------|----------------------------|
| Create section         | `PlotCreationComponent.render()`     | `new_plot_name`, `plot_type_select` |
| Plot selector          | `PlotSelectorComponent.render()`     | `plot_selector`            |
| Controls (rename/del)  | `PlotControlsComponent.render()`     | `rename_{id}`, `del_{id}` |
| Pipeline editor        | `PipelineController.render()`        | Various per-step keys      |
| Plot type selector     | `st.selectbox`                       | `plot_type_sel_{id}`       |
| Config UI              | `plot.render_config_ui(data, config)`| Per-plot-type keys         |
| Settings pills         | `render_settings_pills()`            | `settings_nav`             |
| Settings sections      | `plot.render_settings_section()`     | Section-specific keys      |
| Advanced toggle        | `st.toggle`                          | `show_advanced_{id}`       |
| Auto-refresh           | `st.toggle`                          | `auto_t_{id}`              |
| Refresh button         | `st.button`                          | `refresh_{id}`             |
| Engine selector        | `st.pills`                           | `engine_selector_{id}`     |
| Plotly chart           | `interactive_plotly_chart()`         | `chart_{id}`               |
| Download section       | `render_download_section()`          | `dl_fmt_{id}`, `dl_btn_{id}` |

#### State Read

| Key / Method                              | Source                     |
|-------------------------------------------|----------------------------|
| `api.state_manager.get_plots()`           | RepositoryStateManager     |
| `api.state_manager.get_current_plot_id()` | RepositoryStateManager     |
| `api.state_manager.get_plot_counter()`    | RepositoryStateManager     |
| `api.state_manager.get_data()`            | RepositoryStateManager     |
| `ui_state.plot.consume_pending_updates()` | UIStateManager             |
| `ui_state.plot.get_auto_refresh(id)`      | UIStateManager             |
| `EngineManager.get_engine()`              | session_state              |
| `plot.config`                             | BasePlot instance          |
| `plot.processed_data`                     | BasePlot instance          |
| `plot.pipeline`                           | BasePlot instance          |

#### State Written

| Key / Method                              | Trigger                    |
|-------------------------------------------|----------------------------|
| `api.state_manager.set_current_plot_id()` | Plot selection change      |
| `api.state_manager.add_plot()`            | Create plot                |
| `api.state_manager.set_plots()`           | Delete/type change         |
| `plot.config = current_config`            | Config update              |
| `plot.processed_data = df`                | Pipeline finalization      |
| `plot.pipeline.append(...)`               | Add shaper step            |
| `ui_state.plot.set_auto_refresh()`        | Toggle widget              |
| `ui_state.plot.cleanup(id)`               | Delete plot                |
| `EngineManager.set_engine()`              | Engine selector pills      |
| `st.session_state[last_event_key]`        | Relayout event             |
| `st.session_state[mpl_state_key]`         | Matplotlib figure cache    |

#### Services Called

| Service / Adapter                    | When                          |
|--------------------------------------|-------------------------------|
| `PlotService.create_plot()`          | Create button                 |
| `PlotService.delete_plot()`          | Delete button                 |
| `PlotService.duplicate_plot()`       | Duplicate button              |
| `PlotService.change_plot_type()`     | Type selector change          |
| `PlotFactory.get_available_plot_types()` | Render create + type sel  |
| `apply_shapers(data, configs)`       | Finalize pipeline             |
| `configure_shaper(type, data, ...)`  | Each pipeline step render     |
| `plot.create_figure(data, config)`   | Figure generation             |
| `plot.apply_common_layout(fig, cfg)` | After figure creation         |
| `get_plot_cache()`                   | Figure caching                |

#### Fragments

| Fragment                   | Scope                                   |
|----------------------------|-----------------------------------------|
| `_pipeline_fragment`       | Pipeline editor (add/remove/reorder shapers, configure, preview, finalize) |
| `_render_fragment`         | Visualization section (plot type selector, config UI, settings pills, chart display, download) |

Both are created via `st.fragment(fn)(controller, plot)` -- the programmatic API
rather than the decorator form. This allows passing arguments.

#### Prerequisites

- Data must be loaded (checked in `PipelineController`; shows warning if missing)
- Pipeline must be finalized before visualization (checked in `PlotRenderController`; shows "No processed data available")

---

### 4.4 Save/Load Portfolio Page

- **File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/web/pages/portfolio.py`
- **Function**: `show_portfolio_page(api)`
- **Purpose**: Save and restore complete analysis snapshots

#### Layout

```
## Portfolio Management
---
[Two columns: Save Portfolio | Load Portfolio]
---
### Manage Saved Portfolios
[Expanders for each saved portfolio with Delete button]
```

#### UI Components

| Component                 | Widget                 | Key                          |
|---------------------------|------------------------|------------------------------|
| Portfolio name input      | `st.text_input`        | `"portfolio_save_name"`      |
| Save button               | `st.button`            | --                           |
| Portfolio selector        | `st.selectbox`         | `"portfolio_load_select"`    |
| Load button               | `st.button`            | --                           |
| Delete portfolio buttons  | `st.button` per item   | `"del_portfolio_{name}"`     |
| Portfolio expanders       | `st.expander` per item | --                           |

#### State Read

| Key / Method                            | Source                     |
|-----------------------------------------|----------------------------|
| `api.state_manager.get_data()`          | RepositoryStateManager     |
| `api.state_manager.get_plots()`         | RepositoryStateManager     |
| `api.state_manager.get_config()`        | RepositoryStateManager     |
| `api.state_manager.get_plot_counter()`  | RepositoryStateManager     |
| `api.state_manager.get_csv_path()`      | RepositoryStateManager     |
| `api.state_manager.get_parse_variables()` | RepositoryStateManager   |

#### State Written

| Key / Method                              | Trigger              |
|-------------------------------------------|----------------------|
| `api.state_manager.restore_session(data)` | Load portfolio       |

#### Services Called

| Service Method                        | When                 |
|---------------------------------------|----------------------|
| `api.data_services.save_portfolio()`  | Save button          |
| `api.data_services.load_portfolio()`  | Load button          |
| `api.data_services.list_portfolios()` | On render            |
| `api.data_services.delete_portfolio()`| Delete button        |
| `ConfigSpecBuilder.from_config()`     | Figure spec builder  |

#### Fragments

The entire content (save, load, and manage sections) is wrapped in a single
`st.fragment(_portfolio_fragment)(api)`. This isolates portfolio operations from
the global page -- text input, button clicks, and selectbox changes only rerun
the fragment, not the full app. The Load button uses `st.rerun(scope="app")` to
force a full app rerun after restoring session state.

#### Prerequisites

None strictly required, but meaningful use requires loaded data and plots.

---

### 4.5 Documentation Page

- **File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/web/pages/documentation.py`
- **Function**: `show_documentation_page()`
- **Purpose**: Hub linking to external documentation files

#### Layout

```
## Documentation
---
### WebApp Guide
[2-column grid of link cards]
---
### API Reference
[2-column grid of link cards]
---
### Developer Guides
[2-column grid of link cards]
```

#### UI Components

| Component      | Widget           | Details                     |
|----------------|------------------|-----------------------------|
| Link cards     | `st.markdown`    | Custom `_link_card()` helper |
| Column layouts | `st.columns(2)`  | Two-column grids            |

#### Link Card Categories

**WebApp Guide**: Quick Start, Data Source, Manage Plots, First Analysis, Data Managers, Plot Settings, Export & Download, Portfolios

**API Reference**: Backend Facade, Plotting API, Parsing API, Shaper API

**Developer Guides**: Architecture, Testing Guide, Development Setup, Adding Plot Types

#### State Read/Written

None. This page is purely informational and does not interact with state.

#### Services Called

None. Checks `Path.exists()` for documentation files to show "(coming soon)" status.

#### Fragments / Dialogs

None.

#### Prerequisites

None.

---

## 5. Fragment & Dialog Boundaries

### 5.1 Fragment Inventory

| Page           | Fragment Name                | Form          | Isolation Scope                            |
|----------------|------------------------------|---------------|--------------------------------------------|
| `app.py`       | `_data_preview_fragment`     | `@st.fragment`| Global data metrics (rows, columns, source)|
| Data Managers  | `_summary_fragment`          | `@st.fragment`| Summary tab content                        |
| Data Managers  | `_visualization_fragment`    | `@st.fragment`| Data visualization tab content             |
| Data Managers  | `_seeds_fragment`            | `@st.fragment`| Seeds reducer tab content                  |
| Data Managers  | `_outlier_fragment`          | `@st.fragment`| Outlier remover tab content                |
| Data Managers  | `_preproc_fragment`          | `@st.fragment`| Preprocessor tab content                   |
| Data Managers  | `_mixer_fragment`            | `@st.fragment`| Mixer tab content                          |
| Data Source    | `_parser_config_fragment`    | `@st.fragment`| Parser file inputs, strategy, variables, scan |
| Manage Plots   | `_pipeline_fragment`         | `st.fragment()`| Pipeline editor for current plot          |
| Manage Plots   | `_render_fragment`           | `st.fragment()`| Visualization section for current plot    |
| Portfolio      | `_portfolio_fragment`        | `st.fragment()`| Entire save/load/manage UI                |

**Total: 11 fragments across 4 files.**

### 5.2 Fragment Patterns

Two patterns are used:

1. **Decorator form** (`@st.fragment`): Used when the fragment is a zero-argument
   local function defined immediately above its invocation. Common in `data_managers.py`
   and `data_source_components.py`.

2. **Programmatic form** (`st.fragment(fn)(args...)`): Used in `manage_plots.py`
   and `portfolio.py` when arguments need to be passed to the fragment function.

### 5.3 Dialog Inventory

| Page / Component               | Dialog Name                | Decorator                                  | Trigger                    | Purpose                            |
|---------------------------------|----------------------------|--------------------------------------------|-----------------------------|--------------------------------------|
| Data Source Components          | `variable_config_dialog`   | `@st.dialog("Add Variable")`               | "Add Variable" button       | Add variable from scan or manually  |
| Data Source Components          | `_show_parse_dialog`       | `@st.dialog("Parsing Stats", dismissible=True)` | "Parse Stats" button   | Show parse progress with futures    |
| Variable Editor                 | `deep_scan_dialog`         | `@st.dialog("Deep Scan", dismissible=True)` | Deep scan button in editor | Run deep scan for one variable      |

**Total: 3 dialogs, all on the Data Source page.**

### 5.4 Rerun Scope Behavior

- `st.rerun()` (default): Reruns only the enclosing fragment when called inside
  a fragment; reruns the full app when called outside.
- `st.rerun(scope="app")`: Forces a full app rerun even from within a fragment.
  Used in `portfolio.py` after loading a portfolio to ensure all pages reflect
  the restored state.

---

## 6. Page -> Service Call Map

```
Data Source Page
  |-- ApplicationAPI.available_simulators()
  |-- ApplicationAPI.get_simulator_info()
  |-- api.submit_scan_async()
  |-- api.finalize_scan()
  |-- api.submit_parse_async()
  |-- api.finalize_parsing()
  |-- api.add_to_csv_pool()
  |-- api.load_csv_file()
  |-- api.load_csv_pool()
  |-- api.delete_from_csv_pool()
  |-- api.data_services.has_variable_with_name()
  \-- ApplicationAPI.cancel_pending_scans()

Data Managers Page
  |-- api.state_manager.has_data()
  |-- api.state_manager.get_data()
  |-- api.get_portfolio_history()
  |-- SeedsReducerManager(api).render()  -> api.managers.*
  |-- OutlierRemoverManager(api).render() -> api.managers.*
  |-- PreprocessorManager(api).render()   -> api.managers.*
  \-- MixerManager(api).render()          -> api.managers.*

Manage Plots Page
  |-- PlotService.create_plot()    (via PlotLifecycleAdapter)
  |-- PlotService.delete_plot()    (via PlotLifecycleAdapter)
  |-- PlotService.duplicate_plot() (via PlotLifecycleAdapter)
  |-- PlotService.change_plot_type() (via PlotLifecycleAdapter)
  |-- PlotFactory.get_available_plot_types() (via PlotTypeRegistryAdapter)
  |-- apply_shapers()              (via PipelineExecutorAdapter)
  |-- configure_shaper()           (via PipelineExecutorAdapter)
  |-- plot.create_figure()
  |-- plot.apply_common_layout()
  |-- plot.render_config_ui()
  |-- plot.render_settings_section()
  |-- get_plot_cache()
  |-- EngineManager.get_engine() / set_engine()
  |-- FigureSpecToMatplotlib.create_figure() / apply()
  |-- MatplotlibTraceRenderer.render()
  \-- render_download_section()

Portfolio Page
  |-- api.data_services.save_portfolio()
  |-- api.data_services.load_portfolio()
  |-- api.data_services.list_portfolios()
  |-- api.data_services.delete_portfolio()
  |-- api.state_manager.restore_session()
  \-- ConfigSpecBuilder.from_config()

Documentation Page
  \-- (no services -- reads filesystem for doc file existence)
```

---

## 7. Page -> State Access Map

### 7.1 Session State Keys

| Key Pattern                        | Owner                      | Used By                        |
|------------------------------------|----------------------------|--------------------------------|
| `_nav_page`                        | `app.py`                   | Sidebar navigation             |
| `api`                              | `app.py`                   | All pages (ApplicationAPI ref) |
| `data_source_choice`               | Data Source page            | Segmented control              |
| `simulator_selector`               | Data Source components      | Simulator pills                |
| `stats_path_input`                 | Data Source components      | File path text input           |
| `stats_pattern_input`              | Data Source components      | File pattern text input        |
| `parser_strategy_selector`         | Data Source components      | Strategy segmented control     |
| `plot.{id}.auto_refresh`           | UIStateManager._PlotUIState | Auto-refresh toggle            |
| `plot.{id}.dialog.{name}`          | UIStateManager._PlotUIState | Dialog visibility              |
| `plot.{id}.order.{type}`           | UIStateManager._PlotUIState | Custom ordering                |
| `plot.{id}.edit_shapes`            | UIStateManager._PlotUIState | Shape editing mode             |
| `plot.{id}.last_relayout`          | PlotRenderController       | Relayout event dedup           |
| `plot.{id}.mpl_fig`               | ChartDisplayComponent      | Matplotlib figure cache        |
| `plot.pending_updates`             | UIStateManager._PlotUIState | Pending relayout widget updates|
| `manager.{name}.load_trigger`      | UIStateManager._ManagerUIState | History load triggers       |
| `manager.{name}.form.{field}`      | UIStateManager._ManagerUIState | Form field values           |
| `nav.current_page`                 | UIStateManager._NavUIState | (Available but not primary)    |
| `nav.current_tab`                  | UIStateManager._NavUIState | (Available but not primary)    |
| `export.last_path`                 | UIStateManager._ExportUIState | Last export path             |
| `ring5_engine_mode`                | EngineManager              | Active rendering engine        |
| `settings_nav`                     | Settings pills             | Selected settings section      |
| `portfolio_save_name`              | Portfolio page              | Portfolio name input           |
| `portfolio_load_select`            | Portfolio page              | Portfolio selector             |
| `show_advanced_{id}`               | Render controller           | Advanced settings toggle       |
| `plot_type_sel_{id}`               | Render controller           | Plot type selector             |
| `engine_selector_{id}`             | ChartDisplayComponent      | Engine pills                   |
| `chart_{id}`                       | Interactive plot component  | Plotly chart key               |
| `auto_t_{id}`                      | ChartDisplayComponent      | Auto-refresh toggle            |
| `refresh_{id}`                     | ChartDisplayComponent      | Refresh button                 |
| `dl_fmt_{id}`                      | Download section            | Download format pills          |
| `dl_btn_{id}`                      | Download section            | Download button                |
| `preset_selector_{id}`             | Settings pills              | Preset selector                |

### 7.2 Domain State (RepositoryStateManager)

The `RepositoryStateManager` (accessed via `api.state_manager`) owns persistent
domain state stored in `st.session_state` under its own key namespace:

| Domain State             | Accessor Method             | Used By Pages                  |
|--------------------------|-----------------------------|--------------------------------|
| Raw data (DataFrame)     | `get_data()` / `set_data()` | Data Source, Data Managers, Manage Plots, Portfolio |
| Plots list               | `get_plots()` / `set_plots()` | Manage Plots, Portfolio     |
| Current plot ID          | `get_current_plot_id()`     | Manage Plots                   |
| Plot counter             | `get_plot_counter()`        | Manage Plots, Portfolio        |
| CSV path                 | `get_csv_path()`            | Data Source, Portfolio          |
| Parser config fields     | `get_stats_path()`, etc.    | Data Source                    |
| Parse variables          | `get_parse_variables()`     | Data Source, Portfolio          |
| Scanned variables        | `get_scanned_variables()`   | Data Source                    |
| CSV pool                 | `get_csv_pool()`            | Data Source                    |
| Config                   | `get_config()`              | Portfolio                      |
| Simulator                | `get_simulator()`           | Data Source                    |

---

## 8. Navigation Flow Diagram (ASCII)

```
+============================================================================+
|                          app.py (Streamlit Entry)                           |
|                                                                            |
|   st.set_page_config(layout="wide")                                        |
|   api = ApplicationAPI()  <-- @st.cache_resource                           |
|   st.session_state.api = api                                               |
|                                                                            |
|   +--- SIDEBAR --------------------------------------------------------+  |
|   |  RING-5 Logo/Title                                                  |  |
|   |  -----                                                              |  |
|   |  [Data Source]        <-- st.button, primary if active              |  |
|   |  [Data Managers]      <-- st.button, primary if active              |  |
|   |  [Manage Plots]       <-- st.button, primary if active              |  |
|   |  [Save/Load Portfolio]<-- st.button, primary if active              |  |
|   |  [Documentation]      <-- st.button, primary if active              |  |
|   |  -----                                                              |  |
|   |  [Clear Data]         <-- api.reset_session()                       |  |
|   |  [Reset All]          <-- api.reset_session()                       |  |
|   +---------------------------------------------------------------------+  |
|                                                                            |
|   HEADER: "RING-5 Interactive Analyzer"                                    |
|   DATA PREVIEW (fragment): Rows | Columns | Source                         |
|                                                                            |
|   PAGE DISPATCH (lazy imports):                                            |
|     _nav_page == "Data Source"       --> DataSourcePage(api).render()       |
|     _nav_page == "Data Managers"     --> show_data_managers_page(api)       |
|     _nav_page == "Manage Plots"      --> show_manage_plots_page(api)       |
|     _nav_page == "Save/Load Portfolio" -> show_portfolio_page(api)          |
|     _nav_page == "Documentation"     --> show_documentation_page()          |
+============================================================================+
```

### Typical User Journey

```
    +---------------+     +----------------+     +--------------+     +------------------+
    |  Data Source   |---->| Data Managers  |---->| Manage Plots |---->| Save/Load        |
    |               |     |                |     |              |     | Portfolio         |
    | 1. Select sim |     | 1. View summary|     | 1. Create    |     | 1. Save snapshot |
    | 2. Set paths  |     | 2. Reduce seeds|     | 2. Pipeline  |     | 2. Load previous |
    | 3. Scan vars  |     | 3. Remove outl.|     | 3. Finalize  |     | 3. Manage saved  |
    | 4. Add vars   |     | 4. Preprocess  |     | 4. Configure |     +------------------+
    | 5. Parse      |     | 5. Mix         |     | 5. Style     |
    |   OR          |     +----------------+     | 6. Render    |
    | Upload CSV    |            |               | 7. Download  |
    | Load recent   |            |               +--------------+
    +---------------+            |                      |
           |                     |                      |
           v                     v                      v
    [Data loaded in        [Data transformed      [Plots created
     session state]         in session state]       and rendered]
```

### Manage Plots Internal Flow

```
+-- show_manage_plots_page(api) --------------------------------+
|                                                                |
|  UIStateManager().plot.consume_pending_updates()               |
|  Create Adapters: Lifecycle, Registry, PipelineExecutor        |
|  Create Controllers: Creation, Pipeline, Render                |
|                                                                |
|  1. creation.render_create_section()                           |
|     [Name input] [Type selectbox] [Create button]              |
|                                                                |
|  2. creation.render_selector()                                 |
|     [Plot selectbox] --> returns current_plot or None           |
|                                                                |
|  3. creation.render_controls(current_plot)                     |
|     [Rename input] [Delete button] [Duplicate button]          |
|                                                                |
|  --- FRAGMENT: _pipeline_fragment ---                           |
|  4. pipeline.render(current_plot)                              |
|     [Add transformation selector + button]                     |
|     [Pipeline steps: config UI + preview + up/down/delete]     |
|     [Finalize Pipeline button]                                 |
|  --- END FRAGMENT ---                                          |
|                                                                |
|  --- FRAGMENT: _render_fragment ---                             |
|  5. render.render(current_plot)                                |
|     [Plot type selector]                                       |
|     [Type-specific config UI (render_config_ui)]               |
|     [Advanced toggle + Settings Pills]                         |
|     [Settings section content (render_settings_section)]       |
|     [Auto-refresh toggle + Refresh button]                     |
|     [Engine selector pills: Plotly / Matplotlib]               |
|     [Chart display (Plotly interactive or Matplotlib)]          |
|     [Download section (format pills + download button)]        |
|  --- END FRAGMENT ---                                          |
+----------------------------------------------------------------+
```

---

## 9. Plot Type Catalog

### 9.1 Registered Plot Types (PlotFactory)

| Type Key               | Class                    | Category      | Display Name          | Config UI Module                         |
|------------------------|--------------------------|---------------|-----------------------|------------------------------------------|
| `bar`                  | `BarPlot`                | basic         | Bar Chart             | `base_plot_config.render_common_with_color` |
| `line`                 | `LinePlot`               | basic         | Line Chart            | `base_plot_config.render_common_with_color` |
| `scatter`              | `ScatterPlot`            | basic         | Scatter Plot          | `base_plot_config.render_common_with_color` |
| `grouped_bar`          | `GroupedBarPlot`         | comparison    | Grouped Bar           | `grouped_bar_config.render`              |
| `stacked_bar`          | `StackedBarPlot`         | comparison    | Stacked Bar           | `stacked_bar_config.render`              |
| `grouped_stacked_bar`  | `GroupedStackedBarPlot`  | comparison    | Grouped Stacked Bar   | `grouped_stacked_bar_config.render`      |
| `dual_axis_bar_dot`    | `DualAxisBarDotPlot`     | comparison    | Dual Axis Bar Dot     | `dual_axis_config.render`                |
| `heatmap`              | `HeatmapPlot`            | distribution  | Heatmap               | `heatmap_config.render`                  |
| `histogram`            | `HistogramPlot`          | distribution  | Histogram             | `histogram_config.render`                |

### 9.2 Plot Type Files

| Plot Type              | File Path                                                                          |
|------------------------|------------------------------------------------------------------------------------|
| `BarPlot`              | `src/web/pages/ui/plotting/types/bar_plot.py`                                      |
| `LinePlot`             | `src/web/pages/ui/plotting/types/line_plot.py`                                     |
| `ScatterPlot`          | `src/web/pages/ui/plotting/types/scatter_plot.py`                                  |
| `GroupedBarPlot`       | `src/web/pages/ui/plotting/types/grouped_bar_plot.py`                              |
| `StackedBarPlot`       | `src/web/pages/ui/plotting/types/stacked_bar_plot.py`                              |
| `GroupedStackedBarPlot`| `src/web/pages/ui/plotting/types/grouped_stacked_bar_plot.py`                      |
| `DualAxisBarDotPlot`   | `src/web/pages/ui/plotting/types/dual_axis_bar_dot_plot.py`                        |
| `HeatmapPlot`          | `src/web/pages/ui/plotting/types/heatmap_plot.py`                                  |
| `HistogramPlot`        | `src/web/pages/ui/plotting/types/histogram_plot.py`                                |

### 9.3 Plot Inheritance Hierarchy

```
ABC, PlotConfigUIMixin
      |
  BasePlot (abstract)
      |
      +-- BarPlot
      +-- LinePlot
      +-- ScatterPlot
      +-- GroupedBarPlot
      +-- HeatmapPlot
      +-- HistogramPlot
      +-- DualAxisBarDotPlot
      +-- StackedBarPlot
              |
              +-- GroupedStackedBarPlot
```

### 9.4 Config UI per Plot Type

**Basic plots** (bar, line, scatter): Use `render_common_with_color(data, saved_config, plot_id)` which provides X column, Y column, and optional Color (grouping) column selectors.

**Grouped bar**: Uses `grouped_bar_config.render()` with X, Y, Group column, plus X/Group filters.

**Stacked bar**: Uses `stacked_bar_config.render()` with X column and multi-select Y columns for stacking.

**Grouped stacked bar**: Uses `grouped_stacked_bar_config.render()` with X, Group, multi-Y, dual-axis support, numbered X-axis, and extensive layout controls. Supports secondary and tertiary legend levels.

**Dual axis bar dot**: Uses `dual_axis_config.render()` with X, Y-bar (primary), Y-dot (secondary), Color, line/marker settings.

**Heatmap**: Uses `heatmap_config.render()` with X column, metric columns (multi-select), facet column, aggregation function, colorscale, cell value display options, and totals.

**Histogram**: Uses `histogram_config.render()` with histogram variable detection from column naming patterns (`var..bucket_start-bucket_end`), normalization, cumulative mode, group-by.

---

## 10. Settings Pills System

### 10.1 Architecture

**File**: `src/web/pages/ui/plotting/settings_pills.py`

The settings pills provide a pill-based navigation for plot styling sections.
Sections are split into **basic** (always visible) and **advanced** (hidden behind
a toggle).

### 10.2 Sections

| Key           | Label        | Icon            | Advanced? | Component                      |
|---------------|-------------|-----------------|-----------|--------------------------------|
| `layout`      | Layout       | `dashboard`     | No        | `LayoutSettingsComponent`      |
| `typography`   | Typography   | `text_fields`   | No        | `TypographySettingsComponent`  |
| `legends`     | Legends      | `legend_toggle` | No        | `LegendSettingsComponent`      |
| `axes`        | Axes         | `straighten`    | Yes       | `AxesSettingsComponent`        |
| `data_labels` | Data Labels  | `label`         | Yes       | `DataLabelsSettingsComponent`  |
| `colors`      | Colors       | `palette`       | Yes       | `ColorsSettingsComponent`      |
| `advanced`    | Advanced     | `settings`      | Yes       | `AdvancedSettingsComponent`    |

### 10.3 Preset System

**File**: `src/web/pages/ui/plotting/export/presets/preset_manager.py`

A `render_preset_pills(plot_id)` function renders preset selector pills above the
settings navigation. Presets are loaded from `latex_presets.json` and provide
complete LaTeX-compatible export configurations (font sizes, dimensions, legend
spacing, etc.) for journal-specific requirements.

### 10.4 Dispatch Flow

```python
# In PlotRenderController.render():
show_adv = st.toggle("Show advanced settings", ...)
selected_section = render_settings_pills(show_advanced=show_adv)
extra_config = plot.render_settings_section(selected_section, current_config, data)
```

`render_settings_section()` is defined in `PlotConfigUIMixin` and dispatches to
the appropriate settings component based on the selected pill key.

---

## 11. Style System

### 11.1 Style UI Factory

**File**: `src/web/pages/ui/plotting/styles/factory.py`

```python
class StyleUIFactory:
    @staticmethod
    def get_strategy(plot_id, plot_type) -> BaseStyleUI:
        if plot_type == "dual_axis_bar_dot":  -> BaseStyleUI
        elif "line" in plot_type:              -> LineStyleUI
        elif "scatter" in plot_type:           -> ScatterStyleUI
        elif "bar" in plot_type:               -> BarStyleUI
        else:                                  -> BaseStyleUI
```

### 11.2 Style Application

**File**: `src/web/pages/ui/plotting/styles/applicator.py`

`StyleApplicator.apply_styles(fig, config)` applies common Plotly layout settings
(margins, backgrounds, font sizes, grid colors, axis formatting, legend positioning)
to a figure based on the config dictionary.

### 11.3 Rendering Engines

**File**: `src/web/rendering/engine_manager.py`

Two rendering engines are supported:
- **Plotly** (default): Interactive charts with zoom, pan, hover, legend drag
- **Matplotlib**: Publication-quality output with LaTeX font support, PGF export

Engine selection is per-session via `st.pills` in the chart display component.
The engine state is stored in `st.session_state["ring5_engine_mode"]`.

---

## 12. Shaper Pipeline System

### 12.1 Available Shapers

The shaper pipeline (used in both Data Managers and per-plot pipelines) supports:

| Shaper Type        | UI Config Module                    | Purpose                                   |
|--------------------|-------------------------------------|-------------------------------------------|
| `columnSelector`   | `ColumnSelectorConfig`              | Select/filter columns                     |
| `conditionSelector`| `ConditionSelectorConfig`           | Filter rows by condition                  |
| `normalize`        | `NormalizeConfig`                   | Normalize values to baseline              |
| `mean`             | `MeanConfig`                        | Aggregate by mean                         |
| `splitApply`       | `SplitApplyConfig`                  | Split-apply-combine operations            |
| `transformer`      | `TransformerConfig`                 | Mathematical column transformations       |
| `sort`             | `SortConfig`                        | Sort by columns                           |
| `pivotLonger`      | `PivotLongerConfig`                 | Wide to long format                       |
| `pivotWider`       | `PivotWiderConfig`                  | Long to wide format                       |

### 12.2 Pipeline Flow

```
Raw Data --> [Shaper 1] --> [Shaper 2] --> ... --> [Shaper N] --> Processed Data
                                                                       |
                                                                 plot.processed_data
                                                                       |
                                                              create_figure(data, config)
```

Configuration is via `configure_shaper()` in `src/web/pages/ui/shaper_config.py`
which dispatches to the appropriate config component. Application is via
`apply_shapers()` which uses `ShaperFactory.create_shaper()` from the core layer.

---

## 13. Component Architecture Summary

### 13.1 Directory Structure

```
src/web/
  pages/                          # Top-level page modules
    data_source.py                # DataSourcePage class
    data_managers.py              # show_data_managers_page()
    manage_plots.py               # show_manage_plots_page()
    portfolio.py                  # show_portfolio_page()
    documentation.py              # show_documentation_page()
    plot_adapters.py              # Protocol adapters for controllers
    ui/
      shaper_config.py            # Shaper configuration orchestrator
      plotting/
        base_plot.py              # BasePlot (ABC) + PlotConfigUIMixin
        plot_factory.py           # PlotFactory (registry)
        plot_renderer.py          # Cache key utilities
        plot_service.py           # PlotService (lifecycle)
        plot_config_ui.py         # PlotConfigUIMixin (settings dispatch)
        download_section.py       # Download helpers (Plotly + Matplotlib)
        settings_pills.py         # Pills navigation for settings
        types/                    # Plot type implementations
        styles/                   # Style UI strategies + applicator
        export/presets/           # LaTeX preset manager
        utils/                    # Grouped bar coordinate utilities
  controllers/
    plot/
      creation_controller.py      # Plot lifecycle orchestration
      pipeline_controller.py      # Pipeline editing orchestration
      render_controller.py        # Config + generation + display
  components/
    common/                       # Shared UI components
      chart_display.py            # Chart rendering (Plotly/Matplotlib)
      pipeline.py                 # Pipeline editor UI
      pipeline_step.py            # Individual pipeline step UI
      plot_creation.py            # Plot creation form
      plot_selector.py            # Plot selection dropdown
      plot_controls.py            # Rename/delete/duplicate controls
      reorderable_list.py         # Reorderable list widget
      filtered_selector.py        # Searchable selectbox/multiselect
      history_components.py       # Operations history display
      card_components.py          # File info cards
      data_components.py          # Data preview/details
      layout_components.py        # Layout helpers
    data_source/                  # Data source UI components
      data_source_components.py   # Parser config, CSV pool, dialogs
      variable_editor.py          # Variable CRUD editor
      pattern_index_selector.py   # Pattern-based index selection
    data_managers/                # Data manager UI components
      data_manager_components.py  # Summary/visualization tabs
      seeds_reducer.py            # Seeds reducer manager
      outlier_remover.py          # Outlier remover manager
      preprocessor.py             # Preprocessor manager
      mixer.py                    # Data mixer manager
      data_manager.py             # Base data manager
    shapers/                      # Shaper configuration UIs
      mean_config.py              # Mean shaper config
      normalize_config.py         # Normalize shaper config
      pivot_config.py             # Pivot wider/longer configs
      selector_transformer_configs.py # Column/condition selectors
      sort_config.py              # Sort shaper config
      split_apply_config.py       # Split-apply config
    plotting/                     # Plotting-specific components
      interactive_plot.py         # Interactive Plotly chart wrapper
      config/                     # Plot type config UIs
      settings/                   # Settings section components
  state/
    ui_state_manager.py           # Centralized UI state management
  rendering/
    engine_manager.py             # Plotly/Matplotlib engine selection
    config_builder.py             # FigureConfig construction
    matplotlib_connector.py       # Matplotlib rendering pipeline
    trace_to_plotly.py            # Trace -> Plotly conversion
```

---

## 14. Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` -> `web/pages-and-navigation.md`
- `USER_GUIDE_PLAN.md` -> `webapp/web-interface-overview.md` and all webapp pages
- Step 12 (settings pills) -- needs page context for settings
- Step 18 (data flow) -- needs to know how pages trigger data flow
