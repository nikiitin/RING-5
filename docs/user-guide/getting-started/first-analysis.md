---
layout: default
title: First Analysis
parent: Getting Started
grand_parent: User Guide
nav_order: 3
permalink: /user-guide/getting-started/first-analysis/
redirect_from:
  - /user-guide/getting-started/first-steps/
  - /user-guide/tutorials/create-bar-chart/
  - /user-guide/tutorials/load-and-explore/
---

# First analysis

This workflow parses one metric from a gem5 results tree, creates a bar plot, and exports it. Use a
results directory that contains at least one `stats.txt` file with `simTicks`.

## Parse the results

1. Start RING-5 with `make run` and leave **Data Source** selected.
2. Keep **Parse gem5 Stats Files** selected. Enter the results root in **Stats directory path** and
   keep `stats.txt` in **File pattern**.
3. Select **Quick Scan**. When the scan finishes, select **Add Variable**, search for `simTicks`,
   and select **Add to Configuration**.
4. Select **Parse gem5 Stats Files**. When parsing completes, the page shows the loaded row and
   column counts.

If `simTicks` is absent from some runs, stop and inspect those files. The default parser behavior
keeps missing statistics visible rather than inventing values.

## Create the plot

1. Open **Manage Plots** from the sidebar.
2. In **Create New Plot**, name the plot `Simulation ticks`, select the `bar` plot type, and select
   **Create Plot**.
3. In **Data Processing Pipeline**, add a selector or sorting step only if the raw table needs it,
   then select **Finalize Pipeline for Plotting**.
4. Under **Plot Configuration**, select a categorical column for the X axis and `simTicks` for the
   Y axis. RING-5 generates the first figure automatically; use **Refresh Plot** after later changes
   when automatic refresh is disabled.
5. Select Plotly for interactive inspection or Matplotlib for a static figure.

The parser derives configuration columns from the results directory structure. Choose the column
that identifies the comparison you intend to make; do not assume every results tree produces the
same names.

## Export the result

Use the download controls below the figure. A Matplotlib PDF works without a LaTeX installation.
For the engine-specific format list and optional dependencies, see
[Rendering and Export](../reference/rendering-export/).

## Run the same minimal plot in Python

The supported API accepts any suitable DataFrame:

```python
import pandas as pd
import ring5

data = pd.DataFrame(
    {"benchmark": ["mcf", "xalancbmk"], "simTicks": [4.2e11, 3.8e11]}
)

with ring5.Session() as session:
    spec = ring5.FigureSpec(
        x="benchmark",
        y_columns=["simTicks"],
        title="Simulation ticks",
    )
    figure = session.plot(
        "bar", data=data, config=spec, engine="matplotlib"
    )
    session.export(figure, "simulation-ticks.pdf")
```

Continue with [Load and Parse Data](../workflows/loading-data/) or
[Compare Configurations](../guides/compare-configurations/).
