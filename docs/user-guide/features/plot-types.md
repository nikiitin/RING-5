---
title: "Plot Types Reference"
parent: Features
grand_parent: User Guide
nav_order: 1
---

# Plot Types Reference

RING-5 provides nine plot types for visualizing gem5 simulation data. Each type is
designed for a specific kind of analysis, from comparing metrics across benchmarks
to exploring distributions and correlations.

## Creating a Plot

To create a new plot, navigate to the **Plot** page and open the **Manage Plots**
panel. Click **Create New Plot**, enter a name, and select one of the nine plot
types described below. The configuration panel on the left will update to show
the column selectors and options specific to your chosen type.

You can change a plot's type after creation. Open the plot's management options
and select a new type. RING-5 preserves your data pipeline but resets the column
configuration to match the new type's requirements.

---

## Basic Plot Types

These three types cover the most common visualization needs: comparing values,
tracking trends, and exploring relationships between metrics.

### Bar Chart

A bar chart displays rectangular bars whose heights represent the value of a single
metric. Each bar corresponds to one category on the X axis. When you assign a
Color column, bars within each category are grouped side by side, with each color
representing a different value of that column.

**When to use it.** Use a bar chart to compare a single metric across a set of
categories, such as benchmarks, CPU models, or cache configurations. It is the
most straightforward way to answer "which configuration performs best?"

**Required columns.**

| Field | Description |
|-------|-------------|
| X | Categorical column for the horizontal axis (e.g., benchmark name) |
| Y | Numeric column for bar height (e.g., IPC, miss rate) |
| Color (optional) | Categorical column to group bars by color within each X category |

**Example use case.** You want to compare IPC across the SPEC CPU2006 benchmarks
bzip2, gcc, and mcf. Set X to `benchmark`, Y to `ipc`, and leave Color empty.
You should see one bar per benchmark. To break that down by CPU model, set Color
to `cpu_model`. You should see side-by-side bars within each benchmark, one per
CPU model.

---

### Line Chart

A line chart connects data points with lines to show how a metric changes across
an ordered variable. Data points are shown as markers along the line. You can
choose from six interpolation modes (linear, spline, hv, vh, hvh, vhv) in the
advanced settings to control how the line is drawn between points.

**When to use it.** Use a line chart to visualize trends over a continuous or
ordered variable, such as simulation tick count, cache size, or associativity
level. It is the natural choice when the X axis has a meaningful sequential order.

**Required columns.**

| Field | Description |
|-------|-------------|
| X | Ordered column for the horizontal axis (e.g., simulation tick, cache size) |
| Y | Numeric column for the vertical axis (e.g., miss rate, bandwidth) |
| Color (optional) | Categorical column to draw one line per group |

**Example use case.** You want to track how L2 cache miss rate changes as you
increase cache size from 256 KB to 4 MB. Set X to `l2_cache_size`, Y to
`l2_miss_rate`, and Color to `cpu_model`. You should see one line per CPU model,
each showing the trend of miss rate as cache size increases.

---

### Scatter Plot

A scatter plot displays individual data points positioned by their X and Y values.
Each point represents one observation. This type is useful for spotting clusters,
outliers, and correlations between two numeric variables.

**When to use it.** Use a scatter plot to explore the relationship or correlation
between two numeric metrics. It answers questions like "is there a tradeoff between
IPC and energy consumption?" or "do certain configurations cluster together?"

**Required columns.**

| Field | Description |
|-------|-------------|
| X | Numeric column for horizontal position (e.g., IPC) |
| Y | Numeric column for vertical position (e.g., energy) |
| Color (optional) | Categorical column to color-code points by group |

**Example use case.** You want to explore whether there is a correlation between
IPC and power consumption across all your simulation runs. Set X to `ipc`, Y to
`power_watts`, and Color to `cpu_model`. You should see a cloud of points with
each CPU model in a different color, revealing whether higher IPC comes at
a power cost.

---

## Comparison Plot Types

These four types extend the basic bar chart with grouping, stacking, and
dual-axis capabilities for richer comparisons.

### Grouped Bar

A grouped bar chart organizes bars into major categories along the X axis, with
each major category subdivided into groups. Unlike the basic bar chart with a
Color column, the grouped bar provides explicit control over group ordering,
visual separators between categories, alternating shading, and gap isolation
for summary groups.

**When to use it.** Use a grouped bar when you need fine control over how two
categorical variables interact. It works well for side-by-side comparison of a
metric across benchmarks grouped by configuration, or vice versa.

**Required columns.**

| Field | Description |
|-------|-------------|
| X | Outer category column (e.g., benchmark) |
| Y | Numeric column for bar height (e.g., execution time) |
| Group (optional) | Inner grouping column (e.g., CPU model) |

**Additional options.** You can enable vertical separator lines between categories,
alternating background shading, and an isolation gap before the last category
(useful for separating a "geometric mean" summary bar from individual results).

**Example use case.** You want to compare execution time across benchmarks bzip2,
gcc, mcf, and a geometric mean summary bar, grouped by CPU model (O3, Minor,
Timing). Set X to `benchmark`, Y to `sim_seconds`, and Group to `cpu_model`.
Enable "Isolate Last Group" to visually separate the geometric mean. You should
see clusters of bars per benchmark with a clear gap before the summary.

---

### Stacked Bar

A stacked bar chart displays multiple numeric columns as colored segments stacked
on top of each other within a single bar. The total bar height represents the sum
of all segments. Optional total annotations display the sum above each bar.

**When to use it.** Use a stacked bar to show the composition or breakdown of a
total metric. It answers "what fraction of total execution time is spent in each
pipeline stage?" or "how do cache hit, miss, and MSHR contributions add up?"

**Required columns.**

| Field | Description |
|-------|-------------|
| X | Categorical column for the horizontal axis (e.g., benchmark) |
| Y Columns | Two or more numeric columns to stack (e.g., fetch_time, decode_time, execute_time) |

**Additional options.** You can enable total annotations above bars with
configurable format, font size, position (inside or outside), and a threshold
to hide totals below a minimum value.

**Example use case.** You want to show the breakdown of CPU pipeline stage
latencies for each benchmark. Set X to `benchmark` and select `fetch_cycles`,
`decode_cycles`, `execute_cycles`, and `commit_cycles` as Y Columns. Enable
"Show Totals" to display the total cycles above each bar. You should see each
benchmark bar divided into colored segments representing each pipeline stage.

---

### Grouped Stacked Bar

A grouped stacked bar chart combines the stacking of multiple metrics with the
grouping of categories. Each major category (outer group) contains multiple
sub-groups (inner groups), and each sub-group bar is composed of stacked segments.
This is the most feature-rich plot type in RING-5.

**When to use it.** Use a grouped stacked bar when you need to compare both the
total and the composition of a metric across two categorical dimensions. It handles
scenarios like "compare pipeline stage breakdown across benchmarks, grouped by CPU
model."

**Required columns.**

| Field | Description |
|-------|-------------|
| X | Major group column, the outer category (e.g., benchmark) |
| Group | Minor group column, the inner sub-groups (e.g., CPU model) |
| Y Columns | Two or more numeric columns to stack on the left Y axis |

**Additional options.** This type supports dual-axis mode, where you can assign
additional columns to a secondary Y axis rendered as bars or dots. You can also
enable numbered X-axis labels (replacing long names with numbers and a legend),
custom ordering and renaming of both major and minor groups, and separate legend
management for left and right axis series.

**Example use case.** You want to compare the cache hit/miss breakdown across
benchmarks grouped by CPU model, with IPC shown as dots on a secondary Y axis.
Set X to `benchmark`, Group to `cpu_model`, select `l1_hits` and `l1_misses` as
Y Columns, enable Dual Axis, and add `ipc` as a right-axis column with type
"dots." You should see stacked bars for each CPU model within each benchmark,
with dot markers overlaid showing IPC on the right axis.

---

### Dual Axis Bar Dot

A dual axis bar dot chart overlays two different metrics on the same plot using
two Y axes. The primary metric is displayed as bars (left Y axis) and the
secondary metric as dot markers or connected lines (right Y axis). This lets
you compare metrics that have different scales or units.

**When to use it.** Use a dual axis bar dot chart when you need to compare two
metrics side by side that have different units or ranges. For example, comparing
execution time (seconds) against IPC (ratio) on the same chart.

**Required columns.**

| Field | Description |
|-------|-------------|
| X | Categorical column for the horizontal axis (e.g., benchmark) |
| Y Bar | Numeric column for bars on the left Y axis (e.g., sim_seconds) |
| Y Dot | Numeric column for dots on the right Y axis (e.g., ipc) |
| Color (optional) | Categorical column to group both bars and dots by color |

**Additional options.** You can toggle line connections between dots, adjust dot
symbol and size, set a custom dot color, and isolate the last X category (to
disconnect a summary point from the trend line).

**Example use case.** You want to show execution time as bars and IPC as connected
dots across benchmarks. Set X to `benchmark`, Y Bar to `sim_seconds`, and Y Dot
to `ipc`. Enable "Show Lines" to connect the dots. You should see bars and a
line with markers sharing the same X axis, with separate Y axis scales on the
left and right.

---

## Distribution Plot Types

These two types help you explore data distributions and patterns across
multi-dimensional spaces.

### Histogram

A histogram shows the distribution of a single numeric variable by dividing its
range into bins and displaying the count (or normalized value) of observations
in each bin as bars. RING-5 histograms work with pre-binned data where columns
follow a specific naming convention.

**When to use it.** Use a histogram to understand the distribution of a metric,
such as "how are memory access latencies distributed?" or "what is the shape of
the IPC distribution across all simulation runs?"

**Required columns.**

| Field | Description |
|-------|-------------|
| Histogram Variable | The base variable name; RING-5 detects matching columns that follow the `variable..low-high` naming convention for pre-computed bins |
| Group By (optional) | Categorical column to overlay multiple distributions |

**Additional options.** You can choose a normalization mode (count, probability,
percent, or density), enable cumulative distribution, and adjust bin size for
density normalization.

**Example use case.** Your data contains pre-binned memory latency columns like
`mem_latency..0-10`, `mem_latency..10-20`, and so on. Select `mem_latency` as
the Histogram Variable and set Group By to `cpu_model`. You should see overlaid
histograms (one per CPU model) showing how memory access latencies are
distributed.

---

### Heatmap

A heatmap displays a two-dimensional grid where color intensity represents the
value of a metric. Rows correspond to selected metric columns, columns correspond
to categories from the X axis, and each cell is colored according to its
aggregated value.

**When to use it.** Use a heatmap to get a bird's-eye view of how multiple
metrics vary across configurations. It is effective for spotting patterns,
identifying outliers, and comparing many metrics at once when bar charts would
be too cluttered.

**Required columns.**

| Field | Description |
|-------|-------------|
| X | Categorical column for grid columns (e.g., benchmark or configuration name) |
| Metric Columns | Two or more numeric columns shown as grid rows (e.g., ipc, l1_miss_rate, l2_miss_rate) |
| Facet Column (optional) | Categorical column to create separate sub-heatmaps |

**Additional options.** You can select an aggregation function (mean, sum, min,
max, median, or first), choose a color palette, reverse the color scale, toggle
cell value annotations, and set a display format. Conditional text display lets
you show values only above or below a threshold.

**Example use case.** You want to compare IPC, L1 miss rate, and L2 miss rate
across all SPEC benchmarks for a given CPU model. Set X to `benchmark`, select
`ipc`, `l1_miss_rate`, and `l2_miss_rate` as Metric Columns, and enable "Show
Values." You should see a colored grid where each row is a metric and each
column is a benchmark, with numeric values displayed in each cell.

---

## Choosing the Right Plot Type

Use this decision guide to select the plot type that best fits your analysis
question.

### By analysis goal

| Your question | Recommended plot type |
|---------------|----------------------|
| How does a single metric compare across categories? | Bar Chart |
| How does a metric compare across two categorical variables? | Grouped Bar |
| What is the composition or breakdown of a metric? | Stacked Bar |
| How does composition compare across two grouping dimensions? | Grouped Stacked Bar |
| How does a metric trend over an ordered variable? | Line Chart |
| Is there a correlation between two metrics? | Scatter Plot |
| What is the distribution of a metric? | Histogram |
| How do two metrics with different scales compare? | Dual Axis Bar Dot |
| How do many metrics vary across many configurations at once? | Heatmap |

### By data shape

| Your data looks like... | Recommended plot type |
|-------------------------|----------------------|
| One numeric column, one categorical column | Bar Chart |
| One numeric column, two categorical columns | Grouped Bar |
| Multiple numeric columns, one categorical column | Stacked Bar or Heatmap |
| Multiple numeric columns, two categorical columns | Grouped Stacked Bar |
| One numeric column, one ordered column | Line Chart |
| Two numeric columns | Scatter Plot |
| Pre-binned distribution columns | Histogram |
| Two numeric columns with different units | Dual Axis Bar Dot |

### Common gem5 scenarios

**Comparing benchmark performance.** Start with a Bar Chart. If you need to
break down by CPU model, switch to Grouped Bar. If you need to show pipeline
stage contributions, use Stacked Bar.

**Sensitivity studies.** When sweeping a parameter (cache size, issue width,
frequency), use a Line Chart with the swept parameter on the X axis and the
metric of interest on the Y axis. Set Color to distinguish different
configurations.

**Multi-metric dashboards.** When you need to present many metrics across many
configurations in a compact form, use a Heatmap. It lets reviewers quickly spot
which configuration-metric combinations are outliers.

**Performance-power tradeoffs.** Use a Scatter Plot with IPC on one axis and
power or energy on the other. Use Color to distinguish CPU models or
configurations and look for Pareto-optimal points.

**Dual-metric comparison.** When a paper figure needs to show both execution
time and IPC on the same chart, use Dual Axis Bar Dot. Bars convey the absolute
metric while dots show the ratio metric on a separate scale.
