---
layout: default
title: Show Composition over an Axis with Area Charts
parent: Workflows
grand_parent: User Guide
nav_order: 13
permalink: /user-guide/workflows/area-charts/
---

# Show composition over an axis with area charts

<!--
`uman~ring5.plot.area.documentation~1`

Covers:
- req~ring5.plot.area~1

-->

Area charts emphasize magnitude and composition across an ordered axis. Use them for changes over
time, phases, load levels, or any ordered series where the filled region carries useful meaning.

## Create an area chart

1. Open **Manage Plots** and create an **Area Chart**.
2. Finish the data-shaping pipeline.
3. Select the X-axis order and a numeric Y-axis value.
4. Optionally select a categorical color column to create one area per group.
5. Choose the arrangement, curve, missing-value behavior, and opacity, then refresh the plot.

When a group contains repeated rows at the same X value, RING-5 plots their mean. The source data
is not modified.

## Choose an arrangement

- **Overlay** fills every group from zero. It is useful when shapes matter more than additive
  totals; transparency helps reveal overlap.
- **Stack values** places each group on the cumulative baseline of the previous groups. The top
  edge is the total at every X value.
- **100% stacked** converts each non-negative contribution to a percentage and makes the top edge
  100%. This compares composition when totals differ. Negative values are rejected because their
  percentage contribution is ambiguous.

Legend order controls stack order. Per-series colors, palette selection, and legend labels use the
same controls as other RING-5 plots.

## Control curves and missing values

- **Linear** joins adjacent points directly.
- **Step after** changes at the current X value; **Step before** changes immediately before the
  next value. These are useful for discrete phases and thresholds.
- **Leave gaps** preserves unknown values for overlays. In a stack, a missing contribution has
  zero thickness so the remaining cumulative baseline stays defined.
- **Fill with zero** treats missing contributions as zero.
- **Interpolate** estimates missing interior values linearly and extends the nearest observed value
  to missing ends. Use this only when interpolation is meaningful for the measurement.

## Python workflow

```python
import ring5

with ring5.Session() as session:
    plot = session.create_plot(
        "area",
        data=results,
        name="Power composition",
        config={
            "x": "phase",
            "y": "power_watts",
            "color": "component",
            "area_mode": "normalize",
            "area_interpolation": "hv",
            "area_missing": "zero",
            "area_opacity": 0.65,
        },
    )
    interactive = session.render(plot, engine="plotly")
    publication = session.render(plot, engine="matplotlib")
```

Both engines consume the same upper boundaries and explicit fill baselines, so stacking and
normalization retain the same numerical meaning.
