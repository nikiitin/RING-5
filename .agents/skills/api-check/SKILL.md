---
name: api-check
description: Gate the ApplicationAPI facade contract — the single Web→Core entry point, its three sub-APIs, and the async parse/scan protocol. Use when verifying API usage, reviewing facade/service changes, or checking that the UI talks to core only through the facade.
---

# API check (the facade contract gate)

The UI's **only** doorway into core is `src/core/application_api.py::ApplicationAPI` (one
session-owned instance in `app.py`). There is no separate web facade module. This gate confirms
callers use the facade correctly and the contract holds.

## The contract
- **Three sub-APIs**, exposed as properties and composed by `DefaultServicesAPI(state_manager)`
  in `src/core/services/services_impl.py`:
  - `api.managers` → `ManagersAPI` (arithmetic / outlier / reduction / mixer data managers)
  - `api.data_services` → `DataServicesAPI` (CSV pool, paths, variables, portfolio, pattern index)
  - `api.shapers` → `ShapersAPI` (`ShaperFactory` + `PipelineService`)
- **State** lives behind the facade's `RepositoryStateManager` (single source of truth). Web uses the
  `StateManager` **protocol** via the facade — it must never import `repository_state_manager`
  (arch-check #8).
- **Parsing** is reached only through the injected `SimulationParser` (gem5 by default via
  `SimulatorRegistry.get_parser("gem5")`) — never a concrete `src/parsing/gem5/...` import in core/web.
- The parser backend implements exactly 4 protocol methods (`src/parsing/parser_protocol.py`):
  `submit_parse_async`, `finalize_parsing`, `submit_scan_async`, `aggregate_scan_results`.

## Async parse/scan — the one correct shape (never wrap synchronously)
```python
futures   = api.submit_scan_async(stats_path, pattern, limit=5)
variables = api.finalize_scan([f.result() for f in futures])
batch     = api.submit_parse_async(stats_path, pattern, variables, out_dir, scanned_vars=variables)
csv_path  = api.finalize_parsing(out_dir, [f.result() for f in batch.futures])
```
- **Always pass `scanned_vars`** when parsing regex/pattern variables (needed to reconstruct
  concrete names). Omitting it is the most common contract bug.
- Long-running scans: release with `api.cancel_pending_scans()` — instance-scoped (cancels only
  the futures THAT instance submitted; pool facades hold no future references). The web app's
  single cached instance makes this process-wide there; ring5 Sessions are truly per-session.

## Gate checklist
1. Does new UI code reach into `src/core/...` directly instead of via `api.*`? → route through the facade.
2. New cross-cutting capability added to a service but **not surfaced** on the facade/sub-API the UI
   needs? → add the delegating property/method on `ApplicationAPI` (keep it a thin delegator, no logic).
3. Any sync wrapper around parse/scan, or a call missing `scanned_vars`? → fix.
4. `import streamlit` / `session_state` sneaking into `src/core/` via the facade? → arch violation.
5. Facade method doing real work instead of delegating? → push logic down into the service.

```bash
# quick smells
grep -rn "from src.core.services\|from src.core.state" src/web/ --include=*.py | grep -v application_api
grep -rn "repository_state_manager" src/web/ --include=*.py        # must be empty (arch-check #8)
```

## Keep this skill sharp
Canon, not history — edit in place when the contract moves:
- The sub-API properties and async signatures above mirror `src/core/application_api.py` and
  `src/core/services/services_impl.py`. If you add/rename a facade method, update this list.
- New contract bug caught in review? Add it to the gate checklist; durable facts → a memory.
- Related: `parser-check`, `architecture-check`.

## Verify after
`make arch-check && ./python_venv/bin/mypy src/core/application_api.py && ./python_venv/bin/pytest tests/integration -k "api or facade" -q`
