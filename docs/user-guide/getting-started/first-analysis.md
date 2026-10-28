---
layout: default
title: First Analysis
parent: Getting Started
grand_parent: User Guide
nav_order: 3
permalink: /user-guide/getting-started/first-analysis/
---

# First analysis

<!--
`uman~ring5.workspace.data-preview.documentation~1`

Covers:
- req~ring5.workspace.data-preview~1
-->

Create a bar chart from a small supplied table, export it, and save the workspace. This walkthrough
uses synthetic tutorial values, so no simulator files or optional export tools are needed.
For a ready-made gallery, start with [Explore the example portfolio]({{site.baseurl}}/user-guide/getting-started/showcase/).

## Prepare the input

After [installation]({{site.baseurl}}/user-guide/getting-started/installation/), start `make run` and open <http://localhost:8501>.
Save this text as `first-analysis.csv` on your computer:

```csv
benchmark,ipc
mcf,1.08
xalancbmk,1.31
lbm,0.92
```

## Review and load the table

1. Open **Data Source** in the sidebar and select **Upload data or portfolio**.
2. Upload `first-analysis.csv`. Review the detected columns and accepted/rejected row counts.
3. Check that `benchmark` is text, `ipc` is numeric, all three rows are accepted, and no rows are
   rejected. The preview must contain the values shown above.
4. Select **Load accepted rows**. The workspace header now reports three rows and two columns.

The review does not alter the workspace until you accept it. For encodings, delimiters, Excel,
remote sources, and parsing gem5 output, see
[Load and parse data]({{site.baseurl}}/user-guide/workflows/loading-data/).

## Create and check the chart

1. Open **Manage Plots**. Set **New plot name** to `First IPC comparison`, choose `bar` in
   **Plot type**, and select **Create Plot**.
2. Under **Data Processing Pipeline**, choose **Column Selector** in **Add transformation**
   and select **Add to Pipeline**. In **1. Column Selector**, set **Columns to keep** to
   `benchmark` and `ipc`. Check that its preview retains all three rows and both columns, then
   select **Finalize Pipeline for Plotting**.
3. Under **Plot Configuration**, set **X-axis** to `benchmark` and **Y-axis** to `ipc`.
   Set **Title** to `IPC by benchmark` and **Y-label** to `Instructions per cycle`.
4. Check the rendered bars: `mcf` is 1.08, `xalancbmk` is 1.31, and `lbm` is 0.92.
   If **Auto-refresh** is off, select **Refresh Plot** after changing configuration.

Do not add a reduction step here: every benchmark already has one observation. With repeated runs,
choose the intended grouping and reduction explicitly; see
[Compare configurations]({{site.baseurl}}/user-guide/guides/compare-configurations/).

## Export the figure

Under **Engine**, choose **Plotly** to inspect values on hover. Open **Download**, select `html`
in **Format**, and select **Download HTML**. The self-contained file includes the interactive figure
and its source-data table.

For a paper-ready static file, choose **LaTeX (Matplotlib)**, open **Download**, select `pdf`, and
select **Download PDF**. Ordinary Matplotlib PDF needs no TeX installation; PGF does. Plotly static
images require Chrome. See
[Rendering and export]({{site.baseurl}}/user-guide/reference/rendering-export/) for the exact formats
and dependencies.

## Save and reopen your work

Open **Save/Load Portfolio**, set **Portfolio Name** to `First IPC analysis`, and select
**Save Portfolio**. The saved portfolio contains the table, plot, pipeline, and figure settings.
To reopen it, choose the name under **Select Portfolio**, review **Portfolio integrity**, and select
**Load Portfolio**. Return to **Manage Plots** and check the same bar values.

The web application replaces a saved portfolio with the same exact name. Use a new name when you
want to retain the earlier saved workspace; see
[Manage portfolios]({{site.baseurl}}/user-guide/workflows/portfolios/).

Continue with the [example tour]({{site.baseurl}}/user-guide/getting-started/showcase/) for other chart types, or run a complete
[Python analysis]({{site.baseurl}}/user-guide/workflows/scripting/) using the supported public API.
