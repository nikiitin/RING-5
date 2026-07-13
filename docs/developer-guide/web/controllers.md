---
title: "Controllers"
parent: Web Layer
grand_parent: Developer Guide
nav_order: 2
---

# Controllers

## Overview

The web layer in RING-5 Unified Engine v2 uses a **Page-Controller-Component (PCC)**
architecture. Controllers sit at Layer 2 of the stack and serve as the orchestration
layer between passive UI components, domain services, and application state.

```
Page (Layer 1)        -- thin wiring, adapter creation, fragment setup
  |
Controller (Layer 2)  -- orchestration, state reads, action dispatch
  |
Component (Layer 3)   -- widget rendering, returns user selections
  |
ApplicationAPI        -- domain operations facade
```

Three plot controllers manage the full plot lifecycle on the **Manage Plots** page:

| Controller | File | Responsibility |
|---|---|---|
| `PlotCreationController` | `src/web/controllers/plot/creation_controller.py` | Create, select, rename, delete, duplicate plots |
| `PipelineController` | `src/web/controllers/plot/pipeline_controller.py` | Add, remove, reorder shapers; finalize pipeline |
| `PlotRenderController` | `src/web/controllers/plot/render_controller.py` | Config gathering, figure generation, caching, chart display |

All three controllers are **stateless**. They are instantiated fresh on every Streamlit
rerun, receive dependencies via constructor injection, and hold no mutable state of
their own. Persistent state lives in `ApplicationAPI.state_manager` (domain) or
`UIStateManager` (transient UI).

Controllers use Streamlit directly only for flow control (`st.rerun()`), error display
(`st.exception()`), and non-blocking notifications (`st.toast()`). All widget rendering
is delegated to the Component layer.

---

## PlotCreationController

`PlotCreationController` manages which plots exist and which plot is currently selected.
It does not handle pipeline editing, config gathering, or rendering.

### Constructor

```python
class PlotCreationController:
    def __init__(
        self,
        api: ApplicationAPI,
        ui_state: UIStateManager,
        lifecycle: PlotLifecycleService,   # Protocol
        registry: PlotTypeRegistry,        # Protocol
    ) -> None
```

### Methods

**`render_create_section()`** renders the "Create New Plot" form. It delegates widget
rendering to `PlotCreationComponent.render()`, which returns a dict with `name`,
`plot_type`, and `create_clicked`. When the user clicks create, the controller calls
`self._lifecycle.create_plot()` and triggers `st.rerun()`.

**`render_selector()`** renders plot selector pills via `PlotSelectorComponent`. It
returns the selected `RenderablePlot` or `None` if no plots exist. When the selection
changes, it updates `state_manager.set_current_plot_id()`.

**`render_controls(plot)`** renders rename, delete, and duplicate controls via
`PlotControlsComponent`. It handles each action directly:
- **Rename**: assigns the new name to `plot.name`.
- **Delete**: calls `ui_state.plot.cleanup()` to clear transient UI state, then
  `lifecycle.delete_plot()`, then `st.rerun()`.
- **Duplicate**: calls `lifecycle.duplicate_plot()`, then `st.rerun()`.

### Column Validation

Plot creation validates the user's selections before dispatching to the lifecycle
service. The `create_clicked` action only fires when both the `name` field is populated
and a `plot_type` has been selected from the registry. The check
`if result["create_clicked"] and result["plot_type"]` guards against creating a plot
with no type assigned.

---

## PipelineController

`PipelineController` manages the data transformation pipeline for a plot. It handles
adding, removing, and reordering shaper steps, computing intermediate data at each
step, and finalizing (applying the full pipeline to raw data).

### Constructor

```python
class PipelineController:
    def __init__(
        self,
        api: ApplicationAPI,
        ui_state: UIStateManager,
        pipeline_executor: PipelineExecutor,   # Protocol
    ) -> None
```

### Main Entry Point

The `render(plot)` method orchestrates the full pipeline editor:

1. Renders the section header via `PipelineComponent`.
2. Reads raw data from `self._api.state_manager.get_data()`. If no data is uploaded,
   it renders a warning and returns early.
3. Renders an "Add shaper" selector. When clicked, appends a new step to
   `plot.pipeline` with an empty config and increments `plot.pipeline_counter`.
4. Iterates existing pipeline steps via `_handle_pipeline_steps()`.
5. Renders a "Finalize" button that triggers `_handle_finalize()`.

### Step Management

`_handle_pipeline_steps()` uses **incremental computation** to avoid O(n^2)
re-processing. A `step_input` DataFrame is threaded through the loop: each step's
output becomes the next step's input.

```python
step_input: pd.DataFrame = raw_data
for idx, shaper in enumerate(plot.pipeline):
    result = PipelineStepComponent.render_step(
        ..., step_input=step_input, ...
    )
    # Handle move-up, move-down, delete (each triggers st.rerun)
    step_output = result.get("step_output")
    if step_output is not None:
        step_input = step_output
```

Step actions (move up, move down, delete) mutate `plot.pipeline` via list swaps or
`pop()`, then call `st.rerun()`. If a step raises an exception, the error is displayed
via `st.exception()` and `step_input` is not advanced, so the next step receives the
last successfully computed data.

### Finalize

`_handle_finalize()` applies the full pipeline in one pass via
`self._pipeline.apply_shapers(raw_data, configs)` and stores the result in
`plot.processed_data`. On failure, it renders the error through
`PipelineStepComponent.render_finalize_error()`.

---

## PlotRenderController

`PlotRenderController` orchestrates the visualization section: config gathering, figure
generation with caching, engine delegation, and chart display. It does not handle
pipeline editing or plot lifecycle.

### Constructor

```python
class PlotRenderController:
    def __init__(
        self,
        api: ApplicationAPI,
        ui_state: UIStateManager,
        lifecycle: PlotLifecycleService,   # Protocol
        registry: PlotTypeRegistry,        # Protocol
    ) -> None
```

### Render Orchestration

The `render(plot)` method follows a fixed sequence:

1. **Guard**: returns early with a warning if `plot.processed_data` is `None`.
2. **Plot type selector**: renders a `st.selectbox` with types from the registry.
   If the type changes, calls `lifecycle.change_plot_type()` and reruns.
3. **Type-specific config**: calls `plot.render_config_ui(data, saved_config)`.
4. **Advanced and theme config**: toggles via `st.toggle` and `render_settings_pills`,
   then calls `plot.render_settings_section()`.
5. **Config change detection**: compares `current_config` against `saved_config`.
6. **Refresh controls**: delegates to `ChartDisplayComponent.render_refresh_controls()`.
7. **Visualization**: calls `_render_visualization()`.

### Engine Delegation

`_render_visualization()` presents an engine selector via
`ChartDisplayComponent.render_engine_selector()`. The two supported engines are
**Plotly** (interactive) and **Matplotlib** (static). The choice is stored through
`EngineManager.set_engine()` in session state.

For Plotly, the component returns relayout event data (zoom, pan, legend drag). The
controller deduplicates events by comparing against the last stored event and calls
`plot.update_from_relayout()` when new interaction data is detected.

For Matplotlib, the controller passes pre-computed trace data when available, enabling
the component to render a static equivalent of the Plotly figure.

### Caching

Figure caching uses content-addressable keys computed from three inputs:

```python
cache_key = f"plot_{plot_id}_{config_hash}_{data_hash}"
```

- **Config hash**: MD5 of the config dict serialized as JSON, excluding transient keys
  (`xaxis_range`, `yaxis_range`) so zoom/pan does not invalidate the cache.
- **Data hash**: A fast fingerprint using DataFrame shape, column names, and first/last
  row values. This avoids hashing the entire DataFrame while still detecting changes.

On render, the controller checks the cache first. On a miss, it generates the figure
via `plot.create_figure()` and `plot.apply_common_layout()`, applies legend label
renaming, and stores the result in both `plot.last_generated_fig` and the LRU cache.

---

## Controller-Component Interaction Pattern

Controllers and components follow a strict contract. Components are **passive**: they
render Streamlit widgets and return typed dicts describing user actions. Components
never mutate state, call APIs, or trigger reruns.

The interaction flow for every user action is:

```
Controller calls Component.render(...)
  -> Component renders widgets and returns dict of user selections
Controller inspects the returned dict
  -> If an action is indicated, controller performs the operation
  -> Controller updates state via ApplicationAPI or UIStateManager
  -> Controller calls st.rerun() if the page must refresh
```

For example, in `PlotCreationController.render_controls()`:

```python
actions = PlotControlsComponent.render(plot_id=plot.plot_id, current_name=plot.name)

if actions["new_name"] != plot.name:
    plot.name = actions["new_name"]

if actions["delete_clicked"]:
    self._ui.plot.cleanup(plot.plot_id)
    self._lifecycle.delete_plot(plot.plot_id, self._api.state_manager)
    st.rerun()
```

The component returns what the user wants; the controller decides what to do about it.

---

## How Controllers Use ApplicationAPI

Controllers access domain state exclusively through `ApplicationAPI`. The API object is
injected at construction and stored as `self._api`. Common access patterns include:

| Access | Method | Used By |
|---|---|---|
| Read uploaded data | `self._api.state_manager.get_data()` | `PipelineController` |
| Read all plots | `self._api.state_manager.get_plots()` | `PlotCreationController` |
| Read/write current plot ID | `get_current_plot_id()` / `set_current_plot_id()` | `PlotCreationController` |
| Read plot counter | `self._api.state_manager.get_plot_counter()` | `PlotCreationController` |

Controllers never call `ApplicationAPI` methods for rendering. All domain mutations
(create, delete, duplicate, change type) flow through injected protocol services
(`PlotLifecycleService`, `PipelineExecutor`) rather than calling `ApplicationAPI`
directly for those operations.

Adapters, created at the page level, bridge the protocol contracts to concrete service
implementations:

```python
# manage_plots.py (page layer)
lifecycle = PlotLifecycleAdapter()       # wraps PlotService static methods
registry  = PlotTypeRegistryAdapter()    # wraps PlotFactory class methods
executor  = PipelineExecutorAdapter()    # wraps standalone shaper functions

creation = PlotCreationController(api, ui_state, lifecycle, registry)
pipeline = PipelineController(api, ui_state, executor)
render   = PlotRenderController(api, ui_state, lifecycle, registry)
```

This separation means controllers are testable with mocked dependencies and decoupled
from the concrete `PlotService`, `PlotFactory`, and shaper function implementations.

---

## See Also

- `src/web/pages/manage_plots.py` -- page layer that wires adapters and controllers
- `src/web/pages/plot_adapters.py` -- adapter implementations bridging concrete services to protocols
- `src/web/models/plot_protocols.py` -- protocol definitions (`PlotHandle`, `RenderablePlot`, `PlotLifecycleService`, `PlotTypeRegistry`, `PipelineExecutor`)
- `src/web/state/ui_state_manager.py` -- transient UI state manager used by controllers
- `src/core/application_api.py` -- domain operations facade
- `src/web/components/common/` -- component implementations called by controllers
