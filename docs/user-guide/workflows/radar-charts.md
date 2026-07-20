---
layout: default
title: Compare Profiles with Radar Charts
parent: Workflows
grand_parent: User Guide
nav_order: 14
permalink: /user-guide/workflows/radar-charts/
---

# Compare profiles with radar charts

<!--
`uman~ring5.plot.radar.documentation~1`

Covers:
- req~ring5.plot.radar~1

-->

Radar charts compare profiles across three or more category axes. They work best when every axis
has a comparable meaning or has already been transformed to a common score.

## Create a radar chart

1. Open **Manage Plots** and create a **Radar Chart**.
2. Finish the data-shaping pipeline.
3. Select a categorical axis column and a numeric value column.
4. Optionally select a series column to draw multiple profiles.
5. Choose a shared radial range, geometry, fill, and markers, then refresh the plot.

Repeated category values within a series are averaged. If a series lacks one of the shared
categories, that point is placed at the shared radial minimum so every profile retains the same
axes. The source data is not modified.

## Use one honest scale

Every profile uses exactly the same radial minimum and maximum.

- **Start at zero when possible** uses zero for non-negative data and the observed maximum.
- **Fit observed values** uses the observed minimum and maximum. This can magnify small
  differences, so read the range carefully.
- **Custom range** fixes explicit bounds for repeatable comparisons across figures. The maximum
  must be greater than the minimum.

Do not compare polygon area as if it were a linear statistic: axis order changes area and shape.
Use the category ordering control to keep related radar charts comparable.

## Control geometry and profiles

- Rotate the first category and choose clockwise or counterclockwise order to match domain
  conventions.
- Filled profiles emphasize overall shape; outlines are clearer when many series overlap.
- Markers show exact category positions. Outline width and opacity help separate dense profiles.
- Palettes, legend order, and per-series colors use the same controls as other plots.

## Python workflow

```python
import ring5

with ring5.Session() as session:
    plot = session.create_plot(
        "radar",
        data=scores,
        name="Configuration profiles",
        config={
            "x": "metric",
            "y": "normalized_score",
            "color": "configuration",
            "radar_scale_mode": "custom",
            "radar_min": 0.0,
            "radar_max": 1.0,
            "radar_fill": True,
            "radar_markers": True,
        },
    )
    interactive = session.render(plot, engine="plotly")
    publication = session.render(plot, engine="matplotlib")
```

Both engines consume the same ordered categories, closed profile values, scale, direction, and
rotation from the engine-independent radar trace.
