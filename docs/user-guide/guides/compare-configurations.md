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
