---
layout: default
title: Explore the Example Portfolio
parent: Getting Started
grand_parent: User Guide
nav_order: 4
permalink: /user-guide/getting-started/showcase/
---

# Explore the example portfolio

<!--
`uman~ring5.portfolio.bundled-example.documentation~1`

Covers:
- req~ring5.portfolio.bundled-example~1
-->

Use the bundled portfolio to choose a chart, inspect a working pipeline, and export a figure before
bringing your own results. Every built-in plot type has a configured example. All values are
**synthetic tutorial data**, created to explain operations; they are not simulator measurements or
evidence that one hardware configuration performs better.

The portfolio is available in source checkouts and installed packages. It loads offline, without
gem5 files, Perl, Chrome, or TeX. Those optional tools are needed only for the operations described
in [Rendering and export]({{site.baseurl}}/user-guide/reference/rendering-export/).

## Open the gallery

1. [Set up a checkout]({{site.baseurl}}/user-guide/getting-started/installation/), run `make run` from its root, and open
   <http://localhost:8501>. For an installed package without a checkout, use the
   [Python example below](#open-the-same-examples-in-python).
2. On the empty **Data Source** page, select **Load example portfolio**.
3. The application opens **Manage Plots**. Use **Select Plot** to choose an example.
4. Keep **Plotly** selected under **Engine** for hover and interactive inspection. Choose
   **LaTeX (Matplotlib)** when inspecting a static rendering; ordinary PDF, PNG, and SVG export
   does not require LaTeX.

The load action is available for an empty workspace. Save existing work before clearing it to try
the examples. Loading changes the current session and creates no saved portfolio or revision files.
The bundled resource remains unchanged when you edit a figure.

## Read the first example

Select **01 · Normalized IPC**. Its question is: *How does each configuration compare with its
own workload's baseline?*

The figure maps `benchmark` to X, `ipc` to Y, and `configuration` to color. Its pipeline first selects
the `summary` scenario, then normalizes IPC within each benchmark against `Baseline` and sorts the
result. Inspect the previews under **Data Processing Pipeline**:

| Configuration | Expected normalized IPC | Interpretation |
| --- | ---: | --- |
| `Baseline` | 1.00 | The reference value for that benchmark. |
| `Large L2` | 1.12 | Twelve percent above the illustrative baseline. |
| `Prefetch` | 1.21 | Twenty-one percent above the illustrative baseline. |

These are ratios, so the Y-axis label is `IPC / Baseline`. They describe the constructed example,
not a conclusion about real workloads. Compare **04 · Grouped IPC** to see the absolute values from
the same summary rows.

Change **Title**, then select **Refresh Plot** if **Auto-refresh** is off. Switch to another example
and back: each plot retains its own configuration and pipeline. Changing one figure does not
rewrite the shared table or another figure.

## Choose an example by your question

| Question | Select this example | What to inspect |
| --- | --- | --- |
| How much does a configuration improve relative to a baseline? | **01 · Normalized IPC** (`bar`) | Per-benchmark normalization and the 1.00 reference. |
| How does a metric change in an ordered parameter sweep? | **02 · Cache Capacity Sweep** (`line`) | Increasing cache capacity, ordered X values, and one series per workload. |
| What trade-off exists between two numeric measurements? | **03 · IPC vs Energy** (`scatter`) | IPC and energy on separate numeric axes, with configuration as color. |
| How do configurations compare side by side? | **04 · Grouped IPC** (`grouped_bar`) | Absolute IPC, configuration groups, and illustrative `.sd` companions. |
| Which components contribute to a total? | **05 · Cycle Composition** (`stacked_bar`) | Front-end, execution, and memory cycle components for baseline runs. |
| How does that composition differ across configurations? | **06 · Grouped Cycle Composition** (`grouped_stacked_bar`) | Shared benchmark categories, configuration groups, and the same component units. |
| How are observations distributed among latency intervals? | **07 · Latency Histogram** (`histogram`) | Explicit half-open interval columns and percent normalization. |
| Where are cache miss rates high or low? | **08 · Cache Miss Rates** (`heatmap`) | Workload/configuration mappings and dimensionless miss-rate values. |
| How do throughput and a second measurement change together? | **09 · IPC and Cache Misses** (`dual_axis_bar_dot`) | IPC bars, right-axis miss-rate dots, and explicit units on both axes. |
| How does an additive total change over time? | **10 · Memory Traffic Over Time** (`area`) | Ordered time points and traffic components that can meaningfully be summed. |
| How variable are repeated measurements? | **11 · Repeated-Run IPC** (`box`) | Repeated samples for one workload, grouped by configuration. |
| What fraction of repeated latencies falls below a threshold? | **12 · Repeated-Run Latency ECDF** (`ecdf`) | Empirical cumulative proportions without binning or smoothing. |
| Which rows occupy different parts of a multidimensional design space? | **13 · Design Space** (`parallel_coordinates`) | Mixed categorical/numeric dimensions and the IPC color scale. |
| How do configurations compare across workload categories? | **14 · Workload Profile** (`radar`) | One common IPC scale; category order changes geometry, not observations. |
| Where do requests go between processing stages? | **15 · Request Flow** (`sankey`) | Nonnegative link counts and conserved traffic at intermediate nodes. |
| How do the shapes of repeated latency samples differ? | **16 · Repeated-Run Latency** (`violin`) | Density plus summary controls for the constructed repeated-run samples. |
| Which contributions explain the final energy value? | **17 · Energy Savings** (`waterfall`) | An absolute starting point, negative savings, and the final total. |

The [plot selection reference]({{site.baseurl}}/user-guide/reference/plot-types/) links each chart
family to its required data and detailed controls. Uncertainty output differs by engine; review
[plot configuration]({{site.baseurl}}/user-guide/workflows/plotting/#map-columns-and-configure-the-figure)
before using `.sd` companions in a final figure.

## Check the data behind a chart

Open **Data Managers** to inspect the shared source table. Its `scenario` column separates summary,
cache-sweep, repeated-run, traffic-series, request-flow, and energy-waterfall examples. Columns that
do not apply to a scenario are missing, rather than invented zeros.

Each figure begins with a scenario-selection step. Its recorded pipeline transforms that shared
source into the plotted rows. A column-selection step retains only the fields needed by the
scenario before normalization or other transformations. Keep the scenario selector when editing a
pipeline; otherwise rows intended for other examples can enter the calculation. Review the intermediate tables, then select
**Finalize Pipeline for Plotting** after a change.

Try these checks to connect the figure to its inputs:

- In **02 · Cache Capacity Sweep**, the `blackscholes` series has IPC 1.55, 1.674, and 1.798 at
  64, 128, and 256 KiB. Increasing capacity is an ordered numeric comparison, not a line drawn
  through unrelated benchmark names.
- In **10 · Memory Traffic Over Time**, epochs 0 through 4 total 15, 20, 26, 23, and 18
  requests per 1,000-cycle interval. Stacking the components is meaningful because they share
  a unit and contribute to that interval's total.
- In **15 · Request Flow**, `CPU 0` and `CPU 1` send 100 and 80 requests to `L1`. `L1` sends
  60 to `L2` and 120 directly to `Memory`; `L2` forwards its 60 to `Memory`. Both intermediate
  nodes conserve flow, and `Memory` receives 180 requests. Adding every link would count requests
  more than once.
- In **17 · Energy Savings**, the constructed baseline is 10 J and savings are −1.6 J and
  −1.2 J, so the ending value is 7.2 J. Savings are relative contributions, not absolute values.

The histogram demonstrates ordinary interval-column data. It does not claim that the synthetic
columns carry a gem5 native Distribution declaration. Box and violin examples use repeated samples
for one workload; the data are illustrative, so do not infer statistical evidence from them.

## Export and keep a copy

1. Select the figure and engine you intend to share.
2. Open **Download**, choose `html` for Plotly or `pdf` for Matplotlib, and select the matching
   download button. HTML includes a source-data table; ordinary Matplotlib PDF needs no optional
   external tools.
3. Open **Save/Load Portfolio**, set **Portfolio Name** to `My example study`, and select
   **Save Portfolio**. This writes your editable workspace copy to the normal application-data
   directory, separately from the bundled resource.

For several figures in one artifact, use
[Multi-panel dashboards]({{site.baseurl}}/user-guide/workflows/multi-panel-dashboards/) or
[Analysis reports]({{site.baseurl}}/user-guide/workflows/batch-reports/).
The [portfolio workflow]({{site.baseurl}}/user-guide/workflows/portfolios/) covers storage,
restoration reports, version comparisons, signing, and portable bundles.

## Open the same examples in Python

This script loads the bundled resource and exports its first figure through both engines:

```python
import ring5

with ring5.Session() as session:
    report = session.load_example_portfolio()
    if not report.complete:
        raise RuntimeError(report)

    print([plot.name for plot in session.plots])
    first_plot = session.plots[0]
    for engine, filename in [
        ("matplotlib", "example-ipc.pdf"),
        ("plotly", "example-ipc.html"),
    ]:
        figure = session.render(first_plot, engine=engine)
        session.export(figure, filename, deterministic=True)
```

The load method returns the normal `RestoreReport` and does not save a named portfolio. Use
`session.save_portfolio("my-example-study")` when you intentionally want a retained copy.
For complete scripts using your own data, continue with
[Automate with Python and the CLI]({{site.baseurl}}/user-guide/workflows/scripting/).

The gallery teaches chart selection, per-plot pipelines, rendering, export, and saving. To parse real
simulator output or assess baseline/candidate evidence, follow
[Load and parse data]({{site.baseurl}}/user-guide/workflows/loading-data/) and
[Compare configurations]({{site.baseurl}}/user-guide/guides/compare-configurations/).
