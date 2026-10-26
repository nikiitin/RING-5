---
layout: default
title: Add a Parser
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 1
permalink: /developer-guide/extension-guides/adding-a-parser/
---

# Add a parser

A simulator backend implements `SimulationParser` and registers a factory plus immutable metadata.
Keep simulator-specific names and file handling inside `src/parsing/<simulator>/`.

## Implement the backend

<!--
`uman~ring5.ingestion.simulator-registry.documentation~1`

Covers:
- req~ring5.ingestion.simulator-registry~1

`uman~ring5.extension.parser-protocol.documentation~1`

Covers:
- req~ring5.extension.parser-protocol~1

-->

1. Read `src/parsing/parser_protocol.py` and the gem5 implementation.
2. Create the simulator package with scanning, parsing, and strategies implementing the protocol.
   Complete reduction before each Future resolves to immutable `ParsedFileResult` values.
3. Declare each variable's kind, explicit scalar/entries shape and owned physical columns. Numeric
   cells require floats, including NaN; text cells require exact strings. Metadata columns are
   explicit text cells. Reject missing text and physical column collisions before publication.
   Finalize with the submitted batch's complete plan using the public helpers below.
4. Add a `SimulatorInfo` entry and parser factory in `src/parsing/registry.py`.
5. Import the backend registration from the parsing composition path.
6. Keep scan and parse submission asynchronous. Finalization aggregates caller-owned results and
   exposes file failures.

Metadata supplies the UI display name, default file pattern, strategies, variable types, and any
internal statistics excluded from selection. Do not add simulator conditionals to a generic web
component when metadata or a protocol method can express the difference.

## Public typed output SDK

External backends import their transport values and helpers from `ring5`:

```python
from pathlib import Path
import ring5

def finalize(
    batch: ring5.ParseBatchResult,
    results: list[ring5.ParsedFileResult],
    *,
    complete: bool = True,
) -> ring5.ParsedOutput:
    resolved = ring5.resolve_parsed_output(
        results, batch.var_names, batch.source_paths, complete=complete
    )
    return ring5.publish_parsed_output(
        resolved, Path(batch.output_dir) / "results.csv"
    )
```

`ParseBatchResult` requires an immutable Future tuple and the exact source/output/strategy context.
`ParsedVariableSchema`, `ParsedVariableResult`, `ParsedCell`, `ParsedColumn`, `ParsedSchema`,
`ParsedFileResult`, `ResolvedParsedRows` and `ParsedOutput` are the actual immutable value
constructors. Scalar variables own exactly one cell; entry variables may be empty when nothing was
observed. Every source must provide all declared text and metadata cells; numeric union gaps remain
NaN. Do not invent a bucket for an unobserved dynamic variable. Complete finalization covers every
planned source, while partial finalization still rejects duplicate and unplanned source paths.

The single sequence is `resolve_parsed_output(results, ...)` then
`publish_parsed_output(resolved, path)`. Helpers raise `ParseError` for invalid resolution or
publication; individual immutable constructors reject wrong shapes/types with `TypeError` or
`ValueError`. `ParsedOutput.sha256` binds canonical schema meaning and CSV bytes, not just raw CSV
bytes. Consumers must retain the descriptor and verify it through the canonical reader. No backend
writes a second CSV format or embeds provenance in a magic statistic name.

Inject a backend with `Session(parser=backend)`. Its automatic source capture requires a declared
simulator; an undeclared injected backend can still execute an explicit caller `RecipeSource`.
Backend factories registered through the repository composition can be replayed by that registered
identifier. A backend's arbitrary internal memory remains its responsibility; gem5's admitted work
uses the shared per-submitted-batch result budget.

## Add or change a gem5 stat type

For a gem5 type, add a decorated `StatType` under `src/parsing/gem5/types/`, import it so registration
runs, update the shared Perl classifier under `src/parsing/gem5/perl/libs/`, and expose
the type string in the gem5 registry metadata. Classification order matters where formats overlap.

Implement typed `add_observation` storage hooks and inherit the public lifecycle from `StatType`.
A numeric point, literal configuration string, or numeric mapping represents one observation;
convert numeric wire text in the worker before ingestion. Declare ordinary slots and return defensive
content snapshots. Implement `_missing_count()` from actual observation presence, keeping observed
NaN distinct from absence. Implement `_balance()` to validate expected counts and return missing-value
padding, then `_reduce()` to compute the typed result. Frame kinds can use `FrameStatType` with an
exact entry schema and `_prepare_frame()` hook. Collection ends after balancing; reduction follows
balancing; completed stages are idempotent. Reduced content is readable only after both succeed.
Pass scanned variables when a regex or pattern must expand to concrete source records.

## Test and verify

- Unit-test scanning, parser validation, missing values, and malformed files.
- Test any Perl classifier with representative input lines.
- Add an integration test through `ApplicationAPI.submit_parse_async` and finalization.
- Use real gem5 fixtures when changing existing gem5 output.

```bash
make arch-check
python_venv/bin/mypy src
python_venv/bin/pytest tests/unit -k "parse or scan" -q -n 0 --no-cov
```
