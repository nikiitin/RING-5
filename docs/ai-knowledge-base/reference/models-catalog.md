# RING-5 Models Catalog

> All model classes, type aliases, constants, and validation functions in `src/core/models/`.

---

## Summary Table

| Class | File | Type | Fields |
|---|---|---|---|
| `AnnotationConfig` | `src/core/models/visualization/annotation_config.py` | dataclass | 20 |
| `AxesConfig` | `src/core/models/visualization/axis_config.py` | dataclass | 11 |
| `AxisConfig` | `src/core/models/visualization/axis_config.py` | dataclass | 28 |
| `BarTraceConfig` | `src/core/models/visualization/trace_config.py` | dataclass | 22 (11 inherited + 11 own) |
| `BaseShaperConfig` | `src/core/models/shaper_models.py` | TypedDict | 2 |
| `CacheStatsEntry` | `src/core/models/data_models.py` | TypedDict | 5 |
| `CacheStatsInfo` | `src/core/models/data_models.py` | TypedDict | 3 |
| `ColorbarConfig` | `src/core/models/visualization/legend_config.py` | dataclass | 9 |
| `ColumnInfoResult` | `src/core/models/data_models.py` | TypedDict | 5 |
| `ColumnSelectorConfig` | `src/core/models/shaper_models.py` | TypedDict | 3 (1 own + 2 inherited) |
| `ConditionSelectorConfig` | `src/core/models/shaper_models.py` | TypedDict | 7 (5 own + 2 inherited) |
| `CsvMetadata` | `src/core/models/data_models.py` | TypedDict | 3 |
| `CsvPoolEntry` | `src/core/models/data_models.py` | TypedDict | 7 |
| `DataLabelConfig` | `src/core/models/visualization/data_label_config.py` | dataclass (frozen) | 12 |
| `DimensionConfig` | `src/core/models/visualization/figure_config.py` | dataclass | 7 |
| `FigureConfig` | `src/core/models/visualization/figure_config.py` | dataclass | 22 |
| `HeatmapTraceConfig` | `src/core/models/visualization/trace_config.py` | dataclass | 22 (11 inherited + 11 own) |
| `HistogramTraceConfig` | `src/core/models/visualization/trace_config.py` | dataclass | 14 (11 inherited + 3 own) |
| `ItemSelectorConfig` | `src/core/models/shaper_models.py` | TypedDict | 5 (3 own + 2 inherited) |
| `LegendConfig` | `src/core/models/visualization/legend_config.py` | dataclass | 33 |
| `LegendSpacingConfig` | `src/core/models/visualization/legend_config.py` | dataclass | 7 |
| `LineTraceConfig` | `src/core/models/visualization/trace_config.py` | dataclass | 18 (11 inherited + 7 own) |
| `MarginsConfig` | `src/core/models/visualization/figure_config.py` | dataclass | 5 |
| `MeanShaperConfig` | `src/core/models/shaper_models.py` | TypedDict | 6 (4 own + 2 inherited) |
| `NormalizeShaperConfig` | `src/core/models/shaper_models.py` | TypedDict | 8 (6 own + 2 inherited) |
| `OperationRecord` | `src/core/models/history_models.py` | TypedDict | 4 |
| `ParseBatchResult` | `src/core/models/parsing_models.py` | dataclass (frozen) | 2 |
| `ParseVariableConfig` | `src/core/models/data_models.py` | TypedDict | 18 |
| `PipelineData` | `src/core/models/data_models.py` | TypedDict | 4 |
| `PipelineStep` | `src/core/models/data_models.py` | TypedDict | 3 |
| `PivotLongerShaperConfig` | `src/core/models/shaper_models.py` | TypedDict | 12 (10 own + 2 inherited) |
| `PivotWiderShaperConfig` | `src/core/models/shaper_models.py` | TypedDict | 5 (3 own + 2 inherited) |
| `PlotProtocol` | `src/core/models/plot_protocol.py` | Protocol | 9 attrs + 1 method |
| `PortfolioData` | `src/core/models/portfolio_models.py` | TypedDict | 13 |
| `ReferenceLineConfig` | `src/core/models/visualization/annotation_config.py` | dataclass | 7 |
| `SavedConfigData` | `src/core/models/data_models.py` | TypedDict | 5 |
| `SavedConfigEntry` | `src/core/models/data_models.py` | TypedDict | 4 |
| `ScannedVariable` | `src/core/models/parsing_models.py` | dataclass (frozen) | 4 |
| `ScannedVariableDict` | `src/core/models/data_models.py` | TypedDict | 7 |
| `ScatterTraceConfig` | `src/core/models/visualization/trace_config.py` | dataclass | 18 (11 inherited + 7 own) |
| `SeparatorConfig` | `src/core/models/visualization/figure_config.py` | dataclass | 3 |
| `SeriesStyleConfig` | `src/core/models/visualization/series_style_config.py` | dataclass (frozen) | 9 |
| `ShapeConfig` | `src/core/models/plot_config.py` | TypedDict | 6 |
| `SortShaperConfig` | `src/core/models/shaper_models.py` | TypedDict | 3 (1 own + 2 inherited) |
| `SplitApplyGroupConfig` | `src/core/models/shaper_models.py` | TypedDict | 2 |
| `SplitApplyShaperConfig` | `src/core/models/shaper_models.py` | TypedDict | 4 (2 own + 2 inherited) |
| `StatConfig` | `src/core/models/parsing_models.py` | dataclass (frozen) | 7 |
| `TraceBuildResult` | `src/core/models/visualization/trace_build_result.py` | dataclass | 7 |
| `TraceConfig` | `src/core/models/visualization/trace_config.py` | dataclass | 11 |
| `TransformerShaperConfig` | `src/core/models/shaper_models.py` | TypedDict | 5 (3 own + 2 inherited) |
| `TypographyConfig` | `src/core/models/visualization/typography_config.py` | dataclass | 24 |

---

## Type Aliases

| Alias | File | Definition |
|---|---|---|
| `PlotDeserializer` | `src/core/models/plot_protocol.py` | `Callable[[dict[str, Any]], PlotProtocol \| None]` |
| `ShaperStepConfig` | `src/core/models/shaper_models.py` | `Union[MeanShaperConfig, NormalizeShaperConfig, SortShaperConfig, SplitApplyShaperConfig, TransformerShaperConfig, ColumnSelectorConfig, ConditionSelectorConfig, ItemSelectorConfig, PivotLongerShaperConfig, PivotWiderShaperConfig]` |
| `StatParamValue` | `src/core/models/parsing_models.py` | `str \| int \| float \| bool \| list[str] \| None` |

## Module Constants

| Constant | File | Type | Value |
|---|---|---|---|
| `CSV_DIALECT` | `src/core/models/csv_contract.py` | `str` | `"excel"` |
| `CSV_ENCODING` | `src/core/models/csv_contract.py` | `str` | `"utf-8"` |
| `INHERIT` | `src/core/models/visualization/typography_config.py` | `int` | `-1` |
| `INHERIT_F` | `src/core/models/visualization/axis_config.py`, `legend_config.py`, `typography_config.py` | `float` | `-1.0` |
| `MISSING_VALUE` | `src/core/models/csv_contract.py` | `str` | `""` |
| `PALETTE_REGISTRY` | `src/core/models/visualization/palettes.py` | `dict[str, list[str]]` | 19 palettes (5 colorblind-safe + 14 Plotly qualitative) |

## Validation Functions

| Function | File | Signature |
|---|---|---|
| `validate_parser_csv` | `src/core/models/csv_contract.py` | `(path: Path) -> list[str]` |

---

## Inheritance Hierarchies

**TypedDict inheritance** (`shaper_models.py`):
```
BaseShaperConfig
  ColumnSelectorConfig
  ConditionSelectorConfig
  ItemSelectorConfig
  MeanShaperConfig
  NormalizeShaperConfig
  PivotLongerShaperConfig
  PivotWiderShaperConfig
  SortShaperConfig
  SplitApplyShaperConfig
  TransformerShaperConfig
```

**Dataclass inheritance** (`trace_config.py`):
```
TraceConfig
  BarTraceConfig       (trace_type="bar")
  HeatmapTraceConfig   (trace_type="heatmap")
  HistogramTraceConfig (trace_type="histogram")
  LineTraceConfig      (trace_type="line")
  ScatterTraceConfig   (trace_type="scatter")
```

**Composition** (`figure_config.py`):
```
FigureConfig
  +-- DimensionConfig
  |     +-- MarginsConfig
  +-- TypographyConfig
  +-- AxesConfig
  |     +-- AxisConfig (x)
  |     +-- AxisConfig (y)
  |     +-- AxisConfig (y2, optional)
  +-- list[LegendConfig]
  |     +-- LegendSpacingConfig
  |     +-- ColorbarConfig
  +-- list[TraceConfig]
  +-- list[AnnotationConfig]
  +-- SeparatorConfig
  +-- DataLabelConfig (optional)
  +-- list[SeriesStyleConfig]
  +-- list[ReferenceLineConfig]
```

---

## Model Details (A-L)

### AnnotationConfig
- **File**: `src/core/models/visualization/annotation_config.py`
- **Type**: dataclass
- **Fields**:
  - `text` (str, `""`)
  - `annotation_type` (Literal["text","bar_value","group_label","boxed"], `"text"`)
  - `x` (float | str, `0.0`)
  - `y` (float | str, `0.0`)
  - `xref` (Literal["data","paper"], `"data"`)
  - `yref` (Literal["data","paper"], `"data"`)
  - `xanchor` (Literal["left","center","right","auto"], `"auto"`)
  - `yanchor` (Literal["top","middle","bottom","auto"], `"auto"`)
  - `text_angle` (float, `0.0`)
  - `show_arrow` (bool, `False`)
  - `arrow_head` (int, `0`)
  - `arrow_color` (str, `"#444"`)
  - `font_size` (int, `-1`)
  - `font_color` (str, `"#444"`)
  - `font_bold` (bool, `False`)
  - `border_width` (float, `0.0`)
  - `border_color` (str, `"#444"`)
  - `border_pad` (float, `2.0`)
  - `bgcolor` (str, `""`)
  - `align` (Literal["left","center","right"], `"left"`)
- **Used by**: FigureConfig, TraceBuildResult, Plotly connector, matplotlib connector

### AxesConfig
- **File**: `src/core/models/visualization/axis_config.py`
- **Type**: dataclass
- **Fields**:
  - `x` (AxisConfig, `AxisConfig()`)
  - `y` (AxisConfig, `AxisConfig()`)
  - `y2` (AxisConfig | None, `None`)
  - `group_label_offset` (float, `-0.12`)
  - `group_label_alternate` (bool, `True`)
  - `group_label_alt_spacing` (float, `0.05`)
  - `group_order` (list[str] | None, `None`)
  - `top_axis_line_width` (float, `0.0`)
  - `top_axis_line_color` (str, `"#444"`)
  - `right_axis_line_width` (float, `0.0`)
  - `right_axis_line_color` (str, `"#444"`)
- **Methods**: `to_dict()`, `from_dict(cls, data)`
- **Used by**: FigureConfig

### AxisConfig
- **File**: `src/core/models/visualization/axis_config.py`
- **Type**: dataclass
- **Fields**:
  - `label` (str, `""`)
  - `label_pad` (float, `10.0`)
  - `label_position` (float, `0.5`)
  - `label_standoff` (int, `-1`)
  - `title_vshift` (float, `0.0`)
  - `tick_angle` (float, `0.0`)
  - `tick_pad` (float, `5.0`)
  - `tick_ha` (Literal["left","center","right"], `"center"`)
  - `tick_offset` (float, `0.0`)
  - `tick_values` (list[float|int|str] | None, `None`)
  - `tick_text` (list[str] | None, `None`)
  - `tick_font_color` (str, `""`)
  - `show_ticks` (bool, `True`)
  - `tick_side` (str, `""`)
  - `tick_dash` (str, `"solid"`)
  - `show_tick_labels` (bool, `True`)
  - `dtick` (float | None, `None`)
  - `range` (list[float] | None, `None`)
  - `scale` (Literal["linear","log"], `"linear"`)
  - `margin` (float, `0.02`)
  - `automargin` (bool, `True`)
  - `show_grid` (bool, `True`)
  - `grid_color` (str, `"#E5E5E5"`)
  - `grid_width` (float, `1.0`)
  - `axis_color` (str, `"#444"`)
  - `axis_line_color` (str, `""`)
  - `axis_line_width` (float, `1.0`)
  - `category_order` (list[str] | None, `None`)
  - `label_aliases` (dict[str, str] | None, `None`)
- **Methods**: `to_dict()`, `from_dict(cls, data)`
- **Used by**: AxesConfig (x, y, y2 fields)

### BarTraceConfig
- **File**: `src/core/models/visualization/trace_config.py`
- **Type**: dataclass (extends TraceConfig)
- **Inherited fields**: all 11 from TraceConfig (`trace_type` defaults to `"bar"`)
- **Own fields**:
  - `x_positions` (list[float], `[]`)
  - `bar_width` (float, `0.8`)
  - `offset` (float, `0.0`)
  - `pattern` (str, `""`)
  - `border_width` (float, `0.0`)
  - `border_color` (str, `""`)
  - `text_values` (list[str] | None, `None`)
  - `text_position` (Literal["inside","outside","auto","none"], `"none"`)
  - `text_angle` (float, `0.0`)
  - `text_font_size` (int, `6`)
  - `error_y` (list[float] | None, `None`)
- **Used by**: FigureConfig, TraceBuildResult, Plotly connector, matplotlib connector

### BaseShaperConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False)
- **Fields**:
  - `type` (Required[str])
  - `id` (int)
- **Used by**: all shaper configs inherit from this

### CacheStatsEntry
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=False)
- **Fields**: `size` (int), `maxsize` (int), `hits` (int), `misses` (int), `hit_rate` (float)
- **Used by**: CacheStatsInfo, SimpleCache.stats()

### CacheStatsInfo
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=True)
- **Fields**: `metadata_cache` (CacheStatsEntry), `dataframe_cache` (CacheStatsEntry), `index_size` (int)
- **Used by**: CsvPoolService.get_cache_stats()

### ColorbarConfig
- **File**: `src/core/models/visualization/legend_config.py`
- **Type**: dataclass
- **Fields**:
  - `title_side` (Literal["top","right","bottom","left"], `"top"`)
  - `range_mode` (Literal["auto","manual"], `"auto"`)
  - `zmin` (float | None, `None`)
  - `zmax` (float | None, `None`)
  - `nticks` (int, `5`)
  - `tick_decimals` (int, `2`)
  - `shared` (bool, `True`)
  - `tick_angle` (float, `0.0`)
  - `tick_side` (str, `"right"`)
- **Methods**: `to_dict()`, `from_dict(cls, data)`
- **Used by**: LegendConfig

### ColumnInfoResult
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=True)
- **Fields**: `total_columns` (int), `total_rows` (int), `numeric_columns` (list[str]), `categorical_columns` (list[str]), `columns` (list[str])
- **Used by**: ApplicationAPI.get_column_info()

### ColumnSelectorConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `columns` (Required[list[str]])
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### ConditionSelectorConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `column` (Required[str]), `mode` (Required[str]), `threshold` (float), `range` (list[float]), `values` (list[str])
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### CsvMetadata
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=True)
- **Fields**: `columns` (list[str]), `rows` (int), `dtypes` (dict[str, str])
- **Used by**: CsvPoolService._get_csv_metadata(), CsvPoolEntry

### CsvPoolEntry
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=False, with Required markers)
- **Fields**:
  - `path` (Required[str])
  - `name` (Required[str])
  - `size` (Required[int])
  - `modified` (Required[float])
  - `columns` (list[str])
  - `rows` (int)
  - `dtypes` (dict[str, str])
- **Used by**: CsvPoolService.load_pool(), CSV selection UI

### DataLabelConfig
- **File**: `src/core/models/visualization/data_label_config.py`
- **Type**: dataclass (frozen=True)
- **Fields**:
  - `enabled` (bool, `False`)
  - `color_mode` (Literal["auto","contrast","custom"], `"auto"`)
  - `custom_color` (str, `"#000000"`)
  - `font_size` (int, `10`)
  - `rotation` (int, `0`)
  - `position` (Literal["auto","inside","outside"], `"auto"`)
  - `anchor` (Literal["auto","top","middle","bottom"], `"auto"`)
  - `format_string` (str, `".2f"`)
  - `display_logic` (Literal["all","above_threshold","below_threshold"], `"all"`)
  - `threshold` (float, `0.0`)
  - `size_constraint` (Literal["none","inside"], `"none"`)
  - `auto_contrast` (bool, `True`)
- **Methods**: `to_dict()`, `from_dict(cls, data)`
- **Used by**: FigureConfig

### DimensionConfig
- **File**: `src/core/models/visualization/figure_config.py`
- **Type**: dataclass
- **Fields**:
  - `width` (float, `7.0`) -- inches
  - `height` (float, `4.0`) -- inches
  - `dpi` (int, `300`)
  - `margins` (MarginsConfig, `MarginsConfig()`)
  - `bar_width_scale` (float, `1.0`)
  - `bargap` (float, `0.15`)
  - `bargroupgap` (float, `0.1`)
- **Used by**: FigureConfig

### FigureConfig
- **File**: `src/core/models/visualization/figure_config.py`
- **Type**: dataclass (top-level container)
- **Fields**:
  - `dimensions` (DimensionConfig, `DimensionConfig()`)
  - `typography` (TypographyConfig, lazy via `__post_init__`)
  - `axes` (AxesConfig, lazy via `__post_init__`)
  - `legends` (list[LegendConfig], `[]`)
  - `traces` (list[TraceConfig], `[]`)
  - `annotations` (list[AnnotationConfig], `[]`)
  - `separator` (SeparatorConfig, `SeparatorConfig()`)
  - `data_labels` (DataLabelConfig | None, `None`)
  - `series_styles` (list[SeriesStyleConfig], `[]`)
  - `trace_overrides` (dict[str, SeriesStyleConfig], `{}`)
  - `color_palette` (list[str], Wong 8-color)
  - `barmode` (Literal["group","stack","overlay","relative"], `"group"`)
  - `hatching_sequence` (list[str], `["/","\\","|","-","+","x","o","O"]`)
  - `reference_lines` (list[ReferenceLineConfig], `[]`)
  - `hovermode` (str, `"x unified"`)
  - `enable_stripes` (bool, `False`)
  - `show_error_bars` (bool, `False`)
  - `title` (str, `""`)
  - `paper_bgcolor` (str, `"white"`)
  - `plot_bgcolor` (str, `"white"`)
  - `font_family` (str, `"serif"`)
  - `latex_extra_preamble` (str, `""`)
  - `metadata` (dict[str, str], `{}`)
- **Methods**: `__post_init__()`, `to_dict()`, `from_dict(cls, data)`
- **Used by**: PlotlyFigureSpecBuilder, PresetSpecBuilder, resolve_spec, FigureSpecToPlotly, FigureSpecToMatplotlib

### HeatmapTraceConfig
- **File**: `src/core/models/visualization/trace_config.py`
- **Type**: dataclass (extends TraceConfig)
- **Inherited fields**: all 11 from TraceConfig (`trace_type` defaults to `"heatmap"`)
- **Own fields**:
  - `col_labels` (list[str], `[]`)
  - `row_labels` (list[str], `[]`)
  - `z` (list[list[float | None]], `[]`)
  - `colorscale` (str | list[list[str | float]], `"Viridis"`)
  - `show_values` (bool, `True`)
  - `text` (list[list[str]] | None, `None`)
  - `text_font_size` (int, `10`)
  - `text_color_mode` (str, `"contrast"`)
  - `text_color` (str, `"#000000"`)
  - `totals_position` (str, `""`)
  - `totals_count` (int, `0`)
- **Used by**: FigureConfig, TraceBuildResult, Plotly connector

### HistogramTraceConfig
- **File**: `src/core/models/visualization/trace_config.py`
- **Type**: dataclass (extends TraceConfig)
- **Inherited fields**: all 11 from TraceConfig (`trace_type` defaults to `"histogram"`)
- **Own fields**: `nbins` (int, `20`), `normalization` (Literal["","percent","probability","density"], `""`), `cumulative` (bool, `False`)
- **Used by**: FigureConfig, TraceBuildResult

### ItemSelectorConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `column` (Required[str]), `strings` (Required[list[str]]), `mode` (str)
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### LegendConfig
- **File**: `src/core/models/visualization/legend_config.py`
- **Type**: dataclass (33 fields -- largest visualization dataclass)
- **Fields**:
  - `role` (Literal["primary","secondary","tertiary"], `"primary"`)
  - `visible` (bool, `True`)
  - `font_size` (int, `8`)
  - `font_family` (str, `""`)
  - `bold` (bool, `False`)
  - `ncol` (int, `1`)
  - `col_width` (float, `-1.0`)
  - `entrywidth` (int, `0`)
  - `indentation` (int, `0`)
  - `orientation` (Literal["horizontal","vertical"], `"vertical"`)
  - `itemsizing` (Literal["constant","trace"], `"constant"`)
  - `itemwidth` (int, `30`)
  - `tracegroupgap` (int, `10`)
  - `order` (Literal["normal","reversed"], `"normal"`)
  - `trace_distribution` (str, `""`)
  - `position_x` (float, `-1.0`)
  - `position_y` (float, `-1.0`)
  - `anchor_x` (Literal["left","center","right","auto"], `"auto"`)
  - `anchor_y` (Literal["top","middle","bottom","auto"], `"auto"`)
  - `valign` (Literal["top","middle","bottom"], `"middle"`)
  - `custom_position` (bool, `False`)
  - `bgcolor` (str, `""`)
  - `border_width` (float, `0.0`)
  - `border_color` (str, `"#444"`)
  - `font_color` (str, `"#444"`)
  - `title_font_color` (str, `"#444"`)
  - `title_font_size` (int, `-1`)
  - `title` (str, `""`)
  - `spacing` (LegendSpacingConfig, `LegendSpacingConfig()`)
  - `colorbar` (ColorbarConfig, `ColorbarConfig()`)
  - `number_fontsize` (int, `-1`)
  - `text_fontsize` (int, `-1`)
- **Methods**: `derive_anchors(position_x, position_y)`, `to_dict()`, `from_dict(cls, data)`
- **Used by**: FigureConfig

### LegendSpacingConfig
- **File**: `src/core/models/visualization/legend_config.py`
- **Type**: dataclass
- **Fields**: `columnspacing` (float, `0.5`), `handletextpad` (float, `0.3`), `labelspacing` (float, `0.2`), `handlelength` (float, `1.0`), `handleheight` (float, `0.7`), `borderpad` (float, `0.2`), `borderaxespad` (float, `0.5`)
- **Methods**: `to_dict()`, `from_dict(cls, data)`
- **Used by**: LegendConfig

### LineTraceConfig
- **File**: `src/core/models/visualization/trace_config.py`
- **Type**: dataclass (extends TraceConfig)
- **Inherited fields**: all 11 from TraceConfig (`trace_type` defaults to `"line"`)
- **Own fields**: `line_width` (float, `2.0`), `line_dash` (Literal["solid","dash","dot","dashdot","longdash"], `"solid"`), `marker_symbol` (str, `"circle"`), `marker_size` (int, `6`), `show_markers` (bool, `True`), `fill` (Literal["none","tozeroy","tonexty"], `"none"`), `error_y` (list[float] | None, `None`)
- **Used by**: FigureConfig, TraceBuildResult, Plotly connector, matplotlib connector

---

## Model Details (M-Z)

### MarginsConfig
- **File**: `src/core/models/visualization/figure_config.py`
- **Type**: dataclass
- **Fields**: `top` (float, `40.0`), `bottom` (float, `80.0`), `left` (float, `60.0`), `right` (float, `30.0`), `pad` (float, `0.0`)
- **Methods**: `to_dict()`
- **Used by**: DimensionConfig

### MeanShaperConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `meanVars` (Required[list[str]]), `meanAlgorithm` (Required[str]), `groupingColumns` (Required[list[str]]), `replacingColumn` (Required[str])
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### NormalizeShaperConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `normalizeVars` (Required[list[str]]), `normalizerColumn` (Required[str]), `normalizerValue` (Required[str]), `groupBy` (Required[list[str]]), `normalizerVars` (list[str]), `normalizeSd` (bool)
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### OperationRecord
- **File**: `src/core/models/history_models.py`
- **Type**: TypedDict (total=True)
- **Fields**: `source_columns` (list[str]), `dest_columns` (list[str]), `operation` (str), `timestamp` (str)
- **Used by**: PortfolioData, preprocessor, mixer, outlier remover, seeds reducer

### ParseBatchResult
- **File**: `src/core/models/parsing_models.py`
- **Type**: dataclass (frozen=True)
- **Fields**: `futures` (list[Future[dict[str, Any]]]), `var_names` (list[str])
- **Used by**: worker pool parse submissions, construct_final_csv

### ParseVariableConfig
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=False, with Required markers)
- **Fields**:
  - `name` (Required[str])
  - `type` (Required[str])
  - `_id` (Required[str])
  - `alias` (str)
  - `vectorEntries` (list[str] | str)
  - `useSpecialMembers` (bool)
  - `statisticsOnly` (bool)
  - `statistics` (list[str])
  - `minimum` (float)
  - `maximum` (float)
  - `enableRebin` (bool)
  - `bins` (int)
  - `max_range` (float)
  - `onEmpty` (str)
  - `repeat` (str)
  - `patternSelection` (list[str])
  - `parsed_ids` (list[str])
  - `keepIndices` (bool)
- **Used by**: variable editor UI, StateManager, parser layer, PortfolioData

### PipelineData
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=False, with Required markers)
- **Fields**: `name` (Required[str]), `description` (str), `pipeline` (Required[list[PipelineStep]]), `timestamp` (str)
- **Used by**: PipelineService (JSON serialization)

### PipelineStep
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=True)
- **Fields**: `id` (int), `type` (str), `config` (ShaperStepConfig)
- **Used by**: BasePlot.pipeline, PlotProtocol

### PivotLongerShaperConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**:
  - `id_vars` (Required[list[str]])
  - `value_vars` (Required[list[str]])
  - `var_name` (Required[str])
  - `value_name` (Required[str])
  - `extract_pattern` (str)
  - `extract_group_indices` (list[int])
  - `extract_separator` (str)
  - `selection_filters` (dict[int, list[str]])
  - `selection_strategy` (str)
  - `merge_label` (str)
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### PivotWiderShaperConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `index` (Required[list[str]]), `columns` (Required[str]), `values` (Required[str])
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### PlotProtocol
- **File**: `src/core/models/plot_protocol.py`
- **Type**: Protocol (runtime_checkable)
- **Attributes**:
  - `plot_id` (int)
  - `name` (str)
  - `plot_type` (str)
  - `config` (dict[str, Any])
  - `pipeline` (list[PipelineStep])
  - `pipeline_counter` (int)
  - `legend_mappings_by_column` (dict[str, dict[str, str]])
  - `legend_mappings` (dict[str, str])
  - `processed_data` (pd.DataFrame | None)
- **Methods**: `to_dict() -> dict[str, Any]`
- **Implemented by**: BasePlot (web layer)
- **Used by**: core services, ApplicationAPI

### PortfolioData
- **File**: `src/core/models/portfolio_models.py`
- **Type**: TypedDict (total=False)
- **Fields**:
  - `parse_variables` (list[ParseVariableConfig])
  - `stats_path` (str)
  - `stats_pattern` (str)
  - `csv_path` (str)
  - `use_parser` (bool)
  - `scanned_variables` (list[ScannedVariableDict])
  - `data_csv` (str)
  - `plots` (list[dict[str, Any]])
  - `plot_counter` (int)
  - `config` (dict[str, Any])
  - `shapers` (list[ShaperStepConfig])
  - `manager_history` (list[OperationRecord])
  - `portfolio_history` (list[OperationRecord])
- **Used by**: portfolio save/load service

### ReferenceLineConfig
- **File**: `src/core/models/visualization/annotation_config.py`
- **Type**: dataclass
- **Fields**: `enabled` (bool, `False`), `axis` (Literal["x","y"], `"y"`), `value` (float, `0.0`), `color` (str, `"red"`), `width` (float, `1.5`), `style` (Literal["solid","dash","dot","dashdot"], `"dash"`), `label` (str, `""`)
- **Used by**: FigureConfig

### SavedConfigData
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=False, with Required markers)
- **Fields**: `name` (Required[str]), `description` (str), `timestamp` (str), `shapers` (Required[list[ShaperStepConfig]]), `csv_path` (str | None)
- **Used by**: ConfigService (JSON serialization)

### SavedConfigEntry
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=True)
- **Fields**: `path` (str), `name` (str), `modified` (float), `description` (str)
- **Used by**: ConfigService.load_saved_configs(), config browser UI

### ScannedVariable
- **File**: `src/core/models/parsing_models.py`
- **Type**: dataclass (frozen=True)
- **Fields**: `name` (str), `type` (str), `entries` (list[str], `[]`), `pattern_indices` (list[str] | None, `None`)
- **Methods**: `to_dict() -> ScannedVariableDict`, `from_dict(cls, data) -> ScannedVariable`
- **Used by**: simulator scanner implementations, variable selection UI, parser configuration

### ScannedVariableDict
- **File**: `src/core/models/data_models.py`
- **Type**: TypedDict (total=False, with Required markers)
- **Fields**: `name` (Required[str]), `type` (Required[str]), `entries` (Required[list[str]]), `minimum` (float), `maximum` (float), `pattern_indices` (list[str]), `count` (int)
- **Used by**: ScannedVariable.to_dict(), state management, variable service, PortfolioData

### ScatterTraceConfig
- **File**: `src/core/models/visualization/trace_config.py`
- **Type**: dataclass (extends TraceConfig)
- **Inherited fields**: all 11 from TraceConfig (`trace_type` defaults to `"scatter"`)
- **Own fields**: `marker_symbol` (str, `"circle"`), `marker_size` (int, `8`), `marker_line_width` (float, `0.0`), `marker_line_color` (str, `""`), `colorscale` (str | None, `None`), `size_values` (list[float] | None, `None`), `error_y` (list[float] | None, `None`)
- **Used by**: FigureConfig, TraceBuildResult, Plotly connector, matplotlib connector

### SeparatorConfig
- **File**: `src/core/models/visualization/figure_config.py`
- **Type**: dataclass
- **Fields**: `enabled` (bool, `False`), `style` (Literal["solid","dash","dot","dashdot"], `"dash"`), `color` (str, `"gray"`)
- **Used by**: FigureConfig

### SeriesStyleConfig
- **File**: `src/core/models/visualization/series_style_config.py`
- **Type**: dataclass (frozen=True)
- **Fields**: `line_width` (float, `2.0`), `marker_size` (int, `6`), `opacity` (float, `1.0`), `bar_border_width` (float, `0.0`), `bar_border_color` (str, `""`), `hatching_pattern` (str, `""`), `color` (str, `""`), `symbol` (str, `""`), `display_name` (str, `""`)
- **Methods**: `to_dict()`, `from_dict(cls, data)`
- **Used by**: FigureConfig (series_styles list and trace_overrides dict)

### ShapeConfig
- **File**: `src/core/models/plot_config.py`
- **Type**: TypedDict (total=False, with Required markers)
- **Fields**: `type` (Required[str]), `x0` (Required[float | str]), `y0` (Required[float | str]), `x1` (Required[float | str]), `y1` (Required[float | str]), `line` (dict[str, str | float | int])
- **Used by**: TraceBuildResult, Plotly layout.shapes

### SortShaperConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `order_dict` (Required[dict[str, list[str]]])
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### SplitApplyGroupConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False) -- does NOT inherit BaseShaperConfig
- **Fields**: `columns` (list[str]), `pipeline` (list[ShaperStepConfig])
- **Used by**: SplitApplyShaperConfig (groups field)

### SplitApplyShaperConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `joinColumns` (Required[list[str]]), `groups` (Required[list[SplitApplyGroupConfig]])
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### StatConfig
- **File**: `src/core/models/parsing_models.py`
- **Type**: dataclass (frozen=True)
- **Fields**: `name` (str), `type` (str), `repeat` (int, `1`), `params` (dict[str, StatParamValue], `{}`), `statistics_only` (bool, `False`), `is_regex` (bool, `False`), `keep_indices` (bool, `False`)
- **Used by**: FileParserStrategy implementations

### TraceBuildResult
- **File**: `src/core/models/visualization/trace_build_result.py`
- **Type**: dataclass
- **Fields**:
  - `traces` (Sequence[TraceConfig], `[]`)
  - `annotations` (list[AnnotationConfig], `[]`)
  - `layout_annotations` (list[dict[str, Any]], `[]`)
  - `shapes` (list[ShapeConfig], `[]`)
  - `barmode` (str, `"group"`)
  - `custom_x_ticks` (dict[str, list[float] | list[str] | list[bool]] | None, `None`)
  - `secondary_y` (bool, `False`)
- **Used by**: BasePlot.create_traces(), FigureSpecToPlotly, FigureSpecToMatplotlib

### TraceConfig
- **File**: `src/core/models/visualization/trace_config.py`
- **Type**: dataclass (base class for all trace types)
- **Fields**:
  - `name` (str, `""`)
  - `trace_type` (Literal["bar","line","scatter","histogram","heatmap"], `"bar"`)
  - `x` (list[str | int | float], `[]`)
  - `y` (list[int | float], `[]`)
  - `yaxis` (Literal["y","y2"], `"y"`)
  - `color` (str, `""`)
  - `opacity` (float, `1.0`)
  - `visible` (bool, `True`)
  - `show_in_legend` (bool, `True`)
  - `legendgroup` (str, `""`)
  - `custom_data` (dict[str, Any], `{}`)
- **Used by**: FigureConfig, TraceBuildResult, all trace subclasses

### TransformerShaperConfig
- **File**: `src/core/models/shaper_models.py`
- **Type**: TypedDict (total=False, extends BaseShaperConfig)
- **Own fields**: `column` (Required[str]), `target_type` (Required[str]), `order` (list[str] | None)
- **Inherited fields**: `type` (Required[str]), `id` (int)
- **Used by**: ShaperStepConfig union, shaper pipeline

### TypographyConfig
- **File**: `src/core/models/visualization/typography_config.py`
- **Type**: dataclass
- **Size fields**:
  - `font_size_base` (int, `10`)
  - `font_size_title` (int, `10`)
  - `font_size_xlabel` (int, `9`)
  - `font_size_ylabel` (int, `9`)
  - `font_size_y2label` (int, `-1`)
  - `font_size_ticks` (int, `7`)
  - `font_size_yticks` (int, `7`)
  - `font_size_y2ticks` (int, `-1`)
  - `font_size_annotations` (int, `6`)
  - `font_size_legend` (int, `8`)
  - `font_size_legend2` (int, `-1`)
  - `font_size_legend3` (int, `-1`)
  - `legend3_number_fontsize` (int, `-1`)
  - `legend3_text_fontsize` (int, `-1`)
- **Bold flags**: `bold_title` (False), `bold_xlabel` (False), `bold_ylabel` (False), `bold_y2label` (False), `bold_ticks` (False), `bold_annotations` (True), `bold_group_labels` (True), `bold_legend` (False), `bold_legend2` (False), `bold_legend3` (False)
- **Sentinel inheritance chain**:
  ```
  font_size_base
    font_size_title
    font_size_xlabel
    font_size_ylabel -> font_size_y2label
    font_size_ticks -> font_size_yticks -> font_size_y2ticks
    font_size_annotations
    font_size_legend -> font_size_legend2
                     -> font_size_legend3 -> legend3_number_fontsize
                                          -> legend3_text_fontsize
  ```
- **Used by**: FigureConfig, resolve_spec()

---

## Palette Registry

**File**: `src/core/models/visualization/palettes.py`

### Colorblind-Safe Palettes

| Name | Size | Source |
|---|---|---|
| `okabe_ito` | 8 | Okabe & Ito (2002) |
| `seaborn_cb` | 8 | Seaborn colorblind |
| `tol_bright` | 7 | Paul Tol |
| `viridis_8` | 8 | Viridis 8-stop |
| `wong` | 8 | Wong (2011) -- default palette |

### Plotly Qualitative Palettes

| Name | Size | Name | Size |
|---|---|---|---|
| `Alphabet` | 26 | `Plotly` | 10 |
| `Bold` | 11 | `Safe` | 11 |
| `D3` | 10 | `Set1` | 9 |
| `Dark24` | 24 | `Set2` | 8 |
| `G10` | 10 | `Set3` | 12 |
| `Light24` | 24 | `T10` | 10 |
| `Pastel` | 11 | `Vivid` | 11 |

---

## Serialization Method Coverage

| Has `to_dict()` + `from_dict()` | Has `to_dict()` only | No serialization methods |
|---|---|---|
| AxesConfig | MarginsConfig | All TypedDicts (inherently dict-serializable) |
| AxisConfig | | AnnotationConfig |
| ColorbarConfig | | DimensionConfig |
| DataLabelConfig | | ParseBatchResult |
| FigureConfig | | ReferenceLineConfig |
| LegendConfig | | SeparatorConfig |
| LegendSpacingConfig | | StatConfig |
| ScannedVariable | | TraceConfig and subclasses |
| SeriesStyleConfig | | TraceBuildResult |

---

## Design Patterns

- **Mixed TypedDicts** (`total=False` + `Required`): CsvPoolEntry, SavedConfigData, PipelineData, ParseVariableConfig, ScannedVariableDict, ShapeConfig, all shaper configs
- **Discriminated union**: `ShaperStepConfig` uses the `type` field from `BaseShaperConfig` as a discriminator
- **Sentinel inheritance**: `-1` / `-1.0` values in TypographyConfig and LegendConfig mean "inherit from parent", resolved by `resolve_spec()`
- **Frozen dataclasses**: ParseBatchResult, ScannedVariable, StatConfig, DataLabelConfig, SeriesStyleConfig -- thread-safe sharing across concurrent workers
- **Lazy imports**: `FigureConfig.__post_init__` uses runtime imports to break circular dependencies
- **Protocol-based decoupling**: `PlotProtocol` with `PlotDeserializer` enables core layer to work with plots without knowing concrete implementations
