# Adding a New Simulator Parser

This guide walks through every step required to add a new simulator backend
to RING-5 Unified Engine v2. By the end you will have a fully registered
parser that the UI discovers automatically.

## Overview

You need a new parser when RING-5 must ingest output files from a simulator
that is not yet supported (currently only **gem5** is built-in). The parsing
subsystem is designed around two complementary patterns:

- **`SimulationParser` Protocol** (`src/parsing/parser_protocol.py`) --
  a `@runtime_checkable` structural contract that every backend must satisfy.
- **`SimulatorRegistry`** (`src/parsing/registry.py`) -- a class-level
  registry that maps a `SimulatorInfo` metadata descriptor and a lazy factory
  function to a unique simulator name.

Because the protocol uses structural (duck) typing, your implementation class
does **not** need to inherit from `SimulationParser`. It only needs to expose
the four required methods with compatible signatures.

---

## Step 1 -- Create the Simulator Package

Create a new package under `src/parsing/` for your simulator. The recommended
layout mirrors the existing gem5 package:

```
src/parsing/sniper/
    __init__.py          # SimulatorInfo descriptor + registration
    models.py            # Simulator-specific models (optional)
    impl/
        __init__.py
        sniper_parser_api.py   # Protocol facade
        sniper_parser.py       # Parsing orchestration
        sniper_scanner.py      # Scanning / variable discovery
```

## Step 2 -- Implement the SimulationParser Protocol

Your parser facade must expose the four methods defined in the protocol
(`src/parsing/parser_protocol.py`):

| Method | Responsibility |
|--------|---------------|
| `submit_scan_async` | Discover variables across a sample of output files. Returns a list of `Future[list[ScannedVariable]]`. |
| `aggregate_scan_results` | Deduplicate and merge scan results from multiple workers into a single sorted list. |
| `submit_parse_async` | Submit a parallel parsing job over the output directory. Returns a `ParseBatchResult` containing futures and variable names. |
| `finalize_parsing` | Post-process worker results and write the canonical `results.csv` file. Returns the output path or `None`. |

The full protocol signature is:

```python
from concurrent.futures import Future
from typing import Any
from src.core.models import ParseBatchResult, ScannedVariable, StatConfig

class SimulationParser(Protocol):
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
```

## Step 3 -- Define Simulator-Specific Models

If your simulator has metadata that goes beyond the base `ScannedVariable`
(for example, gem5 adds `minimum` / `maximum` for distribution bucket
ranges), create a subclass in `models.py`:

```python
# src/parsing/sniper/models.py
from dataclasses import dataclass
from src.core.models.parsing_models import ScannedVariable

@dataclass(frozen=True)
class SniperScannedVariable(ScannedVariable):
    """Adds core-count metadata specific to Sniper output."""
    core_count: int | None = None
```

If no extra fields are needed, you can use `ScannedVariable` directly.

## Step 4 -- Register with SimulatorRegistry

Registration happens at **module level** in your package's `__init__.py`.
You must provide a `SimulatorInfo` descriptor and a **lazy factory function**.

```python
# src/parsing/sniper/__init__.py
from src.parsing.registry import (
    ParsingStrategy,
    SimulatorInfo,
    SimulatorRegistry,
)
from src.parsing.parser_protocol import SimulationParser

SNIPER_INFO = SimulatorInfo(
    name="sniper",
    display_name="Sniper",
    description="Sniper multi-core simulator",
    file_pattern="sim.out",
    variable_types=["scalar", "interval"],
    internal_stats=frozenset({"__total_cycles"}),
    parsing_strategies=[
        ParsingStrategy(
            name="default",
            display_name="Default (sim.out)",
            description="Parse standard Sniper sim.out files.",
        ),
    ],
)

def _create_sniper_parser() -> SimulationParser:
    # Lazy import avoids circular dependencies and speeds up startup.
    from src.parsing.sniper.impl.sniper_parser_api import SniperParserAPI
    return SniperParserAPI()

SimulatorRegistry.register(SNIPER_INFO, _create_sniper_parser)
```

Key rules:
- `name` must be unique across all registered simulators.
- At least one `ParsingStrategy` is required; `SimulatorInfo.__post_init__`
  raises `ValueError` otherwise.
- The factory function **must** use a lazy import for the implementation class.
- Duplicate registration of the same name raises `ValueError`.

## Step 5 -- Create Scanning Logic

The scanner discovers what variables exist inside the output files before the
user configures a full parse. Implement two static methods (or instance
methods delegated from the facade):

```python
# src/parsing/sniper/impl/sniper_scanner.py
import os
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from src.core.models import ScannedVariable

class SniperScanner:
    _pool = ThreadPoolExecutor(max_workers=4)

    @staticmethod
    def submit_scan_async(
        stats_path: str,
        stats_pattern: str = "sim.out",
        limit: int = 5,
    ) -> list[Future[list[ScannedVariable]]]:
        path = Path(stats_path)
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {stats_path}")
        files = sorted(path.rglob(stats_pattern))[:limit]
        if not files:
            raise FileNotFoundError("No output files found.")
        return [
            SniperScanner._pool.submit(SniperScanner._scan_file, f)
            for f in files
        ]

    @staticmethod
    def _scan_file(file_path: Path) -> list[ScannedVariable]:
        # Parse the file and return discovered variables.
        variables: list[ScannedVariable] = []
        # ... simulator-specific scanning logic ...
        return variables

    @staticmethod
    def aggregate_scan_results(
        results: list[list[ScannedVariable]],
    ) -> list[ScannedVariable]:
        merged: dict[str, ScannedVariable] = {}
        for file_vars in results:
            for var in file_vars:
                if var.name not in merged:
                    merged[var.name] = var
        return sorted(merged.values(), key=lambda v: v.name)
```

## Step 6 -- Create Parsing Logic with Strategies

The parser orchestrates parallel work across output files and writes the
final CSV. Use `ParseBatchResult` to return futures alongside variable names.

```python
# src/parsing/sniper/impl/sniper_parser.py
import csv, os
from typing import Any
from src.core.models import ParseBatchResult, ScannedVariable, StatConfig

class SniperParser:
    @staticmethod
    def submit_parse_async(
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "default",
        scanned_vars: list[ScannedVariable] | None = None,
    ) -> ParseBatchResult:
        # 1. Discover files
        # 2. Build work items per strategy_type
        # 3. Submit to a thread/process pool
        # 4. Return ParseBatchResult(futures=..., var_names=...)
        ...

    @staticmethod
    def finalize_parsing(
        output_dir: str,
        results: list[dict[str, Any]],
        strategy_type: str = "default",
        var_names: list[str] | None = None,
    ) -> str | None:
        if not results:
            return None
        os.makedirs(output_dir, exist_ok=True)
        csv_path = os.path.join(output_dir, "results.csv")
        # Write header + rows from results dicts
        # ...
        return csv_path
```

Wire the parser and scanner together in a thin facade class:

```python
# src/parsing/sniper/impl/sniper_parser_api.py
from src.parsing.sniper.impl.sniper_parser import SniperParser
from src.parsing.sniper.impl.sniper_scanner import SniperScanner

class SniperParserAPI:
    def submit_scan_async(self, stats_path, stats_pattern="sim.out", limit=5):
        return SniperScanner.submit_scan_async(stats_path, stats_pattern, limit)

    def aggregate_scan_results(self, results):
        return SniperScanner.aggregate_scan_results(results)

    def submit_parse_async(self, stats_path, stats_pattern, variables,
                           output_dir, strategy_type="default",
                           scanned_vars=None):
        return SniperParser.submit_parse_async(
            stats_path, stats_pattern, variables,
            output_dir, strategy_type, scanned_vars,
        )

    def finalize_parsing(self, output_dir, results,
                         strategy_type="default", var_names=None):
        return SniperParser.finalize_parsing(
            output_dir, results, strategy_type, var_names,
        )
```

## Step 7 -- Add Tests

### Unit tests -- protocol compliance and registry integration

```python
# tests/unit/test_sniper_registry.py
import pytest
from src.parsing.parser_protocol import SimulationParser
from src.parsing.registry import SimulatorRegistry

# Importing the package triggers auto-registration
import src.parsing.sniper  # noqa: F401

class TestSniperRegistration:
    def test_registered(self):
        assert "sniper" in SimulatorRegistry.available_simulators()

    def test_parser_satisfies_protocol(self):
        parser = SimulatorRegistry.get_parser("sniper")
        assert isinstance(parser, SimulationParser)

    def test_info_fields(self):
        info = SimulatorRegistry.get_info("sniper")
        assert info.name == "sniper"
        assert info.file_pattern == "sim.out"
        assert len(info.parsing_strategies) >= 1
```

### Integration tests -- end-to-end scan and parse

Create a small fixture directory with sample output files and write tests
that exercise `submit_scan_async` through `finalize_parsing`.

## Step 8 -- Wire into ApplicationAPI

The `ApplicationAPI` (`src/core/application_api.py`) accepts an optional
`parser` argument. The web layer selects the active simulator based on the
`SimulatorRegistry` and passes it in:

```python
from src.parsing.registry import SimulatorRegistry

parser = SimulatorRegistry.get_parser("sniper")   # lazy + cached
api = ApplicationAPI(parser=parser)
```

The registry is also exposed through facade methods on `ApplicationAPI`:

- `ApplicationAPI.available_simulators()` -- lists registered names.
- `ApplicationAPI.available_simulator_info()` -- returns `SimulatorInfo` list.
- `ApplicationAPI.get_simulator_info(name)` -- returns a single info object.

These methods are used by the UI to populate simulator selection dropdowns.
Your newly registered simulator appears there automatically once its
`__init__.py` is imported.

**Ensuring the import happens at startup**: add an import of your package in
the application entry point or in an explicit plugin-loading module so that
the module-level `SimulatorRegistry.register(...)` call executes before the
UI renders its simulator list.

---

## Complete Example

Below is a minimal but functional skeleton for a hypothetical "sniper"
simulator backend. Each file is kept short to illustrate structure; real
implementations will contain the actual file-parsing logic.

### `src/parsing/sniper/__init__.py`

```python
"""Sniper simulator backend -- auto-registers on import."""

from src.parsing.parser_protocol import SimulationParser
from src.parsing.registry import ParsingStrategy, SimulatorInfo, SimulatorRegistry

SNIPER_INFO = SimulatorInfo(
    name="sniper",
    display_name="Sniper",
    description="Sniper multi-core simulator",
    file_pattern="sim.out",
    variable_types=["scalar", "interval"],
    internal_stats=frozenset({"__total_cycles"}),
    parsing_strategies=[
        ParsingStrategy(
            name="default",
            display_name="Default (sim.out)",
            description="Parse standard Sniper sim.out output files.",
        ),
    ],
)

def _create_sniper_parser() -> SimulationParser:
    from src.parsing.sniper.impl.sniper_parser_api import SniperParserAPI
    return SniperParserAPI()

SimulatorRegistry.register(SNIPER_INFO, _create_sniper_parser)
```

### `src/parsing/sniper/impl/sniper_parser_api.py`

```python
"""Thin facade combining SniperParser and SniperScanner."""

from concurrent.futures import Future
from typing import Any
from src.core.models import ParseBatchResult, ScannedVariable, StatConfig
from src.parsing.sniper.impl.sniper_parser import SniperParser
from src.parsing.sniper.impl.sniper_scanner import SniperScanner

class SniperParserAPI:
    def submit_scan_async(self, stats_path, stats_pattern="sim.out", limit=5):
        return SniperScanner.submit_scan_async(stats_path, stats_pattern, limit)

    def aggregate_scan_results(self, results):
        return SniperScanner.aggregate_scan_results(results)

    def submit_parse_async(self, stats_path, stats_pattern, variables,
                           output_dir, strategy_type="default",
                           scanned_vars=None):
        return SniperParser.submit_parse_async(
            stats_path, stats_pattern, variables,
            output_dir, strategy_type, scanned_vars)

    def finalize_parsing(self, output_dir, results,
                         strategy_type="default", var_names=None):
        return SniperParser.finalize_parsing(
            output_dir, results, strategy_type, var_names)
```

---

## Checklist

Before merging, verify every item below:

- [ ] `SimulatorInfo` descriptor is complete (name, display_name, file_pattern, variable_types, internal_stats, parsing_strategies).
- [ ] At least one `ParsingStrategy` is defined.
- [ ] Factory function uses a **lazy import** to avoid circular dependencies.
- [ ] `SimulatorRegistry.register(...)` is called at module level in `__init__.py`.
- [ ] The package is imported at application startup so registration executes.
- [ ] All four `SimulationParser` protocol methods are implemented with matching signatures.
- [ ] `isinstance(parser, SimulationParser)` returns `True` at runtime.
- [ ] `finalize_parsing` writes a well-formed CSV to `output_dir`.
- [ ] `submit_scan_async` raises `FileNotFoundError` when the path is invalid.
- [ ] Unit tests cover registry integration and protocol compliance.
- [ ] Integration tests exercise a scan-then-parse round-trip with fixture data.
- [ ] No imports from `src.web` exist in the parsing package (layer boundary).

## See Also

- `src/parsing/parser_protocol.py` -- the `SimulationParser` protocol definition.
- `src/parsing/registry.py` -- `SimulatorRegistry`, `SimulatorInfo`, `ParsingStrategy`, and the gem5 reference registration.
- `src/parsing/gem5/` -- the reference implementation (gem5 backend).
- `src/core/models/parsing_models.py` -- `ScannedVariable`, `StatConfig`, `ParseBatchResult`.
- `src/core/application_api.py` -- `ApplicationAPI`, the facade consumed by the web layer.
- `tests/unit/test_simulator_registry.py` -- unit tests for the registry pattern.
