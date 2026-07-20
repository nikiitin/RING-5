---
layout: default
title: Trace Flows with Sankey Diagrams
parent: Workflows
grand_parent: User Guide
nav_order: 16
permalink: /user-guide/workflows/sankey-diagrams/
---

# Trace flows with Sankey diagrams

<!--
`uman~ring5.plot.sankey.documentation~1`

Covers:
- req~ring5.plot.sankey~1

-->

Sankey diagrams show how a positive quantity moves between named nodes. Link width represents the
flow value, which makes splits, losses, merges, and downstream outcomes easy to compare.

## Create a Sankey diagram

1. Open **Manage Plots** and create a **Sankey Diagram**.
2. Finish the data-shaping pipeline.
3. Choose the source-node, target-node, and numeric flow-value columns.
4. Optionally choose a link-label column for annotations such as route or reason.
5. Choose node labels, arrangement, link colors, spacing, and opacity, then refresh the plot.

Rows with the same source and target are combined by summing their values. Distinct non-empty link
labels on those rows are retained in first-appearance order.

## Prepare valid flow data

Every source, target, and value cell must be present. Values must be finite and greater than zero;
zero, negative, and non-numeric flows are rejected because they do not define a visible Sankey
width. Node names must be non-empty.

RING-5 also rejects cycles. The shared layout assigns each node to a deterministic left-to-right
layer, so an acyclic flow keeps the same meaning in the interactive and publication renderers.
Reshape feedback loops into a separate stage or diagram before plotting them.

## Control labels and colors

Node labels can show names alone, names with their maximum incoming/outgoing total, or be hidden.
Python callers can supply `sankey_node_labels` to rename individual nodes. A bounded number format
controls displayed totals. Link labels can be selected from a source column and shown or hidden.

Node colors come from the selected figure palette. Links can match their source, match their
target, or use one chosen color. Link opacity, node border color, and border width remain explicit,
so dense flows can be made legible without changing their values.

## Choose an arrangement

- **Snap nodes into columns** keeps nodes aligned and respects their configured spacing.
- **Keep links perpendicular** limits interactive node movement across the flow direction.
- **Allow free node movement** lets Plotly users reposition nodes interactively.
- **Keep computed positions fixed** locks the shared deterministic layout. Python callers can
  override individual fixed coordinates with `sankey_node_positions={"Node": [x, y]}`, where both
  coordinates are between zero and one.

## Python workflow

```python
import ring5

with ring5.Session() as session:
    plot = session.create_plot(
        "sankey",
        data=flows,
        name="Energy flow",
        config={
            "sankey_source": "from_stage",
            "sankey_target": "to_stage",
            "sankey_value": "energy_kwh",
            "sankey_label": "route",
            "sankey_label_mode": "names_with_totals",
            "sankey_arrangement": "fixed",
            "sankey_color_mode": "source",
            "sankey_show_link_labels": True,
        },
    )
    interactive = session.render(plot, engine="plotly")
    publication = session.render(plot, engine="matplotlib")
```

Plotly receives a native Sankey trace. Matplotlib draws the same precomputed node positions and
weighted links as Bézier paths, so aggregation, labels, colors, and flow direction remain aligned.
