---
layout: default
title: User Guide
nav_order: 2
has_children: true
permalink: /user-guide/
---

# User Guide

<!--
`uman~ring5.workspace.web-app.documentation~1`

Covers:
- req~ring5.workspace.web-app~1
-->

Use RING-5 to load or parse measurements, inspect the resulting table, create figures, and retain
the data and configuration needed to reproduce them. Work interactively in the web application or
use the public `ring5` API and CLI for scripts and continuous integration.

## Start with your task

| You have… | Follow… | You will produce… |
| --- | --- | --- |
| No data yet; you want to explore | [Example portfolio tour](getting-started/showcase/) | A working gallery you can inspect, change, export, and save. |
| A new installation; you want to learn the controls | [First analysis](getting-started/first-analysis/) | A figure created from a supplied CSV and a saved portfolio. |
| gem5 results or an existing table | [Load and parse data](workflows/loading-data/) | A reviewed table ready for analysis. |
| Baseline and candidate runs | [Compare configurations](guides/compare-configurations/) | Aligned comparisons, regression evidence, and normalized figures. |
| A figure ready for a paper | [Prepare publication output](guides/publication-export/) | An export with explicit dimensions, typography, and engine. |
| A recurring or batch analysis | [Automate with Python and the CLI](workflows/scripting/) | An executable script with reproducible outputs. |

[Install RING-5](getting-started/installation/) first. Read [Core concepts](getting-started/concepts/)
for the distinction between workspace data, per-plot pipelines, renderers, and portfolios.

## Find detailed instructions

- [Workflows](workflows/) groups loading, data preparation, visualization, sharing, automation,
  and workspace tasks.
- [Analysis guides](guides/) connects those operations into complete research workflows.
- [Reference](reference/) explains chart selection, shaper contracts, figure settings, supported
  export formats, and troubleshooting.

RING-5 does not require a fixed CSV schema. A CSV must be non-empty and have a header; each
operation validates the columns and types it needs. Parser examples use statistic names such as
`simTicks` only where those names exist in the selected gem5 input.
