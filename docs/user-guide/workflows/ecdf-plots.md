---
layout: default
title: Compare Cumulative Distributions with ECDF Plots
parent: Workflows
grand_parent: User Guide
nav_order: 12
permalink: /user-guide/workflows/ecdf-plots/
---

# Compare cumulative distributions with ECDF plots

<!--
`uman~ring5.plot.ecdf.documentation~1`

Covers:
- req~ring5.plot.ecdf~1

-->

An empirical cumulative distribution function (ECDF) shows every observed threshold without
choosing histogram bins or a smoothing bandwidth. It answers questions such as “what fraction of
runs completed at or below this latency?”

## Create an ECDF

1. Open **Manage Plots** and create an **ECDF**.
2. Finish the data-shaping pipeline.
3. Select a numeric **X-axis values** column.
4. Optionally select a categorical color column to compare groups.
5. Choose the cumulative direction and Y-axis meaning, then refresh the plot.

Non-numeric and missing values are omitted. Repeated values are combined at one threshold, so the
step height correctly represents all observations at that value. The source data is not modified.

## Choose cumulative or complementary display

- **Cumulative distribution** shows observations at or below each threshold. It rises from the
  smallest value toward the full sample.
- **Complementary (survival)** shows observations strictly above each threshold. It falls toward
  zero and is useful for tail probabilities, service-level limits, and exceedance counts.

The curve uses post-threshold steps: the vertical change occurs at the observed value and the new
level continues until the next threshold.

## Choose the Y-axis meaning

- **Proportion (0 to 1)** compares groups with different sample sizes on the same probability
  scale.
- **Observation count** retains absolute sample counts. This is useful when the number of runs is
  itself meaningful.

Enable **Show observed thresholds** to place markers at the exact step changes. Markers do not add
or interpolate observations. Category ordering, palettes, and per-series colors use the same
controls as other plots and remain consistent across both rendering engines.

## Python workflow

```python
import ring5

with ring5.Session() as session:
    plot = session.create_plot(
        "ecdf",
        data=results,
        name="Latency survival",
        config={
            "x": "latency_ns",
            "color": "configuration",
            "ecdf_complementary": True,
            "ecdf_y_mode": "proportion",
            "ecdf_markers": True,
        },
    )
    interactive = session.render(plot, engine="plotly")
    publication = session.render(plot, engine="matplotlib")
```

Both engines consume the same sorted thresholds and cumulative ordinates from an
engine-independent step trace.
