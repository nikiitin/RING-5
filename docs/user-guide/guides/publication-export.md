---
layout: default
title: Prepare Publication Output
parent: Analysis Guides
grand_parent: User Guide
nav_order: 2
permalink: /user-guide/guides/publication-export/
redirect_from:
  - /user-guide/tutorials/custom-styling/
  - /user-guide/tutorials/publication-ready/
---

# Prepare publication output

Start from a plot whose data and labels are already correct. Obtain the exact column width, minimum
font size, color requirements, and accepted file formats from the target venue or document template;
RING-5 does not encode venue rules.

## Set the final dimensions

Under **Layout**, select **Single Column (~3.5in)**, **Double Column (~7.0in)**, or **Custom** and set
the height. Treat the presets as starting points, not submission requirements. Matplotlib uses the
physical width and height for export; Plotly uses the corresponding pixel dimensions.

## Check typography and axes

<!--
`uman~ring5.figure.category-groups.documentation~1`

Covers:
- req~ring5.figure.category-groups~1

`uman~ring5.figure.numbered-xaxis.documentation~1`

Covers:
- req~ring5.figure.numbered-xaxis~1

-->

For long grouped-category labels, numbered X-axis mode can replace or supplement ticks with numbers
and a separately positioned number legend. Category super-groups can label adjacent spans and draw
their boundary or rule lines.

Under **Typography**, set title, axis-title, and tick-label sizes for the final printed size. Under
**Axes**, check tick spacing, label rotation, units, and ranges. A truncated range can change the
visual claim, especially for bars.

Under **Legends**, use concise series names and keep the legend away from data. Under **Colors**,
choose a palette that remains distinguishable in grayscale or add patterns when the plot supports
them. Under **Data Labels**, add numbers only when they improve reading at the target size.

Refresh the figure and inspect the selected export engine. Plotly and Matplotlib share the figure
configuration, but text wrapping and spacing can differ.

## Choose an output

- Matplotlib PDF or SVG provides static vector output without LaTeX.
- Matplotlib PGF integrates figure text with LaTeX and requires XeLaTeX. Raster content such as a
  heatmap cannot be written as PGF; the web download falls back to PDF with a warning.
- PNG is appropriate when the publication workflow requires raster output. Inspect it at the final
  resolution.
- Plotly HTML preserves interactivity for supplementary material. Plotly PNG, SVG, and PDF require a
  Chrome-family browser through Kaleido.

RING-5 does not support EPS export.

## Export from the web application

Select **Engine**, refresh the plot, expand **Download**, select **Format**, and use the matching
download button. The format list changes with the active engine.

Open the exported file outside the browser. Check dimensions, clipped labels, embedded or matching
fonts, line weights, marker visibility, and color accessibility at the size used in the paper.

## Export deterministically from Python

```python
figure = session.plot(
    "grouped_bar",
    data=data,
    config=spec,
    engine="matplotlib",
)
session.export(
    figure,
    "figures/ipc.pdf",
    deterministic=True,
)
```

Deterministic export applies byte-stability controls where the format supports them. Keep the input
CSV, script or portfolio, RING-5 version, and exact export command with the paper artifacts.

See [Rendering and Export]({{site.baseurl}}/user-guide/reference/rendering-export/) for the engine-format matrix and
dependency checks.
