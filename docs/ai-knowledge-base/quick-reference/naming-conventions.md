---
title: "Naming Conventions -- RING-5 Unified Engine v2"
parent: Quick Reference
grand_parent: AI Knowledge Base
nav_order: 3
---

# Naming Conventions -- RING-5 Unified Engine v2

## 1. File Naming

| Convention | Pattern | Examples |
|---|---|---|
| General modules | `snake_case.py` | `src/core/services/shapers/factory.py`, `src/web/rendering/engine_manager.py` |
| Protocol files | `*_protocol.py` | `src/parsing/parser_protocol.py`, `src/core/models/plot_protocol.py` |
| Private modules | `_*.py` (underscore prefix) | `src/web/rendering/_connector_protocol.py`, `src/web/rendering/_render_result.py`, `src/web/rendering/_heatmap_utils.py` |
| Service files | `*_service.py` | `src/parsing/parse_service.py`, `src/core/services/data_services/portfolio_service.py` |
| Config files | `*_config.py` | `src/core/models/visualization/figure_config.py`, `src/core/models/visualization/axis_config.py` |
| Repository files | `*_repository.py` | `src/core/state/repositories/plot_repository.py`, `src/core/state/repositories/data_repository.py` |
| Controller files | `*_controller.py` | `src/web/controllers/plot/render_controller.py`, `src/web/controllers/plot/creation_controller.py` |
| Settings UI files | `*_settings.py` | `src/web/components/plotting/settings/legend_settings.py`, `src/web/components/plotting/settings/axes_settings.py` |
| Test files | `test_*.py` | `tests/unit/test_pipeline_service.py`, `tests/integration/test_plot_lifecycle.py` |

## 2. Class Naming

| Convention | Pattern | Examples |
|---|---|---|
| Standard classes | `PascalCase` | `ShaperFactory`, `PlotFactory`, `FigureConfig` |
| Abstract base classes | `PascalCase(ABC)` | `Shaper(ABC)`, `DataManager(ABC)`, `Job(ABC)` |
| Protocol classes | `*Protocol(Protocol)` | `PlotProtocol(Protocol)` |
| Config dataclasses | `*Config` | `FigureConfig`, `AxisConfig`, `LegendConfig`, `TypographyConfig`, `MarginsConfig` |
| Repository classes | `*Repository` | `PlotRepository`, `DataRepository`, `ConfigRepository`, `HistoryRepository` |
| Controller classes | `*Controller` | `PlotRenderController`, `PipelineController`, `PlotCreationController` |
| Factory classes | `*Factory` | `ShaperFactory`, `PlotFactory` |
| Service classes | `*Service` | `PipelineService`, `PortfolioService`, `VariableService` |
| Private helper classes | `_PascalCase` (underscore prefix) | `_PlotUIState` |

## 3. Factory Registry Keys -- Shapers

| Registry Key | Class | Display Name |
|---|---|---|
| `"mean"` | `Mean` | `"Mean Calculator"` |
| `"columnSelector"` | `ColumnSelector` | `"Column Selector"` |
| `"conditionSelector"` | `ConditionSelector` | `"Filter"` |
| `"itemSelector"` | `ItemSelector` | `"Item Selector"` |
| `"normalize"` | `Normalize` | `"Normalize"` |
| `"pivotLonger"` | `PivotLonger` | `"Pivot Longer (Melt)"` |
| `"pivotWider"` | `PivotWider` | `"Pivot Wider"` |
| `"sort"` | `Sort` | `"Sort"` |
| `"splitApply"` | `SplitApply` | `"Split-Apply (Per-Axis)"` |
| `"transformer"` | `Transformer` | `"Transformer"` |

Shaper keys use **camelCase** (`"columnSelector"`, `"pivotLonger"`). Defined in `src/core/services/shapers/factory.py`.

## 4. Factory Registry Keys -- Plot Types

| Registry Key | Class | Display Name | Category |
|---|---|---|---|
| `"bar"` | `BarPlot` | `"Bar Chart"` | `"basic"` |
| `"line"` | `LinePlot` | `"Line Chart"` | `"basic"` |
| `"scatter"` | `ScatterPlot` | `"Scatter Plot"` | `"basic"` |
| `"grouped_bar"` | `GroupedBarPlot` | `"Grouped Bar"` | `"comparison"` |
| `"stacked_bar"` | `StackedBarPlot` | `"Stacked Bar"` | `"comparison"` |
| `"grouped_stacked_bar"` | `GroupedStackedBarPlot` | `"Grouped Stacked Bar"` | `"comparison"` |
| `"dual_axis_bar_dot"` | `DualAxisBarDotPlot` | `"Dual Axis Bar Dot"` | `"comparison"` |
| `"heatmap"` | `HeatmapPlot` | `"Heatmap"` | `"distribution"` |
| `"histogram"` | `HistogramPlot` | `"Histogram"` | `"distribution"` |

Plot keys use **snake_case** (`"grouped_bar"`, `"dual_axis_bar_dot"`). Defined in `src/web/pages/ui/plotting/plot_factory.py`.

## 5. Config Field Naming Prefixes

| Prefix | Domain | Source File | Examples |
|---|---|---|---|
| `font_size_*` | Typography per-element sizes (pts) | `src/core/models/visualization/typography_config.py` | `font_size_base`, `font_size_title`, `font_size_xlabel`, `font_size_ylabel`, `font_size_ticks`, `font_size_legend` |
| `bold_*` | Typography bold flags | `src/core/models/visualization/typography_config.py` | `bold_title`, `bold_xlabel`, `bold_ylabel`, `bold_ticks`, `bold_annotations`, `bold_legend` |
| `tick_*` | Axis tick configuration | `src/core/models/visualization/axis_config.py` | `tick_angle`, `tick_pad`, `tick_ha`, `tick_offset`, `tick_values`, `tick_text`, `tick_font_color` |
| `grid_*` | Axis grid styling | `src/core/models/visualization/axis_config.py` | `grid_color`, `grid_width` |
| `axis_*` | Axis line styling | `src/core/models/visualization/axis_config.py` | `axis_color`, `axis_line_color`, `axis_line_width` |
| `label_*` | Axis label positioning | `src/core/models/visualization/axis_config.py` | `label_pad`, `label_position`, `label_standoff`, `label_aliases` |
| `group_label_*` | X-axis group labels | `src/core/models/visualization/axis_config.py` | `group_label_offset`, `group_label_alternate`, `group_label_alt_spacing` |
| `position_*` | Legend positioning | `src/core/models/visualization/legend_config.py` | `position_x`, `position_y` |
| `anchor_*` | Legend anchor points | `src/core/models/visualization/legend_config.py` | `anchor_x`, `anchor_y` |
| `border_*` | Legend border styling | `src/core/models/visualization/legend_config.py` | `border_width`, `border_color` |
| `*_bgcolor` | Background colors | `src/core/models/visualization/figure_config.py` | `paper_bgcolor`, `plot_bgcolor` |
| `bar*` | Bar layout gaps | `src/core/models/visualization/figure_config.py` | `barmode`, `bargap`, `bargroupgap`, `bar_width_scale` |

## 6. Session State Key Naming

| Pattern | Builder Method | Examples |
|---|---|---|
| `plot.{id}.{suffix}` | `WidgetKeyBuilder.plot_key(id, suffix)` | `"plot.1.auto_refresh"`, `"plot.2.dialog_save"` |
| `manager.{name}.{suffix}` | `WidgetKeyBuilder.manager_key(name, suffix)` | `"manager.mixer.mode"` |
| `g.{suffix}` | `WidgetKeyBuilder.global_key(suffix)` | `"g.theme"` |
| `nav.{suffix}` | Direct string | `"nav.current_page"`, `"nav.current_tab"` |
| `plot.pending_updates` | Direct string | `"plot.pending_updates"` |
| `export.last_path` | Direct string | `"export.last_path"` |

All session state keys are managed through `src/web/state/ui_state_manager.py`. The `WidgetKeyBuilder` class centralizes key construction for collision-free, namespaced strings.

## 7. Module Organization

| Directory Pattern | Purpose | Examples |
|---|---|---|
| `impl/` | Concrete implementations | `src/core/services/shapers/impl/mean.py`, `src/parsing/gem5/impl/gem5_parser.py` |
| `impl/pool/` | Worker pool internals | `src/parsing/gem5/impl/pool/work_pool.py`, `src/parsing/gem5/impl/pool/job.py` |
| `impl/strategies/` | Strategy pattern implementations | `src/parsing/gem5/impl/strategies/simple.py`, `src/parsing/gem5/impl/strategies/config_aware.py` |
| `impl/selector_algorithms/` | Selector algorithm variants | `src/core/services/shapers/impl/selector_algorithms/column_selector.py` |
| `types/` | Type hierarchies and type-specific modules | `src/parsing/gem5/types/scalar.py`, `src/web/pages/ui/plotting/types/bar_plot.py` |
| `config/` | Per-plot-type config UI | `src/web/components/plotting/config/histogram_config.py` |
| `settings/` | Settings panel UI components | `src/web/components/plotting/settings/legend_settings.py` |
| `repositories/` | State repository classes | `src/core/state/repositories/plot_repository.py` |
| `data_services/` | Domain data services | `src/core/services/data_services/portfolio_service.py` |
| `controllers/` | Web layer controllers | `src/web/controllers/plot/render_controller.py` |
| `common/` | Shared/reusable components | `src/web/components/common/` |

## 8. Test File Naming

| Test Category | Directory | Naming Pattern | Examples |
|---|---|---|---|
| Unit tests | `tests/unit/` | `test_*.py` | `test_pipeline_service.py`, `test_shapers_extended.py` |
| Unit sub-packages | `tests/unit/core/visualization/` | `test_*.py` | `test_figure_spec.py`, `test_legend_spec.py` |
| Integration tests | `tests/integration/` | `test_*.py` | `test_plot_lifecycle.py`, `test_gem5_parsing.py` |
| UI unit tests | `tests/ui_unit/` | `test_*.py` | `test_shaper_config_logic.py`, `test_layout_components.py` |
| E2E (Streamlit AppTest) | `tests/ui/` | `test_e2e_*.py` | `test_e2e_data_managers.py`, `test_e2e_full_chain.py` |
| Visual (Playwright) | `tests/visual/` | `test_*.py` | `test_navigation.py`, `test_manage_plots.py` |
| Visual page objects | `tests/visual/pages/` | `*_page.py` | `base_page.py`, `data_source_page.py`, `portfolio_page.py` |
| Performance tests | `tests/performance/` | `test_*.py` | `test_worker_pool_performance.py` |
| Compliance tests | `tests/tests_principle_compliance/` | `test_tdd_ch*_compliance.py` | `test_tdd_ch1_compliance.py` |
| Test helpers | `tests/helpers/` | No `test_` prefix | `benchmark.py`, `gem5_fixtures.py`, `sample_figures.py` |

## 9. Sentinel Values

| Sentinel | Type | Meaning | Used In |
|---|---|---|---|
| `-1` | `int` | Inherit from parent | `TypographyConfig.font_size_*` fields |
| `-1.0` | `float` | Inherit from parent / auto | `LegendConfig.position_x`, `LegendConfig.position_y`, `LegendConfig.col_width` |
| `""` | `str` | Inherit from global / transparent | `LegendConfig.bgcolor`, `AxisConfig.tick_font_color`, `AxisConfig.axis_line_color` |
| `None` | `Optional` | Absent / disabled | `AxisConfig.range`, `FigureConfig.data_labels`, `AxesConfig.y2` |

Constants `INHERIT = -1` and `INHERIT_F = -1.0` are defined in `src/core/models/visualization/typography_config.py` and `src/core/models/visualization/legend_config.py`.

## 10. Rendering Connector Naming

| File | Purpose | Key Class/Constant |
|---|---|---|
| `src/web/rendering/plotly_connector.py` | Plotly engine connector | `FigureSpecToPlotly` |
| `src/web/rendering/matplotlib_connector.py` | Matplotlib engine connector | `FigureSpecToMatplotlib` |
| `src/web/rendering/trace_to_plotly.py` | Trace-level Plotly translation | -- |
| `src/web/rendering/matplotlib_trace_renderer.py` | Trace-level Matplotlib translation | -- |
| `src/web/rendering/config_builder.py` | Builds FigureConfig from UI state | -- |
| `src/web/rendering/preset_applicator.py` | Applies preset overrides to config | -- |
| `src/web/rendering/engine_manager.py` | Engine selection and dispatch | -- |
| `src/web/rendering/_connector_protocol.py` | Styling pipeline ordering contract | `STYLING_PIPELINE_ORDER` tuple |
| `src/web/rendering/_render_result.py` | Render result data container | -- |
| `src/web/rendering/_heatmap_utils.py` | Heatmap-specific helpers | -- |

Connector class names follow the pattern `FigureSpecTo{Engine}`. Private helper modules use the `_` prefix.

## 11. Key Naming Discrepancies

| Context | Convention | Reason |
|---|---|---|
| Shaper registry keys | **camelCase** (`"columnSelector"`) | Legacy compatibility with serialized pipeline configs |
| Plot type registry keys | **snake_case** (`"grouped_bar"`) | Matches Python class naming when lowered |
| Config dataclass fields | **snake_case** (`font_size_title`) | Standard Python attribute convention |
| Session state keys | **dot.namespaced** (`"plot.1.auto_refresh"`) | Prevents collisions, enables scoped cleanup |
| Styling pipeline steps | **snake_case** (`"axis_labels"`) | Internal ordering identifiers in `STYLING_PIPELINE_ORDER` |
