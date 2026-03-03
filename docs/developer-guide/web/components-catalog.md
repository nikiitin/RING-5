# Web Components Catalog

This guide catalogs every reusable UI component in the RING-5 Unified Engine v2
web layer. All components live under `src/web/components/` and are organised
into three packages: `common`, `data_source`, and `data_managers`.

---

## 1. Overview

### Component-Based Architecture (No Presenters)

The web layer follows a **stateless-render** component pattern rather than an
MVP-style presenter architecture. Each component class (or module-level
function):

1. Receives data through parameters -- typically via `ApplicationAPI` or plain
   Python values.
2. Renders Streamlit widgets (`st.button`, `st.selectbox`, etc.).
3. Returns **user-intent signals** (button clicks, selected values) to the
   caller without mutating application state.

```
Controller                   Component
    |                            |
    |--- data, config ---------> |
    |                            |-- st.selectbox, st.button, ...
    |<--- {clicked, value} ----- |
    |                            |
    |--- api.do_thing() -------> |   (controller acts on the signal)
```

All components interact with `ApplicationAPI` exclusively through its public
facade -- never reaching into repositories or services directly.

| Package | Files | Purpose |
|---|---|---|
| `common/` | 10 modules | Shared atoms, chart display, pipeline editor, plot management, filtered selectors, reorderable lists |
| `data_source/` | 3 modules | CSV pool, parser configuration, variable editing |
| `data_managers/` | 6 modules | Preprocessor, seeds reducer, outlier remover, mixer |

---

## 2. Common Components

### 2.1 CardComponents

**Source:** `src/web/components/common/card_components.py`

Two `@staticmethod` methods rendering information cards inside `st.expander`
widgets.

- **`file_info_card(file_info, index)`** -- Returns `(load_clicked,
  preview_clicked, delete_clicked)`. Shows name, size, and modified timestamp.
  First card is auto-expanded. Button keys: `load_{index}`, `preview_{index}`,
  `delete_{index}`.
- **`config_info_card(config_info, index)`** -- Returns `(load_clicked,
  delete_clicked)`. Button keys: `load_cfg_{index}`, `delete_cfg_{index}`.

### 2.2 DataComponents

**Source:** `src/web/components/common/data_components.py`

| Method | Description |
|---|---|
| `show_data_preview(data, title, rows)` | `data.head(rows)` with 4-column metric row (Rows, Columns, Numeric, Categorical). |
| `show_column_details(data)` | Expander with Column, Type, Non-Null, Null, Unique summary. |
| `download_buttons(data, prefix)` | CSV, JSON, and Excel download buttons in a 3-column row. |

### 2.3 HistoryComponents

**Source:** `src/web/components/common/history_components.py`

- **`render_history_table(records, *, title)`** -- DataFrame table in reverse
  chronological order.
- **`render_global_history(all_records, delete_callback, *, key_prefix)`** --
  Last 10 operations with delete buttons (key: `hist_{key_prefix}_del_{i}`).
- **`render_manager_history(all_records, operation_prefix, load_session_key,
  delete_callback)`** -- Filters by prefix, renders Load and Delete buttons per
  record. Load stores the record in `st.session_state[load_session_key]` for the
  history load pattern (see section 9.3).
- **`render_portfolio_history(records)`** -- Full history page with total
  operations metric.

### 2.4 LayoutComponents

**Source:** `src/web/components/common/layout_components.py`

| Method | Returns | Description |
|---|---|---|
| `sidebar_info()` | `None` | App description in sidebar. |
| `navigation_menu()` | `str` | Radio with 5 pages: Data Source, Data Managers, Configure Pipeline, Generate Plots, Load Configuration. |
| `progress_display(step, total, msg)` | `None` | Progress bar with status text. |
| `add_variable_button()` | `bool` | "+ Add Variable" button. |
| `clear_data_button()` | `bool` | "Clear All Data" button. |

---

## 3. Chart Display

**Source:** `src/web/components/common/chart_display.py`

`ChartDisplayComponent` is the central rendering wrapper for the chart area,
handling dual-engine output (Plotly and Matplotlib), refresh logic, and
download wiring. All methods are `@staticmethod`.

**`render_refresh_controls(plot_id, auto_refresh, config_changed)`** -- Returns
`dict` with `auto_refresh`, `manual_refresh`, `should_generate`. Toggle key:
`auto_t_{plot_id}`; button key: `refresh_{plot_id}`. Generation triggers on
manual click or auto-refresh with changed config.

**`render_engine_selector(plot_id, current_engine)`** -- `st.pills` with Plotly
and LaTeX (Matplotlib) options using Material icons. Key:
`engine_selector_{plot_id}`.

**`render_plotly_chart(fig, plot_id, plot_name, config)`** -- Configures the
interactive chart with editable legend positioning, drawing tools (line, path,
circle, rect, eraser), and SVG export. Delegates to
`interactive_plotly_chart()` and returns `relayout_data`. Renders download
section afterward.

**`render_matplotlib_chart(plotly_fig, plot_id, plot_name, config, plot_type,
traces)`** -- Converts a Plotly figure into Matplotlib through a pipeline:

1. Closes previous figure from `st.session_state[plot.{plot_id}.mpl_fig]` to
   prevent memory leaks.
2. Builds and resolves a `FigureSpec` via `ConfigSpecBuilder`.
3. Detects multi-heatmap cases (>1 `HeatmapTraceConfig`) and delegates to
   `_render_multi_heatmap()` with shared or per-trace colour ranges.
4. For standard plots: creates figure, renders traces via
   `MatplotlibTraceRenderer`, applies styling, displays with `st.pyplot`.

---

## 4. Pipeline Components

### 4.1 PipelineComponent

**Source:** `src/web/components/common/pipeline.py`

Renders the shaper pipeline editor UI. Does **not** modify pipeline state or
apply shapers -- that is the controller's job.

Class attributes `SHAPER_DISPLAY_MAP` and `REVERSE_MAP` are sourced from
`ShaperFactory.get_display_name_map()`.

| Method | Returns | Description |
|---|---|---|
| `render_section_header()` | `None` | Pipeline heading. |
| `render_no_data_warning()` | `None` | Warning when no data is loaded. |
| `render_add_shaper(plot_id)` | `dict` (`add_clicked`, `shaper_type`) | Selectbox + "Add to Pipeline" button (3:1 layout). Fallback: `"columnSelector"`. |
| `render_shaper_controls(plot_id, idx, ...)` | `dict` (`move_up`, `move_down`, `delete`) | Up/Down/Del buttons. Up hidden when first; Down hidden when last. |
| `render_finalize_button(plot_id)` | `bool` | Primary "Finalize Pipeline for Plotting" button. |

### 4.2 PipelineStepComponent

**Source:** `src/web/components/common/pipeline_step.py`

Renders a single shaper step inside an `st.expander`. Two-column layout (3:1):
left calls `configure_fn()` for shaper-specific config widgets; right calls
`PipelineComponent.render_shaper_controls()`. If config is non-empty, calls
`apply_fn()` for a live preview.

Returns `PipelineStepResult` (a `TypedDict`) with `new_config`, `move_up`,
`move_down`, `delete`, `preview_data`, `preview_error`, and `step_output`.

---

## 5. Plot Components

### 5.1 PlotCreationComponent

**Source:** `src/web/components/common/plot_creation.py`

Renders a "Create New Plot" form using `st.form` to batch inputs (keystrokes do
not trigger reruns). Returns `dict` with `name`, `plot_type`,
`create_clicked`. Layout: 3-column row (2:1:1).

### 5.2 PlotSelectorComponent

**Source:** `src/web/components/common/plot_selector.py`

Horizontal `st.pills` selector for available plots. Returns the selected plot
name, falling back to the first. Key: `plot_selector`. Also provides
`render_no_plots_warning()`.

### 5.3 PlotControlsComponent

**Source:** `src/web/components/common/plot_controls.py`

Rename, delete, and duplicate controls in a 3-column row. Returns `dict` with
`new_name`, `delete_clicked`, `duplicate_clicked`. Keys: `rename_{plot_id}`,
`delete_plot_{plot_id}`, `dup_plot_{plot_id}`.

---

## 6. Interactive Components

### 6.1 Filtered Selector

**Source:** `src/web/components/common/filtered_selector.py`

Two module-level functions wrapping Streamlit widgets with server-side text
filtering for large option lists.

| Constant | Value | Purpose |
|---|---|---|
| `SELECTBOX_THRESHOLD` | 200 | Below this, standard `st.selectbox` is used |
| `MULTISELECT_THRESHOLD` | 100 | Below this, standard `st.multiselect` is used |
| `MAX_DISPLAYED` | 50 | Maximum options sent to the browser |

**`filtered_selectbox(label, options, *, key, help, placeholder)`** -- Below
threshold: standard selectbox with empty sentinel. Above threshold: text input
for case-insensitive substring filtering, truncated to `MAX_DISPLAYED`.
Session state: `{key}__search`.

**`filtered_multiselect(label, options, *, key, default, help)`** -- Below
threshold: standard multiselect. Above threshold: persistent selection set in
`{key}__selections` that survives filter changes; pre-sets widget value to
intersection of persistent and visible selections; provides "Select all
matching" and "Clear all" bulk actions; returns in original option order.
Session state: `{key}__selections`, `{key}__search`.

### 6.2 Reorderable List

**Source:** `src/web/components/common/reorderable_list.py`

```python
render_reorderable_list(label, items, key_prefix, plot_id,
                        legend_labels=None, default_order=None,
                        enable_rename=False, rename_map=None)
```

Renders a list with up/down arrow buttons for reordering. Stores order in
`st.session_state[{key_prefix}_order_{plot_id}]` via `resolve_item_order()`.
Automatically syncs when the item set changes. Each row: label (or editable
text input), up button, down button. When `enable_rename=True`, returns
`(order, renames)` instead of just the order list.

---

## 7. Data Source Components

### 7.1 DataSourceComponents

**Source:** `src/web/components/data_source/data_source_components.py`

The largest single component class, orchestrating the entire Data Source page.

- **`render_csv_pool(api)`** -- Iterates the CSV pool, renders
  `CardComponents.file_info_card()` per entry, handles Load/Preview/Delete.
- **`render_parser_config(api)`** -- Simulator selector, parser config
  fragment (wrapped in `@st.fragment` for isolated reruns), stats path, file
  pattern, parsing strategy, scanner UI, variable editor, and parse button
  (outside the fragment for full-page rerun).
- **`variable_config_dialog(api)`** -- `@st.dialog("Add Variable")` with
  "Search Scanned Variables" and "Manual Entry" modes. Validates inputs,
  assigns UUIDs, appends to the parse variables list.

### 7.2 VariableEditor

**Source:** `src/web/components/data_source/variable_editor.py`

Renders parser variable configurations. Per variable: common fields (Name,
Alias, Type, Delete) then type-specific dispatch:

| Type | Renderer | Key Features |
|---|---|---|
| vector | `render_vector_config` | Parse mode, statistics checkboxes, entry mode (discovered/manual), deep scan |
| distribution | `render_distribution_config` | Parse mode, statistics, bucket range inputs, deep scan |
| histogram | `render_histogram_config` | Parse mode, rebin, target bins, entry mode |
| configuration | `render_configuration_config` | Default-on-empty text input |

Deep scans use `api.submit_scan_async()` with results in a blocking
`@st.dialog("Deep Scan")` with real-time progress.

### 7.3 PatternIndexSelector

**Source:** `src/web/components/data_source/pattern_index_selector.py`

Thin UI wrapper around `PatternIndexService`. Validates pattern variables,
extracts positional indices, renders per-position `filtered_multiselect`
widgets. All pure logic delegated to the service layer.

---

## 8. Data Manager Components

### 8.1 DataManager ABC

**Source:** `src/web/components/data_managers/data_manager.py`

```python
class DataManager(ABC):
    def __init__(self, api: ApplicationAPI):
        self.api = api

    @property
    @abstractmethod
    def name(self) -> str: ...       # displayed as the tab label

    @abstractmethod
    def render(self) -> None: ...    # all Streamlit widget calls

    def get_data(self) -> pd.DataFrame | None:
        return self.api.state_manager.get_data()

    def set_data(self, data: pd.DataFrame) -> None:
        self.api.state_manager.set_data(data)
```

Every manager declares a `name` property (tab label), implements `render()`,
and inherits `get_data()`/`set_data()` helpers.

### 8.2 Concrete Managers

All four managers follow the **preview-confirm-history** workflow (section 9.2).
Widget keys use `mgr_{prefix}_{suffix}` via `WidgetKeyBuilder.manager_key()`.

| Manager | Name | Preview Key | Purpose |
|---|---|---|---|
| `PreprocessorManager` | "Preprocessor (Basic)" | `"preprocessor"` | Combines two numeric columns with arithmetic (divide, sum, subtract, multiply). Default names like `{src1}_per_{src2}`. |
| `SeedsReducerManager` | "Seeds Reducer" | `"seeds_reduction"` | Aggregates across random seeds: mean and stdev for numeric columns grouped by categorical. Defaults target to `random_seed`. |
| `OutlierRemoverManager` | "Outlier Remover" | `"outlier_removal"` | Removes rows exceeding Q3, grouped by categorical columns. Excludes seed-like columns from group-by defaults. |
| `MixerManager` | "Mixer (Merge Columns)" | `"mixer"` | Merges columns via Sum, Mean, or Concatenation. Two modes: Numerical Operations and Configuration Merge. Propagates `.sd`/`_stdev` errors. |

### 8.3 DataManagerComponents (Page Helpers)

**Source:** `src/web/components/data_managers/data_manager_components.py`

- **`render_summary_tab(data)`** -- 4-column metric row (Rows, Columns, Memory,
  Missing Values), preview, column details, describe(), categorical summaries.
- **`render_visualization_tab(data)`** -- Search/filter, column selection,
  pagination (20/50/100/500/All), CSV download.

---

## 9. Component Interaction Patterns

### 9.1 Stateless Render Pattern

Every component is a pure renderer returning signals. The caller owns all side
effects. Three exceptions manage `st.session_state` directly:

- `render_reorderable_list` -- ordering persistence.
- `filtered_multiselect` -- selection persistence across filter changes.
- `HistoryComponents.render_manager_history` -- load triggers via `on_click`.

### 9.2 Preview-Confirm Workflow

All data managers follow a two-step workflow preventing accidental mutations:

```
Configure widgets -> "Preview" click
  -> validate via api.managers.validate_*()
  -> execute via api.managers.*()
  -> show preview, store in PreviewRepository

"Confirm" click (visible only when preview exists)
  -> retrieve from PreviewRepository
  -> commit via self.set_data()
  -> clear preview, record OperationRecord
  -> st.rerun()
```

### 9.3 History Load Pattern

1. `render_manager_history()` stores the `OperationRecord` in session state via
   `on_click`.
2. Manager calls `UIStateManager().manager.consume_load_trigger(name)` to read
   and clear the trigger.
3. Manager pre-populates widget keys from the record, validating column
   existence.
4. Streamlit renders the pre-filled widgets on the same rerun.

### 9.4 Fragment Isolation and Dialogs

`render_parser_config` wraps its body in `@st.fragment` so that text input
keystrokes only rerun that fragment. The parse button sits outside the fragment
for a full-page rerun.

Two dialog patterns: non-blocking (`@st.dialog("Add Variable")`, returns via
`st.rerun()`) and blocking progress (`@st.dialog("Parsing Stats")` /
`@st.dialog("Deep Scan")`, iterates `as_completed()` with `st.progress`).

### 9.5 Component Composition Tree

```
DataSourcePage
  +-- DataSourceComponents.render_csv_pool(api)
  |     +-- CardComponents.file_info_card
  |     +-- DataComponents.show_data_preview
  +-- DataSourceComponents.render_parser_config(api)
        +-- VariableEditor.render -> type-specific renderers
        |     +-- filtered_multiselect / filtered_selectbox
        |     +-- PatternIndexSelector.render_selector
        +-- variable_config_dialog (dialog)

DataManagersPage
  +-- DataManagerComponents.render_summary_tab / render_visualization_tab
  +-- PreprocessorManager / SeedsReducerManager / OutlierRemoverManager / MixerManager
  |     +-- HistoryComponents.render_manager_history
  +-- HistoryComponents.render_global_history

PipelinePage
  +-- PipelineComponent.render_add_shaper
  +-- PipelineStepComponent.render_step (per step)
  +-- PipelineComponent.render_finalize_button

PlotPage
  +-- PlotCreationComponent / PlotSelectorComponent / PlotControlsComponent
  +-- ChartDisplayComponent (refresh, engine selector, chart render)
```

---

## 10. See Also

- [Architecture Overview](../architecture/overview.md) -- how components fit
  into the layered architecture.
- [State Management](../core/state-management.md) -- `ApplicationAPI` and
  `StateManager` coordination with components.
- [Plotting System](../visualization/plotting-system.md) -- trace configs and
  the rendering pipeline behind `ChartDisplayComponent`.
- [Pipeline and Shapers](../core/pipeline-shapers.md) -- `ShaperFactory` and
  `ShaperStepConfig` driving `PipelineComponent`.
- [Controllers](controllers.md) -- the controller layer that invokes components
  and acts on their return signals.
