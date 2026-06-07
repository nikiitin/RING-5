---
title: "Architecture Overview"
parent: Architecture
grand_parent: Developer Guide
nav_order: 1
redirect_from:
  - /developer/Architecture/
  - /Architecture/
---

# Architecture Overview

## 1. Overview

RING-5 Unified Engine v2 is a Streamlit-based web application for gem5
simulation data analysis and publication-quality plot generation. It ingests
raw simulation statistics (gem5 `stats.txt` files or pre-built CSV), applies
configurable data transformations, builds interactive visualizations with
Plotly and Matplotlib, and exports figures suitable for academic publication.

The codebase is organized as a strict **3-layer architecture** totalling
roughly 237 Python files across 42 packages. Every import between layers
follows a single rule -- the Web layer depends on Core; the Parsing layer
depends on Core; no other cross-layer direction is permitted.

---

## 2. The Three Layers

```
+-----------------------------------------------------------------------+
|                       Web  (Presentation)                             |
|  ~120 files   src/web/                                                |
|  Pages, Components, Controllers, Rendering Engines                    |
+----------------------------------+------------------------------------+
                                   |
                                   v  (imports)
+-----------------------------------------------------------------------+
|                       Core  (Domain)                                  |
|  81 files     src/core/                                               |
|  Models, Services, State Repositories, ApplicationAPI Facade          |
+----------------------------------+------------------------------------+
                                   ^
                                   |  (imports)
+-----------------------------------------------------------------------+
|                       Parsing  (Data / Infrastructure)                |
|  36 files     src/parsing/                                            |
|  gem5 Parser, Scanner, Perl Worker Pool, Strategy Pattern             |
+-----------------------------------------------------------------------+
```

**Import rule: Web --> Core <-- Parsing.** No violations exist.

### Core (`src/core/`, 81 files)

The domain layer. Contains all business models, service interfaces,
service implementations, and application state. It has zero UI imports.

| Sub-package | Purpose |
|---|---|
| `models/` | Dataclasses, TypedDicts, Protocols (`PlotProtocol`, `PlotDeserializer`) |
| `models/visualization/` | 13 config models (`FigureConfig`, `TraceConfig`, `AxisConfig`, ...) |
| `services/` | `ServicesAPI` facade, managers, data services, shapers, visualization |
| `state/` | `StateManager` Protocol, `RepositoryStateManager`, 7 child repositories |
| `application_api.py` | Top-level facade -- the single entry point for the UI |

### Parsing (`src/parsing/`, 36 files)

Handles all data ingestion. Currently only gem5 is implemented, but a
Protocol-based design (`SimulationParser`) supports adding new simulator
backends without touching Core or Web.

| Sub-package | Purpose |
|---|---|
| `parser_protocol.py` | `SimulationParser` Protocol (4 methods) |
| `registry.py` | `SimulatorRegistry` with auto-discovery |
| `gem5/impl/` | `Gem5Parser`, `Gem5Scanner`, worker pools, strategies |
| `gem5/types/` | Self-registering stat types (scalar, vector, distribution, histogram, configuration) |

### Web (`src/web/`, ~120 files)

The presentation layer. Owns all Streamlit UI code, rendering engines, and
user interaction logic.

| Sub-package | Purpose |
|---|---|
| `pages/` | 5 Streamlit pages + plot adapters |
| `pages/ui/plotting/` | `BasePlot` ABC, `PlotFactory`, 9 plot types, settings pills, styles |
| `controllers/plot/` | Creation, pipeline, and render controllers |
| `components/` | Reusable UI components (common, data source, data managers, shapers, plotting) |
| `rendering/` | `ConfigSpecBuilder`, Plotly connector, Matplotlib connector, engine manager |
| `state/ui_state_manager.py` | Web-layer session state management |

---

## 3. Entry Point and Initialization

The application entry point is `app.py` (172 lines). All imports are wrapped
inside `run_app()` so that multiprocessing workers do not trigger Streamlit
context warnings.

**Initialization sequence** (`app.py:15-59`):

1. `st.set_page_config(layout="wide")` configures the Streamlit page.
2. `get_api()` is decorated with `@st.cache_resource`, making `ApplicationAPI`
   a singleton for the lifetime of the Streamlit server process.
3. `BasePlot.from_dict` is injected as `plot_deserializer` -- this is how Core
   can deserialize plot dicts back into Web-layer `BasePlot` instances without
   ever importing from Web.
4. The singleton is stored as `st.session_state.api` so every page can access
   it.

**`ApplicationAPI` composition** (`src/core/application_api.py:60-76`):

```
ApplicationAPI
  |-- RepositoryStateManager   (state)
  |-- DefaultServicesAPI        (services facade)
  |     |-- DefaultManagersAPI       (arithmetic, outlier, reduction)
  |     |-- DefaultDataServicesAPI   (CSV pool, config, variables, portfolio)
  |     \-- DefaultShapersAPI        (factory, pipeline, 7+ shapers)
  |-- ParseService              (Gem5Parser)
  \-- ScannerService            (Gem5Scanner)
```

Constructor injection is used throughout. `ApplicationAPI.__init__` accepts a
`PlotDeserializer` callback and an optional `SimulationParser`. Sub-APIs
(`ServicesAPI`, `DataServicesAPI`, etc.) are composed internally and exposed as
read-only properties: `api.managers`, `api.data_services`, `api.shapers`.

---

## 4. Navigation and Pages

RING-5 uses custom sidebar navigation (not Streamlit's native `st.navigation`).
The active page name is stored in `st.session_state["_nav_page"]` and page
modules are lazy-imported on each rerun (`app.py:138-157`).

| # | Page | Module | Entry | Responsibility |
|---|---|---|---|---|
| 1 | Data Source | `src/web/pages/data_source.py` | `DataSourcePage(api).render()` | Parse gem5 stats, upload CSV, or load from recent pool |
| 2 | Data Managers | `src/web/pages/data_managers.py` | `show_data_managers_page(api)` | Seeds reduction, outlier removal, preprocessing, mixing |
| 3 | Manage Plots | `src/web/pages/manage_plots.py` | `show_manage_plots_page(api)` | Create plots, per-plot shaper pipelines, configure and render |
| 4 | Save/Load Portfolio | `src/web/pages/portfolio.py` | `show_portfolio_page(api)` | Save and restore complete analysis snapshots |
| 5 | Documentation | `src/web/pages/documentation.py` | `show_documentation_page()` | In-app links to guides and API references |

Pages form a linear workflow: ingest data, transform it, plot it, save it.
Each page (except Documentation) receives the `ApplicationAPI` instance as
its sole dependency.

---

## 5. Key Architectural Elements

### 5.1 Protocols (19 total)

| Layer | Protocol | File | Purpose |
|---|---|---|---|
| Core | `StateManager` | `src/core/state/state_manager.py` | 40+ method contract for all state operations |
| Core | `PlotProtocol` | `src/core/models/plot_protocol.py` | Decouples Core from Web's `BasePlot` |
| Core | `ServicesAPI` | `src/core/services/services_api.py` | Unified service facade |
| Core | `DataServicesAPI` | `src/core/services/data_services/data_services_api.py` | CSV pool, config, variables, portfolio |
| Core | `ManagersAPI` | `src/core/services/managers/managers_api.py` | Arithmetic, outlier, reduction |
| Core | `ShapersAPI` | `src/core/services/shapers/shapers_api.py` | Pipeline CRUD and shaper execution |
| Core | `PlotDeserializer` | `src/core/models/plot_protocol.py` | Callback type for dict-to-plot conversion |
| Parsing | `SimulationParser` | `src/parsing/parser_protocol.py` | 4-method contract for simulator backends |
| Parsing | `FileParserStrategy` | `src/parsing/gem5/impl/strategies/file_parser_strategy.py` | Strategy for individual file parsing |
| Web | 10 Protocols | `src/web/models/plot_protocols.py` and others | `PlotHandle`, `ConfigRenderer`, `RenderablePlot`, `PipelineExecutor`, etc. |

### 5.2 Factories (4)

| Factory | File | Creates |
|---|---|---|
| `ShaperFactory` | `src/core/services/shapers/factory.py` | Shaper instances (10 registered types) |
| `StrategyFactory` | `src/parsing/gem5/impl/strategies/factory.py` | `FileParserStrategy` instances |
| `PlotFactory` | `src/web/pages/ui/plotting/plot_factory.py` | `BasePlot` instances (9 plot types) |
| `StyleUIFactory` | `src/web/pages/ui/plotting/styles/factory.py` | `BaseStyleUI` instances |

### 5.3 Registries (4)

| Registry | File | Discovery |
|---|---|---|
| `ShaperFactory._registry` | `src/core/services/shapers/factory.py` | Static dict + `register()` classmethod |
| `SimulatorRegistry` | `src/parsing/registry.py` | Auto-registration via package imports |
| `StatTypeRegistry` | `src/parsing/gem5/types/__init__.py` | Self-registering on import |
| `PlotFactory` | `src/web/pages/ui/plotting/plot_factory.py` | Static dict in factory |

### 5.4 Abstract Base Classes (4)

| ABC | File | Concrete Types |
|---|---|---|
| `Shaper` | `src/core/services/shapers/shaper.py` | 7+ shapers (Selector, Sort, Mean, Normalize, Pivot, ...) |
| `Job` | `src/parsing/gem5/impl/pool/job.py` | `ParseWork`, `ScanWork` |
| `BasePlot` | `src/web/pages/ui/plotting/base_plot.py` | 9 plot types (Bar, Line, Scatter, Heatmap, ...) |
| `DataManager` | `src/web/components/data_managers/data_manager.py` | Preprocessor, SeedsReducer, OutlierRemover, Mixer |

---

## 6. Package-Level Dependency Graph

```
+---------------------------------------------------------------------------+
|                        PRESENTATION (Web)                                 |
|                                                                           |
|  pages/ --> controllers/ --> components/ --> rendering/                    |
|    |              |               |               |                       |
|    |              +---------------+---------------+                       |
|    |                           |                                          |
|    |                    models/plot_protocols.py                           |
|    |                    models/plot_models.py                              |
|    |                    state/ui_state_manager.py                          |
|    |                           |                                          |
|    +---------------------------+------------------------------------------+
                                 |
                                 v
+---------------------------------------------------------------------------+
|                       DOMAIN (Core)                                       |
|                                                                           |
|  application_api.py  (FACADE)                                             |
|    +-- services/                                                          |
|    |   +-- services_api.py    (Protocol)                                  |
|    |   +-- services_impl.py   (DefaultServicesAPI)                        |
|    |   +-- managers/          (arithmetic, outlier, reduction)             |
|    |   +-- data_services/     (CSV, config, variables, portfolio)          |
|    |   +-- shapers/           (factory, pipeline, 7+ shapers)             |
|    |   \-- visualization/     (resolver, palette, interaction)             |
|    +-- models/                                                            |
|    |   +-- data_models.py     parsing_models.py  shaper_models.py         |
|    |   +-- plot_protocol.py   plot_config.py     history_models.py        |
|    |   \-- visualization/     (figure, trace, axis, legend, etc.)         |
|    \-- state/                                                             |
|        +-- state_manager.py   (Protocol)                                  |
|        +-- repository_state_manager.py  (Implementation)                  |
|        \-- repositories/      (7 child repositories)                      |
|                                                                           |
|    application_api.py --> parsing.parser_protocol.SimulationParser         |
|    application_api.py --> parsing.registry.SimulatorRegistry               |
|                                                                           |
+---------------------------------------------------------------------------+
                                 ^
                                 |
+---------------------------------------------------------------------------+
|                    DATA / INFRASTRUCTURE (Parsing)                         |
|                                                                           |
|  parser_protocol.py    (SimulationParser Protocol)                        |
|  registry.py           (SimulatorRegistry)                                |
|  parse_service.py      (shim -> Gem5Parser)                               |
|  scanner_service.py    (shim -> Gem5Scanner)                              |
|  gem5/                                                                    |
|    +-- impl/                                                              |
|    |   +-- gem5_parser.py     gem5_scanner.py                             |
|    |   +-- pool/             (PerlWorkerPool, WorkPool, Job)              |
|    |   +-- scanning/         (scanner, pattern_aggregator)                |
|    |   \-- strategies/       (simple, config_aware, perl_worker)          |
|    \-- types/                (scalar, vector, distribution, etc.)         |
|                                                                           |
+---------------------------------------------------------------------------+

Legend:
  -->  = imports / depends on
  ^/v  = allowed dependency direction
```

---

## 7. Streamlit Integration Points

The application bridges its layered architecture with Streamlit at five
well-defined points.

| Concern | Location | Mechanism |
|---|---|---|
| **Singleton API** | `app.py:54-56` | `@st.cache_resource` ensures one `ApplicationAPI` per server process |
| **Session state storage** | `src/core/state/repositories/` | All 7 repositories use `st.session_state` as their backing store |
| **Page routing** | `app.py:138-157` | Manual `if/elif` dispatch on `st.session_state["_nav_page"]` with lazy imports |
| **Fragment isolation** | `app.py:115-135`, pages | `@st.fragment` / `st.fragment(fn)` scopes reruns to individual tabs and sections (11 fragments total) |
| **Web-layer UI state** | `src/web/state/ui_state_manager.py` | Centralised management of widget keys (`plot.{id}.*`, `manager.{name}.*`) |

Two rendering engines are supported and selectable at runtime via
`st.session_state["ring5_engine_mode"]`:

- **Plotly** (default) -- interactive charts with zoom, pan, hover, and legend
  drag. Rendered through `src/web/rendering/trace_to_plotly.py` and
  `src/web/rendering/plotly_connector.py`.
- **Matplotlib** -- publication-quality output with LaTeX font support and PGF
  export. Rendered through `src/web/rendering/matplotlib_connector.py` and
  `src/web/rendering/matplotlib_trace_renderer.py`.

---

## 8. See Also

| Topic | Path |
|---|---|
| Layer Boundaries (detailed import analysis) | `docs/developer-guide/architecture/layer-boundaries.md` |
| Design Patterns (12 patterns in depth) | `docs/developer-guide/architecture/design-patterns.md` |
| State Management (repository pattern) | `docs/developer-guide/architecture/state-management.md` |
| Core Services API | `docs/developer-guide/api/core-services.md` |
| Plotting System | `docs/developer-guide/api/plotting.md` |
| Parsing System | `docs/developer-guide/api/parsing.md` |
| Adding a New Plot Type | `docs/developer-guide/guides/adding-plot-types.md` |
