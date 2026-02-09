# RING-5 Full Project Architecture

This document provides a comprehensive view of the RING-5 codebase architecture, including all modules, their dependencies, and the layered structure.

## Architecture Overview

```mermaid
flowchart TB
    subgraph LEAF["🌱 LEAF MODULES (no src dependencies)"]
        direction LR
        domain["core/domain/<br>models.py, plot_protocol.py"]
        common["core/common/<br>utils.py"]
        config_mod["core/config/<br>config_manager.py"]
        perf["core/performance.py"]
        p_models["parsing/models.py<br>ScannedVariable, StatConfig"]
    end

    subgraph STATE["📦 STATE LAYER"]
        direction TB
        repos["state/repositories/<br>data, config, parser_state,<br>plot, preview, session"]
        state_mgr["state/state_manager.py<br>RepositoryStateManager"]
        repos --> domain
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

        protocols --> p_models
        factory_parse --> protocols
        factory_parse -.->|lazy| impl_g
        types_g --> p_models
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
        path_svc["path_service.py"]
        config_svc["config_service.py"]
        csv_svc["csv_pool_service.py"]
        pipeline_svc["pipeline_service.py"]
        portfolio_svc["portfolio_service.py"]
        var_svc["variable_service.py<br>variable_validation.py"]
        compute_svc["arithmetic_service.py<br>mixer_service.py<br>reduction_service.py<br>outlier_service.py"]

        subgraph SHAPERS["shapers/"]
            shaper_base["shaper.py (abstract)"]
            shaper_impl["uni_df_shaper.py<br>multi_df_shaper.py"]
            shaper_factory["factory.py"]
            shaper_types["impl/<br>mean, normalize, sort,<br>transformer, selectors"]
            shaper_impl --> shaper_base
            shaper_types --> shaper_impl
            shaper_factory --> shaper_types
        end

        config_svc --> path_svc
        csv_svc --> path_svc
        csv_svc --> perf
        pipeline_svc --> shaper_factory
        pipeline_svc --> common
        portfolio_svc --> state_mgr
    end

    subgraph APP_API["🎯 APPLICATION API (Facade)"]
        app_api["application_api.py<br>ApplicationAPI"]
    end

    app_api --> factory_parse
    app_api --> p_models
    app_api --> csv_svc
    app_api --> pipeline_svc
    app_api --> portfolio_svc
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
        data_comp --> p_models
        dm_list --> compute_svc
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

    class domain,common,config_mod,perf,p_models leaf
    class app_api facade
```

## Layer Descriptions

### 🌱 LEAF MODULES
Foundational modules with **zero** internal dependencies. These form the stable base of the architecture:
- **domain/**: Core type definitions (PortfolioData, PlotProtocol)
- **common/utils.py**: Shared utilities (path normalization, JSON validation)
- **config/**: Configuration schema validation
- **performance.py**: Caching, profiling decorators
- **parsing/models.py**: Data models (ScannedVariable, StatConfig)

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
Business logic services:
- **path_service.py**: Centralized file system navigation
- **csv_pool_service.py**: CSV file discovery and caching
- **pipeline_service.py**: Shaper pipeline composition
- **portfolio_service.py**: Analysis state persistence
- **shapers/**: Data transformation strategies (mean, normalize, sort, select)
- **Compute services**: arithmetic, mixer, reduction, outlier

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
| State | domain |
| Parsing | models, common |
| Services | common, performance, domain, state, shapers |
| ApplicationAPI | parsing, services, state |
| Web | ApplicationAPI, services (compute), performance |

**Important**: The only `core→web` dependency is a `TYPE_CHECKING`-only import in `session_repository.py` for `BasePlot` type hints.
