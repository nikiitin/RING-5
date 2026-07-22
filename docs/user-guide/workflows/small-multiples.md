---
layout: default
title: Compare Groups with Small Multiples
parent: Workflows
grand_parent: User Guide
nav_order: 3.8
permalink: /user-guide/workflows/small-multiples/
---

# Compare groups with small multiples

<!--
`uman~ring5.plots.small-multiples.documentation~1`

Covers:
- req~ring5.plots.small-multiples~1

-->

Small multiples answer “How does the same plot change across these groups?” RING-5 repeats one
configured plot for every category—or every combination of categories—in a single grid. Each panel
uses the same axes, ordering, palette, labels, and styling, so differences are easier to compare
without mentally reconciling separate figures.

## Split a plot into panels

1. Build a plot from a finalized pipeline on **Manage Plots**.
2. Open **Layout** under the plot settings.
3. Turn on **Split this plot into comparable panels**.
4. Under **Create one panel for each combination of**, choose one or more categorical columns.
5. Choose how many panels appear per row. Keep **Share X scale**, **Share Y scale**, and
   **One legend** enabled for the most direct comparison.
6. Refresh the plot if auto-refresh is off.

The panel-count message updates before the figure is built. Two to 24 panels usually remain easy to
scan; when a selection creates more, RING-5 suggests filtering the plot data or choosing a broader
category. Panel row height controls readability without changing the source plot's data.

Panels follow the first appearance of each category combination in the processed data. Their titles
name every facet column and value, such as `architecture: arm · mode: safe`; missing values are shown
as `Missing`, not silently discarded. Both Plotly and Matplotlib use the same panel order and
configuration. Turning the feature off returns to the complete plot.

Small multiples need at least two distinct groups. Numeric columns are not accepted as facets; turn
a coded numeric category into a categorical column first. A heatmap that already uses its own
**Facet by** control contains nested panels, so disable that inner facet before applying general
small multiples.

## Build the same comparison in Python

```python
import pandas as pd
import ring5

data = pd.DataFrame(
    {
        "benchmark": ["mcf", "gcc", "mcf", "gcc"],
        "architecture": ["x86", "x86", "arm", "arm"],
        "ipc": [1.01, 1.22, 1.18, 1.31],
    }
)

with ring5.Session() as session:
    plot = session.create_plot(
        "bar",
        data=data,
        config={"x": "benchmark", "y": "ipc", "ylabel": "IPC"},
    )
    facets = session.create_small_multiples(
        plot,
        by="architecture",
        columns=2,
        order=["arm"],
        labels={"arm": "ARM systems"},
        shared_xaxes=True,
        shared_yaxes=True,
    )
    figure = session.render_small_multiples(facets, engine="matplotlib")
    session.export(figure, "ipc-by-architecture.pdf")
```

For multiple facet columns, use tuples in `order` and `labels`, for example
`order=[("arm", "safe")]`. An explicit order may name only the groups that must come first; all
remaining groups keep their data order. Label overrides are optional and do not change the values
used to select panel rows.

`session.small_multiples(...)` is the create-and-render shortcut. The separate create and render
steps are useful when exporting the same resolved layout through both engines. Rendering operates on
defensive panel subsets and does not change the registered plot's data or configuration. Invalid
columns, orders, labels, or stale plot references raise `ring5.DataValidationError` or
`ring5.RenderError` at the public boundary.
