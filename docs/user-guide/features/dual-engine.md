---
title: "Dual Rendering Engine"
parent: Features
grand_parent: User Guide
nav_order: 3
---

# Dual Rendering Engine

## Overview

RING-5 supports two rendering engines: **Plotly** and **Matplotlib**. Both
engines produce plots from the same data and configuration, but they serve
different purposes. Plotly creates interactive plots for data exploration, while
Matplotlib produces publication-quality static figures for paper submissions.

You can switch between engines at any time without losing your plot
configuration. The same settings -- dimensions, colors, labels, legends -- apply
to both engines. This lets you explore your data interactively and then generate
a camera-ready figure without reconfiguring anything.


## Plotly Engine

The Plotly engine renders interactive plots directly in your browser. You can
zoom into specific data ranges, pan across the plot, and hover over data points
to see exact values.

Plotly plots support the following interactive features:

- **Zoom and pan** -- Click and drag to zoom into a region. Double-click to
  reset the view.
- **Hover tooltips** -- Move your mouse over a data point to see its value,
  label, and any custom data fields.
- **Legend toggling** -- Click a legend entry to hide or show that trace.
  Double-click a legend entry to isolate it.
- **Drawing tools** -- Use the toolbar to draw lines, rectangles, and circles
  as annotations on the plot.
- **One-click SVG export** -- The Plotly toolbar includes a download button that
  saves the current view as an SVG file.

Plotly renders as HTML and JavaScript in the browser. This makes it well suited
for presentations where you want to show live, interactive data, or for sharing
analysis results as self-contained HTML files.


## Matplotlib Engine

The Matplotlib engine renders static, publication-quality figures. It produces
crisp vector output in PDF and PGF formats that look sharp at any resolution.

Key advantages of the Matplotlib engine:

- **LaTeX rendering** -- Labels, titles, and annotations can include LaTeX math
  notation. Special characters are automatically escaped so they render
  correctly.
- **PGF export** -- You can export figures as PGF files that integrate natively
  with LaTeX documents. Fonts in the figure automatically match your document
  fonts.
- **Precise typography** -- Bold text, custom font weights, and fine-grained
  font size control work reliably across all output formats.
- **Publication DPI** -- Export presets set the correct DPI for each venue (300
  for conferences, 600 for Nature and Science).

When you switch to the Matplotlib engine, the plot renders as a static image in
the RING-5 interface. You cannot zoom or hover, but what you see is exactly what
the exported file will look like.


## Switching Engines

You can switch engines on the **Manage Plots** page using the **Engine** selector
displayed above each plot.

1. Navigate to the **Manage Plots** page.
2. Locate the plot you want to change.
3. Click either **Plotly** or **LaTeX (Matplotlib)** in the Engine pills.

You should see the plot re-render with the selected engine. If you chose
Matplotlib, the plot appears as a static image. If you chose Plotly, the plot
becomes interactive.

The engine selection is **per-plot**. You can have some plots rendered with
Plotly and others with Matplotlib in the same session. This is useful when you
want to keep some plots interactive for exploration while preparing others for
export.


## Feature Differences

Most features work identically in both engines. The following table highlights
where they differ.

| Feature                    | Plotly           | Matplotlib          |
|----------------------------|------------------|---------------------|
| Interactive zoom and pan   | Yes              | No                  |
| Hover tooltips             | Yes              | No                  |
| Draggable legend           | Yes              | No                  |
| Drawing tools              | Yes              | No                  |
| LaTeX math in labels       | No               | Yes                 |
| Bold title and axis labels | Limited          | Full support        |
| Y-label vertical position  | Standoff only    | Fine-grained control|
| PGF export (LaTeX native)  | Not available    | Yes                 |
| HTML export (interactive)  | Yes              | Not available       |
| PDF export                 | Yes              | Yes (higher quality)|
| PNG export                 | Yes              | Yes                 |
| SVG export                 | Yes              | Yes                 |
| Error bars                 | Yes              | Not supported       |
| Fill/area charts           | Yes              | Not supported       |
| Cumulative histograms      | Yes              | Not supported       |

Both engines fully support bar charts, line charts, scatter plots, standard
histograms, and heatmaps, including multi-heatmap subplot layouts and secondary
Y-axes.


## Recommended Workflow

For most analysis tasks, the following workflow works well:

1. **Start with Plotly.** Use the interactive engine to explore your data. Zoom
   into interesting regions, hover over outliers, and toggle traces to compare
   different configurations.

2. **Refine your configuration.** Adjust colors, labels, legends, and axis
   ranges while using Plotly. The interactive feedback makes it easy to iterate
   quickly.

3. **Switch to Matplotlib for export.** Once you are satisfied with the plot
   content, switch to the Matplotlib engine. Apply an export preset for your
   target venue (such as ISCA or MICRO).

4. **Export as PDF or PGF.** Use the Download section to export the final figure.
   Choose PGF if you want LaTeX-native output with matching document fonts, or
   PDF for a self-contained vector file.

You should see your final exported figure match what is displayed in the RING-5
interface when using the Matplotlib engine. The Matplotlib preview is a faithful
representation of the exported file.

This workflow combines the strengths of both engines: fast, interactive
exploration with Plotly followed by precise, publication-ready output with
Matplotlib.
