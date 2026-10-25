---
layout: default
title: Add a Plot Type
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 2
permalink: /developer-guide/extension-guides/adding-a-plot-type/
---

# Add a plot type

Copy the nearest implementation under `src/web/pages/ui/plotting/types/`. A plot maps a DataFrame
and configuration to `TraceBuildResult`; it does not construct Plotly or Matplotlib marks.

## Implement and register

<!--
`uman~ring5.extension.plot-registry.documentation~1`

Covers:
- req~ring5.extension.plot-registry~1

-->

1. Subclass `BasePlot`, pass a snake-case identifier to its constructor, and implement
   `create_traces` and `render_config_ui`. Call `super().__init__(plot_id, name, "my_plot")`.
2. Return trace models from `src/core/models/visualization/`. Keep styling in figure configuration
   and connectors.
3. Export the class from `src/web/pages/ui/plotting/types/__init__.py`.
4. Add the constructor and matching metadata to `PlotFactory` in
   `src/web/pages/ui/plotting/plot_factory.py`.
5. Reuse common mapping components. Add a focused component under
   `src/web/components/plotting/config/` only for new fields, with per-plot widget keys.
6. Keep additional state serializable through `BasePlot.to_dict` and portfolio restore. Plot
   tables use the shared typed table codec; do not introduce another table representation.
   Persistent fields require coordinated additions to the writer, `plot_payload.py` field contract
   and `PlotFactory.from_dict` restoration.

The registry identifier is stored in portfolios and accepted by the public API. Use its exact
canonical spelling. A rename replaces all producers, consumers and fixtures without an alias.

Emit concrete neutral trace families from `create_traces`. Both renderers validate the complete
trace sequence before drawing, including hidden traces. A bare `TraceConfig` or an unsupported
family raises `TypeError`; public `Session.render` exposes the failure as `ring5.RenderError`.
Histograms use the shared bucket geometry and emit `BarTraceConfig` with explicit positions and
widths. Supported trace families may be subclassed by registered plot implementations.

## Test and verify

Unit-test trace values, ordering, missing columns, and error-bar behavior. Use `Session.render` to
render configured plots through both Plotly and Matplotlib, including plots restored from a
portfolio. `BasePlot.create_figure` prepares Plotly traces and `apply_common_layout` applies shared
styling; headless clients use the public session to run the complete rendering sequence. Add
integration coverage for non-trivial configuration or public API use.

```bash
make arch-check
python_venv/bin/mypy src ring5
make test-unit
```

Do not add backend branches inside the plot merely to fix a style difference; update both rendering
connectors at the relevant styling step.
