---
title: "End-to-End Data Flow"
parent: Architecture
grand_parent: AI Knowledge Base
nav_order: 4
---

# End-to-End Data Flow

Reference for the 6 data pipelines in RING-5 Unified Engine v2.

- **Central artifact**: `pd.DataFrame` -- universal container across all flows
- **Two slots**: `raw_data` (loaded baseline), `processed_data` (per-plot pipeline output)
- **State gateway**: `RepositoryStateManager` -- all mutations flow through repositories, never direct `st.session_state`

---

## Flow A: Scan -> Parse -> CSV

```
stats.txt files (disk)
    |  rglob + early-stop
    v
ScanWorkPool (ProcessPoolExecutor)
    |  statsScanner.pl -- classifyLine(), type evolution
    v
JSON stdout: [{name, type, entries, min, max}]
    |  merge + PatternAggregator
    v
list[ScannedVariable]  -- stored in ParserStateRepository
    |  user selects variables
    v
list[StatConfig]  -- regex expansion + StrategyFactory
    |
    v
ParseWorkPool (persistent Perl workers)
    |  fileParser.pl -- parseAndPrintLineWithFormat()
    v
stdout: "type/name::entry/value" lines
    |  aggregate per-file dicts
    v
CSV file on disk (csv_contract format)
```

**Key files**: `src/parsing/gem5/impl/gem5_parser.py`, `src/parsing/framework/file_discovery.py`, `src/parsing/gem5/perl/statsScanner.pl`, `src/parsing/gem5/perl/fileParser.pl`, `src/parsing/gem5/perl/libs/TypesFormatRegex.pm`, `src/core/models/csv_contract.py`, `src/web/pages/data_source.py`

| Stage | Data Type |
|-------|-----------|
| File discovery | `list[Path]` |
| Async scan | `list[Future[list[ScannedVariable]]]` |
| Aggregated scan | `list[ScannedVariable]` |
| Variable selection | `list[StatConfig]` |
| Parse handle | `ParseBatchResult` (futures + total + output_dir) |
| Per-file result | `dict[str, Any]` |
| Final output | CSV file path (`str`) |

**Errors**: `FileNotFoundError` if path missing or no files match; `RuntimeError` if Perl unavailable; regex expansion > 50 vars triggers warning; individual file failures yield partial results.

---

## Flow B: CSV -> Load -> DataFrame -> Session State

```
CSV file path (from Flow A, upload, or CSV pool)
    |  validate_path_within() + pd.read_csv()
    v
pd.DataFrame (raw)
    |  identity check, defensive copy, type enforcement
    v
DataRepository stores raw_data
    |  processed_data = None, csv_path stored
    v
Ready for downstream flows
```

**Three entry points**: direct upload (`st.file_uploader`), CSV pool (`api.load_from_pool`), post-parse (`api.finalize_parsing`)

**Key files**: `src/core/application_api.py`, `src/core/services/data_services/csv_pool_service.py`, `src/core/state/repository_state_manager.py`, `src/core/state/repositories/data_repository.py`, `src/web/pages/data_source.py`

**Errors**: path traversal rejected by `validate_path_within()`; malformed CSV fails at `pd.read_csv()`; type enforcement reads `parse_variables` -- missing config is non-fatal.

---

## Flow C: DataFrame -> Managers -> Processed DataFrame

```
pd.DataFrame (from DataRepository)
    |  DataManager.get_data()
    v
api.managers.<operation>(df, params)  -- service call
    |
    v
result_df  -- stored in PreviewRepository (Phase 1)
    |  user confirms
    v
DataRepository updated (Phase 2)  + history record written
```

**Two-phase commit**: Phase 1 stores preview in `PreviewRepository`; Phase 2 promotes to `DataRepository` on user confirmation.

| Manager | Method | Effect |
|---------|--------|--------|
| Seeds Reducer | `reduce_seeds()` | GroupBy + mean/std; reduces rows, adds .sd columns |
| Outlier Remover | `remove_outliers()` | Q3 threshold filter per group; reduces rows |
| Preprocessor | various | Arithmetic/column transforms |
| Mixer | various | Data combination operations |

**Key files**: `src/web/components/data_managers/data_manager.py`, `src/web/components/data_managers/seeds_reducer.py`, `src/web/components/data_managers/outlier_remover.py`, `src/core/state/repositories/preview_repository.py`, `src/web/pages/data_managers.py`

**Errors**: validation in `api.managers.validate_*_inputs()` before service call; empty result after filter shows warning; history written to both tracks (rolling last 20 + unbounded).

---

## Flow D: DataFrame -> Shaper Pipeline -> Shaped DataFrame

```
pd.DataFrame (raw_data)
    |  PipelineController data guard
    v
User adds steps -> list[PipelineStep]
    |
    v
Per step (incremental):
    ShaperFactory.create_shaper(type, config) -> Shaper instance
    current_data.pipe(shaper) -> step_output (chains to next)
    |
    v
"Finalize Pipeline" -> full re-execution from raw_data
    |
    v
plot.processed_data = final DataFrame
```

**10 shaper types**:

| Key | Class | Pattern |
|-----|-------|---------|
| `columnSelector` | `ColumnSelector` | Column reduction |
| `conditionSelector` | `ConditionSelector` | Row filter (conditions) |
| `itemSelector` | `ItemSelector` | Row filter (values) |
| `sort` | `Sort` | Row reorder (CategoricalDtype) |
| `mean` | `Mean` | Append mean rows |
| `normalize` | `Normalize` | Divide by baseline |
| `pivotLonger` | `PivotLonger` | Wide to long |
| `pivotWider` | `PivotWider` | Long to wide |
| `splitApply` | `SplitApply` | Group sub-pipelines + merge |
| `transformer` | `Transformer` | Type conversion |

**Class hierarchy**:
```
Shaper (ABC)
 +-- UniDfShaper (ABC)
 |    +-- Mean, Normalize, Sort, Transformer
 |    +-- Selector (ABC) -> ConditionSelector, ItemSelector
 |    +-- ColumnSelector, SplitApply
 +-- PivotLonger, PivotWider  (extend Shaper directly)
```

**Key files**: `src/web/controllers/plot/pipeline_controller.py`, `src/core/services/shapers/pipeline_service.py`, `src/core/services/shapers/factory.py`, `src/core/models/shaper_models.py`, `src/core/services/shapers/validation.py`

**Errors**: `ValueError` for unknown type; per-shaper `_verify_params()` / `_verify_preconditions()`; pipeline wraps: `ValueError(f"Failed to apply shaper {type}: {e}")`; web layer skips incomplete configs with warning.

---

## Flow E: Shaped DataFrame -> Plot -> Rendered Figure

```
pd.DataFrame (plot.processed_data)
    |  plot.render_config_ui() -> PlotConfig dict
    v
plot.create_traces(data, config)
    |
    v
TraceBuildResult (traces, barmode, shapes, annotations)
    |  traces_to_plotly()
    v
go.Figure (unstyled)
    |  ConfigSpecBuilder.from_config() -> FigureConfig
    |  resolve_config() -> replace -1 sentinels
    |  FigureSpecToPlotly.apply() -> styled figure
    v
go.Figure (fully styled) -> cache -> render in browser
```

**Style application order** (fixed in `FigureSpecToPlotly.apply()`):
dimensions, backgrounds, title, xaxis, yaxis, y2axis, legends, heatmap_colorbars, color_palette, hovermode, font_family, reference_lines, data_labels, series_styling, trace_overrides, separator_lines, stripes, axis_colors

**9 plot types**: `bar`, `grouped_bar`, `stacked_bar`, `grouped_stacked_bar`, `line`, `scatter`, `heatmap`, `histogram`, `dual_axis_bar_dot`

**Cache key**: `plot_{id}_{config_hash}_{data_hash}` -- config_hash excludes transient range keys; data_hash uses shape + first/last row approximation. `SimpleCache` with 128 entries.

**Key files**: `src/web/controllers/plot/render_controller.py`, `src/web/pages/ui/plotting/base_plot.py`, `src/web/rendering/trace_to_plotly.py`, `src/web/rendering/config_builder.py`, `src/web/rendering/plotly_connector.py`, `src/web/pages/ui/plotting/styles/applicator.py`

**Errors**: `create_traces()` failure sets `config_error=True`; `resolve_config()` handles missing keys; relayout maps Plotly events back to `PlotConfig`.

---

## Flow F: Portfolio Save/Load Round-Trip

```
SAVE:
  All repositories -> PortfolioService.save_portfolio()
    plot.to_dict() per plot
    data.to_csv(index=False) -> CSV string
    figure_spec_enricher callback (injected)
    -> json.dump() to portfolios/<name>.json

LOAD:
  portfolios/<name>.json -> json.load()
    PortfolioMigrator.migrate() -> schema upgrade
    -> PortfolioData (TypedDict, 13 fields)
    -> SessionRepository.restore_from_portfolio()
      parser state  -> ParserStateRepository
      config        -> ConfigRepository
      data CSV      -> pd.read_csv(StringIO()) -> DataRepository
      plots         -> plot_deserializer() -> PlotRepository
      history       -> HistoryRepository
    -> st.rerun(scope="app")
```

**Dependency injection chain** (preserves layer boundary -- core never imports web classes):
```
app.py: ApplicationAPI(plot_deserializer=BasePlot.from_dict)
  -> RepositoryStateManager(plot_deserializer)
    -> SessionRepository._plot_deserializer
```

| Preserved | Not Preserved |
|-----------|---------------|
| Raw DataFrame (CSV string) | Cached figures (`last_generated_fig`) |
| Plot objects + configs + pipelines | Preview DataFrames |
| Per-plot processed data | Widget UI state |
| Parser state | `st.session_state` keys |
| Operation history (both tracks) | |

**Key files**: `src/web/pages/portfolio.py`, `src/core/services/data_services/portfolio_service.py`, `src/core/models/portfolio_models.py`, `src/core/services/portfolio_migrator.py`, `src/core/state/repositories/session_repository.py`

**Errors**: corrupt JSON fails at load; migrator handles unknown schema versions; malformed CSV string fails `pd.read_csv()`; unknown plot types logged and skipped.

---

## Data Type Transformations Table

| Stage | Input Type | Output Type | Key File |
|-------|-----------|-------------|----------|
| File discovery | `str` (path) | `list[str]` | `src/parsing/framework/file_discovery.py` |
| Stats scanning | `Path` | `list[ScannedVariable]` | `src/parsing/gem5/perl/statsScanner.pl` |
| Scan aggregation | `list[list[ScannedVariable]]` | `list[ScannedVariable]` | `src/parsing/gem5/impl/gem5_parser.py` |
| Variable normalization | `list[ParseVariableConfig]` | `list[StatConfig]` | `src/core/application_api.py` |
| Parse dispatch | `list[StatConfig]` | `ParseBatchResult` | `src/parsing/gem5/impl/gem5_parser.py` |
| Per-file extraction | `str` (file) | `dict[str, Any]` | `src/parsing/gem5/perl/fileParser.pl` |
| CSV finalization | `list[dict]` | `str` (CSV path) | `src/parsing/gem5/impl/gem5_parser.py` |
| CSV loading | `str` (path) | `pd.DataFrame` | `src/core/services/data_services/csv_pool_service.py` |
| State storage | `pd.DataFrame` | `pd.DataFrame` (copied) | `src/core/state/repository_state_manager.py` |
| Manager transform | `pd.DataFrame` | `pd.DataFrame` | `src/web/components/data_managers/` |
| Shaper instantiation | `ShaperStepConfig` | `Shaper` subclass | `src/core/services/shapers/factory.py` |
| Shaper execution | `pd.DataFrame` | `pd.DataFrame` | `src/core/services/shapers/pipeline_service.py` |
| Trace building | `DataFrame` + `PlotConfig` | `TraceBuildResult` | `src/web/pages/ui/plotting/base_plot.py` |
| Trace conversion | `TraceBuildResult` | `go.Figure` | `src/web/rendering/trace_to_plotly.py` |
| Config spec build | `PlotConfig` (dict) | `FigureConfig` (dataclass) | `src/web/rendering/config_builder.py` |
| Sentinel resolution | `FigureConfig` (-1s) | `FigureConfig` (resolved) | `src/web/rendering/config_builder.py` |
| Style application | `FigureConfig` + `go.Figure` | `go.Figure` (styled) | `src/web/rendering/plotly_connector.py` |
| Portfolio save | Session state | JSON file | `src/core/services/data_services/portfolio_service.py` |
| Portfolio load | JSON file | `PortfolioData` | `src/core/services/data_services/portfolio_service.py` |
| Session restore | `PortfolioData` | Repositories populated | `src/core/state/repositories/session_repository.py` |
