---
layout: default
title: Parsing Subsystem
parent: Subsystems
grand_parent: Developer Guide
nav_order: 1
permalink: /developer-guide/subsystems/parsing/
redirect_from:
  - /developer-guide/parsing/
  - /developer-guide/parsing/parsing-architecture/
  - /developer-guide/parsing/gem5-deep-dive/
---

# Parsing subsystem

`src/parsing/parser_protocol.py` defines `SimulationParser`. `src/parsing/registry.py` maps simulator
names to immutable metadata and parser factories. The web application and `ring5.Session` select a
registered backend rather than importing a simulator implementation directly.

## Async contract

<!--
`uman~ring5.ingestion.persistent-workers.documentation~1`

Covers:
- req~ring5.ingestion.persistent-workers~1

-->

Scanning and parsing are submit/finalize operations. Submit methods validate inputs and return
futures owned by the caller or a parse job. Finalization aggregates successful results, preserves
file failures, and assembles the CSV. Cancellation must affect only work owned by the current API
instance or job.

The gem5 implementation under `src/parsing/gem5/` uses Python orchestration and persistent Perl
workers. Strategies under `src/parsing/gem5/impl/strategies/` control ingestion. Pattern aggregation
can collapse repeated concrete names into a selectable pattern; parsing needs scanned-variable data
to expand those patterns correctly.

## Variable types and CSV

<!--
`uman~ring5.ingestion.pattern-aggregation.documentation~1`

Covers:
- req~ring5.ingestion.pattern-aggregation~1

-->

gem5 stat types register through decorators under `src/parsing/gem5/types/`. Perl scanning modules
classify input lines, while Python types validate, balance, and reduce parsed content. The simulator
registry exposes supported variable-type strings to the UI.

All parsers produce the generic contract in `src/core/models/csv_contract.py`: a header, rows,
consistent columns, values, and explicit `NaN` for missing numeric data. Simulator-specific column
names remain inside the backend.

## Failure and security rules

- Do not turn a regex miss, missing statistic, worker failure, or malformed file into zero.
- Preserve path validation and leading-dash checks before work reaches subprocesses.
- Keep core services and Streamlit out of parsing imports.
- Release or cancel owned futures without shutting down another session's live work.

See [Add a Parser]({{site.baseurl}}/developer-guide/extension-guides/adding-a-parser/) for
implementation steps.
