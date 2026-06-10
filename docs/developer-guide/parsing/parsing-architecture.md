---
title: "Parsing Architecture"
parent: Parsing
grand_parent: Developer Guide
nav_order: 1
redirect_from:
  - /api/Parsing-Guide/
  - /Parsing-Guide/
---

# Parsing Architecture

## Overview

The RING-5 parsing system transforms raw simulator output files into structured
CSV data consumable by the core analysis engine. It is designed around a
**multi-simulator protocol**: any simulator backend can be plugged in by
implementing a single Python protocol and registering with the central registry.
At present, only the **gem5** backend is implemented.

The architecture is organized into three tiers:

1. **Registry tier** -- `SimulatorRegistry` maps simulator names to metadata
   descriptors and lazy-instantiated parser factories.
2. **Python orchestration tier** -- `Gem5Parser` (the gem5 backend) coordinates
   file discovery, scanning, regex expansion, strategy selection, and worker-pool
   dispatch.
3. **Perl execution tier** -- high-performance Perl scripts perform line-by-line
   regex classification and value extraction against gem5 stat files.

A formal **CSV contract** governs the interchange format between the parsing
layer (Layer A) and the core analysis layer (Layer B), ensuring that every
simulator backend produces identically structured output.

### Key source locations

| Module | Path |
|--------|------|
| Protocol definition | `src/parsing/parser_protocol.py` |
| Registry and metadata | `src/parsing/registry.py` |
| Shared framework | `src/parsing/framework/` (WorkPool, Job, find_stats_files) |
| CSV contract | `src/core/models/csv_contract.py` |
| gem5 backend | `src/parsing/gem5/impl/gem5_parser.py` |
| Strategy protocol | `src/parsing/gem5/impl/strategies/file_parser_strategy.py` |
| Strategy factory | `src/parsing/gem5/impl/strategies/factory.py` |
| gem5-specific model | `src/parsing/gem5/models.py` |

---

## SimulationParser Protocol

The `SimulationParser` protocol (`src/parsing/parser_protocol.py`) defines the
contract that every simulator backend must satisfy. It uses Python structural
typing so that any class providing the required methods is accepted -- no
inheritance hierarchy is needed.

```python
@runtime_checkable
class SimulationParser(Protocol):
    def submit_parse_async(
        self, stats_path: str, stats_pattern: str,
        variables: list[StatConfig], output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
    ) -> ParseBatchResult: ...

    def finalize_parsing(
        self, output_dir: str, results: list[dict[str, Any]],
        strategy_type: str = "simple",
        var_names: list[str] | None = None,
    ) -> str | None: ...

    def submit_scan_async(
        self, stats_path: str, stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> list[Future[list[ScannedVariable]]]: ...

    def aggregate_scan_results(
        self, results: list[list[ScannedVariable]],
    ) -> list[ScannedVariable]: ...
```

### The four methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `submit_parse_async` | Launch parallel file parsing for selected variables | `ParseBatchResult` (batch handle) |
| `finalize_parsing` | Aggregate partial results into a consolidated CSV | Path to the CSV, or `None` |
| `submit_scan_async` | Discover available variables across files asynchronously | List of futures resolving to scanned variables |
| `aggregate_scan_results` | Deduplicate and merge scan results from multiple files | Merged variable list |

The `@runtime_checkable` decorator enables `isinstance()` checks at runtime,
which the registry uses internally for validation.

---

## SimulatorRegistry

The `SimulatorRegistry` class (`src/parsing/registry.py`) is the central lookup
point for all simulator backends. It stores two class-level dictionaries:

- `_registry` -- maps simulator names to `(SimulatorInfo, factory)` tuples.
- `_instances` -- caches lazily created parser objects.

### SimulatorInfo

Each simulator registers a frozen dataclass describing its capabilities:

```python
@dataclass(frozen=True)
class SimulatorInfo:
    name: str                                  # Unique key, e.g. "gem5"
    display_name: str                          # UI label
    description: str = ""
    file_pattern: str = "stats.txt"            # Default glob pattern
    variable_types: list[str]                  # e.g. ["scalar", "vector", ...]
    internal_stats: frozenset[str]             # Stats hidden from UI
    parsing_strategies: list[ParsingStrategy]  # At least one required
```

The `__post_init__` validator enforces that every simulator defines at least one
parsing strategy.

### Registration and auto-discovery

Simulators self-register at module load time. The gem5 backend registers itself
at the bottom of `registry.py`:

```python
SimulatorRegistry.register(GEM5_INFO, _create_gem5_parser)
```

The factory uses a **deferred import** to avoid circular dependencies:

```python
def _create_gem5_parser() -> SimulationParser:
    from src.parsing.gem5.impl.gem5_parser import Gem5Parser
    return Gem5Parser()
```

Importing `src.parsing.registry` is sufficient to make gem5 available. Future
simulator backends follow the same pattern: define a `SimulatorInfo`, write a
factory, and call `register()` at module scope.

### Query API

| Method | Returns |
|--------|---------|
| `get_parser(name)` | Lazily creates and caches a `SimulationParser` |
| `get_info(name)` | `SimulatorInfo` without triggering instantiation |
| `available_simulators()` | Sorted list of registered names |
| `available_simulator_info()` | All `SimulatorInfo` objects, sorted |
| `_reset()` | Clears both dictionaries (testing only) |

Duplicate registration raises `ValueError`. Requesting an unknown simulator
raises `KeyError` with the list of available backends in the message.

---

## FileParserStrategy Protocol

Within the gem5 backend, a second protocol defines how individual files are
processed (`src/parsing/gem5/impl/strategies/file_parser_strategy.py`):

```python
class FileParserStrategy(Protocol):
    def execute(
        self, stats_path: str, stats_pattern: str,
        variables: list[StatConfig],
    ) -> list[dict[str, Any]]: ...

    def get_work_items(
        self, stats_path: str, stats_pattern: str,
        variables: list[StatConfig],
    ) -> Sequence[ParseWork]: ...

    def post_process(
        self, results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...
```

The three-phase workflow is:

1. **`get_work_items`** -- discover files and create `ParseWork` objects for the
   worker pool.
2. **`execute`** -- run the complete synchronous parsing pipeline (discovery,
   extraction, result collection).
3. **`post_process`** -- transform or enrich raw results after extraction. For
   example, the config-aware strategy augments results with `config.ini` data.

Two concrete implementations exist:

| Strategy | Key | Description |
|----------|-----|-------------|
| `SimpleStatsStrategy` | `"simple"` | Parses `stats.txt` only. No external metadata. Fastest option. |
| `ConfigAwareStrategy` | `"config_aware"` | Integrates `config.ini` metadata alongside stats data. |

---

## StrategyFactory

The `StrategyFactory` class (`src/parsing/gem5/impl/strategies/factory.py`)
centralizes strategy instantiation so that callers never need inline imports or
conditional chains:

```python
class StrategyFactory:
    @staticmethod
    def create(strategy_type: str) -> FileParserStrategy:
        if strategy_type == "simple":
            from ...strategies.simple import SimpleStatsStrategy
            return SimpleStatsStrategy()

        if strategy_type == "config_aware":
            from ...strategies.config_aware import ConfigAwareStrategy
            return ConfigAwareStrategy()

        raise ValueError(f"Unknown strategy type: '{strategy_type}'")
```

Both branches use **lazy imports** to keep the factory module lightweight and to
avoid pulling in heavy dependencies at import time.

At parse time, `Gem5Parser.submit_parse_async` resolves the strategy with a
single call:

```python
strategy = StrategyFactory.create(strategy_type)
batch_work = strategy.get_work_items(stats_path, stats_pattern, configs)
```

---

## CSV Contract

The CSV file is the "common language" between Layer A (Parsing) and Layer B
(Core). The contract is defined in `src/core/models/csv_contract.py`.

### Constants

```python
MISSING_VALUE: str = ""       # Empty string for missing values
CSV_ENCODING: str = "utf-8"   # Character encoding
CSV_DIALECT: str = "excel"    # Python csv module dialect
```

### Format rules

1. **Header row is mandatory.** Column names are variable names.
2. **Each row represents one dump interval** (begin/end simpoint pair).
3. **Column names are hierarchical**, dot-separated (e.g., `system.cpu.ipc`).
4. **Values are numeric or string.** Float for statistics, string for
   configuration variables.
5. **Missing values are empty strings** -- not `NaN`, not `null`, not `0`.
6. **No simulator-specific metadata** in the CSV -- only data values.

Simulator-specific column naming conventions (e.g., gem5 vector entries using
`..` separator) are handled by each simulator's parser, not by this contract.

### Validation

`validate_parser_csv(path)` performs structural checks on a CSV file:

| Check | Behavior |
|-------|----------|
| File does not exist | Raises `FileNotFoundError` |
| Empty file or empty header | Raises `ValueError` |
| Duplicate column names | Warning |
| Leading/trailing whitespace in column names | Warning |
| Empty column name | Warning |
| Row column count differs from header | Warning with row number |
| Header only, no data rows | Warning |

The function returns an empty list for valid files and a list of warning strings
for files with structural concerns.

---

## Public API Surface

### Legacy re-exports

`src/parsing/__init__.py` provides backward-compatible aliases:

```python
from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService
from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService
__all__ = ["ParseService", "ScannerService"]
```

Existing code can continue to use:

```python
from src.parsing import ParseService, ScannerService
```

### Registry-based access (recommended)

New code should obtain parsers through the registry:

```python
from src.parsing.registry import SimulatorRegistry

parser = SimulatorRegistry.get_parser("gem5")
futures = parser.submit_scan_async("/path/to/stats")
```

The registry returns a single `Gem5Parser` instance — the gem5 backend that
implements the `SimulationParser` protocol directly, covering parsing, scanning,
and CSV assembly behind one interface. A second backend would register its own
class implementing the same protocol.

### Consumer patterns

| Consumer | Pattern | Receives |
|----------|---------|----------|
| Web controllers | `SimulatorRegistry.get_parser("gem5")` | `SimulationParser` (a `Gem5Parser`) |
| Web UI metadata | `SimulatorRegistry.get_info("gem5")` | `SimulatorInfo` (types, strategies) |
| Tests | `SimulatorRegistry._reset()` then re-register | Clean isolated state |

---

## How ApplicationAPI Integrates with Parsing

The `ApplicationAPI` class (`src/core/application_api.py`) is the single entry
point for the presentation layer. It holds a `SimulationParser` instance,
defaulting to the gem5 backend via the registry:

```python
class ApplicationAPI:
    def __init__(self, ..., parser: SimulationParser | None = None):
        self._parser = parser or SimulatorRegistry.get_parser("gem5")
```

ApplicationAPI wraps each protocol method with additional orchestration logic.
The key parsing-related methods are:

| ApplicationAPI method | Delegates to | Extra logic |
|-----------------------|-------------|-------------|
| `submit_scan_async(path, pattern, limit)` | `_parser.submit_scan_async` | None |
| `finalize_scan(results)` | `_parser.aggregate_scan_results` | None |
| `submit_parse_async(path, pattern, variables, ...)` | `_parser.submit_parse_async` | Converts `ParseVariableConfig` dicts and `ScannedVariableDict` dicts into `StatConfig` / `ScannedVariable` objects |
| `finalize_parsing(output_dir, results, ...)` | `_parser.finalize_parsing` | None |
| `find_stats_files(search_path, pattern)` | `Path.rglob` directly | Path normalization and sanitization |

The `submit_parse_async` wrapper is the most involved. It accepts variables as
either `ParseVariableConfig` dictionaries (from the UI), `ScannedVariable`
objects, or `StatConfig` objects, normalizing them all into `StatConfig` before
delegating. It also detects regex patterns in variable names and sets
`is_regex=True` accordingly, and handles legacy aliasing where a variable's
display name differs from its stat name.

ApplicationAPI also exposes registry facade methods so the web layer never
imports parsing modules directly:

```python
@staticmethod
def available_simulators() -> list[str]:
    return SimulatorRegistry.available_simulators()

@staticmethod
def available_simulator_info() -> list[SimulatorInfo]:
    return SimulatorRegistry.available_simulator_info()

@staticmethod
def get_simulator_info(name: str) -> SimulatorInfo:
    return SimulatorRegistry.get_info(name)
```

This ensures the web layer (Layer C) communicates with the parsing layer
(Layer A) exclusively through the ApplicationAPI boundary, preserving the
clean architecture layering.

---

## See Also

- **Adding a new parser backend** -- `docs/developer-guide/extension-guides/` covers
  how to implement `SimulationParser` for a new simulator and register it.
- **Core models** -- `src/core/models/parsing_models.py` defines `ScannedVariable`,
  `StatConfig`, and `ParseBatchResult`.
- **Shaper pipeline** -- the shaper system consumes the CSV output produced by
  the parsing layer. See `docs/developer-guide/core/` for pipeline documentation.
- **gem5 variable types** -- the `GEM5_INFO` descriptor in `src/parsing/registry.py`
  lists the five supported types (scalar, vector, distribution, histogram,
  configuration) plus the 13 internal stats filtered from the UI.
- **Perl subsystem** -- the line-level regex classification lives in
  `src/parsing/gem5/perl/libs/TypesFormatRegex.pm` and the six type modules
  under `src/parsing/gem5/perl/libs/Scanning/Type/`.
