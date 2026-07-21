---
layout: default
title: Portfolio Subsystem
parent: Subsystems
grand_parent: Developer Guide
nav_order: 5
permalink: /developer-guide/subsystems/portfolios/
redirect_from:
  - /developer-guide/web/portfolio-system/
---

# Portfolio subsystem

`PortfolioService` serializes workspace state to JSON under the application data directory. The
embedded DataFrame is stored as CSV text; plots serialize through `BasePlot.to_dict`; configuration,
parser provenance, histories, and save-time environment metadata remain plain JSON-compatible data.

`PortfolioIntegrityService` creates a canonical-JSON SHA-256 digest for the body and separate input,
configuration, and output digests. Its optional signature is HMAC-SHA-256 over the manifest
statement. The service returns `PortfolioIntegrityReport`; checksum validity and signature validity
remain separate so no caller can accidentally describe unsigned content as authenticated.

`PortfolioMigrator` upgrades older schema versions before restore. `StateManager.restore_session`
restores items independently and returns `RestoreReport`, which makes skipped plots, malformed parse
variables, and data errors visible.

`ring5.render_portfolio` uses the same restore path, then renders and exports every restored plot.
The CLI upgrade command re-saves only a complete restore.

## Compatibility rules

<!--
`uman~ring5.portfolio.migration.documentation~1`

Covers:
- req~ring5.portfolio.migration~1

-->

- Increment and migrate the schema for a breaking serialized change.
- Schema V3 adds environment metadata. V1/V2 migration records it as `null`; historical values must
  never be inferred from the machine performing migration.
- Schema V4 adds `integrity_manifest`. V1–V3 migration records it as `null`; generating checksums
  during migration would create false historical evidence.
- Preserve plot and shaper identifiers or translate them during migration.
- Keep plot configuration JSON-compatible and retain figure-config enrichment where required.
- Treat portfolio JSON as untrusted input: sanitize names, validate paths, and validate fields.
- Test old fixtures, partial restore reporting, duplicate names, and current round trips.

Do not silently drop incompatible state while overwriting a portfolio.

## Integrity trust boundary

New saves always create a checksum manifest. `PortfolioService`, `PortfolioRevisionService`, and
`BrowserUploadService` verify the manifest before migration or restoration; mismatched and malformed
content must not reach `StateManager.restore_session`. Legacy portfolios remain readable with the
explicit `legacy-unverified` result.

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
