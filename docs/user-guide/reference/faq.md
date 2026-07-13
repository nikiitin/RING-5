---
title: "Frequently Asked Questions"
parent: Reference
grand_parent: User Guide
nav_order: 1
---

# Frequently Asked Questions

This page answers common questions about using RING-5. If your question is not covered here, check the tutorials and page-specific guides in the User Guide.

---

## Data Loading

### How do I load data?

There are two ways to get data into RING-5:

1. **gem5 stats parsing** -- On the Data Source page, point RING-5 at a directory containing gem5 `stats.txt` files. The tool scans for available variables, lets you select the ones you need, and parses them into a structured table.
2. **CSV upload** -- Upload a pre-processed CSV file on the Data Source page. This works for data from any source, not just gem5.

See the Getting Started guide for a step-by-step walkthrough of both methods.

### What CSV format does RING-5 expect?

Your CSV file must include a header row and at least two metadata columns:

- `benchmark_name` -- identifies the benchmark or workload for each row.
- `config_description` -- identifies the hardware configuration or experiment variant.

All other columns should contain numeric values representing the variables you want to analyze and plot. Each row typically represents one simulation run or one aggregated data point.

### Can I work with simulators other than gem5?

The RING-5 architecture is designed to support multiple simulators through a pluggable parser registry. However, currently only the gem5 parser is implemented.

If you use a different simulator, you can export your results to CSV using the required column format described above and load them into RING-5 that way.

---

## Plotting

### Why is my plot empty?

An empty plot usually means one of the following:

- **No data loaded.** Go to Data Managers and check the Summary section. You should see a row count greater than zero. If the table is empty, return to Data Source and reload your data.
- **Column assignments are wrong.** When creating a plot, verify that the X-axis and Y-axis columns point to columns that actually exist in your dataset and contain numeric data.
- **Filters are too restrictive.** If you have shapers in the plot's shaper pipeline that filter data, they may have removed all rows. Check the shaper pipeline and adjust or remove overly strict filters.

### How do I change the plot type?

RING-5 does not support changing the type of an existing plot in place. To switch from a bar chart to a line chart, for example, create a new plot with the desired type on the Manage Plots page. You can then delete the old plot if you no longer need it.

### What is the difference between Plotly and Matplotlib?

RING-5 supports two rendering engines:

- **Plotly** -- produces interactive charts. You can zoom, pan, hover over data points for tooltips, and toggle series visibility by clicking the legend. Plotly is best for data exploration during your analysis workflow.
- **Matplotlib** -- produces static, publication-quality figures. Matplotlib supports the PGF export format (LaTeX-native vectors) and generally gives you more precise control over the final output. Use Matplotlib when you are ready to export figures for a paper.

You can switch between engines using the engine selector in the Advanced settings pill.

### How do I make plots match conference requirements?

Switch to the Matplotlib engine and set the figure dimensions in the **Layout** settings pill. Choose **Single Column (~3.5in)** or **Double Column (~7.0in)** for the standard two-column paper widths, or **Custom** to enter an exact column width in inches. Because Matplotlib works in physical inches, the exported figure is exactly the size you set.

Adjust font sizes in the **Typography** pill (8 pt or larger is recommended for readability at column width), then export as PDF or PGF for the best results in LaTeX documents.

---

## Data Management

### Can I undo data manager operations?

There is no step-by-step undo button for individual data manager operations. If you need to revert changes:

1. **Reload from Data Source.** Return to the Data Source page and re-parse or re-upload your data. This resets the dataset to its original state.
2. **Save a portfolio first.** Before making significant changes, save a portfolio snapshot on the Portfolio page. You can restore this snapshot later to return to the previous state.

### What does the shaper pipeline do?

The shaper pipeline is a per-plot sequence of data transformations. Shapers modify the data that a specific plot sees without changing the underlying dataset shared by all plots.

Common shaper operations include filtering rows, sorting values, selecting specific columns, normalizing data against a baseline, and computing derived values. Each shaper step is configured independently, and the steps execute in order from top to bottom.

---

## Saving and Exporting

### How do I save my work?

Use the **Portfolio** page to save a complete workspace snapshot. A portfolio stores all loaded data, plot configurations, shaper pipelines, and visual settings. You can reload a portfolio later to resume exactly where you left off.

For individual figures, use the Download section below each chart to export as PNG, SVG, PDF, or PGF.

### What export format should I use for my LaTeX paper?

For LaTeX documents, **PDF** and **PGF** are the recommended formats:

- **PDF** works with `\includegraphics{}` and is compatible with both Plotly and Matplotlib engines.
- **PGF** is a LaTeX-native vector format that inherits your document's fonts. It produces the tightest integration between figures and body text, but is only available with the Matplotlib engine.

For both formats, switch to the Matplotlib engine and set the figure dimensions in the Layout settings pill (for example, Double Column for a two-column paper) before downloading.

---

## Troubleshooting

### The application is slow or unresponsive.

Try pressing `C` to clear the Streamlit cache, then `R` to rerun. If the dataset is very large, consider reducing it with the Seeds Reducer or filtering out unnecessary rows using the Preprocessor on the Data Managers page.

### My exported figure looks different from the preview.

The on-screen preview uses the Plotly engine by default, while publication exports typically use Matplotlib. Visual differences between the two engines are expected. Always check the exported file directly to verify the final appearance. If you need the export to match the preview closely, export from the same engine you used for previewing.
