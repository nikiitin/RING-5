---
title: "Creating Publication-Ready Plots"
parent: Tutorials
grand_parent: User Guide
nav_order: 6
---

# Creating Publication-Ready Plots

This tutorial walks you through creating a camera-ready figure that meets the
submission requirements of top computer architecture conferences such as ISCA,
MICRO, and ASPLOS. By the end, you will have a vector PDF or PGF file at the
exact column width required by the venue, with properly sized fonts and tight
margins.

## Prerequisites

Before starting this tutorial, you should have:

- A working RING-5 installation with data loaded on the Data Source page.
- At least one plot already created on the Manage Plots page. If you have not
  created a plot yet, start with the
  [First Analysis](../getting-started/first-analysis.md) guide to build a basic
  bar chart.
- A LaTeX installation (TeX Live or MiKTeX) if you plan to use PGF export.
  XeLaTeX is the default TeX engine.

## What You Will Build

You will take an existing interactive Plotly chart and transform it into a
publication-quality figure suitable for a single-column conference submission.
The figure will be about 3.5 inches wide, use 10pt fonts, and export as a
vector PDF or native LaTeX PGF file.

The same workflow applies to any target template: set the figure width to your
venue's column width and adjust the font sizes to suit. The steps are identical
-- only the dimensions and font sizes change.

---

## Step 1: Switch to the Matplotlib Engine

Navigate to the **Manage Plots** page and select the plot you want to prepare
for publication.

In the visualization section, locate the **Engine** selector pills. You should
see two options: **Plotly** and **LaTeX (Matplotlib)**. Click **LaTeX
(Matplotlib)**.

You should see the chart re-render as a static image. The interactive zoom,
pan, and hover features are no longer available, but you now have access to
publication-quality rendering.

### Why Matplotlib?

Matplotlib is the right engine for camera-ready figures for three reasons:

1. **Vector PDF output.** Matplotlib produces true vector PDFs where all lines
   and text remain sharp at any zoom level. There are no rasterization
   artifacts.

2. **PGF/LaTeX-native export.** The PGF format outputs raw LaTeX drawing
   commands. When you include a PGF file in your paper, the figure text is
   rendered by your document's own LaTeX compiler. Fonts match your paper
   automatically.

3. **Precise physical dimensions.** Matplotlib works in inches, so a 3.5-inch
   wide figure is exactly 3.5 inches in the output. Conference templates
   specify column widths in inches, and Matplotlib honors them precisely.

Plotly is excellent for interactive exploration during your analysis, but
always switch to Matplotlib before generating your final figures.

---

## Step 2: Set the Figure Dimensions

With the Matplotlib engine active, click the **Layout** settings pill to open
the layout panel.

In the **Document Size Preset** selector, choose the width that matches your
target template:

- **Single Column (~3.5in)** -- for narrow, single-column figures.
- **Double Column (~7.0in)** -- for full-width figures that span both columns.
- **Custom** -- to enter an exact column width in inches.

You should see the chart resize to the selected dimensions. Set the **Height
(inches)** value to suit your figure content (2.5 inches is a common starting
point for a single-column chart).

Because Matplotlib works in physical inches, the exported figure is exactly the
size you set here, so it drops into your LaTeX column at native size with no
scaling.

### Typography for Publication

Recommended font sizes for a column-width figure are roughly: 10 pt title,
9 pt axis labels, and 8 pt tick labels. You set these in the next step.

---

## Step 3: Fine-Tune Typography

Adjust the text sizes to suit your chart content and your venue's requirements.

Click the **Typography** settings pill to open the typography panel. You
should see controls for:

- **Plot title font size** -- 10 pt is a good default.
- **X-axis title font size** -- 9 pt.
- **Y-axis title font size** -- 9 pt.
- **X-axis tick font size** -- 8 pt.
- **Y-axis tick font size** -- 8 pt.

### When to Adjust

If your chart has long benchmark names on the X-axis (such as
`xalancbmk_r_ref`), the 8pt tick labels may overlap. In that case, you have
two options:

- Reduce the X-axis tick font size to 7 pt.
- Rotate the tick labels using the **Axes** pill (covered in Step 5).

If your chart title is long, consider reducing the title font size to 9 pt or
shortening the title text.

After making changes, click **Refresh Plot** (or enable Auto-refresh) to see
the updated chart.

---

## Step 4: Adjust Margins

Click the **Layout** settings pill to open the layout panel.

You set the figure width and height in Step 2. Leave those values as they are
unless you have a specific reason to change the figure size.

If axis labels or the legend are being clipped at the edges of the figure, you
can increase the margins:

- **Left margin** -- increase if the Y-axis label or tick labels are cut off.
- **Bottom margin** -- increase if rotated X-axis tick labels extend below the
  figure boundary.
- **Right margin** -- increase if a secondary Y-axis label is clipped.
- **Top margin** -- increase if the title is partially hidden.

The Matplotlib PDF, PNG, and SVG exports use `bbox_inches="tight"` by default, which
automatically expands the bounding box to include all visible elements. In most
cases, you will not need to adjust margins manually. **PGF is the exception**: it is
exported *without* tight cropping, so its physical size equals the configured figure
size exactly — this is what lets a `\input{figure.pgf}` fill a known LaTeX column
width. Size a PGF figure via its width/height, not by relying on tight cropping.

---

## Step 5: Configure Axes

Click the **Axes** settings pill (you may need to toggle **Show advanced
settings** first) to open the axis configuration panel.

### X-Axis Settings

In the **X-Axis** sub-pill, you can adjust:

- **Label rotation** -- set the angle for X-axis tick labels. For short labels
  like benchmark abbreviations (`mcf`, `omnetpp`, `xalancbmk`), 0 degrees
  works well. For longer labels, try -45 or -90 degrees.
- **Grid lines** -- for most bar charts in publications, X-axis grid lines
  are turned off.
- **Tick marks** -- show or hide tick marks along the axis.

### Y-Axis Settings

In the **Y-Left** sub-pill, you can adjust:

- **Grid lines** -- horizontal grid lines help readers estimate exact values.
  Consider enabling them for bar charts.
- **Step size** -- set to 0 for automatic tick spacing, or enter a specific
  interval (for example, 0.5 for IPC plots).
- **Axis line width and color** -- reasonable defaults are applied
  automatically, but you can darken or thicken axis lines for emphasis.

After configuring the axes, refresh the plot to verify that all labels are
readable and that grid lines are positioned sensibly.

---

## Step 6: Final Visual Check

Before exporting, perform a visual review:

1. **Title.** Is it concise and descriptive? Conference reviewers scan figures
   quickly.

2. **Axis labels.** Do they include units where appropriate (e.g., "IPC
   (instructions/cycle)" or "Execution Time (ms)")?

3. **Legend.** Is it positioned so that it does not overlap data? If the legend
   obscures bars, open the **Legends** pill and reposition it.

4. **Font sizes.** Are all text elements at least 8 pt? Smaller text becomes
   unreadable when the figure is printed at column width.

5. **Color accessibility.** If your chart uses color to distinguish groups,
   consider adding hatching patterns (via the **Colors** pill) for readers who
   cannot differentiate colors.

---

## Step 7: Export as PDF

Expand the **Download** section below the chart. You should see format pills
for **PDF**, **PGF**, **PNG**, and **SVG**.

Click **PDF** to select the PDF format.

Click the **Download** button. Your browser downloads a file named after your
plot with a `.pdf` extension (for example, `IPC_Comparison.pdf`).

You should see a vector PDF file at exactly the dimensions you set in Step 2.
Open it in a PDF viewer and zoom in -- all text and lines remain perfectly
sharp because the output is fully vectorized.

### Including the PDF in LaTeX

To include the PDF in your LaTeX paper, use:

```latex
\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{figures/IPC_Comparison.pdf}
  \caption{IPC comparison across CPU configurations.}
  \label{fig:ipc-comparison}
\end{figure}
```

Because the figure was exported at exactly the column width, using
`width=\columnwidth` displays it at its native size with no scaling.

---

## Step 8: Export as PGF (LaTeX-Native)

If your paper is compiled with LaTeX, the PGF format provides the tightest
integration.

In the **Download** section, click **PGF** to select the PGF format, then
click the **Download** button. Your browser downloads a `.pgf` file.

### What Makes PGF Special

A PGF file contains native LaTeX drawing commands rather than embedded fonts
or rasterized text. When LaTeX compiles your document, it renders the figure
text using your document's own font settings. This means:

- Fonts in the figure match the rest of your paper automatically.
- Mathematical notation in axis labels (`$\alpha$`, `$\times$`) renders
  correctly.
- The file size is smaller than a PDF with embedded fonts.
- Text in the figure is searchable and selectable in the final PDF.

### Including the PGF in LaTeX

To include the PGF file in your paper:

```latex
\begin{figure}[t]
  \centering
  \input{figures/IPC_Comparison.pgf}
  \caption{IPC comparison across CPU configurations.}
  \label{fig:ipc-comparison}
\end{figure}
```

Note that PGF export uses XeLaTeX by default. If your document uses a
different TeX engine, you can change the TeX system setting in the **Advanced**
settings pill under Engine Controls.

### When PGF Is Not Available

PGF export requires that your chart contains only vector-compatible elements.
If your chart includes rasterized content (for example, a heatmap with many
cells), RING-5 automatically falls back to PDF and displays a warning. In that
case, use the PDF format instead.

---

## Tips for Camera-Ready Figures

### Consistency Across Figures

If your paper contains multiple figures, keep them visually consistent:

- Use the same color palette for all figures. Set it once in the **Colors**
  pill and apply it to every plot.
- Use the same figure dimensions and font sizes across all figures so that text
  and proportions match.
- Use the same Y-axis range across related figures to make comparisons
  accurate.

### Font Size Guidelines

Conference submission guidelines typically require all text in figures to be
readable at the printed size. As a general rule:

| Element     | Minimum Size | Recommended Size |
|-------------|-------------|------------------|
| Title       | 8 pt        | 10 pt            |
| Axis labels | 8 pt        | 9 pt             |
| Tick labels | 6 pt        | 8 pt             |
| Legend text  | 6 pt        | 8 pt             |

Stay at or above 8 pt for all text in the figure.

### Test at Actual Size

After exporting, open the PDF and set your viewer to display it at 100% zoom
(actual size). This shows you exactly how the figure will appear in the
printed paper. Check that:

- All text is legible.
- Bar patterns (hatching) are distinguishable.
- Legend entries are spaced far enough apart to read.

### Other Export Formats

While PDF and PGF are the primary formats for papers, the other formats have
their uses:

- **PNG** -- useful for including figures in presentation slides or draft
  documents. The Matplotlib PNG export uses a publication-grade DPI, which is
  sufficient for most purposes.
- **SVG** -- useful if you need to make manual edits in a vector graphics
  editor like Inkscape before including the figure in your paper.

---

## Summary

In this tutorial, you learned how to:

1. Switch from Plotly to the Matplotlib engine for static, publication-quality
   output.
2. Set the figure dimensions to your target column width in the Layout pill.
3. Fine-tune typography, margins, and axis settings for your specific chart
   content.
4. Export the figure as a vector PDF for use with `\includegraphics{}`.
5. Export the figure as a native LaTeX PGF file for use with `\input{}`.
