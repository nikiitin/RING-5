# RING-5 System Architecture Overview

## Purpose

- Streamlit-based web application for gem5 computer architecture simulation data analysis
- Parses gem5 stats files, transforms data via pipelines, generates publication-quality plots
- Strict 3-layer architecture with clean import boundaries

## Technology Stack

| Technology   | Version / Notes                          | Role                              |
|-------------|------------------------------------------|-----------------------------------|
| Python      | 3.12+                                    | Runtime                           |
| Streamlit   | Latest                                   | Web framework, session state      |
| Plotly       | go.Figure-based                         | Primary interactive plotting      |
| Matplotlib   | Secondary engine                        | Static / publication export       |
| Pandas       | DataFrame-centric                       | Data model, transformations       |
| NumPy        | Via Pandas                              | Numeric operations                |
| Perl         | External workers via PerlWorkerPool     | gem5 stats file parsing (54x speedup) |

---

## 3-Layer Architecture

```
+------------------------------------------------------------------+
|                                                                  |
|   LAYER C: WEB (Presentation)          ~120 .py files            |
|                                                                  |
|   pages/ --> controllers/ --> components/ --> rendering/          |
|   models/plot_protocols.py    state/ui_state_manager.py          |
|                                                                  |
+---------------------------+--------------------------------------+
                            |
                            | imports (Web -> Core)
                            v
+------------------------------------------------------------------+
|                                                                  |
|   LAYER B: CORE (Domain)                81 .py files             |
|                                                                  |
|   application_api.py  (FACADE)                                   |
|   services/   models/   state/                                   |
|                                                                  |
+---------------+--------------------------------------------------+
                ^
                | imports (Parsing -> Core)
                |
+------------------------------------------------------------------+
|                                                                  |
|   LAYER A: PARSING (Infrastructure)     36 .py files             |
|                                                                  |
|   parser_protocol.py   registry.py                               |
|   gem5/impl/   gem5/types/   gem5/impl/strategies/               |
|                                                                  |
+------------------------------------------------------------------+
```

| Layer   | Package        | File Count | Responsibility                                    |
|---------|----------------|------------|---------------------------------------------------|
| Core    | `src/core/`    | 81         | Models, Services, State, ApplicationAPI facade     |
| Parsing | `src/parsing/` | 36         | gem5 parser, scanner, Perl integration             |
| Web     | `src/web/`     | ~120       | Streamlit pages, components, controllers, rendering|

---

## Import Rule

```
Web  ---imports--->  Core  <---imports---  Parsing
 |                    |
 | NEVER imports      | 3 deliberate imports from Parsing
 | from Parsing       | (parser_protocol, registry only)
 v                    v
(Web -> Core ONLY)   (Core -> Parsing: facade bridge only)
```

- **Web -> Core**: ~97 import lines (expected, heaviest coupling)
- **Parsing -> Core**: 28 imports (models and utilities)
- **Core -> Parsing**: 3 imports in `src/core/application_api.py` only
- **Web -> Parsing**: ZERO
- **Parsing -> Web**: ZERO
- **Core -> Web**: ZERO

The 3 Core-to-Parsing imports in `src/core/application_api.py`:

```python
# src/core/application_api.py lines 54-55
from src.parsing.parser_protocol import SimulationParser
from src.parsing.registry import SimulatorInfo, SimulatorRegistry
```

---

## Entry Point Chain

```
app.py
  |
  +-- run_app()
       |
       +-- @st.cache_resource
       |     def get_api() -> ApplicationAPI
       |       return ApplicationAPI(plot_deserializer=BasePlot.from_dict)
       |
       +-- st.session_state.api = api   (singleton access for all pages)
       |
       +-- Sidebar navigation (5 pages, lazy imports)
       |
       +-- Page routing: if/elif on st.session_state["_nav_page"]
             |
             +-- DataSourcePage(api).render()
             +-- show_data_managers_page(api)
             +-- show_manage_plots_page(api)
             +-- show_portfolio_page(api)
             +-- show_documentation_page()
```

Key signatures from `app.py`:

```python
# app.py line 54-56
@st.cache_resource(show_spinner="Initializing RING-5...")
def get_api() -> ApplicationAPI:
    return ApplicationAPI(plot_deserializer=BasePlot.from_dict)
```

---

## ApplicationAPI Constructor Wiring

```python
# src/core/application_api.py lines 72-96
class ApplicationAPI:
    def __init__(
        self,
        plot_deserializer: PlotDeserializer | None = None,
        parser: SimulationParser | None = None,
    ) -> None:
        self.state_manager = RepositoryStateManager(
            plot_deserializer=plot_deserializer
        )
        self._services = DefaultServicesAPI(self.state_manager)
        self._parser: SimulationParser = (
            parser or SimulatorRegistry.get_parser("gem5")
        )
```

Object graph created by `ApplicationAPI.__init__`:

```
ApplicationAPI
  |
  +-- self.state_manager = RepositoryStateManager(plot_deserializer)
  |     |
  |     +-- self._session_repo = SessionRepository(plot_deserializer)
  |           |
  |           +-- DataRepository
  |           +-- ConfigRepository
  |           +-- ParserStateRepository
  |           +-- PlotRepository
  |           +-- PreviewRepository
  |           +-- HistoryRepository
  |           +-- VisualizationRepository
  |
  +-- self._services = DefaultServicesAPI(state_manager)
  |     |
  |     +-- self._managers = DefaultManagersAPI()
  |     +-- self._data_services = DefaultDataServicesAPI(state_manager)
  |     +-- self._shapers = DefaultShapersAPI(PathService.get_pipelines_dir())
  |
  +-- self._parser = SimulatorRegistry.get_parser("gem5")
        |
        +-- Gem5ParserAPI()  (lazy-created via registry factory)
```

Sub-API access via properties:

```python
# src/core/application_api.py lines 102-115
@property
def managers(self) -> ManagersAPI: ...
@property
def data_services(self) -> DataServicesAPI: ...
@property
def shapers(self) -> ShapersAPI: ...
```

---

## 5 Pages

| Page              | Module                                           | Entry Signature                                  | Purpose                            |
|-------------------|--------------------------------------------------|--------------------------------------------------|------------------------------------|
| Data Source       | `src/web/pages/data_source.py`                   | `DataSourcePage(api).render()`                   | Scan/parse gem5 stats, load CSV    |
| Data Managers     | `src/web/pages/data_managers.py`                 | `show_data_managers_page(api)`                   | Preprocess, reduce seeds, outliers |
| Manage Plots      | `src/web/pages/manage_plots.py`                 | `show_manage_plots_page(api)`                    | Create/configure/render plots      |
| Save/Load Portfolio | `src/web/pages/portfolio.py`                  | `show_portfolio_page(api)`                       | Workspace save/restore             |
| Documentation     | `src/web/pages/documentation.py`                 | `show_documentation_page()`                      | In-app docs (no API needed)        |

---

## 19 Protocols

### Core Layer (7 Protocols)

| Protocol           | File                                                    | Methods | Purpose                                                |
|--------------------|---------------------------------------------------------|---------|--------------------------------------------------------|
| `StateManager`     | `src/core/state/state_manager.py`                       | 40+     | Full state management contract (data, config, plots)   |
| `PlotProtocol`     | `src/core/models/plot_protocol.py`                      | 1 + 9 attrs | Decouples Core from Web BasePlot                   |
| `PlotDeserializer` | `src/core/models/plot_protocol.py`                      | 1 (`__call__`) | dict -> PlotProtocol callable type              |
| `ServicesAPI`      | `src/core/services/services_api.py`                     | 3 props | Unified facade: managers, data_services, shapers       |
| `DataServicesAPI`  | `src/core/services/data_services/data_services_api.py`  | 25+     | CSV pool, config, variables, portfolio                 |
| `ManagersAPI`      | `src/core/services/managers/managers_api.py`             | 8       | Arithmetic, outlier, reduction operations              |
| `ShapersAPI`       | `src/core/services/shapers/shapers_api.py`              | 7       | Pipeline CRUD + shaper execution                       |

### Parsing Layer (2 Protocols)

| Protocol              | File                                                        | Methods | Purpose                                |
|-----------------------|-------------------------------------------------------------|---------|----------------------------------------|
| `SimulationParser`    | `src/parsing/parser_protocol.py`                            | 4       | Parser contract for simulator backends |
| `FileParserStrategy`  | `src/parsing/gem5/impl/strategies/file_parser_strategy.py`  | 3       | Strategy for file-level parsing        |

### Web Layer (10 Protocols)

| Protocol                 | File                                                             | Methods | Purpose                              |
|--------------------------|------------------------------------------------------------------|---------|--------------------------------------|
| `PlotHandle`             | `src/web/models/plot_protocols.py`                               | attrs only | Read access to plot identity/state|
| `ConfigRenderer`         | `src/web/models/plot_protocols.py`                               | 4       | Plot-specific config UI rendering    |
| `RenderablePlot`         | `src/web/models/plot_protocols.py`                               | composite | PlotHandle + ConfigRenderer        |
| `PlotLifecycleService`   | `src/web/models/plot_protocols.py`                               | 4       | Plot CRUD operations                 |
| `PlotTypeRegistry`       | `src/web/models/plot_protocols.py`                               | 1       | Plot type discovery                  |
| `PipelineExecutor`       | `src/web/models/plot_protocols.py`                               | 2       | apply_shapers, configure_shaper      |
| `SpecificOptionsRenderer`| `src/web/models/plot_protocols.py`                               | 1       | Plot-type-specific options UI        |
| `ReferenceLineRenderer`  | `src/web/components/plotting/settings/advanced_settings.py`      | 1       | Reference line UI callback           |
| `ShapesRenderer`         | `src/web/components/plotting/settings/advanced_settings.py`      | 1       | Shapes UI callback                   |
| `EngineControlsRenderer` | `src/web/components/plotting/settings/advanced_settings.py`      | 1       | Engine-specific controls callback    |

---

## 4 Factories

| Factory           | File                                                    | Layer   | Creation Signature                                                    |
|-------------------|---------------------------------------------------------|---------|-----------------------------------------------------------------------|
| `ShaperFactory`   | `src/core/services/shapers/factory.py`                  | Core    | `create_shaper(shaper_type: str, params: ShaperStepConfig) -> Shaper` |
| `StrategyFactory` | `src/parsing/gem5/impl/strategies/factory.py`           | Parsing | `create(strategy_type: str) -> FileParserStrategy`                    |
| `PlotFactory`     | `src/web/pages/ui/plotting/plot_factory.py`             | Web     | `create_plot(plot_type: str, plot_id: int, name: str) -> BasePlot`    |
| `StyleUIFactory`  | `src/web/pages/ui/plotting/styles/factory.py`           | Web     | `get_strategy(plot_id: int, plot_type: str) -> BaseStyleUI`           |

### ShaperFactory Registered Types (10)

| Key                | Class              | Module                                                            |
|--------------------|--------------------|-------------------------------------------------------------------|
| `mean`             | `Mean`             | `src/core/services/shapers/impl/mean.py`                          |
| `columnSelector`   | `ColumnSelector`   | `src/core/services/shapers/impl/selector_algorithms/column_selector.py` |
| `conditionSelector`| `ConditionSelector`| `src/core/services/shapers/impl/selector_algorithms/condition_selector.py` |
| `itemSelector`     | `ItemSelector`     | `src/core/services/shapers/impl/selector_algorithms/item_selector.py` |
| `normalize`        | `Normalize`        | `src/core/services/shapers/impl/normalize.py`                     |
| `pivotLonger`      | `PivotLonger`      | `src/core/services/shapers/impl/pivot.py`                         |
| `pivotWider`       | `PivotWider`       | `src/core/services/shapers/impl/pivot.py`                         |
| `sort`             | `Sort`             | `src/core/services/shapers/impl/sort.py`                          |
| `splitApply`       | `SplitApply`       | `src/core/services/shapers/impl/split_apply.py`                   |
| `transformer`      | `Transformer`      | `src/core/services/shapers/impl/transformer.py`                   |

### PlotFactory Registered Types (9)

| Key                    | Class                   | Module                                                         |
|------------------------|-------------------------|----------------------------------------------------------------|
| `bar`                  | `BarPlot`               | `src/web/pages/ui/plotting/types/bar_plot.py`                  |
| `line`                 | `LinePlot`              | `src/web/pages/ui/plotting/types/line_plot.py`                 |
| `scatter`              | `ScatterPlot`           | `src/web/pages/ui/plotting/types/scatter_plot.py`              |
| `histogram`            | `HistogramPlot`         | `src/web/pages/ui/plotting/types/histogram_plot.py`            |
| `heatmap`              | `HeatmapPlot`           | `src/web/pages/ui/plotting/types/heatmap_plot.py`              |
| `grouped_bar`          | `GroupedBarPlot`        | `src/web/pages/ui/plotting/types/grouped_bar_plot.py`          |
| `stacked_bar`          | `StackedBarPlot`        | `src/web/pages/ui/plotting/types/stacked_bar_plot.py`          |
| `grouped_stacked_bar`  | `GroupedStackedBarPlot` | `src/web/pages/ui/plotting/types/grouped_stacked_bar_plot.py`  |
| `dual_axis_bar_dot`    | `DualAxisBarDotPlot`    | `src/web/pages/ui/plotting/types/dual_axis_bar_dot_plot.py`    |

### StrategyFactory Registered Types (2)

| Key              | Class                  | Module                                                     |
|------------------|------------------------|------------------------------------------------------------|
| `simple`         | `SimpleStatsStrategy`  | `src/parsing/gem5/impl/strategies/simple.py`               |
| `config_aware`   | `ConfigAwareStrategy`  | `src/parsing/gem5/impl/strategies/config_aware.py`         |

### StyleUIFactory Dispatch Rules

| Condition                  | Class            | Module                                             |
|----------------------------|------------------|----------------------------------------------------|
| `plot_type == "dual_axis_bar_dot"` | `BaseStyleUI`    | `src/web/pages/ui/plotting/styles/base_ui.py` |
| `"line" in plot_type`      | `LineStyleUI`    | `src/web/pages/ui/plotting/styles/line_ui.py`      |
| `"scatter" in plot_type`   | `ScatterStyleUI` | `src/web/pages/ui/plotting/styles/line_ui.py`      |
| `"bar" in plot_type`       | `BarStyleUI`     | `src/web/pages/ui/plotting/styles/bar_ui.py`       |
| fallback                   | `BaseStyleUI`    | `src/web/pages/ui/plotting/styles/base_ui.py`      |

---

## 4 Registries

| Registry                        | File                                           | Layer   | Items Registered                                      | Discovery              |
|---------------------------------|------------------------------------------------|---------|-------------------------------------------------------|------------------------|
| `ShaperFactory._registry`       | `src/core/services/shapers/factory.py`         | Core    | 10 shaper classes                                     | Static dict + `register()` classmethod |
| `SimulatorRegistry`             | `src/parsing/registry.py`                      | Parsing | Simulator backends (gem5)                             | Auto-register on import |
| `StatTypeRegistry`              | `src/parsing/gem5/types/__init__.py`           | Parsing | 5 stat types (scalar, vector, distribution, histogram, configuration) | Self-registering on import |
| `PlotFactory._plot_classes`     | `src/web/pages/ui/plotting/plot_factory.py`    | Web     | 9 plot types                                          | Static dict + `register_plot_type()` |

### SimulatorRegistry Signature

```python
# src/parsing/registry.py
class SimulatorRegistry:
    _registry: dict[str, tuple[SimulatorInfo, Callable[[], SimulationParser]]] = {}
    _instances: dict[str, SimulationParser] = {}

    @classmethod
    def register(cls, info: SimulatorInfo, factory: Callable[[], SimulationParser]) -> None: ...
    @classmethod
    def get_parser(cls, name: str) -> SimulationParser: ...
    @classmethod
    def available_simulators(cls) -> list[str]: ...
```

---

## 4 ABCs

| ABC            | File                                                    | Layer   | Abstract Methods                  | Concrete Implementations                    |
|----------------|--------------------------------------------------------|---------|-----------------------------------|---------------------------------------------|
| `Shaper`       | `src/core/services/shapers/shaper.py`                  | Core    | `_verify_params()`, `__call__()`  | Mean, ColumnSelector, ConditionSelector, ItemSelector, Normalize, PivotLonger, PivotWider, Sort, SplitApply, Transformer |
| `Job`          | `src/parsing/gem5/impl/pool/job.py`                    | Parsing | `__call__()`                      | ParseWork, ScanWork                          |
| `BasePlot`     | `src/web/pages/ui/plotting/base_plot.py`               | Web     | `create_traces()`, `get_legend_column()` | BarPlot, LinePlot, ScatterPlot, HistogramPlot, HeatmapPlot, GroupedBarPlot, StackedBarPlot, GroupedStackedBarPlot, DualAxisBarDotPlot |
| `DataManager`  | `src/web/components/data_managers/data_manager.py`     | Web     | `name` (property), `render()`     | Preprocessor, SeedsReducer, OutlierRemover, Mixer |

### ABC Hierarchies

```
Shaper (ABC)                           BasePlot (PlotConfigUIMixin, ABC)
  +-- Mean                               +-- BarPlot
  +-- ColumnSelector                     +-- LinePlot
  +-- ConditionSelector                  +-- ScatterPlot
  +-- ItemSelector                       +-- HistogramPlot
  +-- Normalize                          +-- HeatmapPlot
  +-- PivotLonger                        +-- GroupedBarPlot
  +-- PivotWider                         +-- StackedBarPlot
  +-- Sort                               +-- GroupedStackedBarPlot
  +-- SplitApply                         +-- DualAxisBarDotPlot
  +-- Transformer

Job (ABC)                              DataManager (ABC)
  +-- ParseWork                          +-- Preprocessor
  +-- ScanWork                           +-- SeedsReducer
                                         +-- OutlierRemover
                                         +-- Mixer
```

### Key ABC Signatures

```python
# src/core/services/shapers/shaper.py
class Shaper(ABC):
    def __init__(self, params: dict[str, Any]) -> None: ...
    @abstractmethod
    def _verify_params(self) -> bool: ...
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame: ...

# src/web/pages/ui/plotting/base_plot.py
class BasePlot(PlotConfigUIMixin, ABC):
    def __init__(self, plot_id: int, name: str, plot_type: str) -> None: ...
    @abstractmethod
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult: ...

# src/web/components/data_managers/data_manager.py
class DataManager(ABC):
    def __init__(self, api: ApplicationAPI): ...
    @property
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def render(self) -> None: ...

# src/parsing/gem5/impl/pool/job.py
class Job(ABC):
    @abstractmethod
    def __call__(self) -> Any: ...
```

---

## Session State Singleton Pattern

```
+-------------------+     @st.cache_resource      +-------------------+
|                   | --------------------------> |                   |
|     app.py        |   get_api() returns single  |  ApplicationAPI   |
|                   |   ApplicationAPI instance    |  (singleton)      |
+-------------------+                              +-------------------+
        |                                                  |
        | st.session_state.api = api                       |
        v                                                  v
+-------------------+                              +-------------------+
| All pages access  |                              | All repositories  |
| api via           | --------------------------> | store data in     |
| st.session_state  |                              | st.session_state  |
+-------------------+                              +-------------------+
```

- `@st.cache_resource` ensures one `ApplicationAPI` per Streamlit server process
- `st.session_state.api = api` makes it accessible to all page modules
- All 7 repositories use `st.session_state` as their backing store
- Pages receive `api` as constructor/function argument (not global import)

---

## Package Dependency Graph

```
+------------------------------------------------------------------+
|                     src/web/ (Layer C)                            |
|                                                                  |
|  pages/                                                          |
|    +-- data_source.py                                            |
|    +-- data_managers.py                                          |
|    +-- manage_plots.py                                           |
|    +-- portfolio.py                                              |
|    +-- documentation.py                                          |
|    +-- plot_adapters.py  (BasePlot -> PlotHandle/ConfigRenderer) |
|    +-- ui/plotting/                                              |
|          +-- base_plot.py      (ABC)                             |
|          +-- plot_factory.py   (Factory)                         |
|          +-- plot_renderer.py                                    |
|          +-- settings_pills.py                                   |
|          +-- types/            (9 plot types)                    |
|          +-- styles/           (StyleUIFactory)                  |
|          +-- export/presets/                                     |
|                                                                  |
|  controllers/plot/                                               |
|    +-- creation_controller.py                                    |
|    +-- pipeline_controller.py                                    |
|    +-- render_controller.py                                      |
|                                                                  |
|  components/                                                     |
|    +-- common/          (12 reusable components)                 |
|    +-- data_source/     (scan/parse UI)                          |
|    +-- data_managers/   (DataManager ABC + 4 managers)           |
|    +-- shapers/         (6 shaper config UIs)                    |
|    +-- plotting/                                                 |
|          +-- interactive_plot.py                                 |
|          +-- config/    (10 config components)                   |
|          +-- settings/  (11 settings panels + widget_factory)    |
|                                                                  |
|  rendering/                                                      |
|    +-- config_builder.py                                         |
|    +-- plotly_connector.py                                       |
|    +-- matplotlib_connector.py                                   |
|    +-- trace_to_plotly.py                                        |
|    +-- engine_manager.py                                         |
|    +-- preset_applicator.py                                      |
|    +-- widgets/                                                  |
|                                                                  |
|  models/                                                         |
|    +-- plot_protocols.py   (10 Protocols)                        |
|    +-- plot_models.py                                            |
|                                                                  |
|  state/                                                          |
|    +-- ui_state_manager.py                                       |
|                                                                  |
+------+-----------+----------+------------------------------------+
       |           |          |
       v           v          v
+------------------------------------------------------------------+
|                    src/core/ (Layer B)                            |
|                                                                  |
|  application_api.py  (FACADE -- single entry point for Web)      |
|                                                                  |
|  services/                                                       |
|    +-- services_api.py      (ServicesAPI Protocol)               |
|    +-- services_impl.py     (DefaultServicesAPI)                 |
|    +-- managers/             (ManagersAPI + DefaultManagersAPI)   |
|    +-- data_services/        (DataServicesAPI + impl + 6 svcs)   |
|    +-- shapers/              (ShapersAPI + factory + 10 shapers) |
|    +-- visualization/        (resolver, palette, interaction)    |
|                                                                  |
|  models/                                                         |
|    +-- plot_protocol.py      (PlotProtocol, PlotDeserializer)    |
|    +-- data_models.py        parsing_models.py  shaper_models.py |
|    +-- history_models.py     portfolio_models.py  csv_contract.py|
|    +-- visualization/        (13 config models)                  |
|                                                                  |
|  state/                                                          |
|    +-- state_manager.py             (StateManager Protocol)      |
|    +-- repository_state_manager.py  (concrete implementation)    |
|    +-- repositories/                (7 child repositories)       |
|          +-- session_repository.py  (AGGREGATE ROOT)             |
|          +-- data_repository.py                                  |
|          +-- config_repository.py                                |
|          +-- parser_state_repository.py                          |
|          +-- plot_repository.py                                  |
|          +-- preview_repository.py                               |
|          +-- history_repository.py                               |
|          +-- visualization_repository.py                         |
|                                                                  |
+------+-----------------------------------------------------------+
       ^
       |  imports (Parsing -> Core: models + utilities)
       |
+------------------------------------------------------------------+
|                   src/parsing/ (Layer A)                          |
|                                                                  |
|  parser_protocol.py      (SimulationParser Protocol)             |
|  registry.py             (SimulatorRegistry + SimulatorInfo)     |
|  parse_service.py        (shim -> Gem5Parser)                    |
|  scanner_service.py      (shim -> Gem5Scanner)                   |
|                                                                  |
|  gem5/                                                           |
|    +-- impl/                                                     |
|    |     +-- gem5_parser.py       gem5_scanner.py                |
|    |     +-- gem5_parser_api.py                                  |
|    |     +-- pool/                                               |
|    |     |     +-- job.py          (Job ABC)                     |
|    |     |     +-- pool.py         (PerlWorkerPool)              |
|    |     |     +-- work_pool.py    (WorkPool singleton)          |
|    |     |     +-- parse_work.py   scan_work.py                  |
|    |     +-- scanning/                                           |
|    |     |     +-- scanner.py      pattern_aggregator.py         |
|    |     +-- strategies/                                         |
|    |           +-- file_parser_strategy.py  (Protocol)           |
|    |           +-- factory.py      (StrategyFactory)             |
|    |           +-- simple.py       config_aware.py               |
|    +-- types/                                                    |
|          +-- scalar.py  vector.py  distribution.py               |
|          +-- histogram.py  configuration.py                      |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Key Design Patterns Summary

| Pattern             | Location                                          | Mechanism                                      |
|---------------------|---------------------------------------------------|------------------------------------------------|
| Facade              | `src/core/application_api.py`                     | Single entry point for UI -> domain            |
| Repository          | `src/core/state/repositories/`                    | 7 repos behind SessionRepository aggregate     |
| Protocol (DIP)      | All layer boundaries                              | 19 Protocol classes for structural typing       |
| Factory             | Core, Parsing, Web                                | 4 factories with registry + creation           |
| Strategy            | `src/parsing/gem5/impl/strategies/`               | Interchangeable parsing strategies             |
| Command             | `src/parsing/gem5/impl/pool/job.py`               | Job ABC for parallel work units                |
| Singleton           | `app.py` via `@st.cache_resource`                 | One ApplicationAPI per server process          |
| Adapter             | `src/web/pages/plot_adapters.py`                  | BasePlot -> PlotHandle/ConfigRenderer          |
| Lazy Import         | `app.py` page routing                             | Only active page module is loaded              |
| Sentinel Value      | `src/core/models/visualization/resolvers.py`      | -1 means "use engine default"                  |
| Mixin               | `PlotConfigUIMixin` in `BasePlot`                 | Separates plot logic from UI config methods    |

---

## File Count Summary

| Layer      | `.py` Files | Packages | `__init__.py` Files |
|------------|-------------|----------|---------------------|
| Core       | 81          | 12       | 12                  |
| Parsing    | 36          | 8        | 8                   |
| Web        | ~120        | 22       | 22                  |
| **Total**  | **~237**    | **42**   | **42**              |
