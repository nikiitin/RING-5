---
name: plot-type-check
description: Gate that a plot type is correctly implemented in RING-5 — BasePlot contract, engine-agnostic traces, PlotFactory registration, dual-engine render, config UI, serialization. Use to verify a new/changed chart type before merging (complements the add-plot-type build skill).
---

# Plot-type check (the chart conformance gate)

A plot type is correct only if it is **engine-agnostic** and fully wired. To *build* one use the
`add-plot-type` skill; this skill verifies the result. Types live in
`src/web/pages/ui/plotting/types/`; the registry is
`src/web/pages/ui/plotting/plot_factory.py::PlotFactory`.

## Checklist
1. **BasePlot contract** — the class subclasses `BasePlot` and implements **both** abstract methods:
   - `create_traces(self, data, config) -> TraceBuildResult`
   - `get_legend_column(self, config) -> str | None`
   `create_figure()` is inherited — only overridden with good reason. (`GroupedStackedBarPlot`
   extends `StackedBarPlot`, not `BasePlot` directly — that's allowed.)
2. **Engine-agnostic** — the plot builds `TraceConfig`/`TraceBuildResult` only. **No `go.*` and no
   `plt.*` inside the plot class.** Styling is not the plot's job (it lives in `FigureConfig` + the
   connectors — see `rendering-figureconfig`).
3. **`plot_type` set before `super().__init__`** in `__init__`.
4. **Registered (snake_case)** — present in `PlotFactory._plot_classes` with a snake_case key
   (`grouped_bar`, not `groupedBar` — shapers use camelCase, plots use snake_case) **and** a matching
   `_plot_metadata` entry (`display_name`, `icon`, `category` ∈ `basic|comparison|distribution`).
5. **Exported** from `src/web/pages/ui/plotting/types/__init__.py` (so registration runs).
6. **Dual-engine** — renders under both Plotly and Matplotlib (toggle `ring5_engine_mode`); the trace
   converters are `trace_to_plotly.py` / `matplotlib_trace_renderer.py`.
7. **Config UI** — if it needs options beyond the shared X/Y/color selectors, a component under
   `src/web/components/plotting/config/` is wired via `plot_config_ui.py`/`PlotConfigUIMixin`, with
   per-plot-unique widget keys `f"{prefix}_{field}_{plot_id}"`.
8. **Serialization round-trips** — `BasePlot.to_dict`/`from_dict` + `PlotFactory` rebuild it; any new
   state is plain/JSON-serializable so portfolios survive save/load.
9. **Conventions** — default palette `wong`; error-bar column is `{y}.sd`.
10. **Coverage** — there is a unit test exercising `create_traces`/`create_figure` with `sample_data`.
    `dual_axis_bar_dot` is WIP and intentionally excluded from coverage — don't count it as a model.

```bash
# registry sanity
grep -n "_plot_classes\|_plot_metadata" src/web/pages/ui/plotting/plot_factory.py
# engine-leak smell (should be empty inside types/)
grep -rn "import plotly\|plotly.graph_objects\|matplotlib\|plt\." src/web/pages/ui/plotting/types/
```

## Keep this skill sharp
Canon, not history — edit in place when the plot contract moves:
- The abstract methods and registry shape above mirror `base_plot.py` and `plot_factory.py`. If a new
  abstract method is added or the metadata schema changes, update this checklist.
- New conformance failure caught in review? Add it here (and to `add-plot-type` if it's a build step);
  durable facts → a memory.

## Verify after
`make arch-check && ./python_venv/bin/mypy src/ && ./python_venv/bin/pytest tests/unit -k plot -q`
