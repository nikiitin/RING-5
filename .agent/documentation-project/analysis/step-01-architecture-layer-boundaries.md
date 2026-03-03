# Step 01 — Architecture & Layer Boundaries Analysis

> **Status**: COMPLETE
> **Analyzed on**: 2026-03-03
> **Branch**: `005/unified-engine-ui-v2`

---

## 1. Executive Summary

The RING-5 Unified Engine v2 follows a **strict 3-layer architecture** with clean import
boundaries. The application is a Streamlit-based web tool for gem5 simulation data analysis
and publication-quality plot generation.

| Layer | Package | File Count | Responsibility |
|-------|---------|-----------|----------------|
| **Core (B)** | `src/core/` | 81 `.py` files | Models, Services, State, ApplicationAPI facade |
| **Parsing (A)** | `src/parsing/` | 36 `.py` files | gem5 parser, scanner, Perl integration |
| **Web (C)** | `src/web/` | ~120 `.py` files | Streamlit pages, components, controllers, rendering |

**Key finding**: The architecture is **almost perfectly clean** — only 3 deliberate
cross-boundary imports exist (Core importing from Parsing via ApplicationAPI facade), and
all other import directions follow the strict rule: **Web → Core ← Parsing**.

---

## 2. Entry Point

### `app.py` (172 lines)
The Streamlit entry point. Key responsibilities:
- Adds project root to `sys.path`
- Wraps all imports inside `run_app()` to prevent import on worker processes
- Initializes `ApplicationAPI` via `st.cache_resource` (singleton)
- Injects `BasePlot.from_dict` as `plot_deserializer` (Dependency Injection)
- Defines sidebar navigation with 5 pages
- Uses lazy page imports (only active page module is loaded)

**Navigation pages** (ordered in sidebar):
1. `Data Source` → `src.web.pages.data_source.DataSourcePage`
2. `Data Managers` → `src.web.pages.data_managers.show_data_managers_page`
3. `Manage Plots` → `src.web.pages.manage_plots.show_manage_plots_page`
4. `Save/Load Portfolio` → `src.web.pages.portfolio.show_portfolio_page`
5. `Documentation` → `src.web.pages.documentation.show_documentation_page`

**State initialization**: `st.session_state.api = api` makes ApplicationAPI globally
accessible to all pages via session state.

---

## 3. Complete Layer Map

### 3.1 Core Layer (`src/core/`) — 81 Python files

The Core layer is the **domain layer** — pure business logic with no UI dependencies.

```
src/core/
├── __init__.py                              # Docstring-only ("RING-5 Core Module")
├── application_api.py                       # FACADE: Single entry point for UI (429 lines)
├── performance.py                           # Performance monitoring utilities
├── common/
│   └── utils.py                             # Shared utilities (path normalization, glob sanitization)
│
├── models/                                  # Domain models (dataclasses, TypedDicts, Protocols)
│   ├── __init__.py                          # Re-exports: ParseBatchResult, ScannedVariable, StatConfig
│   ├── plot_protocol.py                     # PlotProtocol + PlotDeserializer
│   ├── plot_config.py                       # PlotConfig TypeAlias (Dict[str, Any])
│   ├── history_models.py                    # OperationRecord, HistoryEntry
│   ├── data_models.py                       # ParseVariableConfig, CsvPoolEntry, ScannedVariableDict, etc.
│   ├── parsing_models.py                    # StatConfig, ScannedVariable, ParseBatchResult, StatParamValue
│   ├── csv_contract.py                      # CSV format contract types
│   ├── portfolio_models.py                  # PortfolioData, PortfolioConfig
│   ├── shaper_models.py                     # ShaperStepConfig, PipelineStep
│   ├── config/
│   │   ├── __init__.py                      # Re-exports ConfigManager
│   │   └── config_manager.py               # Application configuration management
│   └── visualization/                       # Visualization config models (13 files)
│       ├── __init__.py                      # Re-exports all viz models
│       ├── figure_config.py                 # FigureConfig (top-level viz spec)
│       ├── trace_config.py                  # TraceConfig, BarTraceConfig, LineTraceConfig, etc.
│       ├── axis_config.py                   # AxisConfig (x/y axis settings)
│       ├── legend_config.py                 # LegendConfig
│       ├── typography_config.py             # TypographyConfig
│       ├── annotation_config.py             # AnnotationConfig, ShapeConfig
│       ├── data_label_config.py             # DataLabelConfig
│       ├── series_style_config.py           # SeriesStyleConfig
│       ├── palettes.py                      # Color palette definitions
│       ├── resolvers.py                     # Sentinel value resolution (-1 → default)
│       └── trace_build_result.py            # TraceBuildResult aggregate
│
├── state/                                   # State management (Repository pattern)
│   ├── state_manager.py                     # StateManager Protocol (250 lines, 40+ methods)
│   ├── repository_state_manager.py          # RepositoryStateManager implementation
│   └── repositories/                        # Individual state repositories
│       ├── __init__.py                      # Re-exports all repositories
│       ├── session_repository.py            # SessionRepository (AGGREGATE ROOT, 7 child repos)
│       ├── data_repository.py               # DataRepository: raw/processed DataFrames
│       ├── config_repository.py             # ConfigRepository: config dict, CSV path, temp dir
│       ├── parser_state_repository.py        # ParserStateRepository: variables, patterns, strategies
│       ├── plot_repository.py               # PlotRepository: plots list, current plot, counter
│       ├── preview_repository.py            # PreviewRepository: operation previews
│       ├── history_repository.py            # HistoryRepository: manager + portfolio history
│       └── visualization_repository.py      # VisualizationRepository: CSV pool, saved configs
│
└── services/                                # Business logic services
    ├── __init__.py                          # Re-exports ALL services (62 lines, comprehensive)
    ├── services_api.py                      # ServicesAPI Protocol (unified facade)
    ├── services_impl.py                     # DefaultServicesAPI implementation
    ├── plot_interaction_service.py           # Pure function: update_config_from_relayout
    ├── config_validation_service.py          # Configuration validation
    ├── portfolio_migrator.py                # Portfolio schema migration
    ├── visualization/                       # Visualization services
    │   ├── __init__.py
    │   ├── config_resolver.py               # Sentinel resolution: -1 → actual defaults
    │   ├── palette_service.py               # Color palette management
    │   └── plot_interaction.py              # Plot interaction logic
    ├── managers/                             # Stateless data transformation managers
    │   ├── __init__.py                      # Re-exports: ManagersAPI, DefaultManagersAPI, etc.
    │   ├── managers_api.py                  # ManagersAPI Protocol
    │   ├── managers_impl.py                 # DefaultManagersAPI implementation
    │   ├── arithmetic_service.py            # Arithmetic computations on DataFrames
    │   ├── outlier_service.py               # Outlier removal (IQR/z-score)
    │   └── reduction_service.py             # Seed reduction (mean/median/mode)
    ├── data_services/                       # Data management services
    │   ├── __init__.py                      # Re-exports all data services
    │   ├── data_services_api.py             # DataServicesAPI Protocol (228 lines, 25+ methods)
    │   ├── data_services_impl.py            # DefaultDataServicesAPI implementation
    │   ├── csv_pool_service.py              # CSV file pool management
    │   ├── config_service.py                # Configuration persistence (save/load)
    │   ├── path_service.py                  # Path resolution and validation
    │   ├── variable_service.py              # Variable CRUD and search
    │   ├── portfolio_service.py             # Portfolio save/load/delete
    │   └── pattern_index_service.py         # Pattern index for gem5 stat matching
    └── shapers/                             # Data transformation pipeline
        ├── __init__.py                      # Re-exports: ShapersAPI, ShaperFactory, etc.
        ├── shapers_api.py                   # ShapersAPI Protocol
        ├── shapers_impl.py                  # DefaultShapersAPI implementation
        ├── shaper.py                        # Shaper ABC (base class)
        ├── factory.py                       # ShaperFactory (registry + creation)
        ├── validation.py                    # Pipeline validation
        ├── uni_df_shaper.py                 # Unified DataFrame shaper
        ├── pipeline_service.py              # Pipeline CRUD service
        └── impl/                            # Concrete shaper implementations
            ├── selector.py                  # SelectorShaper
            ├── sort.py                      # SortShaper
            ├── mean.py                      # MeanShaper
            ├── normalize.py                 # NormalizeShaper
            ├── pivot.py                     # PivotShaper
            ├── split_apply.py               # SplitApplyShaper
            ├── transformer.py               # TransformerShaper
            └── selector_algorithms/
                ├── item_selector.py         # Item-based selection
                ├── column_selector.py       # Column-based selection
                └── condition_selector.py    # Condition-based selection
```

### 3.2 Parsing Layer (`src/parsing/`) — 36 Python files

The Parsing layer handles all data ingestion. Currently only gem5 is implemented but
the protocol-based design supports adding new simulators.

```
src/parsing/
├── __init__.py                              # PUBLIC API: ParseService, ScannerService (re-exports)
├── parser_protocol.py                       # SimulationParser Protocol (4 methods)
├── parse_service.py                         # Thin shim → Gem5Parser
├── scanner_service.py                       # Thin shim → Gem5Scanner
├── registry.py                              # SimulatorRegistry (auto-discovery)
│
└── gem5/                                    # gem5-specific implementation
    ├── __init__.py                          # Re-exports Gem5Parser, Gem5Scanner
    ├── models.py                            # gem5-specific data models
    └── impl/
        ├── __init__.py
        ├── gem5_parser.py                   # Gem5Parser (implements SimulationParser)
        ├── gem5_parser_api.py               # Gem5 parser API with configuration
        ├── gem5_scanner.py                  # Gem5Scanner (file/stat discovery)
        ├── pool/                            # Parallel execution infrastructure
        │   ├── __init__.py
        │   ├── job.py                       # Job ABC (Command pattern)
        │   ├── pool.py                      # PerlWorkerPool (625 lines, 54x speedup)
        │   ├── work_pool.py                 # WorkPool singleton (Process+Thread executors)
        │   ├── parse_work.py                # Parse work distribution
        │   └── scan_work.py                 # Scan work distribution
        ├── scanning/                        # File scanning subsystem
        │   ├── __init__.py
        │   ├── scanner.py                   # Core scanning logic
        │   ├── pattern_aggregator.py        # Pattern aggregation
        │   └── gem5_scan_work.py            # Scan work items
        ├── strategies/                      # Parsing strategy pattern
        │   ├── __init__.py
        │   ├── file_parser_strategy.py      # FileParserStrategy Protocol
        │   ├── factory.py                   # StrategyFactory
        │   ├── simple.py                    # SimpleStatsStrategy
        │   ├── config_aware.py              # ConfigAwareStrategy
        │   ├── perl_worker_pool.py          # Perl inter-process communication
        │   └── gem5_parse_work.py           # gem5-specific parse work
        └── types/                           # gem5 statistic types (self-registering)
            ├── __init__.py                  # StatTypeRegistry
            ├── type_mapper.py               # Type discrimination logic
            ├── base.py                      # Base stat type
            ├── scalar.py                    # ScalarStat
            ├── vector.py                    # VectorStat
            ├── distribution.py              # DistributionStat
            ├── histogram.py                 # HistogramStat
            └── configuration.py             # ConfigurationStat
```

### 3.3 Web Layer (`src/web/`) — ~120 Python files

The Presentation layer. Handles all Streamlit UI, rendering, and user interaction.

```
src/web/
├── __init__.py                              # Docstring-only ("RING-5 Web Module")
│
├── state/
│   ├── __init__.py
│   └── ui_state_manager.py                  # Web-layer UI state management
│
├── models/                                  # Web-layer models
│   ├── __init__.py
│   ├── plot_models.py                       # PlotDisplayConfig, web-specific plot types
│   └── plot_protocols.py                    # 12 Protocols for plot rendering contracts
│
├── controllers/                             # Controller pattern for plot operations
│   ├── __init__.py
│   └── plot/
│       ├── __init__.py
│       ├── creation_controller.py           # Plot creation orchestration
│       ├── pipeline_controller.py           # Pipeline execution orchestration
│       └── render_controller.py             # Render orchestration
│
├── pages/                                   # Streamlit pages (5 user-facing pages)
│   ├── __init__.py
│   ├── plot_adapters.py                     # Adapter: BasePlot → PlotHandle/ConfigRenderer
│   ├── data_source.py                       # Data Source page (NOT in data_source/ subdir)
│   ├── data_managers.py                     # Data Managers page
│   ├── manage_plots.py                      # Manage Plots page (main plotting page)
│   ├── portfolio.py                         # Save/Load Portfolio page
│   ├── documentation.py                     # Documentation page
│   └── ui/                                  # UI subsystems
│       ├── __init__.py
│       ├── shaper_config.py                 # Shaper configuration UI
│       └── plotting/                        # Plotting subsystem (largest)
│           ├── __init__.py
│           ├── base_plot.py                 # BasePlot ABC (222 lines)
│           ├── plot_factory.py              # PlotFactory (registry + creation)
│           ├── plot_renderer.py             # Plot rendering orchestration
│           ├── plot_config_ui.py            # PlotConfigUIMixin
│           ├── plot_service.py              # Plot lifecycle service
│           ├── settings_pills.py            # Settings pill navigation system
│           ├── download_section.py          # Download/export section
│           ├── types/                       # 9 concrete plot type implementations
│           │   ├── __init__.py              # Re-exports all 9 plot types
│           │   ├── bar_plot.py              # BarPlot
│           │   ├── line_plot.py             # LinePlot
│           │   ├── scatter_plot.py          # ScatterPlot
│           │   ├── histogram_plot.py        # HistogramPlot
│           │   ├── heatmap_plot.py          # HeatmapPlot
│           │   ├── grouped_bar_plot.py      # GroupedBarPlot
│           │   ├── stacked_bar_plot.py      # StackedBarPlot
│           │   ├── grouped_stacked_bar_plot.py # GroupedStackedBarPlot
│           │   ├── dual_axis_bar_dot_plot.py   # DualAxisBarDotPlot
│           │   └── _trace_helpers.py        # Shared trace-building helpers (private)
│           ├── styles/                      # Per-plot-type style UI strategies
│           │   ├── __init__.py
│           │   ├── factory.py               # StyleUIFactory
│           │   ├── base_ui.py               # BaseStyleUI
│           │   ├── bar_ui.py                # BarStyleUI
│           │   ├── line_ui.py               # LineStyleUI
│           │   ├── colors.py                # Color management
│           │   └── applicator.py            # StyleApplicator
│           └── export/                      # Export/download subsystem
│               ├── __init__.py
│               └── presets/
│                   ├── __init__.py
│                   ├── preset_manager.py    # PresetManager
│                   └── preset_schema.py     # PresetSchema
│
├── components/                              # Reusable UI components
│   ├── __init__.py                          # (empty)
│   ├── common/                              # General-purpose components
│   │   ├── __init__.py                      # (empty)
│   │   ├── card_components.py               # Card UI components
│   │   ├── data_components.py               # Data display components
│   │   ├── history_components.py            # Operation history display
│   │   ├── plot_creation.py                 # Plot creation dialog
│   │   ├── pipeline.py                      # Pipeline UI
│   │   ├── pipeline_step.py                 # Pipeline step UI
│   │   ├── plot_controls.py                 # Plot control widgets
│   │   ├── plot_selector.py                 # Plot selector dropdown
│   │   ├── layout_components.py             # Layout helpers
│   │   ├── filtered_selector.py             # Filtered multi-select
│   │   ├── reorderable_list.py              # Drag-to-reorder list
│   │   └── chart_display.py                 # Chart display wrapper
│   ├── data_source/                         # Data Source page components
│   │   ├── __init__.py                      # (empty)
│   │   ├── data_source_components.py        # Scan/parse UI
│   │   ├── variable_editor.py               # Variable editing UI
│   │   └── pattern_index_selector.py        # Pattern index selection
│   ├── data_managers/                       # Data Manager components
│   │   ├── __init__.py
│   │   ├── data_manager.py                  # DataManager ABC
│   │   ├── data_manager_components.py       # Shared manager UI
│   │   ├── preprocessor.py                  # Preprocessor manager
│   │   ├── seeds_reducer.py                 # Seeds reduction manager
│   │   ├── outlier_remover.py               # Outlier removal manager
│   │   └── mixer.py                         # Data mixer manager
│   ├── shapers/                             # Shaper configuration components
│   │   ├── __init__.py                      # (empty)
│   │   ├── selector_transformer_configs.py  # Selector/Transformer config UI
│   │   ├── sort_config.py                   # Sort shaper config UI
│   │   ├── mean_config.py                   # Mean shaper config UI
│   │   ├── normalize_config.py              # Normalize shaper config UI
│   │   ├── pivot_config.py                  # Pivot shaper config UI
│   │   └── split_apply_config.py            # Split-apply shaper config UI
│   └── plotting/                            # Plotting components
│       ├── __init__.py                      # (empty)
│       ├── interactive_plot.py              # Interactive Plotly display
│       ├── config/                          # Plot-type-specific configuration components
│       │   ├── __init__.py
│       │   ├── base_plot_config.py          # Base config component
│       │   ├── plot_config_components.py    # Shared config components
│       │   ├── grouped_bar_config.py        # Grouped bar config
│       │   ├── stacked_bar_config.py        # Stacked bar config
│       │   ├── grouped_stacked_bar_config.py # Grouped-stacked config
│       │   ├── grouped_stacked_bar_theme.py # Theme for grouped-stacked
│       │   ├── histogram_config.py          # Histogram config
│       │   ├── heatmap_config.py            # Heatmap config
│       │   ├── dual_axis_config.py          # Dual axis config
│       │   └── dual_axis_settings.py        # Dual axis settings
│       └── settings/                        # Settings pill panels (11 tabs)
│           ├── __init__.py
│           ├── widget_factory.py            # Widget factory for settings
│           ├── layout_settings.py           # Layout settings panel
│           ├── typography_settings.py       # Typography settings panel
│           ├── axes_settings.py             # Axes settings panel
│           ├── legend_settings.py           # Legend settings panel
│           ├── colors_settings.py           # Colors settings panel
│           ├── data_labels_settings.py      # Data labels settings panel
│           ├── ordering_settings.py         # Ordering settings panel
│           ├── engine_settings.py           # Engine settings panel
│           ├── reference_line_settings.py   # Reference line settings panel
│           ├── shapes_settings.py           # Shapes settings panel
│           └── advanced_settings.py         # Advanced settings panel (contains 3 Protocols)
│
└── rendering/                               # Rendering engine layer
    ├── __init__.py                          # Public API (8 classes exported)
    ├── config_builder.py                    # ConfigSpecBuilder, PlotlyFigureSpecBuilder, PresetSpecBuilder
    ├── plotly_connector.py                  # FigureSpecToPlotly: FigureConfig → Plotly updates
    ├── matplotlib_connector.py              # FigureSpecToMatplotlib: FigureConfig → matplotlib updates
    ├── matplotlib_trace_renderer.py         # MatplotlibTraceRenderer: TraceConfig → matplotlib artists
    ├── trace_to_plotly.py                   # traces_to_plotly: TraceBuildResult → go.Figure
    ├── engine_manager.py                    # EngineManager: engine mode selection
    ├── preset_applicator.py                 # PresetApplicator: preset → FigureConfig overlay
    ├── _connector_protocol.py               # ConnectorProtocol (private)
    ├── _render_result.py                    # RenderResult type (private)
    ├── _heatmap_utils.py                    # Heatmap-specific rendering utils (private)
    └── widgets/                             # Declarative widget system
        ├── __init__.py
        ├── widget_def.py                    # Widget definition types
        └── widget_renderer.py               # Widget rendering engine
```

---

## 4. Cross-Layer Import Analysis

### 4.1 Import Direction Matrix

| From ↓ \ To → | Core | Parsing | Web |
|----------------|------|---------|-----|
| **Core** | ✅ internal | ⚠️ 3 imports (ApplicationAPI only) | ❌ ZERO |
| **Parsing** | ✅ 28 imports | ✅ internal | ❌ ZERO |
| **Web** | ✅ 97 import lines | ❌ ZERO | ✅ internal |

**Verdict: ARCHITECTURE IS CLEAN** ✅

### 4.2 Core → Parsing (3 deliberate imports)

These exist solely in `src/core/application_api.py` as the **facade bridge**:

```python
# application_api.py:54-55
from src.parsing.parser_protocol import SimulationParser
from src.parsing.registry import SimulatorInfo, SimulatorRegistry
```

**Justification**: ApplicationAPI is the single orchestration point. It needs to:
1. Accept a `SimulationParser` (Protocol type) for dependency injection
2. Access `SimulatorRegistry` for simulator auto-discovery
3. Use `SimulatorInfo` for registry metadata

These are **protocol/interface imports only** — ApplicationAPI never imports concrete
implementations (Gem5Parser, Gem5Scanner). This is Dependency Inversion in action.

### 4.3 Core → Web: ZERO imports ✅

No file in `src/core/` imports from `src/web/`. The core layer is completely independent of
the presentation layer.

### 4.4 Parsing → Web: ZERO imports ✅

No file in `src/parsing/` imports from `src/web/`. The parsing layer has no knowledge of
the UI.

### 4.5 Web → Parsing: ZERO imports ✅

No file in `src/web/` imports from `src/parsing/`. All parsing access goes through
`ApplicationAPI`, which is in the core layer.

### 4.6 Parsing → Core: 28 imports (legitimate)

The parsing layer imports **models and utilities** from core. Key imports:

| Parsing File | Core Imports |
|-------------|-------------|
| `gem5/models.py` | `parsing_models.StatConfig, ScannedVariable, ParseBatchResult` |
| `gem5/impl/gem5_parser.py` | `data_models.ParseVariableConfig, ShaperStepConfig` |
| `gem5/impl/gem5_scanner.py` | `parsing_models.ScannedVariable, StatConfig` |
| `gem5/impl/strategies/simple.py` | `parsing_models.*`, `data_models.ParseVariableConfig` |
| `gem5/impl/strategies/config_aware.py` | `parsing_models.*`, `data_models.ParseVariableConfig` |
| `gem5/impl/strategies/perl_worker_pool.py` | `parsing_models.StatParamValue` |
| `gem5/impl/scanning/scanner.py` | `parsing_models.ScannedVariable` |
| `gem5/types/*.py` | `parsing_models.StatConfig` |
| `parser_protocol.py` | `parsing_models.ParseBatchResult, ScannedVariable, StatConfig` |
| `registry.py` | `parser_protocol.SimulationParser` |
| `gem5/impl/gem5_parser_api.py` | `data_services.pattern_index_service.PatternIndexService` |

**Notable**: One service-level import exists — `gem5_parser_api.py` imports
`PatternIndexService` from core services. This is the tightest coupling between
parsing and core.

### 4.7 Web → Core: 97 import lines (expected, heaviest coupling)

The web layer extensively imports from core for:
- **Models**: `PlotConfig`, `FigureConfig`, `TraceConfig`, `ShaperStepConfig`, etc.
- **Services**: `ApplicationAPI` (primary entry point)
- **Protocols**: `PlotProtocol`, `StateManager`
- **Visualization configs**: All config models for rendering

This is the expected coupling direction — the presentation layer depends on the domain.

---

## 5. Public API Surface per Layer

### 5.1 Core Layer Public API

**`src/core/__init__.py`**: Minimal — just a docstring.

**`src/core/services/__init__.py`**: The main public API surface (62 lines):
- Primary: `ServicesAPI` (Protocol), `DefaultServicesAPI` (implementation)
- Sub-API Protocols: `ManagersAPI`, `DataServicesAPI`, `ShapersAPI`
- Sub-API implementations: `DefaultManagersAPI`, `DefaultDataServicesAPI`, `DefaultShapersAPI`
- Individual services: `ArithmeticService`, `OutlierService`, `ReductionService`,
  `CsvPoolService`, `ConfigService`, `PathService`, `VariableService`, `PortfolioService`,
  `PipelineService`, `ShaperFactory`

**`src/core/models/__init__.py`**: Re-exports `ParseBatchResult`, `ScannedVariable`, `StatConfig`

**`src/core/models/visualization/__init__.py`**: Re-exports `FigureConfig` and all
visualization config models.

**`src/core/state/repositories/__init__.py`**: Re-exports all repository classes.

**Primary entry point**: `ApplicationAPI` class in `src/core/application_api.py`

### 5.2 Parsing Layer Public API

**`src/parsing/__init__.py`**: Well-defined public API:
```python
from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService
from src.parsing.gem5.impl.gem5_scanner import Gem5Scanner as ScannerService
__all__ = ["ParseService", "ScannerService"]
```

**Backward-compatibility shims**: `parse_service.py` and `scanner_service.py` are thin
re-export files kept for test-patch compatibility.

### 5.3 Web Layer Public API

**`src/web/__init__.py`**: Minimal — just a docstring + comment about test discoverability.

**`src/web/rendering/__init__.py`**: Well-defined public API (8 classes):
```python
__all__ = [
    "ConfigSpecBuilder", "EngineManager", "FigureSpecToPlotly",
    "FigureSpecToMatplotlib", "PlotlyFigureSpecBuilder", "PresetApplicator",
    "PresetSpecBuilder", "MatplotlibTraceRenderer",
]
```

**`src/web/pages/ui/plotting/types/__init__.py`**: Exports all 9 plot types.

Most web-layer packages have empty or minimal `__init__.py` files — the API surface
is defined by direct imports rather than package-level re-exports.

---

## 6. Protocol Catalog (19 Protocols)

### 6.1 Core Layer Protocols (7)

| Protocol | File | Line | Methods | Purpose |
|----------|------|------|---------|---------|
| `StateManager` | `core/state/state_manager.py` | 28 | 40+ | State management contract (data, config, parser, plots, previews, history) |
| `PlotProtocol` | `core/models/plot_protocol.py` | 18 | 1 (`to_dict`) + 9 properties | Decouples Core from Web's BasePlot |
| `ServicesAPI` | `core/services/services_api.py` | 25 | 3 properties | Unified facade: `managers`, `data_services`, `shapers` |
| `DataServicesAPI` | `core/services/data_services/data_services_api.py` | 31 | 25+ | CSV pool, config persistence, variable mgmt, portfolio |
| `ManagersAPI` | `core/services/managers/managers_api.py` | — | ~6 | Arithmetic, outlier, reduction operations |
| `ShapersAPI` | `core/services/shapers/shapers_api.py` | — | ~8 | Pipeline CRUD + shaper execution |
| `PlotDeserializer` | `core/models/plot_protocol.py` | — | 1 (`__call__`) | Callback type for dict → PlotProtocol conversion |

**Key observation**: `StateManager` is by far the largest Protocol (~250 lines, 40+ methods),
defining the complete contract for application state management.

### 6.2 Parsing Layer Protocols (2)

| Protocol | File | Line | Methods | Purpose |
|----------|------|------|---------|---------|
| `SimulationParser` | `parsing/parser_protocol.py` | — | 4 (`scan`, `parse`, `get_strategies`, `get_strategy_params`) | Parser contract for simulator backends |
| `FileParserStrategy` | `parsing/gem5/impl/strategies/file_parser_strategy.py` | — | 1 (`parse_file`) | Strategy for individual file parsing |

### 6.3 Web Layer Protocols (10)

| Protocol | File | Line | Methods | Purpose |
|----------|------|------|---------|---------|
| `PlotHandle` | `web/models/plot_protocols.py` | — | Properties only | Read access to plot identity/state |
| `ConfigRenderer` | `web/models/plot_protocols.py` | — | 1 | Renders plot-specific configuration UI |
| `RenderablePlot` | `web/models/plot_protocols.py` | — | Composite | `PlotHandle + ConfigRenderer` (duck-typed union) |
| `PlotLifecycleService` | `web/models/plot_protocols.py` | — | ~5 | Plot CRUD operations |
| `PlotTypeRegistry` | `web/models/plot_protocols.py` | — | 2 | Plot type discovery |
| `PipelineExecutor` | `web/models/plot_protocols.py` | — | 2 | `apply_shapers`, `configure_shaper` |
| `SpecificOptionsRenderer` | `web/models/plot_protocols.py` | — | 1 (`__call__`) | Renders plot-type-specific options |
| `OrderingRenderer` | `web/models/plot_protocols.py` | — | 1 (`__call__`) | Renders ordering controls |
| `ReferenceLineRenderer` | `web/components/plotting/settings/advanced_settings.py` | 33 | 1 (`__call__`) | Renders reference line UI |
| `ShapesRenderer` | `web/components/plotting/settings/advanced_settings.py` | 44 | 1 (`__call__`) | Renders shapes UI |
| `EngineControlsRenderer` | `web/components/plotting/settings/advanced_settings.py` | 53 | 1 (`__call__`) | Renders engine-specific controls |

**Key observation**: Web Protocols are mostly **single-method callable protocols** — they
act as typed function signatures for UI rendering callbacks. This follows a "function
protocol" pattern common in Streamlit applications where components are composed from
callback functions.

---

## 7. Factory Catalog (4 Factories)

| Factory | File | Layer | Creates | Registry Type |
|---------|------|-------|---------|---------------|
| `ShaperFactory` | `core/services/shapers/factory.py` | Core | Shaper instances | `_registry: dict[str, type[Shaper]]` (10 registered types) |
| `StrategyFactory` | `parsing/gem5/impl/strategies/factory.py` | Parsing | FileParserStrategy instances | Strategy name → class mapping |
| `StyleUIFactory` | `web/pages/ui/plotting/styles/factory.py` | Web | BaseStyleUI instances | Plot type → style UI strategy |
| `PlotFactory` | `web/pages/ui/plotting/plot_factory.py` | Web | BasePlot instances | Plot type → class mapping |

### 7.1 ShaperFactory Registered Types (10)
1. `selector` → SelectorShaper
2. `sort` → SortShaper
3. `mean` → MeanShaper
4. `normalize` → NormalizeShaper
5. `pivot` → PivotShaper
6. `split_apply` → SplitApplyShaper
7. `transformer` → TransformerShaper
8. `uni_df` → UniDfShaper
9. `item_selector` → ItemSelector (algorithm)
10. `column_selector` → ColumnSelector (algorithm)

### 7.2 PlotFactory Registered Types (9)
1. `bar` → BarPlot
2. `line` → LinePlot
3. `scatter` → ScatterPlot
4. `histogram` → HistogramPlot
5. `heatmap` → HeatmapPlot
6. `grouped_bar` → GroupedBarPlot
7. `stacked_bar` → StackedBarPlot
8. `grouped_stacked_bar` → GroupedStackedBarPlot
9. `dual_axis_bar_dot` → DualAxisBarDotPlot

---

## 8. Registry Catalog (4 Registries)

| Registry | File | Layer | Registered Items | Discovery Mechanism |
|----------|------|-------|-----------------|---------------------|
| `ShaperFactory._registry` | `core/services/shapers/factory.py` | Core | 10 shaper classes | Static dict + `register()` classmethod |
| `SimulatorRegistry` | `parsing/registry.py` | Parsing | Simulator backends (gem5) | Auto-registration via package imports |
| `StatTypeRegistry` | `parsing/gem5/types/__init__.py` | Parsing | 5 stat types (scalar, vector, distribution, histogram, configuration) | Self-registering on import |
| `PlotFactory` | `web/pages/ui/plotting/plot_factory.py` | Web | 9 plot types | Static dict in factory |

---

## 9. ABC Catalog (4 Abstract Base Classes)

| ABC | File | Layer | Concrete Implementations | Key Abstract Methods |
|-----|------|-------|-------------------------|---------------------|
| `Shaper` | `core/services/shapers/shaper.py` | Core | 7+ concrete shapers | `_verify_params()`, `__call__()` |
| `Job` | `parsing/gem5/impl/pool/job.py` | Parsing | ParseWork, ScanWork | `__call__()` |
| `BasePlot` | `web/pages/ui/plotting/base_plot.py` | Web | 9 concrete plot types | `create_traces()`, `get_legend_column()` |
| `DataManager` | `web/components/data_managers/data_manager.py` | Web | 4 concrete managers | `name` (property), `render()` |

### 9.1 BasePlot Hierarchy (9 types)
```
BasePlot (PlotConfigUIMixin, ABC)
├── BarPlot
├── LinePlot
├── ScatterPlot
├── HistogramPlot
├── HeatmapPlot
├── GroupedBarPlot
├── StackedBarPlot
├── GroupedStackedBarPlot
└── DualAxisBarDotPlot
```

### 9.2 DataManager Hierarchy (4 managers)
```
DataManager (ABC)
├── Preprocessor
├── SeedsReducer
├── OutlierRemover
└── Mixer
```

### 9.3 Shaper Hierarchy (7+ shapers)
```
Shaper (ABC)
├── SelectorShaper
├── SortShaper
├── MeanShaper
├── NormalizeShaper
├── PivotShaper
├── SplitApplyShaper
├── TransformerShaper
└── UniDfShaper
```

---

## 10. Architecture Patterns Found

### 10.1 Facade Pattern
**Location**: `ApplicationAPI` in `src/core/application_api.py`
**Description**: Single entry point for the UI to access all business logic. Composes
ServicesAPI, ParseService, ScannerService, and RepositoryStateManager. The web layer
ONLY interacts with core through this facade (plus direct model imports).

### 10.2 Repository Pattern
**Location**: `src/core/state/repositories/`
**Description**: State is abstracted behind repository interfaces. `SessionRepository`
is the aggregate root composing 7 child repositories:
1. `DataRepository` — raw/processed DataFrames
2. `ConfigRepository` — configuration dict, CSV path, temp directory
3. `ParserStateRepository` — variables, patterns, strategies, simulator
4. `PlotRepository` — plots list, current plot, counter
5. `PreviewRepository` — operation preview DataFrames
6. `HistoryRepository` — manager + portfolio operation history
7. `VisualizationRepository` — CSV pool, saved configurations

All repositories store data in `st.session_state` (Streamlit's session store).

### 10.3 Protocol Pattern (Dependency Inversion)
**Location**: All layer boundaries
**Description**: Python `Protocol` classes define contracts between layers:
- `StateManager` Protocol → `RepositoryStateManager` implementation
- `ServicesAPI` Protocol → `DefaultServicesAPI` implementation
- `SimulationParser` Protocol → `Gem5Parser` implementation
- `PlotProtocol` Protocol → `BasePlot` implementation
- `PlotDeserializer` Protocol → `BasePlot.from_dict` implementation

The core layer never depends on concrete implementations from web or parsing.

### 10.4 Factory Pattern
**Location**: 4 factories across all layers (see Factory Catalog §7)
**Description**: Polymorphic creation of domain objects. Each factory maintains a
registry mapping string type names to concrete classes.

### 10.5 Strategy Pattern
**Location**: `src/parsing/gem5/impl/strategies/`
**Description**: Interchangeable file parsing strategies:
- `SimpleStatsStrategy` — basic stats file parsing
- `ConfigAwareStrategy` — configuration-aware parsing with pattern matching
Both implement `FileParserStrategy` Protocol. Selected via `StrategyFactory`.

### 10.6 Command Pattern
**Location**: `src/parsing/gem5/impl/pool/job.py`
**Description**: `Job` ABC encapsulates work items (`ParseWork`, `ScanWork`) for
parallel execution in worker pools.

### 10.7 Singleton Pattern
**Location**: `ApplicationAPI` via `st.cache_resource`
**Description**: `get_api()` function in `app.py` uses Streamlit's caching to ensure
only one `ApplicationAPI` instance exists per session.

### 10.8 Adapter Pattern
**Location**: `src/web/pages/plot_adapters.py`
**Description**: Adapts `BasePlot` instances to satisfy `PlotHandle` and `ConfigRenderer`
protocols, bridging between the concrete plot implementation and the protocol-based
rendering system.

### 10.9 Observer Pattern (implicit)
**Location**: `StateManager.set_data(data, on_change=callback)`
**Description**: The `set_data` method accepts an optional `on_change` callback that
is triggered when data changes, allowing reactive updates.

### 10.10 Sentinel Value Pattern
**Location**: `src/core/models/visualization/resolvers.py`
**Description**: Typography, legend, and axis configs use sentinel values (`-1`, `-1.0`)
to indicate "use engine default". The `config_resolver` service resolves these to
actual values during rendering. This allows configs to be partially specified.

### 10.11 Mixin Pattern
**Location**: `PlotConfigUIMixin` (mixed into `BasePlot`)
**Description**: `BasePlot` inherits from `PlotConfigUIMixin` for UI configuration
methods, separating plot logic from UI concerns while keeping them on the same object.

### 10.12 Lazy Import Pattern
**Location**: `app.py` page routing, `BasePlot.from_dict`
**Description**: Page modules and plot types are imported only when activated.
Prevents loading the entire web layer for unused pages. Critical for keeping
Streamlit reruns fast.

---

## 11. Boundary Violations

### NONE FOUND ✅

The architecture is clean. There are no violations of the layering rules:
- ❌ Core never imports from Web
- ❌ Parsing never imports from Web
- ❌ Web never imports from Parsing
- ⚠️ Core imports 3 items from Parsing (deliberate facade bridge — analyzed in §4.2)

---

## 12. Dependency Injection Mechanism

The application uses **constructor injection** with Protocol types:

1. **`ApplicationAPI.__init__`**:
   ```python
   def __init__(
       self,
       plot_deserializer: PlotDeserializer | None = None,
       parser: SimulationParser | None = None,
   )
   ```
   - `plot_deserializer` injected as `BasePlot.from_dict` from `app.py`
   - `parser` defaults to `ParseService()` (Gem5Parser) if not provided

2. **`DataManager.__init__`**:
   ```python
   def __init__(self, api: ApplicationAPI)
   ```
   - All data managers receive ApplicationAPI via constructor

3. **Page functions**:
   ```python
   DataSourcePage(api).render()
   show_manage_plots_page(api)
   ```
   - All pages receive ApplicationAPI as argument

4. **Service composition** (in `DefaultServicesAPI`):
   ```python
   def __init__(self, state_manager: StateManager):
       self._managers = DefaultManagersAPI()
       self._data = DefaultDataServicesAPI(state_manager)
       self._shapers = DefaultShapersAPI(state_manager)
   ```

---

## 13. Package-Level Dependency Graph

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION (Web)                            │
│                                                                      │
│  pages/ ──→ controllers/ ──→ components/ ──→ rendering/              │
│    │              │               │               │                  │
│    │              └───────────────┴───────────────┘                  │
│    │                           │                                     │
│    │                    models/plot_protocols.py                      │
│    │                    models/plot_models.py                         │
│    │                    state/ui_state_manager.py                     │
│    │                           │                                     │
│    └───────────────────────────┼─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       DOMAIN (Core)                                  │
│                                                                      │
│  application_api.py  (FACADE)                                        │
│    ├── services/                                                     │
│    │   ├── services_api.py    (Protocol)                             │
│    │   ├── services_impl.py   (DefaultServicesAPI)                   │
│    │   ├── managers/          (arithmetic, outlier, reduction)        │
│    │   ├── data_services/     (CSV, config, variables, portfolio)     │
│    │   ├── shapers/           (factory, pipeline, 7+ shapers)        │
│    │   └── visualization/     (resolver, palette, interaction)        │
│    ├── models/                                                       │
│    │   ├── data_models.py     parsing_models.py  shaper_models.py    │
│    │   ├── plot_protocol.py   plot_config.py     history_models.py   │
│    │   └── visualization/     (figure, trace, axis, legend, etc.)    │
│    └── state/                                                        │
│        ├── state_manager.py   (Protocol)                             │
│        ├── repository_state_manager.py  (Implementation)             │
│        └── repositories/      (7 child repositories)                 │
│                                                                      │
│    application_api.py ──→ parsing.parser_protocol.SimulationParser    │
│    application_api.py ──→ parsing.registry.SimulatorRegistry          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │
┌──────────────────────────────────────────────────────────────────────┐
│                    DATA/INFRASTRUCTURE (Parsing)                      │
│                                                                      │
│  parser_protocol.py    (SimulationParser Protocol)                   │
│  registry.py           (SimulatorRegistry)                           │
│  parse_service.py      (shim → Gem5Parser)                           │
│  scanner_service.py    (shim → Gem5Scanner)                          │
│  gem5/                                                               │
│    ├── impl/                                                         │
│    │   ├── gem5_parser.py     gem5_scanner.py                        │
│    │   ├── pool/             (PerlWorkerPool, WorkPool, Job)         │
│    │   ├── scanning/         (scanner, pattern_aggregator)           │
│    │   └── strategies/       (simple, config_aware, perl_worker)     │
│    └── types/                (scalar, vector, distribution, etc.)    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

Legend:
  ──→  = imports / depends on
  ▲/▼  = allowed dependency direction
```

---

## 14. Private Module Conventions

Files prefixed with `_` are considered internal/private:
- `src/web/rendering/_connector_protocol.py` — internal connector contract
- `src/web/rendering/_render_result.py` — internal render result type
- `src/web/rendering/_heatmap_utils.py` — heatmap-specific rendering utilities
- `src/web/pages/ui/plotting/types/_trace_helpers.py` — shared trace-building helpers

---

## 15. Streamlit Integration Points

The architecture bridges with Streamlit in these key locations:

| Integration | File | Mechanism |
|------------|------|-----------|
| Singleton initialization | `app.py:54` | `@st.cache_resource` |
| Session state storage | All repositories | `st.session_state` as backing store |
| Page routing | `app.py:138-157` | Manual `if/elif` on sidebar selection |
| Data preview | `app.py:115-135` | `@st.fragment` for isolated rerun |
| UI State | `web/state/ui_state_manager.py` | Web-layer session state management |

---

## 16. File Count Summary

| Layer | `.py` Files | Packages | `__init__.py` Files |
|-------|-----------|----------|-------------------|
| Core | 81 | 12 | 12 |
| Parsing | 36 | 8 | 8 |
| Web | ~120 | 22 | 22 |
| **Total** | **~237** | **42** | **42** |

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `architecture/overview.md`, `architecture/layer-boundaries.md`, `architecture/design-patterns.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `architecture/system-overview.md`, `architecture/layer-boundaries.md`, `architecture/design-patterns.md`
- Step 18 (end-to-end data flow) — needs the layer map
- Step 19 (extension points) — needs protocol and factory catalogs
