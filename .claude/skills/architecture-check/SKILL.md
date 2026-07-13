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
make arch-check        # the 8 boundary greps below — exits non-zero on any violation
make quality-gate      # arch + mypy + black + flake8 + security, one summary (CI-equivalent)
```
`make arch-check` runs exactly these 8 checks (each must return empty):
1. **no Streamlit in core** — `import streamlit`/`from streamlit` under `src/core/`
2. **no session_state in core** — `session_state` under `src/core/`
3. **no `inplace=True`** — anywhere under `src/`
4. **no bare `except:`** — anywhere under `src/`
5. **no `eval(`/`exec(`** — under `src/` (excluding tests)
6. **models → services** — `src/core/models/` must not import `src.core.services` (models depend on nobody)
7. **parsing → core.services** — `src/parsing/` (Layer A) must not import `src.core.services` (Layer B)
8. **web → concrete state** — `src/web/` must not name `repository_state_manager` (use the
   `StateManager` protocol via the `ApplicationAPI` facade)

The same 8 live as local hooks in `.pre-commit-config.yaml` (ids `no-streamlit-in-core` …
`no-web-to-state-manager`). `make quality-gate` folds a subset into Gate 1 plus mypy/black/flake8/bandit.

## The 7 hard rules (CLAUDE.md §1)
1. **Git is human-only** — never run git mutations.
2. No Streamlit / `session_state` in `src/core/` or `src/parsing/` (UI state lives only in `src/web/`).
3. No `inplace=True` on DataFrames in `src/` — return new objects (`.copy()` first).
4. No bare `except:` — catch specific exceptions; raise/log, never silently swallow.
5. No `eval()`/`exec()` in `src/`; no `pickle.load` on untrusted data.
6. **Never fabricate data** — a failed gem5 regex must raise/log, never guess a value.
7. **Async parse/scan only** — never add a synchronous wrapper.

Rules 6 and 7 are **not greppable** — verify them by reading the touched code, not just by a green
`make arch-check`. The fabrication rule is the highest-stakes one (see [[ring5-arch-audit-2026-06]]).

## What "fix at the source" means
- Web needs core data? Go through `ApplicationAPI` (`api.managers`/`api.data_services`/`api.shapers`),
  not a direct `src/core` reach-around. See the `api-check` skill.
- Core needs parsing? Through the `SimulationParser` protocol + `SimulatorRegistry`, never a
  `src/parsing/gem5/...` concrete import.
- A model needs logic? The logic belongs in a service; the model stays pure data.
- Tempted to add `# noqa`/`inplace=True`/a bare except to pass? That's the violation, not the fix.

## Keep this skill sharp
This skill is canon, not history — edit it in place (present tense, no changelog) when it drifts:
- The 8 checks above mirror `arch-check:` in the `Makefile` and the local hooks in
  `.pre-commit-config.yaml`. If those change, re-read them and update this list — they are the
  source of truth, this is a summary.
- When the gate catches a failure mode worth remembering, add it here; if it's a durable project
  fact, also write a memory under `~/.claude/.../memory/`.

## Verify after
`make arch-check && make quality-gate`
