# Tutorial: Normalize Data for Fair Comparison

This tutorial shows you how to normalize performance metrics to a baseline
configuration. Normalization is the standard way to present relative speedup in
computer architecture research, where all results are expressed as a factor of a
chosen reference point (1.0 = baseline).

## Prerequisites

Before starting, make sure you have:

- RING-5 running in your browser (typically at `http://localhost:8501`)
- Data loaded with **multiple configurations** to compare (see the
  [Load and Explore Data](load-and-explore.md) tutorial)

Your dataset should contain columns similar to these:

| Column | Example Values |
|--------|---------------|
| `benchmark_name` | `mcf`, `omnetpp`, `xalancbmk` |
| `config_description` | `baseline`, `optimized`, `aggressive` |
| `system.cpu.ipc` | `2.10`, `1.85`, `2.40` |

If you loaded the sample dataset, you have three configurations (`baseline`,
`optimized`, `aggressive`) across three SPEC benchmarks, which is exactly what
you need for this tutorial.

---

## The Scenario

You ran gem5 simulations with three CPU configurations and want to answer the
question: "How much faster is each configuration compared to the baseline?"

Raw IPC numbers like 2.10 versus 2.35 require mental arithmetic to interpret.
Normalized values make the comparison instant: 1.0 means "same as baseline" and
1.12 means "12% faster than baseline." This is the format reviewers and readers
expect in architecture papers and technical reports.

---

## Step 1: Create a Grouped Bar Plot

If you already have a bar chart from the
[Create a Bar Chart](create-bar-chart.md) tutorial, you can reuse it. Otherwise,
create a new one now.

1. Navigate to the **Manage Plots** page from the sidebar.
2. Click **Create New Plot**.
3. Enter the name `Normalized IPC` and select **Grouped Bar** as the plot type.
4. Click **Create**.

### Configure the Plot Columns

In the configuration panel, set the following:

- **X-axis**: Select `benchmark_name`
- **Y-axis**: Select `system.cpu.ipc`
- **Group by**: Select `config_description`

You should see a grouped bar chart with clusters of bars for each benchmark,
one bar per configuration. At this point, the chart shows raw IPC values (for
example, approximately 2.10 for `mcf/baseline` and 2.50 for `mcf/aggressive`).

---

## Step 2: Add a Column Selector Shaper (Optional)

If your dataset has many numeric columns, you can streamline the pipeline by
first selecting only the columns you need. This step is optional but helps keep
the data clean.

1. Scroll to the **Pipeline** section below the chart.
2. Click **Add Shaper** and select **Column Selector** from the dropdown.
3. In the **Columns** multiselect, choose:
   - `benchmark_name`
   - `config_description`
   - `system.cpu.ipc`

You should see the pipeline step appear with your selected columns. The chart
will look the same because you kept all the columns the plot needs.

---

## Step 3: Add the Normalize Shaper

This is the key step. The Normalize shaper divides each metric value by the
corresponding baseline value within each group.

1. Click **Add Shaper** again and select **Normalize** from the dropdown.
2. The Normalize configuration panel will appear with several fields arranged
   in two columns.

### Left Column -- Variables

**Normalizer variables (will be summed)**:
Select `system.cpu.ipc`. These are the columns whose baseline values form the
denominator. In most cases, this is the same as the variable you want to
normalize.

**Variables to normalize**:
Select `system.cpu.ipc`. These are the columns that will be divided by the
baseline value.

**Normalizer column (baseline identifier)**:
Select `config_description`. This is the categorical column that identifies
which row is the baseline.

### Right Column -- Baseline and Grouping

**Baseline value**:
Select `baseline`. This tells the shaper which value in the
`config_description` column represents the reference configuration. Every other
configuration will be expressed relative to this one.

**Group by**:
Select `benchmark_name`. This ensures normalization happens independently for
each benchmark. Without this, the shaper would look for a single global
baseline row instead of one per benchmark.

Leave **Automatically normalize standard deviation columns** checked (the
default). This is useful if your data includes `.sd` columns from repeated
simulation runs.

---

## Step 4: Review the Normalized Result

After adding the Normalize shaper, the chart updates automatically. You should
see a significant change in the Y-axis values.

What to expect:

- **Baseline bars** are all exactly **1.0** (by definition, the baseline divided
  by itself equals 1.0).
- **Optimized bars** show values greater than 1.0. For example, on the `mcf`
  benchmark, the optimized configuration should show approximately **1.12**
  (meaning 12% higher IPC than baseline).
- **Aggressive bars** show even larger values. On `mcf`, you should see
  approximately **1.19** (19% higher IPC than baseline).

The Y-axis now represents relative IPC rather than absolute IPC. A value of
1.15 means "15% more instructions per cycle than baseline."

---

## Step 5: Add Refinements

### Sort by Benchmark Name

Add a **Sort** shaper to control the order of benchmarks on the X-axis.

1. Click **Add Shaper** and select **Sort**.
2. In **Sort by columns**, select `benchmark_name`.
3. In the order expander, arrange the values as desired (for example,
   `mcf`, `omnetpp`, `xalancbmk` for alphabetical order).

### Update the Chart Title

Expand the **Advanced Settings** section and change the title to:

```
Relative IPC (Normalized to Baseline)
```

Update the axis labels to match:

- **X-axis label**: `Benchmark`
- **Y-axis label**: `Relative IPC (Baseline = 1.0)`

You should see the chart with clear, descriptive labels that communicate the
normalization scheme to your audience.

---

## Step 6: Interpret the Results

With normalization applied, the chart tells a clear story at a glance:

| Benchmark | Optimized | Aggressive |
|-----------|-----------|------------|
| `mcf` | ~1.12x | ~1.19x |
| `omnetpp` | ~1.14x | ~1.22x |
| `xalancbmk` | ~1.13x | ~1.23x |

The `aggressive` configuration delivers 19-23% higher IPC than baseline across
all benchmarks. The `optimized` configuration is consistently in the 12-14%
range. These relative numbers are much easier to compare than the raw IPC
values.

---

## Why Normalize?

Normalization is standard practice in computer architecture research for
several important reasons.

**Fair comparison across benchmarks.** Raw metrics vary wildly between
benchmarks. An IPC of 2.10 on `mcf` and 1.85 on `omnetpp` does not mean `mcf`
is "better" -- the benchmarks have fundamentally different characteristics.
Normalization removes the benchmark-specific scale and lets you focus on the
relative effect of each configuration.

**Readable charts.** When all bars cluster around 1.0, readers can instantly
see which configurations improve performance and by how much. A bar at 1.15 is
immediately understood as "15% better."

**Convention in the field.** Conferences like ISCA, MICRO, and HPCA expect
normalized results. Reviewers will look for a clearly identified baseline and
relative performance numbers. Presenting raw metrics without normalization may
lead to confusion about your experimental methodology.

**Combining heterogeneous metrics.** If you later want to compute a geometric
mean across benchmarks (using the Mean shaper), the values must be normalized
first. A geometric mean of raw IPC values is not meaningful because benchmarks
operate at different absolute scales.

---

## Summary

In this tutorial, you learned how to:

- Add a **Normalize** shaper to divide metric values by a baseline reference
- Configure the normalizer column (`config_description`), baseline value
  (`baseline`), variables to normalize (`system.cpu.ipc`), and grouping column
  (`benchmark_name`)
- Interpret normalized results where 1.0 equals the baseline and values above
  1.0 indicate improvement
- Refine the chart with Sort ordering and descriptive titles
- Understand why normalization is essential for architecture research

The Normalize shaper is one of the most important tools in RING-5 for
preparing publication-quality charts. Combined with the Mean shaper (for
computing geometric means across benchmarks), it gives you the standard
analysis pipeline used in architecture papers.

### Next Steps

- [Create a Bar Chart](create-bar-chart.md) -- If you have not yet explored
  basic chart creation
- [Create a Heatmap](create-heatmap.md) -- Visualize many metrics at once in
  a compact grid
