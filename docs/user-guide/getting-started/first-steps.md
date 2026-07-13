---
title: "First Steps with RING-5"
parent: Getting Started
grand_parent: User Guide
nav_order: 3
redirect_from:
  - /webapp/Quick-Start/
  - /Quick-Start/
---

# First Steps with RING-5

This guide walks you through a complete analysis session -- from launching the
application to saving a finished portfolio. By the end, you will have loaded
data, created a bar chart comparing CPU performance across configurations, and
exported the result.

**Prerequisites**: RING-5 is installed and its dependencies are available.
See the [Installation Guide](installation.md) if you have not set up the
application yet.

---

## 1. Launch the Application

Open a terminal in the project root directory and run:

```bash
streamlit run app.py
```

Your default browser should open automatically at `http://localhost:8501`. You
should see the RING-5 Interactive Analyzer with a sidebar on the left containing
five navigation buttons: **Data Source**, **Data Managers**, **Manage Plots**,
**Save/Load Portfolio**, and **Documentation**.

The sidebar is your primary means of moving between pages. Below the navigation
buttons you will also find **Clear Data** and **Reset All** controls for
starting fresh at any point.

The application starts on the **Data Source** page, which is the first step of
the analysis workflow.

---

## 2. Load Data via CSV

The Data Source page presents an info box describing the available input methods,
followed by a segmented control with three options:

- **Parse Stats Files** -- for raw gem5 simulator output
- **I already have CSV data** -- for pre-processed CSV files
- **Load from Recent** -- for previously loaded CSV files

For this walkthrough you will use a prepared sample dataset. Select
**I already have CSV data** from the segmented control.

### About the Sample Data

The sample dataset (`tests/e2e/fixtures/sample_data.csv`) contains simulated
gem5 output for a small benchmark suite. It has **18 rows** and **8 columns**:

| Column | Description |
|--------|-------------|
| `benchmark_name` | Workload name (mcf, omnetpp, xalancbmk) |
| `config_description` | CPU configuration (baseline, optimized, aggressive) |
| `seed` | Random seed for the simulation run (0 or 1) |
| `system.cpu.ipc` | Instructions per cycle |
| `system.cpu.numCycles` | Total CPU cycles |
| `simTicks` | Simulated time in ticks |
| `system.cpu.dcache.overall_miss_rate` | L1 data cache miss rate |
| `system.cpu.committedInsts` | Number of committed instructions |

The data represents 3 benchmarks across 3 configurations with 2 seeds each
(3 x 3 x 2 = 18 rows). This is a typical structure for gem5 experiments where
you sweep configurations and repeat with multiple seeds for statistical
confidence.

Once the data is loaded into the session, a summary bar appears at the top of
the main content area showing the row count, column count, and source filename.

---

## 3. Explore Your Data

Click the **Data Managers** button in the sidebar to navigate to the Data
Managers page.

You should see a header reading **Data Managers & Transformations** followed by
an info box and a row of seven tabs:

- **Summary** -- dataset shape and statistics
- **Data Visualization** -- interactive dataframe preview
- **Seeds Reducer** -- aggregate across seeds
- **Outlier Remover** -- remove statistical outliers
- **Preprocessor** -- derive or rename columns
- **Mixer** -- merge multiple datasets
- **Operations History** -- audit trail of transformations

### Summary Tab

The Summary tab is selected by default. You should see the dataset shape
(18 rows, 8 columns), column data types, and descriptive statistics for the
numeric columns. This is a quick sanity check that your data loaded correctly.

### Data Visualization Tab

Click the **Data Visualization** tab. You should see the full dataframe rendered
as an interactive table. You can sort by any column by clicking its header, and
scroll through all 18 rows.

For this walkthrough you do not need to apply any transformations. The sample
data is already clean and ready for plotting.

---

## 4. Create Your First Bar Chart

Click the **Manage Plots** button in the sidebar. You should see the
**Manage Plots** page with a **Create Plot** form at the top.

### Create the Plot

The form contains three fields in a single row:

1. **New plot name** -- a text field with a default name (e.g., "Plot 1").
   Change it to something descriptive like "IPC by Benchmark".
2. **Plot type** -- a dropdown listing all available types. Select **Bar**.
3. **Create Plot** -- a submit button. Click it to create the plot.

You should see the new plot appear in the plot selector dropdown below the
creation form.

### Configure the Axes

After creating the plot, the visualization section appears with column selector
widgets. You will see two columns of controls:

**Left column -- Axis selectors:**

- **X-axis**: Select `benchmark_name` from the dropdown. This places benchmark
  names along the horizontal axis.
- **Y-axis**: Select `system.cpu.ipc` from the dropdown. This sets IPC as the
  measured value on the vertical axis.
- **Color by (optional)**: Select `config_description`. This groups bars by
  configuration, so each benchmark shows one bar per configuration side by side.

**Right column -- Labels:**

- **Title**: Auto-populated as "system.cpu.ipc by benchmark_name". You can
  change this to something cleaner like "IPC Comparison by Benchmark".
- **X Label**, **Y Label**, **Legend Title**: Adjust these as desired.

### Render the Chart

If auto-refresh is enabled (the default), the chart renders automatically as
you change settings. If not, click the **Refresh** button to generate the
figure.

You should see a grouped bar chart with three clusters (one per benchmark),
each containing three bars colored by configuration. The baseline configuration
should show the lowest IPC, while aggressive shows the highest, matching the
expected trend where more aggressive CPU pipelines achieve higher throughput.

---

## 5. Customize the Plot

Below the chart you will find a **Show advanced settings** toggle. By default,
three settings pills are visible:

- **Layout** -- chart dimensions (width, height) and margins
- **Typography** -- font sizes for title, axis labels, and tick marks
- **Legends** -- legend position, orientation, and visibility

Click the **Layout** pill to open the layout settings. You can adjust the chart
width and height to fit your needs. The chart updates when you apply changes.

### Enable Advanced Settings

Toggle **Show advanced settings** to reveal four additional pills:

- **Axes** -- axis range, tick formatting, grid lines
- **Data Labels** -- value annotations on bars
- **Colors** -- color palette and individual series colors
- **Advanced** -- bar mode, opacity, and other fine-grained options

For example, click the **Typography** pill and change the title font size to
make the heading more prominent. You should see the chart update to reflect
your changes.

---

## 6. Export the Plot

Below the rendered chart, look for the **Download** expander (collapsed by
default). Click it to expand the download section.

You will see a row of format pills. The default rendering engine is Plotly,
which provides four export formats:

- **HTML** -- interactive chart you can open in any browser
- **PNG** -- raster image suitable for presentations
- **SVG** -- scalable vector graphic for publications
- **PDF** -- portable document for printing

Select **PNG** by clicking its pill. Then click the **Download PNG** button.
Your browser will download a file named after your plot (e.g.,
`IPC by Benchmark.png`).

> **Tip**: For publication-quality figures, consider switching to the
> Matplotlib rendering engine using the engine selector pills above the chart.
> Matplotlib supports PGF export, which produces native LaTeX vector output
> suitable for direct inclusion in TeX documents. Set the figure dimensions in
> the Layout settings pill (for example, Double Column for a two-column paper)
> to match your target column width.

---

## 7. Save Your Work

Click the **Save/Load Portfolio** button in the sidebar. You should see the
**Portfolio Management** page divided into two columns: **Save Portfolio** on
the left and **Load Portfolio** on the right.

### Save a Portfolio

1. In the **Save Portfolio** column, type a name in the text field -- for
   example, "IPC Analysis Session".
2. Click the **Save** button.

You should see a success message confirming the portfolio was saved. The
portfolio captures a complete snapshot of your session: the loaded data, all
plots with their configurations, pipeline steps, and operation history.

### Manage Saved Portfolios

Below the save/load columns, a **Manage Saved Portfolios** section lists all
saved portfolios as expandable cards. Each card shows the portfolio contents
and includes a **Delete** button.

Portfolios are stored as JSON files in the `.ring5/portfolios/` directory
within your project. You can share these files with collaborators, and they
can load them from the same page to reproduce your exact analysis state.

---

## What's Next

You have completed a full cycle: loading data, inspecting it, creating a plot,
customizing it, exporting it, and saving your session. Here are some directions
to explore further:

- **[Data Source](../pages/data-source.md)** -- Learn how to parse raw gem5
  stats files directly, configure variable extraction, and use the scanner to
  auto-discover simulation metrics.

- **[Data Managers](../pages/data-managers.md)** -- Aggregate across seeds
  with the Seeds Reducer, remove outliers, derive new columns, or mix multiple
  datasets together.

- **[Portfolio](../pages/portfolio.md)** -- Deep dive into saving, loading,
  and sharing analysis sessions with your team.

- **Additional Plot Types** -- Beyond bar charts, RING-5 supports line plots,
  scatter plots, histograms, heatmaps, grouped bar, stacked bar, grouped
  stacked bar, and dual-axis bar-dot plots. Experiment with these on the
  Manage Plots page.

- **Publication-quality export** -- Switch to the Matplotlib engine, set the
  figure width to your venue's column width in the Layout pill, and export PDF
  or LaTeX-native PGF to produce camera-ready figures.
