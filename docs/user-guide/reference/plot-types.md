---
layout: default
title: Plot Types
parent: Reference
grand_parent: User Guide
nav_order: 1
permalink: /user-guide/reference/plot-types/
---

# Plot types

Choose a plot type from the relationship in the processed table. The registry shown in **Plot type**
is authoritative; scripts can inspect the same identifiers:

```python
import ring5

print(ring5.available_plot_types())
```

## Selection guide

<!--
`uman~ring5.plot.bar.documentation~1`

Covers:
- req~ring5.plot.bar~1

`uman~ring5.plot.dual-axis-bar-dot.documentation~1`

Covers:
- req~ring5.plot.dual-axis-bar-dot~1

`uman~ring5.plot.grouped-bar.documentation~1`

Covers:
- req~ring5.plot.grouped-bar~1

`uman~ring5.plot.grouped-stacked-bar.documentation~1`

Covers:
- req~ring5.plot.grouped-stacked-bar~1

`uman~ring5.plot.heatmap.documentation~1`

Covers:
- req~ring5.plot.heatmap~1

`uman~ring5.plot.histogram.documentation~2`

Covers:
- req~ring5.plot.histogram~2

`uman~ring5.plot.line.documentation~1`

Covers:
- req~ring5.plot.line~1

`uman~ring5.plot.scatter.documentation~1`

Covers:
- req~ring5.plot.scatter~1

`uman~ring5.plot.stacked-bar.documentation~1`

Covers:
- req~ring5.plot.stacked-bar~1

-->

<!--
`uman~ring5.ingestion.histogram.documentation~1`

Covers:
- req~ring5.ingestion.histogram~1

-->

| Relationship | Starting point | Data requirement |
| --- | --- | --- |
| One numeric measure by category | `bar` | Categorical X and numeric Y |
| Configurations side by side | `grouped_bar` | X, group, and numeric Y |
| Components of a total | `stacked_bar` | X and numeric component columns |
| Components nested within comparisons | `grouped_stacked_bar` | Major and minor groups plus stack columns |
| Trend over an ordered value | `line` | Ordered X and numeric Y |
| Relationship between numeric measures | `scatter` | Numeric X and Y |
| Frequency distributions | `histogram` | A declared native layout, or explicit interval columns such as `<variable>..<start>-<end>` |
| Matrix of values | `heatmap` | Row, column, and numeric value mappings |
| Bars with a distinct right-axis measure | `dual_axis_bar_dot` | Bar mapping and right-axis dot mapping |

These are task descriptions, not a frozen registry inventory. Extensions can register additional
identifiers.

## Plot-specific controls

### Dual-axis controls

<!--
`uman~ring5.figure.dual-axis-controls.documentation~1`

Covers:
- req~ring5.figure.dual-axis-controls~1

-->

<!--
`uman~ring5.figure.dual-axis-dot-layout.documentation~1`

Covers:
- req~ring5.figure.dual-axis-dot-layout~1

-->

Dual-axis bar-and-dot and grouped-stacked plots configure right-axis metrics, range and title, bars
or dots, dot marker and line styling, per-group connecting lines, and unified or separate legends.

For grouped bar-and-dot plots, **Dot placement** can keep the right-axis series at each benchmark
center or align every dot directly with the bar for the same configuration. With aligned dots,
**Line connection scope** either follows each configuration across benchmark groups or connects the
configurations only inside one benchmark group. The latter deliberately stops every line before the
next benchmark, making comparisons inside a group explicit without implying a trend between groups.

### Histogram controls

<!--
`uman~ring5.figure.histogram-controls.documentation~2`

Covers:
- req~ring5.figure.histogram-controls~2

-->

Histogram plots select a logical frequency variable and optional categorical group. Grouped traces
overlay. Native Distribution data uses its exact declared bindings, including arbitrary physical
column names. Ordinary Vector/CSV data uses the explicit interval suffix contract described below.

A native view displays storage-cell mass at ordinal positions with literal bucket labels and equal
glyph widths. The default axis title is **Native bucket**; an explicit title takes precedence.
Underflow, every allocated native slot (including slots above the tracked maximum), and overflow
remain in order. Selected summaries are excluded by their declared role. No continuous support is
inferred from a native label. Native count, probability, percent and cumulative probability/CDF are
available; continuous rebinning and noncumulative density raise an error. A Distribution-to-Vector
label view without complete geometry raises an actionable error instead of guessing a grid.

Measured zero counts support raw and cumulative count. Probability, percent, density and normalized
cumulative modes require finite positive selected mass in every selected group. Every native
frequency must be measured, finite and nonnegative. An incomplete group or unrepresentable count
rejects the whole view and preserves the previous figure. Raw noncumulative count does not require
that the sum of distinct finite counts fit in one float; cumulative counts must remain finite.

### Heatmap controls

<!--
`uman~ring5.figure.heatmap-controls.documentation~1`

Covers:
- req~ring5.figure.heatmap-controls~1

-->

Heatmaps map row, column, and numeric value fields with optional facets. Controls include palette,
range, shared or individual colorbars, missing-cell text, and formatted cell labels.

### Cumulative histograms

<!--
`uman~ring5.figure.histogram-cumulative.documentation~2`

Covers:
- req~ring5.figure.histogram-cumulative~2

-->

Cumulative mode accumulates pre-binned values in display order after applying the selected count,
probability, percent, or density normalization. Cumulative density means cumulative probability,
including tails, and requires finite positive selected mass. Native storage cells use the same
CDF meaning without assigning a continuous density width.

## Common checks

- Finalize the shaper pipeline before mapping columns.
- Keep categorical order explicit when lexical order would change the claim.
- Use a stacked plot only when segments share a meaningful total.
- Label dual axes with units and use visually distinct series encodings.
- Do not use a line merely to connect unrelated categories.
- Inspect error-bar source columns after reduction or normalization.

All plot implementations construct engine-independent traces and can be rendered through Plotly or
Matplotlib. Backend-specific spacing can still differ, so inspect the target engine before export.

Generic interval histogram columns use the suffixes `0-9` for an inclusive integer range,
`[0,2.5)` for a half-open continuous range, `10+` for overflow, and `<0` for underflow.
Each measured row must use nonoverlapping buckets. The inclusive ranges `0-10`
and `10-20` overlap at ten and raise an error; use `0-9` and `10-19` for integer
buckets or `[0,10)` and `[10,20)` for continuous intervals. Bare fractional
ranges are ambiguous and require explicit half-open labels. Histogram rebinning conserves counts; splitting an existing
interval distributes its count uniformly over the overlapping new intervals. Density
uses each finite interval's actual width and requires finite bounds. Cumulative
density is a cumulative probability, including any underflow and overflow counts.
Different rows can use overlapping interval schemas when simulator runs use different
bucket widths. Rebinning adds the observed mass from each interval; absent interval
fields are omitted. Every row must contain at least one measured bucket. Malformed
buckets, entirely missing observations, negative/nonfinite counts and arithmetic overflow raise an
error. Zero-total normalized output also raises an error; observed raw zero counts remain valid.
An explicit generic Histogram request interprets ordinary Vector/CSV labels as intervals without
certifying native Distribution identity or geometry.

Radar profiles preserve absent category observations as gaps. Adjusting the radial
scale does not replace missing observations with values. Incomplete profiles remain
unfilled. Box and violin legends
include each observed group, including groups absent from the first category.
