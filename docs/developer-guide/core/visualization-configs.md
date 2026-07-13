---
title: "Visualization Configuration Models"
parent: Core
grand_parent: Developer Guide
nav_order: 4
---

# Visualization Configuration Models

This guide covers the visualization configuration system in RING-5 Unified Engine v2.
`FigureConfig` is the engine-agnostic, canonical description of every visual
aspect of a plot. Both the Plotly and matplotlib connectors consume it without
modification. Source files live under `src/core/models/visualization/`.
Resolution logic lives under `src/core/services/visualization/`.

---

## 1. Overview

The system is organized into three tiers: **Data** (`src/core/models/visualization/` -- 12 `*Config` dataclasses and palette registry), **Logic** (`src/core/services/visualization/` -- sentinel resolution, palette lookup), and **Building** (`src/web/rendering/` -- builders that translate UI dicts and Plotly figures into `FigureConfig`).

Key design decisions:

- **Composition over inheritance.** `FigureConfig` is a tree of composed dataclass instances, not a class hierarchy.
- **Sentinel values** (`-1` / `-1.0`) enable inheritance chains resolved in a single pass by `resolve_config()`.
- **Round-trip serialization.** Every config implements `to_dict()` / `from_dict()` for JSON portfolio persistence.
- **Colorblind-safe defaults.** The Wong palette (8 colors) is the default for all new figures.

---

## 2. FigureConfig -- Top-Level Container

**File:** `src/core/models/visualization/figure_config.py`

`FigureConfig` is a mutable `@dataclass` that owns every rendering parameter. Its `__post_init__` lazily initializes `typography` and `axes` to avoid circular imports. The full tree contains approximately 160+ individual settings across 12 nested dataclass types.

| Field | Type | Default |
|-------|------|---------|
| `dimensions` | `DimensionConfig` | factory |
| `typography` | `TypographyConfig` | None (post-init) |
| `axes` | `AxesConfig` | None (post-init) |
| `legends` | `list[LegendConfig]` | `[]` (1--3 entries) |
| `traces` | `list[TraceConfig]` | `[]` |
| `annotations` | `list[AnnotationConfig]` | `[]` |
| `separator` | `SeparatorConfig` | factory |
| `data_labels` | `DataLabelConfig or None` | `None` |
| `series_styles` | `list[SeriesStyleConfig]` | `[]` |
| `trace_overrides` | `dict[str, SeriesStyleConfig]` | `{}` |
| `color_palette` | `list[str]` | Wong 8 hex |
| `barmode` | `Literal[...]` | `"group"` |
| `hatching_sequence` | `list[str]` | 8 patterns |
| `reference_lines` | `list[ReferenceLineConfig]` | `[]` |
| `hovermode` | `str` | `"x unified"` |
| `enable_stripes` / `show_error_bars` | `bool` | `False` |
| `title` | `str` | `""` |
| `paper_bgcolor` / `plot_bgcolor` | `str` | `"white"` |
| `font_family` | `str` | `"serif"` |
| `latex_extra_preamble` | `str` | `""` |
| `metadata` | `dict[str, str]` | `{}` |

**MarginsConfig** -- `top` (40), `bottom` (80), `left` (60), `right` (30), `pad` (0), all in points. **DimensionConfig** -- `width` (7.0 in), `height` (4.0 in), `dpi` (300), `margins`, `bar_width_scale` (1.0), `bargap` (0.15), `bargroupgap` (0.1). **SeparatorConfig** -- `enabled` (False), `style` ("dash"), `color` ("gray").

---

## 3. TypographyConfig

**File:** `src/core/models/visualization/typography_config.py`

Controls font sizes (in points) and bold flags for every text element. Fields set to `-1` (the `INHERIT` sentinel) resolve to their parent value during sentinel resolution. Bold flags are always explicit booleans and do not participate in resolution.

| Field | Default | Inherits From |
|-------|---------|---------------|
| `font_size_title` | 10 | explicit |
| `font_size_xlabel` / `ylabel` | 9 | explicit |
| `font_size_y2label` | -1 | `font_size_ylabel` |
| `font_size_ticks` | 7 | explicit (X-axis ticks) |
| `font_size_yticks` | 7 | explicit (Y-axis ticks) |
| `font_size_y2ticks` | -1 | `font_size_yticks` |
| `font_size_legend` | 8 | explicit (primary legend) |
| `font_size_legend2` | -1 | `font_size_legend` |

Bold flags: `bold_title`, `bold_xlabel`, `bold_ylabel`, `bold_y2label`, `bold_ticks` (all False).

---

## 4. AxisConfig and AxesConfig

**File:** `src/core/models/visualization/axis_config.py`

`AxisConfig` describes a single axis with field groups: **Label** (`label`, `label_pad` 10pt, `label_position` 0.5, `label_standoff` -1, `title_vshift`), **Ticks** (`tick_angle`, `tick_pad` 5pt, `tick_ha`, `tick_offset`, `tick_values`, `tick_text`, `tick_font_color`, `show_ticks`, `tick_side`, `tick_dash`, `show_tick_labels`, `dtick`), **Range** (`range`, `scale` linear/log, `margin` 0.02, `automargin`), **Grid** (`show_grid`, `grid_color` #E5E5E5, `grid_width`, `axis_color` #444, `axis_line_color`, `axis_line_width`), **Order** (`category_order`, `label_aliases`).

`AxesConfig` wraps `x: AxisConfig`, `y: AxisConfig`, `y2: AxisConfig | None` (None = no secondary Y-axis), plus `group_label_offset` (-0.12), `group_label_alternate` (True), `group_label_alt_spacing` (0.05), `group_order`, and opposite axis line settings (`top_axis_line_width`, `right_axis_line_width`, both 0.0 by default).

Y2 inheritance: `y2.label_pad` and `y2.tick_pad` inherit from `y` when set to `-1.0`.

---

## 5. LegendConfig

**File:** `src/core/models/visualization/legend_config.py`

All legends use the same `LegendConfig` dataclass distinguished by `role` (`"primary"`, `"secondary"`, `"tertiary"`). A figure stores `list[LegendConfig]` with 1--3 entries.

Key fields by group -- **Typography:** `font_size` (8), `font_family`, `bold`. **Layout:** `ncol`, `col_width` (-1.0), `orientation` ("vertical"), `itemsizing`, `itemwidth`, `tracegroupgap`, `order`. **Position:** `position_x`/`position_y` (-1.0 = auto), `anchor_x`/`anchor_y` ("auto"), `custom_position`. **Styling:** `bgcolor`, `border_width`, `border_color`, `font_color`, `title_font_size` (-1), `title`.

**LegendSpacingConfig** -- `columnspacing` (0.5), `handletextpad` (0.3), `labelspacing` (0.2), `handlelength` (1.0), `handleheight` (0.7), `borderpad` (0.2), `borderaxespad` (0.5). Secondary/tertiary use -1.0 to inherit from primary.

**ColorbarConfig** -- heatmap-specific: `title_side`, `range_mode`, `zmin`/`zmax`, `nticks` (5), `tick_decimals` (2), `shared`, `tick_angle`, `tick_side`.

**Multi-level inheritance:** secondary/tertiary `font_size` (-1) resolves to primary's; `title_font_size` (-1) resolves to own resolved `font_size`. Every spacing field at -1.0 resolves to the primary's corresponding value.

**Anchor auto-derivation:** `LegendConfig.derive_anchors(x, y)` -- when `x > 0.8`, anchor is `"left"` (extends inward); when `x < 0.2`, anchor is `"right"`. Same vertically.

---

## 6. TraceConfig Hierarchy

**File:** `src/core/models/visualization/trace_config.py`

Trace configs use dataclass inheritance with `trace_type` as discriminator. Base `TraceConfig` has: `name`, `trace_type`, `x`, `y`, `yaxis` (y/y2), `color`, `opacity`, `visible`, `show_in_legend`, `legendgroup`, `custom_data`.

| Subclass | trace_type | Key Extra Fields |
|----------|------------|-----------------|
| `BarTraceConfig` | `"bar"` | `x_positions`, `bar_width`, `offset`, `pattern`, `border_width`, `text_values`, `text_position`, `error_y` |
| `LineTraceConfig` | `"line"` | `line_width`, `line_dash`, `marker_symbol`, `marker_size`, `show_markers`, `fill`, `error_y` |
| `ScatterTraceConfig` | `"scatter"` | `marker_symbol`, `marker_size`, `colorscale`, `size_values`, `error_y` |
| `HistogramTraceConfig` | `"histogram"` | `nbins`, `normalization`, `cumulative` |
| `HeatmapTraceConfig` | `"heatmap"` | `col_labels`, `row_labels`, `z`, `colorscale`, `text_color_mode` |

`BarTraceConfig` carries pre-computed `x_positions`, `bar_width`, and `offset` so neither connector reimplements bar grouping math. `HistogramTraceConfig` exists for the rare case of raw unbinned data; most histograms are pre-binned as `BarTraceConfig`.

---

## 7. AnnotationConfig and ShapeConfig

**File:** `src/core/models/visualization/annotation_config.py`

`AnnotationConfig` describes a text annotation with discriminator `annotation_type`: `"text"` (free-form), `"bar_value"` (auto-positioned), `"group_label"` (below x-axis), `"boxed"` (tertiary legend item). Key fields: `text`, `x`/`y`, `xref`/`yref`, anchors, `text_angle`, `show_arrow`, `font_size` (-1 = use typography default), `font_color`, `font_bold`, border and background styling.

`ReferenceLineConfig` -- a horizontal or vertical line: `enabled`, `axis` ("x"/"y"), `value`, `color` ("red"), `width` (1.5), `style` ("dash"), `label`.

---

## 8. DataLabelConfig

**File:** `src/core/models/visualization/data_label_config.py`

A frozen (`frozen=True`) dataclass for value annotations on traces. Because it is frozen, it cannot be mutated after creation and is not subject to sentinel resolution.

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `False` | Master toggle |
| `color_mode` | `"auto"` | `"auto"`, `"contrast"`, `"custom"` |
| `custom_color` | `"#000000"` | Color when mode is `"custom"` |
| `font_size` | 10 | Size in points |
| `rotation` | 0 | Degrees (-90 to 90) |
| `position` | `"auto"` | `"auto"`, `"inside"`, `"outside"` |
| `anchor` | `"auto"` | `"auto"`, `"top"`, `"middle"`, `"bottom"` |
| `format_string` | `".2f"` | d3-format string |
| `display_logic` | `"all"` | `"all"`, `"above_threshold"`, `"below_threshold"` |
| `threshold` | 0.0 | Numeric threshold for conditional display |
| `size_constraint` | `"none"` | `"none"` or `"inside"` (resize to fit bars) |
| `auto_contrast` | `True` | Flip text color based on background luminance |

---

## 9. SeriesStyleConfig

**File:** `src/core/models/visualization/series_style_config.py`

A frozen dataclass for per-trace styling overrides. Stored in two places on `FigureConfig`: as a positional list in `series_styles` (matched by index to traces) and as a name-keyed dict in `trace_overrides`.

| Field | Default | Purpose |
|-------|---------|---------|
| `line_width` | 2.0 | Line width in points |
| `marker_size` | 6 | Marker diameter in points |
| `opacity` | 1.0 | Fill/marker opacity |
| `bar_border_width` | 0.0 | Bar border width |
| `bar_border_color` | `""` | Bar border color |
| `hatching_pattern` | `""` | Hatch pattern for bars |
| `color` | `""` | Explicit trace color override |
| `symbol` | `""` | Marker symbol override |
| `display_name` | `""` | Legend entry rename |

---

## 10. Palette System

**Files:** `src/core/models/visualization/palettes.py` (data), `src/core/services/visualization/palette_service.py` (logic)

`PALETTE_REGISTRY` combines two internal dictionaries at module load time: `{**_COLORBLIND_PALETTES, **_PLOTLY_PALETTES}`. All palettes are stored as pre-resolved hex lists with no runtime Plotly dependency.

### Colorblind-safe palettes (5)

| Name | Colors | Source |
|------|--------|--------|
| `wong` | 8 | Wong (2011) -- **the default for all new figures** |
| `okabe_ito` | 8 | Okabe and Ito (same colors as Wong, different order) |
| `tol_bright` | 7 | Paul Tol bright scheme |
| `viridis_8` | 8 | Discrete 8-color sampling of the Viridis colormap |
| `seaborn_cb` | 8 | Seaborn colorblind palette |

### Plotly qualitative palettes (13)

| Name | Colors | | Name | Colors |
|------|--------|-|------|--------|
| `Plotly` | 10 | | `Set1` | 9 |
| `D3` | 10 | | `Set2` | 8 |
| `G10` | 10 | | `Set3` | 12 |
| `T10` | 10 | | `Pastel` | 11 |
| `Alphabet` | 26 | | `Safe` | 11 |
| `Dark24` | 24 | | `Vivid` | 11 |
| `Light24` | 24 | | `Bold` | 11 |

### Resolution logic

`resolve_palette(name)` follows a four-step resolution order:

1. If `name` is `None`, empty, or not a string, return the Wong palette (copy).
2. Exact match in `PALETTE_REGISTRY` -- return copy.
3. Case-insensitive match -- return copy.
4. No match -- return Wong palette (copy).

Always returns a copy (safe to mutate). `get_palette_names()` returns an ordered list with colorblind-safe palettes first, then Plotly palettes alphabetically. `is_colorblind_safe(name)` checks membership in the colorblind-safe set.

---

## 11. Sentinel Value Resolution

**File:** `src/core/services/visualization/config_resolver.py`

### The sentinel pattern

The sentinel value `-1` (int) or `-1.0` (float) means "inherit from the nearest parent in the resolution chain." This is safe because all config fields are non-negative in valid configurations.

```python
SENTINEL_INT: int = -1       # for integer fields (font sizes, ncol)
SENTINEL_FLOAT: float = -1.0 # for float fields (positions, spacing)
```

Module-level aliases: `INHERIT = -1` in `typography_config.py`, `INHERIT_F = -1.0` in `typography_config.py`, `axis_config.py`, and `legend_config.py`.

### resolve_config()

```python
def resolve_config(spec: FigureConfig) -> FigureConfig:
    resolved = deepcopy(spec)          # pure -- never mutates input
    _resolve_typography(resolved.typography)
    _resolve_legends(resolved.legends)
    _resolve_axes(resolved.axes)
    return resolved
```

The function is **pure** (deep copy), **single-pass**, **idempotent**, and **fail-safe** (skips chains on type-check failure).

### Typography chain

Resolution processes top-down so dependent fields see already-resolved parents:

```
font_size_ylabel  ----------->  font_size_y2label
font_size_ticks  -->  font_size_yticks  -->  font_size_y2ticks
font_size_legend  -->  font_size_legend2
```

Example: `font_size_legend = 8`, `font_size_legend2 = -1` resolves to 8.

### Legend chain

Secondary/tertiary (indices 1, 2) inherit from primary (index 0):

- `font_size`: -1 resolves to `primary.font_size`.
- `title_font_size`: -1 resolves to own resolved `font_size`.
- Spacing: generic field-iteration replaces any -1.0 with primary's value:

```python
for f in fields(spacing):
    val = getattr(spacing, f.name)
    if isinstance(val, float) and val == SENTINEL_FLOAT:
        setattr(spacing, f.name, getattr(parent, f.name))
```

The primary legend also resolves its own `title_font_size` relative to its own `font_size`.

### Axes chain

Only `y2.label_pad` and `y2.tick_pad` inherit from `y` when set to `-1.0`. If `y2 is None`, resolution is a no-op.

### Atomic helpers

The two building-block functions used throughout resolution:

```python
def _resolve_int(value: int, parent: int) -> int:
    return parent if value == SENTINEL_INT else value

def _resolve_float(value: float, parent: float) -> float:
    return parent if value == SENTINEL_FLOAT else value
```

### Immutability notes

`DataLabelConfig` and `SeriesStyleConfig` are frozen dataclasses (`frozen=True`). They cannot be mutated after creation and have no sentinel fields, so they are never subject to resolution. All other config dataclasses are mutable, which allows the resolver to modify the deep-copied config tree in-place during its single pass.

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
|   +-- font_size_title, font_size_xlabel, font_size_ylabel, ...
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
\-- enable_stripes, show_error_bars, title, font_family, metadata
```

### Sentinel inheritance arrows

```
Typography:
  font_size_ylabel --------> font_size_y2label
  font_size_ticks ---------> font_size_yticks -------> font_size_y2ticks
  font_size_legend --------> font_size_legend2
Legends (list):
  legends[0].font_size ----> legends[1].font_size, legends[2].font_size
  legends[0].spacing.* ----> legends[1].spacing.*, legends[2].spacing.*
  each legend.font_size ---> own title_font_size
Axes:
  axes.y.label_pad --------> axes.y2.label_pad
  axes.y.tick_pad ---------> axes.y2.tick_pad
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
- `src/web/rendering/config_builder.py` -- ConfigSpecBuilder, PlotlyFigureSpecBuilder
