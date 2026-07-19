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

<!--
`uman~ring5.ingestion.parse-integrity.documentation~1`

Covers:
- req~ring5.ingestion.parse-integrity~1

-->

Check **Stats directory path** and **File pattern** against the filesystem. Run **Quick Scan** first,
then use **Deep Scan** when variables differ between runs. Parsing needs Perl; check it with
`ring5 doctor`.

If the path is outside the allowed web roots, start RING-5 from the results parent directory or set
`RING5_ALLOWED_STATS_ROOTS` before starting the server. The Data Source page lists the active roots.
Separate multiple roots with `:` on Linux and macOS or `;` on Windows.

If a scan reports a line, file-size, file-count, or timeout limit, narrow the selected results tree
or split the analysis. The scanner fails that file visibly; it never returns the first part of an
oversized file as though the scan were complete. In Python, `scan_limit=0` scans all matches up to
the 10,000-file discovery ceiling. The web Deep Scan deliberately samples at most 256 files.

Do not use lenient parsing to hide a misspelled statistic. `--lenient` and `strict=False` are for
intentional missing columns represented as `NaN`.

## Input bounds and path containment

<!--
`uman~ring5.quality.input-security.documentation~1`

Covers:
- req~ring5.quality.input-security~1

-->

Browser paths are resolved below configured statistics roots, file names and glob patterns are
sanitized before filesystem work, and regular-expression matching has pattern, input-length, and
execution-time bounds. Large data columns are also capped before their distinct values become
widget options. A rejected or truncated input is reported; widening a limit requires reviewing the
work and payload it permits.

## Parsing reports a resource-limit error

Reduce either the number of files or requested variables. One parse accepts at most 4,096 files,
2,048 logical variables and aliases, one million file-variable cells, 256 MiB per input file, and
4 GiB across the selected inputs. A parser worker rejects an input beyond ten million lines, and a
parse batch has a ten-minute completion bound. These are
failure boundaries, not truncation points: no CSV is reported as complete after a limit is crossed.

A pattern variable expands to at most 1,024 instances by default. On trusted inputs only, set
`RING5_MAX_VAR_REPEAT` to a larger integer or `0` to disable that cap. Arbitrary regular expressions
are not supported; use literal ASCII statistic-name characters and `\d+` placeholders.

## A CSV does not load

<!--
`uman~ring5.ingestion.csv-contract.documentation~1`

Covers:
- req~ring5.ingestion.csv-contract~1

-->

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
