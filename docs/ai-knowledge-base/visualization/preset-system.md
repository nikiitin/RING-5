# Preset System

> **Scope**: 13 publication presets, PresetManager loading, PresetSchema types, PresetApplicator overlay.
> **Key files**: `src/web/pages/ui/plotting/export/presets/latex_presets.json`, `src/web/pages/ui/plotting/export/presets/preset_manager.py`, `src/web/pages/ui/plotting/export/presets/preset_schema.py`, `src/web/rendering/preset_applicator.py`, `src/web/rendering/config_builder.py` (PresetSpecBuilder)

---

## Architecture (ASCII)

```
latex_presets.json                          (13 presets, JSON)
       |
       v
PresetManager.load_preset("nature")        preset_manager.py
       |  validate + cache + return LaTeXPreset dict
       v
LaTeXPreset dict (TypedDict)               preset_schema.py
       |
       v
PresetApplicator.apply(config_spec, preset_dict)   preset_applicator.py:42
       |
       |  1. PresetSpecBuilder.from_preset(preset_dict)  -> FigureConfig
       |  2. dataclasses.replace(spec, **overrides)
       v
FigureConfig (merged: preset layout + user data)
       |
       v
resolve_config(spec)                        config_resolver.py:60
       |  resolves -1 sentinels from preset's secondary/tertiary defaults
       v
FigureConfig (ready for connector)
```

---

## 13 Presets Catalog

**Source**: `src/web/pages/ui/plotting/export/presets/latex_presets.json` (272 lines)

| # | Preset | Description | Width | Height | Font | Base Pt | DPI | Line W | Marker | Preamble |
|---|--------|-------------|-------|--------|------|---------|-----|--------|--------|----------|
| 1 | `single_column` | IEEE/ACM single column | 3.5" | 1.97" | serif | 10 | 300 | 1.0 | 4.0 | zi4 |
| 2 | `double_column` | Full width two-column | 7.0" | 5.25" | serif | 10 | 300 | 1.0 | 4.0 | zi4 |
| 3 | `micro` | MICRO conference | 3.5" | 2.5" | serif | 10 | 300 | 1.0 | 4.0 | zi4 |
| 4 | `isca` | ISCA conference | 3.5" | 2.5" | serif | 10 | 300 | 1.0 | 4.0 | zi4 |
| 5 | `asplos` | ASPLOS conference | 3.5" | 2.5" | serif | 10 | 300 | 1.0 | 4.0 | zi4 |
| 6 | `hpca` | HPCA conference | 3.5" | 2.5" | serif | 10 | 300 | 1.0 | 4.0 | zi4 |
| 7 | `taco` | ACM TACO journal | 3.5" | 2.5" | serif | 10 | 300 | 1.0 | 4.0 | zi4 |
| 8 | `nature` | Nature journal | 3.5" | 3.5" | Arial | 7 | 600 | 0.5 | 2.0 | -- |
| 9 | `science` | Science journal | 3.5" | 2.5" | sans-serif | 8 | 600 | 0.5 | 2.0 | -- |
| 10 | `ieee_single` | IEEE transactions | 3.5" | 2.5" | serif | 10 | 300 | 1.0 | 4.0 | -- |
| 11 | `acm` | ACM proceedings | 3.5" | 2.5" | serif | 9 | 300 | 1.0 | 4.0 | zi4 |
| 12 | `poster` | Poster (large) | 10.0" | 7.0" | sans-serif | 24 | 150 | 2.0 | 8.0 | -- |
| 13 | `slides` | Presentation slides | 8.0" | 4.5" | sans-serif | 18 | 150 | 1.5 | 6.0 | -- |

**Observations**:
- Computer architecture presets (micro, isca, asplos, hpca) share identical settings
- `nature` and `science` use smaller fonts (7-8pt), thinner lines (0.5pt), higher DPI (600)
- `poster` and `slides` use large fonts (18-24pt), thick lines, low DPI (150)
- "zi4" = `\usepackage[varqu,scaled=0.95]{zi4}` (Inconsolata monospace font)

### Per-Preset Font Sizes

| Preset | base | title | labels | ticks |
|--------|------|-------|--------|-------|
| single_column | 10 | 10 | 9 | 8 |
| double_column | 10 | 10 | 9 | 8 |
| micro/isca/asplos/hpca/taco | 10 | 10 | 9 | 8 |
| nature | 7 | 8 | 7 | 6 |
| science | 8 | 9 | 8 | 7 |
| ieee_single | 10 | 10 | 9 | 8 |
| acm | 9 | 10 | 9 | 8 |
| poster | 24 | 28 | 24 | 20 |
| slides | 18 | 22 | 18 | 14 |

### Shared Legend Spacing (all 13 presets)

| Parameter | Value |
|-----------|-------|
| `legend_columnspacing` | 1.0 |
| `legend_handletextpad` | 0.5 |
| `legend_labelspacing` | 0.3 |
| `legend_handlelength` | 1.5 |
| `legend_handleheight` | 0.7 |
| `legend_borderpad` | 0.3 |
| `legend_borderaxespad` | 0.3 |

---

## PresetManager

**File**: `src/web/pages/ui/plotting/export/presets/preset_manager.py` (283 lines)

- Singleton-like class with class-level `_cache`, `_presets_data`, `_initialized`
- Lazy initialization: `_initialize()` loads `latex_presets.json` once on first access

### Public API

| Method | Signature | Description |
|--------|-----------|-------------|
| `load_preset` | `(name: str) -> LaTeXPreset` | Load, validate, cache, return preset dict |
| `list_presets` | `() -> list[str]` | All available preset names |
| `get_preset_info` | `(name: str) -> dict` | Metadata (description, typical_use) only |
| `validate_preset` | `(preset: dict) -> None` | Checks required fields + positive values |

### Validation Rules (in `validate_preset()`)

- 19 required fields must be present
- Positive values required for:
  - `width_inches`, `height_inches`
  - `font_size_base`, `font_size_title`, `font_size_xlabel`, `font_size_ylabel`, `font_size_legend`, `font_size_ticks`
  - `line_width`, `marker_size`, `dpi`

---

## LaTeXPreset TypedDict

**File**: `src/web/pages/ui/plotting/export/presets/preset_schema.py` (lines 11-125)

`LaTeXPreset` is a `TypedDict(total=False)` with 60+ optional fields organized into groups:

| Group | Fields | Count |
|-------|--------|-------|
| Physical dimensions | `width_inches`, `height_inches` | 2 |
| Font family + base | `font_family`, `font_size_base` | 2 |
| Per-element font sizes | `font_size_title`, `font_size_labels`, `font_size_xlabel`, `font_size_ylabel`, `font_size_y2label`, `font_size_legend`, `font_size_legend2`, `font_size_legend3`, `font_size_ticks`, `font_size_yticks`, `font_size_y2ticks`, `font_size_annotations` | 12 |
| Bold flags | `bold_title`, `bold_xlabel`, `bold_ylabel`, `bold_y2label`, `bold_legend`, `bold_legend2`, `bold_legend3`, `bold_ticks`, `bold_annotations`, `bold_group_labels` | 10 |
| Line/marker/DPI | `line_width`, `marker_size`, `dpi` | 3 |
| Primary legend spacing | `legend_columnspacing` .. `legend_borderaxespad`, `legend_ncol` | 8 |
| Secondary legend spacing | `legend2_columnspacing` .. `legend2_borderaxespad`, `legend2_ncol` | 8 |
| Tertiary legend | `legend3_borderpad`, `legend3_labelspacing`, `legend3_number_fontsize`, `legend3_text_fontsize` | 4 |
| Positioning | `ylabel_pad`, `ylabel_y_position`, `y2label_pad`, `y2tick_pad`, `xtick_pad`, `ytick_pad`, `group_label_offset`, `group_label_alternate`, `group_label_alt_spacing` | 9 |
| Axis/bar spacing | `xaxis_margin`, `bar_width_scale`, `xtick_rotation`, `xtick_ha`, `xtick_offset` | 5 |
| Legend position | `legend_custom_pos`, `legend_x`, `legend_y` | 3 |
| Separator | `group_separator`, `group_separator_style`, `group_separator_color` | 3 |
| LaTeX preamble | `latex_extra_preamble` | 1 |

---

## ExportResult TypedDict

**File**: `src/web/pages/ui/plotting/export/presets/preset_schema.py` (lines 127-159)

```python
class ExportResult(TypedDict):
    success: bool
    data: bytes | None
    format: str
    error: str | None
    metadata: dict[str, Any]
```

---

## PresetApplicator

**File**: `src/web/rendering/preset_applicator.py` (194 lines)

Stateless service. All methods are `@staticmethod`.

### apply() -- Full Overlay

```python
PresetApplicator.apply(spec, preset_info) -> FigureConfig
```

```
OVERRIDDEN by preset:              KEPT from user config:
  dimensions                         traces
  typography                         annotations
  axes                               data_labels
  legends                            series_styles
  separator                          trace_overrides
  font_family                        color_palette
  latex_extra_preamble               hatching_sequence
                                     reference_lines
                                     hovermode, enable_stripes
                                     show_error_bars, title
                                     paper_bgcolor, plot_bgcolor
                                     barmode, metadata
```

Implementation:
```python
preset_spec = PresetSpecBuilder.from_preset(preset_info)
return dataclasses.replace(spec,
    dimensions=preset_spec.dimensions,
    typography=preset_spec.typography,
    axes=preset_spec.axes,
    legends=preset_spec.legends,
    separator=preset_spec.separator,
    font_family=preset_spec.font_family,
    latex_extra_preamble=preset_spec.latex_extra_preamble,
)
```

Uses `dataclasses.replace()` -- returns a **new** FigureConfig. Never mutates input.

### apply_partial() -- Selective Overlay

```python
PresetApplicator.apply_partial(spec, preset_info) -> FigureConfig
```

Only overrides field groups whose preset keys are actually present. Uses set intersection:

| Key Group | Keys | FigureConfig Field |
|-----------|------|--------------------|
| `_DIMENSION_KEYS` | `width_inches`, `height_inches`, `dpi`, `bar_width_scale` | `dimensions` |
| `_TYPO_KEYS` | All `font_size_*` and `bold_*` (24 keys) | `typography` |
| `_AXES_KEYS` | `xtick_*`, `ylabel_*`, `group_label_*` (11 keys) | `axes` |
| `_LEGEND_KEYS` | `legend_*`, `legend2_*`, `legend3_*` (20 keys) | `legends` |
| `_SEPARATOR_KEYS` | `group_separator`, `group_separator_style`, `group_separator_color` | `separator` |
| (individual) | `font_family` | `font_family` |
| (individual) | `latex_extra_preamble` | `latex_extra_preamble` |

---

## PresetSpecBuilder

**File**: `src/web/rendering/config_builder.py` (lines 188-343, class `PresetSpecBuilder`)

`PresetSpecBuilder.from_preset(preset)` converts the flat `LaTeXPreset` dict to a full `FigureConfig`:

1. **DimensionConfig**: `width_inches` -> `width`, `height_inches` -> `height`, `dpi`, `bar_width_scale`
2. **TypographyConfig**: All 14 font sizes (7 explicit + 7 sentinel `-1` for secondary) + 10 bold flags
3. **AxesConfig**: X-axis (tick rotation/pad/ha/offset/margin) + Y-axis (label pad/position/tick pad) + group labels
4. **3 LegendConfigs**:
   - Primary: concrete spacing from 7 `legend_*` keys
   - Secondary: sentinel `-1.0` spacing from `legend2_*` keys (defaults to `-1.0`)
   - Tertiary: sentinel `-1.0` spacing from `legend3_*` keys
5. **SeparatorConfig**: `group_separator` -> `enabled`, `group_separator_style` -> `style`, `group_separator_color` -> `color`
6. **Scalars**: `font_family`, `latex_extra_preamble`

---

## Preset UI Selection

**File**: `src/web/pages/ui/plotting/settings_pills.py` (~125 lines)

```python
render_preset_pills(plot_id) -> str | None
```

- Lists all presets via `PresetManager.list_presets()`
- Prepends `"none"` option
- Renders `st.pills()` with `selection_mode="single"`, `default="none"`
- Format: "None" for no preset, UPPERCASE for names (e.g., "ISCA")
- Returns selected preset name or `None`

---

## Adding a New Preset

1. Add entry to `src/web/pages/ui/plotting/export/presets/latex_presets.json`
2. Auto-discovered by `PresetManager.list_presets()` (reads JSON `presets` key)
3. Auto-appears in `render_preset_pills()` UI
4. **No code changes required** -- purely data-driven

### Required JSON Fields

```json
{
  "description": "Venue description",
  "width_inches": 3.5,
  "height_inches": 2.5,
  "font_family": "serif",
  "font_size_base": 10,
  "font_size_title": 10,
  "font_size_labels": 9,
  "font_size_ticks": 8,
  "line_width": 1.0,
  "marker_size": 4.0,
  "dpi": 300,
  "legend_columnspacing": 1.0,
  "legend_handletextpad": 0.5,
  "legend_labelspacing": 0.3,
  "legend_handlelength": 1.5,
  "legend_handleheight": 0.7,
  "legend_borderpad": 0.3,
  "legend_borderaxespad": 0.3
}
```

### Optional Fields (with defaults)

- All `bold_*` flags (default `False`, except `bold_annotations=True`, `bold_group_labels=True`)
- `font_size_xlabel`, `font_size_ylabel`, `font_size_yticks`, `font_size_annotations`, `font_size_legend`
- Secondary/tertiary legend spacing (default `-1.0` = inherit primary)
- `xtick_rotation`, `xtick_ha`, `xtick_pad`, `xtick_offset`
- `ylabel_pad`, `ylabel_y_position`, `ytick_pad`
- `group_label_offset`, `group_label_alternate`, `group_label_alt_spacing`
- `bar_width_scale`, `xaxis_margin`
- `group_separator`, `group_separator_style`, `group_separator_color`
- `latex_extra_preamble`

---

## File Index

| File | Role | Lines |
|------|------|-------|
| `src/web/pages/ui/plotting/export/presets/latex_presets.json` | 13 preset definitions (JSON) | 272 |
| `src/web/pages/ui/plotting/export/presets/preset_manager.py` | Load, validate, cache presets | 283 |
| `src/web/pages/ui/plotting/export/presets/preset_schema.py` | `LaTeXPreset` + `ExportResult` TypedDicts | 159 |
| `src/web/rendering/preset_applicator.py` | `PresetApplicator.apply()` + `apply_partial()` | 194 |
| `src/web/rendering/config_builder.py` | `PresetSpecBuilder.from_preset()` | 926 (builder at lines 188-343) |
| `src/web/pages/ui/plotting/settings_pills.py` | `render_preset_pills()` UI | 125 |
