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
parser provenance, and histories remain plain JSON-compatible data.

`PortfolioMigrator` upgrades older schema versions before restore. `StateManager.restore_session`
restores items independently and returns `RestoreReport`, which makes skipped plots, malformed parse
variables, and data errors visible.

`ring5.render_portfolio` uses the same restore path, then renders and exports every restored plot.
The CLI upgrade command re-saves only a complete restore.

## Compatibility rules

- Increment and migrate the schema for a breaking serialized change.
- Preserve plot and shaper identifiers or translate them during migration.
- Keep plot configuration JSON-compatible and retain figure-config enrichment where required.
- Treat portfolio JSON as untrusted input: sanitize names, validate paths, and validate fields.
- Test old fixtures, partial restore reporting, duplicate names, and current round trips.

Do not silently drop incompatible state while overwriting a portfolio.
