# Design Patterns Catalog

This document catalogs the 12 design patterns used in the RING-5 Unified Engine v2
codebase. Each entry identifies the GoF classification, the files where the pattern
is implemented, how it works with concrete code references, why it was chosen, and
which other patterns it collaborates with.

---

## 1. Facade

**GoF Classification:** Structural

**Location:** `src/core/application_api.py` -- class `ApplicationAPI` (lines 60--429)

**Implementation.**
`ApplicationAPI` is the single entry point through which the entire web layer
accesses business logic. It composes four internal subsystems and exposes
high-level, use-case-oriented methods so that pages never import services or
repositories directly.

```python
# src/core/application_api.py:60-96
class ApplicationAPI:
    def __init__(
        self,
        plot_deserializer: PlotDeserializer | None = None,
        parser: SimulationParser | None = None,
    ) -> None:
        self.state_manager = RepositoryStateManager(plot_deserializer=plot_deserializer)
        self._services = DefaultServicesAPI(self.state_manager)
        self._parser: SimulationParser = parser or SimulatorRegistry.get_parser("gem5")

    @property
    def managers(self) -> ManagersAPI:
        return self._services.managers

    @property
    def data_services(self) -> DataServicesAPI:
        return self._services.data_services

    @property
    def shapers(self) -> ShapersAPI:
        return self._services.shapers
```

Pages interact with the facade by receiving it as a constructor or function argument:

```python
# app.py:138-141
if page == "Data Source":
    from src.web.pages.data_source import DataSourcePage
    DataSourcePage(api).render()
```

**Design Rationale.**
A facade enforces the architectural boundary between the presentation and domain
layers. Without it, every page and component would import services and
repositories individually, creating a web of cross-layer dependencies. The
facade also provides a natural place for orchestration logic -- for example,
`load_data()` coordinates loading via `DataServicesAPI`, then persists the
result via `RepositoryStateManager`, then resets derived state.

**Related Patterns:** Singleton (the facade itself is cached as a singleton),
Protocol (the facade depends on `ServicesAPI`, `SimulationParser`, and
`PlotDeserializer` protocols rather than concrete classes).

---

## 2. Repository

**GoF Classification:** Enterprise / Domain-Driven Design (not in the original
GoF catalog; classified under the Repository pattern from Fowler's PoEAA)

**Location:** `src/core/state/repositories/` -- 8 files

**Implementation.**
Application state is abstracted behind repository interfaces.
`SessionRepository` acts as the aggregate root, composing seven child
repositories. Each child has a single responsibility: one slice of session
state.

```python
# src/core/state/repositories/session_repository.py:26-54
class SessionRepository:
    def __init__(self, plot_deserializer: PlotDeserializer | None = None) -> None:
        self.data_repo = DataRepository()
        self.plot_repo = PlotRepository()
        self.parser_repo = ParserStateRepository()
        self.config_repo = ConfigRepository()
        self.preview_repo = PreviewRepository()
        self.history_repo = HistoryRepository()
        self.visualization_repo = VisualizationRepository()
        self._plot_deserializer = plot_deserializer
```

`RepositoryStateManager` wraps the aggregate root and implements the
`StateManager` protocol by delegating to the appropriate child repository:

```python
# src/core/state/repository_state_manager.py:61-62
def get_data(self) -> pd.DataFrame | None:
    return self._session_repo.data_repo.get_data()
```

Each child repository is a plain Python class with in-memory storage. For
example, `DataRepository` holds a raw DataFrame and a processed DataFrame:

```python
# src/core/state/repositories/data_repository.py:27-29
class DataRepository:
    def __init__(self) -> None:
        self._data: pd.DataFrame | None = None
        self._processed_data: pd.DataFrame | None = None
```

The seven child repositories and their domains are:

| Repository | Domain |
|---|---|
| `DataRepository` | Raw and processed DataFrames |
| `ConfigRepository` | Configuration dict, CSV path, temp directory |
| `ParserStateRepository` | Variables, patterns, strategies, simulator |
| `PlotRepository` | Plots list, current plot, counter |
| `PreviewRepository` | Operation preview DataFrames |
| `HistoryRepository` | Manager and portfolio operation history |
| `VisualizationRepository` | CSV pool, saved visualization configs |

**Design Rationale.**
Splitting state into focused repositories keeps each class small and testable.
The aggregate-root pattern prevents inconsistent partial updates -- for example,
`clear_all()` on `SessionRepository` ensures every child is reset in one call.
The in-memory backing store can later be swapped for `st.session_state` or a
database without changing the `StateManager` protocol contract.

**Related Patterns:** Protocol (the `StateManager` protocol decouples
consumers from `RepositoryStateManager`), Facade (`ApplicationAPI` delegates
state operations to this layer).

---

## 3. Protocol (Dependency Inversion)

**GoF Classification:** Structural -- analogous to the Interface / Abstract
Interface role in GoF terminology, applied here through Python's structural
typing system.

**Location:** 19 Protocol classes distributed across all three layers.
Core: `src/core/state/state_manager.py`, `src/core/models/plot_protocol.py`,
`src/core/services/services_api.py`. Parsing:
`src/parsing/parser_protocol.py`,
`src/parsing/gem5/impl/strategies/file_parser_strategy.py`. Web:
`src/web/models/plot_protocols.py`.

**Implementation.**
Every layer boundary is spanned by a Protocol rather than a concrete import.
The core layer defines `StateManager`, `ServicesAPI`, `PlotProtocol`, and
`PlotDeserializer`. Concrete implementations live in other packages.

```python
# src/core/state/state_manager.py:27-28
@runtime_checkable
class StateManager(Protocol):
    def get_data(self) -> pd.DataFrame | None: ...
    def set_data(self, data: pd.DataFrame | None,
                 on_change: Callable[[], None] | None = None) -> None: ...
    # ... 40+ methods
```

```python
# src/core/models/plot_protocol.py:17-41
@runtime_checkable
class PlotProtocol(Protocol):
    plot_id: int
    name: str
    plot_type: str
    config: dict[str, Any]
    # ...
    def to_dict(self) -> dict[str, Any]: ...

PlotDeserializer = Callable[[dict[str, Any]], PlotProtocol | None]
```

The parsing layer defines `SimulationParser` so that the facade can accept any
backend without importing gem5-specific code:

```python
# src/parsing/parser_protocol.py:7-8
@runtime_checkable
class SimulationParser(Protocol):
    def submit_parse_async(self, ...) -> ParseBatchResult: ...
    def submit_scan_async(self, ...) -> list[Future[list[ScannedVariable]]]: ...
```

The `PlotDeserializer` callable type is injected at startup so that the core
layer can deserialize plots from portfolio data without ever importing
`BasePlot`:

```python
# app.py:56
api = ApplicationAPI(plot_deserializer=BasePlot.from_dict)
```

**Design Rationale.**
Python's `Protocol` provides structural (duck) typing at the interface level
without requiring inheritance. This keeps the core layer completely independent
of the web and parsing layers. The architecture can add a new simulator backend
by implementing `SimulationParser` without modifying any core code.

**Related Patterns:** Facade (protocols define what the facade depends on),
Factory (factories return objects that satisfy protocols), Strategy (strategies
implement the `FileParserStrategy` protocol).

---

## 4. Factory

**GoF Classification:** Creational

**Location:** Four factories across all three layers:

| Factory | File | Registered Types |
|---|---|---|
| `ShaperFactory` | `src/core/services/shapers/factory.py` | 10 shaper types |
| `StrategyFactory` | `src/parsing/gem5/impl/strategies/factory.py` | 2 strategy types |
| `PlotFactory` | `src/web/pages/ui/plotting/plot_factory.py` | 9 plot types |
| `StyleUIFactory` | `src/web/pages/ui/plotting/styles/factory.py` | 4 style UI types |

**Implementation.**
Each factory maintains a registry mapping string identifiers to concrete
classes. The caller passes a type string and receives a fully constructed
instance.

`ShaperFactory` uses a class-level dictionary registry with a `register()`
classmethod for extensibility:

```python
# src/core/services/shapers/factory.py:30-51
class ShaperFactory:
    _registry: dict[str, type[Shaper]] = {
        "mean": Mean,
        "columnSelector": ColumnSelector,
        "sort": Sort,
        "normalize": Normalize,
        # ... 10 total entries
    }

    @classmethod
    def create_shaper(cls, shaper_type: str, params: ShaperStepConfig) -> Shaper:
        shaper_class = cls._registry.get(shaper_type)
        if shaper_class is None:
            raise ValueError(f"Unknown shaper type '{shaper_type}'.")
        return shaper_class(dict(params))
```

`PlotFactory` follows the same pattern for plot types:

```python
# src/web/pages/ui/plotting/plot_factory.py:32-51
class PlotFactory:
    _plot_classes: dict[str, Callable[[int, str], BasePlot]] = {
        "bar": BarPlot,
        "line": LinePlot,
        "scatter": ScatterPlot,
        # ... 9 total entries
    }
```

`StrategyFactory` uses lazy imports inside the creation method to avoid
circular dependencies:

```python
# src/parsing/gem5/impl/strategies/factory.py:20-49
class StrategyFactory:
    @staticmethod
    def create(strategy_type: str) -> FileParserStrategy:
        if strategy_type == "simple":
            from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy
            return SimpleStatsStrategy()
        if strategy_type == "config_aware":
            from src.parsing.gem5.impl.strategies.config_aware import ConfigAwareStrategy
            return ConfigAwareStrategy()
        raise ValueError(f"Unknown strategy type: '{strategy_type}'.")
```

**Design Rationale.**
Factories centralize object creation so that callers never need to know which
concrete class to instantiate. The registry approach obeys the Open/Closed
Principle: adding a new shaper or plot type means adding one entry to the
registry dictionary, with no changes to existing consumer code.

**Related Patterns:** Strategy (factories often create strategy objects),
Protocol (created objects satisfy protocol contracts), Lazy Import
(`StrategyFactory.create()` uses deferred imports).

---

## 5. Strategy

**GoF Classification:** Behavioral

**Location:** `src/parsing/gem5/impl/strategies/` -- `FileParserStrategy`
protocol in `file_parser_strategy.py`, concrete strategies in `simple.py`
and `config_aware.py`

**Implementation.**
The parsing system defines a `FileParserStrategy` protocol with three methods
representing a three-phase parsing workflow: discovery, execution, and post-
processing.

```python
# src/parsing/gem5/impl/strategies/file_parser_strategy.py:25-46
class FileParserStrategy(Protocol):
    def execute(self, stats_path: str, stats_pattern: str,
                variables: list[StatConfig]) -> list[dict[str, Any]]: ...
    def get_work_items(self, stats_path: str, stats_pattern: str,
                       variables: list[StatConfig]) -> Sequence[ParseWork]: ...
    def post_process(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]: ...
```

Two concrete strategies implement this contract:

- **`SimpleStatsStrategy`** -- Parses basic `stats.txt` files. Suitable for
  scalar and vector statistics.
- **`ConfigAwareStrategy`** -- Parses `stats.txt` and augments results with
  data from `config.ini` files. Used when configuration parameters are needed
  alongside performance counters.

The strategy is selected at runtime by name through `StrategyFactory.create()`,
and the gem5 parser delegates to whichever strategy is active:

```python
# Usage in gem5_parser (conceptual flow):
strategy = StrategyFactory.create(strategy_type)  # "simple" or "config_aware"
work_items = strategy.get_work_items(path, pattern, variables)
results = strategy.execute(path, pattern, variables)
final = strategy.post_process(results)
```

**Design Rationale.**
Different gem5 output configurations require different parsing logic.
Encapsulating each algorithm behind a common interface lets users switch
strategies at parse time without touching the parser itself. Adding a new gem5
output format means implementing one new class.

**Related Patterns:** Factory (`StrategyFactory` creates strategies), Protocol
(the strategy contract is a Protocol), Command (each strategy produces
`ParseWork` command objects).

---

## 6. Command

**GoF Classification:** Behavioral

**Location:** `src/parsing/gem5/impl/pool/job.py` -- `Job` ABC (lines 18--29),
`src/parsing/gem5/impl/pool/parse_work.py` -- `ParseWork` (lines 15--53)

**Implementation.**
`Job` is an abstract base class with a single `__call__` method. Concrete
subclasses encapsulate a unit of work that can be submitted to a worker pool
for parallel execution.

```python
# src/parsing/gem5/impl/pool/job.py:18-29
class Job(ABC):
    """Base interface for all parallel tasks. Follows the Command pattern."""

    @abstractmethod
    def __call__(self) -> Any:
        """Execute the job logic."""

    def __str__(self) -> str:
        return self.__class__.__name__
```

`ParseWork` extends `Job` for parsing operations:

```python
# src/parsing/gem5/impl/pool/parse_work.py:15-44
class ParseWork(Job):
    def __init__(self, **kwargs: Any) -> None: ...

    def __call__(self) -> ParsedVarsDict:
        raise NotImplementedError("Subclass must implement __call__")
```

Scan operations follow the same structure through `ScanWork`. Both are created
by their respective strategies and submitted to `PerlWorkerPool` or `WorkPool`
for concurrent execution across process and thread executors.

**Design Rationale.**
The Command pattern decouples the creation of work from its execution. A
strategy discovers files and produces work items. The pool infrastructure
executes them in parallel without knowing what each item does. This separation
enables the 54x speedup documented in `PerlWorkerPool` by distributing
parsing across multiple processes.

**Related Patterns:** Strategy (strategies produce command objects), Factory
(the strategy acts as a factory for work items).

---

## 7. Singleton

**GoF Classification:** Creational

**Location:** `app.py` lines 54--58

**Implementation.**
`ApplicationAPI` is instantiated exactly once per Streamlit session using
`@st.cache_resource`, which caches the return value of `get_api()` for the
lifetime of the server process.

```python
# app.py:54-58
@st.cache_resource(show_spinner="Initializing RING-5...")
def get_api() -> ApplicationAPI:
    return ApplicationAPI(plot_deserializer=BasePlot.from_dict)

api = get_api()
st.session_state.api = api
```

The instance is also stored in `st.session_state.api` so that all pages and
components can access it without re-importing or re-constructing.

**Design Rationale.**
Streamlit reruns the entire script on every user interaction. Without caching,
`ApplicationAPI` and its entire dependency tree (services, repositories, parser
backend) would be reconstructed on each rerun, discarding all in-memory state.
`@st.cache_resource` provides singleton semantics in a framework-idiomatic way,
and the `ApplicationAPI.__init__` logger confirms this with the message
`"ApplicationAPI initialized (Singleton Service)"`.

**Related Patterns:** Facade (`ApplicationAPI` is the singleton facade).

---

## 8. Adapter

**GoF Classification:** Structural

**Location:** `src/web/pages/plot_adapters.py` -- three adapter classes
(lines 44--112)

**Implementation.**
Three adapter classes bridge concrete static-method services and standalone
functions to the instance-method protocols expected by controllers.

```python
# src/web/pages/plot_adapters.py:44-71
class PlotLifecycleAdapter:
    """Adapts PlotService static methods to PlotLifecycleService protocol."""

    def create_plot(self, name, plot_type, state_manager) -> PlotHandle:
        return PlotService.create_plot(name, plot_type, state_manager)

    def delete_plot(self, plot_id, state_manager) -> None:
        PlotService.delete_plot(plot_id, state_manager)

    def duplicate_plot(self, plot, state_manager) -> PlotHandle:
        return PlotService.duplicate_plot(cast(BasePlot, plot), state_manager)
```

```python
# src/web/pages/plot_adapters.py:86-111
class PipelineExecutorAdapter:
    """Adapts apply_shapers() and configure_shaper() functions
    to PipelineExecutor protocol."""

    def apply_shapers(self, data, configs) -> pd.DataFrame:
        return apply_shapers(data, configs)

    def configure_shaper(self, shaper_type, data, shaper_id, config, owner_id=None):
        return configure_shaper(shaper_type, data, shaper_id, config, owner_id=owner_id)
```

Controllers receive these adapters through constructor injection:

```python
# Usage in manage_plots.py (conceptual):
lifecycle = PlotLifecycleAdapter()
registry  = PlotTypeRegistryAdapter()
pipeline  = PipelineExecutorAdapter()

creation = PlotCreationController(api, ui_state, lifecycle, registry)
```

**Design Rationale.**
The controllers are designed against protocol interfaces (`PlotLifecycleService`,
`PlotTypeRegistry`, `PipelineExecutor`) for testability. Existing services use
`@staticmethod` and `@classmethod` patterns that cannot directly satisfy instance-
method protocols. The adapters convert between these two calling conventions
without modifying either side.

**Related Patterns:** Protocol (adapters satisfy protocol contracts), Facade
(the adapted services are part of the facade's downstream dependencies).

---

## 9. Observer (Implicit)

**GoF Classification:** Behavioral

**Location:** `src/core/state/repositories/data_repository.py` --
`DataRepository.set_data()` (lines 41--61),
`src/core/state/state_manager.py` -- `StateManager.set_data()` (lines 44--48)

**Implementation.**
The `set_data` method on both the `StateManager` protocol and the
`DataRepository` accept an optional `on_change` callback. When data is set,
the callback fires:

```python
# src/core/state/repositories/data_repository.py:41-54
def set_data(
    self, data: pd.DataFrame | None, on_change: Callable[[], None] | None = None
) -> None:
    self._data = data
    if on_change:
        on_change()
```

The protocol advertises this contract so any implementation must honor it:

```python
# src/core/state/state_manager.py:44-48
def set_data(
    self, data: pd.DataFrame | None, on_change: Callable[[], None] | None = None
) -> None:
    """Set the raw DataFrame with optional change callback."""
    ...
```

This is a lightweight, single-subscriber observer. The callback is not stored
persistently -- it fires once at the point of the `set_data` call rather than
being registered for future events.

**Design Rationale.**
A full publish/subscribe system would be over-engineered for a Streamlit
application where reruns handle most reactivity. The optional callback gives
callers a hook for side effects (clearing derived caches, triggering
recomputation) precisely when they need one, without imposing a listener
registration API on every consumer.

**Related Patterns:** Repository (the observer hook lives on the repository
method), Facade (`ApplicationAPI.load_data()` can pass callbacks when setting
data).

---

## 10. Sentinel Value

**GoF Classification:** Not a GoF pattern. This is a domain-specific idiom
sometimes called the "Special Case" or "Null Object" variant.

**Location:** `src/core/services/visualization/config_resolver.py` (lines 56--57
for constants, lines 60--75 for the resolver function). Backward-compatibility
shim at `src/core/models/visualization/resolvers.py`.

**Implementation.**
Visualization configuration dataclasses use `-1` (int) and `-1.0` (float) as
sentinel values meaning "inherit from parent" or "use engine default". The
`resolve_config()` function walks the `FigureConfig` tree in a single pass and
replaces all sentinels with resolved values.

```python
# src/core/services/visualization/config_resolver.py:56-57
SENTINEL_INT: int = -1
SENTINEL_FLOAT: float = -1.0
```

```python
# src/core/services/visualization/config_resolver.py:60-75
def resolve_config(spec: FigureConfig) -> FigureConfig:
    """Return a new FigureConfig with all sentinel values resolved."""
    resolved = deepcopy(spec)
    _resolve_typography(resolved.typography)
    _resolve_legends(resolved.legends)
    _resolve_axes(resolved.axes)
    return resolved
```

Resolution follows explicit inheritance chains documented in the module
docstring. For example, `font_size_y2label` inherits from `font_size_ylabel`,
and secondary legend spacing inherits from primary legend spacing:

```python
# src/core/services/visualization/config_resolver.py:96-97
typo.font_size_y2label = _resolve_int(typo.font_size_y2label, typo.font_size_ylabel)
```

```python
# src/core/services/visualization/config_resolver.py:78-81
def _resolve_int(value: int, parent: int) -> int:
    return parent if value == SENTINEL_INT else value
```

**Design Rationale.**
Sentinel values let configuration objects be partially specified. A user can
set the base font size and leave all sub-sizes at `-1`; the resolver cascades
the base value to every child field. This is critical for the settings UI,
which exposes a tree of font-size controls where most users only adjust the
root. The alternative -- `Optional[int]` with `None` -- would require `None`
checks throughout every connector, which is more error-prone.

**Related Patterns:** Protocol (resolved configs flow through protocols to
rendering connectors).

---

## 11. Mixin

**GoF Classification:** Not a GoF pattern. Mixins are a Python-specific
composition idiom (sometimes classified under the broader "Multiple
Inheritance" or "Trait" category).

**Location:** `src/web/pages/ui/plotting/plot_config_ui.py` -- class
`PlotConfigUIMixin` (lines 36--419),
`src/web/pages/ui/plotting/base_plot.py` -- class `BasePlot` (line 20)

**Implementation.**
`BasePlot` inherits from both `PlotConfigUIMixin` and `ABC`:

```python
# src/web/pages/ui/plotting/base_plot.py:20
class BasePlot(PlotConfigUIMixin, ABC):
```

The mixin provides all Streamlit widget rendering methods for plot
configuration -- layout settings, typography, legend, axes, colors, data
labels, and advanced options. It declares the instance attributes it expects
from the host class:

```python
# src/web/pages/ui/plotting/plot_config_ui.py:36-54
class PlotConfigUIMixin:
    """Mixin providing all plot configuration UI rendering methods."""

    # Declare expected attributes for type checking
    plot_id: int
    plot_type: str
    config: PlotConfig
    processed_data: pd.DataFrame | None
    _style_ui: BaseStyleUI
```

The mixin dispatches to component classes for each settings section:

```python
# src/web/pages/ui/plotting/plot_config_ui.py:102-183
def render_settings_section(self, section, saved_config, data=None) -> PlotConfig:
    if section == "layout":
        return LayoutSettingsComponent(self.plot_id, self.plot_type).render(saved_config)
    if section == "typography":
        return TypographySettingsComponent(self.plot_id, self.plot_type).render(...)
    if section == "legends":
        return LegendSettingsComponent(self.plot_id, self.plot_type).render(...)
    # ... additional sections
```

**Design Rationale.**
Separating UI rendering into a mixin keeps `BasePlot` focused on figure
generation, serialization, and trace creation. The mixin is ~400 lines of
Streamlit widget code that would otherwise bloat the base class. Because all
nine plot types share the same settings UI framework (differing only in
`render_config_ui` and `render_specific_advanced_options`), the mixin avoids
duplicating this code across each subclass while remaining more flexible than
a separate helper class that would need explicit delegation.

**Related Patterns:** Factory (the `StyleUIFactory` creates the `_style_ui`
strategy that the mixin uses), Strategy (the mixin delegates to style UI
strategy objects).

---

## 12. Lazy Import

**GoF Classification:** Not a GoF pattern. This is a Python performance idiom
sometimes called "Deferred Import" or "Import on Demand".

**Location:** `app.py` lines 138--157 (page routing), `src/web/pages/ui/plotting/base_plot.py`
lines 205--206 (`from_dict` deserialization), `src/web/pages/ui/plotting/plot_config_ui.py`
(settings component imports), `src/parsing/gem5/impl/strategies/factory.py`
lines 34--44 (`StrategyFactory.create`)

**Implementation.**
Page modules are imported inside `if` branches so that only the active page's
module tree is loaded on each Streamlit rerun:

```python
# app.py:138-157
if page == "Data Source":
    from src.web.pages.data_source import DataSourcePage
    DataSourcePage(api).render()
elif page == "Data Managers":
    from src.web.pages.data_managers import show_data_managers_page
    show_data_managers_page(api)
elif page == "Manage Plots":
    from src.web.pages.manage_plots import show_manage_plots_page
    show_manage_plots_page(api)
# ...
```

`BasePlot.from_dict` imports `PlotFactory` inside the method body to break a
circular dependency between the base class and its factory:

```python
# src/web/pages/ui/plotting/base_plot.py:205-208
@classmethod
def from_dict(cls, data: dict[str, Any]) -> "BasePlot":
    from .plot_factory import PlotFactory
    plot = PlotFactory.create_plot(plot_type=data["plot_type"], ...)
```

`StrategyFactory.create()` similarly defers imports of concrete strategies:

```python
# src/parsing/gem5/impl/strategies/factory.py:34-37
if strategy_type == "simple":
    from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy
    return SimpleStatsStrategy()
```

The settings mixin also uses lazy imports for component classes:

```python
# src/web/pages/ui/plotting/plot_config_ui.py:191-195
def _render_engine_specific_controls(self, saved_config, config) -> None:
    from src.web.components.plotting.settings.engine_settings import (
        EngineSettingsComponent,
    )
    EngineSettingsComponent(self.plot_id, self.plot_type).render(saved_config, config)
```

**Design Rationale.**
Streamlit re-executes the entire `app.py` script on every user interaction.
Eager imports of all five page modules (and their transitive dependencies --
Plotly, Matplotlib, dataclass trees) would add hundreds of milliseconds to
every rerun. Lazy imports ensure that only the currently active page pays the
import cost. The application logs a warning when a rerun exceeds 500 ms
(`app.py:161`), confirming that import time is actively monitored. The
`run_app()` wrapper itself (`app.py:15`) is also a lazy-import boundary: it
prevents worker subprocesses from loading Streamlit modules.

**Related Patterns:** Factory (`StrategyFactory` and `PlotFactory` both use
lazy imports internally), Singleton (the `@st.cache_resource` singleton avoids
re-initialization, complementing lazy imports).

---

## Pattern Interaction Map

The twelve patterns are not isolated; they form a coherent architectural
skeleton. The following table summarizes how they collaborate:

| Producer Pattern | Consumer Pattern | Interaction |
|---|---|---|
| Facade | Singleton | The facade is instantiated as a singleton |
| Facade | Repository | The facade delegates state operations to the repository layer |
| Facade | Protocol | The facade depends on protocol contracts, not implementations |
| Factory | Strategy | Factories create strategy instances |
| Factory | Protocol | Factory products satisfy protocol interfaces |
| Factory | Lazy Import | Factory creation methods use deferred imports |
| Strategy | Command | Strategies produce command objects for parallel execution |
| Repository | Observer | Repository `set_data` fires a change callback |
| Mixin | Strategy | The mixin delegates to `StyleUI` strategy objects created by the factory |
| Sentinel Value | Protocol | Resolved configs flow through protocol-defined boundaries |
| Adapter | Protocol | Adapters satisfy protocol contracts for controllers |
| Lazy Import | Singleton | Lazy imports and singleton caching both reduce Streamlit rerun cost |

---

## Summary

The RING-5 Unified Engine v2 uses these 12 patterns to achieve three goals:

1. **Clean layer boundaries.** Protocols, the Facade, and Adapters ensure that
   the web layer never imports parsing code and the core layer never imports
   web code. Only 3 deliberate cross-boundary imports exist (in
   `ApplicationAPI`), all targeting protocol types.

2. **Extensibility without modification.** Factories with open registries and
   Strategy/Protocol contracts mean that new plot types, shaper transformations,
   and parser backends can be added by implementing an interface and registering
   a string key. No existing code changes.

3. **Streamlit performance.** Singleton caching, Lazy Imports, and the Sentinel
   Value resolver all target the constraint that Streamlit re-executes the
   script on every interaction. These patterns keep reruns under 500 ms even
   as the codebase grows.
