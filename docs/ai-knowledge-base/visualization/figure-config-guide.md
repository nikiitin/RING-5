---
title: "FigureConfig Dataclass Hierarchy"
parent: Visualization
grand_parent: AI Knowledge Base
nav_order: 1
---

# FigureConfig Dataclass Hierarchy

> **Scope**: Complete field reference for the engine-agnostic `FigureConfig` composition tree.
> **Key file**: `src/core/models/visualization/figure_config.py` (lines 98-301)

---

## Composition Tree (ASCII)

```
FigureConfig                           figure_config.py:98  @dataclass, mutable
|
+-- dimensions: DimensionConfig        figure_config.py:62
|   +-- width: float = 7.0            (inches)
|   +-- height: float = 4.0           (inches)
|   +-- dpi: int = 300
|   +-- bar_width_scale: float = 1.0
|   +-- bargap: float = 0.15
|   +-- bargroupgap: float = 0.1
|   +-- margins: MarginsConfig         figure_config.py:32
|       +-- top: float = 40.0         (points)
|       +-- bottom: float = 80.0
|       +-- left: float = 60.0
|       +-- right: float = 30.0
|       +-- pad: float = 0.0
|
+-- typography: TypographyConfig       typography_config.py:23
|   +-- font_size_base: int = 10
|   +-- font_size_title: int = 10
|   +-- font_size_xlabel: int = 9
|   +-- font_size_ylabel: int = 9
|   +-- font_size_y2label: int = -1    SENTINEL (inherits ylabel)
|   +-- font_size_ticks: int = 7
|   +-- font_size_yticks: int = 7
|   +-- font_size_y2ticks: int = -1    SENTINEL (inherits yticks)
|   +-- font_size_annotations: int = 6
|   +-- font_size_legend: int = 8
|   +-- font_size_legend2: int = -1    SENTINEL (inherits legend)
|   +-- font_size_legend3: int = -1    SENTINEL (inherits legend)
|   +-- legend3_number_fontsize: int = -1  SENTINEL (inherits legend3)
|   +-- legend3_text_fontsize: int = -1    SENTINEL (inherits legend3)
|   +-- bold_title: bool = False
|   +-- bold_xlabel: bool = False
|   +-- bold_ylabel: bool = False
|   +-- bold_y2label: bool = False
|   +-- bold_ticks: bool = False
|   +-- bold_annotations: bool = True
|   +-- bold_group_labels: bool = True
|   +-- bold_legend: bool = False
|   +-- bold_legend2: bool = False
|   +-- bold_legend3: bool = False
|
+-- axes: AxesConfig                   axis_config.py:80
|   +-- x: AxisConfig                  axis_config.py:22
|   +-- y: AxisConfig                  (same class)
|   +-- y2: AxisConfig | None = None
|   +-- group_label_offset: float = -0.12
|   +-- group_label_alternate: bool = True
|   +-- group_label_alt_spacing: float = 0.05
|   +-- group_order: list[str] | None = None
|   +-- top_axis_line_width: float = 0.0
|   +-- top_axis_line_color: str = "#444"
|   +-- right_axis_line_width: float = 0.0
|   +-- right_axis_line_color: str = "#444"
|
+-- legends: list[LegendConfig]        legend_config.py:94
|   +-- [0] primary
|   +-- [1] secondary (optional)
|   +-- [2] tertiary (optional)
|
+-- traces: list[TraceConfig]          trace_config.py:20
+-- annotations: list[AnnotationConfig]  annotation_config.py:19
+-- separator: SeparatorConfig         figure_config.py:84
+-- data_labels: DataLabelConfig | None  data_label_config.py:16
+-- series_styles: list[SeriesStyleConfig]  series_style_config.py:16
+-- trace_overrides: dict[str, SeriesStyleConfig]
+-- color_palette: list[str]           (Wong 8-color default)
+-- barmode: Literal["group","stack","overlay","relative"] = "group"
+-- hatching_sequence: list[str]       ["/","\\","|","-","+","x","o","O"]
+-- reference_lines: list[ReferenceLineConfig]  annotation_config.py:65
+-- hovermode: str = "x unified"
+-- enable_stripes: bool = False
+-- show_error_bars: bool = False
+-- title: str = ""
+-- paper_bgcolor: str = "white"
+-- plot_bgcolor: str = "white"
+-- font_family: str = "serif"
+-- latex_extra_preamble: str = ""
+-- metadata: dict[str, str] = {}
```

---

## AxisConfig Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `label` | `str` | `""` | Axis title text |
| `label_pad` | `float` | `10.0` | Padding between label and ticks |
| `label_position` | `float` | `0.5` | Vertical position (0=bottom, 1=top) |
| `label_standoff` | `int` | `-1` | SENTINEL -- Plotly standoff |
| `title_vshift` | `float` | `0.0` | Matplotlib label vertical offset |
| `tick_angle` | `float` | `0.0` | Tick label rotation angle |
| `tick_pad` | `float` | `5.0` | Padding between ticks and axis |
| `tick_ha` | `str` | `"center"` | Tick horizontal alignment |
| `tick_offset` | `float` | `0.0` | Horizontal tick offset (points) |
| `tick_values` | `list | None` | `None` | Explicit tick positions |
| `tick_text` | `list[str] | None` | `None` | Explicit tick labels |
| `tick_font_color` | `str` | `""` | Tick label color |
| `show_ticks` | `bool` | `True` | Show tick marks |
| `tick_side` | `str` | `""` | Tick side ("" = default) |
| `tick_dash` | `str` | `"solid"` | Grid line dash style |
| `show_tick_labels` | `bool` | `True` | Show tick label text |
| `dtick` | `float | None` | `None` | Tick step interval |
| `range` | `list[float] | None` | `None` | Axis range [min, max] |
| `scale` | `str` | `"linear"` | "linear" or "log" |
| `margin` | `float` | `0.02` | Axis margin fraction |
| `automargin` | `bool` | `True` | Plotly automargin |
| `show_grid` | `bool` | `True` | Show grid lines |
| `grid_color` | `str` | `"#E5E5E5"` | Grid line color |
| `grid_width` | `float` | `1.0` | Grid line width |
| `axis_color` | `str` | `"#444"` | Axis/spine color |
| `axis_line_color` | `str` | `""` | Per-axis line override |
| `axis_line_width` | `float` | `1.0` | Per-axis line width |
| `category_order` | `list[str] | None` | `None` | Category ordering |
| `label_aliases` | `dict | None` | `None` | Tick label remapping |

**Source**: `src/core/models/visualization/axis_config.py` (lines 22-78)

---

## LegendConfig Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `role` | `str` | `"primary"` | "primary" / "secondary" / "tertiary" |
| `visible` | `bool` | `True` | |
| `font_size` | `int` | `8` | SENTINEL-capable (-1 = inherit primary) |
| `font_family` | `str` | `""` | |
| `bold` | `bool` | `False` | |
| `ncol` | `int` | `1` | Number of columns |
| `col_width` | `float` | `-1.0` | SENTINEL |
| `entrywidth` | `int` | `0` | Plotly entry width (px) |
| `indentation` | `int` | `0` | Plotly indentation |
| `orientation` | `str` | `"vertical"` | "vertical" / "horizontal" |
| `itemsizing` | `str` | `"constant"` | "constant" / "trace" |
| `itemwidth` | `int` | `30` | Min item width (px) |
| `tracegroupgap` | `int` | `10` | Gap between trace groups |
| `order` | `str` | `"normal"` | "normal" / "reversed" |
| `trace_distribution` | `str` | `""` | |
| `position_x` | `float` | `-1.0` | SENTINEL (-1 = auto) |
| `position_y` | `float` | `-1.0` | SENTINEL (-1 = auto) |
| `anchor_x` | `str` | `"auto"` | |
| `anchor_y` | `str` | `"auto"` | |
| `valign` | `str` | `"middle"` | |
| `custom_position` | `bool` | `False` | |
| `bgcolor` | `str` | `""` | |
| `border_width` | `float` | `0.0` | |
| `border_color` | `str` | `"#444"` | |
| `font_color` | `str` | `"#444"` | |
| `title_font_color` | `str` | `"#444"` | |
| `title_font_size` | `int` | `-1` | SENTINEL (inherits own font_size) |
| `title` | `str` | `""` | |
| `number_fontsize` | `int` | `-1` | SENTINEL (inherits own font_size) |
| `text_fontsize` | `int` | `-1` | SENTINEL (inherits own font_size) |
| `spacing` | `LegendSpacingConfig` | factory | See below |
| `colorbar` | `ColorbarConfig` | factory | See below |

**Source**: `src/core/models/visualization/legend_config.py` (lines 94-239)

---

## LegendSpacingConfig Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `columnspacing` | `float` | `0.5` | SENTINEL-capable (-1.0) |
| `handletextpad` | `float` | `0.3` | SENTINEL-capable (-1.0) |
| `labelspacing` | `float` | `0.2` | SENTINEL-capable (-1.0) |
| `handlelength` | `float` | `1.0` | SENTINEL-capable (-1.0) |
| `handleheight` | `float` | `0.7` | SENTINEL-capable (-1.0) |
| `borderpad` | `float` | `0.2` | SENTINEL-capable (-1.0) |
| `borderaxespad` | `float` | `0.5` | SENTINEL-capable (-1.0) |

**Source**: `src/core/models/visualization/legend_config.py` (lines 61-91)

---

## ColorbarConfig Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `title_side` | `str` | `"top"` | |
| `range_mode` | `str` | `"auto"` | "auto" / "manual" |
| `zmin` | `float | None` | `None` | Manual minimum |
| `zmax` | `float | None` | `None` | Manual maximum |
| `nticks` | `int` | `5` | |
| `tick_decimals` | `int` | `2` | |
| `shared` | `bool` | `True` | Shared across heatmaps |
| `tick_angle` | `float` | `0.0` | |
| `tick_side` | `str` | `"right"` | |

**Source**: `src/core/models/visualization/legend_config.py` (lines 23-58)

---

## TraceConfig Hierarchy

```
TraceConfig (base)                     trace_config.py:20
+-- name: str = ""
+-- trace_type: Literal["bar","line","scatter","histogram","heatmap"]
+-- x: list = []
+-- y: list = []
+-- yaxis: Literal["y","y2"] = "y"
+-- color: str = ""
+-- opacity: float = 1.0
+-- visible: bool = True
+-- show_in_legend: bool = True
+-- legendgroup: str = ""
+-- custom_data: dict = {}
|
+-- BarTraceConfig         trace_type="bar"
|   extra: x_positions, bar_width, offset, pattern,
|          border_width, border_color, text_values,
|          text_position, text_angle, text_font_size, error_y
|
+-- LineTraceConfig        trace_type="line"
|   extra: line_width, line_dash, marker_symbol,
|          marker_size, show_markers, fill, error_y
|
+-- ScatterTraceConfig     trace_type="scatter"
|   extra: marker_symbol, marker_size, marker_line_width,
|          marker_line_color, colorscale, size_values, error_y
|
+-- HistogramTraceConfig   trace_type="histogram"
|   extra: nbins, normalization, cumulative
|
+-- HeatmapTraceConfig     trace_type="heatmap"
    extra: col_labels, row_labels, z, colorscale,
           show_values, text, text_font_size,
           text_color_mode, text_color,
           totals_position, totals_count
```

---

## Other Sub-Config Dataclasses

### SeparatorConfig (`figure_config.py:84`)

| Field | Type | Default |
|-------|------|---------|
| `enabled` | `bool` | `False` |
| `style` | `Literal["solid","dash","dot","dashdot"]` | `"dash"` |
| `color` | `str` | `"gray"` |

### DataLabelConfig (`data_label_config.py:16`, frozen=True)

| Field | Type | Default |
|-------|------|---------|
| `enabled` | `bool` | `False` |
| `color_mode` | `Literal["auto","contrast","custom"]` | `"auto"` |
| `custom_color` | `str` | `"#000000"` |
| `font_size` | `int` | `10` |
| `rotation` | `int` | `0` |
| `position` | `str` | `"auto"` |
| `anchor` | `str` | `"auto"` |
| `format_string` | `str` | `".2f"` |
| `display_logic` | `str` | `"all"` |
| `threshold` | `float` | `0.0` |
| `size_constraint` | `str` | `"none"` |
| `auto_contrast` | `bool` | `True` |

### SeriesStyleConfig (`series_style_config.py:16`, frozen=True)

| Field | Type | Default |
|-------|------|---------|
| `line_width` | `float` | `2.0` |
| `marker_size` | `int` | `6` |
| `opacity` | `float` | `1.0` |
| `bar_border_width` | `float` | `0.0` |
| `bar_border_color` | `str` | `""` |
| `hatching_pattern` | `str` | `""` |
| `color` | `str` | `""` |
| `symbol` | `str` | `""` |
| `display_name` | `str` | `""` |

### AnnotationConfig (`annotation_config.py:19`)

| Field | Type | Default |
|-------|------|---------|
| `text` | `str` | `""` |
| `annotation_type` | `str` | `""` |
| `x` | `float | str` | `0` |
| `y` | `float | str` | `0` |
| `xref` | `str` | `"data"` |
| `yref` | `str` | `"data"` |
| `xanchor` | `str` | `"left"` |
| `yanchor` | `str` | `"bottom"` |
| `text_angle` | `float` | `0` |
| `show_arrow` | `bool` | `False` |
| `arrow_head` | `int` | `0` |
| `arrow_color` | `str` | `""` |
| `font_size` | `int` | `-1` |
| `font_color` | `str` | `"#444"` |
| `font_bold` | `bool` | `False` |
| `border_width` | `float` | `0` |
| `border_color` | `str` | `""` |
| `border_pad` | `float` | `0` |
| `bgcolor` | `str` | `""` |
| `align` | `str` | `"left"` |

### ReferenceLineConfig (`annotation_config.py:65`)

| Field | Type | Default |
|-------|------|---------|
| `enabled` | `bool` | `True` |
| `axis` | `str` | `"y"` |
| `value` | `float` | `0.0` |
| `color` | `str` | `"red"` |
| `width` | `float` | `1.5` |
| `style` | `str` | `"dash"` |
| `label` | `str` | `""` |

---

## Config Lifecycle

```
PHASE 1: CREATION
  UI widgets -> Dict[str, Any]
       |
       v
  ConfigSpecBuilder.from_config(config, plot_type)  config_builder.py:362
       |
       v
  FigureConfig (may contain -1 sentinels)

PHASE 2: MODIFICATION (optional)
  a) PresetApplicator.apply(spec, preset)   preset_applicator.py:42
  b) PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)  config_builder.py:112

PHASE 3: RESOLUTION
  resolve_config(spec)                      config_resolver.py:60
       |  deepcopy + resolve typography + legends + axes
       v
  FigureConfig (all sentinels -> concrete values)

PHASE 4: RENDERING
  +-- Plotly:      FigureSpecToPlotly.apply(spec, fig)
  +-- Matplotlib:  FigureSpecToMatplotlib.apply(spec, ax)

PHASE 5: SERIALIZATION
  spec.to_dict() -> JSON -> portfolio file

PHASE 6: RESTORATION
  portfolio file -> JSON -> FigureConfig.from_dict(data)
```

---

## Serialization Protocol

| Config Class | `to_dict()` Strategy | `from_dict()` Strategy |
|-------------|---------------------|----------------------|
| `FigureConfig` | `dataclasses.asdict()` recursive | Explicit field extraction with type coercion |
| `MarginsConfig` | Explicit field enumeration | Constructor `**kwargs` |
| `AxisConfig` | `dataclasses.asdict()` | `__dataclass_fields__` filtering |
| `LegendConfig` | Explicit + delegates to spacing/colorbar | `__dataclass_fields__` filtering |
| `LegendSpacingConfig` | Explicit | `__dataclass_fields__` filtering |
| `ColorbarConfig` | Explicit | `__dataclass_fields__` filtering |
| `DataLabelConfig` | Explicit | Explicit with type coercion |
| `SeriesStyleConfig` | Explicit | Explicit with type coercion |

**Round-trip guarantee**: `FigureConfig.from_dict(spec.to_dict()) == spec`

---

## Mutability Summary

| Config | Frozen? | Sentinel Fields? |
|--------|---------|-----------------|
| `FigureConfig` | No | No (sub-configs have them) |
| `DimensionConfig` | No | No |
| `MarginsConfig` | No | No |
| `TypographyConfig` | No | Yes (7 fields) |
| `AxesConfig` | No | No |
| `AxisConfig` | No | Yes (label_standoff, label_pad, tick_pad on y2) |
| `LegendConfig` | No | Yes (font_size, title_font_size, position_x/y, etc.) |
| `LegendSpacingConfig` | No | Yes (all 7 fields) |
| `ColorbarConfig` | No | No |
| `SeparatorConfig` | No | No |
| `DataLabelConfig` | **Yes** | No |
| `SeriesStyleConfig` | **Yes** | No |
| `AnnotationConfig` | No | Yes (font_size = -1) |
| `TraceConfig` + subclasses | No | No |

---

## File Index

| File | Classes | Lines |
|------|---------|-------|
| `src/core/models/visualization/figure_config.py` | `MarginsConfig`, `DimensionConfig`, `SeparatorConfig`, `FigureConfig` | 301 |
| `src/core/models/visualization/trace_config.py` | `TraceConfig` + 5 subclasses | 151 |
| `src/core/models/visualization/axis_config.py` | `AxisConfig`, `AxesConfig` | 141 |
| `src/core/models/visualization/legend_config.py` | `ColorbarConfig`, `LegendSpacingConfig`, `LegendConfig` | 239 |
| `src/core/models/visualization/typography_config.py` | `TypographyConfig` | 72 |
| `src/core/models/visualization/annotation_config.py` | `AnnotationConfig`, `ReferenceLineConfig` | 78 |
| `src/core/models/visualization/data_label_config.py` | `DataLabelConfig` | 100 |
| `src/core/models/visualization/series_style_config.py` | `SeriesStyleConfig` | 81 |
| `src/core/models/visualization/trace_build_result.py` | `TraceBuildResult` | 44 |
| `src/core/models/visualization/palettes.py` | `PALETTE_REGISTRY` + helpers | 323 |

**Total config classes**: 12 distinct dataclasses. **Total fields**: ~160+.
