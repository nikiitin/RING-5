---
title: "Shaper Pipeline Reference"
parent: Features
grand_parent: User Guide
nav_order: 4
redirect_from:
  - /api/Data-Transformations/
  - /Data-Transformations/
---

# Shaper Pipeline Reference

## Overview

Shapers are per-plot data transformation steps that modify your data before it is rendered in a chart. They form a pipeline: your data flows through each step sequentially, from top to bottom, with the output of one step becoming the input of the next.

Shapers never change your original dataset. Each step works on a copy of the data, so you can freely add, remove, and reconfigure steps without worrying about losing your parsed simulation results.

RING-5 provides ten shaper types. Eight of them cover the most common analysis workflows and are described in detail in this guide: Column Selector, Item Selector, Sort, Filter, Normalize, Mean Calculator, Transformer, and Split-Apply-Combine. Two additional types (Pivot Longer and Pivot Wider) handle advanced data reshaping and are summarized at the end.

---

## How to Use the Pipeline

### Adding Steps

On the **Manage Plots** page, each plot has a shaper pipeline editor. To add a transformation step:

1. Open the shaper pipeline section for your plot.
2. Select a shaper type from the dropdown menu.
3. Click **Add to Pipeline**.

You should see the new step appear at the bottom of your pipeline list, with its configuration options displayed.

### Configuring Steps

Each step shows its own set of parameters immediately after you add it. Fill in the required fields (such as which columns to operate on or what threshold to use). The configuration is saved automatically as you make changes.

### Reordering and Removing Steps

Steps execute from top to bottom. The order matters because each step receives the output of the previous one.

You can reorder steps using the up and down arrow buttons next to each step. To remove a step, click its delete button. You should see the pipeline update immediately.

### Applying the Pipeline

Once you have configured your pipeline, click **Finalize Pipeline for Plotting**. The pipeline runs all steps in order, and the transformed data is sent to the plotting engine. If any step encounters an error (such as a missing column), you will see a descriptive error message indicating which step failed.

### Saving and Loading Pipelines

After building a pipeline that produces the analysis you need, you can save it for reuse. Enter a descriptive name and click the save button. Saved pipelines are stored as JSON files and can be loaded onto any plot.

To load a previously saved pipeline, select it from the list of available pipelines. The steps and their configurations are restored exactly as they were when saved. You can then modify the loaded pipeline without affecting the saved version.

---

## Shaper Types

### Column Selector

**Purpose.** Keeps only the columns you specify and removes everything else. Use this as the first step in most pipelines to narrow your data down to the metrics you care about.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Columns | A list of column names to keep. Select one or more columns from the multiselect widget. |

All categorical columns that your plot needs (such as `benchmark` or `config`) are typically preserved automatically. You use the Column Selector to choose which numeric metric columns to retain.

**Example.** You have parsed gem5 statistics containing dozens of metrics (IPC, cache miss rates, branch mispredictions, cycle counts, and more). You only want to plot IPC. Add a Column Selector step and select `ipc` from the column list. You should see all other numeric columns disappear from the data, leaving only the columns needed for your plot axis and the `ipc` metric.

---

### Item Selector

**Purpose.** Filters rows by matching values in a categorical column. Use this to keep only specific benchmarks, CPU configurations, or any other category.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Column | The categorical column to filter on (e.g., `benchmark`). |
| Values | A list of values to keep (e.g., `bzip2`, `gcc`, `mcf`). |
| Mode | `exact` (default) matches values exactly. `contains` matches rows where the column value contains any of the specified substrings. |

**Example.** Your dataset includes results for 20 SPEC benchmarks but you want to focus on memory-intensive workloads. Add an Item Selector step, set the column to `benchmark`, and select `mcf`, `lbm`, and `milc` from the values list. You should see the data reduced to only those three benchmarks.

If you need substring matching -- for instance, to select all benchmarks whose names contain "gcc" -- switch the mode to `contains` and enter `gcc` in the values list.

---

### Sort

**Purpose.** Reorders rows by applying a custom categorical ordering to one or more columns. This controls the order in which items appear along a plot axis.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Order dictionary | For each column you want to sort by, specify the desired order of its values. Select a column, then arrange its values in the order you want them to appear. |

The Sort shaper uses stable sorting, which means that if two rows have the same value in the sorted column, their original relative order is preserved. Values not included in your specified order appear after all specified values.

**Example.** You want your bar chart to show CPU configurations in a specific order: `MinorCPU` first, then `O3CPU`, then `TimingSimpleCPU`. Add a Sort step, select the `config` column, and arrange the values in that order. You should see your plot axis follow the exact sequence you specified.

---

### Filter

**Purpose.** Filters rows based on a numeric or categorical condition. Unlike the Item Selector (which matches exact values), the Filter supports comparison operators and numeric ranges.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Column | The column to apply the condition to. |
| Mode | The filter mode. Options are described below. |
| Threshold | A numeric value used with `greater_than` or `less_than` modes. |
| Range | A minimum and maximum value used with `range` mode. |
| Values | A list of allowed values used with categorical mode. |

**Supported filter modes.**

| Mode | Description |
|------|-------------|
| `greater_than` | Keep rows where the column value is greater than the threshold. |
| `less_than` | Keep rows where the column value is less than the threshold. |
| `range` | Keep rows where the column value falls within the specified minimum and maximum (inclusive). |
| `equals` | Keep rows where the column value equals a specific value. |
| `contains` | Keep rows where the column value (as text) contains a specific substring. |
| Categorical | Keep rows where the column value is in a specified set of allowed values. |

**Example.** You want to exclude benchmark runs with very low IPC (below 0.1), which may indicate failed or misconfigured simulations. Add a Filter step, select the `ipc` column, set the mode to `greater_than`, and set the threshold to `0.1`. You should see rows with IPC at or below 0.1 removed from the data.

---

### Normalize

**Purpose.** Divides metric values by a baseline reference, producing relative numbers such as speedup or slowdown. This is essential for comparing CPU configurations against a common baseline.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Variables to normalize | The numeric columns whose values will be divided by the baseline (e.g., `ipc`, `cycles`). |
| Normalizer column | The categorical column that identifies configurations (e.g., `config`). |
| Normalizer value | The specific value in that column to use as the baseline (e.g., `MinorCPU`). |
| Group by | The columns that define independent normalization groups (e.g., `benchmark`). Each group gets its own baseline value. |
| Normalizer variables | (Optional) The columns used to compute the denominator. Defaults to the same columns as "Variables to normalize." |
| Normalize standard deviation | (Optional) Whether to also normalize standard deviation columns. Enabled by default. |

Within each group, the shaper finds the row matching the baseline value, extracts its metric values, and divides all rows in that group by those values. The baseline row itself becomes 1.0 for all normalized metrics.

**Example.** You want to express IPC as a speedup relative to `MinorCPU`. Add a Normalize step, set the variables to normalize to `ipc`, the normalizer column to `config`, the normalizer value to `MinorCPU`, and group by `benchmark`. You should see all IPC values converted to ratios where `MinorCPU` is 1.0 for each benchmark. A value of 1.5 means that configuration is 1.5 times faster than `MinorCPU` on that benchmark.

---

### Mean Calculator

**Purpose.** Computes a summary statistic (arithmetic mean, geometric mean, or harmonic mean) across groups and appends the result as new rows. This is the standard way to add a "GEOMEAN" summary row to benchmark comparisons.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Algorithm | The type of mean to compute: `arithmean` (arithmetic mean), `geomean` (geometric mean), or `hmean` (harmonic mean). |
| Variables | The numeric columns to aggregate (e.g., `ipc`). |
| Grouping columns | The columns that define groups. One summary row is created per group (e.g., group by `config` to get one mean per CPU configuration). |
| Replacing column | The categorical column where the mean label is placed in the new rows (e.g., `benchmark`). The new row will have a value like `geomean` in this column. |

The Mean Calculator does not replace any existing rows. It appends new summary rows to the bottom of your data.

**Algorithm guidance.** For normalized performance ratios (speedup values), use geometric mean (`geomean`). For absolute values like cycle counts, use arithmetic mean (`arithmean`). For rate-based metrics, harmonic mean (`hmean`) may be more appropriate.

**Example.** After normalizing IPC to a baseline, you want to add a geometric mean summary across all benchmarks for each configuration. Add a Mean Calculator step, set the algorithm to `geomean`, the variables to `ipc`, group by `config`, and the replacing column to `benchmark`. You should see new rows appended to the data with `benchmark` set to `geomean`, one for each CPU configuration. These rows contain the geometric mean of all benchmark IPC values within that configuration.

---

### Transformer

**Purpose.** Converts a column between numeric (scalar) and categorical (factor) types. Use this when a column is stored as numbers but should be treated as categories for grouping, or vice versa.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Column | The column to convert. |
| Target type | `scalar` to convert to numeric, or `factor` to convert to categorical. |
| Order | (Optional, for `factor` only) An explicit ordering for the category values. |

When converting to `scalar`, values that cannot be parsed as numbers become `NaN`. When converting to `factor`, all values are cast to text strings. If you provide an explicit order, the column becomes an ordered categorical, which affects sorting and plot axis ordering.

**Example.** Your gem5 data has a `num_cores` column stored as numbers (1, 2, 4, 8), but you want to use it as a categorical axis in your plot. Add a Transformer step, select the `num_cores` column, and set the target type to `factor`. Optionally, provide an order of `1, 2, 4, 8` to ensure the categories appear in that sequence on your plot axis.

---

### Split-Apply-Combine

**Purpose.** Splits your data into independent column groups, applies a separate sub-pipeline to each group, and merges the results back together. This is designed for dual-axis plots where each axis variable needs its own normalization or aggregation without affecting the other.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Join columns | The categorical columns shared across all groups, used to merge results back together (e.g., `benchmark`, `config`). |
| Groups | Two to four column groups. Each group specifies which numeric columns it contains and its own sub-pipeline of transformation steps. |

Each group's sub-pipeline can include steps like Mean Calculator, Normalize, Sort, and Filter. The groups are processed independently, then merged back on the join columns.

**Example.** You have a dual-axis plot with `ipc` on the left axis and `cache_miss_rate` on the right axis. You want to normalize `ipc` to the `MinorCPU` baseline, but show `cache_miss_rate` as absolute values. Add a Split-Apply-Combine step with join columns set to `benchmark` and `config`. Create two groups: one containing `ipc` with a Normalize sub-pipeline (baseline = `MinorCPU`), and another containing `cache_miss_rate` with no sub-pipeline. You should see the merged result where IPC values are normalized while cache miss rates remain unchanged.

---

### Pivot Longer (Melt)

**Purpose.** Transforms data from wide format to long format. Multiple columns are collapsed into a single column of values, with a companion column recording which original column each value came from. This is useful when your gem5 output has multiple metrics as separate columns and you need them stacked for a grouped or faceted plot.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| ID variables | The columns to keep as-is (e.g., `benchmark`, `config`). These are not melted. |
| Value variables | The columns to unpivot (e.g., `ipc`, `cpi`). Each becomes a row. |
| Variable name | The name for the new column that records which original column a value came from. |
| Value name | The name for the new column that holds the values. |
| Extract pattern | (Optional) A regex pattern to parse structured column names into components. |

**Example.** Your data has columns `benchmark`, `config`, `ipc`, and `cpi`. You want a single "metric" column. Add a Pivot Longer step with ID variables = `benchmark, config`, value variables = `ipc, cpi`, variable name = `metric`, and value name = `value`. You should see the data reshaped so that each original row becomes two rows: one for `ipc` and one for `cpi`.

### Pivot Wider

**Purpose.** Transforms data from long format to wide format by spreading the values of one column into multiple new columns. This is the inverse of Pivot Longer.

**Parameters.**

| Parameter | Description |
|-----------|-------------|
| Index | The columns that define each row in the output (e.g., `benchmark`). |
| Columns from | The column whose unique values become new column names (e.g., `config`). |
| Values from | The column whose values populate the new cells (e.g., `ipc`). |

**Example.** Your long-format data has columns `benchmark`, `config`, and `ipc`, with one row per benchmark-config pair. You want each configuration to become its own column. Add a Pivot Wider step with index = `benchmark`, columns from = `config`, and values from = `ipc`. You should see one row per benchmark with separate columns for each CPU configuration's IPC value.

These two shapers are typically needed only for advanced data restructuring scenarios. Most common analysis workflows can be handled with the other eight shaper types.

---

## Common Pipeline Recipes

Below are three pipeline configurations that address frequent gem5 analysis tasks.

### Show IPC for Selected Benchmarks

**Goal.** Display IPC for a specific set of benchmarks, sorted in a custom order.

| Step | Shaper | Configuration |
|------|--------|---------------|
| 1 | Column Selector | Keep `ipc` (and your categorical columns). |
| 2 | Item Selector | Column = `benchmark`, values = the benchmarks you want to display. |
| 3 | Sort | Column = `benchmark`, order = your preferred sequence. |

You should see a clean chart with only the selected benchmarks, displayed in the exact order you specified.

### Normalize to a Baseline CPU

**Goal.** Express IPC as speedup relative to a baseline configuration.

| Step | Shaper | Configuration |
|------|--------|---------------|
| 1 | Column Selector | Keep `ipc`. |
| 2 | Normalize | Variables = `ipc`, normalizer column = `config`, normalizer value = `MinorCPU`, group by = `benchmark`. |

You should see IPC values converted to ratios where `MinorCPU` equals 1.0 for every benchmark.

### Geometric Mean Across Benchmarks

**Goal.** Add a summary row showing the geometric mean of normalized IPC across all benchmarks, per configuration.

| Step | Shaper | Configuration |
|------|--------|---------------|
| 1 | Column Selector | Keep `ipc`. |
| 2 | Normalize | Variables = `ipc`, normalizer column = `config`, normalizer value = `MinorCPU`, group by = `benchmark`. |
| 3 | Mean Calculator | Algorithm = `geomean`, variables = `ipc`, grouping columns = `config`, replacing column = `benchmark`. |

You should see a `geomean` row appended for each CPU configuration, summarizing normalized IPC performance across the entire benchmark suite.

---

## Tips

**Start with Column Selector.** Narrowing your data to only the metrics you need makes every subsequent step simpler and faster.

**Check order of operations.** Normalizing before filtering ensures all benchmarks contribute to the baseline calculation. Filtering before normalizing may remove the baseline row and cause an error.

**Use Mean Calculator after Normalize.** Computing geometric means on normalized (ratio) data is the standard methodology for summarizing relative performance across benchmark suites.

**Capture your pipeline in a portfolio.** A shaper pipeline is part of its plot's configuration. Once you have built a pipeline that produces the analysis you need, save a portfolio to persist the complete workspace — data, plots, and their pipelines — so you can restore the same transformation sequence in a later session.

---

## Troubleshooting

**"Missing column" error.** This means a shaper step references a column that does not exist in the data it receives. This often happens when a Column Selector earlier in the pipeline removed the column, or when loading a saved pipeline against a different dataset. Check that all referenced column names match your current data.

**Empty result after Item Selector.** If your chart is blank after adding an Item Selector, the specified values may not match any rows. Verify that the values you entered exactly match the values in your data (check for extra spaces or case differences). Switch to `contains` mode if you are unsure of the exact value strings.

**Normalize produces all zeros.** This indicates the baseline row has a value of zero for the normalized metric. Division by zero is handled by setting the result to 0.0. Check that your baseline configuration (e.g., `MinorCPU`) produced valid, non-zero values for the metrics you are normalizing.

**Geometric mean returns NaN.** The geometric mean requires all input values to be positive. If any benchmark has a zero or negative value for the metric being aggregated, the result is NaN. Filter out invalid rows before applying the Mean Calculator, or use arithmetic mean instead.
