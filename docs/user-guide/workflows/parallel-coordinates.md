---
layout: default
title: Compare Rows with Parallel Coordinates
parent: Workflows
grand_parent: User Guide
nav_order: 17
permalink: /user-guide/workflows/parallel-coordinates/
---

# Compare rows with parallel coordinates

<!--
`uman~ring5.plot.parallel-coordinates.documentation~1`

Covers:
- req~ring5.plot.parallel-coordinates~1

-->

Parallel-coordinate plots draw one path per row across an ordered set of vertical dimensions. They
are useful for finding multivariate trade-offs, clusters, and unusual profiles that a pairwise
chart can hide.

## Create a parallel-coordinate plot

1. Open **Manage Plots** and create **Parallel Coordinates**.
2. Finish the data-shaping pipeline.
3. Select at least two dimensions in the order they should appear.
4. Optionally choose a dimension that colors the row paths.
5. Choose range behavior, an optional numeric brush, color scale, and dimming strength, then
   refresh the plot.

The selected dimension order is the axis order. The source data is not changed.

## Mix numeric and categorical dimensions

Numeric values keep their original scale. Categorical values are encoded once in first-appearance
order, and both renderers display their original labels at the encoded tick positions. Missing or
non-finite dimension and color values are rejected instead of producing partial paths.

Each numeric axis can fit its observed data or include zero. Python callers can set exact ranges
with `parallel_ranges={"power": [0, 100]}`. A range maximum must be finite and greater than its
minimum. Constant dimensions receive a small visible range automatically.

## Brush rows without losing context

Choose one numeric dimension and a visible brush range in the application. Plotly exposes the
native draggable constraint; Matplotlib draws rows inside the same range clearly and dims rows
outside it. The **Rows outside the brush** control changes that dimming in both engines.

Python workflows can constrain several dimensions at once with
`parallel_brushes={"ipc": [1.0, 2.0], "power": [10, 25]}`. A row must satisfy every configured
brush to remain emphasized.

## Use a meaningful color scale

A numeric color dimension uses its numeric range. A categorical color dimension uses the same
stable encoding and shows category labels on the scale. Choose Viridis, Cividis, Plasma, Inferno,
Magma, Turbo, or RdBu; the scale can be reversed and its legend hidden. Without a color dimension,
all paths use the selected fixed line color.

Python callers can rename axes with `parallel_labels` and set explicit `parallel_color_min` and
`parallel_color_max` bounds when figures must remain comparable.

## Python workflow

```python
import ring5

with ring5.Session() as session:
    plot = session.create_plot(
        "parallel_coordinates",
        data=profiles,
        name="Architecture trade-offs",
        config={
            "parallel_dimensions": ["power_w", "architecture", "ipc", "cores"],
            "parallel_color": "ipc",
            "parallel_labels": {"power_w": "Power (W)"},
            "parallel_ranges": {"power_w": [0, 100]},
            "parallel_brushes": {"ipc": [1.2, 3.0]},
            "parallel_colorscale": "Cividis",
            "parallel_reverse_colorscale": False,
        },
    )
    interactive = session.render(plot, engine="plotly")
    publication = session.render(plot, engine="matplotlib")
```

Plotly receives native parallel-coordinate dimensions and constraints. Matplotlib normalizes the
same encoded values against the same explicit ranges, preserving row paths, brushes, and colors.
