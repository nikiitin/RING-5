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
embedded DataFrame is stored as CSV text; plots serialize through `BasePlot.to_dict`; configuration,
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

The supported portfolio schema is version 4. Serialized files declare `schema_version: 4`,
`version: "4.0"`, their parser strategy and simulator, environment metadata, and an integrity
manifest. Missing or unsupported schema versions raise a typed version error before restoration.
No reader infers old defaults, translates keys, or rewrites a file into the current schema.

Treat portfolio JSON as untrusted input: sanitize names, validate paths, and verify content before
restoration. Test current writer round trips, partial restore reporting, duplicate names, and
rejection of unsupported schemas. Do not overwrite a partial restore without reviewing its report.

## Integrity trust boundary

New saves always create a checksum manifest. `PortfolioService`, `PortfolioRevisionService`, and
`BrowserUploadService` validate the schema and verify the manifest before restoration. Missing, mismatched, or malformed
manifests must not reach `StateManager.restore_session`.

The whole-document digest excludes only `integrity_manifest`. Named sections are diagnostic subsets:

- inputs: embedded CSV and semantics plus CSV/parser provenance;
- configuration: application configuration, histories, plot definitions, and pipelines, excluding
  plot result data;
- outputs: plot IDs, processed CSV data, and processed semantics.

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
