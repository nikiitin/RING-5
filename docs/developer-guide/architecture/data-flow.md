---
layout: default
title: Data Flow
parent: Architecture
grand_parent: Developer Guide
nav_order: 2
permalink: /developer-guide/architecture/data-flow/
redirect_from:
  - /engineering-reference/architecture/data-flow/
---

# Data flow

## Parse and load

<!--
`uman~ring5.ingestion.parse-output-provenance.documentation~1`

Covers:
- req~ring5.ingestion.parse-output-provenance~1

`uman~ring5.quality.async-ownership.documentation~1`

Covers:
- req~ring5.quality.async-ownership~1

-->

```mermaid
sequenceDiagram
    participant UI as Web or ring5.Session
    participant API as ApplicationAPI
    participant Parser as SimulationParser
    participant Pool as Work pools
    participant Cache as Incremental JSON cache
    participant State as StateManager
    UI->>API: submit scan or parse
    API->>Parser: validate and create work
    Parser->>Pool: submit independent files
    Pool-->>API: results and visible failures
    UI->>API: finalize batch
    opt incremental parse
        Parser->>Cache: reuse fingerprint-matched scalar rows
        Parser->>Cache: atomically replace successful merged rows
    end
    API->>Parser: assemble and validate CSV
    API->>State: store table and provenance
```

Scan and parse work follows submit/finalize contracts. Submission returns owned futures; finalization
aggregates results and preserves per-file failures. Do not hide asynchronous work inside a component
or fabricate a placeholder value after a parser error.

`BackgroundJobService` observes those existing futures without duplicating their parser payloads.
It also owns a two-worker executor for explicitly submitted transformations and exports. Its
thread-safe records are bounded, exposed as immutable snapshots, and scoped to one
`ApplicationAPI` session. Cancellation distinguishes a request from terminal cancellation, and a
retry is offered only when the service owns a factory for the complete operation. The web job
center depends on the application facade and these core models; core does not import Streamlit.

Incremental submission first discovers the same bounded file set and hashes complete input
contents. It filters the normal strategy work items to new or changed paths; it does not introduce
a synchronous parser or bypass the shared worker pool. Finalization uses each worker result's
internal source provenance to replace exactly that file's finalized row, retains unchanged rows,
and omits deleted paths. The JSON cache contains strings and fingerprints rather than pickles or
live parser objects. The final CSV and cache are each replaced atomically, and the cache is written
only after every changed worker succeeds.

`Session.load` and the CSV pool converge on `ApplicationAPI.load_data`, which stores a DataFrame in
the session repository. The generic CSV contract requires a header and rows; individual services
validate operation-specific columns and types.

The review-before-load path first creates an immutable `ImportPreview` in the core service. Format
detection, corrections, inference, and row classification do not touch session state. Loading
re-reads the bounded source, verifies its SHA-256 fingerprint and the complete preview result, then
stores only accepted rows through `ApplicationAPI.load_import_preview`.

Browser uploads cross a separate `BrowserUploadService` trust boundary. It validates extension,
declared media type, byte size, and parse structure before staging content below the session's
temporary directory. CSV stays delimited text; flat JSON and the first visible Excel worksheet are
normalized to bounded UTF-8 CSV and then enter the normal `ImportPreview` path. A portfolio is
migrated and summarized without state mutation, re-fingerprinted on confirmation, and only then
passed to `StateManager.restore_session`.

Remote sources enter that same boundary through `RemoteSourceService`. Its HTTP, system-SSH, and
S3-compatible adapters share a deny-by-default `RemoteSourcePolicy`, DNS/private-address checks,
bounded reads, sanitized errors, and query-free display provenance. HTTP redirects are
re-authorized; credentialed requests do not redirect. The application facade passes only fetched
bytes and a safe filename into `BrowserUploadService`, so remote transports cannot bypass import
review or portfolio confirmation.

## Transform and plot

```mermaid
flowchart LR
    RAW[Session data] --> MANAGER[Data manager service]
    MANAGER --> UPDATED[New session DataFrame]
    UPDATED --> PIPE[Per-plot shaper pipeline]
    PIPE --> PROCESSED[Processed plot data]
    PROCESSED --> TRACE[Typed trace construction]
    TRACE --> SPEC[Resolved FigureConfig]
    SPEC --> PLOTLY[Plotly connector]
    SPEC --> MPL[Matplotlib connector]
```

Manager services and shapers copy their inputs. A confirmed manager result replaces the workspace
table; a shaper result belongs to its plot. The render controller pairs processed data, persisted
configuration, rendering engine, and a cache key before reusing a figure.

## Save and restore

Portfolio saving serializes the active table, plots, plot configuration, pipelines, parser
provenance, and history. `PortfolioMigrator` upgrades older JSON before
`StateManager.restore_session` restores compatible items and returns a `RestoreReport`.

Headless replay loads the same portfolio, renders each restored plot through the selected connector,
and exports it. A partial restore remains visible; the CLI refuses to upgrade a portfolio when
re-saving would discard skipped content.
