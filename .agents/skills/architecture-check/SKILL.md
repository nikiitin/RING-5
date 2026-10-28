---
name: architecture-check
description: Gate the RING-5 architecture — the 7 hard rules and the strict 3-layer dependency direction (Web → Core ← Parsing). Use before merging, after any structural/refactor change, or when asked to "check architecture", "run the arch gate", or verify layer boundaries.
---

# Architecture check (the boundary gate)

RING-5 follows `Web → Core ← Parsing`. [AGENTS.md](../../../AGENTS.md) defines the required
invariants; pre-commit, CI and `make arch-check` enforce the structural and unsafe-syntax subset.
Review behavioral requirements in the touched owners as well as running the checker.

## Run it

```bash
make arch-check
make quality-gate
```

`make arch-check` runs `scripts/check_architecture.py`. The AST checker inspects production
imports, layer boundaries, session-state access, mutation flags, bare exception handlers, dynamic
execution, and ellipsis statements. The local `architecture` pre-commit hook runs the same script.
The required invariants are defined in [AGENTS.md](../../../AGENTS.md).

Read touched parsing paths to verify that failures remain visible and submit/finalize contracts
are preserved. Syntax checks cannot prove those behavioral properties. Git operations follow the
user's instructions and must preserve unrelated work.

## What "fix at the source" means
- Web service/state operations go through `ApplicationAPI` and its three sub-APIs. Shared typed
  models and protocols remain valid imports. See [api-check](../api-check/SKILL.md).
- Core needs parsing? Through the `SimulationParser` protocol + `SimulatorRegistry`, never a
  `src/parsing/gem5/...` concrete import.
- Models own typed data and validation; scientific algorithms and orchestration belong in services.
- Fix actual boundary and unsafe-syntax violations without suppressing or weakening the gate.

## Keep this skill sharp

Keep this guide aligned with `scripts/check_architecture.py`, the Make targets, and the local
pre-commit hooks. Document durable contracts in the developer guide.

## Verify after

`make arch-check && make quality-gate`
