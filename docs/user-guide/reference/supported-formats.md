---
title: "Supported Formats"
parent: Reference
grand_parent: User Guide
nav_order: 2
---

# Supported Formats

This reference lists all file formats that RING-5 can read and write.

---

## Input Formats

### gem5 stats.txt Files

RING-5 can parse statistics files produced by the gem5 simulator. These files are typically named `stats.txt` and contain hierarchical, dot-separated variable names with numeric values.

Each stats file represents one simulation run (a unique combination of benchmark, hardware configuration, and random seed). RING-5 scans these files to discover available variables, then extracts the ones you select into a structured table.

Variable types recognized during parsing include scalars, vectors, distributions, histograms, and configuration entries. See the Key Concepts page for details on each type.

### CSV Files

You can upload pre-processed data as CSV files. This is useful when your data comes from a custom pipeline, a different simulator, or manual preparation.

Your CSV must include these two metadata columns:

- `benchmark_name` -- identifies the benchmark or workload for each row.
- `config_description` -- identifies the hardware configuration or experiment variant.

All additional columns should contain numeric data representing the variables you want to plot. Each row represents one entry (typically one simulation run or one aggregated result).

The CSV must have a header row. Values should be numeric (integer or floating-point). Missing values can be left as empty cells.

---

## Export Formats

When you export a plot from the Download section, four formats are available. The exact set depends on which rendering engine is active (Plotly or Matplotlib).

### PNG (Raster Image)

- **Engines**: Plotly, Matplotlib
- **File extension**: `.png`
- **Best for**: Drafts, slide decks, quick sharing.

PNG produces a bitmap image at the configured DPI (default 300). The image looks sharp at its native resolution but may appear pixelated if scaled up significantly.

### SVG (Scalable Vector Graphics)

- **Engines**: Plotly, Matplotlib
- **File extension**: `.svg`
- **Best for**: Web pages, editing in vector tools (Inkscape, Adobe Illustrator).

SVG is a vector format that scales to any size without quality loss. Text remains selectable and editable in vector editors.

### PDF (Portable Document Format)

- **Engines**: Plotly, Matplotlib
- **File extension**: `.pdf`
- **Best for**: LaTeX papers, print-quality documents.

PDF produces a vector figure that you can include directly in LaTeX with `\includegraphics{}`. Text is embedded as vector outlines, ensuring consistent rendering across systems.

### PGF (LaTeX-Native Vector)

- **Engine**: Matplotlib only
- **File extension**: `.pgf`
- **Best for**: LaTeX documents where font consistency with the body text is critical.

PGF is a LaTeX-native format. When included in a LaTeX document with `\input{}` or the `pgf` package, the figure inherits the document's fonts and text styling automatically. This produces the tightest visual integration between figures and body text. PGF export is only available when the Matplotlib rendering engine is active.

### HTML (Interactive)

- **Engine**: Plotly only
- **File extension**: `.html`
- **Best for**: Interactive exploration, sharing with collaborators who want to zoom and hover.

HTML produces a self-contained interactive chart. Recipients can zoom, pan, hover for data values, and toggle series visibility in their web browser.

---

## Portfolio Format

RING-5 uses an internal JSON-based format to save and restore complete workspace snapshots on the Portfolio page. A portfolio file stores:

- All loaded datasets and their transformation history.
- Every plot configuration, including shaper pipelines and visual settings.
- The current state of the application session.

Portfolio files are intended for use within RING-5 only. They are not designed for exchange with other tools.

---

## Format Compatibility Summary

The following table summarizes which formats work with each rendering engine.

| Format | Plotly Engine | Matplotlib Engine | Vector/Raster |
|--------|:------------:|:-----------------:|:-------------:|
| PNG | Yes | Yes | Raster |
| SVG | Yes | Yes | Vector |
| PDF | Yes | Yes | Vector |
| PGF | No | Yes | Vector (LaTeX) |
| HTML | Yes | No | Interactive |

When choosing a format, consider your end use. For conference papers and journals, use PDF or PGF with the Matplotlib engine. For presentations, PNG at high DPI or SVG works well. For sharing interactive results with collaborators, use HTML from the Plotly engine.
