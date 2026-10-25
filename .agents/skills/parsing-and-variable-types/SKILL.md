---
name: parsing-and-variable-types
description: Work on RING-5's gem5 parsing/scanning subsystem — the async scan/parse API, adding a new gem5 stat (variable) type, the Perl parsing layer, and debugging async parsing/worker-pool issues. Use for any parsing, scanning, stats.txt, Perl, or worker-pool task.
---

# Parsing & variable types (gem5, Layer A)

Parsing is async + multi-simulator. Python orchestrates `concurrent.futures` over singleton pools;
the heavy lifting is a **persistent Perl worker pool** (≈54× faster than per-variable subprocesses).
Layout: `src/parsing/` (protocol, registry, services) and `src/parsing/gem5/` (impl, types, perl).

## The async API (never add sync wrappers)
```python
# Scan: discover variables
futures   = api.submit_scan_async(stats_path, pattern="stats.txt", limit=5)
scan      = api.finalize_scan([f.result() for f in futures])
configs   = api.compile_parse_variables(
    [api.draft_from_scanned_variable(v.to_dict()) for v in scan.variables]
)

# Parse: extract selected variables → CSV
batch    = api.submit_parse_async(stats_path, pattern, configs, out_dir,
                                  strategy_type="simple", scanned_vars=scan.variables)
csv_path = api.finalize_parsing(out_dir, [f.result() for f in batch.futures])
```
- **Always pass `scanned_vars`** when parsing regex/pattern variables — it's needed to bind
  explicit `SourceInstance(source_name, indices)` records. Never reconstruct names from indices.
- Every runnable config requires `params.source_type`; manual producers declare the raw kind
  independently of the output representation. `params.selected_sources` contains concrete names.
  Submission resolves selections once into private accumulator specifications and direct routes.
- Strategies: `simple` (stats.txt only) and `config_aware` (also reads `config.ini`), via
  `StrategyFactory` in `gem5/impl/strategies/`.
- Pattern aggregation (`gem5/impl/scanning/pattern_aggregator.py`) collapses per-core repeats into
  one numeric pattern with explicit `instances` (~94% reduction). `internal_stats` (see registry `GEM5_INFO`)
  are excluded from selection.

## Add a new gem5 variable (stat) type
Stat types self-register; there are two halves — **Python** (model + reduction) and **Perl**
(line classification). Existing types: `scalar`, `vector`, `distribution`, `histogram`,
`configuration` (in `src/parsing/gem5/types/`).

1. **Python type** — `src/parsing/gem5/types/<name>.py`:
   ```python
   from src.parsing.gem5.types.base import StatType, register_type

   @register_type("mytype")
   class MyType(StatType[list[float], float]):
       # Declare slots and owned storage. Implement content as a defensive snapshot,
       # _add_observation(value), _balance() -> padding_count, and _reduce() -> result.
       # Inherit the public lifecycle methods; they enforce collection → balance → reduce.
       ...
   ```
   `add_observation(float | str | Mapping[str, float])` accepts one typed source/dump
   observation. Numeric strings, booleans and list-valued frames are rejected; convert
   wire text at the worker boundary. Collection closes after balancing. The public
   balance/reduce methods are idempotent, and reduced content is inaccessible until both
   succeed. Frame-based types can inherit `FrameStatType` and supply their entry schema
   and frame validation; one frame list remains the authoritative store.

   Declare `required_params` for OFT capability discovery; constructor and codec validation
   enforce executable options. Import it so the decorator runs (add to `types/__init__.py`). `TypeMapper.create_stat(resolved_spec)` /
   `StatTypeRegistry.create("mytype", ...)` then dispatch by name. (There is **no**
   `TYPE_TO_SCRIPT`/`TYPE_TO_COLUMNS` dict — registration is purely the decorator.)

2. **Perl classification** — add/extend a regex module under
   `src/parsing/gem5/perl/libs/Scanning/Type/<Name>.pm`, then wire it into the single
   `TypesFormatRegex::classifyLine` classifier. It returns an ordered record list; each measurement
   retains its source entry, scan label, and value. The scanner aggregates those records and the
   persistent worker serializes them. Preserve dump events and deferred geometry; validate oneline
   geometry while preserving gem5's zero-suppressed bounds. Test both consumers with the same raw
   fixtures.

3. **Register the type string** in `SimulatorRegistry` `GEM5_INFO.variable_types`
   (`src/parsing/registry.py`) so the UI offers it.

4. **Tests:** unit-test the Perl module directly (feed sample lines), then integration-test through
   `ApplicationAPI.submit_parse_async`. Use `tests/helpers/gem5_fixtures` and real data via
   `make test-data`.

## Debugging async parsing
- **Hangs / timeouts:** check `gem5/impl/strategies/perl_worker_pool.py` (worker health check skips
  if `last_used < 60s`; `is_busy` uses GIL atomicity). Pools register `atexit` cleanup and have
  `shutdown()` — call `ApplicationAPI.cancel_pending_scans()` to release THAT instance's scan
  futures/memory (handle-based; pool facades keep none; the web app shares one cached instance).
- **Missing/empty columns in CSV:** `construct_final_csv` unions headers across files; a variable
  absent in the first file is fine. If a header is *permanently* short, suspect header being built
  from a sample file rather than the variable config.
- **Wrong values / type mismatch:** Perl may report `Vector` where the user expected
  `Distribution`/`Histogram`; explicit source/output routing is handled in `gem5/impl/strategies/gem5_parse_work.py`.
- **Never fabricate:** on regex non-match the parser logs/raises — keep it that way; don't default to 0.
- Worker keys are validated against leading-dash flag injection before reaching the pool — preserve that.

## Verify after
`make arch-check && ./python_venv/bin/mypy src/ && ./python_venv/bin/pytest tests/unit/ -k "parse or scan or gem5" -q`
(plus `tests/integration/test_real_gem5_data.py` when touching real parsing).
