---
title: "Adding a New Simulator Parser"
parent: Development
grand_parent: AI Knowledge Base
nav_order: 1
---

# Adding a New Simulator Parser

## Overview

- Pattern: Registry + Protocol
- Protocol: `SimulationParser` (`src/parsing/parser_protocol.py`)
- Registry: `SimulatorRegistry` (`src/parsing/registry.py`)
- Metadata: `SimulatorInfo` frozen dataclass (`src/parsing/registry.py`)
- Reference implementation: gem5 (`src/parsing/gem5/impl/gem5_parser.py`)

## Protocol Contract

```python
# src/parsing/parser_protocol.py

@runtime_checkable
class SimulationParser(Protocol):

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
    ) -> ParseBatchResult: ...

    def finalize_parsing(
        self,
        output_dir: str,
        results: list[dict[str, Any]],
        strategy_type: str = "simple",
        var_names: list[str] | None = None,
    ) -> str | None: ...

    def submit_scan_async(
        self,
        stats_path: str,
        stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> list[Future[list[ScannedVariable]]]: ...

    def aggregate_scan_results(
        self,
        results: list[list[ScannedVariable]],
    ) -> list[ScannedVariable]: ...
```

| Method | Purpose |
|--------|---------|
| `submit_parse_async` | Submit async parsing job over simulation output files |
| `finalize_parsing` | Post-process results into canonical CSV format |
| `submit_scan_async` | Discover potential variables across simulation files |
| `aggregate_scan_results` | Deduplicate and merge scan results from workers |

## Steps

### 1. Create the module directory

```
src/parsing/my_simulator/
    __init__.py
    parser.py
```

### 2. Define SimulatorInfo metadata

```python
# src/parsing/my_simulator/__init__.py

from src.parsing.registry import SimulatorInfo, ParsingStrategy

MY_SIM_INFO = SimulatorInfo(
    name="my_simulator",                          # unique lowercase id
    display_name="My Simulator",                  # UI label
    description="Custom architecture simulator",  # tooltip text
    file_pattern="results.log",                   # default filename pattern
    variable_types=["scalar", "vector"],           # supported variable types
    internal_stats=frozenset({"__internal_total"}),# stats excluded from UI
    parsing_strategies=[
        ParsingStrategy(
            name="default",
            display_name="Default Parser",
            description="Standard results.log parsing",
        ),
    ],
)
```

- `SimulatorInfo` is frozen (immutable).
- At least one `ParsingStrategy` is required (`__post_init__` enforces this).
- `name` must be unique across all registered simulators.

### 3. Implement the parser class

```python
# src/parsing/my_simulator/parser.py

from concurrent.futures import Future
from typing import Any

from src.core.models import ParseBatchResult, ScannedVariable, StatConfig


class MySimulatorParser:
    """Satisfies SimulationParser protocol via structural typing."""

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "default",
        scanned_vars: list[ScannedVariable] | None = None,
    ) -> ParseBatchResult:
        # 1. Walk stats_path for files matching stats_pattern
        # 2. Parse each file extracting requested variables
        # 3. Return ParseBatchResult with futures and metadata
        ...

    def finalize_parsing(
        self,
        output_dir: str,
        results: list[dict[str, Any]],
        strategy_type: str = "default",
        var_names: list[str] | None = None,
    ) -> str | None:
        # 1. Aggregate per-file results into a single DataFrame
        # 2. Write CSV to output_dir
        # 3. Return path to CSV or None on failure
        ...

    def submit_scan_async(
        self,
        stats_path: str,
        stats_pattern: str = "results.log",
        limit: int = 5,
    ) -> list[Future[list[ScannedVariable]]]:
        # 1. Quick scan of up to `limit` files
        # 2. Return futures that resolve to variable lists
        ...

    def aggregate_scan_results(
        self,
        results: list[list[ScannedVariable]],
    ) -> list[ScannedVariable]:
        # 1. Flatten and deduplicate variables
        # 2. Return merged list
        ...
```

- No need to inherit from `SimulationParser`. Protocol uses structural typing.
- Signature must match exactly (parameter names, types, defaults).

### 4. Register with SimulatorRegistry

```python
# src/parsing/my_simulator/__init__.py  (append after MY_SIM_INFO)

from src.parsing.registry import SimulatorRegistry


def _create_my_simulator_parser():
    # Lazy import avoids circular dependencies and reduces startup time
    from src.parsing.my_simulator.parser import MySimulatorParser
    return MySimulatorParser()


SimulatorRegistry.register(MY_SIM_INFO, _create_my_simulator_parser)
```

### 5. Ensure module is imported at startup

- Import `src.parsing.my_simulator` in the application entry point.
- Registration happens at module load time (like gem5 in `src/parsing/registry.py`).

### 6. Verify registration

```python
from src.parsing.registry import SimulatorRegistry

assert "my_simulator" in SimulatorRegistry.available_simulators()
parser = SimulatorRegistry.get_parser("my_simulator")
assert isinstance(parser, SimulationParser)  # runtime_checkable
```

## Registry API Reference

| Method | Returns |
|--------|---------|
| `SimulatorRegistry.register(info, factory)` | None (raises ValueError on duplicate) |
| `SimulatorRegistry.get_parser(name)` | `SimulationParser` (lazy-creates and caches) |
| `SimulatorRegistry.get_info(name)` | `SimulatorInfo` |
| `SimulatorRegistry.available_simulators()` | `list[str]` (sorted) |
| `SimulatorRegistry._reset()` | None (testing only) |

## Conventions

1. Simulator names: lowercase (`gem5`, `my_simulator`)
2. Factory functions: use lazy imports to avoid circular dependencies
3. Parser instances: cached after first creation (singleton per name)
4. Layer rule: parsing layer must NOT import from `src/web/`
