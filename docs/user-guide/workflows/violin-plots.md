---
layout: default
title: Compare Density Shapes with Violin Plots
parent: Workflows
grand_parent: User Guide
nav_order: 11
permalink: /user-guide/workflows/violin-plots/
---

# Compare density shapes with violin plots

<!--
`uman~ring5.plot.violin.documentation~1`

Covers:
- req~ring5.plot.violin~1

-->

Violin plots show the full shape of a numeric distribution for every category. They are useful
when a box plot's quartiles hide clusters, skew, or multiple peaks.

## Create a violin plot

1. Open **Manage Plots** and create a **Violin Plot**.
2. Finish the data-shaping pipeline.
3. Choose a categorical **X-axis category** and numeric **Y-axis values**.
4. Optionally choose a categorical color column to compare groups within every category.
5. Refresh the visualization.

The application omits non-numeric values from the density calculation and skips empty
category/group combinations. Your source data is not modified.

## Read and tune the density

The width of a violin represents estimated observation density, not a numeric axis value. Wider
parts contain more nearby observations.

- **Scott's rule** is a dependable general-purpose bandwidth.
- **Silverman's rule** is robust to broad tails and often retains slightly more structure.
- **Smoothing multiplier** adjusts the selected rule. Lower values reveal more local detail;
  higher values emphasize the overall shape.
- **Include smoothed tails** lets the kernel density extend beyond the observed minimum and
  maximum. **Observed range only** clips the display to actual data bounds.
- **Equal maximum width** compares shapes directly. **Scale by sample count** also makes groups
  with fewer observations narrower.

Bandwidth changes the estimate, so avoid selecting a value only because it creates a preferred
visual story. Check that important features remain visible across nearby smoothing settings.

## Choose the display

- Use horizontal orientation when category labels are long.
- Full violins are best for a single distribution. A right/upper or left/lower half violin can
  leave space for annotations or a paired display.
- **Box and median**, **Mean line**, and **Box and mean** add a compact inner summary. Select
  **None** when the density shape should stand alone.
- Observation points reveal sample size and exact values. Jitter separates overlapping points;
  it does not change the data.

Category order, legend order, palettes, and per-series colors use the same controls as other
RING-5 plots. Explicit per-series colors remain consistent in Plotly and Matplotlib exports.

## Python workflow

```python
import ring5

with ring5.Session() as session:
    plot = session.create_plot(
        "violin",
        data=results,
        name="IPC density",
        config={
            "x": "benchmark",
            "y": "ipc",
            "color": "configuration",
            "bandwidth_method": "silverman",
            "bandwidth_scale": 1.0,
            "density_scale": "count",
            "summary_mode": "box+mean",
            "point_mode": "all",
        },
    )
    interactive = session.render(plot, engine="plotly")
    print_figure = session.render(plot, engine="matplotlib")
```

Both renderers consume the same engine-independent observations, bandwidth, and summary trace.
This keeps the statistical meaning stable when switching engines.
