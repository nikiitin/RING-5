---
title: "Key Concepts"
parent: Getting Started
grand_parent: User Guide
nav_order: 2
---

# Key Concepts

This page introduces the core ideas behind RING-5. Understanding these concepts will help you navigate the application and make the most of its features.

## Simulator Data

gem5 produces statistics files (typically named `stats.txt`) that contain performance counters and configuration values from a simulation run. Each variable in these files follows a hierarchical dot-separated naming convention, such as `system.cpu.ipc` or `system.l2cache.overall_misses::total`.

A single research experiment usually involves many stats files -- one per combination of benchmark, hardware configuration, and random seed. RING-5 can parse these files directly or accept pre-processed CSV data.

## Variables

A variable is a single named measurement or setting extracted from a stats file. RING-5 recognizes five variable types:

- **Scalar** -- A single numeric value (e.g., `system.cpu.ipc 1.523`).
- **Vector** -- An indexed set of values (e.g., `system.cpu.op_class::IntAlu 1234`).
- **Distribution** -- Bucketed counts with percentages (e.g., `system.l2.miss_latency::128 45`).
- **Histogram** -- Range-bucketed counts (e.g., `system.mem.bw_read::0-1024 100`).
- **Configuration** -- A key-value setting (e.g., `system.cpu.type=DerivO3CPU`).

When you add variables on the Data Source page, you choose which types and names to extract. RING-5 scans your stats files to show you what is available before you commit to a full parse.

## Entries

After parsing, your data is organized as a table (DataFrame) where each row is called an entry. An entry typically represents one unique combination of benchmark, hardware configuration, and random seed. Columns correspond to the variables you selected for parsing, plus metadata columns that identify the benchmark and configuration.

## Data Managers

Before you create plots, you may need to clean and transform your data. The Data Managers page provides four specialized tools:

- **Seeds Reducer** -- Aggregates multiple random-seed runs into a single representative value (mean, median, or other statistic) per benchmark-configuration pair.
- **Outlier Remover** -- Detects and removes statistical outliers that could skew your results.
- **Preprocessor** -- Applies column-level transformations such as renaming, filtering, or computing derived variables.
- **Mixer** -- Combines entries from different data sources or applies cross-dataset operations.

Each operation you perform is recorded in an operations history, so you can review and understand the transformations applied to your data.

## Plots

RING-5 supports nine plot types, covering the most common visualization needs in computer architecture research:

- **Bar** -- Compare a single metric across categories (e.g., IPC per benchmark).
- **Grouped Bar** -- Compare multiple configurations side by side within each category.
- **Stacked Bar** -- Show how sub-components contribute to a total.
- **Grouped Stacked Bar** -- Combine grouping and stacking for multi-level comparisons.
- **Line** -- Visualize trends over a continuous or ordered axis.
- **Scatter** -- Explore relationships between two numeric variables.
- **Histogram** -- Display the distribution of a single variable.
- **Dual Axis** -- Overlay two metrics with independent Y-axes (bar + dot).
- **Heatmap** -- Represent a matrix of values using color intensity.

You create and manage all plots on the Manage Plots page. Each plot has its own independent configuration, shaper pipeline, and rendering settings.

## Shaper Pipeline

Every plot has a shaper pipeline -- an ordered sequence of data transformations applied to the dataset before the plot is rendered. Shapers let you tailor the data for each individual plot without modifying the underlying dataset.

The available shapers are:

- **Column Selector** -- Keep only the columns relevant to your plot.
- **Item Selector** -- Filter rows by selecting specific values in a column.
- **Condition Selector** -- Filter rows by numeric or categorical conditions.
- **Sort** -- Reorder rows by custom category ordering.
- **Normalize** -- Divide values by a baseline row (e.g., normalize IPC to a reference configuration).
- **Mean Calculator** -- Aggregate rows using arithmetic, geometric, or harmonic mean.
- **Transformer** -- Convert column types (e.g., cast a string column to numeric).
- **Pivot Longer / Pivot Wider** -- Reshape data between long and wide formats.
- **Split-Apply** -- Split data into groups, apply a sub-pipeline to each group, and recombine.

You build your pipeline by adding shapers one at a time. Each shaper receives the output of the previous one, and you can reorder or remove steps as needed.

## Settings Pills

Once a plot is rendered, you can fine-tune its appearance through settings pills -- tabbed configuration panels that appear below the plot. Settings are organized into basic and advanced groups:

- **Basic settings** cover the most common adjustments: display options (title, axis labels), color theme, and plot-type-specific options (e.g., bar orientation).
- **Advanced settings** include typography (font sizes, bold flags), axis configuration (tick angles, grid, ranges), legend placement and styling, and data labels.

A toggle at the top of the settings area switches between basic and advanced modes. Changes take effect immediately when you regenerate the plot.

## Portfolios

A portfolio is a complete snapshot of your RING-5 session saved as a single JSON file. It captures everything: your loaded data, parser configuration, all plots and their shaper pipelines, Data Manager operation history, and every settings adjustment you have made.

You can save and load portfolios from the Save/Load Portfolio page. This is useful for resuming work across sessions, sharing an analysis with collaborators, or archiving a reproducible workflow alongside your paper submission.
