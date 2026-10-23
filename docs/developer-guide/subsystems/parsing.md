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

The gem5 backend produces one row per input file. `repeat` declares the expected number of dumps
per concrete statistic. Spatial patterns average all concrete instances and dumps; scanner-generated
scalar-pattern vectors retain one entry per selected instance and average its temporal dumps.
Missing variables, expected instances, dumps, or summary measurements remain `NaN`. Only omitted
interior frequency buckets in an otherwise complete observed distribution are inferred as zero.

Full and incremental parsing use the same deterministic union of observed columns. A histogram
bucket discovered in a later file remains in the schema, with `NaN` for files lacking that bucket.
Raw gem5 histogram endpoints are inclusive integers (`0-9`, `10-19`). Rebinning treats these as
`[0,10)` and `[10,20)`, and preserves total frequency under the uniform-within-bucket assumption.
New integer output bins retain inclusive labels; fractional boundaries use explicit half-open
labels such as `[0,2.5)`. `10+` includes values at or above ten, and `<0` retains negative mass.
A single target bin is labeled `0+` because it retains all nonnegative values, including overflow.
The figure layer also supports legacy CSV histograms with shared-edge continuous labels.

Config-aware parsing reads `config.ini` as UTF-8 literal values and preserves parameter-name case.
Percent signs and interpolation-looking workload arguments remain unchanged.

## Failure and security rules

- Do not turn a regex miss, missing statistic, worker failure, or malformed file into zero.
- Preserve path validation and leading-dash checks before work reaches subprocesses.
- Keep core services and Streamlit out of parsing imports.
- Release or cancel owned futures without shutting down another session's live work.

See [Add a Parser]({{site.baseurl}}/developer-guide/extension-guides/adding-a-parser/) for
implementation steps.
