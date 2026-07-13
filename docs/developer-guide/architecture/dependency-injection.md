---
title: "Dependency Injection"
parent: Architecture
grand_parent: Developer Guide
nav_order: 4
---

# Dependency Injection

## Overview

RING-5 Unified Engine v2 uses **manual constructor injection** for dependency
management. There is no DI framework or container -- all wiring is explicit
Python code. Dependencies flow downward from a single composition root in
`app.py` through `ApplicationAPI` and into services, state management, and UI
components.

The approach relies on two key techniques:

- **Constructor parameters** to pass collaborators into classes at creation time.
- **`Protocol` types** (from `typing`) to define contracts so that higher-level
  modules depend on abstractions, not concrete implementations.

## Composition Root

The composition root lives in `app.py` inside the Streamlit-cached `get_api()`
factory:

```python
# app.py
@st.cache_resource(show_spinner="Initializing RING-5...")
def get_api() -> ApplicationAPI:
    return ApplicationAPI(plot_deserializer=BasePlot.from_dict)
```

This single call constructs the entire object graph:

1. `ApplicationAPI.__init__` receives the `plot_deserializer` callable and an
   optional `parser`.
2. It creates a `RepositoryStateManager`, forwarding `plot_deserializer`.
3. `RepositoryStateManager` creates a `SessionRepository`, which in turn
   instantiates seven domain repositories (`DataRepository`, `PlotRepository`,
   `ConfigRepository`, `ParserStateRepository`, `HistoryRepository`,
   `PreviewRepository`, `VisualizationRepository`).
4. `DefaultServicesAPI` is constructed with the `state_manager` reference,
   and internally builds its three sub-APIs.
5. The parser backend defaults to the gem5 parser obtained from
   `SimulatorRegistry` when no explicit parser is supplied.

Because `get_api()` is decorated with `@st.cache_resource`, the graph is built
once per Streamlit server process and reused across reruns.

## ApplicationAPI as DI Hub

`ApplicationAPI` (`src/core/application_api.py`) acts as the central
composition point. Its constructor signature declares the two injectable
collaborators:

```python
class ApplicationAPI:
    def __init__(
        self,
        plot_deserializer: PlotDeserializer | None = None,
        parser: SimulationParser | None = None,
    ) -> None:
        self.state_manager = RepositoryStateManager(plot_deserializer=plot_deserializer)
        self._services = DefaultServicesAPI(self.state_manager)
        self._parser = parser or SimulatorRegistry.get_parser("gem5")
```

Every downstream layer receives what it needs through this hub:

| Dependency | Injected as | Purpose |
|---|---|---|
| `PlotDeserializer` | `BasePlot.from_dict` | Deserialize plot dicts without importing web-layer classes |
| `SimulationParser` | gem5 parser (default) | Parse simulator output files |
| `StateManager` | `RepositoryStateManager` instance | Shared application state |
| `DefaultServicesAPI` | Internal composition | Service facade for managers, data, and shapers |

The `ApplicationAPI` instance is then passed to every page and component that
needs access to domain services or application state.

## Protocol-Based Contracts

Dependency inversion is achieved through `typing.Protocol` classes decorated
with `@runtime_checkable`. The core layer defines the contracts; concrete
implementations live in separate modules.

**`StateManager`** (`src/core/state/state_manager.py`) -- defines the full
contract for state operations. `ApplicationAPI` depends on this protocol, not
on `RepositoryStateManager` directly.

**`SimulationParser`** (`src/parsing/parser_protocol.py`) -- defines the
parsing contract (`submit_parse_async`, `finalize_parsing`,
`submit_scan_async`, `aggregate_scan_results`). Any simulator backend
implementing this protocol can be injected.

**`PlotProtocol`** and **`PlotDeserializer`** (`src/core/models/plot_protocol.py`)
-- decouple the core and repository layers from the web-layer `BasePlot` class.
`PlotDeserializer` is a callable type alias
(`Callable[[dict[str, Any]], PlotProtocol | None]`) injected at startup so
portfolio restoration never imports web-layer modules.

This pattern keeps the `src/core` package free of any Streamlit or web-layer
imports.

## Service Layer Composition

`DefaultServicesAPI` (`src/core/services/services_impl.py`) composes three
domain-aligned sub-APIs:

```python
class DefaultServicesAPI:
    def __init__(self, state_manager: StateManager) -> None:
        self._managers = DefaultManagersAPI()
        self._data_services = DefaultDataServicesAPI(state_manager)
        self._shapers = DefaultShapersAPI(PathService.get_pipelines_dir())
```

Each sub-API receives only the dependencies it needs:

- `DefaultManagersAPI` -- stateless data transformations, no dependencies.
- `DefaultDataServicesAPI` -- needs `state_manager` for portfolio persistence.
- `DefaultShapersAPI` -- needs a pipelines directory path from `PathService`.

`ApplicationAPI` exposes these through read-only properties (`api.managers`,
`api.data_services`, `api.shapers`), allowing UI components to reach services
without tight coupling to the internal composition.

## Page and Component Injection

All pages and UI components receive `ApplicationAPI` as a constructor or
function argument. The composition root in `app.py` passes the cached instance:

```python
# Pages receive api as argument
DataSourcePage(api).render()
show_data_managers_page(api)
show_manage_plots_page(api)
show_portfolio_page(api)
```

**Data managers** extend an abstract `DataManager` base class
(`src/web/components/data_managers/data_manager.py`) that stores the API
reference:

```python
class DataManager(ABC):
    def __init__(self, api: ApplicationAPI):
        self.api = api
```

All four concrete managers (`SeedsReducerManager`, `OutlierRemoverManager`,
`PreprocessorManager`, `MixerManager`) inherit this constructor and gain
access to state and services through `self.api`.

**Controllers** on the Manage Plots page use a more granular injection pattern,
receiving protocol-compatible adapters alongside `api`:

```python
creation = PlotCreationController(api, ui_state, lifecycle, registry)
pipeline = PipelineController(api, ui_state, pipeline_executor)
```

Here `lifecycle`, `registry`, and `pipeline_executor` are lightweight adapter
objects that bridge static utility methods to protocol contracts, keeping
controllers decoupled from concrete implementations.

## Testing with DI

Because all dependencies are injected through constructors and defined by
Protocol types, substituting test doubles is straightforward:

```python
# Create a mock that satisfies the SimulationParser protocol
class FakeParser:
    def submit_parse_async(self, ...): ...
    def finalize_parsing(self, ...): ...
    def submit_scan_async(self, ...): ...
    def aggregate_scan_results(self, ...): ...

# Inject the fake into ApplicationAPI
api = ApplicationAPI(parser=FakeParser())
```

Similarly, `PlotDeserializer` can be replaced with a lambda for tests that do
not need real plot deserialization:

```python
api = ApplicationAPI(plot_deserializer=lambda d: None)
```

No patching or monkey-patching is required -- the constructor parameters
provide natural seams for test isolation.

## See Also

- [Architecture Overview](overview.md) -- layer diagram and module boundaries.
- `src/core/application_api.py` -- the DI hub.
- `src/core/state/state_manager.py` -- the `StateManager` protocol.
- `src/core/models/plot_protocol.py` -- `PlotProtocol` and `PlotDeserializer`.
- `src/parsing/parser_protocol.py` -- the `SimulationParser` protocol.
- `src/core/services/services_impl.py` -- service layer composition.
