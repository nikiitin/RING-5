---
layout: default
title: Add a Plot Type
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 2
permalink: /developer-guide/extension-guides/adding-a-plot-type/
redirect_from:
  - /engineering-reference/development/adding-a-plot-type/
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
   `create_traces` plus `get_legend_column` when grouping creates legend entries.
2. Return trace models from `src/core/models/visualization/`. Keep styling in figure configuration
   and connectors.
3. Export the class from `src/web/pages/ui/plotting/types/__init__.py`.
4. Add the constructor and matching metadata to `PlotFactory` in
   `src/web/pages/ui/plotting/plot_factory.py`.
5. Reuse common mapping components. Add a focused component under
   `src/web/components/plotting/config/` only for new fields, with per-plot widget keys.
6. Ensure every new state value is JSON-compatible so `BasePlot.to_dict` and portfolio restore
   round-trip it.

The registry identifier is stored in portfolios and accepted by the public API. Renaming it later
requires a migration.

## Test and verify

Unit-test trace values, ordering, missing columns, and error-bar behavior. Render representative data
through both connectors. Add integration coverage for non-trivial configuration or public API use.

```bash
make arch-check
python_venv/bin/mypy src ring5
make test-unit
```

Do not add backend branches inside the plot merely to fix a style difference; update both rendering
connectors at the relevant styling step.
