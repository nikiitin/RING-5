---
layout: default
title: Add a Renderer
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 4
permalink: /developer-guide/extension-guides/adding-a-renderer/
---

# Add a renderer

A renderer consumes typed traces and a fully resolved `FigureConfig`. Adding an engine affects core
engine typing, web selection, headless rendering, export, and portfolio replay; treat it as a
cross-cutting compatibility change.

## Implement the connector

<!--
`uman~ring5.extension.render-connector.documentation~1`

Covers:
- req~ring5.extension.render-connector~1

-->

1. Add the engine value to `src/core/models/visualization/engine.py` and update exhaustive engine
   selection in `src/web/rendering/engine_manager.py`.
2. Implement trace translation and a stateless figure-configuration connector under
   `src/web/rendering/`. Retain explicit source-to-native associations in the engine result.
3. Follow the styling order in `src/web/rendering/_connector_protocol.py`. Connectors receive
   resolved configuration and must not implement inheritance sentinels themselves.
4. Wire native construction into `plot_renderer.py` and `dashboard_builder.py`. Chart display
   consumes the complete artifact; it does not construct another figure or retain another cache.
5. Add supported byte formats, MIME types, extensions, and dependency failures in
   `src/web/rendering/figure_export.py` and its download component.
6. Update `ring5._render`, `ring5._export`, portfolio defaults, CLI choices, and public engine types.

Do not import the new backend from core models or services. If the renderer cannot express a trace
or setting, report or test the limitation instead of silently dropping it.

## Native result ownership

`prepare_figure` produces owned neutral traces and resolved styling once. `build_plotly_figure`
returns `PlotlyRenderResult`; `build_matplotlib_figure_from_prepared` returns
`MatplotlibFigureResult`. Both expose `.figure`. Their connector `apply(spec, result)` methods
return `None` and preflight the entire supplied root before changing style or text. Matplotlib's
internal panel operations receive one required `MatplotlibRenderResult` and derive its axes.

Each binding retains the original panel source ordinal, raw name, group and legend role together
with actual inserted traces or owned artists. Native artist discovery and current display names
do not establish source identity. Preserve raw names through construction and style lookup;
`FigureConfig.legend_labels` projects display text afterward. Positional styles use emission slots,
including hidden sources. A rename never changes style keys, source values or legend-group identity.

Plotly generated facet titles use reserved ordinal annotation role names, with the corresponding
source association held in the result. Missing or duplicated owned roles fail visibly. Compositors
transfer associations to actual copied destination traces and panel roles. Direct native copies
require explicit associations for connector restyling; they cannot reuse the original result or recover identities
from aliased text. Foreign decorations remain outside the owned source set.

The result owns generated legend/colorbar outputs. Reapply updates existing owned outputs; a
structural colorbar change checks current callback/backlink and layout generation before removal.
Automatic-layout motion remains valid while that engine owns the participant. Foreign adoption or
layout divergence requires a fresh generation, without guessed reparenting or accumulated shrink.
Shared legends merge only equal original identity, role/group and known final native glyphs;
unsupported glyph state keeps separate entries.

These are internal renderer contracts. Figure scripts use `ring5.Session`, which returns the
selected engine's native figure. Exports consume fully styled figures and do not need bindings.

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
