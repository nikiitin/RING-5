---
name: api-check
description: Gate the ApplicationAPI facade contract — the single Web→Core entry point, its three sub-APIs, and the async parse/scan protocol. Use when verifying API usage, reviewing facade/service changes, or checking that the UI talks to core only through the facade.
---

# API check (the facade contract gate)

UI domain operations go through `src/core/application_api.py::ApplicationAPI`, with one
browser-session-owned instance in `app.py`. Shared typed models and protocols remain importable
by presentation code. This gate checks service/state access and submit/finalize ownership.

## The contract
- **Three sub-APIs**, exposed as properties and composed by `DefaultServicesAPI(state_manager)`
  in `src/core/services/services_impl.py`:
  - `api.managers` → `ManagersAPI` (arithmetic / outlier / reduction / mixer data managers)
  - `api.data_services` → `DataServicesAPI` (CSV pool, paths, variables, portfolio, pattern index)
  - `api.shapers` → `ShapersAPI` (`ShaperFactory` + `PipelineService`, plus current editor metadata via `get_shaper_display_names()`)
- **State** lives behind the facade's `RepositoryStateManager` (single source of truth). Web uses the
  `StateManager` **protocol** via the facade — it must never import `repository_state_manager`
  (enforced by `scripts/check_architecture.py`).
- **Parsing** is reached only through the injected `SimulationParser` (gem5 by default via
  `SimulatorRegistry.get_parser("gem5")`) — never a concrete `src/parsing/gem5/...` import in core/web.
- The parser backend implements the eight methods in `src/parsing/parser_protocol.py`: submit and
  finalize pairs for full parsing, incremental parsing, parser-playground sampling, and scanning.

## Submit/finalize ownership
```python
futures   = api.submit_scan_async(stats_path, pattern, limit=5)
scan      = api.finalize_scan([f.result() for f in futures])
drafts    = [api.draft_from_scanned_variable(v.to_dict()) for v in scan.variables]
```
Scanning supplies evidence and editable drafts. Complete every missing or ambiguous output/source
choice before compilation; each runnable draft needs compatible `params.source_type`. Full native
Distribution frequencies also require caller-declared `minimum`, `maximum`, positive `bucket_size`
and explicit `zero_policy`. A scan supplies neither that grid nor an omission guarantee.
Statistics-only extraction needs no grid. Continue only with the caller-completed `drafts`:

```python
configs   = api.compile_parse_variables(drafts)
batch     = api.submit_parse_async(stats_path, pattern, configs, out_dir, scanned_vars=scan.variables)
output    = api.finalize_parsing(batch, [f.result() for f in batch.futures])
```
- Full finalization requires the exact submitted `ParseBatchResult` and returns `ParsedOutput`.
  `complete=False` permits non-empty partial output while preserving the submitted source plan.
  Public `Session.parse` orchestrates this backend contract; do not add a second parser route.
- Runnable inputs are `StatConfig` values. UI drafts compile through `api.compile_parse_variables`;
  durable job and recipe payloads use `StatConfigCodec` exact snake_case serialization.
- **Always pass `scanned_vars`** when parsing numeric patterns (required explicit concrete
  source records). Every runnable request declares `params.source_type`; `selected_sources` contains
  concrete source names, while numeric coordinates remain in `SourceInstance` metadata.
- `api.cancel_pending_scans()` cancels only futures submitted by that API instance. Pool facades
  retain no batches. The web API is browser-session scoped; public Sessions own separate APIs.

Use `api.close(wait=True)` when a caller needs deterministic background-job shutdown. Browser
cleanup can use the default nonblocking background close; parser work always settles before its
workspace is removed.

## Gate checklist
1. Route UI service calls and repository operations through `api.*`; shared models and protocols
   do not require facade wrappers.
2. New cross-cutting capability added to a service but **not surfaced** on the facade/sub-API the UI
   needs? Surface the operation on `ApplicationAPI` or its existing sub-API. Keep scientific
   algorithms in services; the facade validates boundary inputs and coordinates owned state.
3. Preserve submitted batch context through finalization and supply concrete `scanned_vars`
   for numeric patterns. Do not bypass the backend ownership contract.
4. `import streamlit` / `session_state` sneaking into `src/core/` via the facade? → arch violation.
5. Keep transformation and parsing algorithms in their service/backend owners.

```bash
# quick smells
rg -n 'from src\.core\.(services|state)' src/web/ -g '*.py'  # inspect service access vs. protocols
rg -n 'repository_state_manager' src/web/ -g '*.py'       # no concrete repository imports
```

## Keep this skill sharp
Canon, not history — edit in place when the contract moves:
- The sub-API properties and async signatures above mirror `src/core/application_api.py` and
  `src/core/services/services_impl.py`. If you add/rename a facade method, update this list.
- New contract bug caught in review? Add it to the gate checklist; document durable contracts in the developer guide.
- Related: `parser-check`, `architecture-check`.

## Verify after
`make arch-check && ./python_venv/bin/mypy src/core/application_api.py && ./python_venv/bin/pytest tests/integration -k "api or facade" -q`
