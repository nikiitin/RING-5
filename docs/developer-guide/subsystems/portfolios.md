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
- Preserve plot and shaper identifiers or translate them during migration.
- Keep plot configuration JSON-compatible and retain figure-config enrichment where required.
- Treat portfolio JSON as untrusted input: sanitize names, validate paths, and validate fields.
- Test old fixtures, partial restore reporting, duplicate names, and current round trips.

Do not silently drop incompatible state while overwriting a portfolio.
