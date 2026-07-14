---
layout: default
title: Manage Datasets
parent: Workflows
grand_parent: User Guide
nav_order: 2
permalink: /user-guide/workflows/managing-datasets/
---

# Manage datasets

Use **Data Managers** for changes that every later plot should see. Use a plot's **Data Processing
Pipeline** for filtering, normalization, sorting, and reshaping that belongs to only that plot.

Keep an unchanged source CSV outside the application. Data-manager confirmations replace the active
workspace table, while the implementation returns a new DataFrame rather than mutating its input.

## Inspect the table

Open **Data Managers** and use **Summary** to check column types and missing values. Use **Data
Visualization** to search, select columns, and inspect rows. **Download Current View as CSV** exports
the filtered view for inspection; it does not redefine the active workspace table.

Before changing data, verify that configuration columns are categorical and statistics are numeric.
An incorrect inferred type usually indicates inconsistent CSV values.

## Reduce repeated runs

Use **Seeds Reducer** after confirming the raw runs and before normalizing a figure:

1. Choose the seed, iteration, or run identifier in **Column to reduce over**.
2. Select the configuration columns that define a comparison group.
3. Select the numeric statistics to aggregate.
4. Select **Apply Seeds Reducer** and inspect the preview.
5. Select **Confirm and Apply Seeds Reducer** only when the groups are correct.

The result contains the mean and a companion `.sd` column for each selected statistic. Do not include
the seed identifier in the group-by columns; that would prevent runs from being combined.

The public API accepts explicit grouping and statistic columns:

```python
reduced = session.reduce_seeds(
    data,
    categorical_cols=["benchmark", "configuration"],
    statistic_cols=["ipc"],
)
```

## Remove outliers

**Outlier Remover** computes Q1 and Q3 for a numeric column and removes values outside
`[Q1 - 1.5 × IQR, Q3 + 1.5 × IQR]`. Optional group-by columns calculate independent bounds for
each experiment group.

Exclude seed-like columns from the group-by selection: one-row groups cannot identify outliers.
Review the removed row count and preview before selecting **Confirm and Apply Outlier Remover**.

The equivalent public call is:

```python
clean = session.remove_outliers(
    data,
    outlier_col="ipc",
    group_by_cols=["benchmark", "configuration"],
)
```

Outlier removal is a methodological decision. Record the chosen grouping and preserve the original
measurements.

## Derive or combine columns

- **Preprocessor** applies a selected binary arithmetic operation to two numeric columns. Use
  **Preview Result**, check invalid or infinite results, then select **Confirm and Add Column to
  Dataset**.
- **Mixer** combines several numeric columns with sum or mean, or concatenates columns into a
  configuration label. When matching standard-deviation columns exist, numeric mixing propagates
  them into the result.

Name derived columns for the quantity and unit they contain. For example, a division is not
automatically IPC unless the numerator and denominator have the correct semantics.

## Review operation history

Each manager records confirmed operations. Use its history to reload a configuration, and use
**Operations History** to review workspace changes. History records configuration; they do not
replace versioned source data or a reproducible script.

Next: [Create and Configure Plots](plotting/) or
[Compare Simulations](../tutorials/compare-simulations/).
