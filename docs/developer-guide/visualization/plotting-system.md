---
title: "Plotting System"
parent: Visualization
grand_parent: Developer Guide
nav_order: 1
---

# Plotting System

This guide documents the plotting subsystem of the RING-5 Unified Engine v2. It
covers the factory pattern, the base plot abstraction, all nine concrete plot
types, the trace building pipeline, the configuration UI mixin, style
application, and the end-to-end lifecycle of a plot from creation to rendering.

---

## 1. Overview

The plotting system is a three-tier architecture that translates a user-selected
plot type into engine-agnostic trace specifications, which are then rendered by
downstream connectors (Plotly, Matplotlib).

| Tier | Role | Key Module |
|------|------|------------|
| **Plot Factory** | Class-level registry mapping string keys to constructors | `plot_factory.py` |
| **Base Plot (ABC)** | Abstract base providing lifecycle, serialization, and config UI mixin | `base_plot.py` |
| **Concrete Plot Types** | 9 implementations producing `TraceBuildResult` from data and config | `types/*.py` |

The nine registered plot types span three categories:

| Category | Plot Types |
|----------|------------|
| **basic** | `bar`, `line`, `scatter` |
| **comparison** | `grouped_bar`, `stacked_bar`, `grouped_stacked_bar`, `dual_axis_bar_dot` |
| **distribution** | `heatmap`, `histogram` |

The high-level data flow is:

```
User selects plot type
  -> PlotFactory.create_plot(type, id, name) -> BasePlot subclass
  -> plot.render_config_ui(data, saved_config) -> PlotConfig dict
  -> plot.create_traces(data, config) -> TraceBuildResult
  -> traces_to_plotly(result) -> go.Figure
  -> plot.apply_common_layout(fig, config) -> styled go.Figure
  -> chart display renders the figure
```

**Source files:**

- `src/web/pages/ui/plotting/plot_factory.py` -- factory and registry
- `src/web/pages/ui/plotting/base_plot.py` -- abstract base class
- `src/web/pages/ui/plotting/plot_config_ui.py` -- configuration UI mixin
- `src/web/pages/ui/plotting/types/` -- all nine concrete plot implementations

---

## 2. BasePlot ABC

`BasePlot` is the abstract base class from which every concrete plot type
inherits. It combines two parents: `PlotConfigUIMixin` (for UI rendering) and
`ABC` (for abstract method enforcement).

**File:** `src/web/pages/ui/plotting/base_plot.py`

### 2.1 Instance Fields

| Attribute | Type | Purpose |
|-----------|------|---------|
| `plot_id` | `int` | Unique identifier |
| `name` | `str` | Display name |
| `plot_type` | `str` | Type key matching the factory registry |
| `config` | `PlotConfig` (alias for `dict[str, Any]`) | Current configuration |
| `processed_data` | `DataFrame or None` | Shaped data ready for plotting |
| `last_generated_fig` | `go.Figure or None` | Cached Plotly figure |
| `last_traces` | `TraceBuildResult or None` | Cached trace build output |
| `pipeline` | `list[PipelineStep]` | Data shaping pipeline steps |
| `pipeline_counter` | `int` | Next pipeline step ID |
| `legend_mappings_by_column` | `dict[str, dict[str, str]]` | Per-column legend label overrides |
| `legend_mappings` | `dict[str, str]` | Global legend label overrides |
| `_style_ui` | `BaseStyleUI` | Style UI strategy (assigned via `StyleUIFactory`) |
| `_applicator` | `StyleApplicator` | Style application engine |

### 2.2 Abstract Methods

Every concrete plot type must implement three methods:

```python
@abstractmethod
def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
    """Produce engine-agnostic trace data from data and config."""

@abstractmethod
def get_legend_column(self, config: PlotConfig) -> str | None:
    """Return the column name used for legend/color coding."""

@abstractmethod
def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
    """Render the configuration UI for this plot type (inherited from mixin)."""
```

### 2.3 PlotConfigUIMixin

**File:** `src/web/pages/ui/plotting/plot_config_ui.py`

This mixin class is separated from `BasePlot` to isolate UI rendering concerns.
It provides the pills-based settings dispatcher and several hookable methods.

**`render_settings_section(section, saved_config, data)`** routes to
the correct settings component based on the pill key:

| Section Key | Component | Notes |
|-------------|-----------|-------|
| `"layout"` | `LayoutSettingsComponent` | Always available |
| `"typography"` | `TypographySettingsComponent` | Key prefix `"theme_"` |
| `"legends"` | `LegendSettingsComponent` | Checks dual-axis and secondary/tertiary support |
| `"axes"` | `AxesSettingsComponent` | Injects `render_specific_fn` and `render_ordering_fn` |
| `"data_labels"` | `DataLabelsSettingsComponent` | Key prefix `"theme_"` |
| `"colors"` | `ColorsSettingsComponent` | Passes data for series discovery |
| `"advanced"` | `AdvancedSettingsComponent` | Injects reference line, shapes, engine callbacks |

**Hookable overrides for subclasses:**

- `render_specific_advanced_options(saved_config, data)` -- bar gap sliders,
  bar-group gap, stacked border width. `LinePlot` overrides this for line shape
  selection; `DualAxisBarDotPlot` overrides for dot/line controls.
- `render_advanced_options(saved_config, data)` -- full advanced panel.
  `GroupedStackedBarPlot` completely replaces it.
- `_supports_secondary_legend()` and `_supports_tertiary_legend()` -- override
  to enable multi-legend pills.

### 2.4 Serialization

`to_dict()` converts the plot state to a dictionary (excluding `go.Figure`
objects). `from_dict()` reconstructs a plot by calling `PlotFactory.create_plot()`
and restoring saved state fields.

Serialized fields: `id`, `name`, `plot_type`, `config`, `processed_data`
(as CSV string), `pipeline`, `pipeline_counter`, `legend_mappings_by_column`,
`legend_mappings`.

---

## 3. PlotFactory

**File:** `src/web/pages/ui/plotting/plot_factory.py`

The `PlotFactory` uses a class-level registry pattern with classmethod API.

### 3.1 Registry

```python
_plot_classes: dict[str, Callable[[int, str], BasePlot]] = {
    "bar":                  BarPlot,
    "dual_axis_bar_dot":    DualAxisBarDotPlot,
    "grouped_bar":          GroupedBarPlot,
    "heatmap":              HeatmapPlot,
    "stacked_bar":          StackedBarPlot,
    "grouped_stacked_bar":  GroupedStackedBarPlot,
    "histogram":            HistogramPlot,
    "line":                 LinePlot,
    "scatter":              ScatterPlot,
}
```

Every constructor has the uniform signature `(plot_id: int, name: str) -> BasePlot`.

### 3.2 Metadata

Each plot type has a `PlotTypeMetadata` TypedDict with `display_name`, `icon`
(Material icon), and `category` fields. The metadata is used by the UI to
present available plot types grouped by category.

### 3.3 Factory Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_plot` | `(plot_type, plot_id, name) -> BasePlot` | Look up constructor, call it; raises `ValueError` on unknown type |
| `get_available_plot_types` | `() -> list[str]` | Return registry keys |
| `get_plot_metadata` | `() -> dict[str, PlotTypeMetadata]` | Return metadata copy for UI presentation |
| `register_plot_type` | `(plot_type, plot_class, metadata)` | Register a new type at runtime; validates `issubclass(plot_class, BasePlot)` |

### 3.4 Type Discovery

The factory imports all concrete types from `src/web/pages/ui/plotting/types/__init__.py`,
which re-exports every plot class. The `__init__.py` also defines `__all__` for
controlled wildcard imports. Runtime registration via `register_plot_type()`
allows adding new plot types without modifying the factory source.

---

## 4. Plot Type Catalog

The following table summarizes all nine plot types, their required configuration
columns, trace output type, and distinguishing features.

| Registry Key | Class | Extends | Trace Config | Barmode | Config Component | Legend Column | Secondary Y |
|--------------|-------|---------|--------------|---------|------------------|---------------|-------------|
| `bar` | `BarPlot` | `BasePlot` | `BarTraceConfig` | `group` | `base_plot_config` | `color` | No |
| `line` | `LinePlot` | `BasePlot` | `LineTraceConfig` | `group` | `base_plot_config` | `color` | No |
| `scatter` | `ScatterPlot` | `BasePlot` | `ScatterTraceConfig` | `group` | `base_plot_config` | `color` | No |
| `histogram` | `HistogramPlot` | `BasePlot` | `BarTraceConfig` | `overlay`/`relative` | `histogram_config` | `group_by` | No |
| `heatmap` | `HeatmapPlot` | `BasePlot` | `HeatmapTraceConfig` | `group` | `heatmap_config` | `None` | No |
| `grouped_bar` | `GroupedBarPlot` | `BasePlot` | `BarTraceConfig` | `group` | `grouped_bar_config` | `group` | No |
| `stacked_bar` | `StackedBarPlot` | `BasePlot` | `BarTraceConfig` | `stack` | `stacked_bar_config` | `None` | No |
| `grouped_stacked_bar` | `GroupedStackedBarPlot` | `StackedBarPlot` | `BarTraceConfig`+ | `stack` | `grouped_stacked_bar_config` | `None` | Optional |
| `dual_axis_bar_dot` | `DualAxisBarDotPlot` | `BasePlot` | `BarTraceConfig` + `LineTraceConfig`/`ScatterTraceConfig` | `group` | `dual_axis_config` | `color` | Yes |

**Key required columns per type:**

- **Bar, Line, Scatter**: `x`, `y`, optional `color`
- **Grouped Bar**: `x`, `y`, `group`, optional `color`
- **Stacked Bar**: `x`, `y_columns` (list)
- **Grouped Stacked Bar**: `x`, `group`, `y_columns`, optional `y_columns_right`
- **Dual Axis Bar Dot**: `x`, `y_bar`, `y_dot`, optional `color`
- **Histogram**: `histogram_variable`, optional `group_by`
- **Heatmap**: `x`, `metric_columns` (list), optional `facet_col`

**Inheritance note:** `GroupedStackedBarPlot` extends `StackedBarPlot`
rather than `BasePlot` directly, inheriting stacked trace building,
totals annotations, and hover templates.

---

## 5. Trace Building System

### 5.1 TraceBuildResult

**File:** `src/core/models/visualization/trace_build_result.py`

`TraceBuildResult` is the return type of every `create_traces()` implementation.
It bundles data traces with layout-level metadata.

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `traces` | `Sequence[TraceConfig]` | `[]` | Engine-agnostic trace list |
| `annotations` | `list[AnnotationConfig]` | `[]` | Structured text annotations (group labels, legends) |
| `layout_annotations` | `list[dict]` | `[]` | Raw annotation dicts passed to layout |
| `shapes` | `list[ShapeConfig]` | `[]` | Separator lines, shading rectangles |
| `barmode` | `str` | `"group"` | `"group"`, `"stack"`, `"overlay"`, `"relative"` |
| `custom_x_ticks` | `dict or None` | `None` | Override x-axis: `{"vals": [...], "text": [...]}` |
| `secondary_y` | `bool` | `False` | Whether secondary Y-axis is used |

### 5.2 TraceConfig Hierarchy

**File:** `src/core/models/visualization/trace_config.py`

All trace configs are engine-agnostic dataclasses. Pre-computed positioning
data (such as `x_positions` and `bar_width`) is embedded so that downstream
connectors do not need to reimplement grouping or bar-spacing math.

| Config Class | Discriminator | Key Extra Fields |
|--------------|---------------|------------------|
| `TraceConfig` | (base) | `name`, `trace_type`, `x`, `y`, `yaxis`, `color`, `opacity`, `legendgroup` |
| `BarTraceConfig` | `"bar"` | `x_positions`, `bar_width`, `offset`, `pattern`, `border_width`, `text_values`, `error_y` |
| `LineTraceConfig` | `"line"` | `line_width`, `line_dash`, `marker_symbol`, `show_markers`, `fill`, `error_y` |
| `ScatterTraceConfig` | `"scatter"` | `marker_symbol`, `marker_size`, `colorscale`, `size_values`, `error_y` |
| `HistogramTraceConfig` | `"histogram"` | `nbins`, `normalization`, `cumulative` |
| `HeatmapTraceConfig` | `"heatmap"` | `col_labels`, `row_labels`, `z`, `colorscale`, `show_values`, `text` |

### 5.3 Per-Type Trace Generation

**Simple types (Bar, Line, Scatter)** share a common pattern via the
`build_color_grouped_traces()` helper in `_trace_helpers.py`:

1. Extract error bar column (`"{y_col}.sd"`) if enabled.
2. Split data by optional color column with configurable group ordering.
3. For each group, call a type-specific `_make_trace()` closure that
   returns the appropriate `TraceConfig` subclass.

**Histogram** uses a unique approach: it detects pre-binned columns by naming
convention (`{variable}..{low}-{high}`), parses bucket ranges, applies
normalization (count, probability, percent, density), and optionally computes
cumulative sums.

**Heatmap** builds a z-matrix where rows are metric columns and columns are
x-axis values. It supports aggregation functions, faceting, conditional text
display, and optional totals rows/columns.

**Grouped Bar** delegates to `GroupedBarUtils.calculate_grouped_coordinates()`
to compute manual x-positions, tick marks, separator shapes, and bar widths.

**Stacked Bar** iterates over `y_columns`, creating one `BarTraceConfig` per
column. It attaches `customdata` with totals for hover templates and optionally
builds totals annotations above the stacks.

**Grouped Stacked Bar** is the most complex type. It combines stacked bars with
major/minor grouping, coordinate mapping, dual-axis support, numbered X-axis
labeling, and separate legend management. When no `group` column is configured,
it falls back to `StackedBarPlot.create_traces()`.

**Dual Axis Bar Dot** creates bar traces on the primary Y-axis and line or
scatter traces on the secondary Y-axis. When `isolate_last_group` is enabled,
the last x-category is split into a standalone markers-only trace to visually
disconnect a summary point from the trend line.

---

## 6. Plot Configuration UI

Each plot type delegates its column selection UI to a dedicated config component
in `src/web/components/plotting/config/`.

### 6.1 Config Component Mapping

| Config Component | Plot Type(s) | Key Widgets |
|------------------|--------------|-------------|
| `base_plot_config.render_common_with_color()` | bar, line, scatter | X, Y, Color column selectors |
| `grouped_bar_config.render()` | grouped_bar | X, Y, Group, Color + X/Group filters |
| `stacked_bar_config.render()` | stacked_bar | X + Multi-Y columns + X filter + totals toggle |
| `grouped_stacked_bar_config.render()` | grouped_stacked_bar | X, Group + Multi-Y + dual-axis right columns |
| `dual_axis_config.render()` | dual_axis_bar_dot | X, Y-bar, Y-dot, Color selectors |
| `heatmap_config.render()` | heatmap | X, Metric columns, Facet, Aggregation |
| `histogram_config.render()` | histogram | Variable, Group-by, Normalization, Bin size |

### 6.2 Integration

Each concrete plot type's `render_config_ui()` method calls its corresponding
config component, passing the current data and saved configuration. The
component renders Streamlit widgets and returns a `PlotConfig` dict with the
selected column names and type-specific options.

Example from `BarPlot`:

```python
@override
def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
    return render_common_with_color(data, saved_config, self.plot_id)
```

---

## 7. Plot Lifecycle

The lifecycle of a plot from creation to display follows these steps:

### Step 1 -- Type Selection

The user selects a plot type from the UI dropdown. The `PlotService` calls
`PlotFactory.create_plot()` which instantiates the concrete subclass.

### Step 2 -- Factory Creation

```python
PlotService.create_plot(name, type, state_manager)
  -> state_manager.start_next_plot_id() -> id
  -> PlotFactory.create_plot(type, id, name) -> BasePlot subclass
  -> state_manager.add_plot(plot)
  -> state_manager.set_current_plot_id(id)
```

### Step 3 -- Config UI Rendering

The `RenderController` calls `plot.render_config_ui(data, saved_config)` to
render column selectors and type-specific options. This returns a `PlotConfig`
dict.

### Step 4 -- Settings Section

The pills-based settings navigation calls
`plot.render_settings_section(section, saved_config, data)` which dispatches to
the appropriate settings component (layout, typography, legends, axes, colors,
data labels, or advanced).

### Step 5 -- Config Merge

The controller merges the config dicts from the config UI, settings section, and
theme options into the plot's `config` attribute.

### Step 6 -- Data Shaping

The pipeline shapers transform raw data into `plot.processed_data`.

### Step 7 -- Figure Generation

`plot.generate_figure()` orchestrates the rendering pipeline:

```python
def generate_figure(self) -> go.Figure:
    fig = self.create_figure(self.processed_data, self.config)
    fig = self.apply_common_layout(fig, self.config)
    # Apply custom legend labels
    if legend_labels := self.config.get("legend_labels"):
        fig.for_each_trace(lambda t: t.update(name=legend_labels.get(t.name, t.name)))
    self.last_generated_fig = fig
    return fig
```

Within `create_figure()`:

1. `create_traces(data, config)` -- calls the abstract method on the concrete type,
   producing a `TraceBuildResult`.
2. `traces_to_plotly(result)` -- the connector converts traces to a `go.Figure`.

### Step 8 -- Style Application

`apply_common_layout(fig, config)` delegates to `StyleApplicator.apply_styles()`:

```
config dict -> ConfigSpecBuilder.from_config() -> FigureConfig
            -> resolve_config()                 -> FigureConfig (sentinels resolved)
            -> FigureSpecToPlotly.apply()        -> go.Figure mutations
```

### Step 9 -- Display

The controller passes the final figure to `ChartDisplayComponent` for rendering.
Client-side zoom/pan events call `plot.update_from_relayout()` to persist
viewport state.

---

## 8. Style System

### 8.1 StyleUIFactory

**File:** `src/web/pages/ui/plotting/styles/factory.py`

The `StyleUIFactory` dispatches to per-type style UI managers based on the
plot type string.

| Plot Type | Style UI Class | Per-Series Controls |
|-----------|---------------|---------------------|
| `dual_axis_bar_dot` | `BaseStyleUI` | Color override only |
| `line` | `LineStyleUI` | Marker symbol, marker size, line width |
| `scatter` | `ScatterStyleUI` | Marker symbol, marker size, line width |
| `bar`, `grouped_bar`, `stacked_bar`, `grouped_stacked_bar` | `BarStyleUI` | Pattern hatch selector |
| `heatmap`, `histogram` | `BaseStyleUI` | Color override only |

### 8.2 BaseStyleUI

**File:** `src/web/pages/ui/plotting/styles/base_ui.py`

`BaseStyleUI` is the base strategy class. It renders the full style
configurator UI through `render_style_ui()`, which composes five sections:

1. **Series Colors** -- per-series color pickers with palette awareness and custom override toggle.
2. **Data Labels** -- show/hide values, format, position, font size, rotation.
3. **Backgrounds and Grid** -- transparent mode, plot/paper background colors, grid/axis colors.
4. **Legend Styling** -- delegates to `LegendSettingsComponent`.
5. **Typography** -- delegates to `TypographySettingsComponent`.

The key extensibility hook is `_render_specific_series_visuals()`. Subclasses
override this to add type-specific controls within each series color entry.

### 8.3 BarStyleUI

**File:** `src/web/pages/ui/plotting/styles/bar_ui.py`

Adds a hatch pattern selector per series. Available patterns: solid (empty
string), `/`, `\`, `x`, `-`, `|`, `+`, `.`.

### 8.4 LineStyleUI and ScatterStyleUI

**File:** `src/web/pages/ui/plotting/styles/line_ui.py`

`LineStyleUI` adds per-series marker symbol selection (circle, square, diamond,
cross, x, triangle-up, triangle-down), marker size, and line width controls
within an expander. `ScatterStyleUI` inherits from `LineStyleUI` without
modification.

### 8.5 StyleApplicator

**File:** `src/web/pages/ui/plotting/styles/applicator.py`

The `StyleApplicator` bridges the flat `PlotConfig` dictionary to the
engine-agnostic `FigureConfig` model:

1. `ConfigSpecBuilder.from_config(config, plot_type)` builds a `FigureConfig`.
2. `resolve_config()` resolves sentinel values in the config.
3. `FigureSpecToPlotly.apply(spec, fig)` applies all Plotly layout mutations.
4. Raw Plotly shapes (not part of the `FigureConfig` model) are applied directly.

The applicator stores the resolved spec in `self.last_spec` for downstream
consumers such as the LaTeX export pipeline.

---

## 9. See Also

- `src/web/pages/ui/plotting/plot_service.py` -- `PlotService` for create,
  delete, duplicate, change type, and export operations.
- `src/web/pages/ui/plotting/plot_renderer.py` -- `PlotRenderer` for
  cache-key computation utilities.
- `src/web/pages/ui/plotting/utils/grouped_bar_utils.py` -- `GroupedBarUtils`
  for coordinate calculation and shape building in grouped bar layouts.
- `src/web/pages/ui/plotting/utils/grouped_stacked_bar_helpers.py` -- helper
  functions for ordering, renaming, numbered X-axis, and dual-axis features.
- `src/web/rendering/trace_to_plotly.py` -- the `traces_to_plotly()` connector
  that converts `TraceBuildResult` into `go.Figure`.
- `src/core/models/visualization/figure_config.py` -- the `FigureConfig` model
  used by the style application pipeline.
- `src/web/models/plot_models.py` -- `PlotConfig`, `PlotDisplayConfig`,
  `SeriesStyleConfig`, and related TypedDicts.
- `src/web/models/plot_protocols.py` -- `PlotHandle`, `ConfigRenderer`,
  `RenderablePlot` protocol contracts for decoupling controllers from
  concrete implementations.
