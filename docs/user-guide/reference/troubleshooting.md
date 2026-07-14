---
layout: default
title: Troubleshooting and FAQ
parent: Reference
grand_parent: User Guide
nav_order: 5
permalink: /user-guide/reference/troubleshooting/
redirect_from:
  - /user-guide/reference/faq/
  - /user-guide/reference/keyboard-shortcuts/
---

# Troubleshooting and FAQ

## The application does not start

Run from the repository root and use the environment installed by `make dev` or `make install`:

```bash
test -x python_venv/bin/streamlit
make run
```

If port 8501 is occupied, stop the previous Streamlit process or pass a different server port to
the Streamlit command.

## Parsing finds no files or variables

Check **Stats directory path** and **File pattern** against the filesystem. Run **Quick Scan** first,
then use **Deep Scan** when variables differ between runs. Parsing needs Perl; check it with
`ring5 doctor`.

Do not use lenient parsing to hide a misspelled statistic. `--lenient` and `strict=False` are for
intentional missing columns represented as `NaN`.

## A CSV does not load

Confirm that the file is readable, has a non-empty header, contains a data row, and uses consistent
row widths. RING-5 does not require specific gem5 columns. Operations later validate the columns and
types they need.

## A plot is blank or reports missing columns

Inspect the finalized pipeline output, not only the workspace table. A selector or pivot may have
removed or renamed a mapped column. Check row count, numeric types, missing values, and plot mapping,
then select **Finalize Pipeline for Plotting** and **Refresh Plot**.

## Normalization fails

Every group must contain the selected baseline, and its denominator must be nonzero. Check spelling,
types, and whitespace in the baseline column. Preview the pipeline immediately before and after the
normalize step.

## Static Plotly export fails

Plotly PNG, SVG, and PDF require a Chrome-family browser. Use Plotly HTML, switch to Matplotlib, or
install the browser dependency reported by `ring5 doctor`.

## PGF export fails or becomes PDF

Run `make check-latex`. PGF requires XeLaTeX and supporting packages. Raster content cannot be saved
as PGF; the web application warns and downloads PDF instead.

## A portfolio restores partially

Read every `RestoreReport` field in Python or every warning in the web application. Do not upgrade
or overwrite the source portfolio until the data and all intended plots restore. Newer portfolio
schema versions cannot be loaded by older RING-5 releases.

## Are there application keyboard shortcuts?

RING-5 does not define a custom shortcut layer. Browser, Streamlit, and Plotly interactions apply
only when their controls have focus. Use the visible navigation and plot modebar so a browser
shortcut does not accidentally replace an application action. Stop the local server with
<kbd>Ctrl</kbd>+<kbd>C</kbd> in its terminal.

## Where should I report a reproducible failure?

Open a GitHub issue with the RING-5 version, command or UI path, complete error, minimal input shape,
and output from `ring5 doctor`. Remove private result paths and unpublished data.
