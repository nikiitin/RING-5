---
title: "Layer Boundaries"
parent: Architecture
grand_parent: Engineering Reference
nav_order: 2
---

# Layer Boundaries

## Three-Layer Architecture

```
+-----------------------------------------------------+
|                  WEB  (src/web/)                     |
|  pages/ controllers/ components/ rendering/ models/  |
+---------------------------+--------------------------+
                            |  imports
                            v
+-----------------------------------------------------+
|                 CORE  (src/core/)                    |
|  application_api.py  services/  models/  state/      |
+----------+------------------+-----------------------+
           |  3 protocol      ^
           |  imports          |  imports
           v                  |
+-----------------------------------------------------+
|               PARSING  (src/parsing/)                |
|  parser_protocol.py  registry.py  gem5/              |
+-----------------------------------------------------+
```

**Rule**: Web --> Core <-- Parsing. No other cross-layer direction is allowed.

---

## Import Direction Matrix

| From \ To       | Core             | Parsing                          | Web        |
|-----------------|------------------|----------------------------------|------------|
| **Core**        | (internal)       | 3 imports in `application_api.py`| FORBIDDEN  |
| **Parsing**     | 26 imports / 19 files | (internal)                  | FORBIDDEN  |
| **Web**         | 104 imports / 58 files | FORBIDDEN                  | (internal) |

---

## Allowed Imports Per Layer

| Layer     | CAN import from           | Import targets                                      |
|-----------|---------------------------|-----------------------------------------------------|
| **Core**  | `src/core/*`              | Own models, services, state, utils                  |
| **Core**  | `src/parsing` (3 only)    | `SimulationParser`, `SimulatorRegistry`, `ScanWorkPool` via `application_api.py` |
| **Parsing** | `src/core/models/*`     | `ParseBatchResult`, `ScannedVariable`, `StatConfig`, `StatParamValue`, `ScannedVariableDict`, `ParseVariableConfig` |
| **Parsing** | `src/core/common/utils` | `normalize_user_path`, `sanitize_glob_pattern`      |
| **Parsing** | `src/core/services`     | `PatternIndexService` (1 service import)            |
| **Parsing** | `src/parsing/*`         | Own modules                                         |
| **Web**   | `src/core/*`              | `ApplicationAPI`, all models, services, protocols   |
| **Web**   | `src/web/*`               | Own pages, components, rendering, models            |

---

## Forbidden Imports Per Layer

| Layer       | MUST NOT import from | Violation grep command                          |
|-------------|---------------------|-------------------------------------------------|
| **Core**    | `src.web`           | `grep -r "from src.web" src/core/`              |
| **Parsing** | `src.web`           | `grep -r "from src.web" src/parsing/`           |
| **Web**     | `src.parsing`       | `grep -r "from src.parsing" src/web/`           |

All three commands must produce empty output.

---

## Core-to-Parsing Bridge

File: `src/core/application_api.py`

Three imports exist. Each is deliberate.

```python
# Line 54 -- Protocol type for dependency injection
from src.parsing.parser_protocol import SimulationParser

# Line 55 -- Registry metadata for simulator auto-discovery
from src.parsing.registry import SimulatorInfo, SimulatorRegistry
```

**Why these exist**:

| Import              | Used for                                      | Pattern              |
|---------------------|-----------------------------------------------|----------------------|
| `SimulationParser`  | Constructor parameter type (`parser: SimulationParser`) | Dependency Inversion |
| `SimulatorRegistry` | `list_simulators()`, `get_simulator_info()`   | Service Locator      |
| `SimulatorInfo`     | Return type from registry queries             | DTO                  |

`ApplicationAPI` never imports concrete implementations (`Gem5Parser`).
Concrete parsers are injected or resolved via the registry at runtime.

---

## Boundary Validation Commands

Run from project root. Each command must produce **no output** (zero matches).

```bash
# Core must not import from Web
grep -rn "from src\.web" src/core/
# Expected: (empty)

# Parsing must not import from Web
grep -rn "from src\.web" src/parsing/
# Expected: (empty)

# Web must not import from Parsing
grep -rn "from src\.parsing" src/web/
# Expected: (empty)

# Core-to-Parsing imports (audit -- should be exactly 3 lines)
grep -rn "from src\.parsing" src/core/
# Expected: exactly 3 results, all in application_api.py
```

---

## Where Does New Code Go?

| If the new code is...                  | Place it in                                    | Example                                  |
|----------------------------------------|------------------------------------------------|------------------------------------------|
| A data model / dataclass / TypedDict   | `src/core/models/`                             | New `BenchmarkResult` dataclass          |
| A visualization config model           | `src/core/models/visualization/`               | New `WatermarkConfig`                    |
| A Protocol (cross-layer contract)      | `src/core/models/` or `src/core/services/`     | New `ExportProtocol`                     |
| Business logic / data transformation   | `src/core/services/`                           | New normalization algorithm              |
| A shaper (pipeline step)               | `src/core/services/shapers/impl/`              | New `FilterShaper`                       |
| State management                       | `src/core/state/repositories/`                 | New `ExportRepository`                   |
| A new simulator parser                 | `src/parsing/<simulator>/`                     | New `sniperparser/`                      |
| A parsing strategy                     | `src/parsing/gem5/impl/strategies/`            | New `HybridStrategy`                     |
| A Streamlit page                       | `src/web/pages/`                               | New `benchmarks.py` page                 |
| A reusable UI widget                   | `src/web/components/common/`                   | New `progress_bar.py`                    |
| A page-specific UI component           | `src/web/components/<feature>/`                | New `data_source/filter_panel.py`        |
| A plot type                            | `src/web/pages/ui/plotting/types/`             | New `BoxPlot`                            |
| A settings panel                       | `src/web/components/plotting/settings/`        | New `animation_settings.py`              |
| A rendering connector                  | `src/web/rendering/`                           | New `bokeh_connector.py`                 |
| Plot style UI strategy                 | `src/web/pages/ui/plotting/styles/`            | New `heatmap_ui.py`                      |
| A utility / helper                     | `src/core/common/utils.py`                     | New path helper                          |

---

## Common Mistakes to Avoid

### 1. Importing Parsing From Web

```python
# WRONG -- Web must never import from Parsing
from src.parsing.gem5.impl.gem5_parser import Gem5Parser

# CORRECT -- Go through ApplicationAPI
api = st.session_state.api  # ApplicationAPI instance
result = api.parse_batch(variables)
```

### 2. Importing Web From Core

```python
# WRONG -- Core must never know about the UI
from src.web.pages.ui.plotting.base_plot import BasePlot

# CORRECT -- Use PlotProtocol (defined in Core)
from src.core.models.plot_protocol import PlotProtocol
```

### 3. Importing Concrete Classes Instead of Protocols

```python
# WRONG -- Couples to implementation
from src.core.state.repository_state_manager import RepositoryStateManager

# CORRECT -- Depend on the Protocol
from src.core.state.state_manager import StateManager
```

### 4. Adding New Core-to-Parsing Imports Outside ApplicationAPI

```python
# WRONG -- Scatters the bridge across multiple core files
# In src/core/services/some_service.py:
from src.parsing.gem5.models import SomeGem5Model

# CORRECT -- All parsing access goes through ApplicationAPI
# Add a method to ApplicationAPI that wraps the parsing call
```

### 5. Putting UI Logic in Core

```python
# WRONG -- Streamlit in core
import streamlit as st
def save_data(df):
    st.session_state["data"] = df

# CORRECT -- Core returns data; Web stores it
# Core: def process_data(df) -> pd.DataFrame
# Web:  st.session_state["data"] = api.process_data(df)
```

### 6. Putting Business Logic in Web

```python
# WRONG -- Computation in a Streamlit component
# In src/web/components/common/chart_display.py:
df["normalized"] = df["value"] / df["value"].max()

# CORRECT -- Move to a Core service
# In src/core/services/managers/arithmetic_service.py:
def normalize_column(df, col): ...
```

### 7. Skipping the Facade

```python
# WRONG -- Web reaching into Core internals
from src.core.state.repositories.data_repository import DataRepository
repo = DataRepository()
repo.set_raw_data(df)

# CORRECT -- Use ApplicationAPI methods
api.set_data(df)
```

---

## Quick Reference: Layer File Counts

| Layer     | Python files | Packages | Primary entry point         |
|-----------|-------------|----------|-----------------------------|
| Core      | 81          | 12       | `src/core/application_api.py` (ApplicationAPI) |
| Parsing   | 36          | 8        | `src/parsing/__init__.py` (ParseService, ScannerService) |
| Web       | ~120        | 22       | `app.py` (Streamlit entry point)                |

---

## Dependency Flow Summary

```
app.py
  |
  v
ApplicationAPI  <--- single facade, lives in Core
  |         |
  v         v
Services   StateManager (Protocol)
  |              |
  v              v
Managers    RepositoryStateManager
DataSvcs         |
Shapers     7 Repositories (all use st.session_state)
  |
  v
ParseService / ScannerService  <--- injected from Parsing
```

- Web layer calls `ApplicationAPI` methods.
- `ApplicationAPI` delegates to `ServicesAPI` and `StateManager`.
- `ApplicationAPI` delegates parsing to `SimulationParser` (injected).
- No layer skips are permitted.
