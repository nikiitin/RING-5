---
title: "Design Patterns Catalog"
parent: Architecture
grand_parent: AI Knowledge Base
nav_order: 3
---

# Design Patterns Catalog

## Quick Reference

| # | Pattern | GoF Type | Primary Location | Layer |
|---|---------|----------|-----------------|-------|
| 1 | Facade | Structural | `src/core/application_api.py` | Core |
| 2 | Repository | DDD | `src/core/state/repositories/` | Core |
| 3 | Protocol (DI) | Structural | All layer boundaries (19 protocols) | All |
| 4 | Factory | Creational | `src/core/services/shapers/factory.py`, `src/web/pages/ui/plotting/plot_factory.py` | Core, Web |
| 5 | Strategy | Behavioral | `src/parsing/gem5/impl/strategies/` | Parsing |
| 6 | Command | Behavioral | `src/parsing/framework/job.py` | Parsing |
| 7 | Singleton | Creational | `src/parsing/framework/work_pool.py`, `app.py` | Parsing, Entry |
| 8 | Adapter | Structural | `src/web/pages/plot_adapters.py` | Web |
| 9 | Observer | Behavioral | `src/core/state/repositories/data_repository.py` | Core |
| 10 | Sentinel Value | Domain-specific | `src/core/services/visualization/config_resolver.py` | Core |
| 11 | Mixin | Python-specific | `src/web/pages/ui/plotting/plot_config_ui.py` | Web |
| 12 | Lazy Import | Python-specific | `app.py`, `src/web/pages/ui/plotting/base_plot.py` | Entry, Web |

---

## 1. Facade

**Location:** `src/core/application_api.py` -- `ApplicationAPI` (~429 lines)

| When to Use | When NOT to Use |
|-------------|-----------------|
| UI page needs multi-step orchestration (load + state update) | Single stateless transformation (call sub-API directly) |
| New cross-cutting operation spanning services | Direct model access |

```python
# src/core/application_api.py
class ApplicationAPI:
    def __init__(self, plot_deserializer=None, parser=None):
        self.state_manager = RepositoryStateManager(plot_deserializer=plot_deserializer)
        self._services = DefaultServicesAPI(self.state_manager)
        self._parser = parser or SimulatorRegistry.get_parser("gem5")

    @property
    def managers(self) -> ManagersAPI: return self._services.managers
    @property
    def data_services(self) -> DataServicesAPI: return self._services.data_services
```

**Related:** Protocol (DI) for constructor args, Singleton via `@st.cache_resource`, Repository as composed state

---

## 2. Repository

**Location:** `src/core/state/repositories/` -- 7 child repos + `SessionRepository` aggregate root

| When to Use | When NOT to Use |
|-------------|-----------------|
| New persistent state category | Temporary UI-only state (use `st.session_state` directly) |
| Isolating storage mechanism from business logic | One-off computed values |

```
SessionRepository (aggregate root)
  +-- DataRepository          +-- ConfigRepository       +-- ParserStateRepository
  +-- PlotRepository          +-- PreviewRepository      +-- HistoryRepository
  +-- VisualizationRepository
```

```python
# src/core/state/repositories/data_repository.py
class DataRepository:
    def __init__(self):
        self._data: pd.DataFrame | None = None

    def set_data(self, data, on_change=None):
        self._data = data
        if on_change:
            on_change()
```

**Related:** Facade delegates through `RepositoryStateManager`, Observer via `on_change`, Protocol defines `StateManager` contract

---

## 3. Protocol (Dependency Inversion)

**Location:** All layer boundaries -- 19 `typing.Protocol` classes

| When to Use | When NOT to Use (use ABC instead) |
|-------------|----------------------------------|
| Cross-layer boundary contract | Shared implementation needed |
| Testable interface (mock without subclass) | Template Method pattern |
| Single-method callback contract | Need `__init__` enforcement |

**Key protocols:**

| Protocol | File | Boundary |
|----------|------|----------|
| `PlotProtocol` | `src/core/models/plot_protocol.py` | Core <-> Web |
| `SimulationParser` | `src/parsing/parser_protocol.py` | Core <-> Parsing |
| `ServicesAPI` | `src/core/services/services_api.py` | Core internal |
| `FileParserStrategy` | `src/parsing/gem5/impl/strategies/file_parser_strategy.py` | Parsing internal |
| `PlotHandle` | `src/web/models/plot_protocols.py` | Web internal |

```python
# src/core/models/plot_protocol.py
@runtime_checkable
class PlotProtocol(Protocol):
    plot_id: int
    name: str
    plot_type: str
    config: dict[str, Any]
    def to_dict(self) -> dict[str, Any]: ...

PlotDeserializer = Callable[[dict[str, Any]], PlotProtocol | None]
```

**Related:** Facade accepts protocol-typed args, Factory creates objects satisfying protocols, Adapter wraps classes to match protocols

---

## 4. Factory

**Locations:** 4 factories across all layers

| Factory | File | Registration | Creates |
|---------|------|-------------|---------|
| `ShaperFactory` | `src/core/services/shapers/factory.py` | `register(type_id, class)` | `Shaper` subclasses (10 types) |
| `PlotFactory` | `src/web/pages/ui/plotting/plot_factory.py` | `register_plot_type(id, class, meta)` | `BasePlot` subclasses (9 types) |
| `StrategyFactory` | `src/parsing/gem5/impl/strategies/factory.py` | Name-to-class mapping | `FileParserStrategy` impls |
| `StyleUIFactory` | `src/web/pages/ui/plotting/styles/factory.py` | Conditional logic (not extensible) | `BaseStyleUI` subclasses |

```python
# src/core/services/shapers/factory.py
class ShaperFactory:
    _registry: dict[str, type[Shaper]] = {"mean": Mean, "sort": Sort, ...}  # 10 total

    @classmethod
    def register(cls, shaper_type: str, shaper_class: type[Shaper]) -> None:
        cls._registry[shaper_type] = shaper_class

    @classmethod
    def create_shaper(cls, shaper_type: str, params: ShaperStepConfig) -> Shaper:
        shaper_class = cls._registry.get(shaper_type)
        if shaper_class is None:
            raise ValueError(f"Unknown shaper type '{shaper_type}'.")
        return shaper_class(dict(params))
```

**Related:** Strategy instances created by factories, Singleton registries (class-level dicts), Protocol contracts on created objects

---

## 5. Strategy

**Location:** `src/parsing/gem5/impl/strategies/`

| When to Use | When NOT to Use |
|-------------|-----------------|
| Multiple algorithms for same operation | Single algorithm with no variants |
| Algorithm selected at runtime by user | Compile-time choice |

| Strategy Protocol | Implementations | Selection |
|------------------|-----------------|-----------|
| `FileParserStrategy` | `SimpleStatsStrategy`, `ConfigAwareStrategy` | `StrategyFactory` by name |
| `BaseStyleUI` (ABC) | `BarStyleUI`, `LineStyleUI`, `ScatterStyleUI` | `StyleUIFactory.get_strategy()` |

```python
# src/parsing/gem5/impl/strategies/file_parser_strategy.py
class FileParserStrategy(Protocol):
    def execute(self, stats_path, stats_pattern, variables) -> list[dict[str, Any]]: ...
    def get_work_items(self, stats_path, stats_pattern, variables) -> Sequence[ParseWork]: ...
    def post_process(self, results) -> list[dict[str, Any]]: ...
```

**Related:** Factory creates strategies, Protocol defines contract, Command objects produced by `get_work_items()`

---

## 6. Command

**Location:** `src/parsing/framework/job.py` (ABC), `parse_work.py`, `scan_work.py`

| When to Use | When NOT to Use |
|-------------|-----------------|
| Parallel/deferred execution via pool | Synchronous one-shot call |
| Need to queue, serialize, or retry work | Simple function call |

```python
# src/parsing/framework/job.py
class Job(ABC):
    @abstractmethod
    def __call__(self) -> Any:
        """Execute the job logic."""

# src/parsing/gem5/impl/pool/parse_work.py
class ParseWork(Job):
    def __call__(self) -> ParsedVarsDict:
        raise NotImplementedError("Subclass must implement __call__")
```

**Related:** Strategy produces commands via `get_work_items()`, Singleton `WorkPool` executes them

---

## 7. Singleton

**Locations:** `WorkPool` (thread-safe `__new__`), `ApplicationAPI` (Streamlit `@st.cache_resource`)

| Variant | When to Use |
|---------|-------------|
| `@st.cache_resource` | App-level shared resource across Streamlit reruns |
| `__new__` + lock | Process/thread pool requiring exactly one instance |
| Class-level `dict` | Factory registries (implicit singleton state) |

```python
# src/parsing/framework/work_pool.py
class WorkPool:
    _instance: WorkPool | None = None
    _new_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> WorkPool:
        with cls._new_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

# app.py
@st.cache_resource(show_spinner="Initializing RING-5...")
def get_api() -> ApplicationAPI:
    return ApplicationAPI(plot_deserializer=BasePlot.from_dict)
```

**Related:** Facade is the primary singleton, Command submitted to singleton pool

---

## 8. Adapter

**Location:** `src/web/pages/plot_adapters.py`

| When to Use | When NOT to Use |
|-------------|-----------------|
| Controller expects protocol, impl is static/class methods | Class already satisfies protocol structurally |
| Wrapping standalone functions into instance-method interface | Direct delegation without interface mismatch |

| Adapter | Wraps | Satisfies Protocol |
|---------|-------|-------------------|
| `PlotLifecycleAdapter` | `PlotService` static methods | `PlotLifecycleService` |
| `PlotTypeRegistryAdapter` | `PlotFactory` class methods | `PlotTypeRegistry` |
| `PipelineExecutorAdapter` | `apply_shapers()` function | `PipelineExecutor` |

```python
# src/web/pages/plot_adapters.py
class PlotLifecycleAdapter:
    def create_plot(self, name, plot_type, state_manager) -> PlotHandle:
        return PlotService.create_plot(name, plot_type, state_manager)

    def delete_plot(self, plot_id, state_manager) -> None:
        PlotService.delete_plot(plot_id, state_manager)
```

**Related:** Protocol defines the target contract, Facade for subsystem simplification

---

## 9. Observer

**Location:** `src/core/state/repositories/data_repository.py`

| When to Use | When NOT to Use |
|-------------|-----------------|
| State change should trigger derived state cleanup | UI reactivity (Streamlit reruns handle this) |
| One-shot callback on mutation | Multi-subscriber notification (not supported) |

```python
# src/core/state/repositories/data_repository.py
def set_data(self, data, on_change: Callable[[], None] | None = None):
    self._data = data
    if on_change:
        on_change()
# Usage: data_repo.set_data(new_df, on_change=lambda: preview_repo.clear_all())
```

**Related:** Repository provides the mutation methods, Facade orchestrates callback wiring

---

## 10. Sentinel Value

**Location:** `src/core/services/visualization/config_resolver.py`

| Use Sentinel (`-1`) | Use `None` | Use default value |
|---------------------|-----------|-------------------|
| Field should inherit from parent in hierarchy | Field is truly optional/absent | Field has a fixed fallback |

```
font_size_ylabel --> font_size_y2label
font_size_ticks --> font_size_yticks --> font_size_y2ticks
font_size_legend --> font_size_legend2
```

```python
# src/core/services/visualization/config_resolver.py
SENTINEL_INT: int = -1
SENTINEL_FLOAT: float = -1.0

def resolve_config(spec: FigureConfig) -> FigureConfig:
    out = deepcopy(spec)  # pure function, never mutates input
    _resolve_typography(out)
    _resolve_legends(out)
    _resolve_axes(out)
    return out
```

**Related:** Consumed by rendering Strategy (both Plotly and Matplotlib connectors)

---

## 11. Mixin

**Location:** `src/web/pages/ui/plotting/plot_config_ui.py` -- `PlotConfigUIMixin`

| When to Use | When NOT to Use |
|-------------|-----------------|
| Shared behavior across sibling classes needing host attributes | Deep inheritance (prefer composition) |
| Separating orthogonal concerns (plot logic vs UI rendering) | Standalone reusable utility (use module functions) |

```python
# src/web/pages/ui/plotting/plot_config_ui.py
class PlotConfigUIMixin:
    """Expects self.plot_id, self.plot_type, self.config, self._style_ui from host."""
    plot_id: int
    plot_type: str

    def render_settings_section(self, section, saved_config, data=None):
        if section == "layout":
            return LayoutSettingsComponent(self.plot_id, self.plot_type).render(saved_config)
        # ... dispatches to 7 settings components

# src/web/pages/ui/plotting/base_plot.py
class BasePlot(PlotConfigUIMixin, ABC):  # mixin + ABC = concrete plots inherit both
    def __init__(self, plot_id, name, plot_type):
        self.plot_id = plot_id
        self._style_ui = StyleUIFactory.get_strategy(self.plot_id, self.plot_type)
```

**Related:** Factory creates `BasePlot` subclasses containing the mixin, Strategy for style dispatch

---

## 12. Lazy Import

**Locations:** `app.py` (page routing), `src/web/pages/ui/plotting/base_plot.py` (rendering), `src/parsing/registry.py` (parser factories)

| When to Use | When NOT to Use |
|-------------|-----------------|
| Page module only needed when its nav tab is active | Module always needed on every rerun |
| Import would create circular dependency | No circular risk and module is lightweight |
| Heavy third-party lib used in one code path | Module used in all code paths |

```python
# app.py -- only active page module loaded per Streamlit rerun
if page == "Data Source":
    from src.web.pages.data_source import DataSourcePage
    DataSourcePage(api).render()

# src/web/pages/ui/plotting/base_plot.py -- deferred rendering import
def create_figure(self, data, config) -> go.Figure:
    from src.web.rendering.trace_to_plotly import traces_to_plotly
    return traces_to_plotly(self.create_traces(data, config))

# src/parsing/registry.py -- lazy parser class import in factory callable
def _create_gem5_parser() -> SimulationParser:
    from src.parsing.gem5.impl.gem5_parser import Gem5Parser
    return Gem5Parser()
```

**Related:** Singleton combines with lazy import for one-time init, Factory callables use lazy imports

---

## Pattern Interaction Map

```
Facade (ApplicationAPI)
  |-- composes --> Repository (SessionRepository + 7 children)
  |-- accepts  --> Protocol (PlotDeserializer, SimulationParser)
  |-- created via --> Singleton (@st.cache_resource)
  |-- delegates to --> Factory (ShaperFactory via ShapersAPI)
  +-- Strategy (FileParserStrategy)
  |     +-- produces --> Command (ParseWork, ScanWork)
  |     +-- submitted to --> Singleton (WorkPool)
  +-- Adapter (PlotLifecycleAdapter, PipelineExecutorAdapter)
  |     +-- satisfies --> Protocol (PlotLifecycleService, PipelineExecutor)
  +-- Mixin (PlotConfigUIMixin) --> mixed into Factory product (BasePlot)
  +-- Sentinel Value (config_resolver) --> resolves FigureConfig tree
  +-- Observer (on_change) --> attached to Repository mutations
  +-- Lazy Import --> defers page modules, rendering, parser classes
```

## Anti-Pattern Guidance

| Do NOT | Do Instead | Reason |
|--------|-----------|--------|
| Import web-layer classes in core | Define Protocol in core; inject impl at startup | Maintains `Web -> Core <- Parsing` direction |
| Use `__new__` singleton for app state | Use `@st.cache_resource` + `st.session_state` | Streamlit manages lifecycle |
| Add conditionals to `StyleUIFactory` | Convert to registry-based factory | Current conditional form is not extensible |
| Use `None` for "inherit from parent" | Use sentinel `-1` / `-1.0` | `None` = absent; sentinel = inherit (distinct semantics) |
| Put UI methods on `BasePlot` directly | Add to `PlotConfigUIMixin` | Separates lifecycle from rendering concerns |
