---
title: "File Locations Quick Reference"
parent: Quick Reference
grand_parent: Engineering Reference
nav_order: 1
---

# File Locations Quick Reference

> Where is X in RING-5 Unified Engine v2?

- **Architecture**: 3-layer (Core / Parsing / Web), a few hundred `.py` files
- **Root entry point**: `app.py`
- **Source root**: `src/` | **Test root**: `tests/`

---

## 1. Entry Points

- **Streamlit app entry**: `app.py`
- **ApplicationAPI facade**: `src/core/application_api.py`
- **Parsing public API**: `src/parsing/__init__.py` (re-exports ParseService, ScannerService)
- **Page modules** (imported lazily in `app.py`):
  - `src/web/pages/data_source.py` -- DataSourcePage
  - `src/web/pages/data_managers.py` -- show_data_managers_page
  - `src/web/pages/manage_plots.py` -- show_manage_plots_page
  - `src/web/pages/portfolio.py` -- show_portfolio_page
  - `src/web/pages/documentation.py` -- show_documentation_page

---

## 2. Models

### Core Data Models (`src/core/models/`)

- **ParseVariableConfig, CsvPoolEntry, ScannedVariableDict**: `data_models.py`
- **StatConfig, ScannedVariable, ParseBatchResult**: `parsing_models.py`
- **ShaperStepConfig, PipelineStep**: `shaper_models.py`
- **PortfolioData, PortfolioConfig**: `portfolio_models.py`
- **PlotProtocol, PlotDeserializer**: `plot_protocol.py`
- **PlotConfig TypeAlias**: `plot_config.py`
- **OperationRecord, HistoryEntry**: `history_models.py`
- **CSV format contract types**: `csv_contract.py`
- **ConfigManager**: `config/config_manager.py`

### Visualization Config Models (`src/core/models/visualization/`)

- **FigureConfig**: `figure_config.py`
- **TraceConfig, BarTraceConfig, LineTraceConfig**: `trace_config.py`
- **AxisConfig**: `axis_config.py`
- **LegendConfig**: `legend_config.py`
- **TypographyConfig**: `typography_config.py`
- **AnnotationConfig, ShapeConfig**: `annotation_config.py`
- **DataLabelConfig**: `data_label_config.py`
- **SeriesStyleConfig**: `series_style_config.py`
- **Color palettes**: `palettes.py`
- **Sentinel resolvers (-1 to default)**: `resolvers.py`
- **TraceBuildResult**: `trace_build_result.py`

### Web / Parsing Models

- **PlotDisplayConfig, web plot types**: `src/web/models/plot_models.py`
- **12 rendering Protocols (PlotHandle, ConfigRenderer, etc.)**: `src/web/models/plot_protocols.py`
- **gem5-specific models**: `src/parsing/gem5/models.py`

---

## 3. Services

### Service Facades (`src/core/services/`)

- **ServicesAPI Protocol**: `services_api.py`
- **DefaultServicesAPI**: `services_impl.py`

### Managers -- Stateless Data Transforms (`src/core/services/managers/`)

- **ManagersAPI Protocol**: `managers_api.py`
- **DefaultManagersAPI**: `managers_impl.py`
- **ArithmeticService**: `arithmetic_service.py`
- **OutlierService (IQR/z-score)**: `outlier_service.py`
- **ReductionService (mean/median/mode)**: `reduction_service.py`

### Data Services (`src/core/services/data_services/`)

- **DataServicesAPI Protocol (25+ methods)**: `data_services_api.py`
- **DefaultDataServicesAPI**: `data_services_impl.py`
- **CsvPoolService**: `csv_pool_service.py`
- **ConfigService (save/load)**: `config_service.py`
- **PathService**: `path_service.py`
- **VariableService**: `variable_service.py`
- **PortfolioService**: `portfolio_service.py`
- **PatternIndexService**: `pattern_index_service.py`

### Shapers -- Data Transformation Pipeline (`src/core/services/shapers/`)

- **ShapersAPI Protocol**: `shapers_api.py`
- **DefaultShapersAPI**: `shapers_impl.py`
- **Shaper ABC**: `shaper.py`
- **ShaperFactory**: `factory.py`
- **PipelineService**: `pipeline_service.py`
- **Pipeline validation**: `validation.py`
- **UniDfShaper**: `uni_df_shaper.py`
- **Concrete shapers** (`impl/`): `selector.py`, `sort.py`, `mean.py`, `normalize.py`, `pivot.py`, `split_apply.py`, `transformer.py`
- **Selector algorithms** (`impl/selector_algorithms/`): `item_selector.py`, `column_selector.py`, `condition_selector.py`

### Visualization Services (`src/core/services/visualization/`)

- **ConfigResolver**: `config_resolver.py`
- **PaletteService**: `palette_service.py`
- **Plot interaction helpers**: `plot_interaction.py`
- **PortfolioMigrator**: `src/core/services/portfolio_migrator.py`

---

## 4. State Management

### Core State (`src/core/state/`)

- **StateManager Protocol (40+ methods)**: `state_manager.py`
- **RepositoryStateManager**: `repository_state_manager.py`

### Repositories (`src/core/state/repositories/`)

- **SessionRepository (aggregate root)**: `session_repository.py`
- **DataRepository (DataFrames)**: `data_repository.py`
- **ConfigRepository (config dict, CSV path)**: `config_repository.py`
- **ParserStateRepository (variables, patterns)**: `parser_state_repository.py`
- **PlotRepository (plots list, current plot)**: `plot_repository.py`
- **PreviewRepository (operation previews)**: `preview_repository.py`
- **HistoryRepository**: `history_repository.py`
- **VisualizationRepository (CSV pool, saved configs)**: `visualization_repository.py`

### Other

- **UI state manager (web-layer)**: `src/web/state/ui_state_manager.py`
- **Shared utilities**: `src/core/common/utils.py`
- **Performance monitoring**: `src/core/performance.py`

---

## 5. Parsing

### Protocols and Registry (`src/parsing/`)

- **SimulationParser Protocol**: `parser_protocol.py`
- **SimulatorRegistry**: `registry.py`
- **Shared framework**: `framework/` (`work_pool.py`, `job.py`, `file_discovery.py`)

### gem5 Implementation (`src/parsing/gem5/impl/`)

- **Gem5Parser**: `gem5_parser.py`
- **Gem5Parser** (parse + scan + CSV; implements `SimulationParser`): `gem5_parser.py`

### Strategies (`src/parsing/gem5/impl/strategies/`)

- **FileParserStrategy Protocol**: `file_parser_strategy.py`
- **StrategyFactory**: `factory.py`
- **SimpleStatsStrategy**: `simple.py`
- **ConfigAwareStrategy**: `config_aware.py`
- **Perl worker pool**: `perl_worker_pool.py`

### Stat Types (`src/parsing/gem5/types/`)

- **StatTypeRegistry**: `__init__.py`
- **TypeMapper**: `type_mapper.py`
- **Types**: `scalar.py`, `vector.py`, `distribution.py`, `histogram.py`, `configuration.py`

### Pool (`src/parsing/gem5/impl/pool/`)

- **Job ABC**: `job.py` | **PerlWorkerPool**: `pool.py` | **WorkPool**: `work_pool.py`

### Scanning (`src/parsing/gem5/impl/scanning/`)

- **Scanner**: `scanner.py` | **Pattern aggregator**: `pattern_aggregator.py`

---

## 6. Pages

- **Data Source**: `src/web/pages/data_source.py`
- **Data Managers**: `src/web/pages/data_managers.py`
- **Manage Plots**: `src/web/pages/manage_plots.py`
- **Portfolio (Save/Load)**: `src/web/pages/portfolio.py`
- **Documentation**: `src/web/pages/documentation.py`
- **Plot adapters**: `src/web/pages/plot_adapters.py`
- **Shaper config UI**: `src/web/pages/ui/shaper_config.py`

---

## 7. Components

### Common (`src/web/components/common/`)

- `card_components.py`, `data_components.py`, `history_components.py`, `plot_creation.py`
- `pipeline.py`, `pipeline_step.py`, `plot_controls.py`, `plot_selector.py`
- `chart_display.py`, `layout_components.py`, `filtered_selector.py`, `reorderable_list.py`

### Data Source (`src/web/components/data_source/`)

- `data_source_components.py`, `variable_editor.py`, `pattern_index_selector.py`

### Data Managers (`src/web/components/data_managers/`)

- **DataManager ABC**: `data_manager.py` | **Shared UI**: `data_manager_components.py`
- **Concrete**: `preprocessor.py`, `seeds_reducer.py`, `outlier_remover.py`, `mixer.py`

### Shapers (`src/web/components/shapers/`)

- `selector_transformer_configs.py`, `sort_config.py`, `mean_config.py`, `normalize_config.py`, `pivot_config.py`, `split_apply_config.py`

### Plotting (`src/web/components/plotting/`)

- **Interactive display**: `interactive_plot.py`
- **Config** (`config/`): `base_plot_config.py`, `plot_config_components.py`, `grouped_bar_config.py`, `stacked_bar_config.py`, `grouped_stacked_bar_config.py`, `histogram_config.py`, `heatmap_config.py`, `dual_axis_config.py`, `dual_axis_settings.py`

---

## 8. Controllers

All under `src/web/controllers/plot/`:

- **Creation controller**: `creation_controller.py`
- **Pipeline controller**: `pipeline_controller.py`
- **Render controller**: `render_controller.py`

---

## 9. Rendering (`src/web/rendering/`)

- **ConfigSpecBuilder, PlotlyFigureSpecBuilder**: `config_builder.py`
- **FigureSpecToPlotly**: `plotly_connector.py` | **FigureSpecToMatplotlib**: `matplotlib_connector.py`
- **MatplotlibTraceRenderer**: `matplotlib_trace_renderer.py` | **traces_to_plotly**: `trace_to_plotly.py`
- **EngineManager**: `engine_manager.py` | **Byte export**: `figure_export.py`
- **Private**: `_connector_protocol.py`, `_render_result.py`, `_heatmap_utils.py`
- **Widgets**: `widgets/widget_def.py`, `widgets/widget_renderer.py`

---

## 10. Plot Types (9 types)

All under `src/web/pages/ui/plotting/types/`:

| Type | File |
|------|------|
| BarPlot | `bar_plot.py` |
| LinePlot | `line_plot.py` |
| ScatterPlot | `scatter_plot.py` |
| HistogramPlot | `histogram_plot.py` |
| HeatmapPlot | `heatmap_plot.py` |
| GroupedBarPlot | `grouped_bar_plot.py` |
| StackedBarPlot | `stacked_bar_plot.py` |
| GroupedStackedBarPlot | `grouped_stacked_bar_plot.py` |
| DualAxisBarDotPlot | `dual_axis_bar_dot_plot.py` |

**Plotting infrastructure** (`src/web/pages/ui/plotting/`):

- **BasePlot ABC**: `base_plot.py`
- **PlotFactory**: `plot_factory.py`
- **PlotRenderer**: `plot_renderer.py`
- **PlotConfigUIMixin**: `plot_config_ui.py`
- **PlotService**: `plot_service.py`
- **Settings pills**: `settings_pills.py`
- **Download section**: `download_section.py`

**Style UI** (`src/web/pages/ui/plotting/styles/`):

- `factory.py`, `base_ui.py`, `bar_ui.py`, `line_ui.py`, `colors.py`, `applicator.py`

---

## 11. Settings Panels (11 pills)

All under `src/web/components/plotting/settings/`:

- **Widget factory**: `widget_factory.py`
- **Layout**: `layout_settings.py` | **Typography**: `typography_settings.py`
- **Axes**: `axes_settings.py` | **Legend**: `legend_settings.py`
- **Colors**: `colors_settings.py` | **Data labels**: `data_labels_settings.py`
- **Ordering**: `ordering_settings.py` | **Engine**: `engine_settings.py`
- **Reference line**: `reference_line_settings.py` | **Shapes**: `shapes_settings.py`
- **Advanced (3 Protocols)**: `advanced_settings.py`

---

## 12. Export

- **Download section UI**: `src/web/pages/ui/plotting/download_section.py`
- **Byte export (UI-free)**: `src/web/rendering/figure_export.py`
- **Config builder**: `src/web/rendering/config_builder.py`

---

## 13. Tests

### Directory Structure

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Unit tests (~130 files) |
| `tests/integration/` | Integration tests (~37 files) |
| `tests/ui/` | E2E UI tests with Streamlit (~10 files) |
| `tests/ui_unit/` | UI component unit tests (~14 files) |
| `tests/ui_logic/` | UI logic/controller tests (~11 files) |
| `tests/visual/` | Visual/screenshot tests (Playwright) |
| `tests/performance/` | Performance regression tests |
| `tests/tests_principle_compliance/` | TDD compliance checks |
| `tests/helpers/` | Test helper utilities |
| `tests/data/` | Test data fixtures |

### Key Test Files by Feature

- **ApplicationAPI**: `tests/unit/test_application_api.py`
- **Architecture**: `tests/unit/test_architecture_boundary.py`
- **State**: `tests/unit/test_state_repositories.py`, `tests/unit/test_repository_state_manager.py`
- **Parsing**: `tests/unit/test_parsing_services.py`, `tests/unit/test_parse_service.py`
- **Scanner**: `tests/unit/test_scanning.py`, `tests/unit/test_scanner_comprehensive.py`
- **Shapers**: `tests/unit/test_pipeline_service.py`, `tests/unit/test_shaper_edge_cases.py`
- **Plot types**: `tests/unit/test_plot_types.py`, `tests/unit/test_plot_classes.py`
- **Rendering**: `tests/unit/test_trace_to_plotly.py`, `tests/unit/test_engine_manager.py`
- **Portfolio**: `tests/integration/test_portfolio_round_trip.py`
- **Settings pills**: `tests/unit/test_settings_pills.py`, `tests/ui_logic/test_settings_pills.py`
- **Controllers**: `tests/unit/test_plot_controllers.py`, `tests/ui_logic/test_creation_controller.py`
- **Full pipeline E2E**: `tests/integration/test_full_pipeline_e2e.py`
- **Visual E2E**: `tests/visual/test_comprehensive_e2e.py`
