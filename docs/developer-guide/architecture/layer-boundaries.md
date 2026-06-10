---
title: "Layer Boundaries"
parent: Architecture
grand_parent: Developer Guide
nav_order: 2
---

# Layer Boundaries

## Overview

RING-5 Unified Engine v2 is organized into three layers with strict import
direction rules. Every Python module belongs to exactly one of these layers:

| Layer | Package | Files | Responsibility |
|-------|---------|-------|----------------|
| **Core** | `src/core/` | 81 `.py` | Models, services, state, `ApplicationAPI` facade |
| **Parsing** | `src/parsing/` | 36 `.py` | gem5 parser, scanner, Perl worker integration |
| **Web** | `src/web/` | ~120 `.py` | Streamlit pages, components, controllers, rendering |

The fundamental rule is **Web depends on Core; Parsing depends on Core; nothing
depends on Web except Web itself.** This ensures that business logic and data
ingestion stay decoupled from the presentation framework. The rule is enforced
by convention and validated by automated grep checks (see
[Boundary Validation](#boundary-validation) below).

Violating layer boundaries introduces hidden coupling that makes refactoring
dangerous and testing difficult. A single `import streamlit` inside
`src/core/` would tie the domain layer to a specific UI framework. A Web
import inside Parsing would make the data ingestion pipeline untestable
without a running Streamlit server.

---

## Import Direction Matrix

The table below summarizes every cross-layer import relationship. "Internal"
means the layer imports from itself (always allowed).

| From / To | Core | Parsing | Web |
|-----------|------|---------|-----|
| **Core** | internal | 3 imports (`ApplicationAPI` only) | **ZERO** |
| **Parsing** | 28 import lines | internal | **ZERO** |
| **Web** | 96 import lines across 58 files | **ZERO** | internal |

Three cells are unconditionally forbidden and contain zero imports: Core to
Web, Parsing to Web, and Web to Parsing. The three Core-to-Parsing imports
are a deliberate Dependency Inversion bridge explained in the next section.

---

## Core to Parsing Bridge

Core imports from Parsing in exactly **one file** and for exactly **three
symbols**. Both import statements live in `src/core/application_api.py`:

```python
# src/core/application_api.py:54
from src.parsing.parser_protocol import SimulationParser

# src/core/application_api.py:55
from src.parsing.registry import SimulatorInfo, SimulatorRegistry
```

### Why these imports exist

`ApplicationAPI` is the single orchestration facade. It needs to:

1. Accept a `SimulationParser` **protocol type** for dependency injection so
   callers can swap parser backends (see `src/core/application_api.py:75`).
2. Access `SimulatorRegistry` to perform auto-discovery of registered
   simulators (see `src/core/application_api.py:94`).
3. Use `SimulatorInfo` to return registry metadata to the UI without the UI
   importing from Parsing directly (see `src/core/application_api.py:414`).

All three are **protocol or metadata** imports. `ApplicationAPI` never imports
a concrete implementation such as `Gem5Parser`. This is Dependency Inversion:
the core depends on an abstraction that Parsing implements.

---

## Parsing to Core Dependencies

The Parsing layer imports models and utilities from Core -- 28 import lines
across 12 files. This is the expected direction: infrastructure depends on
the domain.

| Parsing file | Core imports | Purpose |
|-------------|-------------|---------|
| `src/parsing/parser_protocol.py:4` | `ParseBatchResult`, `ScannedVariable`, `StatConfig` | Protocol type signatures |
| `src/parsing/gem5/models.py:13-14` | `ScannedVariableDict`, `ScannedVariable` | Extend core model with gem5 metadata |
| `src/parsing/gem5/impl/gem5_parser.py` | `ParseBatchResult`, `ScanResult`, `ScanFileResult`, `ScannedVariable`, `StatConfig`, `PatternIndexService`, `normalize_user_path` | gem5 backend (parse + scan + CSV) |
| `src/parsing/framework/file_discovery.py` | `normalize_user_path`, `sanitize_glob_pattern` | Shared stats-file discovery |
| `src/parsing/gem5/impl/pool/pool.py:14` | `ScannedVariable` | Worker pool type hints |
| `src/parsing/gem5/impl/pool/scan_work.py:9` | `ScannedVariable` | Scan work items |
| `src/parsing/gem5/impl/scanning/scanner.py:17` | `ScannedVariable` | Core scanning logic |
| `src/parsing/gem5/impl/scanning/pattern_aggregator.py:16` | `ScannedVariable` | Pattern aggregation |
| `src/parsing/gem5/impl/scanning/gem5_scan_work.py:15` | `ScannedVariable` | Scan work definitions |
| `src/parsing/gem5/impl/strategies/simple.py:28-33` | `normalize_user_path`, `sanitize_glob_pattern`, `StatConfig` | Simple parsing strategy |
| `src/parsing/gem5/impl/strategies/file_parser_strategy.py:21` | `StatConfig` | Strategy protocol definition |
| `src/parsing/gem5/types/base.py:11` | `StatParamValue` | Base stat type |
| `src/parsing/gem5/types/vector.py:14` | `StatParamValue` | Vector stat type |
| `src/parsing/gem5/types/distribution.py:6` | `StatParamValue` | Distribution stat type |
| `src/parsing/gem5/types/histogram.py:7` | `StatParamValue` | Histogram stat type |
| `src/parsing/gem5/types/configuration.py:5` | `StatParamValue` | Configuration stat type |
| `src/parsing/gem5/types/type_mapper.py:11-13` | `StatConfig`, `ScannedVariableDict`, `StatParamValue` | Type discrimination |

The imports fall into three categories:

- **Models** (`StatConfig`, `ScannedVariable`, `ParseBatchResult`,
  `StatParamValue`, `ScannedVariableDict`) -- the vast majority.
- **Utilities** (`normalize_user_path`, `sanitize_glob_pattern`) -- shared
  path helpers from `src/core/common/utils.py`.
- **Services** (`PatternIndexService`) -- the tightest coupling point. This
  is a service-level import used by `src/parsing/gem5/impl/gem5_parser.py`.

---

## Web to Core Dependencies

Web imports from Core extensively -- 96 import statements across 58 files.
This is the expected and heaviest coupling direction: the presentation layer
consumes the domain.

The imports group into four categories:

### Models and data types

Web components import domain models for type hints and data manipulation:
`FigureConfig`, `TraceConfig`, `AxisConfig`, `ShaperStepConfig`,
`PipelineStep`, `PlotConfig`, `OperationRecord`, `ParseVariableConfig`,
`ScannedVariable`, among others.

Examples: `src/web/pages/ui/plotting/base_plot.py:10-12`,
`src/web/rendering/config_builder.py:19-38`,
`src/web/components/data_source/variable_editor.py`.

### Visualization configuration

Rendering connectors and settings components import the full visualization
model hierarchy (`FigureConfig`, `AxesConfig`, `LegendConfig`,
`TypographyConfig`, `TraceBuildResult`, palette utilities) to translate
engine-agnostic configs into Plotly or matplotlib calls.

Examples: `src/web/rendering/plotly_connector.py`,
`src/web/rendering/matplotlib_connector.py`,
`src/web/rendering/trace_to_plotly.py`.

### ApplicationAPI facade

Pages and controllers import `ApplicationAPI` (or receive it via constructor
injection) as their single access point to business logic. No page file
reaches into `src/core/services/` or `src/core/state/` directly for
operations -- they go through the facade.

Examples: `src/web/pages/data_source.py`, `src/web/pages/manage_plots.py`,
`src/web/controllers/plot/render_controller.py`.

### Protocols

Web-layer code imports core protocols (`PlotProtocol`, `StateManager`,
`ServicesAPI`) to remain decoupled from concrete implementations when
declaring function signatures or properties.

---

## Forbidden Import Directions

Three import directions are unconditionally forbidden. They currently have
**zero** occurrences and must remain that way.

### Core must never import from Web

The Core layer contains pure domain logic. If `src/core/` imported Streamlit
widgets or web components, Core could no longer be tested without a UI
framework. The `PlotDeserializer` callback is injected at runtime through
`ApplicationAPI.__init__` (see `src/core/application_api.py:74`) precisely to
avoid a Core-to-Web import for plot deserialization.

### Parsing must never import from Web

The Parsing layer handles data ingestion. It communicates results via core
models (`ParseBatchResult`, `ScannedVariable`). If Parsing tried to render
Streamlit widgets or read `st.session_state`, it would break the parallel
worker pool architecture that gives the parser its 54x speedup.

### Web must never import from Parsing

All parsing access goes through `ApplicationAPI`. The Web layer calls
`api.submit_parse_async()` and `api.finalize_parsing()` -- it never
instantiates `Gem5Parser` directly. This indirection means a new simulator
backend could be registered without touching any Web code.

---

## Public API Surface per Layer

Each layer exposes a well-defined public API through its `__init__.py` files.

### Core

The primary entry point is `ApplicationAPI` in
`src/core/application_api.py:60`.

`src/core/services/__init__.py` re-exports the full service API:

- `ServicesAPI` (Protocol), `DefaultServicesAPI` (implementation)
- Sub-API protocols: `ManagersAPI`, `DataServicesAPI`, `ShapersAPI`
- Sub-API implementations: `DefaultManagersAPI`, `DefaultDataServicesAPI`,
  `DefaultShapersAPI`
- Individual services: `ArithmeticService`, `OutlierService`,
  `ReductionService`, `CsvPoolService`, `ConfigService`, `PathService`,
  `VariableService`, `PortfolioService`, `PipelineService`, `ShaperFactory`

`src/core/models/__init__.py` re-exports `ParseBatchResult`,
`ScannedVariable`, `StatConfig`.

`src/core/models/visualization/__init__.py` re-exports `FigureConfig` and all
visualization config models, palette utilities, and the config resolver.

### Parsing

`src/parsing/__init__.py` defines a minimal public API:

```python
# src/parsing/__init__.py exposes no concrete classes — reach a backend only via:
from src.parsing.registry import SimulatorRegistry
parser = SimulatorRegistry.get_parser("gem5")   # -> Gem5Parser (a SimulationParser)
```

Some tests import the backend under a local alias (e.g. `Gem5Parser as
ParseService`) for readability — these are test-local cosmetics, not production
shims.

### Web

`src/web/rendering/__init__.py` exports the rendering public API (8 classes):

```python
__all__ = [
    "ConfigSpecBuilder", "EngineManager", "FigureSpecToPlotly",
    "FigureSpecToMatplotlib", "PlotlyFigureSpecBuilder", "PresetApplicator",
    "PresetSpecBuilder", "MatplotlibTraceRenderer",
]
```

`src/web/pages/ui/plotting/types/__init__.py` exports all 9 plot types.

Most other Web sub-packages have minimal `__init__.py` files; their API
surface is defined by direct imports rather than package-level re-exports.

---

## Boundary Validation

Run these commands from the repository root to verify that no forbidden
imports exist. Each command must return zero results.

### Core must not import Streamlit

```bash
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__
```

Expected output: empty (no matches).

### Core must not reference session_state

```bash
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__
```

Expected output: empty (no matches).

### Core must not import from Web

```bash
grep -rn "from src\.web\.\|import src\.web" src/core/ --include="*.py" | grep -v __pycache__
```

Expected output: empty (no matches).

### Parsing must not import from Web

```bash
grep -rn "from src\.web\.\|import src\.web" src/parsing/ --include="*.py" | grep -v __pycache__
```

Expected output: empty (no matches).

### Web must not import from Parsing

```bash
grep -rn "from src\.parsing\.\|import src\.parsing" src/web/ --include="*.py" | grep -v __pycache__
```

Expected output: empty (no matches).

### Core to Parsing limited to ApplicationAPI only

```bash
grep -rn "from src\.parsing\." src/core/ --include="*.py" | grep -v __pycache__
```

Expected output: exactly two lines, both in `src/core/application_api.py`.

---

## Guidelines for New Code

When adding a new module, ask which layer it belongs in and follow the rules
below.

### When to put code in Core

- The module defines a domain model (dataclass, TypedDict, Protocol).
- The module implements business logic that does not depend on Streamlit or
  any specific parser backend.
- The module provides a service that multiple layers will consume.

Never import `streamlit`, `plotly`, or `matplotlib` in Core.

### When to put code in Parsing

- The module implements a new simulator backend or parsing strategy.
- The module extends the worker pool or scanning infrastructure.
- The module defines simulator-specific data models that extend core models
  (as `Gem5ScannedVariable` extends `ScannedVariable`).

Import core models and utilities freely. Never import from Web.

### When to put code in Web

- The module renders Streamlit widgets or HTML.
- The module translates `FigureConfig` into Plotly or matplotlib calls.
- The module orchestrates UI workflows (controllers, pages).

Import from Core freely. Never import from Parsing -- use `ApplicationAPI`
instead. If you need parsing results, the facade already exposes them.

### Adding a cross-layer dependency

If none of the above fits, consider whether a new protocol in Core can bridge
the gap. The existing `SimulationParser` protocol is the model: Core defines
the abstraction, the implementing layer provides the concrete class, and the
consumer depends only on the protocol.

---

## See Also

- **Architecture Overview** -- `docs/developer-guide/architecture/` for the
  high-level system diagram and package map.
- **Design Patterns** -- documents the Facade, Repository, Strategy, Factory,
  and Protocol patterns used at layer boundaries.
- **ApplicationAPI Reference** -- `src/core/application_api.py` is the
  primary boundary enforcement point.
- **Boundary enforcement** -- `make arch-check` (and the pre-commit hooks) verify these rules on every
  change; see also [`CLAUDE.md`](../../../CLAUDE.md) §1-2.
