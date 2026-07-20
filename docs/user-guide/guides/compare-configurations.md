---
layout: default
title: Compare Configurations
parent: Analysis Guides
grand_parent: User Guide
nav_order: 1
permalink: /user-guide/guides/compare-configurations/
redirect_from:
  - /user-guide/tutorials/compare-simulations/
  - /user-guide/tutorials/normalize-data/
---

# Compare configurations

This workflow compares a candidate against a baseline across benchmarks. It keeps repeated-run
reduction separate from baseline normalization so variability and ratios remain auditable.

Assume the input has `benchmark`, `configuration`, `seed`, and numeric `ipc` columns. Substitute the
names produced by your results tree.

## Check the experimental groups

Before transforming data, verify that each benchmark and configuration has the intended seed set.
Missing or duplicated runs bias the mean and standard deviation. Keep the raw table for this check.

## Calculate regressions

<!--
`uman~ring5.analysis.regression-comparison.documentation~1`

Covers:
- req~ring5.analysis.regression-comparison~1

-->

Open **Data Managers**, select **Compare**, and configure:

1. the column containing the baseline and candidate groups;
2. two different group values;
3. the columns that uniquely align their rows;
4. one or more numeric metrics;
5. whether higher or lower values are preferable;
6. a non-negative percentage or absolute tolerance.

The preview contains one row per alignment key and metric. It reports the source values, absolute
change, percentage change, threshold, and one of `improvement`, `regression`, `unchanged`,
`missing_baseline`, `missing_candidate`, `missing_value`, or `not_comparable`. Percentage change is
`(candidate - baseline) / abs(baseline) × 100`. A nonzero value cannot be compared by percentage
against a zero baseline; use an absolute threshold when that comparison is meaningful.

Duplicate alignment keys are rejected. Reduce repeated runs first or include the run identifier in
the alignment keys. The preview can be downloaded without changing the dataset. **Use Comparison
Result** replaces the active table with the long-form result so it can be plotted.

The public API compares separate tables and supports per-metric directions and thresholds:

```python
comparison = session.compare(
    baseline,
    candidate,
    key_columns=["benchmark"],
    metric_columns=["ipc", "latency"],
    directions={"ipc": "higher", "latency": "lower"},
    thresholds={"ipc": 2.0, "latency": 5.0},
    threshold_mode="percentage",
    baseline_name="main",
    candidate_name="change",
)
```

## Estimate statistical evidence

<!--
`uman~ring5.analysis.statistical-comparison.documentation~1`

Covers:
- req~ring5.analysis.statistical-comparison~1

-->

Select **Statistics** as the comparison method when each baseline and candidate group contains
repeated observations. Alignment keys define independent groups; rows within each key are samples.
Leave the keys empty to compare all observations together.

For every key and metric, RING-5 reports:

- finite sample counts and arithmetic means;
- the candidate-minus-baseline mean difference and Welch confidence interval;
- Hedges' g standardized effect size;
- a two-sided Welch t-test p-value and the configured significance result;
- a deterministic bootstrap estimate and percentile confidence interval;
- warnings for missing groups, discarded non-finite values, insufficient samples, small samples,
  and zero variance.

The confidence level, significance level, bootstrap count, and small-sample warning threshold are
configurable. Bootstrap counts are bounded from 100 to 50,000. Statistical significance does not
measure practical importance; review the observed difference, interval, effect size, sample design,
and warnings together.

The equivalent public API accepts DataFrames or `ring5.Table` values:

```python
statistics = session.compare_statistics(
    baseline_runs,
    candidate_runs,
    group_columns=["benchmark"],
    metric_columns=["ipc"],
    confidence_level=0.95,
    alpha=0.05,
    bootstrap_samples=2_000,
    random_seed=0,
    minimum_sample_size=5,
)
```

## Reduce repeated runs

On **Data Managers**, open **Seeds Reducer**. Choose `seed` as **Column to reduce over**, group by
`benchmark` and `configuration`, and calculate statistics for `ipc`. Apply, inspect the preview, and
confirm. The result contains `ipc` means and `ipc.sd` standard deviations.

## Normalize the plot data

On **Manage Plots**, create a `grouped_bar` plot and add **Normalize** to its **Data Processing
Pipeline**. Configure:

- values to normalize: `ipc`;
- baseline column: `configuration`;
- baseline value: `baseline`;
- group by: `benchmark`;
- standard-deviation normalization: enabled.

Every benchmark group must contain exactly the intended baseline value. Preview the normalized data:
baseline rows should equal `1.0`, and candidate rows should contain `candidate / baseline`. Finalize
the pipeline only after checking those invariants.

## Configure the comparison

<!--
`uman~ring5.figure.group-separators.documentation~1`

Covers:
- req~ring5.figure.group-separators~1

-->

Grouped comparisons can draw separators between major categories and either add a gap or divider
before an isolated final group. Category super-groups can add stronger boundaries and labels over
adjacent category runs.

Map `benchmark` to the X axis, `ipc` to the Y axis, and `configuration` to the group. Label the Y
axis with the ratio direction, such as `IPC / baseline`; a generic label such as `Normalized IPC`
can hide whether larger or smaller is better. Enable error bars when the plot recognizes the
companion `.sd` column.

Do not infer statistical significance from overlap alone. RING-5 displays the variability supplied
by the dataset; it does not choose a hypothesis test.

## Reproduce the transformation in Python

```python
import ring5

with ring5.Session() as session:
    raw = session.load("results.csv")
    reduced = session.reduce_seeds(
        raw,
        categorical_cols=["benchmark", "configuration"],
        statistic_cols=["ipc"],
    )
    normalized = session.shape(
        reduced,
        [
            {
                "type": "normalize",
                "normalizeVars": ["ipc"],
                "normalizerVars": ["ipc"],
                "normalizerColumn": "configuration",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark"],
                "normalizeSd": True,
            }
        ],
    )
    spec = ring5.FigureSpec(
        x="benchmark",
        group="configuration",
        y_columns=["ipc"],
        ylabel="IPC / baseline",
    )
    figure = session.plot(
        "grouped_bar",
        data=normalized,
        config=spec,
        engine="matplotlib",
    )
    session.export(figure, "figures/ipc-normalized.pdf", deterministic=True)
```

Next: [Prepare Publication Output]({{site.baseurl}}/user-guide/guides/publication-export/).
