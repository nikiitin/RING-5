---
name: architecture-check
description: Gate the RING-5 architecture — the 7 hard rules and the strict 3-layer dependency direction (Web → Core ← Parsing). Use before merging, after any structural/refactor change, or when asked to "check architecture", "run the arch gate", or verify layer boundaries.
---

# Architecture check (the boundary gate)

RING-5 has **one** allowed dependency direction — `Web → Core ← Parsing` — and 7 hard rules
enforced by pre-commit, CI, and `make arch-check`. This skill is the gate: run it, read every
violation, fix at the source (never weaken the check).

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
- Web needs core data? Go through `ApplicationAPI` (`api.managers`/`api.data_services`/`api.shapers`),
  not a direct `src/core` reach-around. See the `api-check` skill.
- Core needs parsing? Through the `SimulationParser` protocol + `SimulatorRegistry`, never a
  `src/parsing/gem5/...` concrete import.
- A model needs logic? The logic belongs in a service; the model stays pure data.
- Tempted to add `# noqa`/`inplace=True`/a bare except to pass? That's the violation, not the fix.

## Keep this skill sharp

Keep this guide aligned with `scripts/check_architecture.py`, the Make targets, and the local
pre-commit hooks. Document durable contracts in the developer guide.

## Verify after

`make arch-check && make quality-gate`
