---
layout: default
title: Add a Renderer
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 4
permalink: /developer-guide/extension-guides/adding-a-renderer/
redirect_from:
  - /engineering-reference/development/adding-a-renderer/
---

# Add a renderer

A renderer consumes typed traces and a fully resolved `FigureConfig`. Adding an engine affects core
engine typing, web selection, headless rendering, export, and portfolio replay; treat it as a
cross-cutting compatibility change.

## Implement the connector

1. Add the engine value to `src/core/models/visualization/engine.py` and update exhaustive engine
   selection in `src/web/rendering/engine_manager.py`.
2. Implement trace translation and a stateless figure-configuration connector under
   `src/web/rendering/`.
3. Follow the styling order in `src/web/rendering/_connector_protocol.py`. Connectors receive
   resolved configuration and must not implement inheritance sentinels themselves.
4. Update the UI render branch and lifecycle in `src/web/components/common/chart_display.py`.
5. Add supported byte formats, MIME types, extensions, and dependency failures in
   `src/web/rendering/figure_export.py` and its download component.
6. Update `ring5._render`, `ring5._export`, portfolio defaults, CLI choices, and public engine types.

Do not import the new backend from core models or services. If the renderer cannot express a trace
or setting, report or test the limitation instead of silently dropping it.

## Test and verify

Add configuration round-trip tests, trace translation tests, connector-order tests, export tests,
headless API tests, portfolio replay tests, and a UI engine-selection test. Compare representative
plots with existing engines for semantics rather than pixel identity.

```bash
make arch-check
make quality-gate
make test
make test-e2e
```
