---
layout: default
title: Manage Datasets
parent: Workflows
grand_parent: User Guide
nav_order: 2
permalink: /user-guide/workflows/managing-datasets/
redirect_from:
  - /user-guide/pages/data-managers/
---

# Manage datasets

Use **Data Managers** for changes that every later plot should see. Use a plot's **Data Processing
Pipeline** for filtering, normalization, sorting, and reshaping that belongs to only that plot.

Keep an unchanged source CSV outside the application. Data-manager confirmations replace the active
workspace table, while the implementation returns a new DataFrame rather than mutating its input.

## Inspect the table

<!--
`uman~ring5.data.summary.documentation~1`

Covers:
- req~ring5.data.summary~1

`uman~ring5.data.table-view.documentation~1`

Covers:
- req~ring5.data.table-view~1

-->

Open **Data Managers** and use **Summary** to check column types and missing values. Use **Data
Visualization** to search, select columns, and inspect rows. **Download Current View as CSV** exports
the filtered view for inspection; it does not redefine the active workspace table.

Before changing data, verify that configuration columns are categorical and statistics are numeric.
An incorrect inferred type usually indicates inconsistent CSV values.

## Preview and confirm changes

<!--
`uman~ring5.data.preview-confirm.documentation~1`

Covers:
- req~ring5.data.preview-confirm~1

-->

Seeds Reducer, Outlier Remover, Preprocessor, Mixer, and Compare calculate into an isolated preview. The
active workspace table changes only after the corresponding confirmation control is selected.
Discarding or replacing a preview leaves the active table unchanged.

## Reduce repeated runs

<!--
`uman~ring5.data.seed-reduction.documentation~1`

Covers:
- req~ring5.data.seed-reduction~1

-->

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

<!--
`uman~ring5.data.outlier-removal.documentation~1`

Covers:
- req~ring5.data.outlier-removal~1

-->

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

### Binary arithmetic

<!--
`uman~ring5.data.arithmetic.documentation~1`

Covers:
- req~ring5.data.arithmetic~1

-->

**Preprocessor** creates a named column by dividing, adding, subtracting, or multiplying two numeric
source columns. Division by zero produces a missing value. Use **Preview Result**, inspect invalid or
infinite results, then select **Confirm and Add Column to Dataset**.

### Numeric column mixing

<!--
`uman~ring5.data.numeric-mixer.documentation~1`

Covers:
- req~ring5.data.numeric-mixer~1

-->

**Mixer** creates a named sum or arithmetic mean from two or more numeric columns. The source
columns remain in the result.

### Configuration label mixing

<!--
`uman~ring5.data.configuration-mixer.documentation~1`

Covers:
- req~ring5.data.configuration-mixer~1

-->

In configuration mode, **Mixer** converts the selected source values to text and concatenates them
in selection order with the configured separator. This mode does not calculate uncertainty.

### Uncertainty propagation

<!--
`uman~ring5.data.error-propagation.documentation~1`

Covers:
- req~ring5.data.error-propagation~1

-->

For numeric sums and means, Mixer looks for a `.sd` or `_stdev` companion for each source column.
When at least one is present, it combines variances and writes `<result>.sd`; means divide the
combined standard deviation by the number of source columns.

Name derived columns for the quantity and unit they contain. For example, a division is not
automatically IPC unless the numerator and denominator have the correct semantics.

## Review operation history

<!--
`uman~ring5.data.operation-history.documentation~1`

Covers:
- req~ring5.data.operation-history~1

-->

Each manager records confirmed operations. Use its history to reload a configuration, and use
**Operations History** to review workspace changes. History records configuration; they do not
replace versioned source data or a reproducible script.

Next: [Create and Configure Plots]({{site.baseurl}}/user-guide/workflows/plotting/) or
[Compare Configurations]({{site.baseurl}}/user-guide/guides/compare-configurations/).
