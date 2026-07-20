---
layout: default
title: Explore Rows Behind a Plot
parent: Workflows
grand_parent: User Guide
nav_order: 3.7
permalink: /user-guide/workflows/plot-drill-down/
---

# Explore rows behind a plot

<!--
`uman~ring5.plots.drill-down.documentation~1`

Covers:
- req~ring5.plots.drill-down~1

-->

Plot drill-down answers a practical question: “Which rows produced this value?” A click on a bar,
point, line marker, histogram bin, or heatmap cell opens a read-only table of its contributing
source rows. Closing that table returns to the complete plot with the active axes, labels, styles,
and other figure settings intact.

## Inspect a value in the application

1. Build a plot from a finalized pipeline on **Manage Plots** and use the Plotly engine.
2. Turn on **Explore source rows** below the engine selector.
3. Click a plotted value. RING-5 shows the clicked trace and coordinates, the matched dimensions,
   the number of source rows, and a scrollable source table.
4. Select **Back to full plot** to close the table. The plot configuration is not reset or rebuilt.

The feature is opt-in so ordinary Plotly editing, zooming, and panning remain uncluttered. Matplotlib
is a static engine and therefore does not expose point clicks.

RING-5 attaches only the point's grouping dimensions to the browser figure—for example,
`workload = mcf` and `variant = baseline`. Full source rows remain in the Python session and are
resolved only after the click. The resolver returns a defensive copy and never changes the plot's
source data or processed data.

The behavior applies to every registered plot family. For a heatmap cell, the X category and facet
identify contributing rows; the metric is already represented by the selected heatmap row. For a
histogram bin, every row in the selected histogram group can contribute a bucket count, so the
detail table shows that group rather than inventing per-sample values that are not present in the
flattened gem5 histogram columns.

The live source snapshot is captured when a web pipeline is finalized. It is intentionally not
duplicated inside portfolio files, which keeps portfolios compact and avoids silently embedding a
second copy of the input dataset. After restoring an older or self-contained portfolio, drill-down
falls back to its saved processed rows.

## Resolve the same rows in Python

```python
import pandas as pd
import ring5

source = pd.DataFrame(
    {
        "workload": ["mcf", "mcf", "gcc"],
        "seed": [0, 1, 0],
        "ipc": [1.01, 1.07, 1.22],
    }
)

with ring5.Session() as session:
    plot = session.create_plot(
        "bar",
        data=source,
        config={"x": "workload", "y": "ipc"},
        name="Mean IPC",
    )

    result = session.drill_down(plot, {"workload": "mcf"})
    print(result.row_count)  # 2
    print(result.rows[["seed", "ipc"]])
```

The application derives the filter mapping from a clicked point. Python callers provide that
mapping explicitly. `ring5.DrillDownResult.rows` returns a fresh DataFrame copy on every access;
changing it cannot affect the registered plot or its source snapshot. Invalid plot IDs, filter
columns, and non-scalar filter values raise `ring5.DataValidationError`.
