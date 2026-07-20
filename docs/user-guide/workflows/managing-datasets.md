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

## Keep multiple named datasets

<!--
`uman~ring5.data.multi-dataset-workspace.documentation~1`

Covers:
- req~ring5.data.multi-dataset-workspace~1

-->

Open **Data Managers → Workspace** and choose **Retain Current Dataset** to keep the active table
under a session-unique name. Retained tables appear with their row count, column count, and active
state. Activating another table updates the existing Summary, transformation, and plotting pages;
it does not delete or overwrite the other retained tables.

With at least two named datasets, the workspace can:

- compare aligned numeric metrics while leaving both sources untouched;
- join tables on one or more shared key columns and retain the result under a new name;
- append rows using the union or intersection of columns and retain the result;
- remove one retained table without removing unrelated tables.

Joined and appended results become independent named datasets. Transformations made through the
existing data managers update only the active named dataset. Named datasets are held in the current
session; a portfolio continues to snapshot its active dataset.

The public API supports the same workflow:

```python
session.add_dataset("main", baseline)
session.add_dataset("candidate", candidate, select=False)

comparison = session.compare_datasets(
    "main",
    "candidate",
    key_columns=["benchmark"],
    metric_columns=["ipc"],
    thresholds=2.0,
)
paired = session.join_datasets(
    "main",
    "candidate",
    "paired",
    on=["benchmark"],
)
all_runs = session.append_datasets(
    ["main", "candidate"],
    "all_runs",
    select=False,
)
```

`list_datasets()` returns immutable `DatasetInfo` summaries. `get_dataset()` returns a defensive
copy, so editing it cannot change the retained source accidentally. Use `select_dataset()` to make
a named table active and `remove_dataset()` to remove it explicitly.

## Trace and recover dataset changes

<!--
`uman~ring5.data.lineage-undo-redo.documentation~1`

Covers:
- req~ring5.data.lineage-undo-redo~1

-->

Expand **Lineage & recovery** beneath a named dataset to answer three practical questions: what
changed, which named datasets contributed to it, and which exact table state is active. Every
confirmed change to a named dataset creates an immutable in-session revision with:

- a human-readable operation such as an append, join, seeds reduction, or arithmetic change;
- source dataset names and parent revision IDs that expose ancestry;
- row and column counts;
- a SHA-256 content fingerprint for identifying the exact table state.

Choose a revision to inspect its first 100 rows without changing the dataset. **Undo Last Change**
moves to the preceding state and **Redo Change** reapplies the most recently undone state. **Restore
This Revision** makes any inspected intermediate state current. If you confirm a new change after
undoing, the new revision branches from that restored state and the abandoned revision remains
inspectable, while the redo action is cleared.

The public API exposes the same recovery flow:

```python
lineage = session.dataset_lineage("all_runs")
for revision in lineage.revisions:
    print(revision.sequence, revision.operation, revision.fingerprint)

old_table = session.get_dataset_revision(lineage.revisions[0].revision_id)
session.undo_dataset("all_runs")
session.redo_dataset("all_runs")
session.restore_dataset_revision(lineage.revisions[0].revision_id)
```

Revision snapshots are defensive copies held only for the current session. They are not yet stored
inside portfolios, so save an important recovered table separately before ending the session.

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

## Profile data quality

<!--
`uman~ring5.data.quality-profiler.documentation~1`

Covers:
- req~ring5.data.quality-profiler~1

-->

Open **Data Quality** to inspect the active table without changing it. Select columns that are
expected to contain numeric, boolean, datetime, or text values, then select **Profile Dataset**.
The report includes:

- missing cells and redundant duplicate rows;
- inferred and stored column types;
- unique values and constant columns;
- infinite numeric values;
- values outside the 1.5 × IQR bounds;
- values that cannot be interpreted as the selected expected type.

Missing expected columns are reported by the public API. Type validation ignores missing cells so
missingness and invalid values remain separate counts. IQR outliers are screening results, not
automatic exclusions; inspect the experiment design before removing them.

```python
report = session.profile_data(
    data,
    expected_types={
        "ipc": "numeric",
        "completed": "boolean",
        "timestamp": "datetime",
    },
)
print(report.duplicate_rows, report.schema_violations)
column_profile = report.to_frame()
```

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
