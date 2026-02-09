# RING-5 Full Project Architecture

This document provides a comprehensive view of the RING-5 codebase architecture, including all modules, their dependencies, and the layered structure.

## Architecture Overview

```mermaid
flowchart TB
    subgraph LEAF["🌱 LEAF MODULES (no src dependencies)"]
        direction LR
        models["core/models/<br>parsing_models.py (ScannedVariable, StatConfig)<br>portfolio_models.py (PortfolioData)<br>plot_protocol.py (PlotProtocol)<br>config/ (ConfigValidator, ConfigTemplateGenerator)"]
        common["core/common/<br>utils.py"]
        perf["core/performance.py"]
    end

    subgraph STATE["📦 STATE LAYER"]
        direction TB
        repos["state/repositories/<br>data, config, parser_state,<br>plot, preview, session"]
        state_mgr["state/state_manager.py<br>RepositoryStateManager"]
        repos --> models
        state_mgr --> repos
    end

    subgraph PARSING["🔬 PARSING LAYER"]
        direction TB
        protocols["Protocols<br>parser_protocol.py<br>scanner_protocol.py<br>parser_api.py"]
        factory_parse["factory.py<br>ParserAPIFactory"]

        subgraph GEM5["gem5/ Implementation"]
            direction TB
            types_g["types/<br>base, scalar, vector,<br>distribution, histogram,<br>configuration, type_mapper"]
            pool_g["impl/pool/<br>job, work_pool, pool,<br>parse_work, scan_work"]
            scanning_g["impl/scanning/<br>scanner, pattern_aggregator,<br>gem5_scan_work"]
            strategies_g["impl/strategies/<br>factory, file_parser_strategy,<br>simple, config_aware,<br>gem5_parse_work, perl_worker_pool"]
            impl_g["impl/<br>gem5_parser.py<br>gem5_scanner.py<br>gem5_parser_api.py"]
        end

        protocols --> models
        factory_parse --> protocols
        factory_parse -.->|lazy| impl_g
        types_g --> models
        scanning_g --> types_g
        scanning_g --> pool_g
        strategies_g --> types_g
        strategies_g --> pool_g
        impl_g --> scanning_g
        impl_g --> strategies_g
        impl_g --> pool_g
    end

    subgraph SERVICES["⚙️ SERVICES LAYER"]
        direction TB
        svc_api["ServicesAPI / DefaultServicesAPI<br><i>(Facade + Composition Root)</i>"]

        subgraph MANAGERS["managers/"]
            direction TB
            mgr_api["ManagersAPI<br>DefaultManagersAPI"]
            arith_svc["arithmetic_service.py"]
            outlier_svc["outlier_service.py"]
            reduction_svc["reduction_service.py"]
            mgr_api --> arith_svc
            mgr_api --> outlier_svc
            mgr_api --> reduction_svc
        end

        subgraph DATA_SVC["data_services/"]
            direction TB
            ds_api["DataServicesAPI<br>DefaultDataServicesAPI"]
            path_svc["path_service.py"]
            config_svc["config_service.py"]
            csv_svc["csv_pool_service.py"]
            var_svc["variable_service.py"]
            portfolio_svc["portfolio_service.py"]
            ds_api --> path_svc
            ds_api --> config_svc
            ds_api --> csv_svc
            ds_api --> var_svc
            ds_api --> portfolio_svc
            config_svc --> path_svc
            csv_svc --> path_svc
            csv_svc --> perf
            portfolio_svc --> state_mgr
        end

        subgraph SHAPERS["shapers/"]
            direction TB
            sh_api["ShapersAPI<br>DefaultShapersAPI"]
            pipeline_svc["pipeline_service.py"]

            shaper_base["shaper.py (abstract)"]
            shaper_impl["uni_df_shaper.py"]
            shaper_factory["factory.py"]
            shaper_types["impl/<br>mean, normalize, sort,<br>transformer, selectors"]
            shaper_impl --> shaper_base
            shaper_types --> shaper_impl
            shaper_factory --> shaper_types

            sh_api --> pipeline_svc
            sh_api --> shaper_factory
            pipeline_svc --> shaper_factory
            pipeline_svc --> common
        end

        svc_api --> mgr_api
        svc_api --> ds_api
        svc_api --> sh_api
        svc_api -->|"injects pipelines_dir: Path"| sh_api
    end

    subgraph APP_API["🎯 APPLICATION API (Facade)"]
        app_api["application_api.py<br>ApplicationAPI"]
    end

    app_api --> factory_parse
    app_api --> models
    app_api --> svc_api
    app_api --> state_mgr

    subgraph WEB["🖥️ WEB LAYER (Streamlit UI)"]
        direction TB
        subgraph PAGES["pages/"]
            pages_list["data_source.py<br>upload_data.py<br>data_managers.py<br>manage_plots.py<br>portfolio.py<br>performance.py"]
        end

        subgraph UI_COMP["ui/components/"]
            data_comp["data_source_components.py<br>upload_components.py<br>data_manager_components.py<br>plot_manager_components.py<br>variable_editor.py"]
            ui_utils["card_components.py<br>layout_components.py<br>data_components.py<br>plot_config_components.py"]
            shaper_ui["shapers/<br>mean_config, normalize_config,<br>selector_transformer_configs"]
        end

        subgraph DATA_MGR["ui/data_managers/impl/"]
            dm_list["mixer.py<br>outlier_remover.py<br>preprocessor.py<br>seeds_reducer.py"]
        end

        subgraph PLOTTING["ui/plotting/"]
            plot_core["base_plot.py<br>plot_factory.py<br>plot_renderer.py<br>plot_service.py"]
            plot_types["types/<br>bar_plot, grouped_bar_plot,<br>stacked_bar_plot, line_plot,<br>scatter_plot, histogram_plot"]
            styles["styles/<br>manager, applicator,<br>base_ui, bar_ui, line_ui,<br>colors"]
            export["export/<br>latex_export_service.py<br>presets/, converters/"]
            plot_types --> plot_core
            plot_core --> styles
            plot_core --> export
        end

        shaper_config["shaper_config.py"]

        pages_list --> app_api
        pages_list --> UI_COMP
        pages_list --> DATA_MGR
        pages_list --> PLOTTING
        data_comp --> app_api
        data_comp --> models
        dm_list --> mgr_api
        PLOTTING --> perf
        shaper_config --> shaper_factory
        shaper_config --> shaper_ui
    end

    %% Cross-layer dependencies
    impl_g --> common
    strategies_g --> common

    classDef leaf fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef facade fill:#fff3e0,stroke:#ff9800,stroke-width:3px
    classDef core fill:#e3f2fd,stroke:#2196f3,stroke-width:1px
    classDef web fill:#fce4ec,stroke:#e91e63,stroke-width:1px

    class models,common,perf leaf
    class app_api facade
```

## Layer Descriptions

### 🌱 LEAF MODULES
Foundational modules with **zero** internal dependencies. These form the stable base of the architecture:
- **models/**: Core data models, protocols, and configuration (ScannedVariable, StatConfig, PortfolioData, PlotProtocol, ConfigValidator, ConfigTemplateGenerator)
- **common/utils.py**: Shared utilities (path normalization, JSON validation)
- **performance.py**: Caching, profiling decorators

### 📦 STATE LAYER
Application state management using the Repository pattern:
- **repositories/**: Individual state stores (data, config, parser, plot, preview, session)
- **state_manager.py**: Facade composing all repositories

### 🔬 PARSING LAYER
gem5 simulator output parsing with Strategy pattern:
- **Protocols**: Simulator-agnostic interfaces (ParserProtocol, ScannerProtocol)
- **Factory**: Creates parser instances by simulator type
- **gem5/**: Complete gem5 implementation
  - **types/**: Stat type handlers (scalar, vector, distribution, histogram)
  - **impl/pool/**: Work pool for parallel execution
  - **impl/scanning/**: Variable discovery and pattern aggregation
  - **impl/strategies/**: Parsing strategies (simple, config-aware)

### ⚙️ SERVICES LAYER
Business logic services organized into three domain-aligned submodules:
- **ServicesAPI / DefaultServicesAPI**: Top-level facade and composition root
- **managers/**: Stateless data transformation operations (arithmetic, outlier removal, seed reduction)
- **data_services/**: Data storage and retrieval (CSV pool, config persistence, path navigation, variable management, portfolio snapshots)
- **shapers/**: Pipeline CRUD, shaper execution, and data transformation strategies (mean, normalize, sort, select)

Each submodule has its own Protocol (API) and default implementation. Cross-module dependencies are resolved via dependency injection at the composition root.

### 🎯 APPLICATION API (Facade)
Single entry point for all backend operations:
- Orchestrates parsing, CSV loading, pipelines, portfolios
- All web layer components import through this facade

### 🖥️ WEB LAYER (Streamlit UI)
Presentation layer:
- **pages/**: Page-level components (data source, upload, plots, portfolio)
- **ui/components/**: Reusable UI widgets
- **ui/data_managers/**: Data preprocessing UIs (mixer, outlier, reducer)
- **ui/plotting/**: Plot creation, rendering, styles, LaTeX export
- **ui/shaper_config.py**: Shaper pipeline UI

## Key Design Principles

1. **Layered Architecture**: Strict dependency direction (leaf → core → web)
2. **Facade Pattern**: ApplicationAPI as clean boundary between core and web
3. **Repository Pattern**: State management with specialized repositories
4. **Strategy Pattern**: Pluggable parsing strategies and shapers
5. **Factory Pattern**: Dynamic creation of parsers, shapers, plots
6. **Protocol-Based Interfaces**: Type-safe contracts between layers

## Dependency Rules

| From Layer | Can Import From |
|------------|-----------------|
| Leaf Modules | *(nothing)* |
| State | models |
| Parsing | models, common |
| Services | common, performance, models, state |
| ApplicationAPI | parsing, services (facade), state, models |
| Web | ApplicationAPI, services (managers), performance, models |

**Important**: The only `core→web` dependency is a `TYPE_CHECKING`-only import in `session_repository.py` for `BasePlot` type hints.
