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

## Export regression results for automation

<!--
`uman~ring5.automation.machine-readable-regression.documentation~1`

Covers:
- req~ring5.automation.machine-readable-regression~1

-->

After a threshold comparison, use **Download results JSON** for scripts and retained artifacts or
**Download JUnit XML** for CI test-report viewers. Both exports identify the baseline and candidate,
retain every alignment key and metric value, and record the direction, threshold, threshold unit,
and outcome. The existing CSV remains available for exploratory analysis.

The JSON format is deterministic UTF-8, ends with a newline, and carries
`"format": "ring5.regression-results"` plus `"schema_version": 1`. Its summary reports total,
failed, and incomplete comparisons as well as counts for every outcome. Non-finite or unavailable
numeric values are represented as JSON `null`, never non-standard `NaN` or infinity tokens.

The JUnit mapping is deliberately conservative:

- `regression` is a failed testcase;
- `missing_baseline`, `missing_candidate`, `missing_value`, and `not_comparable` are skipped
  testcases because no threshold decision can be made;
- `improvement` and `unchanged` are passing testcases.

JUnit suite properties contain the format version and both source identifiers. Each testcase has
properties for the keys, metric values, changes, direction, threshold, unit, and outcome, so the XML
does not hide the evidence behind the pass/fail projection.

The public API exports either document directly from the result of `Session.compare`:

```python
from pathlib import Path

json_bytes = session.export_regression_results(comparison)
junit_bytes = session.export_regression_results(comparison, format="junit")

Path("regression-results.json").write_bytes(json_bytes)
Path("regression-results.xml").write_bytes(junit_bytes)
```

Use stable, meaningful `baseline_name` and `candidate_name` values when creating the comparison;
those names become the source identifiers in both documents. An export rejects empty, mixed-source,
or structurally modified comparison results instead of emitting ambiguous automation data.

### Fail CI on regressions

<!--
`uman~ring5.automation.ci-regression-gates.documentation~1`

Covers:
- req~ring5.automation.ci-regression-gates~1

-->

`ring5 regression-gate` loads separate baseline and candidate CSV files, compares the configured
metrics, emits the same machine-readable result described above, and communicates the decision in
its process status:

```bash
ring5 regression-gate results/main.csv results/change.csv \
  --key benchmark --metric ipc --metric latency \
  --default-threshold 5 \
  --direction latency=lower --threshold ipc=2 \
  --baseline-id main --candidate-id "$GITHUB_SHA" \
  --format junit --output artifacts/regression.xml
```

Repeat `--key` for composite alignment keys and `--metric` for every gated measurement. Higher is
better and the tolerance is zero by default. `--default-direction` and `--default-threshold` change
those defaults; repeat `--direction METRIC=higher|lower` or `--threshold METRIC=VALUE` for explicit
per-metric overrides. `--threshold-mode` applies either percentage or absolute units consistently
to the gate.

Without `--output`, versioned JSON is written to standard output. Use `--format junit` with an
output path when the CI system collects test artifacts. Results are emitted for every completed
comparison decision, including a failing or incomplete gate.

| Exit status | Meaning |
|---:|---|
| `0` | Every comparison is complete and no metric exceeds its regression threshold. |
| `1` | Comparison is complete and at least one metric is a regression. |
| `2` | CLI configuration, CSV loading, comparison, or result writing failed; details are on standard error. |
| `3` | Evidence is incomplete because a row is missing a baseline, candidate, finite value, or comparable percentage. |

Status `3` takes precedence if the result contains both a regression and incomplete rows. This
prevents a partial dataset from being reported as a trustworthy pass or ordinary threshold failure.

## Read regression annotations

<!--
`uman~ring5.analysis.regression-annotations.documentation~1`

Covers:
- req~ring5.analysis.regression-annotations~1

-->

Threshold comparisons include a **Regression Map** above the result table. Every comparable point
uses redundant cues so the outcome is not conveyed by color alone:

- ▲ and blue identify an improvement;
- ▼ and vermillion identify a regression;
- ● and gray identify a change within the configured tolerance.

The displayed outcome comes from the chosen preferred direction and tolerance. For example, a
negative change is an improvement when lower values are preferable. Hover a point for its signed
change and outcome. Missing or non-comparable rows remain in the table but are not placed at a
misleading zero position on the chart.

For another plotting library, add the same labels and accessible styles to a comparison result:

```python
annotated = session.annotate_comparison(
    comparison,
    label_columns=["benchmark"],
    change_mode="threshold",
)
```

`annotation_label` identifies the point. `annotation_change` is the numeric plotting value, while
`annotation_text`, `annotation_symbol`, `annotation_marker`, and `annotation_color` provide display
cues. `change_mode="threshold"` follows the threshold unit stored in each comparison row; use
`"percentage"` or `"absolute"` to force one scale.

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
