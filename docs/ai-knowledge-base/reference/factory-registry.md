---
title: "Factory and Registry Reference"
parent: Reference
grand_parent: AI Knowledge Base
nav_order: 4
---

# Factory and Registry Reference

## Quick Index

| Name | Kind | Layer | File |
|------|------|-------|------|
| `ShaperFactory` | Factory + Registry | Core | `src/core/services/shapers/factory.py` |
| `PlotFactory` | Factory + Registry | Web | `src/web/pages/ui/plotting/plot_factory.py` |
| `StrategyFactory` | Factory | Parsing | `src/parsing/gem5/impl/strategies/factory.py` |
| `StyleUIFactory` | Factory | Web | `src/web/pages/ui/plotting/styles/factory.py` |
| `SimulatorRegistry` | Registry | Parsing | `src/parsing/registry.py` |
| `StatTypeRegistry` | Registry | Parsing | `src/parsing/gem5/types/base.py` |

---

## Factories

### ShaperFactory

- **File**: `src/core/services/shapers/factory.py`
- **Layer**: Core
- **Produces**: `Shaper` (ABC in `src/core/services/shapers/shaper.py`)
- **Backing store**: `_registry: dict[str, type[Shaper]]` -- class-level static dict, 10 entries
- **Creation**: `create_shaper(cls, shaper_type: str, params: ShaperStepConfig) -> Shaper`
- **Registration**: `register(cls, shaper_type: str, shaper_class: type[Shaper]) -> None`
- **Lookup**: `get_available_types(cls) -> list[str]`
- **Error on unknown key**: `ValueError`

#### Registered Types (10)

| Registry Key | Class | Display Name | File | Inherits |
|-------------|-------|-------------|------|----------|
| `"mean"` | `Mean` | Mean Calculator | `src/core/services/shapers/impl/mean.py` | `Shaper` |
| `"columnSelector"` | `ColumnSelector` | Column Selector | `src/core/services/shapers/impl/selector_algorithms/column_selector.py` | `UniDfShaper` |
| `"conditionSelector"` | `ConditionSelector` | Filter | `src/core/services/shapers/impl/selector_algorithms/condition_selector.py` | `Selector` |
| `"itemSelector"` | `ItemSelector` | Item Selector | `src/core/services/shapers/impl/selector_algorithms/item_selector.py` | `Selector` |
| `"normalize"` | `Normalize` | Normalize | `src/core/services/shapers/impl/normalize.py` | `Shaper` |
| `"pivotLonger"` | `PivotLonger` | Pivot Longer (Melt) | `src/core/services/shapers/impl/pivot.py` | `Shaper` |
| `"pivotWider"` | `PivotWider` | Pivot Wider | `src/core/services/shapers/impl/pivot.py` | `Shaper` |
| `"sort"` | `Sort` | Sort | `src/core/services/shapers/impl/sort.py` | `Shaper` |
| `"splitApply"` | `SplitApply` | Split-Apply (Per-Axis) | `src/core/services/shapers/impl/split_apply.py` | `Shaper` |
| `"transformer"` | `Transformer` | Transformer | `src/core/services/shapers/impl/transformer.py` | `Shaper` |

#### Inheritance Hierarchy

```
Shaper (ABC)  -- src/core/services/shapers/shaper.py
|-- Mean
|-- Normalize
|-- PivotLonger
|-- PivotWider
|-- Sort
|-- SplitApply
|-- Transformer
|-- UniDfShaper  -- src/core/services/shapers/uni_df_shaper.py
    |-- Selector (ABC)  -- src/core/services/shapers/impl/selector.py
    |   |-- ItemSelector
    |   |-- ConditionSelector
    |-- ColumnSelector
```

#### Constructor Contract

```python
shaper = ShaperFactory.create_shaper("mean", {"columns": [...], "group_by": [...]})
# Internally: Mean(dict(params))
# Shaper.__init__ validates via self._verify_params()
```

---

### PlotFactory

- **File**: `src/web/pages/ui/plotting/plot_factory.py`
- **Layer**: Web
- **Produces**: `BasePlot` (ABC in `src/web/pages/ui/plotting/base_plot.py`)
- **Backing store**: `_plot_classes: dict[str, Callable[[int, str], BasePlot]]` -- class-level static dict, 9 entries
- **Metadata store**: `_plot_metadata: dict[str, PlotTypeMetadata]`
- **Creation**: `create_plot(cls, plot_type: str, plot_id: int, name: str) -> BasePlot`
- **Registration**: `register_plot_type(cls, plot_type: str, plot_class: Callable, metadata: PlotTypeMetadata | None) -> None`
- **Validation on register**: Checks `issubclass(plot_class, BasePlot)`
- **Error on unknown key**: `ValueError`

#### Registered Types (9)

| Registry Key | Class | Display Name | Icon | Category | File |
|-------------|-------|-------------|------|----------|------|
| `"bar"` | `BarPlot` | Bar Chart | `bar_chart` | basic | `src/web/pages/ui/plotting/types/bar_plot.py` |
| `"line"` | `LinePlot` | Line Chart | `show_chart` | basic | `src/web/pages/ui/plotting/types/line_plot.py` |
| `"scatter"` | `ScatterPlot` | Scatter Plot | `scatter_plot` | basic | `src/web/pages/ui/plotting/types/scatter_plot.py` |
| `"grouped_bar"` | `GroupedBarPlot` | Grouped Bar | `bar_chart` | comparison | `src/web/pages/ui/plotting/types/grouped_bar_plot.py` |
| `"stacked_bar"` | `StackedBarPlot` | Stacked Bar | `stacked_bar_chart` | comparison | `src/web/pages/ui/plotting/types/stacked_bar_plot.py` |
| `"grouped_stacked_bar"` | `GroupedStackedBarPlot` | Grouped Stacked Bar | `stacked_bar_chart` | comparison | `src/web/pages/ui/plotting/types/grouped_stacked_bar_plot.py` |
| `"dual_axis_bar_dot"` | `DualAxisBarDotPlot` | Dual Axis Bar Dot | `waterfall_chart` | comparison | `src/web/pages/ui/plotting/types/dual_axis_bar_dot_plot.py` |
| `"heatmap"` | `HeatmapPlot` | Heatmap | `grid_on` | distribution | `src/web/pages/ui/plotting/types/heatmap_plot.py` |
| `"histogram"` | `HistogramPlot` | Histogram | `bar_chart` | distribution | `src/web/pages/ui/plotting/types/histogram_plot.py` |

#### Constructor Contract

```python
plot = PlotFactory.create_plot("bar", plot_id=1, name="IPC Comparison")
# Internally: BarPlot(1, "IPC Comparison")
# Subclass sets self.plot_type before calling super().__init__
```

---

### StrategyFactory

- **File**: `src/parsing/gem5/impl/strategies/factory.py`
- **Layer**: Parsing
- **Produces**: `FileParserStrategy` (Protocol in `src/parsing/gem5/impl/strategies/file_parser_strategy.py`)
- **Backing store**: Inline `if/elif` dispatch (no dict registry)
- **Creation**: `create(strategy_type: str) -> FileParserStrategy` (`@staticmethod`)
- **Uses lazy imports**: Yes, avoids circular dependencies
- **Error on unknown key**: `ValueError`

#### Registered Types (2)

| Strategy Key | Class | File |
|-------------|-------|------|
| `"simple"` | `SimpleStatsStrategy` | `src/parsing/gem5/impl/strategies/simple.py` |
| `"config_aware"` | `ConfigAwareStrategy` | `src/parsing/gem5/impl/strategies/config_aware.py` |

#### FileParserStrategy Protocol Methods

| Method | Signature |
|--------|-----------|
| `execute` | `(stats_path: str, stats_pattern: str, variables: list[StatConfig]) -> list[dict[str, Any]]` |
| `get_work_items` | `(stats_path: str, stats_pattern: str, variables: list[StatConfig]) -> Sequence[ParseWork]` |
| `post_process` | `(results: list[dict[str, Any]]) -> list[dict[str, Any]]` |

---

### StyleUIFactory

- **File**: `src/web/pages/ui/plotting/styles/factory.py`
- **Layer**: Web
- **Produces**: `BaseStyleUI` (in `src/web/pages/ui/plotting/styles/base_ui.py`)
- **Backing store**: Inline `if/elif` dispatch with substring matching (no dict registry)
- **Creation**: `get_strategy(plot_id: int, plot_type: str) -> BaseStyleUI` (`@staticmethod`)
- **Fallback**: Returns `BaseStyleUI` for unrecognized types
- **Integration**: `BasePlot.__init__` calls this to set `self._style_ui`

#### Dispatch Rules (evaluated in order)

| Condition | Returned Class | File |
|-----------|---------------|------|
| `plot_type == "dual_axis_bar_dot"` | `BaseStyleUI` | `src/web/pages/ui/plotting/styles/base_ui.py` |
| `"line" in plot_type` | `LineStyleUI` | `src/web/pages/ui/plotting/styles/line_ui.py` |
| `"scatter" in plot_type` | `ScatterStyleUI` | `src/web/pages/ui/plotting/styles/line_ui.py` |
| `"bar" in plot_type` | `BarStyleUI` | `src/web/pages/ui/plotting/styles/bar_ui.py` |
| fallback | `BaseStyleUI` | `src/web/pages/ui/plotting/styles/base_ui.py` |

#### Style UI Hierarchy

```
BaseStyleUI  -- src/web/pages/ui/plotting/styles/base_ui.py
|-- BarStyleUI   -- src/web/pages/ui/plotting/styles/bar_ui.py
|-- LineStyleUI  -- src/web/pages/ui/plotting/styles/line_ui.py
    |-- ScatterStyleUI  -- src/web/pages/ui/plotting/styles/line_ui.py
```

---

## Registries (standalone)

### SimulatorRegistry

- **File**: `src/parsing/registry.py`
- **Layer**: Parsing
- **Backing store**: `_registry: dict[str, tuple[SimulatorInfo, Callable[[], SimulationParser]]]`
- **Instance cache**: `_instances: dict[str, SimulationParser]` (lazy instantiation)
- **Population**: Auto-registration at module load -- `SimulatorRegistry.register(GEM5_INFO, _create_gem5_parser)` at bottom of file
- **Extension**: `register(cls, info: SimulatorInfo, factory: Callable[[], SimulationParser]) -> None`
- **Lookup**: `get_parser(cls, name: str) -> SimulationParser` (creates on first access, caches)
- **Error on duplicate**: `ValueError`
- **Error on unknown key**: `KeyError`
- **Reset (testing)**: `_reset(cls)` clears both dicts

#### Registered Simulators (1)

| Key | Display Name | Factory | Parser Class |
|-----|-------------|---------|-------------|
| `"gem5"` | `"gem5"` | `_create_gem5_parser()` | `Gem5Parser` (`src/parsing/gem5/impl/gem5_parser.py`) |

#### gem5 SimulatorInfo

- **file_pattern**: `"stats.txt"`
- **variable_types**: `["scalar", "vector", "distribution", "histogram", "configuration"]`
- **internal_stats**: `{"total", "mean", "gmean", "stdev", "samples", "sample_period", "min_val", "max_val", "min_bucket", "max_bucket", "num_buckets", "underflows", "overflows"}`
- **parsing_strategies**: `"simple"` (Simple stats.txt only), `"config_aware"` (Integrates config.ini)

---

### StatTypeRegistry

- **File**: `src/parsing/gem5/types/base.py`
- **Layer**: Parsing
- **Backing store**: `_types: dict[str, type[StatType]]`
- **Population**: Self-registration via `@register_type("name")` decorator; imports in `src/parsing/gem5/types/__init__.py` trigger execution
- **Extension**: `register(cls, type_name: str) -> Callable` (decorator factory)
- **Creation**: `create(cls, type_name: str, repeat: int = 1, **kwargs) -> StatType`
- **Lookup**: `get_types(cls) -> list[str]`
- **Convenience alias**: `register_type = StatTypeRegistry.register`
- **Error on unknown key**: `ValueError`

#### Registered Types (5)

| Registry Key | Class | File | Required Params |
|-------------|-------|------|----------------|
| `"scalar"` | `Scalar` | `src/parsing/gem5/types/scalar.py` | none |
| `"vector"` | `Vector` | `src/parsing/gem5/types/vector.py` | `entries` |
| `"distribution"` | `Distribution` | `src/parsing/gem5/types/distribution.py` | `minimum`, `maximum` |
| `"histogram"` | `Histogram` | `src/parsing/gem5/types/histogram.py` | none (dynamic buckets) |
| `"configuration"` | `Configuration` | `src/parsing/gem5/types/configuration.py` | `onEmpty` |

#### Self-Registration Pattern

```python
# In each type module (e.g., src/parsing/gem5/types/scalar.py):
@register_type("scalar")
class Scalar(StatType): ...

# In src/parsing/gem5/types/__init__.py (triggers registration on import):
from src.parsing.gem5.types import scalar as _scalar
from src.parsing.gem5.types import vector as _vector
from src.parsing.gem5.types import distribution as _distribution
from src.parsing.gem5.types import histogram as _histogram
from src.parsing.gem5.types import configuration as _configuration
```

#### Type Mapper Integration

- `TypeMapper` in `src/parsing/gem5/types/type_mapper.py` wraps `StatTypeRegistry.create()` with parameter normalization
- Called by parser internals to instantiate stat objects from `StatConfig` models

---

## Cross-Reference: Factory Usage Sites

| Factory | Primary Caller | Call Site |
|---------|---------------|----------|
| `ShaperFactory.create_shaper()` | `DefaultShapersAPI` | `src/core/services/shapers/shapers_impl.py` |
| `PlotFactory.create_plot()` | `CreationController` | `src/web/controllers/plot/creation_controller.py` |
| `StrategyFactory.create()` | `Gem5Parser` | `src/parsing/gem5/impl/gem5_parser.py` |
| `StyleUIFactory.get_strategy()` | `BasePlot.__init__()` | `src/web/pages/ui/plotting/base_plot.py` |
| `SimulatorRegistry.get_parser()` | `ApplicationAPI` | `src/core/application_api.py` |
| `StatTypeRegistry.create()` | `TypeMapper.create_stat()` | `src/parsing/gem5/types/type_mapper.py` |

---

## Extension Checklist

### New Shaper
1. Create class inheriting `Shaper` or `UniDfShaper` in `src/core/services/shapers/impl/`
2. Add to `ShaperFactory._registry` and `_display_names` in `src/core/services/shapers/factory.py`
3. Add UI config component in `src/web/components/shapers/`

### New Plot Type
1. Create class inheriting `BasePlot` in `src/web/pages/ui/plotting/types/`
2. Add to `PlotFactory._plot_classes` and `_plot_metadata` in `src/web/pages/ui/plotting/plot_factory.py`
3. Export from `src/web/pages/ui/plotting/types/__init__.py`
4. Add `StyleUIFactory` dispatch rule if custom style UI is needed

### New Simulator Backend
1. Implement `SimulationParser` protocol
2. Create `SimulatorInfo` with at least one `ParsingStrategy`
3. Call `SimulatorRegistry.register(info, factory_fn)` at module level

### New Stat Type
1. Create class inheriting `StatType` in `src/parsing/gem5/types/`
2. Decorate with `@register_type("type_name")`
3. Import module in `src/parsing/gem5/types/__init__.py`
4. Add parameter mapping in `TypeMapper.create_stat()` if needed
