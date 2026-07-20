---
layout: default
title: Compare Distributions with Box Plots
parent: Workflows
grand_parent: User Guide
nav_order: 3.95
permalink: /user-guide/workflows/box-plots/
---

# Compare distributions with box plots

<!--
`uman~ring5.plot.box.documentation~1`

Covers:
- req~ring5.plot.box~1

-->

Use a box plot when the spread and unusual observations matter alongside the typical value. RING-5
draws the same distribution summary with Plotly and Matplotlib, so interactive exploration and
publication export share one configuration.

On **Manage Plots**, create a plot with type **box**, finalize its shaping pipeline, and choose:

- **X-axis category** for the distributions to compare.
- **Y-axis values** for the numeric observations summarized inside each box.
- **Color by** to split every category into comparable subgroups. Leave it empty to style categories
  as individual series.
- **Orientation** to place categories on the horizontal or vertical axis.

## Control the statistical summary

The **Distribution summary** section keeps the statistical decisions explicit:

- **Quartile calculation** offers linear interpolation, inclusive median, and exclusive median.
- **Whisker range** offers Tukey's interquartile-range rule, the observed minimum and maximum, or a
  chosen percentile interval. Tukey mode exposes its IQR multiplier.
- **Show observations** displays outliers, all observations, or no points. Jitter separates repeated
  values without adding randomness, so repeated renders remain reproducible.
- **Notched boxes** show a median interval, while **Show mean** adds the arithmetic mean.
- **Box width** and **Whisker cap width** adjust geometry without changing the statistics.

Values that cannot be converted to numbers are omitted from that distribution. Empty category and
group combinations are skipped. The source table is never modified.

## Style and automate box plots

The standard **Colors** section applies palette or per-series overrides. A color-group override is
reused across every category, while an ungrouped plot can style each category separately.

```python
plot = session.create_plot(
    "box",
    data=results,
    config={
        "x": "benchmark",
        "y": "ipc",
        "color": "configuration",
        "orientation": "vertical",
        "quartile_method": "inclusive",
        "whisker_mode": "tukey",
        "whisker_multiplier": 1.5,
        "point_mode": "outliers",
        "notched": False,
        "show_mean": True,
    },
)

interactive = session.render(plot, engine="plotly")
publication = session.render(plot, engine="matplotlib")
```

Invalid columns and configuration values raise typed `ring5` errors at the public boundary. Both
engines consume the same engine-independent trace contract, including quartile choices, explicit
fences, means, and outlier membership.
