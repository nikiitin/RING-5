# Visualization Configuration Models

This guide covers the visualization configuration system in RING-5 Unified Engine v2.
`FigureConfig` is the engine-agnostic, canonical description of every visual
aspect of a plot. Both the Plotly and matplotlib connectors consume it without
modification. Source files live under `src/core/models/visualization/`.
Resolution logic lives under `src/core/services/visualization/`.

---

## 1. Overview

The system is organized into three tiers: **Data** (`src/core/models/visualization/` -- 12 `*Config` dataclasses and palette registry), **Logic** (`src/core/services/visualization/` -- sentinel resolution, palette lookup), and **Building** (`src/web/rendering/` -- builders that translate UI dicts or presets into `FigureConfig`).

Key design decisions:

- **Composition over inheritance.** `FigureConfig` is a tree of composed dataclass instances, not a class hierarchy.
- **Sentinel values** (`-1` / `-1.0`) enable inheritance chains resolved in a single pass by `resolve_config()`.
- **Round-trip serialization.** Every config implements `to_dict()` / `from_dict()` for JSON portfolio persistence.
- **Colorblind-safe defaults.** The Wong palette (8 colors) is the default for all new figures.

---

## 2. FigureConfig -- Top-Level Container

**File:** `src/core/models/visualization/figure_config.py`

`FigureConfig` is a mutable `@dataclass` that owns every rendering parameter. Its `__post_init__` lazily initializes `typography` and `axes` to avoid circular imports. It contains approximately 160+ individual settings across 12 nested dataclass types.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `dimensions` | `DimensionConfig` | factory | Physical size, margins, bar gaps |
| `typography` | `TypographyConfig` | `None` (post-init) | Font sizes and bold flags |
| `axes` | `AxesConfig` | `None` (post-init) | X, Y, Y2 axis settings |
| `legends` | `list[LegendConfig]` | `[]` | 1--3 legend instances |
| `traces` | `list[TraceConfig]` | `[]` | Data trace descriptions |
| `annotations` | `list[AnnotationConfig]` | `[]` | Text annotations |
| `separator` | `SeparatorConfig` | factory | Group separator lines |
| `data_labels` | `DataLabelConfig or None` | `None` | Value annotations on traces |
| `series_styles` | `list[SeriesStyleConfig]` | `[]` | Global per-trace styling |
| `trace_overrides` | `dict[str, SeriesStyleConfig]` | `{}` | Named per-trace overrides |
| `color_palette` | `list[str]` | Wong 8 hex | Active color palette |
| `barmode` | `Literal` | `"group"` | `"group"`, `"stack"`, `"overlay"`, `"relative"` |
| `hatching_sequence` | `list[str]` | 8 patterns | B/W bar differentiation |
| `reference_lines` | `list[ReferenceLineConfig]` | `[]` | Horizontal/vertical baselines |
| `hovermode` | `str` | `"x unified"` | Plotly hover behavior |
| `enable_stripes` | `bool` | `False` | Alternating background bands |
| `show_error_bars` | `bool` | `False` | Error bar visibility |
| `title` | `str` | `""` | Figure title text |
| `paper_bgcolor` / `plot_bgcolor` | `str` | `"white"` | Background colors |
| `font_family` | `str` | `"serif"` | Global font family |
| `latex_extra_preamble` | `str` | `""` | Extra LaTeX preamble for export |
| `metadata` | `dict[str, str]` | `{}` | Arbitrary key-value metadata |

**MarginsConfig** holds `top` (40), `bottom` (80), `left` (60), `right` (30), `pad` (0) in points. **DimensionConfig** holds `width` (7.0 in), `height` (4.0 in), `dpi` (300), `margins`, `bar_width_scale` (1.0), `bargap` (0.15), `bargroupgap` (0.1). **SeparatorConfig** holds `enabled` (False), `style` ("dash"), `color` ("gray").

---

## 3. TypographyConfig

**File:** `src/core/models/visualization/typography_config.py`

Controls font sizes (in points) and bold flags for every text element. Fields set to `-1` (the `INHERIT` sentinel) resolve to their parent value during sentinel resolution. Bold flags are always explicit booleans and do not participate in sentinel resolution.

| Field | Default | Inherits From |
|-------|---------|---------------|
| `font_size_base` | 10 | root (no parent) |
| `font_size_title` | 10 | explicit |
| `font_size_xlabel` / `ylabel` | 9 | explicit |
| `font_size_y2label` | -1 | `font_size_ylabel` |
| `font_size_ticks` | 7 | explicit (X-axis ticks) |
| `font_size_yticks` | 7 | explicit (Y-axis ticks) |
| `font_size_y2ticks` | -1 | `font_size_yticks` |
| `font_size_annotations` | 6 | explicit |
| `font_size_legend` | 8 | explicit (primary legend) |
| `font_size_legend2` / `legend3` | -1 | `font_size_legend` |
| `legend3_number_fontsize` / `text_fontsize` | -1 | `font_size_legend3` |

Bold flags: `bold_title`, `bold_xlabel`, `bold_ylabel`, `bold_y2label`, `bold_ticks`, `bold_annotations` (True), `bold_group_labels` (True), `bold_legend`, `bold_legend2`, `bold_legend3`.

---

## 4. AxisConfig and AxesConfig

**File:** `src/core/models/visualization/axis_config.py`

`AxisConfig` describes a single axis: **Label** (`label`, `label_pad` 10pt, `label_position` 0.5, `label_standoff` -1, `title_vshift` 0.0), **Ticks** (`tick_angle`, `tick_pad` 5pt, `tick_ha`, `tick_offset`, `tick_values`, `tick_text`, `tick_font_color`, `show_ticks`, `tick_side`, `tick_dash`, `show_tick_labels`, `dtick`), **Range** (`range`, `scale` linear/log, `margin` 0.02, `automargin`), **Grid** (`show_grid`, `grid_color` #E5E5E5, `grid_width`, `axis_color` #444, `axis_line_color`, `axis_line_width`), **Order** (`category_order`, `label_aliases`).

`AxesConfig` wraps `x: AxisConfig`, `y: AxisConfig`, and `y2: AxisConfig | None`. When `y2` is `None`, the figure has no secondary Y-axis. Additional fields: `group_label_offset` (-0.12), `group_label_alternate` (True), `group_label_alt_spacing` (0.05), `group_order`, `top_axis_line_width` (0.0), `top_axis_line_color`, `right_axis_line_width` (0.0), `right_axis_line_color`.

Y2 inheritance: `y2.label_pad` and `y2.tick_pad` inherit from their `y` counterparts when set to `-1.0`.

---

## 5. LegendConfig

**File:** `src/core/models/visualization/legend_config.py`

All legends use the same `LegendConfig` dataclass distinguished by `role`: `"primary"`, `"secondary"`, or `"tertiary"`. A figure stores `list[LegendConfig]` with 1--3 entries.

Key fields: `visible`, `font_size` (8pt), `font_family`, `bold`, `ncol` (1), `col_width` (-1.0), `orientation` ("vertical"), `itemsizing` ("constant"), `position_x`/`position_y` (-1.0 = auto), `anchor_x`/`anchor_y` ("auto"), `bgcolor`, `border_width`, `border_color`, `title_font_size` (-1), `number_fontsize` (-1), `text_fontsize` (-1).

**LegendSpacingConfig** -- `columnspacing` (0.5), `handletextpad` (0.3), `labelspacing` (0.2), `handlelength` (1.0), `handleheight` (0.7), `borderpad` (0.2), `borderaxespad` (0.5). Secondary/tertiary legends use -1.0 to inherit from primary.

**ColorbarConfig** -- heatmap-specific: `title_side`, `range_mode`, `zmin`/`zmax`, `nticks` (5), `tick_decimals` (2), `shared`, `tick_angle`, `tick_side`.

**Anchor auto-derivation:** `LegendConfig.derive_anchors(x, y)` uses thresholds -- when `x > 0.8`, anchor is `"left"` (box extends inward); when `x < 0.2`, anchor is `"right"`.

---

## 6. TraceConfig Hierarchy

**File:** `src/core/models/visualization/trace_config.py`

Trace configs use dataclass inheritance. The `trace_type` field acts as a discriminator. Base `TraceConfig` has: `name`, `trace_type`, `x`, `y`, `yaxis` (y/y2), `color`, `opacity`, `visible`, `show_in_legend`, `legendgroup`, `custom_data`.

| Subclass | trace_type | Key Extra Fields |
|----------|------------|-----------------|
| `BarTraceConfig` | `"bar"` | `x_positions`, `bar_width`, `offset`, `pattern`, `border_width`, `text_values`, `error_y` |
| `LineTraceConfig` | `"line"` | `line_width`, `line_dash`, `marker_symbol`, `marker_size`, `show_markers`, `fill`, `error_y` |
| `ScatterTraceConfig` | `"scatter"` | `marker_symbol`, `marker_size`, `colorscale`, `size_values`, `error_y` |
| `HistogramTraceConfig` | `"histogram"` | `nbins`, `normalization`, `cumulative` |
| `HeatmapTraceConfig` | `"heatmap"` | `col_labels`, `row_labels`, `z`, `colorscale`, `text_color_mode` |

The key design in `BarTraceConfig` is that plot types pre-compute `x_positions`, `bar_width`, and `offset`, so neither connector needs to reimplement bar grouping math.

---

## 7. AnnotationConfig and ShapeConfig

**File:** `src/core/models/visualization/annotation_config.py`

`AnnotationConfig` describes a text annotation with a discriminator `annotation_type`: `"text"` (free-form), `"bar_value"` (auto-positioned), `"group_label"` (below x-axis), `"boxed"` (tertiary legend item). Key fields: `text`, `x`/`y`, `xref`/`yref` ("data"/"paper"), anchors, `text_angle`, `show_arrow`, `font_size` (-1 = use typography default), `font_color`, `font_bold`, border and background styling.

`ReferenceLineConfig` describes a baseline or threshold line: `enabled`, `axis` ("x"/"y"), `value`, `color` ("red"), `width` (1.5), `style` ("dash"), `label`.

---

## 8. DataLabelConfig

**File:** `src/core/models/visualization/data_label_config.py`

A frozen (`frozen=True`) dataclass for value annotations on traces. Not subject to sentinel resolution. Fields: `enabled` (False), `color_mode` ("auto"/"contrast"/"custom"), `custom_color`, `font_size` (10), `rotation`, `position` ("auto"/"inside"/"outside"), `anchor`, `format_string` (".2f"), `display_logic` ("all"/"above_threshold"/"below_threshold"), `threshold`, `size_constraint` ("none"/"inside"), `auto_contrast` (True).

---

## 9. SeriesStyleConfig

**File:** `src/core/models/visualization/series_style_config.py`

A frozen dataclass for per-trace styling. Stored as a positional list in `series_styles` (matched by index) and as a name-keyed dict in `trace_overrides`. Fields: `line_width` (2.0), `marker_size` (6), `opacity` (1.0), `bar_border_width` (0.0), `bar_border_color`, `hatching_pattern`, `color`, `symbol`, `display_name`.

---

## 10. Palette System

**Files:** `src/core/models/visualization/palettes.py` (data), `src/core/services/visualization/palette_service.py` (logic)

`PALETTE_REGISTRY` combines 5 colorblind-safe palettes (`wong`, `okabe_ito`, `tol_bright`, `viridis_8`, `seaborn_cb`) with 13 Plotly qualitative palettes (`Plotly`, `D3`, `G10`, `T10`, `Alphabet`, `Dark24`, `Light24`, `Set1`--`Set3`, `Pastel`, `Safe`, `Vivid`, `Bold`). All stored as pre-resolved hex lists.

Resolution: `resolve_palette(name)` tries exact match, then case-insensitive match, falling back to Wong. Always returns a copy. `get_palette_names()` returns colorblind-safe first, then Plotly alphabetical. `is_colorblind_safe(name)` checks membership in the colorblind set.

---

## 11. Sentinel Value Resolution

**File:** `src/core/services/visualization/config_resolver.py`

The sentinel value `-1` (int) or `-1.0` (float) means "inherit from parent." This is safe because all config fields are non-negative in valid configurations.

```python
def resolve_config(spec: FigureConfig) -> FigureConfig:
    resolved = deepcopy(spec)          # pure -- never mutates input
    _resolve_typography(resolved.typography)
    _resolve_legends(resolved.legends)
    _resolve_axes(resolved.axes)
    return resolved
```

The function is **pure** (returns a deep copy), **single-pass**, and **idempotent**.

### Typography chain

Resolution order is top-down; dependent fields are resolved after their parents:

```
font_size_ylabel  ----------->  font_size_y2label
font_size_ticks  -->  font_size_yticks  -->  font_size_y2ticks
font_size_legend  +->  font_size_legend2
                  \->  font_size_legend3  +->  legend3_number_fontsize
                                          \->  legend3_text_fontsize
```

### Legend chain

Secondary/tertiary inherit from primary (index 0): `font_size` (-1 to primary's), `title_font_size` (-1 to own resolved font_size), `number_fontsize`/`text_fontsize` (-1 to own font_size). Spacing fields use a generic field-iteration loop -- any `-1.0` in `LegendSpacingConfig` resolves to the primary's corresponding value.

### Axes chain

Only `y2.label_pad` and `y2.tick_pad` inherit from `y` when set to `-1.0`. If `y2 is None`, resolution is a no-op.

---

## 12. Config Hierarchy Diagram

```
FigureConfig
|
+-- dimensions: DimensionConfig
|   +-- width, height, dpi, bar_width_scale, bargap, bargroupgap
|   \-- margins: MarginsConfig {top, bottom, left, right, pad}
|
+-- typography: TypographyConfig
|   +-- font_size_base, font_size_title, font_size_xlabel, ...
|   \-- bold_title, bold_xlabel, bold_ylabel, ...
|
+-- axes: AxesConfig
|   +-- x: AxisConfig
|   +-- y: AxisConfig
|   +-- y2: AxisConfig | None          [inherits from y]
|   \-- group_label_offset, group_label_alternate, ...
|
+-- legends: list[LegendConfig]        [index 0 = primary]
|   \-- each: role, font_size, bold, ncol, position, ...
|       +-- spacing: LegendSpacingConfig
|       \-- colorbar: ColorbarConfig
|
+-- traces: list[TraceConfig]
|   +-- BarTraceConfig, LineTraceConfig, ScatterTraceConfig
|   +-- HistogramTraceConfig, HeatmapTraceConfig
|
+-- annotations: list[AnnotationConfig]
+-- data_labels: DataLabelConfig | None    [frozen]
+-- series_styles: list[SeriesStyleConfig] [frozen]
+-- trace_overrides: dict[str, SeriesStyleConfig]
+-- separator: SeparatorConfig
+-- reference_lines: list[ReferenceLineConfig]
+-- color_palette, barmode, hatching_sequence, hovermode
+-- enable_stripes, show_error_bars, title
+-- paper_bgcolor, plot_bgcolor, font_family
\-- latex_extra_preamble, metadata
```

---

## 13. See Also

- `src/core/models/visualization/figure_config.py` -- FigureConfig, DimensionConfig, MarginsConfig, SeparatorConfig
- `src/core/models/visualization/typography_config.py` -- TypographyConfig
- `src/core/models/visualization/axis_config.py` -- AxisConfig, AxesConfig
- `src/core/models/visualization/legend_config.py` -- LegendConfig, LegendSpacingConfig, ColorbarConfig
- `src/core/models/visualization/trace_config.py` -- TraceConfig and all subclasses
- `src/core/models/visualization/annotation_config.py` -- AnnotationConfig, ReferenceLineConfig
- `src/core/models/visualization/data_label_config.py` -- DataLabelConfig
- `src/core/models/visualization/series_style_config.py` -- SeriesStyleConfig
- `src/core/models/visualization/palettes.py` -- PALETTE_REGISTRY, color definitions
- `src/core/services/visualization/config_resolver.py` -- resolve_config, SENTINEL_INT, SENTINEL_FLOAT
- `src/core/services/visualization/palette_service.py` -- resolve_palette, get_palette_names
- `src/web/rendering/config_builder.py` -- ConfigSpecBuilder, PlotlyFigureSpecBuilder, PresetSpecBuilder
- `src/web/rendering/preset_applicator.py` -- PresetApplicator
