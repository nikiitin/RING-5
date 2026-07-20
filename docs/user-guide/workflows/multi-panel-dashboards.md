---
layout: default
title: Build Multi-panel Dashboards
parent: Workflows
grand_parent: User Guide
nav_order: 3.5
permalink: /user-guide/workflows/multi-panel-dashboards/
---

# Build multi-panel dashboards

<!--
`uman~ring5.plots.multi-panel-dashboard.documentation~1`

Covers:
- req~ring5.plots.multi-panel-dashboard~1

-->

A dashboard combines two or more plots from the current workspace into one exportable figure. The
source plots remain independent: changing a dashboard does not rewrite a plot's data pipeline or
figure settings, and changing a source plot appears after the dashboard is rebuilt.

## Build a dashboard in the application

1. Create and configure at least two plots on **Manage Plots**.
2. Open **Multi-panel dashboard** at the bottom of the page.
3. Select the panels. They are placed left-to-right and then top-to-bottom in the displayed order.
4. Choose the number of columns and the complete figure's width and height. RING-5 calculates the
   required number of rows and leaves unused grid cells empty.
5. Add a dashboard title. Turn on shared X or Y axes only when the panels use compatible scales;
   optionally enter one shared axis title. **One shared legend** combines repeated series labels.
6. Select Plotly for an interactive dashboard or Matplotlib for a publication-oriented static
   figure, then select **Build dashboard**.
7. Under **Export whole dashboard**, download the complete grid—not the currently selected source
   plot—in one supported engine format.

The preview is a deliberate snapshot. When controls or source plots change, RING-5 asks you to
build again so it is clear which configuration will be exported.

Plotly dashboards export to self-contained HTML without an external browser; PNG, SVG, and PDF use
Kaleido. Matplotlib dashboards export to PDF, PGF, PNG, and SVG. See
[Rendering and Export]({{site.baseurl}}/user-guide/reference/rendering-export/) for dependencies.

A plot that is itself a nested multi-panel heatmap cannot currently occupy one dashboard cell.
Create separate heatmap plots for those panels instead. This prevents an ambiguous hidden second
grid from being flattened or overlaid during export.

## Build and export a dashboard in Python

```python
import ring5

with ring5.Session() as session:
    data = session.load("results.csv")
    ipc = session.create_plot(
        "bar",
        data=data,
        config={"x": "benchmark", "y": "ipc", "ylabel": "IPC"},
        name="Instructions per cycle",
    )
    misses = session.create_plot(
        "line",
        data=data,
        config={"x": "benchmark", "y": "l2_misses", "ylabel": "Misses"},
        name="L2 misses",
    )

    dashboard = session.create_dashboard(
        [ipc, misses],
        title="Performance overview",
        columns=2,
        width=1400,
        height=650,
        shared_xaxes=True,
        x_title="Benchmark",
    )
    figure = session.render_dashboard(dashboard, engine="matplotlib")
    session.export(figure, "figures/performance-overview.pdf", deterministic=True)
```

`create_dashboard` accepts registered plot objects or their integer IDs. Its returned
`ring5.DashboardSpec` is immutable and records panel order, grid, labels, legend behavior, and
dimensions. It deliberately retains plot IDs instead of copying plots, so every later render uses
the current source-plot data and configuration. If a referenced plot has been deleted, rendering
fails with `ring5.RenderError` instead of silently omitting a panel.
