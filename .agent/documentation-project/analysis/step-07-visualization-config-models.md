# Step 07 — Visualization Config Models (Deep Dive)

> **Objective**: Deep-dive into the visualization configuration system —
> composition tree, sentinel resolution, preset system, and serialization.

---

## 1. Executive Summary

The RING-5 Unified Engine v2 visualization configuration system is built around
**`FigureConfig`** — a single, engine-agnostic dataclass that serves as the
**canonical description** of every visual aspect of a plot. Both the Plotly and
matplotlib connectors consume this object; neither modifies it.

The system is organized into three architectural tiers:

| Tier | Layer | Responsibility |
|------|-------|----------------|
| **Data** | `src/core/models/visualization/` | 12 `*Config` dataclasses + palette registry |
| **Logic** | `src/core/services/visualization/` | Sentinel resolution, palette lookup, interaction |
| **Building** | `src/web/rendering/` | 3 builders (`ConfigSpecBuilder`, `PlotlyFigureSpecBuilder`, `PresetSpecBuilder`), preset applicator, 2 connectors |

Key design patterns:

- **Composition over inheritance**: `FigureConfig` is a tree of composed
  sub-config dataclasses (not a class hierarchy).
- **Sentinel values** (`-1` / `-1.0`): Enable inheritance chains resolved in
  one pass by `resolve_config()`.
- **Preset overlay**: 13 journal/venue-specific presets override
  presentation-layer fields while preserving data-derived fields.
- **Round-trip serialization**: Every config class implements `to_dict()` /
  `from_dict()` for JSON portfolio persistence.
- **Colorblind-safe defaults**: The Wong palette is the default; 5 colorblind-safe
  + 13 Plotly palettes are registered.

**File counts**: 12 model modules, 3 service modules, 4 builder/applicator
modules, 1 JSON preset file, 1 TypedDict schema module.

---

## 2. FigureConfig Composition Tree

```
FigureConfig  (src/core/models/visualization/figure_config.py:98)
│   @dataclass, mutable, __post_init__ for lazy defaults
│
├── dimensions: DimensionConfig  (figure_config.py:62)
│   │   width: float = 7.0 (inches)
│   │   height: float = 4.0 (inches)
│   │   dpi: int = 300
│   │   bar_width_scale: float = 1.0
│   │   bargap: float = 0.15
│   │   bargroupgap: float = 0.1
│   │
│   └── margins: MarginsConfig  (figure_config.py:32)
│       top=40.0, bottom=80.0, left=60.0, right=30.0, pad=0.0  (all pts)
│
├── typography: TypographyConfig  (typography_config.py:23)
│   │   font_size_base=10, font_size_title=10, font_size_xlabel=9,
│   │   font_size_ylabel=9, font_size_y2label=-1 (INHERIT),
│   │   font_size_ticks=7, font_size_yticks=7, font_size_y2ticks=-1,
│   │   font_size_annotations=6, font_size_legend=8,
│   │   font_size_legend2=-1, font_size_legend3=-1,
│   │   legend3_number_fontsize=-1, legend3_text_fontsize=-1,
│   │   bold_title=False, bold_xlabel=False, bold_ylabel=False,
│   │   bold_y2label=False, bold_ticks=False, bold_annotations=True,
│   │   bold_group_labels=True, bold_legend=False,
│   │   bold_legend2=False, bold_legend3=False
│   (no sub-objects)
│
├── axes: AxesConfig  (axis_config.py:80)
│   │   group_label_offset=-0.12, group_label_alternate=True,
│   │   group_label_alt_spacing=0.05, group_order=None,
│   │   top_axis_line_width=0.0, top_axis_line_color="#444",
│   │   right_axis_line_width=0.0, right_axis_line_color="#444"
│   │
│   ├── x: AxisConfig  (axis_config.py:22)
│   │       label, label_pad=10.0, label_position=0.5,
│   │       label_standoff=-1, title_vshift=0.0,
│   │       tick_angle=0.0, tick_pad=5.0, tick_ha="center",
│   │       tick_offset=0.0, tick_values=None, tick_text=None,
│   │       tick_font_color="", show_ticks=True, tick_side="",
│   │       tick_dash="solid", show_tick_labels=True, dtick=None,
│   │       range=None, scale="linear", margin=0.02,
│   │       automargin=True, show_grid=True, grid_color="#E5E5E5",
│   │       grid_width=1.0, axis_color="#444", axis_line_color="",
│   │       axis_line_width=1.0, category_order=None,
│   │       label_aliases=None
│   │
│   ├── y: AxisConfig  (same class as x)
│   │
│   └── y2: AxisConfig | None  (None = no secondary Y-axis)
│           Inherits label_pad and tick_pad from y when sentinel
│
├── legends: list[LegendConfig]  (legend_config.py:94)
│   │   Typically 1-3 entries: [primary, secondary?, tertiary?]
│   │
│   └── LegendConfig (per entry):
│       │   role: "primary" | "secondary" | "tertiary"
│       │   visible=True, font_size=8, font_family="", bold=False,
│       │   ncol=1, col_width=-1.0, entrywidth=0, indentation=0,
│       │   orientation="vertical", itemsizing="constant",
│       │   itemwidth=30, tracegroupgap=10, order="normal",
│       │   trace_distribution="", position_x=-1.0, position_y=-1.0,
│       │   anchor_x="auto", anchor_y="auto", valign="middle",
│       │   custom_position=False, bgcolor="", border_width=0.0,
│       │   border_color="#444", font_color="#444",
│       │   title_font_color="#444", title_font_size=-1, title="",
│       │   number_fontsize=-1, text_fontsize=-1
│       │
│       ├── spacing: LegendSpacingConfig  (legend_config.py:61)
│       │       columnspacing=0.5, handletextpad=0.3,
│       │       labelspacing=0.2, handlelength=1.0,
│       │       handleheight=0.7, borderpad=0.2,
│       │       borderaxespad=0.5
│       │
│       └── colorbar: ColorbarConfig  (legend_config.py:23)
│               title_side="top", range_mode="auto",
│               zmin=None, zmax=None, nticks=5,
│               tick_decimals=2, shared=True, tick_angle=0.0,
│               tick_side="right"
│
├── traces: list[TraceConfig]  (trace_config.py:20)
│       (populated by plot type's create_traces())
│
├── annotations: list[AnnotationConfig]  (annotation_config.py:19)
│       text, annotation_type, x, y, xref, yref, xanchor, yanchor,
│       text_angle, show_arrow, arrow_head, arrow_color,
│       font_size=-1, font_color, font_bold,
│       border_width, border_color, border_pad, bgcolor, align
│
├── separator: SeparatorConfig  (figure_config.py:84)
│       enabled=False, style="dash", color="gray"
│
├── data_labels: DataLabelConfig | None  (data_label_config.py:16)
│       @dataclass(frozen=True)
│       enabled=False, color_mode="auto", custom_color="#000000",
│       font_size=10, rotation=0, position="auto", anchor="auto",
│       format_string=".2f", display_logic="all", threshold=0.0,
│       size_constraint="none", auto_contrast=True
│
├── series_styles: list[SeriesStyleConfig]  (series_style_config.py:16)
│       @dataclass(frozen=True)
│       line_width=2.0, marker_size=6, opacity=1.0,
│       bar_border_width=0.0, bar_border_color="",
│       hatching_pattern="", color="", symbol="", display_name=""
│
├── trace_overrides: dict[str, SeriesStyleConfig]
│       Keyed by trace name for per-trace styling
│
├── color_palette: list[str]  (Wong default: 8 hex colors)
├── barmode: "group" | "stack" | "overlay" | "relative"
├── hatching_sequence: list[str]  (["/", "\\", "|", "-", "+", "x", "o", "O"])
├── reference_lines: list[ReferenceLineConfig]  (annotation_config.py:65)
│       enabled, axis="y", value=0.0, color="red",
│       width=1.5, style="dash", label=""
│
├── hovermode: str = "x unified"
├── enable_stripes: bool = False
├── show_error_bars: bool = False
├── title: str = ""
├── paper_bgcolor: str = "white"
├── plot_bgcolor: str = "white"
├── font_family: str = "serif"
├── latex_extra_preamble: str = ""
└── metadata: dict[str, str] = {}
```

**Total config classes**: 12 distinct dataclasses compose the tree.
**Total fields** (including nested): approximately 160+ individual settings.

---

## 3. Sentinel Value System

### 3.1 Sentinel Constants

The system defines sentinel values in two locations:

| Constant | Value | Defined In | Used For |
|----------|-------|------------|----------|
| `SENTINEL_INT` | `-1` | `config_resolver.py:57` | Integer fields (font sizes, ncol) |
| `SENTINEL_FLOAT` | `-1.0` | `config_resolver.py:58` | Float fields (positions, spacing) |
| `INHERIT` | `-1` | `typography_config.py:18` | Alias for SENTINEL_INT within typography |
| `INHERIT_F` | `-1.0` | `typography_config.py:19`, `axis_config.py:18`, `legend_config.py:19` | Alias for SENTINEL_FLOAT within various modules |

**Semantic meaning**: A sentinel value means "inherit this value from the
nearest parent in the resolution chain." The value `-1` was chosen because all
config fields are non-negative in valid configurations (font sizes, positions,
spacing are all >= 0).

### 3.2 Inheritance Chains

Three independent inheritance chains are resolved by `resolve_config()`:

#### Typography Chain (`_resolve_typography`)

```
font_size_base (root: 10pt)
├── font_size_title (10)         ← explicit, not inherited
├── font_size_xlabel (9)         ← explicit
├── font_size_ylabel (9)         ← explicit
│   └── font_size_y2label       ← INHERIT (-1) → resolves to ylabel value
├── font_size_ticks (7)          ← explicit (X-axis ticks)
│   ├── font_size_yticks (7)     ← explicit (but could be -1 → ticks)
│   │   └── font_size_y2ticks   ← INHERIT (-1) → resolves to yticks value
│   (NOTE: y2ticks inherits from yticks, which inherits from ticks)
├── font_size_annotations (6)    ← explicit
└── font_size_legend (8)         ← explicit (primary)
    ├── font_size_legend2        ← INHERIT (-1) → resolves to legend value
    └── font_size_legend3        ← INHERIT (-1) → resolves to legend value
        ├── legend3_number_fontsize  ← INHERIT (-1) → resolves to legend3
        └── legend3_text_fontsize    ← INHERIT (-1) → resolves to legend3
```

**Resolution order matters**: y2ticks depends on yticks, which depends on
ticks. The resolver processes `ticks → yticks → y2ticks` top-down.

#### Legend Chain (`_resolve_legends`)

```
legends[0] (primary)
│   font_size = 8
│   title_font_size = -1 → resolves to own font_size
│   number_fontsize = -1 → resolves to own font_size
│   text_fontsize = -1 → resolves to own font_size
│   spacing = LegendSpacingConfig(columnspacing=0.5, ...)
│
├── legends[1] (secondary)
│   font_size = -1 → resolves to primary.font_size
│   title_font_size = -1 → resolves to own font_size (after resolution)
│   number_fontsize = -1 → resolves to own font_size
│   text_fontsize = -1 → resolves to own font_size
│   spacing.* = -1.0 → each field resolves to primary.spacing.*
│
└── legends[2] (tertiary)
    font_size = -1 → resolves to primary.font_size
    title_font_size = -1 → resolves to own font_size
    number_fontsize = -1 → resolves to own font_size
    text_fontsize = -1 → resolves to own font_size
    spacing.* = -1.0 → each field resolves to primary.spacing.*
```

Legend spacing resolution iterates over all `dataclass.fields()` of
`LegendSpacingConfig` and replaces any `-1.0` with the primary's
corresponding value (generic, field-agnostic loop).

#### Axes Chain (`_resolve_axes`)

```
axes.y (primary Y-axis)
│   label_pad = 10.0
│   tick_pad = 5.0
│
└── axes.y2 (secondary Y-axis, if not None)
    label_pad = -1.0 → resolves to y.label_pad
    tick_pad = -1.0 → resolves to y.tick_pad
```

Only two fields (`label_pad`, `tick_pad`) participate in y2 inheritance.
If `axes.y2 is None`, the axis resolution is a no-op.

### 3.3 `resolve_config()` Algorithm

```
File: src/core/services/visualization/config_resolver.py:60

def resolve_config(spec: FigureConfig) -> FigureConfig:
    1. resolved = deepcopy(spec)        # PURE — never mutates input
    2. _resolve_typography(resolved.typography)   # in-place on the copy
    3. _resolve_legends(resolved.legends)         # in-place on the copy
    4. _resolve_axes(resolved.axes)               # in-place on the copy
    5. return resolved                            # all sentinels replaced
```

**Key properties**:

- **Pure function**: Input is never mutated; returns a deep copy.
- **Single pass**: All three chains are resolved sequentially in ONE call.
- **Idempotent**: Running `resolve_config()` on an already-resolved config is
  a no-op (no field will be `-1`).
- **Fail-safe**: If a sub-config type check fails (e.g., `isinstance` returns
  False), that chain is silently skipped.

The helper functions `_resolve_int(value, parent)` and
`_resolve_float(value, parent)` are the atomic operations: if `value ==
SENTINEL`, return `parent`, else return `value`.

---

## 4. ConfigSpecBuilder Pipeline

### 4.1 Three Builder Classes

The system provides three distinct paths from source data to `FigureConfig`:

```
┌──────────────────────────────────────────────────────────────┐
│  Source                   Builder Class              Result  │
│  ────────                 ─────────────              ──────  │
│  UI widget config dict →  ConfigSpecBuilder      →  FigureConfig  │
│  Plotly go.Figure      →  PlotlyFigureSpecBuilder →  FigureConfig  │
│  Preset dict (LaTeX)   →  PresetSpecBuilder       →  FigureConfig  │
└──────────────────────────────────────────────────────────────┘
```

All three live in `src/web/rendering/config_builder.py`.

### 4.2 ConfigSpecBuilder.from_config() — The Primary Path

This is the **main production path**. UI widgets produce a flat
`Dict[str, Any]` config dict, and `ConfigSpecBuilder.from_config()` maps it
to a typed `FigureConfig`.

**Signature**:
```python
@staticmethod
def from_config(config: dict[str, Any], plot_type: str = "") -> FigureConfig
```

**Key design decision**: `dpi` is set to `1` so that pixel values from the UI
round-trip without conversion: `width=800px / dpi=1 = 800 inches-in-name-only`,
then `800 * 1 = 800px` when the connector multiplies by dpi. This avoids
floating-point drift.

**Build sequence** (line-by-line through the method):

1. **Dimensions** (lines 379-394):
   - `MarginsConfig` from `margin_t`, `margin_b`, `margin_l`, `margin_r`, `margin_pad`
   - `DimensionConfig` with `dpi=1`, width/height in effective pixels
   - Conditional `bargap`/`bargroupgap` based on `plot_type` containing "bar"

2. **Typography** (lines 397-405):
   - Maps UI keys (`title_font_size`, `xaxis_title_font_size`, etc.) to
     `TypographyConfig` fields
   - Only sets explicit fields; secondary Y / legend2 / legend3 use defaults (-1)

3. **Axes** (lines 408-482):
   - X-axis: label, tick_angle, range, category_order, label_aliases, grid,
     tick visibility, tick_dash, tick colors, axis lines
   - Numbered x-axis mode handling: `numbered_xaxis_modes` multiselect controls
     tick visibility and rotation
   - Y-axis: label, tick_angle, range, dtick, standoff, title_vshift, grid
   - `AxesConfig`: wraps x + y + group_label settings + opposite axis lines

4. **Legends** (lines 484-494):
   - Primary legend always created via `_build_legend_from_config(config, "legend_", "primary")`
   - Secondary legend conditionally added if any `legend2_*` keys are non-None
   - Tertiary legend conditionally added if any `legend3_*` keys are non-None
   - `_build_legend_from_config()` is a 95-line helper that:
     - Converts `tracegroupgap` (px) to `labelspacing` (font-size multiples)
     - Converts `itemwidth` (px) to `handlelength` (font-size multiples)
     - Auto-derives anchor from position via `LegendConfig.derive_anchors()`
     - Builds `LegendSpacingConfig`, `ColorbarConfig`, and `LegendConfig`

5. **Backgrounds, Title** (lines 496-501)

6. **Data Labels** (lines 503-549):
   - Only built when `config["show_values"]` is truthy
   - Validates and normalizes `color_mode`, `position`, `anchor`,
     `size_constraint` literals
   - Creates a frozen `DataLabelConfig`

7. **Reference Lines** (lines 551-563):
   - Single reference line from `reference_line_enabled` + settings

8. **Series Styles and Trace Overrides** (lines 565-594):
   - Global `SeriesStyleConfig` from `bar_border_width`, `marker_size`, `line_width`
   - Per-trace `trace_overrides` dict from `config["series_styles"]`

9. **Color Palette** (line 597):
   - Calls `resolve_palette(config.get("color_palette"))` — name to hex list

10. **Feature Flags and Barmode** (lines 599-610)

11. **Assembly** (lines 612-629):
    - All sub-objects composed into final `FigureConfig`

### 4.3 PlotlyFigureSpecBuilder.from_plotly()

Extracts a `FigureConfig` from an existing `go.Figure` + config dict.
Used for **reverse-engineering** the spec from a Plotly figure (e.g., for
portfolio save after interactive edits).

Also provides `enrich_from_plotly(spec, fig)` which merges computed layout
data (tick positions, barmode, legend3 items) into an existing spec.

### 4.4 PresetSpecBuilder.from_preset()

Builds a `FigureConfig` from a `LaTeXPreset` dictionary. Used as the
intermediate step in preset application (see Section 5).

**Mapping highlights**:
- `width_inches` → `DimensionConfig.width`
- `font_size_*` → `TypographyConfig.font_size_*`
- `bold_*` → `TypographyConfig.bold_*`
- `legend_*` → `LegendSpacingConfig` fields
- `legend2_*` → secondary `LegendConfig` with sentinel spacing
- `legend3_*` → tertiary `LegendConfig` with sentinel spacing
- `xtick_*` → `AxisConfig` x-axis fields
- `ylabel_*` → `AxisConfig` y-axis fields
- `group_*` → `AxesConfig` group label fields + `SeparatorConfig`

---

## 5. Preset System

### 5.1 Architecture

```
latex_presets.json  ──→  PresetManager.load_preset("name")
                         │  (validates, caches, returns LaTeXPreset)
                         ▼
LaTeXPreset dict    ──→  PresetApplicator.apply(config_spec, preset_dict)
                         │  1. PresetSpecBuilder.from_preset(preset_dict)
                         │  2. dataclasses.replace(spec, **overrides)
                         ▼
FigureConfig (merged)
```

### 5.2 Preset Catalog (13 Presets)

Source: `src/web/pages/ui/plotting/export/presets/latex_presets.json`

| # | Preset Name | Description | Width | Height | Font Family | Base Font | DPI |
|---|-------------|-------------|-------|--------|-------------|-----------|-----|
| 1 | `single_column` | Standard IEEE/ACM single column | 3.5" | 1.97" | serif | 10pt | 300 |
| 2 | `double_column` | Full width for two-column papers | 7.0" | 5.25" | serif | 10pt | 300 |
| 3 | `micro` | MICRO conference style | 3.5" | 2.5" | serif | 10pt | 300 |
| 4 | `isca` | ISCA conference style | 3.5" | 2.5" | serif | 10pt | 300 |
| 5 | `asplos` | ASPLOS conference style | 3.5" | 2.5" | serif | 10pt | 300 |
| 6 | `hpca` | HPCA conference style | 3.5" | 2.5" | serif | 10pt | 300 |
| 7 | `taco` | ACM TACO journal style | 3.5" | 2.5" | serif | 10pt | 300 |
| 8 | `nature` | Nature journal style | 3.5" | 3.5" | Arial | 7pt | 600 |
| 9 | `science` | Science journal style | 3.5" | 2.5" | sans-serif | 8pt | 600 |
| 10 | `ieee_single` | IEEE transactions style | 3.5" | 2.5" | serif | 10pt | 300 |
| 11 | `acm` | ACM proceedings style | 3.5" | 2.5" | serif | 9pt | 300 |
| 12 | `poster` | Poster style (large) | 10.0" | 7.0" | sans-serif | 24pt | 150 |
| 13 | `slides` | Presentation slides style | 8.0" | 4.5" | sans-serif | 18pt | 150 |

**Observations**:
- Computer architecture conferences (micro, isca, asplos, hpca) share identical
  settings (3.5" x 2.5", serif, 10pt, 300dpi).
- Nature and Science have distinct requirements: smaller fonts (7-8pt), thinner
  lines (0.5pt), higher DPI (600).
- Poster and slides presets use much larger fonts and dimensions for readability.
- 8 of the 13 presets include `latex_extra_preamble: "\\usepackage[varqu,scaled=0.95]{zi4}"`
  for monospace font matching in LaTeX documents.

### 5.3 PresetManager

**File**: `src/web/pages/ui/plotting/export/presets/preset_manager.py`

- **Singleton-like class** with class-level `_cache`, `_presets_data`, `_initialized`.
- Lazy initialization: `_initialize()` loads `latex_presets.json` once on first access.
- `load_preset(name)`: Extracts `LaTeXPreset` fields from raw JSON, validates,
  caches, returns. Unknown keys (like `description`, `typical_use`) are stripped.
- `list_presets()`: Returns all available preset names.
- `get_preset_info(name)`: Returns metadata (description, typical_use) without
  loading full config.
- `validate_preset(preset)`: Checks required fields exist and all dimension /
  font size / DPI values are positive.

### 5.4 PresetApplicator

**File**: `src/web/rendering/preset_applicator.py`

Two application modes:

#### `apply(spec, preset_info)` — Full Overlay
Replaces ALL presentation-layer fields from the preset:
```
OVERRIDDEN by preset:           KEPT from config spec:
  dimensions                      traces
  typography                      annotations
  axes                            data_labels
  legends                         series_styles
  separator                       trace_overrides
  font_family                     color_palette
  latex_extra_preamble            hatching_sequence
                                  reference_lines
                                  hovermode, enable_stripes
                                  show_error_bars, title
                                  paper_bgcolor, plot_bgcolor
                                  metadata
```

Uses `dataclasses.replace()` for immutable composition — returns a **new**
`FigureConfig` without mutating the input.

#### `apply_partial(spec, preset_info)` — Selective Overlay
Only overrides field groups whose preset keys are actually present. Groups are
defined by key-set intersection:
- `_DIMENSION_KEYS` (4 keys) → `dimensions`
- `_TYPO_KEYS` (24 keys) → `typography`
- `_AXES_KEYS` (11 keys) → `axes`
- `_LEGEND_KEYS` (20 keys) → `legends`
- `_SEPARATOR_KEYS` (3 keys) → `separator`
- `font_family`, `latex_extra_preamble` individually

### 5.5 LaTeXPreset TypedDict Schema

**File**: `src/web/pages/ui/plotting/export/presets/preset_schema.py`

`LaTeXPreset` is a `TypedDict(total=False)` with 60+ optional fields organized
into groups:
- Physical dimensions (2 fields)
- Font family + base size (2 fields)
- Per-element font sizes (12 fields)
- Bold flags (10 fields)
- Line / marker / DPI (3 fields)
- Legend spacing (7 primary + 7 secondary + 4 tertiary = 18 fields)
- Positioning parameters (9 fields)
- Axis / bar spacing (6 fields)
- Legend position (3 fields)
- Separator (3 fields)
- LaTeX preamble (1 field)

---

## 6. Palette Registry & Resolution

### 6.1 Registry Structure

**File**: `src/core/models/visualization/palettes.py`

The `PALETTE_REGISTRY` is a flat `dict[str, list[str]]` combining two internal
dictionaries at module load time:

```python
PALETTE_REGISTRY = {**_COLORBLIND_PALETTES, **_PLOTLY_PALETTES}
```

**Ordering** is maintained in `_PALETTE_ORDER`: colorblind-safe names first,
then Plotly names sorted alphabetically. This ordering is exposed to the UI
for dropdown population.

### 6.2 Colorblind-Safe Palettes (5)

| Palette | Colors | Source |
|---------|--------|--------|
| `wong` | 8 | Wong (2011) — THE default for all new figures |
| `okabe_ito` | 8 | Okabe & Ito (same colors as Wong, different order; black last) |
| `tol_bright` | 7 | Paul Tol's bright scheme |
| `viridis_8` | 8 | 8-color discrete sampling of the Viridis colormap |
| `seaborn_cb` | 8 | Seaborn's colorblind palette |

### 6.3 Plotly Qualitative Palettes (13)

Listed as pre-resolved hex lists (no runtime dependency on Plotly's color
module):

| Palette | Colors | Source |
|---------|--------|--------|
| `Plotly` | 10 | Default Plotly qualitative |
| `D3` | 10 | D3.js category10 |
| `G10` | 10 | Google 10 |
| `T10` | 10 | Tableau 10 |
| `Alphabet` | 26 | Color Brewer Alphabet |
| `Dark24` | 24 | Dark qualitative |
| `Light24` | 24 | Light qualitative |
| `Set1` | 9 | Color Brewer Set1 |
| `Set2` | 8 | Color Brewer Set2 |
| `Set3` | 12 | Color Brewer Set3 |
| `Pastel` | 11 | Pastel qualitative |
| `Safe` | 11 | Color Brewer Safe |
| `Vivid` | 11 | Carto Vivid |
| `Bold` | 11 | Carto Bold |

**Total**: 18 palettes (5 + 13) in the registry.

### 6.4 Palette Resolution Logic

**File**: `src/core/services/visualization/palette_service.py`

```python
def resolve_palette(name: object) -> list[str]:
    """
    Resolution order:
    1. If name is None/empty/not-string → return Wong palette (copy)
    2. Exact match in PALETTE_REGISTRY → return copy
    3. Case-insensitive match → return copy
    4. No match → return Wong palette (copy)
    """
```

**Key properties**:
- Always returns a **copy** (safe to mutate).
- Fallback is always Wong (colorblind-safe).
- Case-insensitive matching enables user-friendly palette names.

```python
def get_palette_names() -> list[str]:
    # Returns _PALETTE_ORDER: colorblind-safe first, then Plotly alphabetical

def is_colorblind_safe(name: str) -> bool:
    # Checks membership in _COLORBLIND_PALETTES dict
```

### 6.5 Backward-Compatibility Shims

Both `palettes.py` and `resolvers.py` in the models layer re-export service-layer
functions for backward compatibility:

- `palettes.py` re-exports `resolve_palette`, `get_palette_names`, `is_colorblind_safe`
  from `palette_service.py`
- `resolvers.py` re-exports `resolve_config`, `SENTINEL_INT`, `SENTINEL_FLOAT`
  from `config_resolver.py`

Both are marked for removal in Phase 10 (Dead Code Removal).

---

## 7. Serialization Protocol

### 7.1 Overview

All config dataclasses follow a consistent serialization pattern for JSON
persistence (portfolio save/load):

| Method | Direction | Strategy |
|--------|-----------|----------|
| `to_dict() → dict` | Object → JSON | Recursive dict conversion |
| `from_dict(data) → Self` | JSON → Object | Constructor with field filtering |

### 7.2 `to_dict()` Implementations

Three strategies are used across the codebase:

**Strategy A — `dataclasses.asdict()` (FigureConfig)**:
```python
# FigureConfig.to_dict()
def to_dict(self) -> dict[str, Any]:
    from dataclasses import asdict
    return asdict(self)
```
Full recursive conversion of the entire tree. Relies on stdlib `asdict()` which
handles nested dataclasses, lists, and dicts automatically.

**Strategy B — Explicit field enumeration (most sub-configs)**:
```python
# MarginsConfig.to_dict(), ColorbarConfig.to_dict(), LegendConfig.to_dict(),
# DataLabelConfig.to_dict(), SeriesStyleConfig.to_dict()
def to_dict(self):
    return {"field1": self.field1, "field2": self.field2, ...}
```
Hand-written dicts. More verbose but guaranteed to only include known fields.
Used by configs that need control over serialization (e.g., `LegendConfig` calls
`self.spacing.to_dict()` and `self.colorbar.to_dict()` explicitly).

**Strategy C — `asdict()` on individual config (AxisConfig)**:
```python
# AxisConfig.to_dict()
def to_dict(self):
    from dataclasses import asdict
    return asdict(self)
```
Same as Strategy A but on a leaf config.

### 7.3 `from_dict()` Implementations

Two patterns:

**Pattern A — `__dataclass_fields__` filtering (AxisConfig, LegendSpacingConfig, ColorbarConfig)**:
```python
@classmethod
def from_dict(cls, data):
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```
Filters out unknown keys using the dataclass introspection attribute.
Clean and generic but does not validate types.

**Pattern B — Explicit field extraction with defaults (DataLabelConfig, SeriesStyleConfig, FigureConfig)**:
```python
@classmethod
def from_dict(cls, data):
    return cls(
        field1=type_cast(data.get("field1", default)),
        field2=type_cast(data.get("field2", default)),
        ...
    )
```
Explicit control over each field with type coercion (`bool()`, `int()`,
`float()`, `str()`). More robust against malformed input.

### 7.4 FigureConfig.from_dict() — The Master Deserializer

The most complex deserializer, handling all nested objects:

1. **Dimensions**: Pops `margins` from `dims_data`, builds `MarginsConfig`,
   then `DimensionConfig`.
2. **Typography**: Direct `TypographyConfig(**typo_data)`.
3. **Axes**: Delegates to `AxesConfig.from_dict()` which recursively calls
   `AxisConfig.from_dict()` for x, y, y2.
4. **Legends**: Maps list of dicts through `LegendConfig.from_dict()`.
5. **Annotations**: Direct `AnnotationConfig(**ad)` for each entry.
6. **Separator**: Direct `SeparatorConfig(**sep_data)`.
7. **Data labels**: `DataLabelConfig.from_dict()` if dict, else `None`.
8. **Series styles**: `SeriesStyleConfig.from_dict()` for each dict entry.
9. **Trace overrides**: Dict comprehension mapping names to `SeriesStyleConfig.from_dict()`.
10. **Reference lines**: `ReferenceLineConfig(**rd)` for each dict entry.
11. **Scalars**: Direct `.get()` with defaults for palette, hatching, hovermode,
    flags, title, colors, font_family, preamble, metadata.

**Note**: `traces` are passed through as-is (`data.get("traces", [])`) — they
are typically not serialized as config objects but as raw dicts representing
Plotly trace data.

### 7.5 Round-Trip Guarantee

The docstring claims: `FigureConfig.from_dict(spec.to_dict()) == spec`.
This works because:
- `to_dict()` uses `dataclasses.asdict()` which recursively converts all nested
  dataclasses to plain dicts.
- `from_dict()` rebuilds all nested objects from those dicts.
- All fields have defaults matching their serialized representation.

### 7.6 Immutability Notes

| Config | Frozen? | Impact |
|--------|---------|--------|
| `DataLabelConfig` | Yes (`frozen=True`) | Cannot be mutated after creation |
| `SeriesStyleConfig` | Yes (`frozen=True`) | Cannot be mutated after creation |
| All others | No (mutable) | Can be mutated by `resolve_config()` |

The resolver relies on mutability — it modifies the deep-copied config in-place.
Frozen configs (`DataLabelConfig`, `SeriesStyleConfig`) are not subject to
sentinel resolution (they have no sentinel fields).

---

## 8. TraceConfig Hierarchy (Deep Dive)

### 8.1 Base Class

**File**: `src/core/models/visualization/trace_config.py:20`

```python
@dataclass
class TraceConfig:
    name: str = ""
    trace_type: Literal["bar", "line", "scatter", "histogram", "heatmap"] = "bar"
    x: list[str | int | float] = field(default_factory=list)
    y: list[int | float] = field(default_factory=list)
    yaxis: Literal["y", "y2"] = "y"
    color: str = ""
    opacity: float = 1.0
    visible: bool = True
    show_in_legend: bool = True
    legendgroup: str = ""
    custom_data: dict[str, Any] = field(default_factory=dict)
```

`TraceConfig` uses **dataclass inheritance** (not protocol/ABC). The `trace_type`
field acts as a discriminator for subclass dispatch in connectors.

### 8.2 Subclass Details

| Subclass | trace_type | Extra Fields | Unique Purpose |
|----------|------------|--------------|----------------|
| `BarTraceConfig` | `"bar"` | `x_positions`, `bar_width`, `offset`, `pattern`, `border_width`, `border_color`, `text_values`, `text_position`, `text_angle`, `text_font_size`, `error_y` | Pre-computed bar positioning; hatch patterns |
| `LineTraceConfig` | `"line"` | `line_width`, `line_dash`, `marker_symbol`, `marker_size`, `show_markers`, `fill`, `error_y` | Line style, fill areas, marker toggling |
| `ScatterTraceConfig` | `"scatter"` | `marker_symbol`, `marker_size`, `marker_line_width`, `marker_line_color`, `colorscale`, `size_values`, `error_y` | Bubble charts, continuous color mapping |
| `HistogramTraceConfig` | `"histogram"` | `nbins`, `normalization`, `cumulative` | Engine-side binning (rare path) |
| `HeatmapTraceConfig` | `"heatmap"` | `col_labels`, `row_labels`, `z`, `colorscale`, `show_values`, `text`, `text_font_size`, `text_color_mode`, `text_color`, `totals_position`, `totals_count` | 2D data matrices, cell annotations |

### 8.3 Key Design: Pre-Computed Bar Positioning

`BarTraceConfig` carries `x_positions`, `bar_width`, and `offset` — the
exact pixel/data coordinates where each bar should be placed. This means:

- The **plot type** (e.g., `GroupedBarPlot`) computes all grouping math.
- The **matplotlib connector** does NOT need to reimplement bar grouping —
  it receives ready-to-plot coordinates.
- The **Plotly connector** can use these or let Plotly's native grouping
  override them.

### 8.4 Plot Type to TraceConfig Mapping

| Plot Type | TraceConfig Subclass(es) |
|-----------|--------------------------|
| `bar_plot.py` | `BarTraceConfig` |
| `grouped_bar_plot.py` | `BarTraceConfig` (multiple, with offsets) |
| `stacked_bar_plot.py` | `BarTraceConfig` (multiple, same x_positions) |
| `grouped_stacked_bar_plot.py` | `BarTraceConfig` |
| `line_plot.py` | `LineTraceConfig` |
| `scatter_plot.py` | `ScatterTraceConfig` |
| `histogram_plot.py` | `HistogramTraceConfig` or `BarTraceConfig` (pre-binned) |
| `heatmap_plot.py` | `HeatmapTraceConfig` |
| `dual_axis_bar_dot_plot.py` | `BarTraceConfig` + `ScatterTraceConfig` (yaxis="y2") |

### 8.5 TraceBuildResult

**File**: `src/core/models/visualization/trace_build_result.py:22`

`TraceBuildResult` is the **output** of every plot type's `create_traces()`
method. It bundles:

| Field | Type | Purpose |
|-------|------|---------|
| `traces` | `Sequence[TraceConfig]` | The actual trace configs |
| `annotations` | `list[AnnotationConfig]` | Group labels, tertiary legend items |
| `layout_annotations` | `list[dict[str, Any]]` | Raw Plotly annotation dicts |
| `shapes` | `list[ShapeConfig]` | Separator lines, shading rectangles |
| `barmode` | `str` | Bar grouping mode |
| `custom_x_ticks` | `dict | None` | Custom tick positions/labels |
| `secondary_y` | `bool` | Whether Y2 axis is used |

This is distinct from `TraceConfig` — it is a **container** that packages
traces with their layout-level metadata. The downstream connector processes
the `TraceBuildResult` to:
1. Render each `TraceConfig` as engine-specific trace objects.
2. Apply annotations, shapes, and tick overrides to the layout.
3. Configure barmode and secondary Y axis.

---

## 9. Config Lifecycle

The complete lifecycle of a `FigureConfig` through the system:

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: CREATION                                              │
│                                                                 │
│  UI Widgets (settings pills, sliders, dropdowns)                │
│       │                                                         │
│       ▼                                                         │
│  Dict[str, Any] config                                          │
│       │                                                         │
│       ▼                                                         │
│  ConfigSpecBuilder.from_config(config, plot_type)               │
│       │                                                         │
│       ▼                                                         │
│  FigureConfig (may contain -1 sentinels)                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 2: MODIFICATION (optional)                               │
│                                                                 │
│  ┌──────────────────────────────────────────┐                   │
│  │ Export path only:                        │                   │
│  │   PresetManager.load_preset("nature")    │                   │
│  │       ▼                                  │                   │
│  │   PresetApplicator.apply(spec, preset)   │                   │
│  │       ▼                                  │                   │
│  │   FigureConfig (preset overrides merged) │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                 │
│  ┌──────────────────────────────────────────┐                   │
│  │ Plotly enrichment (interactive):         │                   │
│  │   PlotlyFigureSpecBuilder.enrich_from_   │                   │
│  │     plotly(spec, fig)                    │                   │
│  │       ▼                                  │                   │
│  │   FigureConfig (tick data merged)        │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 3: RESOLUTION                                            │
│                                                                 │
│  resolve_config(spec)                                           │
│       │  deepcopy + resolve typography + legends + axes         │
│       ▼                                                         │
│  FigureConfig (all sentinels replaced with concrete values)     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 4: RENDERING                                             │
│                                                                 │
│  ┌───────────────────────────┬───────────────────────────┐      │
│  │ Plotly Path               │ Matplotlib Path            │     │
│  │                           │                            │     │
│  │ FigureSpecToPlotly        │ FigureSpecToMatplotlib     │     │
│  │   .apply(fig, spec)       │   .apply(fig, spec)        │     │
│  │       ▼                   │       ▼                    │     │
│  │ go.Figure (styled)        │ matplotlib Figure (styled) │     │
│  └───────────────────────────┴───────────────────────────┘      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 5: SERIALIZATION (portfolio save)                        │
│                                                                 │
│  spec.to_dict()  →  JSON  →  portfolio file                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 6: RESTORATION (portfolio load)                          │
│                                                                 │
│  portfolio file  →  JSON  →  FigureConfig.from_dict(data)      │
│       ▼                                                         │
│  FigureConfig (reconstructed, may need re-resolution)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.1 Trace Data Flow (Parallel to Config)

While `FigureConfig` carries layout/style settings, trace data follows a
parallel path:

```
BasePlot.create_traces(data, config)
    │
    ▼
TraceBuildResult
    │  .traces = [TraceConfig, ...]
    │  .annotations = [AnnotationConfig, ...]
    │  .shapes = [ShapeConfig, ...]
    │
    ▼
┌───────────────────────────┬───────────────────────────┐
│ Plotly Connector           │ Matplotlib Connector       │
│  trace_to_plotly()         │  MatplotlibTraceRenderer   │
│    TraceConfig → go.Bar    │    TraceConfig → ax.bar()  │
│    TraceConfig → go.Scatter│    TraceConfig → ax.plot() │
└───────────────────────────┴───────────────────────────┘
```

The merge point is in the connector: `FigureConfig` (layout) and
`TraceBuildResult` (data) are both consumed by the same connector to
produce the final rendered figure.

---

## 10. Downstream Dependencies

### 10.1 Direct Consumers of FigureConfig

| Consumer | File | How It Uses FigureConfig |
|----------|------|--------------------------|
| `FigureSpecToPlotly` | `src/web/rendering/plotly_connector.py` | Reads all fields to configure Plotly layout |
| `FigureSpecToMatplotlib` | `src/web/rendering/matplotlib_connector.py` | Reads all fields to configure matplotlib figure |
| `MatplotlibTraceRenderer` | `src/web/rendering/matplotlib_trace_renderer.py` | Reads TraceConfig subclasses to create artists |
| `PresetApplicator` | `src/web/rendering/preset_applicator.py` | Merges preset onto existing FigureConfig |
| `PlotlyFigureSpecBuilder` | `src/web/rendering/config_builder.py` | Enriches FigureConfig from Plotly figure |
| `resolve_config` | `src/core/services/visualization/config_resolver.py` | Resolves all sentinel values |
| `styles/applicator.py` | `src/web/pages/ui/plotting/styles/applicator.py` | Applies style settings |
| Portfolio save/load | via `to_dict()` / `from_dict()` | JSON persistence |

### 10.2 Direct Consumers of TraceConfig Subclasses

| Consumer | Consumes |
|----------|----------|
| 9 plot types in `src/web/pages/ui/plotting/types/` | Produce `TraceConfig` subclasses |
| `FigureSpecToPlotly` / `trace_to_plotly.py` | Translate `TraceConfig` to Plotly traces |
| `MatplotlibTraceRenderer` | Translate `TraceConfig` to matplotlib artists |

### 10.3 Direct Consumers of Palette System

| Consumer | Usage |
|----------|-------|
| `ConfigSpecBuilder.from_config()` | Calls `resolve_palette()` to convert name → hex list |
| UI palette dropdown | Calls `get_palette_names()` for available options |
| UI palette indicator | Calls `is_colorblind_safe()` for accessibility badge |
| `FigureConfig.color_palette` | Stores the resolved hex list |

### 10.4 Analysis Feeds Into

| Downstream Document | Sections Used |
|---------------------|---------------|
| Step 10 (Plotting System) | TraceConfig hierarchy, TraceBuildResult pipeline |
| Step 11 (Rendering Engines) | FigureConfig consumption by connectors |
| Step 12 (Settings Pills) | ConfigSpecBuilder config key mapping |
| Step 18 (Data Flow) | Config lifecycle phases 1-4 |
| Developer Guide: adding-a-new-plot | TraceConfig subclass creation, TraceBuildResult contract |
| Developer Guide: config-models | Full config hierarchy documentation |
| AI Knowledge Base: visualization-pipeline | Complete lifecycle diagram |

---

## Appendix A: File Index

| File | Classes/Functions | Lines |
|------|-------------------|-------|
| `src/core/models/visualization/__init__.py` | Re-exports 20+ symbols | 83 |
| `src/core/models/visualization/figure_config.py` | `MarginsConfig`, `DimensionConfig`, `SeparatorConfig`, `FigureConfig` | 301 |
| `src/core/models/visualization/trace_config.py` | `TraceConfig`, `BarTraceConfig`, `LineTraceConfig`, `ScatterTraceConfig`, `HistogramTraceConfig`, `HeatmapTraceConfig` | 151 |
| `src/core/models/visualization/axis_config.py` | `AxisConfig`, `AxesConfig` | 141 |
| `src/core/models/visualization/legend_config.py` | `ColorbarConfig`, `LegendSpacingConfig`, `LegendConfig` | 239 |
| `src/core/models/visualization/typography_config.py` | `TypographyConfig` | 72 |
| `src/core/models/visualization/annotation_config.py` | `AnnotationConfig`, `ReferenceLineConfig` | 78 |
| `src/core/models/visualization/data_label_config.py` | `DataLabelConfig` | 100 |
| `src/core/models/visualization/series_style_config.py` | `SeriesStyleConfig` | 81 |
| `src/core/models/visualization/trace_build_result.py` | `TraceBuildResult` | 44 |
| `src/core/models/visualization/palettes.py` | `PALETTE_REGISTRY`, `_COLORBLIND_PALETTES`, `_PLOTLY_PALETTES`, `_PALETTE_ORDER` | 323 |
| `src/core/models/visualization/resolvers.py` | Backward-compat shim | 13 |
| `src/core/services/visualization/config_resolver.py` | `resolve_config`, `SENTINEL_INT`, `SENTINEL_FLOAT` | 185 |
| `src/core/services/visualization/palette_service.py` | `resolve_palette`, `get_palette_names`, `is_colorblind_safe` | 78 |
| `src/web/rendering/config_builder.py` | `PlotlyFigureSpecBuilder`, `PresetSpecBuilder`, `ConfigSpecBuilder` | 926 |
| `src/web/rendering/preset_applicator.py` | `PresetApplicator` | 194 |
| `src/web/pages/ui/plotting/export/presets/preset_manager.py` | `PresetManager` | 283 |
| `src/web/pages/ui/plotting/export/presets/preset_schema.py` | `LaTeXPreset`, `ExportResult` | 159 |
| `src/web/pages/ui/plotting/export/presets/latex_presets.json` | 13 preset definitions | 273 |

## Appendix B: Complete Field Inventory

### FigureConfig Fields (21 direct fields)

| Field | Type | Default | Mutable | Sentinel |
|-------|------|---------|---------|----------|
| `dimensions` | `DimensionConfig` | factory | Yes | No |
| `typography` | `TypographyConfig` | `None` → post_init | Yes | Contains sentinels |
| `axes` | `AxesConfig` | `None` → post_init | Yes | Contains sentinels |
| `legends` | `list[LegendConfig]` | `[]` | Yes | Contains sentinels |
| `traces` | `list[TraceConfig]` | `[]` | Yes | No |
| `annotations` | `list[AnnotationConfig]` | `[]` | Yes | No |
| `separator` | `SeparatorConfig` | factory | Yes | No |
| `data_labels` | `DataLabelConfig \| None` | `None` | Yes | No |
| `series_styles` | `list[SeriesStyleConfig]` | `[]` | Yes | No |
| `trace_overrides` | `dict[str, SeriesStyleConfig]` | `{}` | Yes | No |
| `color_palette` | `list[str]` | Wong 8 colors | Yes | No |
| `barmode` | `Literal[...]` | `"group"` | Yes | No |
| `hatching_sequence` | `list[str]` | 8 patterns | Yes | No |
| `reference_lines` | `list[ReferenceLineConfig]` | `[]` | Yes | No |
| `hovermode` | `str` | `"x unified"` | Yes | No |
| `enable_stripes` | `bool` | `False` | Yes | No |
| `show_error_bars` | `bool` | `False` | Yes | No |
| `title` | `str` | `""` | Yes | No |
| `paper_bgcolor` | `str` | `"white"` | Yes | No |
| `plot_bgcolor` | `str` | `"white"` | Yes | No |
| `font_family` | `str` | `"serif"` | Yes | No |
| `latex_extra_preamble` | `str` | `""` | Yes | No |
| `metadata` | `dict[str, str]` | `{}` | Yes | No |

### TypographyConfig Fields with Sentinel Behavior (13 font sizes + 10 bolds)

| Field | Default | Inherits From |
|-------|---------|---------------|
| `font_size_base` | 10 | root (no parent) |
| `font_size_title` | 10 | explicit |
| `font_size_xlabel` | 9 | explicit |
| `font_size_ylabel` | 9 | explicit |
| `font_size_y2label` | -1 | ylabel |
| `font_size_ticks` | 7 | explicit |
| `font_size_yticks` | 7 | explicit |
| `font_size_y2ticks` | -1 | yticks |
| `font_size_annotations` | 6 | explicit |
| `font_size_legend` | 8 | explicit |
| `font_size_legend2` | -1 | legend |
| `font_size_legend3` | -1 | legend |
| `legend3_number_fontsize` | -1 | legend3 |
| `legend3_text_fontsize` | -1 | legend3 |
