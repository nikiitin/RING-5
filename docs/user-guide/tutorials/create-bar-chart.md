# Tutorial: Create a Bar Chart

This tutorial walks you through creating a bar chart that compares IPC
(Instructions Per Cycle) across different CPU configurations. By the end, you
will have a publication-ready chart showing how each configuration performs on
each benchmark.

## Prerequisites

Before starting, make sure you have:

- RING-5 running in your browser (typically at `http://localhost:8501`)
- Data loaded into the application, either by importing a CSV file or by
  parsing gem5 simulation output (see the
  [Load and Explore Data](load-and-explore.md) tutorial)

Your dataset should contain columns similar to these:

| Column | Example Values |
|--------|---------------|
| `benchmark_name` | `mcf`, `omnetpp`, `xalancbmk` |
| `config_description` | `baseline`, `optimized`, `aggressive` |
| `system.cpu.ipc` | `2.10`, `1.85`, `2.40` |

If you loaded the sample dataset, you already have all of these columns.

---

## Step 1: Navigate to Manage Plots

From the sidebar, click the **Manage Plots** page. This is where you create,
configure, and manage all of your visualizations.

You should see the plot management interface. If you have not created any plots
yet, the main area will be empty with a prompt to create your first plot.

---

## Step 2: Create a New Plot

Click the **Create New Plot** button. A dialog will appear asking you to
configure the new plot.

Fill in the following fields:

- **Plot name**: Enter `IPC Comparison` (or any descriptive name you prefer).
- **Plot type**: Select **Bar Chart** from the dropdown.

Click **Create** to confirm.

You should see your new plot appear in the plot list on the left side of the
page. The plot configuration panel will open on the right, ready for you to
select data columns.

---

## Step 3: Configure Data Columns

The configuration panel is organized into two columns. On the left side, you
will find the axis selectors. On the right side, you will find title and label
fields.

### Select the X-axis

In the **X-axis** dropdown, select `benchmark_name`. This places each benchmark
along the horizontal axis so you can compare them side by side.

### Select the Y-axis

In the **Y-axis** dropdown, select `system.cpu.ipc`. This is the metric you
want to compare -- the number of instructions completed per clock cycle.

### Select the Color column

In the **Color by (optional)** dropdown, select `config_description`. This
groups the bars by CPU configuration, assigning a distinct color to each one
(`baseline`, `optimized`, `aggressive`).

You should see a preview of the chart update automatically. Each benchmark will
have a cluster of colored bars, one per configuration.

---

## Step 4: Apply a Sort Shaper

By default, the benchmarks appear in the order they occur in the dataset. To
make the chart more readable, you can sort the benchmarks alphabetically.

1. Scroll down to the **Pipeline** section below the chart configuration.
2. Click the **Add Shaper** button (or the "+" icon).
3. From the shaper type dropdown, select **Sort**.
4. In the **Sort by columns** multiselect, pick `benchmark_name`.
5. An expander labeled **Order for 'benchmark_name'** will appear. You should
   see the three values: `mcf`, `omnetpp`, `xalancbmk`. They are listed in
   alphabetical order by default. If you want a different order, remove values
   and re-add them in your preferred sequence.

The pipeline processes your data before it reaches the chart. After adding the
Sort shaper, the bars will appear in the order you specified: first `mcf`, then
`omnetpp`, then `xalancbmk`.

You should see the chart update to reflect the new ordering.

---

## Step 5: Review the Rendered Chart

At this point, your bar chart shows:

- **X-axis**: Benchmark names (`mcf`, `omnetpp`, `xalancbmk`)
- **Y-axis**: IPC values (ranging roughly from 1.85 to 2.53)
- **Colors**: One color per configuration (`baseline`, `optimized`, `aggressive`)

Each cluster of bars makes it easy to see that `aggressive` consistently
achieves the highest IPC, followed by `optimized`, then `baseline`. For
example, on the `mcf` benchmark, you should see IPC values near 2.10 for
baseline, 2.35 for optimized, and 2.50 for aggressive.

---

## Step 6: Customize the Chart Appearance

To fine-tune the chart for a presentation or paper, expand the advanced
settings.

### Open Advanced Settings

Click the **Advanced Settings** toggle (or expander) below the main
configuration area. This reveals additional options for titles, layout,
typography, and styling.

### Change the Title

In the **Title** field, replace the auto-generated title with:

```
IPC by Benchmark and CPU Configuration
```

This gives readers an immediate understanding of what the chart shows.

### Adjust Axis Labels

- Set **X-axis label** to `Benchmark`
- Set **Y-axis label** to `Instructions Per Cycle (IPC)`

These labels are clearer than the raw column names.

### Adjust Layout Dimensions

If the chart feels cramped or too wide, you can modify the layout dimensions in
the advanced settings. Common adjustments include:

- **Width**: Try `800` for a standard presentation width.
- **Height**: Try `500` for a balanced aspect ratio.

You should see the chart resize to match your new dimensions.

---

## Step 7: Export the Chart

Once you are satisfied with the chart, you can download it as an image file.

1. Scroll down to the **Download** section (or expand it if collapsed).
2. Select **PNG** as the export format. Other options include SVG and PDF,
   depending on your needs.
3. Click the **Download** button.

The file will be saved to your browser's default download location. PNG is a
good choice for presentations and web pages. For inclusion in LaTeX papers, SVG
or PDF may be preferable since they are vector formats that scale without
losing quality.

---

## Summary

In this tutorial, you learned how to:

- Create a new Bar Chart plot from the Manage Plots page
- Configure the X-axis (`benchmark_name`), Y-axis (`system.cpu.ipc`), and
  Color (`config_description`) columns
- Add a Sort shaper to control the order of benchmarks on the X-axis
- Customize the chart title, axis labels, and layout dimensions using Advanced
  Settings
- Export the finished chart as a PNG image

You now have the foundation for creating any bar chart in RING-5. To compare
metrics across more complex groupings (such as multiple Y-axis columns or
stacked categories), explore the **Grouped Bar** and **Stacked Bar** plot types
from the same Manage Plots page.

### Next Steps

- [Normalize Data for Fair Comparison](normalize-data.md) -- Learn how to
  express performance relative to a baseline configuration
- [Create a Heatmap](create-heatmap.md) -- Visualize many metrics at once in
  a compact grid
