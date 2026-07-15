---
layout: default
title: Load and Parse Data
parent: Workflows
grand_parent: User Guide
nav_order: 1
permalink: /user-guide/workflows/loading-data/
redirect_from:
  - /user-guide/pages/data-source/
---

# Load and parse data

Start with a gem5 results tree when RING-5 should discover and parse statistics. Start with a CSV
when another tool already produced the analysis table.

## Parse gem5 statistics in the web application

On **Data Source**, select **Parse gem5 Stats Files** and set:

- **Stats directory path** to the common root of the gem5 runs.
- **File pattern** to the statistics filename, normally `stats.txt`. Wildcards such as `*.txt` are
  accepted.
- **Select ingestion strategy** to a strategy provided by the selected simulator. Keep the default
  unless your dataset needs a different registered strategy.

Select **Quick Scan** to inspect a bounded sample. Use **Deep Scan** when variables or vector entries
differ across runs. Quick Scan reads up to 10 files; Deep Scan reads up to 256 files. Scanning
discovers names and types; it does not parse the dataset. A scan that cannot read every selected
file reports the file failures instead of presenting partial metadata as complete.

The path must be below an allowed root displayed on the Data Source page. Administrators configure
the roots with the `RING5_ALLOWED_STATS_ROOTS` environment variable; when it is unset, RING-5 uses
the directory where the web process started. See
[Install RING-5]({{site.baseurl}}/user-guide/getting-started/installation/) for examples.

Add variables from the scan results. Check vector and distribution entry selections before parsing:
their configuration controls which output columns are created. Then select **Parse gem5 Stats
Files**. RING-5 assembles the parser output into one CSV and loads it into the workspace.

The parser records missing values as `NaN`. It reports file failures instead of substituting
simulator values. Investigate missing variables before reducing or normalizing the data.

## Reopen parser output in the web application

Parsed CSVs are stored in the application's recent-file pool. On **Data Source**, select **Load from
Recent**, choose a file, and load it. The recent-file pool is local application state, not a durable
archive; copy important results to research storage.

## Load an existing CSV in Python

`Session.load` reads a non-empty CSV with a header. It does not require fixed gem5 columns.

```python
import ring5

with ring5.Session() as session:
    data = session.load("results.csv")
    print(data.columns.tolist())
```

An operation may still require categorical or numeric columns appropriate to that task. Loading
raises `ring5.DataLoadError` for missing, unreadable, malformed, or empty input.

## Parse from Python

The synchronous API scans, submits parser work, finalizes it, and returns the assembled CSV path:

```python
import ring5

with ring5.Session() as session:
    result = session.parse(
        "results/",
        variables=["simTicks", "system.cpu.ipc"],
        pattern="stats.txt",
        scan_limit=10,
    )
    data = session.load(result.csv_path)
```

Set `scan_limit=0` when every matching file must be scanned for variable discovery. Exhaustive
discovery is capped at 10,000 files; a larger explicit limit is rejected. This differs from the web
Deep Scan sample, which remains capped at 256 files. By default, `parse` raises
`ring5.MissingStatError` if a requested statistic produces no values. Use `strict=False` only when
a `NaN` column is an intentional part of the analysis.

Pattern variables accept the scanner form `system.cpu\d+.ipc` and the equivalent escaped-literal
form `system\.cpu\d+\.ipc`. Only literal statistic-name characters and `\d+` numeric placeholders
are accepted; arbitrary regular expressions are rejected before parsing.

For a non-blocking workflow, call `Session.parse_submit(...)`, then `finalize()` or `cancel()` on the
returned job. Each job owns its futures.

Parsing and pattern expansion have aggregate file, byte, variable, file-variable, and time bounds.
Crossing a bound raises `ring5.ScanError` or `ring5.ParseError`; RING-5 does not truncate the output
and report success. For trusted, unusually wide pattern variables, `RING5_MAX_VAR_REPEAT` can raise
the default 1,024-instance cap, or `0` can disable that one cap.

## Parse from the CLI

Repeat `--variable` for each statistic:

```bash
source python_venv/bin/activate
ring5 parse results/ \
  --variable simTicks \
  --variable system.cpu.ipc \
  --output analysis/results.csv
```

The CLI defaults to the `stats.txt` pattern and strict missing-stat handling. Run
`ring5 parse --help` for the current arguments.

Next: [Manage Datasets]({{site.baseurl}}/user-guide/workflows/managing-datasets/) or
[Create and Configure Plots]({{site.baseurl}}/user-guide/workflows/plotting/).
