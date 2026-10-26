---
layout: default
title: Portfolio Subsystem
parent: Subsystems
grand_parent: Developer Guide
nav_order: 5
permalink: /developer-guide/subsystems/portfolios/
---

# Portfolio subsystem

`PortfolioService` serializes workspace state to JSON under the application data directory. The
embedded DataFrame uses the shared typed table codec; plots serialize through `BasePlot.to_dict`;
configuration,
parser provenance, histories, and save-time environment metadata remain plain JSON-compatible data.

`PortfolioIntegrityService` creates a canonical-JSON SHA-256 digest for the body and separate input,
configuration, and output digests. Its optional signature is HMAC-SHA-256 over the manifest
statement. The service returns `PortfolioIntegrityReport`; checksum validity and signature validity
remain separate so no caller can accidentally describe unsigned content as authenticated.

`validate_portfolio_schema` accepts only the current serialized format before restore. `StateManager.restore_session`
restores items independently and returns `RestoreReport`, which makes skipped plots, malformed parse
variables, and data errors visible.

`ring5.render_portfolio` uses the same restore path, then renders and exports every restored plot.


## Schema contract

<!--
`uman~ring5.portfolio.schema.documentation~1`

Covers:
- req~ring5.portfolio.schema~1

-->

The supported portfolio schema is version 9. Serialized files declare `schema_version: 9`,
`version: "9.0"`, their parser strategy and simulator, environment metadata, and an integrity
manifest. Missing or unsupported schema versions raise a typed version error before restoration.
No reader infers old defaults, translates keys, or rewrites a file into the current schema.
Editable plot configuration uses `legend2_*` for a separate right legend and
`anchor_x`/`anchor_y` in every legend tier. Retired `dual_legend_*` and tier
`xanchor`/`yanchor` configuration keys in every tier, including the primary legend, fail before
plot restoration. Built-in heatmap configurations use `color_palette`, `reverse_colorscale`
and `show_values`; their key admission uses the explicit plot type so plugin-owned keys and
typed trace colorscales remain independent. Recipe schema 4 shares the same key admission
while retaining unmaterialized parameter values. Concrete common values
use a separate `validate_plot_config_values` stage: every legend orientation is exactly
`horizontal` or `vertical`. Recipe save/load retain template values; materialization applies
the concrete-value guard after parameter substitution.
Per-series styles map text names to style mappings, with a current string `pattern` value.
A present `opacity` is a finite real scalar in `[0, 1]`; omission preserves source opacity, while
explicit `0` and `1` override it. Present `null`, booleans and strings are rejected after recipe
materialization. Template admission retains opacity placeholders before materialization.
The same pure admission runs before plot enrichment, portfolio publication and restoration.

Treat portfolio JSON as untrusted input: sanitize names, validate paths, and verify content before
restoration. Test current writer round trips, partial restore reporting, duplicate names, and
rejection of unsupported schemas. Do not overwrite a partial restore without reviewing its report.

## Integrity trust boundary

New saves always create a checksum manifest. `PortfolioService`, `PortfolioRevisionService`, and
`BrowserUploadService` validate the schema and verify the manifest before restoration. Missing, mismatched, or malformed
manifests must not reach `StateManager.restore_session`.

The whole-document digest excludes only `integrity_manifest`. Named sections are diagnostic subsets:

- inputs: embedded typed workspace data plus CSV/parser provenance;
- configuration: application configuration, histories, plot definitions, and pipelines, excluding
  plot result data;
- outputs: plot IDs and typed source and processed frames.

The whole digest also covers schema/version, timestamp, environment metadata, and any unknown
top-level field, so an unchanged named-section table does not imply an unchanged document.

HMAC secrets enter only through save/verify calls and must never enter serialized state, logs, job
records, or error text. A signed manifest without a supplied secret is `signature-unverified`; a
wrong secret is `signature-invalid`. Restoring signed content without authentication is permitted by
the general core API only when `require_signature` is false. Human-facing restore flows require a
secret whenever a signature is present. Automation that expects a signature must always set
`require_signature=True`, because an optional signature cannot prevent stripping without an
external trust policy.

## Portable bundle format

`PortfolioBundleService` writes deterministic `.ring5-bundle` ZIP archives with fixed member
timestamps and sorted paths. `manifest.json` declares every member's role, media type, uncompressed
size, and SHA-256 digest. Required roles are the portfolio, source manifest, environment metadata,
and Python requirements. One exact `.ring5-snapshot` and bounded files below `results/` are optional.

Readers reject duplicate, encrypted, unsupported-compression, absolute, backslash, traversal,
undeclared, oversized, or checksum-mismatched members before returning content. The nested snapshot
is decoded and fingerprint-verified in memory. The portfolio schema and integrity checks run before
`restore_session`. Neither ZIP layer is extracted to a filesystem, and browser inspection remains
non-mutating until explicit restoration.


## Typed frame persistence

`TypedTableCodec` owns the current `ring5.typed-table` payload. A portfolio's `data` field and
each plot's `source_data` and `processed_data` fields contain that payload or `null`. Empty frames
remain present tables. The codec retains typed values, nullable dtypes, category order, exact axes
and supported attributes. It rejects unknown schema keys, unsupported types and coercing
reconstructions before publication. Plot sources remain distinct from their transformed results.

Dataset snapshots use the same codec inside their own archive container. CSV remains available
for input and export. Integrity manifests checksum the complete typed JSON documents; logical
frame fingerprints identify scientific content and remain a separate contract. The source manifest
records a SHA-256 digest of the canonical serialized typed payload under `embedded_table_sha256`.


Typed table admission checks decoded allocation budgets before constructing pandas axes or arrays.
Each table supports at most 1,000,000 axis entries, 10,000 columns and 5,000,000 cells, within
10,000,000 aggregate items, 64 MiB of estimated encoded graph or decoded storage, and 32 nesting
levels. Encoding charges nodes incrementally before emitting them and iterates frame values
without bulk list conversion.
The budget includes category and MultiIndex levels, compact range axes, padded dtypes and nested
attribute arrays. Container byte limits remain independent; a compact file cannot declare an
unbounded decoded table.

Plot documents use the fields admitted by `src/core/common/plot_payload.py`. Legend names live in
`config.legend_labels`; copies, comparisons and portfolio restoration use that same configuration.
Unknown plot fields raise errors before restoration or publication. Explicit `FigureConfig.from_dict`
decoding rejects unknown typography names. A saved `figure_spec` records resolved styling metadata
for inspection; restoration uses the plot configuration.
