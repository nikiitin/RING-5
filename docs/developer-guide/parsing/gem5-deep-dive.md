---
title: "gem5 Parsing Implementation Deep Dive"
parent: Parsing
grand_parent: Developer Guide
nav_order: 2
---

# gem5 Parsing Implementation Deep Dive

This guide walks through the gem5 parsing subsystem in RING-5 Unified Engine v2,
covering every layer from high-level orchestration down to per-line regex
dispatch so that developers can understand, debug, and extend the pipeline.

---

## 1. Overview

### 1.1 The gem5 stats.txt Format

The gem5 architectural simulator writes statistics to `stats.txt` files
containing hierarchical, dot-separated stat names in several data shapes:

```
system.cpu.ipc                        1.523                     # scalar
system.cpu.op_class::IntAlu           1234 50.00% 100.00%       # vector entry
system.l2.miss_latency::128           45 12.50% 87.50%          # distribution bucket
system.mem.bw_read::0-1024            100 25.00% 25.00%         # histogram range
system.cpu.type=DerivO3CPU                                      # configuration
```

A single run may dump stats multiple times (simpoints), separated by
`---------- Begin/End Simulation Statistics ----------` dividers. Large
experiments produce hundreds of files, each containing thousands of variables
across 16+ CPU cores.

### 1.2 Three-Tier Architecture

| Tier | Location | Role |
|------|----------|------|
| **Python orchestration** | `src/parsing/gem5/impl/` | File discovery, regex expansion, strategy selection, work dispatch, CSV aggregation |
| **Perl execution** | `src/parsing/gem5/perl/` | Line-by-line regex classification and value extraction |
| **Type system** | `src/parsing/gem5/types/` | Self-registering Python types that validate, store, balance, and reduce parsed values |

Two distinct phases provide a clean separation of concerns:
1. **Scanning** -- discover what variables exist (fast, unfiltered).
2. **Parsing** -- extract specific variable values the user selected (filtered, parallel).

---

## 2. Gem5Scanner -- File Discovery, Stat Scanning, Pattern Aggregation

**Source:** `src/parsing/gem5/impl/gem5_scanner.py`

### 2.1 File Discovery with Early Stop

`submit_scan_async()` normalises the input path, sanitises the glob pattern,
and uses `Path.rglob()` with an early-stop optimisation -- when `limit > 0`,
the generator is consumed only until enough files are collected:

```python
if limit > 0:
    files_unsorted: list[Path] = []
    for f in search_path.rglob(safe_pattern):
        files_unsorted.append(f)
        if len(files_unsorted) >= limit:
            break
```

Found files become `Gem5ScanWork` items submitted to `ScanWorkPool`, which
dispatches each as a threaded job via the unified `WorkPool`.

### 2.2 Scan Result Aggregation

`aggregate_scan_results()` performs a two-phase merge. **Phase 1** merges
variables across files: vector/histogram entries are unioned; distribution
`minimum`/`maximum` ranges are widened; scalars use first-seen. **Phase 2**
runs `PatternAggregator.aggregate_patterns()` to consolidate repeated numeric
patterns (see Section 7).

### 2.3 Perl Scanning

Each `Gem5ScanWork` delegates to `Gem5StatsScanner`, which runs
`statsScanner.pl`. The Perl script classifies every non-empty, non-divider
line via `classifyLine()`, maintains a type-evolution hash, and outputs JSON:

```json
[
  {"name": "system.cpu.ipc", "type": "scalar"},
  {"name": "system.cpu.op_class", "type": "vector", "entries": ["IntAlu", "MemRead"]},
  {"name": "system.l2.miss_latency", "type": "distribution",
   "entries": ["128", "256"], "minimum": 128, "maximum": 256}
]
```

---

## 3. Gem5Parser -- Variable Parsing and Batch Processing

**Source:** `src/parsing/gem5/impl/gem5_parser.py`

### 3.1 The Four-Step Pipeline

`submit_parse_async()` orchestrates:

1. **Regex expansion.** For each `StatConfig` with `is_regex=True`, the parser
   compiles the pattern and matches against scanned variables. With
   `keep_indices=True`, it expands into individual concrete configs via
   `PatternIndexService.reconstruct_concrete_name()`. With
   `keep_indices=False`, matched names are stored in `params["parsed_ids"]`.
   A warning fires if expansion exceeds 50 variables.

2. **Strategy resolution.** `StrategyFactory.create(strategy_type)` returns
   a `SimpleStatsStrategy` or `ConfigAwareStrategy`.

3. **Work item generation.** The strategy discovers files and builds per-file
   `Gem5ParseWork` objects, each receiving a deep-copied variable map for
   thread safety.

4. **Pool dispatch.** Work items are submitted to `ParseWorkPool` for parallel
   execution.

### 3.2 CSV Aggregation

`finalize_parsing()` delegates post-processing to the strategy and then calls
`construct_final_csv()`. Headers are built as the **union** of all results so
variables missing from some files still appear. Complex types expand into
`varName..entryKey` columns. Missing values are `"NaN"`.

---

## 4. Gem5ParserAPI -- High-Level API with Configuration

**Source:** `src/parsing/gem5/impl/gem5_parser_api.py`

`Gem5ParserAPI` is the object returned by
`SimulatorRegistry.get_parser("gem5")`. It implements the `SimulationParser`
protocol as a thin facade delegating to the two service classes:

| Method | Delegates to | Phase |
|--------|-------------|-------|
| `submit_scan_async` | `Gem5Scanner` | Scanning |
| `aggregate_scan_results` | `Gem5Scanner` | Scanning |
| `submit_parse_async` | `Gem5Parser` | Parsing |
| `finalize_parsing` | `Gem5Parser` | Parsing |

This keeps scanning and parsing logic in separate, focused classes while giving
consumers a single entry point. Typical usage:

```python
api = Gem5ParserAPI()
futures = api.submit_scan_async("/path/to/stats")
results = [f.result() for f in futures]
variables = api.aggregate_scan_results(results)
```

---

## 5. Stat Type System -- Five Types

**Source:** `src/parsing/gem5/types/`

### 5.1 Type Overview

| Type | Class | Content shape | Reduction |
|------|-------|---------------|-----------|
| `scalar` | `Scalar` | `list[float]` | Arithmetic mean across simpoints |
| `vector` | `Vector` | `dict[str, list[float]]` | Per-entry arithmetic mean |
| `distribution` | `Distribution` | `dict[str, list[float]]` | Per-bucket arithmetic mean |
| `histogram` | `Histogram` | `dict[str, list[float]]` | Per-bin arithmetic mean |
| `configuration` | `Configuration` | `list[str]` | First non-empty value |

### 5.2 Safety Invariants

`StatType` (base class) enforces strict access discipline via custom
`__setattr__` and `__getattribute__` overrides:

- Setting arbitrary attributes raises `AttributeError`.
- Accessing `reduced_content` before calling **both** `balance_content()` and
  `reduce_duplicates()` raises `AttributeError`.

### 5.3 Balance-and-Reduce Lifecycle

Every `StatType` follows a mandatory three-step lifecycle:

1. **Content assignment** -- `stat.content = value` (once per simpoint).
2. **`balance_content()`** -- pads to exactly `repeat` entries (zeros), or
   raises `RuntimeError` if there are too many.
3. **`reduce_duplicates()`** -- computes the final value (typically arithmetic
   mean) and stores it in `_reduced_content`.

---

## 6. StatTypeRegistry -- Self-Registering Type Discrimination

**Source:** `src/parsing/gem5/types/base.py`

### 6.1 Decorator-Based Registration

Each type module registers itself at import time via:

```python
@register_type("scalar")
class Scalar(StatType): ...
```

`register_type` is an alias for `StatTypeRegistry.register()`, which stores
the class in a class-level `_types` dict keyed by type name.

### 6.2 Creation and Lookup

```python
scalar = StatTypeRegistry.create("scalar", repeat=1)
vector = StatTypeRegistry.create("vector", repeat=1, entries=["IntAlu", "MemRead"])
```

Unknown types raise `ValueError` listing available options.

### 6.3 Import-Time Triggering

The `src/parsing/gem5/types/__init__.py` imports all five type modules to force
registration. Simply importing the package populates the registry -- no manual
wiring required.

### 6.4 TypeMapper

`TypeMapper` (`src/parsing/gem5/types/type_mapper.py`) bridges external type
names from Perl/Scanner output to the registry. It normalises strings to
lowercase and routes `StatConfig` objects to `StatTypeRegistry.create()`,
mapping type-specific parameters (`entries`, `minimum`, `maximum`, `bins`,
`statistics`, `onEmpty`).

---

## 7. Pattern Aggregation -- 94% Variable Count Reduction

**Source:** `src/parsing/gem5/impl/scanning/pattern_aggregator.py`

Multi-core gem5 simulations emit identical stats per core (e.g., `system.cpu0`
through `system.cpu15`). Without aggregation, a 16-core run with 1000 base
stats would present 16,000 variables to the user.

### 7.1 Three-Step Algorithm

1. **Extract signature.** `_extract_pattern()` matches `[a-zA-Z_]+(\d+)`
   sequences and replaces numeric parts with `{}` placeholders.
   `system.cpu0.ipc` becomes signature `system.cpu{}.ipc`, ID `"0"`.

2. **Group by signature.** Variables sharing a signature are grouped.
   Single-instance groups are kept unchanged.

3. **Create pattern variable.** Multi-instance groups become one
   `Gem5ScannedVariable` with `name` set to the regex (e.g.,
   `system.cpu\d+.ipc`), `entries` as sorted numeric IDs, and
   `pattern_indices` as the full original names for later expansion.

### 7.2 Type Promotion

When all grouped instances are scalars, the pattern variable becomes a `vector`
whose entries are the numeric IDs. Complex types (vector, distribution,
histogram) preserve their original type and carry both `pattern_indices` and
the union of their sub-entries.

### 7.3 Reduction Ratio

For a 16-core system: 16 individual variables per stat become 1 pattern
variable. With multi-level hierarchy (`l0_cntrl0..15` + `l1_cntrl0..15`),
the effective reduction reaches approximately 94%.

---

## 8. PerlWorkerPool -- 54x Speedup via Persistent Processes

**Source:** `src/parsing/gem5/impl/strategies/perl_worker_pool.py`

Spawning a Perl interpreter per file costs 30-50 ms startup. The
`PerlWorkerPool` eliminates this by maintaining persistent
`fileParserServer.pl` subprocesses accepting commands over stdin/stdout.

### 8.1 Architecture

```
PerlWorkerPool (singleton, 4 workers default)
  +-- PerlWorker[0..3] --> subprocess(perl fileParserServer.pl)
  +-- health_monitor_thread (30s interval, PING/PONG checks)
  +-- worker_queue (thread-safe checkout/return)
```

### 8.2 Communication Protocol

| Direction | Message | Meaning |
|-----------|---------|---------|
| Server -> Client | `READY` | Initialisation complete |
| Client -> Server | `PARSE path\|\|var1\|\|var2\n` | Parse request |
| Server -> Client | `type/name::entry/value` | Parsed output (per line) |
| Server -> Client | `END_PARSE` | End-of-output marker |
| Client -> Server | `PING` / Server `PONG` | Health check |
| Client -> Server | `SHUTDOWN` | Graceful termination |

### 8.3 Health Monitoring and Recovery

A background thread checks idle workers every 30 seconds via PING/PONG.
Recently-used workers (within 60 s) and busy workers are skipped to avoid
TOCTOU races. Unhealthy workers are restarted in-place. A circuit-breaker in
`parse_file()` fails fast when all workers are down.

### 8.4 Performance

| Metric | Subprocess | Worker pool | Speedup |
|--------|-----------|-------------|---------|
| Per-file latency | 30-50 ms | < 1 ms | ~54x |
| 20-file batch | ~0.5 s | ~0.01 s | ~50x |

### 8.5 Queue-Based I/O

Each `PerlWorker` runs one persistent reader thread that drains stdout into a
`queue.Queue`. `_read_line_with_timeout()` pulls from this queue, preventing
thread-per-readline accumulation under load.

---

## 9. WorkPool -- Process + Thread Executor Management

**Source:** `src/parsing/gem5/impl/pool/work_pool.py`

### 9.1 Unified Singleton

`WorkPool` manages a lazily-created `ProcessPoolExecutor` (CPU-bound, `N-1`
workers where `N = cpu_count`) and `ThreadPoolExecutor` (I/O-bound, `2N`
workers). Callers pick the executor via the `use_threads` parameter on
`submit()`.

### 9.2 Facade Pools

| Facade | Submits | Returns | Executor |
|--------|---------|---------|----------|
| `ScanWorkPool` | `ScanWork` items | `Future[list[ScannedVariable]]` | Thread pool |
| `ParseWorkPool` | `ParseWork` items | `Future[ParsedVarsDict]` | Thread pool |

Both are singletons with `get_instance()` / `reset()` class methods.  They
auto-calculate chunk sizes and clear stale future references on each batch.

### 9.3 Lifecycle

An `atexit` handler shuts down both executors when the interpreter exits,
ensuring subprocess resources are released.

---

## 10. Parsing Strategies -- SimpleStatsStrategy vs ConfigAwareStrategy

**Source:** `src/parsing/gem5/impl/strategies/`

### 10.1 FileParserStrategy Protocol

```python
class FileParserStrategy(Protocol):
    def get_work_items(self, stats_path, stats_pattern, variables) -> Sequence[ParseWork]: ...
    def execute(self, stats_path, stats_pattern, variables) -> list[dict]: ...
    def post_process(self, results) -> list[dict]: ...
```

### 10.2 SimpleStatsStrategy (default)

Discovers files via `rglob`, maps variables to `StatType` objects through
`TypeMapper.create_stat()`, deep-copies the variable map per file, and wraps
each in a `Gem5ParseWork`. Its `post_process()` is a pass-through. When a
`StatConfig` carries `parsed_ids` from regex expansion, the strategy sets
`repeat = len(parsed_ids)` and creates shallow-copy aliases so values from all
matching concrete variables flow into one `StatType` for arithmetic-mean
reduction (spatial aggregation across cores).

### 10.3 ConfigAwareStrategy

Extends `SimpleStatsStrategy` by overriding `post_process()`. It locates
`config.ini` next to each stats file, parses it with `configparser`, and
attaches the result:

```python
config_path = Path(sim_result["sim_path"]).parent / "config.ini"
if config_path.exists():
    sim_result["config"] = self._parse_config(config_path)
```

Downstream consumers can then access simulation parameters (clock frequency,
cache sizes, CPU type) alongside statistical data.

### 10.4 Gem5ParseWork -- The Per-File Worker

The callable executed in the thread pool. It: (1) sends a `PARSE` command to
a `PerlWorker` from the `PerlWorkerPool`; (2) routes each `type/varID/value`
output line -- scalars and configurations get direct content assignment, entry
types (vector/distribution/histogram) are buffered and applied in bulk,
summaries route to parent entry buffers; (3) validates all variables and
returns the populated dict.

---

## 11. See Also

| Topic | Location |
|-------|----------|
| `SimulatorRegistry` and `SimulationParser` protocol | `src/parsing/registry.py`, `src/parsing/parser_protocol.py` |
| CSV contract and validation | `src/core/models/csv_contract.py` |
| Perl regex building blocks (7 shared patterns) | `src/parsing/gem5/perl/libs/Scanning/RegexUtils.pm` |
| Perl type modules (Scalar, Vector, Distribution, Histogram, Configuration, Summary) | `src/parsing/gem5/perl/libs/Scanning/Type/` |
| Master Perl dispatch (`classifyLine`, `parseAndPrintLineWithFormat`) | `src/parsing/gem5/perl/libs/TypesFormatRegex.pm` |
| `PatternIndexService` (concrete name reconstruction) | `src/core/services/data_services/pattern_index_service.py` |
| `Gem5ScannedVariable` model (min/max metadata) | `src/parsing/gem5/models.py` |
| Shaper pipeline (consumes parsed CSV) | `src/core/services/data_services/shaper/` |
| Web controllers (invoke scanning/parsing) | `src/web/controllers/` |
