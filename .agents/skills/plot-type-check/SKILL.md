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
1. **BasePlot contract** — the class subclasses `BasePlot` and implements the plot hooks:
   - `create_traces(self, data, config) -> TraceBuildResult`
   - `render_config_ui(self, data, saved_config) -> PlotConfig`
   `create_figure()` and `apply_common_layout()` are inherited. (`GroupedStackedBarPlot`
   extends `StackedBarPlot`, not `BasePlot` directly — that's allowed.)
2. **Engine-agnostic** — the plot builds `TraceConfig`/`TraceBuildResult` only. **No `go.*` and no
   `plt.*` inside the plot class.** Styling is not the plot's job (it lives in `FigureConfig` + the
   connectors — see `rendering-figureconfig`).
3. **Constructor** calls `super().__init__(plot_id, name, "my_plot")` with its exact registry ID.
4. **Registered (snake_case)** — present in `PlotFactory._plot_classes` with a snake_case key
   (`grouped_bar`, not `groupedBar` — shapers use camelCase, plots use snake_case) **and** a matching
   `_plot_metadata` entry (`display_name`, `icon`, `category` ∈ `basic|comparison|distribution`).
5. **Exported** from `src/web/pages/ui/plotting/types/__init__.py` (so registration runs).
6. **Dual-engine** — configured and restored plots render through public
   `Session.render(plot, engine="plotly")` and `Session.render(plot, engine="matplotlib")`;
   the trace converters are `trace_to_plotly.py` / `matplotlib_trace_renderer.py`.
7. **Config UI** — if it needs options beyond the shared X/Y/color selectors, a component under
   `src/web/components/plotting/config/` is wired via `plot_config_ui.py`/`PlotConfigUIMixin`, with
   per-plot widget keys from `WidgetKeyBuilder.plot_key(plot_id, "widgets.<field>")`.
8. **Serialization round-trips** — `BasePlot.to_dict` + `PlotFactory.from_dict` rebuild state.
   Plot tables use the shared typed table codec; persistent fields are admitted by
   `src/core/common/plot_payload.py` and explicitly restored.
9. **Conventions** — default palette `wong`; error-bar column is `{y}.sd`.
10. **Coverage** — there is a unit test exercising `create_traces`/`create_figure` with `sample_data`.
    Every registered built-in, including `dual_axis_bar_dot`, participates in dual-engine catalog
    and restored-portfolio rendering tests.

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
- New conformance failure caught in review? Add its check here and to `add-plot-type` when it affects
  implementation. Document durable contracts in the repository developer guide.

## Verify after
`make arch-check && ./python_venv/bin/mypy src/ && ./python_venv/bin/pytest tests/unit -k plot -q`
