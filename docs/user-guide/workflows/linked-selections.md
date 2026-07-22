---
layout: default
title: Link Dashboard Selections
parent: Workflows
grand_parent: User Guide
nav_order: 3.6
permalink: /user-guide/workflows/linked-selections/
---

# Link dashboard selections

<!--
`uman~ring5.plots.linked-selections.documentation~1`

Covers:
- req~ring5.plots.linked-selections~1

-->

Linked selections make related values easier to compare across a Plotly dashboard. A box or lasso
selection in one panel can either emphasize matching points in every panel or temporarily remove
unrelated points from the preview. The source plots and their datasets never change.

## Choose what “related” means

RING-5 relates panels by an exact value on one visible axis:

- **X axis** is useful when panels share categories, workloads, dates, or another horizontal key.
- **Y axis** is useful when the shared comparison key appears vertically.

For example, selecting workload `mcf` on the X axis of an IPC panel also finds `mcf` on the X axis
of the power panel. A trace without matching visible values remains present but has no selected
points in highlight mode and no points in filter mode. Use panels with the same semantic axis and
compatible value representation; RING-5 does not guess joins between differently named or encoded
categories.

## Link panels in the application

1. Create at least two plots and open **Multi-panel dashboard** on **Manage Plots**.
2. Select **Interactive Plotly**, then turn on **Link panel selections**.
3. Under **Relate values on**, choose X or Y.
4. Under **Linked behavior**, choose **Highlight** to fade unrelated markers or **Filter** to show
   only matching points.
5. Build the dashboard and use Plotly's box or lasso tool in any panel.
6. Select **Clear selection** to restore the complete preview.

The selection affects a temporary copy of the composed figure. Rebuilding, changing the link
configuration, or clearing the selection restores the full dashboard without rewriting the source
data. The whole-dashboard download continues to export the complete built dashboard. Linked
selection is unavailable for Matplotlib because it is a static rendering engine.

Heatmaps retain only the matching rows or columns in both behaviors because Plotly does not expose
point highlighting for heatmap cells.

## Apply the same contract in Python

```python
import ring5

with ring5.Session() as session:
    data = session.load("results.csv")
    ipc = session.create_plot(
        "bar",
        data=data,
        config={"x": "workload", "y": "ipc"},
        name="IPC",
    )
    power = session.create_plot(
        "scatter",
        data=data,
        config={"x": "workload", "y": "power"},
        name="Power",
    )
    dashboard = session.create_dashboard([ipc, power], columns=2)
    link = session.create_linked_selection(
        dashboard,
        axis="x",
        mode="highlight",
    )
    complete = session.render_dashboard(dashboard, engine="plotly")
    selected = ring5.apply_linked_selection(complete, link, ["mcf", "gcc"])

    # `complete` is unchanged; `selected` is a separate Plotly figure.
    session.export(selected, "figures/selected-workloads.html")
```

`ring5.LinkedSelectionSpec` is immutable and records the linked plot IDs, visible relation axis,
and behavior. `ring5.apply_linked_selection` always returns a new Plotly figure and raises
`ring5.RenderError` when the input cannot be transformed.
