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

<!--
`uman~ring5.ingestion.configuration.documentation~1`

Covers:
- req~ring5.ingestion.configuration~1

`uman~ring5.ingestion.configuration-fallbacks.documentation~1`

Covers:
- req~ring5.ingestion.configuration-fallbacks~1

`uman~ring5.ingestion.distribution-range-scan.documentation~1`

Covers:
- req~ring5.ingestion.distribution-range-scan~1

`uman~ring5.ingestion.file-discovery.documentation~1`

Covers:
- req~ring5.ingestion.file-discovery~1

`uman~ring5.ingestion.gem5-backend.documentation~1`

Covers:
- req~ring5.ingestion.gem5-backend~1

`uman~ring5.ingestion.histogram-rebinning.documentation~1`

Covers:
- req~ring5.ingestion.histogram-rebinning~1

`uman~ring5.ingestion.output-aliases.documentation~1`

Covers:
- req~ring5.ingestion.output-aliases~1

`uman~ring5.ingestion.pattern-index-selection.documentation~1`

Covers:
- req~ring5.ingestion.pattern-index-selection~1

`uman~ring5.ingestion.scalar.documentation~1`

Covers:
- req~ring5.ingestion.scalar~1

`uman~ring5.ingestion.scan-presets-progress.documentation~1`

Covers:
- req~ring5.ingestion.scan-presets-progress~1

`uman~ring5.ingestion.source-modes.documentation~1`

Covers:
- req~ring5.ingestion.source-modes~1

`uman~ring5.ingestion.statistics-only.documentation~1`

Covers:
- req~ring5.ingestion.statistics-only~1

`uman~ring5.ingestion.variable-editor.documentation~1`

Covers:
- req~ring5.ingestion.variable-editor~1

`uman~ring5.ingestion.variable-entry-selection.documentation~1`

Covers:
- req~ring5.ingestion.variable-entry-selection~1

`uman~ring5.ingestion.variable-scan.documentation~1`

Covers:
- req~ring5.ingestion.variable-scan~1

`uman~ring5.ingestion.vector.documentation~1`

Covers:
- req~ring5.ingestion.vector~1

`uman~ring5.ingestion.web-path-authorization.documentation~1`

Covers:
- req~ring5.ingestion.web-path-authorization~1

-->

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

Use **Alias** when the CSV column should have a concise logical name while discovery still targets
the original statistic or numeric pattern. Scalar aliases must remain unique across both source and
output names. For a configuration variable, **On Empty** supplies the value to emit when the
selected path position contains no metadata; otherwise the first extracted value is retained.

The parser records missing values as `NaN`. It reports file failures instead of substituting
simulator values. Investigate missing variables before reducing or normalizing the data.

## Reopen parser output in the web application

<!--
`uman~ring5.ingestion.csv-delimiter-detection.documentation~1`

Covers:
- req~ring5.ingestion.csv-delimiter-detection~1

`uman~ring5.ingestion.csv-pool.documentation~1`

Covers:
- req~ring5.ingestion.csv-pool~1

-->

Parsed CSVs are stored in the application's recent-file pool. On **Data Source**, select **Load from
Recent**, choose a file, and load it. The recent-file pool is local application state, not a durable
archive; copy important results to research storage.

Recent-file cards include cached row, column, and type metadata. CSV loading detects common
delimiters rather than requiring comma-only input; the file must still satisfy the non-empty header
contract.

### Upload data or a portfolio from your browser

<!--
`uman~ring5.ingestion.browser-upload.documentation~1`

Covers:
- req~ring5.ingestion.browser-upload~1

-->

Select **Upload data or portfolio** on **Data Source** to choose a file from your computer. RING-5
accepts CSV, tabular JSON, modern Excel (`.xlsx`), and RING-5 portfolio JSON. The browser sends the
file contents—not its local path—and RING-5 keeps the staged copy in temporary session storage.

Each upload is limited to 64 MiB. RING-5 validates the filename extension, the browser-declared
media type, and the actual content before showing an action. It also fingerprints the original
bytes with SHA-256. JSON tables contain one object or an array of flat objects; nested cell values
are rejected. Excel imports use the first visible worksheet and require a unique, non-empty header
row. Tabular uploads are additionally bounded to 100,000 rows, 500 columns, 2,000,000 cells, and
10,000 characters per normalized cell.

CSV, JSON, and Excel datasets continue into the same required import review described below. A
JSON file that could be either data or a portfolio can be labeled explicitly with **Interpret JSON
as**. Portfolio uploads show their schema version, plot count, and whether data is present before
**Restore uploaded portfolio** replaces the current workspace. Validation alone never changes
workspace data or plots.

### Fetch an authorized remote source

<!--
`uman~ring5.ingestion.remote-sources.documentation~1`

Covers:
- req~ring5.ingestion.remote-sources~1

-->

Under **Upload data or portfolio**, select **Remote source** to fetch through HTTPS, SSH, or an
S3-compatible endpoint. Remote access is disabled until the server administrator sets an exact or
wildcard host allowlist, for example:

```bash
export RING5_ALLOWED_REMOTE_HOSTS="data.example.org,*.objects.example.org"
```

The allowlist is applied to the original host and every HTTP redirect. Public network addresses
are required by default, which prevents a remote URL from reaching loopback, link-local, or private
services. A controlled on-premises deployment can set `RING5_ALLOW_PRIVATE_REMOTE_HOSTS=1`.
HTTPS is required for HTTP and S3 endpoints; `RING5_REQUIRE_REMOTE_TLS=0` is available only for an
explicitly authorized development endpoint.

- **HTTPS** accepts a URL and an optional bearer token. URL query strings and tokens are omitted
  from displayed provenance and errors, and credentialed requests do not follow redirects.
- **SSH** uses the server process's SSH agent/configuration or a server-side private-key path. It
  requires batch mode, strict host-key checking, a safe absolute remote path, and never accepts a
  password in the source URI.
- **S3-compatible** uses path-style object URLs and optional AWS Signature Version 4 access,
  secret, and session credentials. Credentials are sent in headers and are not retained in the
  staged result.

Every adapter stops at the same 64 MiB boundary. The fetched bytes then undergo the same file-type,
parsing, fingerprint, and human review checks as a browser upload. Fetching alone does not change
workspace data or plots; select **Load accepted rows** or **Restore uploaded portfolio** only after
reviewing the result.

### Review a tabular import before loading

<!--
`uman~ring5.ingestion.import-preview.documentation~1`

Covers:
- req~ring5.ingestion.import-preview~1

-->

Select **Review & Load** or **Preview** on a recent-file card to inspect the source without changing
the workspace. Both actions open the same required review; no web import enters the workspace
directly. RING-5 shows the detected encoding and delimiter, every inferred column type, accepted
and rejected row counts, a bounded accepted-row preview, and the physical source line and reason
for each shown rejection.

Use the controls above the preview to correct the encoding, delimiter, one-based header row,
surrounding whitespace, and missing-value tokens. Set **Import as** for a column when its inferred
type is unsuitable. The preview is recalculated immediately, so a type mismatch becomes a visible
rejected row before loading. Select **Load accepted rows** only after those outcomes are correct.

The source is fingerprinted when previewed. If it changes before loading, RING-5 refuses the load
and asks for another review. Files, row counts, column counts, displayed rows, missing-value tokens,
and rejection details are bounded; accepted and rejected totals still describe the complete
reviewed source within those limits.

## Load an existing CSV in Python

<!--
`uman~ring5.ingestion.csv-load.documentation~1`

Covers:
- req~ring5.ingestion.csv-load~1

-->

`Session.load` reads a non-empty CSV with a header. It does not require fixed gem5 columns.

```python
import ring5

with ring5.Session() as session:
    data = session.load("results.csv")
    print(data.columns.tolist())
```

An operation may still require categorical or numeric columns appropriate to that task. Loading
raises `ring5.DataLoadError` for missing, unreadable, malformed, or empty input.

For review-before-load automation, call `preview_import`, inspect its immutable result, then pass
that exact result to `load_import`:

```python
with ring5.Session() as session:
    preview = session.preview_import(
        "instrument.txt",
        header_row=2,
        column_types={"ipc": "number", "stable": "boolean"},
    )
    print(preview.encoding, preview.delimiter)
    print(preview.accepted_row_count, preview.rejected_row_count)
    for row in preview.rejected_rows:
        print(row.line_number, row.reason)
    data = session.load_import(preview)
```

Supported corrections are UTF-8, UTF-8 with BOM, Windows-1252, or Latin-1 text; comma, semicolon,
tab, or pipe delimiters; and text, integer, number, boolean, or ISO datetime column types. Loading
uses nullable pandas dtypes where a reviewed numeric or boolean column contains missing values.

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
form `system\.cpu\d+\.ipc`. Only literal ASCII statistic-name characters and `\d+` numeric
placeholders are accepted; arbitrary regular expressions are rejected before parsing.

When a pattern has one or more numeric positions, **Select specific indices** filters the discovered
instances. Enabling it preserves each selected instance as a separate concrete output column;
leaving it disabled applies the variable type's normal pattern aggregation.

Vector, distribution, and histogram editors offer **Statistics Only**, **Entries Only**, and
**Entries + Statistics** modes where applicable. Entries can be selected from scan results or
entered manually. A per-variable deep scan discovers entries across the larger bounded sample and
aggregates the minimum and maximum bucket range for distributions. Histogram configurations can
also rebin inconsistent source ranges into a fixed bucket count and maximum range.

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
