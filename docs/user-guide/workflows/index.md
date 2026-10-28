---
layout: default
title: Workflows
parent: User Guide
nav_order: 3
has_children: true
permalink: /user-guide/workflows/
---

# Workflows

<!--
`uman~ring5.workspace.navigation.documentation~2`

Covers:
- req~ring5.workspace.navigation~2
-->

Start with [First analysis]({{site.baseurl}}/user-guide/getting-started/first-analysis/) for a complete
web walkthrough, or [the example portfolio]({{site.baseurl}}/user-guide/getting-started/showcase/) to
inspect configured figures. Use the task groups below for detailed procedures.

## Load and prepare data

- [Load and parse data](loading-data/): review uploaded tables, parse gem5 statistics, or reopen results.
- [Manage datasets](managing-datasets/): inspect quality, retain named tables, validate schemas and
  joins, reduce repeated runs, and derive columns.
- [Reuse dataset snapshots](dataset-snapshots/): retain exact tables across browser and Python sessions.
- [Monitor background jobs](background-jobs/): review progress, cancellation, retries, and errors.

## Create and explore figures

- [Create and configure plots](plotting/): create a plot, finalize its pipeline, map columns, and export.
- [Compare and copy plot settings](copy-plot-settings/): inspect field-level changes before reusing settings.
- [Style line charts](line-styles/): choose consistent connectors, dashes, widths, and markers.
- [Compare groups with small multiples](small-multiples/): split a figure into aligned panels.
- [Explore rows behind a plot](plot-drill-down/): inspect contributing data while retaining the figure.
- [Build multi-panel dashboards](multi-panel-dashboards/): combine independent plots into one figure.
- [Link dashboard selections](linked-selections/): inspect matching values across Plotly panels.
- [Compose publication panels](publication-panel-composition/): add panel labels, captions, and spacing.

Choose a chart by the question it answers in [Plot types]({{site.baseurl}}/user-guide/reference/plot-types/).
The focused chart guides cover:

| Question | Guide |
| --- | --- |
| How spread out are repeated observations? | [Box plots](box-plots/), [violin plots](violin-plots/) |
| What fraction falls below a threshold? | [ECDF plots](ecdf-plots/) |
| How do components change over an ordered axis? | [Area charts](area-charts/) |
| How do profiles compare on a shared scale? | [Radar charts](radar-charts/) |
| Which contributions explain a change? | [Waterfall charts](waterfall-charts/) |
| Where does a measured quantity flow? | [Sankey diagrams](sankey-diagrams/) |
| Which combinations of dimensions distinguish rows? | [Parallel coordinates](parallel-coordinates/) |

## Save, share, and automate

- [Manage portfolios](portfolios/): save and restore a workspace, compare versions, or reuse recipes.
- [Build analysis reports](batch-reports/): share figures, processed tables, findings, and provenance.
- [Review an analysis together](collaborative-review/): retain authored comments and statuses.
- [Automate with Python and the CLI](scripting/): run scripts, parameter matrices, and repeatable exports.

For end-to-end comparisons and final paper figures, use [Analysis guides]({{site.baseurl}}/user-guide/guides/).

## Work efficiently in the application

- [Follow a guided analysis](guided-analysis/): navigate milestones from source selection to download.
- [Search the workspace](workspace-search/): find variables, datasets, plots, pipelines, and guides.
- [Use the command palette and shortcuts](command-palette/): navigate and invoke workspace actions.
- [Organize favorites and tags](favorites-tags/): keep related analysis objects discoverable.
- [Recover an interrupted workspace](autosave-recovery/): review and restore browser-private drafts.
