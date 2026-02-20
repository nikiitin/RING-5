---
title: "Phase 5 — MVC Refactoring (Phase B)"
nav_order: 30
---

# Phase 5 — MVC Architecture Refactoring (Phase B)

## Overview

Phase B is a 10-step refactoring that established strict **MVC separation**,
eliminated bridge/adapter layers, moved visualization models to the core layer,
and introduced a typed trace pipeline. The codebase went from ~3400 tests to
3288 tests (removed tests for deleted components) with zero regressions.

## Motivation

The pre-Phase B architecture had several issues:

1. **Layer violations**: Visualization models (`FigureSpec`, connectors) lived
   in `src/core/visualization/` but depended on Plotly — a presentation concern.
2. **Excessive indirection**: `FigureEngine` → `FigureCreator` → `FigureStyler`
   → `ConfigSpecBuilder` → `ConfigBridge` chain added complexity without value.
3. **Protocol bloat**: `ChartDisplay`, `FigureCreator`, `FigureStyler` protocols
   existed for indirection that wasn't needed.
4. **Scattered services**: `src/web/services/` and `src/web/figures/` directories
   duplicated functionality already in `src/core/services/`.

## Phase Summary

| Phase | Name | What Changed |
|-------|------|-------------|
| B1 | Dead Code Removal | Deleted unused files and dead imports |
| B2 | Core Visualization Models | Renamed `specs` → `configs` (`FigureSpec` → `FigureConfig`, etc.) |
| B3 | Visualization Repository + API | Created `VisualizationRepository` and `ApplicationAPI.get/set_visualization_config()` |
| B4 | Move Connectors | Moved `src/core/visualization/connectors/` → `src/web/rendering/` |
| B5 | Widgets Dissolution | Moved widgets to `src/web/rendering/widgets/`, dissolved `src/web/services/` and `src/web/figures/` |
| B6 | Render Controller | Moved UI rendering from `PlotRenderer` into `ChartPresenter`, eliminated `ChartDisplay`/`ChartDisplayAdapter` |
| B7 | Plot Types → TraceBuildResult | All 8 plot types now produce `TraceBuildResult` via `create_traces()` |
| B8 | Eliminate Bridges | Removed `FigureEngine`, `ConfigBridge`, `FigureCreator`/`FigureStyler` protocols |
| B9 | Final Cleanup | Layer violation audit, orphan removal, export verification |
| B10 | Documentation | Updated all architecture docs to match new structure |

## Architecture After Phase B

### Core Layer (`src/core/`)

```text
src/core/
├── application_api.py              ← Facade (single entry point)
├── models/
│   ├── visualization/              ← Typed visualization models (NEW)
│   │   ├── figure_config.py            FigureConfig (was FigureSpec)
│   │   ├── axis_config.py              AxisConfig (was AxisSpec)
│   │   ├── legend_config.py            LegendConfig (was LegendSpec)
│   │   ├── typography_config.py        TypographyConfig (was TypographySpec)
│   │   ├── trace_config.py             TraceConfig (NEW - typed traces)
│   │   ├── trace_build_result.py       TraceBuildResult (NEW)
│   │   ├── annotation_config.py        AnnotationConfig
│   │   ├── data_label_config.py        DataLabelConfig
│   │   ├── series_style_config.py      SeriesStyleConfig
│   │   ├── palettes.py                 Color palettes
│   │   └── resolvers.py                Config resolution logic
│   ├── parsing_models.py
│   ├── plot_config.py
│   └── plot_protocol.py
├── state/
│   └── repositories/
│       ├── visualization_repository.py ← Per-plot FigureConfig storage (NEW)
│       └── ...
└── services/                       ← Business logic (unchanged)
```

### Web Layer (`src/web/`)

```text
src/web/
├── models/                         ← Layer 5: Pure data contracts
│   ├── plot_models.py                  8 TypedDicts
│   └── plot_protocols.py               6 Protocols (ChartDisplay REMOVED)
├── rendering/                      ← Engine connectors (MOVED from core)
│   ├── engine_manager.py               Engine dispatch
│   ├── plotly_connector.py              Plotly rendering
│   ├── matplotlib_connector.py          Matplotlib rendering
│   ├── trace_to_plotly.py               TraceBuildResult → go.Figure
│   ├── preset_applicator.py             Preset styling
│   ├── config_builder.py               Config dict → FigureConfig
│   └── widgets/                         Declarative widget system
├── controllers/plot/               ← Orchestration (MVC)
│   ├── creation_controller.py
│   ├── pipeline_controller.py
│   └── render_controller.py
├── presenters/plot/                ← Widget rendering (MVC)
│   ├── chart_presenter.py              st.plotly_chart / st.pyplot
│   ├── config_presenter.py
│   ├── controls_presenter.py
│   └── ...
├── state/
│   └── ui_state_manager.py
└── pages/
    ├── manage_plots.py                  Thin DI composition root
    ├── plot_adapters.py                 3 protocol adapters
    └── ui/plotting/
        ├── base_plot.py                 create_traces() + generate_figure()
        └── types/                       8 plot types → TraceBuildResult
```

## Key Architectural Changes

### 1. Trace-Based Pipeline (B7)

**Before**: Plot types returned `go.Figure` directly via `create_figure()`.

**After**: Plot types return `TraceBuildResult` via `create_traces()`.

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

The `TraceBuildResult` is then converted to a `go.Figure` by
`traces_to_plotly()` or to a Matplotlib figure by the matplotlib connector.

### 2. FigureEngine Elimination (B8)

**Before**: 5-layer indirection chain.
```
PlotRenderer → FigureEngine → FigureCreator → plot.create_figure()
                            → FigureStyler → ConfigSpecBuilder → ConfigBridge
```

**After**: Direct, inlined calls.
```
RenderController → plot.generate_figure()
                       ├── create_traces() → TraceBuildResult
                       ├── traces_to_plotly() → go.Figure
                       └── apply_common_layout() → styled Figure
```

### 3. Models in Core (B2-B4)

Visualization models moved from `src/core/visualization/` (which imported
Plotly) to `src/core/models/visualization/` (pure Python dataclasses, zero
engine dependencies). Connectors moved to `src/web/rendering/` where Plotly
and Matplotlib imports are appropriate.

### 4. Protocol Simplification (B6, B8)

| Removed Protocol | Reason |
|-----------------|--------|
| `ChartDisplay` | Replaced by direct `ChartPresenter` calls |
| `ChartDisplayAdapter` | Bridge no longer needed |
| `FigureCreator` | Inlined into `BasePlot.generate_figure()` |
| `FigureStyler` | Inlined into `BasePlot.generate_figure()` |

Remaining protocols (6): `PlotHandle`, `ConfigRenderer`, `RenderablePlot`,
`PlotLifecycleService`, `PlotTypeRegistry`, `PipelineExecutor`.

## Deleted Components

| Component | Phase | Replacement |
|-----------|-------|-------------|
| `src/web/figures/` | B5, B8 | Logic inlined into callers |
| `src/web/services/` | B5 | Merged into `src/core/services/` |
| `src/core/visualization/connectors/` | B4 | Moved to `src/web/rendering/` |
| `FigureEngine` | B8 | `BasePlot.generate_figure()` + `RenderController` |
| `ConfigBridge` | B8 | Dead code, no production callers |
| `PlotlyTraceExtractor` | B7 | `TraceBuildResult` pipeline |
| `ConfigSpecBuilder` | B4 | `config_builder.py` in rendering |

## Data Flow (Current)

```text
User Action (Streamlit)
    ↓
PlotRenderController._render_visualization()
    ├── api.get_plot(plot_id) → PlotHandle
    ├── plot.create_traces(data, config) → TraceBuildResult
    ├── traces_to_plotly(result) → go.Figure
    ├── plot.apply_common_layout(fig, config)
    ├── ChartPresenter.render_engine_selector() → engine choice
    ├── EngineManager.get_connector(engine) → Connector
    ├── connector.render(fig_config, traces) → Figure
    └── ChartPresenter.render_chart(figure)
```

## Test Results

| Phase | Tests | Status |
|-------|-------|--------|
| B7 | 3340 | ✅ pass |
| B8 | 3288 | ✅ pass |
| B9 | 3288 | ✅ pass |

Test count decreased from B7→B8 because tests for deleted components
(`FigureEngine`, `PlotlyTraceExtractor`, `ConfigBridge`) were removed.

## Commits

| Phase | Commit | Message |
|-------|--------|---------|
| B7 | `c79ded5` | Plot types produce TraceBuildResult |
| B8 | `8da3953` | Eliminate FigureEngine, ConfigBridge, FigureCreator/FigureStyler |
| B9 | `7d98d86` | Final cleanup + layer verification |
| B10 | — | Documentation update (this file) |

## Related Documentation

- [Architecture Overview](Architecture.md) — Updated high-level architecture
- [Web Layer Architecture](web-layer-architecture.md) — Updated 5-layer diagram
- [Phase 3 Architecture](phase3-architecture.md) — Historical FigureEngine design
- [Phase 4 Architecture](phase4-architecture.md) — Declarative widget system
