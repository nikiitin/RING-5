# RING-5 User Guide

RING-5 is a data analysis and visualization tool designed for researchers working with the gem5 architectural simulator. It helps you turn raw simulation output into publication-quality plots suitable for venues such as ISCA, MICRO, ASPLOS, and HPCA.

Whether you are comparing CPU configurations across SPEC benchmarks or visualizing cache miss distributions, RING-5 handles the entire pipeline: parsing gem5 stats files, cleaning and transforming data, building plots, and exporting figures with conference-specific formatting presets.

## What You Will Find Here

This guide is organized into five sections.

- **Getting Started** -- Install the application, learn the key concepts, and produce your first plot.
  - [Installation](getting-started/installation.md)
  - [Key Concepts](getting-started/concepts.md)

- **Page Guides** -- Detailed walkthroughs for every page in the application.
  - Data Source -- load simulation data into RING-5.
  - Data Managers -- clean, reduce, and preprocess your dataset.
  - Manage Plots -- create, configure, and render visualizations.
  - Save/Load Portfolio -- persist and restore entire analysis sessions.

- **Features** -- In-depth coverage of individual capabilities.
  - Shaper Pipeline -- per-plot data transformations (filter, sort, normalize, and more).
  - Settings Pills -- fine-grained control over typography, axes, legends, and layout.
  - Export Presets -- one-click formatting for IEEE, ACM, and other conference templates.

- **Tutorials** -- Step-by-step recipes for common research workflows.

- **Reference** -- Plot type catalog, configuration keys, and keyboard shortcuts.

## Quick Start

The fastest path from raw data to a finished plot takes five steps.

1. **Launch the application.** Run `streamlit run app.py` from the project root and open your browser at `http://localhost:8501`. You should see the RING-5 Interactive Analyzer with the Data Source page active.

2. **Load your data.** On the Data Source page, select "I already have CSV data" if you have a preprocessed CSV file, or select "Parse Stats" to point RING-5 at a directory of gem5 `stats.txt` files. After loading, a metrics bar at the top of the page should display the number of rows, columns, and the source file name.

3. **Navigate to Manage Plots.** Click "Manage Plots" in the sidebar. This page is where you create and configure all of your visualizations.

4. **Create a bar chart.** Click "Add Plot," give it a name, and select "Bar" as the plot type. Choose your X-axis variable (for example, benchmark names) and Y-axis variable (for example, IPC). Click "Generate" and you should see a rendered bar chart appear below the configuration panel.

5. **Export the figure.** Scroll down to the download section beneath your plot. Select a format (PNG, PDF, or SVG) and, optionally, apply an export preset such as "ISCA" to set conference-ready dimensions and fonts. Click the download button. The file should save to your browser's default download location.

From here you can refine your plot using the shaper pipeline, adjust styling through the settings pills, or add more plots to your analysis session.

## Requirements

RING-5 requires Python 3.12 or later and runs on Linux, macOS, and Windows. See the [Installation](getting-started/installation.md) page for detailed setup instructions.
