# Phase 3 — Wire FigureEngine

> **Note (Phase B update):** `FigureEngine`, `ConfigSpecBuilder`, `FigureCreator`,
> and `FigureStyler` were **eliminated** in Phase B8. Figure creation is now
> inlined into `BasePlot.generate_figure()` and `PlotRenderController._render_visualization()`.
> Plot types produce `TraceBuildResult` via `create_traces()` instead of
> calling `FigureEngine.build()`. This document is preserved as historical
> context for Phase 3's original design.

## Overview

Phase 3 routes all figure creation through `FigureEngine` and connects
`StyleApplicator` to `FigureSpec`, establishing the engine-agnostic
visualization pipeline.

## Architecture After Phase 3

```text
┌──────────────────────────────────────────────────────────────┐
│  PlotRenderer / BasePlot.generate_figure()                   │
│    ↓ (delegates to)                                          │
│  FigureEngine.build(plot_type, data, config)                 │
│    ├─ FigureCreator.create_figure(data, config) → go.Figure  │
│    ├─ FigureStyler.apply_styles(fig, config)                 │
│    │    ├─ ConfigSpecBuilder.from_config(config) → FigureSpec │
│    │    ├─ resolve_spec(spec) → resolved FigureSpec          │
│    │    ├─ self.last_spec = resolved_spec  (stored for export)│
│    │    └─ ... existing Plotly-specific rendering unchanged   │
│    └─ _apply_legend_labels(fig, config)                      │
└──────────────────────────────────────────────────────────────┘

Export path:
  StyleApplicator.last_spec
    → FigureSpecToMatplotlib.apply(spec, ax)
    → matplotlib figure → PDF/SVG/EPS
```

## What Changed

### Step 20: Route through FigureEngine

- `plot_renderer.py`: `render_plot()` → `FigureEngine.from_plot()` → `engine.build()`
- `base_plot.py`: `generate_figure()` → `FigureEngine.from_plot()` → `engine.build()`
- Single entry point for all figure generation

### Step 21: ConfigSpecBuilder + StyleApplicator.last_spec

- `connectors/builders.py`: New `ConfigSpecBuilder.from_config(config, plot_type)` (130 lines)
  - Maps flat config dict → FigureSpec dataclass tree
  - `dpi=1` trick: pixel values pass through inches without loss
- `applicator.py`: Builds and stores `self.last_spec` on every `apply_styles()` call
- Existing Plotly rendering remains unchanged (dual-write approach)

### Step 22: PlotConfig type alias

- `plot_models.py`: Expanded `PlotDisplayConfig` with ~60 missing keys, added `PlotConfig` alias
- `base_plot.py`: `self.config: PlotConfig` (was `Dict[str, Any]`)
- `protocols.py`: `FigureCreator`/`FigureStyler` signatures use `PlotConfig`

### Step 24: Integration tests (11 tests)

- End-to-end `FigureEngine.build()` with real `StyleApplicator`
- Config → spec → Plotly layout property agreement
- `last_spec` populated after `engine.build()`
- Spec serialization round-trip
- Multi-type engine dispatch

### Step 25: Code health

- Fixed duplicate `grid_color` key in `PlotDisplayConfig`
- mypy strict: 0 errors on all new code (pre-existing `grouped_stacked_bar_plot.py:113` excluded)
- Dead code scan: all imports consumed, no orphans

## Test Summary

| Suite      | Tests  | Status   |
| ---------- | ------ | -------- |
| Full suite | 3305   | ✅ pass  |
| Skipped    | 2      | —        |
| Coverage   | 90.39% | ≥ 90% ✅ |

## Files Modified (10 tracked, 16 untracked)

### Source (modified)

- `src/core/visualization/connectors/__init__.py` — export ConfigSpecBuilder
- `src/core/visualization/connectors/builders.py` — +151 lines (ConfigSpecBuilder)
- `src/web/figures/protocols.py` — PlotConfig signatures
- `src/web/models/plot_models.py` — +75 lines (expanded TypedDict + PlotConfig)
- `src/web/pages/ui/plotting/base_plot.py` — FigureEngine routing + PlotConfig
- `src/web/pages/ui/plotting/plot_renderer.py` — FigureEngine routing
- `src/web/pages/ui/plotting/styles/applicator.py` — last_spec + ConfigSpecBuilder
- `src/web/pages/ui/plotting/export/converters/impl/layout_applier.py` — legend3 fix
- `src/web/pages/ui/plotting/export/converters/impl/matplotlib_converter.py` — FigureSpec legends

### Source (new — Phase 2 widgets)

- `src/core/visualization/widgets/` — 4 files (widget_def, widget_renderer, config_bridge)

### Tests (new)

- `tests/unit/core/visualization/` — 10 test files (spec, resolvers, connectors, widgets, etc.)
- `tests/integration/test_phase3_figure_engine.py` — 11 integration tests

## Recommended Commits

```text
[Phase 1 / Step 6]     Tests for FigureSpec module
[Phase 1 / Step 10-11] Export pipeline + legend3 spacing fix
[Phase 2]              Declarative widget system
[Phase 3 / Step 20-22] FigureEngine wiring + ConfigSpecBuilder
[Phase 3 / Step 24-25] Integration tests + code health
```
