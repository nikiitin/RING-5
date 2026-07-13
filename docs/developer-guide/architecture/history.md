---
title: "Architecture History"
parent: Architecture
grand_parent: Developer Guide
nav_order: 9
---

# Architecture History

> **This page is a historical record, not current API.**
> It documents the major refactors the RING-5 visualization stack went through.
> Paths and components described here may reflect *past* states of the codebase
> and are intentionally written in the past tense ("X was moved to Y").
>
> For the **current** architecture, see:
> - [Architecture Overview](overview.md)
> - [Layer Boundaries](layer-boundaries.md)

The codebase evolved through three major phases. Each established a piece of the
engine-agnostic visualization pipeline, and the final phase consolidated the
layering by removing indirection and merging duplicated service code into the
core layer.

| Phase | Theme | Net effect |
| ----- | ----- | ---------- |
| Phase 3 | FigureEngine wiring | A single entry point for figure creation and an engine-agnostic spec/config tree (later inlined away). |
| Phase 4 | Declarative widget system | UI controls expressed as declarative widget sections instead of hand-coded Streamlit calls. |
| Phase 5 | Component/Controller refactor | Strict layer separation, removal of indirection layers, models moved to the core layer, a typed trace pipeline, and the **dissolution of the web services directory into the core services layer**. |

---

## Phase 3 — Wire FigureEngine

### What changed and why

Phase 3 routed all figure creation through a central `FigureEngine` and connected
the style applicator to a `FigureSpec`, establishing the first engine-agnostic
visualization pipeline. The motivation was to have **one entry point** for every
figure that any plot type or renderer produced, instead of scattered, plot-specific
figure construction.

Conceptually the pipeline at the end of Phase 3 looked like this:

```text
PlotRenderer / BasePlot.generate_figure()
   ↓ delegates to
FigureEngine.build(plot_type, data, config)
   ├─ FigureCreator.create_figure(data, config) → go.Figure
   ├─ FigureStyler.apply_styles(fig, config)
   │    ├─ ConfigSpecBuilder.from_config(config) → FigureSpec
   │    ├─ resolve_spec(spec) → resolved FigureSpec
   │    └─ store last_spec (for export)
   └─ apply legend labels
```

Key additions:

- **Single figure entry point.** `render_plot()` and `generate_figure()` both
  routed through `FigureEngine`.
- **`ConfigSpecBuilder`.** Mapped a flat config dictionary into a `FigureSpec`
  dataclass tree, so styling could be described declaratively and reused for
  export (PDF/SVG/EPS via a matplotlib conversion path).
- **A `PlotConfig` type.** The previously untyped config dict was given a typed
  contract, expanding the display-config keys and using it consistently across
  the figure-creation signatures.
- **Dual-write approach.** Existing Plotly-specific rendering was left unchanged
  while the spec tree was built alongside it, de-risking the migration.

### Note

The `FigureEngine`, `ConfigSpecBuilder`, `FigureCreator`, and `FigureStyler`
abstractions introduced here were **later eliminated in Phase 5**. Figure creation
was inlined into `BasePlot.generate_figure()` and the plot render controller, and
plot types began producing a `TraceBuildResult` instead of calling
`FigureEngine.build()`. Phase 3 is preserved here for context on the original design.

---

## Phase 4 — Declarative Widget System

### What changed and why

Phase 4 introduced a **declarative widget system** for the styling UI. Instead of
hand-coding each Streamlit control, sections of the controls UI were described as
declarative widget definitions that a `WidgetRenderer` turned into widgets. The
goal was to shrink and standardize the UI code and prove a migration path away
from large blocks of imperative Streamlit calls.

The first section wired through the renderer was the legend-sizing section, which
shrank substantially once expressed declaratively. The renderer coexisted with
hand-coded sections that still needed bespoke UX (multi-column layouts, conditional
rendering, and dynamic per-series widgets).

Highlights:

- **Aligned defaults.** Standard declarative sections were aligned with the
  production defaults of the existing hand-coded UI (layout dimensions, margins,
  typography, backgrounds, axis colors, tick fonts).
- **Granular sections.** Legend configuration was split into position, appearance,
  and sizing sub-sections, with a convenience aggregate that combined them. New
  sections for data labels and margins were added.
- **A planned migration ladder.** Future tiers were sketched for column-layout
  support, conditional visibility (`visible_when` predicates), and dynamic/repeater
  sections for per-series controls.

### Note

The declarative widget definitions and `WidgetRenderer` were originally placed in
`src/core/visualization/widgets/`. They were later moved to
`src/web/rendering/widgets/` during the Phase 5 refactor (and the `ConfigBridge`
helper was removed). The declarative widget system remained functional at its new
location.

---

## Phase 5 — Component/Controller Refactor (removal of the presenter layer)

### What changed and why

Phase 5 was a multi-step refactor that established **strict layer separation**,
eliminated bridge/adapter indirection, moved visualization models into the core
layer, introduced a typed trace pipeline, and **dissolved the web services
directory into the core services layer**.

The pre-Phase 5 architecture had accumulated several problems:

1. **Layer violations.** Visualization models (`FigureSpec`, connectors) lived
   under `src/core/visualization/` but depended on Plotly — a presentation
   concern leaking into the core layer.
2. **Excessive indirection.** The `FigureEngine → FigureCreator → FigureStyler →
   ConfigSpecBuilder → ConfigBridge` chain added complexity without value.
3. **Protocol bloat.** Several protocols existed only to support indirection that
   was no longer needed.
4. **Scattered services.** A `src/web/services/` directory (and a `src/web/figures/`
   directory) duplicated functionality that already belonged in
   `src/core/services/`.

### Major moves

**Visualization models moved to the core layer.** The spec dataclasses were
renamed to configs and relocated from the Plotly-importing
`src/core/visualization/` into the pure-Python `src/core/models/visualization/`
(zero engine dependencies). `FigureSpec` became `FigureConfig`, and the axis,
legend, and typography specs became their config equivalents. A
`VisualizationRepository` (per-plot `FigureConfig` storage) and corresponding
`ApplicationAPI` accessors were added.

**Rendering connectors moved to the web layer.** The connectors moved from
`src/core/visualization/connectors/` to `src/web/rendering/`, where Plotly and
Matplotlib imports are appropriate. The current connectors live there as
`plotly_connector.py`, `matplotlib_connector.py`, `trace_to_plotly.py`, and
`matplotlib_trace_renderer.py`. The flat-config-to-`FigureConfig` builder replaced
the old `ConfigSpecBuilder`.

**Typed trace pipeline.** Plot types stopped returning a Plotly `go.Figure`
directly and instead produced a `TraceBuildResult` of typed `TraceConfig` objects
via `create_traces()`. The result is converted to a Plotly figure (or a Matplotlib
figure) by the rendering connectors, making the pipeline engine-agnostic:

```python
# Before (tight coupling to Plotly)
class BarPlot(BasePlot):
    def create_figure(self, data, config) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Bar(...))
        return fig

# After (engine-agnostic)
class BarPlot(BasePlot):
    def create_traces(self, data, config) -> TraceBuildResult:
        traces = [TraceConfig(name="x", x=[...], y=[...], trace_type="bar")]
        return TraceBuildResult(traces=traces, barmode="group")
```

**FigureEngine eliminated.** The five-layer indirection chain was replaced with
direct, inlined calls. Figure creation now happens inside
`BasePlot.generate_figure()` and the plot render controller:

```text
RenderController → plot.generate_figure()
                       ├── create_traces() → TraceBuildResult
                       ├── traces → go.Figure (via rendering connector)
                       └── apply_common_layout() → styled Figure
```

### The presenter layer was removed in favor of Components + Controllers

The most consequential change in this refactor was the move to a
**Components + Controllers** UI model. There is **no presenter layer** in the
current architecture.

- **Components** live in `src/web/components/` and own widget rendering — drawing
  Streamlit/visualization output (for example, the chart-display component renders
  the figure and the engine selector). The component that displays a chart is
  `ChartDisplayComponent` in `src/web/components/common/chart_display.py`.
- **Controllers** live in `src/web/controllers/plot/` and orchestrate the work,
  split into creation, pipeline, and render responsibilities.

The figure-creation indirection that the old engine layer provided was inlined,
and the bridge/adapter protocols that only existed to support it were deleted.

### Services dissolved into the core layer

The duplicated `src/web/services/` directory (and the related `src/web/figures/`
directory) was **dissolved**: its logic was merged into the core services layer at
`src/core/services/` (organized into `data_services/`, `managers/`, and
`visualization/`). Business logic now lives in the core layer, with the web layer
limited to components, controllers, rendering connectors, and UI state
(`src/web/state/ui_state_manager.py`).

### Summary of what this phase deleted

| Removed | Replacement |
| ------- | ----------- |
| `src/web/figures/` | Logic inlined into callers |
| `src/web/services/` | Merged into `src/core/services/` |
| `src/core/visualization/connectors/` | Moved to `src/web/rendering/` |
| `FigureEngine` | `BasePlot.generate_figure()` + the render controller |
| `FigureCreator` / `FigureStyler` | Inlined into `BasePlot.generate_figure()` |
| `ConfigBridge` | Dead code, removed |
| `ConfigSpecBuilder` | Config builder in `src/web/rendering/` |
| Presenter layer | Components (`src/web/components/`) + Controllers (`src/web/controllers/plot/`) |

---

## Where to look now

After these phases, the live architecture is:

- **Facade:** `src/core/application_api.py::ApplicationAPI` — single entry point.
- **Models:** `FigureConfig` and related configs in `src/core/models/visualization/`.
- **Rendering connectors:** `src/web/rendering/` (`plotly_connector.py`,
  `matplotlib_connector.py`, `trace_to_plotly.py`, `matplotlib_trace_renderer.py`),
  driven by the 16-step `STYLING_PIPELINE_ORDER` in
  `src/web/rendering/_connector_protocol.py`.
- **Plotting:** `src/web/pages/ui/plotting/` (`plot_factory.py`, `base_plot.py`,
  `types/`, `styles/`, `plot_renderer.py`).
- **Services:** `src/core/services/` (`data_services/`, `managers/`,
  `visualization/`).
- **Shapers:** `src/core/services/shapers/`, with UI configs in
  `src/web/components/shapers/`.
- **State:** core state in `src/core/state/`; UI state in
  `src/web/state/ui_state_manager.py`.
- **UI:** Components (`src/web/components/`) + Controllers
  (`src/web/controllers/plot/`).

For full, current detail, start with the
[Architecture Overview](overview.md) and the
[Layer Boundaries](layer-boundaries.md) page. To check test status, `run make test`.
