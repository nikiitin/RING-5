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

1. Read `src/parsing/parser_protocol.py` and the gem5 implementation.
2. Create the simulator package with scanning, parsing, strategies, and model adapters needed by the
   protocol.
3. Produce the CSV contract in `src/core/models/csv_contract.py`; use `NaN` for missing numeric
   values and report malformed input.
4. Add a `SimulatorInfo` entry and parser factory in `src/parsing/registry.py`.
5. Import the backend registration from the parsing composition path.
6. Keep scan and parse submission asynchronous. Finalization aggregates caller-owned results and
   exposes file failures.

Metadata supplies the UI display name, default file pattern, strategies, variable types, and any
internal statistics excluded from selection. Do not add simulator conditionals to a generic web
component when metadata or a protocol method can express the difference.

## Add or change a gem5 stat type

For a gem5 type, add a decorated `StatType` under `src/parsing/gem5/types/`, import it so registration
runs, update both ordered Perl classification paths under `src/parsing/gem5/perl/libs/`, and expose
the type string in the gem5 registry metadata. Classification order matters where formats overlap.

Preserve the lifecycle that balances and reduces content before reading reduced values. Pass scanned
variables into parsing when a regex or pattern must expand to concrete names.

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
