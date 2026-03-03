# Step 13 -- Controllers & Web-Layer Patterns Analysis

> **Objective**: Document the controller layer, adapter pattern, web-layer models,
> protocols, and all architectural patterns used in the presentation layer to organize
> business logic orchestration.

---

## 1. Executive Summary

The RING-5 Unified Engine v2 web layer implements a **Page-Controller-Component (PCC)**
architecture with protocol-based dependency injection and an adapter bridge to legacy
static-method services. Three plot controllers (`PlotCreationController`,
`PipelineController`, `PlotRenderController`) orchestrate the full plot lifecycle on the
**Manage Plots** page. A separate `DataManager` ABC hierarchy handles data transformation
operations on the **Data Managers** page.

Key architectural properties:

| Property | Decision |
|----------|----------|
| Controller lifecycle | **Per-page-render** -- instantiated fresh on every Streamlit rerun |
| Statefulness | **Stateless** -- all persistent state lives in `ApplicationAPI.state_manager` (domain) or `UIStateManager` (transient UI) |
| Dependency injection | **Constructor injection** via Python `Protocol` contracts |
| Service access | Via **Adapter pattern** -- three adapters wrap static/class-method services into instance-method objects satisfying protocol contracts |
| Component role | **Passive** -- render Streamlit widgets, return typed dicts of user actions; no state mutation, no reruns |
| Streamlit usage in controllers | Intentional for `st.rerun()` (flow control), `st.exception()` (tracebacks), `st.toast()` (feedback), and `st.warning()` (guards) |
| Presenter layer | **Deleted** -- formerly `config_presenter.py`, `controls_presenter.py`, `pipeline_presenter.py`; replaced by Component classes |

The controllers sit at **Layer 2** in the documented architecture stack:

```
  Page (Layer 1) -- thin wiring, adapter creation, fragment setup
    |
  Controller (Layer 2) -- orchestration, state reads, action dispatch   <-- THIS ANALYSIS
    |
  Component (Layer 3) -- widget rendering, returns user selections
    |
  UIStateManager (Layer 4) -- typed session_state access
    |
  Models / Protocols (Layer 5) -- pure data definitions, contracts
    |
  ApplicationAPI -- domain operations facade
```

---

## 2. Controller Inventory

| # | Class | File | Purpose | Injected Dependencies |
|---|-------|------|---------|-----------------------|
| 1 | `PlotCreationController` | `src/web/controllers/plot/creation_controller.py:42` | Plot lifecycle: create, select, rename, delete, duplicate | `ApplicationAPI`, `UIStateManager`, `PlotLifecycleService`, `PlotTypeRegistry` |
| 2 | `PipelineController` | `src/web/controllers/plot/pipeline_controller.py:40` | Data transformation pipeline: add/remove/reorder shapers, finalize | `ApplicationAPI`, `UIStateManager`, `PipelineExecutor` |
| 3 | `PlotRenderController` | `src/web/controllers/plot/render_controller.py:44` | Visualization: config gathering, figure generation, caching, chart display | `ApplicationAPI`, `UIStateManager`, `PlotLifecycleService`, `PlotTypeRegistry` |

All three controllers are instantiated in `src/web/pages/manage_plots.py:79-81` and receive
their dependencies from the same `show_manage_plots_page()` function scope.

---

## 3. Controller Detail Catalog

### 3.1 PlotCreationController

- **File**: `src/web/controllers/plot/creation_controller.py:42`
- **Class**: `PlotCreationController`
- **Purpose**: Manages which plots exist and which plot is currently selected. Handles
  create, select, rename, delete, and duplicate operations.
- **Single Responsibility**: Plot lifecycle -- does NOT handle pipeline editing, config
  gathering, or rendering.

#### Constructor

```python
def __init__(
    self,
    api: ApplicationAPI,
    ui_state: UIStateManager,
    lifecycle: PlotLifecycleService,   # Protocol
    registry: PlotTypeRegistry,        # Protocol
) -> None
```

**Stored as instance attributes**:
- `self._api: ApplicationAPI`
- `self._ui: UIStateManager`
- `self._lifecycle: PlotLifecycleService`
- `self._registry: PlotTypeRegistry`

#### Methods

| Method | Signature | Return | Description |
|--------|-----------|--------|-------------|
| `render_create_section` | `(self) -> None` | `None` | Renders "Create New Plot" form via `PlotCreationComponent.render()`. On `create_clicked`, calls `self._lifecycle.create_plot()` then `st.rerun()`. |
| `render_selector` | `(self) -> RenderablePlot \| None` | `RenderablePlot \| None` | Renders plot selector pills via `PlotSelectorComponent.render()`. Returns selected plot or `None` if no plots exist. Updates `state_manager.set_current_plot_id()` on selection change. |
| `render_controls` | `(self, plot: PlotHandle) -> None` | `None` | Renders rename/delete/duplicate controls via `PlotControlsComponent.render()`. Handles rename (direct assignment), delete (cleanup + lifecycle + rerun), duplicate (lifecycle + rerun). |

#### Protocol Dependencies

| Protocol | Methods Used | Satisfied By |
|----------|-------------|--------------|
| `PlotLifecycleService` | `create_plot()`, `delete_plot()`, `duplicate_plot()` | `PlotLifecycleAdapter` (wraps `PlotService`) |
| `PlotTypeRegistry` | `get_available_types()` | `PlotTypeRegistryAdapter` (wraps `PlotFactory`) |
| `PlotHandle` | `.plot_id`, `.name` (read/write) | `BasePlot` at runtime |
| `RenderablePlot` | `.plot_id`, `.name`, `.plot_type`, `.config`, `.processed_data` | `BasePlot` at runtime |

#### Component Dependencies

| Component | Method Called | Returns |
|-----------|-------------|---------|
| `PlotCreationComponent` | `.render(default_name, available_types)` | `dict` with `name`, `plot_type`, `create_clicked` |
| `PlotSelectorComponent` | `.render(plot_names, default_index)` | Selected plot name `str` |
| `PlotSelectorComponent` | `.render_no_plots_warning()` | `None` (renders warning) |
| `PlotControlsComponent` | `.render(plot_id, current_name)` | `dict` with `new_name`, `delete_clicked`, `duplicate_clicked` |

#### State Access Patterns

| State Source | Access Type | Keys/Methods |
|--------------|------------|--------------|
| `ApplicationAPI.state_manager` | Read | `get_plot_counter()`, `get_plots()`, `get_current_plot_id()` |
| `ApplicationAPI.state_manager` | Write | `set_current_plot_id()` |
| `UIStateManager.plot` | Write | `cleanup(plot_id)` (on delete) |

#### Called By

- `src/web/pages/manage_plots.py:84` -- `creation.render_create_section()`
- `src/web/pages/manage_plots.py:87` -- `creation.render_selector()`
- `src/web/pages/manage_plots.py:91` -- `creation.render_controls(current_plot)`

---

### 3.2 PipelineController

- **File**: `src/web/controllers/plot/pipeline_controller.py:40`
- **Class**: `PipelineController`
- **Purpose**: Manages the data transformation pipeline for a plot -- adding/removing/
  reordering shapers, computing intermediate data at each step, previewing output, and
  finalizing the pipeline.
- **Single Responsibility**: Pipeline editing -- does NOT handle plot creation, config, or
  rendering.

#### Constructor

```python
def __init__(
    self,
    api: ApplicationAPI,
    ui_state: UIStateManager,
    pipeline_executor: PipelineExecutor,   # Protocol
) -> None
```

**Stored as instance attributes**:
- `self._api: ApplicationAPI`
- `self._ui: UIStateManager`
- `self._pipeline: PipelineExecutor`

#### Methods

| Method | Signature | Return | Description |
|--------|-----------|--------|-------------|
| `render` | `(self, plot: PlotHandle) -> None` | `None` | Main entry: renders section header, "Add shaper" selector, current pipeline steps, and "Finalize" button. Delegates to private helpers. |
| `_handle_pipeline_steps` | `(self, plot: PlotHandle, raw_data: pd.DataFrame) -> None` | `None` | Iterates pipeline steps with incremental computation (O(n) not O(n^2)). For each step: renders via `PipelineStepComponent`, handles move-up/move-down/delete actions, advances `step_input`. |
| `_handle_finalize` | `(self, plot: PlotHandle, raw_data: pd.DataFrame) -> None` | `None` | Applies full pipeline to raw data via `self._pipeline.apply_shapers()`, stores result in `plot.processed_data`. |

#### Protocol Dependencies

| Protocol | Methods Used | Satisfied By |
|----------|-------------|--------------|
| `PipelineExecutor` | `apply_shapers()`, `configure_shaper()` | `PipelineExecutorAdapter` (wraps `apply_shapers()` and `configure_shaper()` functions) |
| `PlotHandle` | `.plot_id`, `.name`, `.pipeline`, `.pipeline_counter`, `.processed_data` | `BasePlot` at runtime |

#### Component Dependencies

| Component | Method Called | Returns |
|-----------|-------------|---------|
| `PipelineComponent` | `.render_section_header()` | `None` |
| `PipelineComponent` | `.render_no_data_warning()` | `None` |
| `PipelineComponent` | `.render_pipeline_label()` | `None` |
| `PipelineComponent` | `.render_add_shaper(plot_id)` | `dict` with `add_clicked`, `shaper_type` |
| `PipelineComponent` | `.render_finalize_button(plot_id)` | `bool` |
| `PipelineStepComponent` | `.render_step(plot_id, idx, shaper_type, shaper_id, step_input, current_config, is_first, is_last, configure_fn, apply_fn)` | `PipelineStepResult` TypedDict |
| `PipelineStepComponent` | `.render_finalize_result(processed)` | `None` |
| `PipelineStepComponent` | `.render_finalize_error(error)` | `None` |

#### State Access Patterns

| State Source | Access Type | Keys/Methods |
|--------------|------------|--------------|
| `ApplicationAPI.state_manager` | Read | `get_data()` (raw uploaded data) |
| `PlotHandle` (mutable) | Read/Write | `plot.pipeline` (list mutation: append, pop, swap), `plot.pipeline_counter` (increment), `plot.processed_data` (write on finalize) |

#### Incremental Computation Design

The `_handle_pipeline_steps` method avoids O(n^2) re-computation by threading `step_input`
through the loop. Each step's output (`result["step_output"]`) becomes the next step's
input, so the pipeline is applied incrementally in one pass.

#### Called By

- `src/web/pages/manage_plots.py:95` -- via `st.fragment(_pipeline_fragment)(pipeline, current_plot)`

---

### 3.3 PlotRenderController

- **File**: `src/web/controllers/plot/render_controller.py:44`
- **Class**: `PlotRenderController`
- **Purpose**: Orchestrates the visualization section -- config gathering (type-specific +
  advanced + theme), figure generation with caching, engine selection, and chart display.
- **Single Responsibility**: Turning plot config + data into a rendered chart. Does NOT
  handle pipeline editing or plot lifecycle.

#### Constructor

```python
def __init__(
    self,
    api: ApplicationAPI,
    ui_state: UIStateManager,
    lifecycle: PlotLifecycleService,   # Protocol
    registry: PlotTypeRegistry,        # Protocol
) -> None
```

**Stored as instance attributes**:
- `self._api: ApplicationAPI`
- `self._ui: UIStateManager`
- `self._lifecycle: PlotLifecycleService`
- `self._registry: PlotTypeRegistry`

#### Methods

| Method | Signature | Return | Description |
|--------|-----------|--------|-------------|
| `render` | `(self, plot: RenderablePlot) -> None` | `None` | Main entry point. Orchestrates: (1) no-data guard, (2) plot type selector, (3) type-specific config via `plot.render_config_ui()`, (4) advanced+theme config via `plot.render_settings_section()`, (5) config change detection, (6) refresh controls via `ChartDisplayComponent`, (7) figure generation via `_render_visualization`. |
| `_render_visualization` | `(self, plot: RenderablePlot, should_generate: bool) -> None` | `None` | Figure lifecycle: cache check, generation via `plot.create_figure()` + `plot.apply_common_layout()`, legend label renaming, engine selection via `ChartDisplayComponent`, Plotly or Matplotlib chart display, relayout event handling. |
| `_compute_figure_cache_key` | `(plot_id: int, config: PlotConfig, data_hash: str) -> str` | `str` | Static method. Computes stable MD5-based cache key from config (excluding transient zoom/pan) + data hash. |
| `_compute_data_hash` | `(data: pd.DataFrame) -> str` | `str` | Static method. Fast DataFrame fingerprint using shape + first/last row + column names. |

#### Protocol Dependencies

| Protocol | Methods Used | Satisfied By |
|----------|-------------|--------------|
| `PlotLifecycleService` | `change_plot_type()` | `PlotLifecycleAdapter` (wraps `PlotService`) |
| `PlotTypeRegistry` | `get_available_types()` | `PlotTypeRegistryAdapter` (wraps `PlotFactory`) |
| `RenderablePlot` | `.plot_id`, `.name`, `.plot_type`, `.config`, `.processed_data`, `.last_generated_fig`, `.last_traces`, `render_config_ui()`, `render_settings_section()`, `create_figure()`, `apply_common_layout()`, `update_from_relayout()` | `BasePlot` at runtime |

#### Component Dependencies

| Component | Method Called | Returns |
|-----------|-------------|---------|
| `ChartDisplayComponent` | `.render_refresh_controls(plot_id, auto_refresh, config_changed)` | `dict` with `auto_refresh`, `manual_refresh`, `should_generate` |
| `ChartDisplayComponent` | `.render_engine_selector(plot_id, current_engine)` | `str \| None` |
| `ChartDisplayComponent` | `.render_plotly_chart(fig, plot_id, plot_name, config)` | `dict \| None` (relayout data) |
| `ChartDisplayComponent` | `.render_matplotlib_chart(plotly_fig, plot_id, plot_name, config, plot_type, traces)` | `None` |
| `ChartDisplayComponent` | `.render_error(error)` | `None` |
| `render_settings_pills` | `render_settings_pills(show_advanced)` | `str \| None` (selected section key) |

#### External Dependencies

| Dependency | Usage |
|------------|-------|
| `EngineManager` | `.get_engine()`, `.set_engine()`, `.is_matplotlib()` -- manages Plotly vs Matplotlib mode in session state |
| `get_plot_cache()` | Figure cache (LRU): `.get(key)`, `.set(key, fig)` |
| `PlotConfig` | Type alias `dict[str, Any]` -- progressive typing toward `PlotDisplayConfig` |

#### State Access Patterns

| State Source | Access Type | Keys/Methods |
|--------------|------------|--------------|
| `UIStateManager.plot` | Read | `get_auto_refresh(plot_id)` |
| `UIStateManager.plot` | Write | `set_auto_refresh(plot_id, value)` |
| `RenderablePlot` (mutable) | Write | `plot.config = current_config`, `plot.last_generated_fig = fig` |
| `st.session_state` | Read/Write | `plot.{plot_id}.last_relayout` (relayout event deduplication) |
| `EngineManager` | Read/Write | `ring5_engine_mode` session state key |

#### Figure Caching Strategy

1. Cache key = `plot_{id}_{config_hash_8}_{data_hash_12}` (excludes `xaxis_range`, `yaxis_range`)
2. On render: check cache first, restore `plot.last_generated_fig` if cache hit
3. On generation: call `plot.create_figure()` + `plot.apply_common_layout()`, rename legend labels, store in both `plot.last_generated_fig` and `cache.set()`
4. Data hash uses shape + first/last row + column names for speed

#### Called By

- `src/web/pages/manage_plots.py:98` -- via `st.fragment(_render_fragment)(render, current_plot)`

---

## 4. Adapter Pattern

### 4.1 Overview

**File**: `src/web/pages/plot_adapters.py`
**Layer**: Pages (Layer 1)

The adapter pattern bridges **old concrete classes** (which use static/class methods) to
**protocol contracts** (which require instance methods). This is the classic Gang of Four
Adapter pattern applied to enable protocol-based dependency injection without rewriting the
underlying service implementations.

```
Controller depends on Protocol (abstract)
    |
Adapter implements Protocol (adapts concrete -> abstract)
    |
Concrete Service (static/class methods, standalone functions)
```

### 4.2 PlotLifecycleAdapter

```python
class PlotLifecycleAdapter:
    """Adapts PlotService static methods to PlotLifecycleService protocol."""
```

| Adapter Method | Delegates To | Notes |
|----------------|-------------|-------|
| `create_plot(name, plot_type, state_manager) -> PlotHandle` | `PlotService.create_plot(name, plot_type, state_manager)` | Direct pass-through |
| `delete_plot(plot_id, state_manager) -> None` | `PlotService.delete_plot(plot_id, state_manager)` | Direct pass-through |
| `duplicate_plot(plot, state_manager) -> PlotHandle` | `PlotService.duplicate_plot(cast(BasePlot, plot), state_manager)` | Casts `PlotHandle` to `BasePlot` |
| `change_plot_type(plot, new_type, state_manager) -> PlotHandle` | `PlotService.change_plot_type(cast(BasePlot, plot), new_type, state_manager)` | Casts `PlotHandle` to `BasePlot` |

**Satisfies**: `PlotLifecycleService` protocol
**Used By**: `PlotCreationController`, `PlotRenderController`

### 4.3 PlotTypeRegistryAdapter

```python
class PlotTypeRegistryAdapter:
    """Adapts PlotFactory class methods to PlotTypeRegistry protocol."""
```

| Adapter Method | Delegates To |
|----------------|-------------|
| `get_available_types() -> list[str]` | `PlotFactory.get_available_plot_types()` |

**Satisfies**: `PlotTypeRegistry` protocol
**Used By**: `PlotCreationController`, `PlotRenderController`

### 4.4 PipelineExecutorAdapter

```python
class PipelineExecutorAdapter:
    """Adapts apply_shapers() and configure_shaper() functions to PipelineExecutor protocol."""
```

| Adapter Method | Delegates To |
|----------------|-------------|
| `apply_shapers(data, configs) -> pd.DataFrame` | `apply_shapers(data, configs)` (standalone function) |
| `configure_shaper(shaper_type, data, shaper_id, config, owner_id) -> ShaperStepConfig` | `configure_shaper(shaper_type, data, shaper_id, config, owner_id)` (standalone function) |

**Satisfies**: `PipelineExecutor` protocol
**Used By**: `PipelineController`

### 4.5 Adapter Wiring Site

All adapters are instantiated in `src/web/pages/manage_plots.py:74-76`:

```python
lifecycle: PlotLifecycleAdapter = PlotLifecycleAdapter()
registry: PlotTypeRegistryAdapter = PlotTypeRegistryAdapter()
pipeline_executor: PipelineExecutorAdapter = PipelineExecutorAdapter()
```

Then injected into controllers at lines 79-81:

```python
creation = PlotCreationController(api, ui_state, lifecycle, registry)
pipeline = PipelineController(api, ui_state, pipeline_executor)
render   = PlotRenderController(api, ui_state, lifecycle, registry)
```

---

## 5. Web-Layer Protocols

### 5.1 Overview

**File**: `src/web/models/plot_protocols.py`
**Layer**: Models (Layer 5) -- NO Streamlit dependency

Protocols define the contracts between controllers and concrete implementations. Controllers
import only these protocols, never the concrete `BasePlot`, `PlotService`, `PlotFactory`,
or shaper functions.

### 5.2 Protocol Hierarchy

```
PlotHandle (Protocol, runtime_checkable)
    |
    +-- ConfigRenderer (Protocol)
    |
    +-- RenderablePlot (PlotHandle + ConfigRenderer, Protocol, runtime_checkable)

PlotLifecycleService (Protocol)
PlotTypeRegistry (Protocol)
PipelineExecutor (Protocol)
```

### 5.3 PlotHandle

```python
@runtime_checkable
class PlotHandle(Protocol):
    plot_id: int
    name: str
    plot_type: str
    config: dict[str, Any]
    processed_data: pd.DataFrame | None
    pipeline: list[PipelineStep]
    pipeline_counter: int
```

**Purpose**: Contract for plot object attributes as seen by controllers.
**Satisfied By**: `BasePlot` (without modification).
**Used By**: `PlotCreationController.render_controls()`, `PipelineController.render()`.

### 5.4 ConfigRenderer

```python
class ConfigRenderer(Protocol):
    plot_id: int
    def render_config_ui(self, data, config) -> dict[str, Any]: ...
    def render_display_options(self, config) -> dict[str, Any]: ...
    def render_theme_options(self, config) -> dict[str, Any]: ...
    def render_settings_section(self, section, saved_config, data=None) -> dict[str, Any]: ...
```

**Purpose**: Config-UI rendering facet for type-specific widgets.
**Satisfied By**: `BasePlot` (which has all these methods).
**Used By**: `PlotRenderController.render()` (via `RenderablePlot`).

### 5.5 RenderablePlot

```python
@runtime_checkable
class RenderablePlot(PlotHandle, ConfigRenderer, Protocol):
    last_generated_fig: go.Figure | None
    last_traces: TraceBuildResult | None
    def create_figure(self, data, config) -> go.Figure: ...
    def apply_common_layout(self, fig, config) -> go.Figure: ...
    def update_from_relayout(self, relayout_data) -> bool: ...
```

**Purpose**: Combined protocol for plots that support data access AND config rendering AND
figure generation. Replaces unsafe `cast(ConfigRenderer, plot)` pattern.
**Satisfied By**: `BasePlot`.
**Used By**: `PlotRenderController.render()`, `PlotRenderController._render_visualization()`.

### 5.6 PlotLifecycleService

```python
class PlotLifecycleService(Protocol):
    def create_plot(self, name, plot_type, state_manager) -> PlotHandle: ...
    def delete_plot(self, plot_id, state_manager) -> None: ...
    def duplicate_plot(self, plot, state_manager) -> PlotHandle: ...
    def change_plot_type(self, plot, new_type, state_manager) -> PlotHandle: ...
```

**Purpose**: Contract for plot CRUD operations.
**Implemented By**: `PlotLifecycleAdapter` (wraps `PlotService` static methods).

### 5.7 PlotTypeRegistry

```python
class PlotTypeRegistry(Protocol):
    def get_available_types(self) -> list[str]: ...
```

**Purpose**: Contract for querying available plot types.
**Implemented By**: `PlotTypeRegistryAdapter` (wraps `PlotFactory.get_available_plot_types()`).

### 5.8 PipelineExecutor

```python
class PipelineExecutor(Protocol):
    def apply_shapers(self, data, configs) -> pd.DataFrame: ...
    def configure_shaper(self, shaper_type, data, shaper_id, config, owner_id=None) -> ShaperStepConfig: ...
```

**Purpose**: Contract for pipeline operations (apply shapers, render shaper config UI).
**Implemented By**: `PipelineExecutorAdapter` (wraps standalone `apply_shapers()` and
`configure_shaper()` functions from `src/web/pages/ui/shaper_config`).

---

## 6. Web-Layer Models

### 6.1 Overview

**File**: `src/web/models/plot_models.py`
**Layer**: Models (Layer 5) -- ZERO Streamlit imports, ZERO side effects

These models are framework-agnostic TypedDicts that serve as the shared vocabulary between
Controllers, Components, and State.

### 6.2 Model Catalog

| TypedDict | total | Purpose | Key Fields |
|-----------|-------|---------|------------|
| `AnnotationLineConfig` | `False` | Line styling for annotation shapes | `color: str`, `width: int` |
| `AnnotationShapeConfig` | `False` | Plot annotation shape (line, circle, rect) | `type`, `x0`, `y0`, `x1`, `y1`, `line` |
| `SeriesStyleConfig` | `False` | Per-series visual styling | `name`, `color`, `marker_symbol`, `pattern` |
| `RelayoutEventData` | `False` | Plotly relayout event subset | `xaxis_range`, `yaxis_range`, `legend_x/y`, etc. |
| `ShaperStep` | `True` | Single pipeline step | `id: int`, `type: str`, `config: ShaperStepConfig` |
| `MarginsConfig` | `False` | Plot margins in pixels | `top`, `bottom`, `left`, `right` |
| `TypographyConfig` | `False` | Font sizes and colors | `font_size`, `title_font_size`, etc. |
| `PlotDisplayConfig` | `False` | Complete display config (canonical schema) | ~90 fields across identity, appearance, interaction, advanced |
| `PlotConfig` | n/a | Runtime alias `dict[str, Any]` | Progressive typing alias for `PlotDisplayConfig` |

### 6.3 PlotConfig Migration Path

`PlotConfig = dict[str, Any]` is the current runtime type used in controller/component
signatures. It signals "this dictionary follows the `PlotDisplayConfig` schema but may
contain extra keys." The migration path is to narrow `PlotConfig` to `PlotDisplayConfig`
one call site at a time as widgets and applicators become fully spec-driven.

---

## 7. DataManager Architecture

### 7.1 Abstract Base Class

**File**: `src/web/components/data_managers/data_manager.py:13`

```python
class DataManager(ABC):
    def __init__(self, api: ApplicationAPI):
        self.api = api

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def render(self) -> None: ...

    def get_data(self) -> pd.DataFrame | None:
        return self.api.state_manager.get_data()

    def set_data(self, data: pd.DataFrame) -> None:
        self.api.state_manager.set_data(data)
```

**Design**: Template Method pattern. Each subclass implements `name` (tab label) and
`render()` (full UI). The base class provides `get_data()` / `set_data()` helpers that
route through `ApplicationAPI.state_manager`.

### 7.2 Concrete Implementations

| Class | File | `name` Property | Purpose |
|-------|------|-----------------|---------|
| `SeedsReducerManager` | `src/web/components/data_managers/seeds_reducer.py:16` | `"Seeds Reducer"` | Aggregates data across random seeds (mean + stdev) |
| `MixerManager` | `src/web/components/data_managers/mixer.py:16` | `"Mixer (Merge Columns)"` | Merges multiple columns with SD propagation |
| `OutlierRemoverManager` | `src/web/components/data_managers/outlier_remover.py:16` | `"Outlier Remover"` | Filters outliers based on IQR (Q3 threshold) |
| `PreprocessorManager` | `src/web/components/data_managers/preprocessor.py:16` | `"Preprocessor (Basic)"` | Creates new columns via arithmetic (divide, sum, etc.) |

### 7.3 Common DataManager Patterns

All four managers follow a consistent internal pattern:

1. **Render header and info**: `st.markdown("### ...")` + `st.info("...")`
2. **Get data**: `self.get_data()` with early return on `None`
3. **History load trigger**: `UIStateManager().manager.consume_load_trigger("manager_name")`
   restores widget state from a previously saved operation
4. **Widget rendering**: Column selectors, operation selectors, config inputs
5. **Preview button**: Calls `self.api.managers.<operation>()` and stores result via
   `self.api.set_preview("key", result_df)`
6. **Confirm button**: Retrieves preview, calls `self.set_data()`, records
   `OperationRecord` in history, clears preview, calls `st.rerun()`
7. **History display**: `HistoryComponents.render_manager_history(...)` with load/delete

### 7.4 DataManager Wiring

**File**: `src/web/pages/data_managers.py`

DataManagers are instantiated inline within `st.fragment` closures:

```python
with tab3:
    @st.fragment
    def _seeds_fragment() -> None:
        SeedsReducerManager(api).render()
    _seeds_fragment()
```

Each uses `st.fragment` for partial re-rendering (only the tab's content reruns, not the
full page).

### 7.5 DataManagerComponents (Static UI Helpers)

**File**: `src/web/components/data_managers/data_manager_components.py:14`

```python
class DataManagerComponents:
    @staticmethod
    def render_summary_tab(data: pd.DataFrame) -> None: ...
    @staticmethod
    def render_visualization_tab(data: pd.DataFrame) -> None: ...
```

These are pure rendering components (no state mutation) for the Summary and Data
Visualization tabs on the Data Managers page.

---

## 8. UIStateManager Architecture

### 8.1 Overview

**File**: `src/web/state/ui_state_manager.py`
**Layer**: State (Layer 4)

Replaces all scattered `st.session_state["key"]` access with a single, namespaced, typed
manager. Every piece of transient UI state flows through this class.

### 8.2 Class Structure

```
UIStateManager
    |-- .plot: _PlotUIState          # plot.{id}.* keys
    |-- .manager: _ManagerUIState    # manager.{name}.* keys
    |-- .nav: _NavUIState            # nav.* keys
    |-- .export: _ExportUIState      # export.* keys
    |
    +-- cleanup_all()                # Remove all namespaced keys
    +-- get_all_keys()               # Debug: list all managed keys
```

### 8.3 Sub-Manager Details

#### _PlotUIState (namespace: `plot.{plot_id}.*`)

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_auto_refresh` | `(plot_id) -> bool` | Auto-refresh toggle (default `True`) |
| `set_auto_refresh` | `(plot_id, value) -> None` | Set auto-refresh |
| `is_dialog_visible` | `(plot_id, dialog) -> bool` | Check dialog visibility |
| `set_dialog_visible` | `(plot_id, dialog, visible) -> None` | Show/hide dialog |
| `hide_all_dialogs` | `(plot_id) -> None` | Hide all dialogs for a plot |
| `get_order` | `(plot_id, order_type) -> list \| None` | Custom ordering (xaxis, group, legend) |
| `set_order` | `(plot_id, order_type, order) -> None` | Set custom ordering |
| `is_editing_shapes` | `(plot_id) -> bool` | Shape editing mode |
| `set_editing_shapes` | `(plot_id, editing) -> None` | Toggle shape editing |
| `get_pending_updates` | `() -> dict \| None` | Pending widget updates from relayout |
| `set_pending_updates` | `(updates) -> None` | Store pending updates |
| `consume_pending_updates` | `() -> dict \| None` | Atomic pop of pending updates |
| `cleanup` | `(plot_id) -> None` | Remove ALL keys for a plot (incl. legacy) |

#### _ManagerUIState (namespace: `manager.{name}.*`)

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_load_trigger` | `(manager_name) -> dict \| None` | Pending load-from-history trigger |
| `set_load_trigger` | `(manager_name, record) -> None` | Set load trigger |
| `consume_load_trigger` | `(manager_name) -> dict \| None` | Atomic pop of load trigger |
| `set_form_value` | `(manager_name, field, value) -> None` | Set form field value |
| `get_form_value` | `(manager_name, field) -> Any \| None` | Get form field value |
| `cleanup` | `(manager_name) -> None` | Remove all keys for a manager |

#### _NavUIState (namespace: `nav.*`)

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_current_page` | `() -> str \| None` | Current page name |
| `set_current_page` | `(page) -> None` | Set current page |
| `get_current_tab` | `() -> str \| None` | Current tab |
| `set_current_tab` | `(tab) -> None` | Set current tab |

#### _ExportUIState (namespace: `export.*`)

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_last_export_path` | `() -> str` | Last export path (default `""`) |
| `set_last_export_path` | `(path) -> None` | Set export path |

### 8.4 WidgetKeyBuilder

```python
class WidgetKeyBuilder:
    @staticmethod
    def plot_key(plot_id, *parts) -> str:     # "plot.{id}.{parts}"
    @staticmethod
    def manager_key(manager, *parts) -> str:  # "manager.{mgr}.{parts}"
    @staticmethod
    def global_key(*parts) -> str:            # "g.{parts}"
```

Used directly by DataManager implementations for widget key construction.

### 8.5 State Boundary

| State Type | Owner | Examples |
|------------|-------|---------|
| **Transient UI state** | `UIStateManager` | Auto-refresh toggles, dialog visibility, ordering widgets, pending relayout updates |
| **Persistent domain state** | `ApplicationAPI.state_manager` (`RepositoryStateManager`) | Data, plots, config, history, plot counter |

---

## 9. Presenter Deletion Analysis

### 9.1 Deleted Files

The following presenters were **deleted** in the current branch (confirmed: files do not
exist on disk):

- `src/web/presenters/plot/config_presenter.py`
- `src/web/presenters/plot/controls_presenter.py`
- `src/web/presenters/plot/pipeline_presenter.py`

### 9.2 Stale Reference

The `src/web/presenters/plot/__init__.py` file still contains imports from the deleted
files:

```python
from src.web.presenters.plot.config_presenter import ConfigPresenter
from src.web.presenters.plot.controls_presenter import PlotControlsPresenter
from src.web.presenters.plot.pipeline_presenter import PipelinePresenter
```

This `__init__.py` will raise `ImportError` if any code attempts to import from
`src.web.presenters.plot`. Currently, no other source file imports from this path (the
grep confirms the only references are within this `__init__.py` itself), so it is dead code
but represents a cleanup opportunity.

### 9.3 What Replaced Presenters

| Deleted Presenter | Replacement | File |
|-------------------|-------------|------|
| `PlotControlsPresenter` | `PlotControlsComponent` | `src/web/components/common/plot_controls.py` |
| `PipelinePresenter` | `PipelineComponent` + `PipelineStepComponent` | `src/web/components/common/pipeline.py`, `pipeline_step.py` |
| `ConfigPresenter` | Inline rendering in `PlotRenderController.render()` + `plot.render_config_ui()` + `plot.render_settings_section()` | `src/web/controllers/plot/render_controller.py` |

### 9.4 Pattern Shift

The shift from Presenters to Components represents a simplification:

- **Presenters**: Were designed as "passive UI renderers" returning typed dicts, with no
  state management. In practice they duplicated logic that now lives in components.
- **Components**: Same philosophy (render widgets, return typed dicts) but named
  "Component" for consistency with Streamlit's component model.
- **Net effect**: One fewer layer (Presenter is folded into Component). Controllers call
  Components directly instead of going through Presenters.

---

## 10. Web Layer Design Patterns

### 10.1 Page-Controller-Component (PCC) Architecture

The web layer does NOT use classic MVC. Instead it uses a Streamlit-adapted pattern:

```
Page (thin wiring)
  |-- creates Adapters (bridge to concrete services)
  |-- creates Controllers (with injected dependencies)
  |-- calls Controller methods in sequence
  |
Controller (orchestration)
  |-- reads state (ApplicationAPI, UIStateManager)
  |-- calls Components (passive rendering)
  |-- interprets Component return values (user actions)
  |-- performs domain operations (via protocol services)
  |-- updates state
  |-- triggers reruns (st.rerun)
  |
Component (presentation)
  |-- renders Streamlit widgets
  |-- returns typed dicts of user selections
  |-- NO state mutation, NO API calls, NO reruns
```

### 10.2 Dependency Injection via Constructor + Protocol

Controllers never import concrete service classes. Instead:

1. Protocols define abstract contracts (`PlotLifecycleService`, `PlotTypeRegistry`,
   `PipelineExecutor`)
2. Adapters wrap concrete classes to satisfy protocols
3. The Page creates adapters and injects them into controller constructors
4. Controllers store dependencies as typed protocol references

This enables:
- **Testability**: Tests inject `MagicMock` objects as dependencies
- **Decoupling**: Controllers are independent of concrete `PlotService`, `PlotFactory` etc.
- **Substitutability**: Adapters can be swapped without touching controllers

### 10.3 Adapter Pattern (GoF)

Three adapters (`PlotLifecycleAdapter`, `PlotTypeRegistryAdapter`,
`PipelineExecutorAdapter`) convert static/class-method services and standalone functions
into instance-method objects compatible with protocol contracts. This is the textbook
Object Adapter pattern.

### 10.4 Stateless Controller Pattern

Controllers hold no mutable state across Streamlit reruns. All persistent state lives in:
- `ApplicationAPI.state_manager` (domain: data, plots, config, history)
- `UIStateManager` (transient: auto-refresh, dialog flags, ordering)

Controllers are instantiated fresh on every page render, receive their dependencies via
constructor injection, and are garbage collected at the end of the render cycle.

### 10.5 Template Method Pattern (DataManager)

The `DataManager` ABC defines the skeleton algorithm (`get_data()` / `set_data()`) while
subclasses provide the specific `name` and `render()` implementations. The preview/confirm
flow is a convention (not enforced by the ABC) that all four implementations follow.

### 10.6 Protocol-Based Structural Typing

Python `Protocol` classes enable structural subtyping: `BasePlot` satisfies `PlotHandle`,
`ConfigRenderer`, and `RenderablePlot` without explicitly inheriting from them. The
`@runtime_checkable` decorator on `PlotHandle` and `RenderablePlot` enables `isinstance()`
checks at runtime.

### 10.7 Fragment-Based Partial Rendering

Both the Manage Plots page and Data Managers page use `st.fragment` to isolate controller
render calls. This means that interactions within a fragment (e.g., pipeline step
manipulation) only reruns that fragment, not the entire page.

```python
# manage_plots.py
st.fragment(_pipeline_fragment)(pipeline, current_plot)
st.fragment(_render_fragment)(render, current_plot)
```

### 10.8 Incremental Pipeline Computation

`PipelineController._handle_pipeline_steps()` threads `step_input` through the loop,
using each step's output as the next step's input. This avoids the naive O(n^2) approach
of re-applying all previous shapers from scratch at each step.

### 10.9 Figure Cache with Content-Addressable Keys

`PlotRenderController` uses MD5-based content-addressable cache keys that combine plot ID,
config hash (excluding transient zoom/pan state), and data hash (shape + first/last row
fingerprint). This ensures cache invalidation on any config or data change while avoiding
unnecessary regeneration during zoom/pan interactions.

---

## 11. Test Coverage Summary

### 11.1 Test Files

| Test File | Covers | Test Count |
|-----------|--------|------------|
| `tests/ui_logic/test_creation_controller.py` | `PlotCreationController` | 10 tests across 3 test classes |
| `tests/ui_logic/test_render_controller.py` | `PlotRenderController` | 8 tests across 4 test classes |
| `tests/ui_logic/test_plot_adapters.py` | All 3 adapters + protocol conformance | 10 tests across 4 test classes |
| `tests/ui_logic/test_protocols_and_models.py` | Protocols + TypedDicts | 9 tests across 3 test classes |

### 11.2 Test Strategy

- **Mocked Streamlit**: All tests patch `st` to avoid requiring a Streamlit runtime
- **Mocked dependencies**: Controllers receive `MagicMock` objects for `api`, `ui_state`,
  `lifecycle`, `registry`, `pipeline_executor`
- **StubPlotHandle**: Lightweight stub in `tests/ui_logic/conftest.py:19` satisfying
  `PlotHandle`, `ConfigRenderer`, and `RenderablePlot` protocols
- **Delegation verification**: Tests verify that controllers delegate to the correct
  service/component methods with the correct arguments
- **Error resilience**: Tests verify that config errors are caught and displayed via
  `st.exception` without crashing the flow

### 11.3 Notable Test Patterns

- `TestRenderCreateSection`: Verifies presenter receives `default_name` based on
  `plot_counter + 1`, lifecycle is called on `create_clicked`, no action when
  `create_clicked=False` or `plot_type=None`
- `TestRenderControls`: Verifies rename updates `plot.name`, delete calls
  `ui_state.plot.cleanup()` + `lifecycle.delete_plot()` + `st.rerun()`, duplicate calls
  `lifecycle.duplicate_plot()` + `st.rerun()`
- `TestErrorResilience`: Verifies that config errors set `config_error=True` and
  result in `should_generate=False`, while the flow continues to render

---

## 12. Component Layer Summary

Components used by controllers follow a consistent pattern: all methods are `@staticmethod`,
no instance state, they render Streamlit widgets and return typed dicts or primitive values.

| Component | File | Methods |
|-----------|------|---------|
| `PlotCreationComponent` | `src/web/components/common/plot_creation.py` | `render(default_name, available_types) -> dict` |
| `PlotSelectorComponent` | `src/web/components/common/plot_selector.py` | `render(plot_names, default_index) -> str`, `render_no_plots_warning() -> None` |
| `PlotControlsComponent` | `src/web/components/common/plot_controls.py` | `render(plot_id, current_name) -> dict` |
| `PipelineComponent` | `src/web/components/common/pipeline.py` | `render_section_header()`, `render_no_data_warning()`, `render_pipeline_label()`, `render_add_shaper(plot_id) -> dict`, `render_shaper_controls(...) -> dict`, `render_finalize_button(plot_id) -> bool` |
| `PipelineStepComponent` | `src/web/components/common/pipeline_step.py` | `render_step(...) -> PipelineStepResult`, `render_finalize_result(processed)`, `render_finalize_error(error)` |
| `ChartDisplayComponent` | `src/web/components/common/chart_display.py` | `render_refresh_controls(...) -> dict`, `render_engine_selector(...) -> str\|None`, `render_plotly_chart(...) -> dict\|None`, `render_matplotlib_chart(...)`, `render_error(error)` |

---

## 13. Downstream Dependencies

This analysis feeds into:

- `DEVELOPER_GUIDE_PLAN.md` -- `web/controllers.md` (controller usage guide)
- `AI_KNOWLEDGE_BASE_PLAN.md` -- `architecture/system-overview.md` (web layer section)
- **Step 18 (Data Flow)** -- controllers orchestrate the data flow from user input through
  pipeline to visualization
- **Step 19 (Extension Points)** -- controller pattern for adding new features (new
  controller, new adapter, new protocol)

### Cleanup Opportunities Identified

1. **Stale presenter `__init__.py`**: `src/web/presenters/plot/__init__.py` imports deleted
   files. Should be removed or emptied.
2. **PlotRenderer duplication**: `src/web/pages/ui/plotting/plot_renderer.py` contains
   static methods (`_compute_figure_cache_key`, `_compute_data_hash`) that are duplicated
   in `PlotRenderController`. The `PlotRenderer` class is retained as a legacy utility.
3. **PlotConfig progressive typing**: The `dict[str, Any]` alias should be progressively
   narrowed to `PlotDisplayConfig` as individual call sites are migrated.
