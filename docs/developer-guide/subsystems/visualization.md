---
layout: default
title: Visualization Subsystem
parent: Subsystems
grand_parent: Developer Guide
nav_order: 3
permalink: /developer-guide/subsystems/visualization/
---

# Visualization subsystem

Visualization separates data mapping, styling, and backend translation.

```mermaid
flowchart LR
    DATA[Processed DataFrame] --> PLOT[BasePlot.create_traces]
    PLOT --> TRACES[TraceBuildResult]
    FLAT[Flat plot config] --> BUILDER[Config builder]
    BUILDER --> CONFIG[FigureConfig]
    CONFIG --> RESOLVE[Config resolver]
    TRACES --> PLOTLY[Plotly connector]
    RESOLVE --> PLOTLY
    TRACES --> MPL[Matplotlib connector]
    RESOLVE --> MPL
    PLOTLY --> EXPORT[Engine-aware exporter]
    MPL --> EXPORT
```

## Engine-independent traces

<!--
`uman~ring5.render.engine-independent-traces.documentation~1`

Covers:
- req~ring5.render.engine-independent-traces~1

-->

Every registered plot type produces a typed `TraceBuildResult` before backend rendering. It carries
concrete trace families plus backend-neutral separators, shaded regions, rules, typed
`AnnotationConfig` entries, tick positions, and secondary-axis metadata. Histogram plots emit bar
traces with shared measured bucket geometry.

`src/web/rendering/figure_preparation.py::prepare_figure` owns effective semantic/accessibility
configuration, one trace callback, non-color encoding and relabeling, and one typed styling
build/resolve. It returns an owned `PreparedFigure` without constructing native figures.
`BasePlot.create_figure` and the single-plot Plotly report route use this preparation. Numbered
annotations carry their semantic legend role; the central resolver applies inherited font sizes.

Plot types live under `src/web/pages/ui/plotting/types/` because their configuration UI and current
composition are web-owned. They emit models from `src/core/models/visualization/` and do not create
backend marks directly.

`src/web/rendering/config_builder.py` maps persisted flat configuration into `FigureConfig`.
`src/core/services/visualization/config_resolver.py` replaces inheritance sentinels on a copy before
a connector runs. Plotly and Matplotlib connectors apply the same ordered styling contract; trace
renderers handle mark-specific translation.

Export bytes are produced by `src/web/rendering/figure_export.py` and shared by the download UI and
the `ring5` facade. The UI owns Matplotlib figure lifecycle and session caches; connectors remain
stateless and do not close caller-owned figures.

When adding a visual setting, update its model round trip, builder, UI, both connectors, and public
`FigureSpec` when it belongs to the supported scripting surface. See
[Add a Renderer]({{site.baseurl}}/developer-guide/extension-guides/adding-a-renderer/).
