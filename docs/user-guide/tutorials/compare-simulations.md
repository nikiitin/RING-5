# Comparing Simulations with Multiple Seeds

This tutorial walks you through analyzing gem5 simulation data that includes
multiple random seeds per configuration. You will learn how to reduce repeated
runs into statistically meaningful averages, create a grouped bar chart from
the reduced data, and interpret the results to compare CPU configurations.

## Why Multiple Seeds Matter

gem5 simulations can produce slightly different results depending on
randomization in the memory system, branch predictor warm-up, and OS
interaction modeling. Running each configuration with multiple random seeds
gives you statistical confidence that observed differences are real, not
artifacts of a single random run.

A typical multi-seed experiment runs each (benchmark, configuration) pair two
or more times with different seed values. The sample dataset used in this
tutorial runs 3 benchmarks across 3 configurations with 2 seeds each,
producing 18 total rows.

---

## Prerequisites

Before starting this tutorial, you should have:

- A working RING-5 installation.
- The sample dataset loaded. You can find it at
  `tests/e2e/fixtures/sample_data.csv` in the RING-5 repository. Load it on
  the **Data Source** page.

If you have your own multi-seed gem5 data, you can follow the same steps. The
key requirement is that your data contains a column distinguishing seeds (such
as `seed`, `random_seed`, `iteration`, or `run_id`).

---

## Step 1: Understand the Sample Data

After loading the sample dataset on the Data Source page, navigate to the
**Data Managers** page. Click the **Summary** tab.

You should see the following metrics at the top:

- **Rows**: 18
- **Columns**: 8

The dataset contains these columns:

| Column               | Type        | Description                              |
|----------------------|-------------|------------------------------------------|
| benchmark_name       | categorical | Benchmark program (mcf, omnetpp, xalancbmk) |
| config_description   | categorical | CPU configuration (baseline, optimized, aggressive) |
| seed                 | numeric     | Random seed identifier (0 or 1)          |
| system.cpu.ipc       | numeric     | Instructions per cycle                   |
| system.cpu.numCycles | numeric     | Total CPU cycles                         |
| simTicks             | numeric     | Simulated ticks                          |
| system.cpu.dcache.overall_miss_rate | numeric | Data cache miss rate        |
| system.cpu.committedInsts | numeric | Committed instructions                  |

The 18 rows come from 3 benchmarks x 3 configurations x 2 seeds. For example,
the benchmark `mcf` with `baseline` configuration appears twice: once with
seed 0 and once with seed 1. The IPC values for these two runs are 2.10 and
2.15 respectively -- close but not identical, which is exactly why multiple
seeds are necessary.

---

## Step 2: Reduce Seeds in Data Managers

You want to collapse the two seed runs for each (benchmark, configuration)
pair into a single mean value. The **Seeds Reducer** tab in Data Managers does
exactly this.

### Open the Seeds Reducer

Click the **Seeds Reducer** tab. You should see an info box explaining the
purpose of the reducer, followed by configuration controls.

### Select the Column to Reduce Over

The first control is a dropdown labeled **Column to reduce over**. This is the
column whose values represent independent repeated runs.

Select **seed** from the dropdown. This tells the reducer that rows sharing
the same benchmark and configuration but differing in the `seed` column are
repeated measurements that should be averaged.

### Choose Group-By Columns

In the left panel labeled **Group by columns**, you should see a multiselect
widget with the categorical columns pre-selected. Make sure the following
columns are selected:

- `benchmark_name`
- `config_description`

These columns define what constitutes a unique configuration. All rows with
the same benchmark name and configuration description (but different seed
values) will be grouped together.

### Choose Numeric Columns

In the right panel labeled **Calculate stats for**, you should see all numeric
columns pre-selected. Keep all of them selected:

- `system.cpu.ipc`
- `system.cpu.numCycles`
- `simTicks`
- `system.cpu.dcache.overall_miss_rate`
- `system.cpu.committedInsts`

The reducer computes the arithmetic mean across seeds for each of these
columns.

### Apply the Reduction

Click **Apply Seeds Reducer**.

You should see a success message: **"Reduced from 18 to 9 rows!"** Two metric
cards confirm the reduction: Original Rows (18) and Reduced Rows (9). A
preview table shows the first rows of the reduced dataset.

The 9 remaining rows represent the 3 benchmarks x 3 configurations, each with
seed-averaged values. For example, the `mcf` / `baseline` row now shows an
IPC of 2.125 (the mean of 2.10 and 2.15).

### What the Reducer Creates

For each numeric column, the reducer produces two output columns:

- The original column name, now containing the **mean** across seeds.
- A companion column with a `.sd` suffix containing the **standard deviation**.

For example, `system.cpu.ipc` becomes the mean IPC, and a new column
`system.cpu.ipc.sd` contains the standard deviation of IPC across the two
seeds.

These `.sd` columns are recognized throughout RING-5. If you later normalize
your data in a shaper pipeline, the standard deviation columns are
automatically scaled by the same baseline value. If you enable error bars in
your plot settings, they are drawn from these `.sd` columns.

### Confirm the Reduction

Review the preview table to verify the values look correct. Then click
**Confirm and Apply Seeds Reducer**.

You should see a confirmation toast. The working dataset is now the 9-row
reduced version.

---

## Step 3: Verify the Reduced Data

Click the **Summary** tab to confirm the reduction took effect.

You should see:

- **Rows**: 9
- **Columns**: 13 (the original 8 minus the `seed` column, plus 5 new `.sd`
  columns)

Click the **Data Visualization** tab to browse the full reduced dataset. Each
row represents a unique (benchmark, configuration) pair with averaged metrics.

---

## Step 4: Create a Grouped Bar Chart

Navigate to the **Manage Plots** page.

### Create the Plot

In the **Create Plot** form at the top of the page:

1. Enter `Seed-Averaged IPC` in the **New plot name** field.
2. Select **Grouped Bar** from the **Plot type** dropdown.
3. Click **Create Plot**.

You should see the new plot appear as a selected pill in the plot selector.

### Configure Columns

In the visualization section, configure the column assignments:

- **X-axis**: select `benchmark_name`. This places the three benchmarks
  along the horizontal axis.
- **Y-axis**: select `system.cpu.ipc`. This displays the seed-averaged IPC
  on the vertical axis.
- **Group by**: select `config_description`. This creates three bars per
  benchmark, one for each CPU configuration.

Set the chart labels:

- **Title**: `IPC by Benchmark and Configuration`
- **X-axis label**: `Benchmark`
- **Y-axis label**: `IPC (instructions/cycle)`

Click **Refresh Plot** (or enable Auto-refresh).

You should see a grouped bar chart with three clusters of bars (mcf, omnetpp,
xalancbmk), each containing three bars (baseline, optimized, aggressive). The
bars display the seed-averaged IPC values.

---

## Step 5: Enable Error Bars

The seed reduction created `.sd` columns that capture the variability across
seeds. You can display this variability as error bars on the chart.

Toggle **Show advanced settings** if it is not already active. Click the
**Advanced** settings pill. Inside, locate the **Show Error Bars** checkbox
and enable it.

Refresh the plot. You should see thin vertical error bars on top of each bar,
representing plus/minus one standard deviation of IPC across the two seeds.

The error bars are small in this dataset because the two seeds produce similar
IPC values. In a real experiment with more seeds and greater variability, error
bars help readers judge whether differences between configurations are
statistically meaningful.

---

## Step 6: Compare Across Configurations

With the grouped bar chart displayed, you can now compare how each CPU
configuration performs across the benchmarks:

### Reading the Chart

- **mcf**: The aggressive configuration achieves the highest IPC (around
  2.52), followed by optimized (around 2.37), and baseline (around 2.13).
  All three configurations improve monotonically.

- **omnetpp**: The same trend holds, but the overall IPC is lower. Baseline
  IPC is around 1.87, optimized reaches 2.12, and aggressive reaches 2.27.

- **xalancbmk**: Again, aggressive leads at around 2.42, with optimized at
  2.22 and baseline at 1.97.

### Key Observations

The aggressive configuration consistently achieves the highest IPC across all
benchmarks. However, the magnitude of improvement varies:

- For `mcf`, aggressive provides roughly 18% higher IPC than baseline.
- For `omnetpp`, the improvement is roughly 21%.
- For `xalancbmk`, the improvement is roughly 23%.

These differences are meaningful because the error bars (seed variability) are
much smaller than the gaps between configurations. If error bars overlapped
significantly between two configurations, you would need more seeds to draw
confident conclusions.

---

## Step 7: Add a Geometric Mean Summary (Optional)

To quantify the overall improvement across all benchmarks, you can add a
geometric mean summary row using the shaper pipeline.

### Add a Mean Calculator Step

In the **Pipeline editor** section on the Manage Plots page:

1. Select **Mean Calculator** from the **Add transformation** dropdown.
2. Click **Add to Pipeline**.

You should see a new pipeline step appear.

### Configure the Mean Calculator

Expand the pipeline step and configure it:

- **Algorithm**: select **Geometric Mean** (`geomean`). Geometric mean is the
  standard summary statistic for performance ratios like IPC.
- **Group by columns**: select `config_description`. This computes a separate
  mean for each CPU configuration.
- **Calculate mean for**: select `system.cpu.ipc`.
- **Replacing column**: select `benchmark_name`. The summary row will have
  `geomean` as its benchmark name.

Click **Finalize Pipeline for Plotting**.

You should see the chart update with a fourth cluster labeled `geomean`
showing the geometric mean IPC for each configuration. This provides a single
summary number for each configuration's average performance across all
benchmarks.

---

## Summary

In this tutorial, you learned how to:

1. **Understand multi-seed data.** The sample dataset contains 18 rows
   representing 3 benchmarks x 3 configurations x 2 seeds each.

2. **Reduce seeds using Data Managers.** The Seeds Reducer tab aggregates
   repeated seed runs into mean values with standard deviation columns,
   reducing 18 rows to 9.

3. **Create a grouped bar chart.** Using the seed-averaged data, you built a
   grouped bar chart comparing IPC across benchmarks and configurations.

4. **Display error bars.** The `.sd` columns from the seed reduction enabled
   error bars that show variability across seeds.

5. **Compare configurations.** By reading the chart, you identified that the
   aggressive configuration consistently outperforms baseline and optimized
   across all benchmarks.

6. **Summarize with geometric mean.** The Mean Calculator shaper added a
   `geomean` summary row for an overall performance comparison.

### Next Steps

- To prepare your chart for a conference submission, follow the
  [Creating Publication-Ready Plots](publication-ready.md) tutorial.
- To learn more about the full range of data transformations available in the
  shaper pipeline, see the [Manage Plots](../pages/manage-plots.md)
  reference.
- To explore the Data Managers page in more detail, see the
  [Data Managers](../pages/data-managers.md) reference.
