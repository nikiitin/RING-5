# Step 14 — Export, Download & Presets Analysis

> **Objective**: Document the complete export pipeline, all 13 presets,
> LaTeX generation, and download UI integration.

---

## 1. Executive Summary

The RING-5 Unified Engine v2 provides a full-featured, publication-quality export system
built around three pillars:

1. **13 venue-specific presets** (stored in `latex_presets.json`) that encode precise
   dimensions, fonts, DPI, and legend spacing for IEEE, ACM, ISCA, MICRO, ASPLOS, HPCA,
   TACO, Nature, Science, poster, and slides targets.
2. **A dual-engine export pipeline** that supports Plotly (Kaleido v1) for HTML/PNG/SVG/PDF
   and Matplotlib (`savefig`) for PDF/PGF/PNG/SVG -- with PGF producing native LaTeX
   vector output.
3. **A Streamlit download UI** (`render_download_section`) that presents engine-aware
   format pills and an `st.download_button`, plus a programmatic `export_plot_to_file`
   API for batch export.

The preset system is **immutable** -- presets are overlaid onto a `FigureConfig`
via `dataclasses.replace()`, producing a new spec with publication-quality
dimensions/typography/axes/legends while preserving all user-defined trace data,
colors, and annotations.  Sentinel resolution (`-1` values) ensures clean
inheritance chains before any connector touches the spec.

---

## 2. Export Architecture Overview

```
                         ┌─────────────────────────┐
                         │   User clicks Download   │
                         └─────────┬───────────────┘
                                   │
                                   ▼
                   ┌─────────────────────────────────┐
                   │  render_download_section()       │
                   │  (download_section.py)           │
                   │                                  │
                   │  EngineManager.is_matplotlib()?  │
                   └───────┬───────────┬──────────────┘
                           │           │
                    ┌──────┘           └──────┐
                    ▼                          ▼
    ┌──────────────────────────┐  ┌──────────────────────────┐
    │  _render_mpl_download()  │  │ _render_plotly_download() │
    │                          │  │                           │
    │  Format pills:           │  │  Format pills:            │
    │    PDF / PGF / PNG / SVG │  │    HTML / PNG / SVG / PDF │
    │                          │  │                           │
    │  matplotlib_download_    │  │  plotly_download_bytes()  │
    │  bytes(fig, fmt)         │  │  (fig, fmt)               │
    └────────┬─────────────────┘  └────────┬──────────────────┘
             │                              │
             ▼                              ▼
    ┌──────────────────────┐    ┌──────────────────────┐
    │  fig.savefig(buf)    │    │  fig.to_image() or   │
    │  (agg/pgf backend)   │    │  fig.to_html()       │
    └──────────┬───────────┘    └──────────┬───────────┘
               │                            │
               ▼                            ▼
    ┌──────────────────────────────────────────────────┐
    │  st.download_button(data=bytes, mime=...,        │
    │                     file_name=plot_name + ext)   │
    └──────────────────────────────────────────────────┘
```

### Preset Application Pipeline

```
User config (flat dict)
       │
       ▼
ConfigSpecBuilder.from_config(config, plot_type)
       │
       ▼
FigureConfig (data-derived: traces, colors, annotations)
       │
       ├── [Optional] PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)
       │
       ▼
PresetApplicator.apply(spec, preset_dict)     ← overlay publication fields
       │
       ▼
resolve_config(spec)                          ← resolve -1 sentinels
       │
       ▼
FigureSpecToPlotly.apply(spec, fig)    OR    FigureSpecToMatplotlib.apply(spec, ax)
```

---

## 3. File Inventory

### 3.1 Download UI

| File | Purpose | LOC |
|------|---------|-----|
| `src/web/pages/ui/plotting/download_section.py` | Byte-producing functions + `render_download_section()` UI | 274 |

### 3.2 Export Preset System

| File | Purpose | LOC |
|------|---------|-----|
| `src/web/pages/ui/plotting/export/__init__.py` | Module entry -- re-exports `PresetManager` | 5 |
| `src/web/pages/ui/plotting/export/presets/__init__.py` | Re-exports `PresetManager`, `LaTeXPreset`, `ExportResult` | 6 |
| `src/web/pages/ui/plotting/export/presets/preset_manager.py` | Loads, validates, caches presets from JSON | 283 |
| `src/web/pages/ui/plotting/export/presets/preset_schema.py` | `LaTeXPreset` TypedDict + `ExportResult` TypedDict | 159 |
| `src/web/pages/ui/plotting/export/presets/latex_presets.json` | JSON catalogue of all 13 presets | 272 |

### 3.3 Preset Application

| File | Purpose | LOC |
|------|---------|-----|
| `src/web/rendering/preset_applicator.py` | `PresetApplicator.apply()` and `apply_partial()` | 194 |
| `src/web/rendering/config_builder.py` | `PresetSpecBuilder.from_preset()` + `ConfigSpecBuilder.from_config()` | 926 |

### 3.4 Rendering Connectors (Export Paths)

| File | Purpose | LOC |
|------|---------|-----|
| `src/web/rendering/engine_manager.py` | `EngineManager` -- Plotly/Matplotlib mode toggle | 85 |
| `src/web/rendering/plotly_connector.py` | `FigureSpecToPlotly.apply()` -- FigureConfig to Plotly calls | 890 |
| `src/web/rendering/matplotlib_connector.py` | `FigureSpecToMatplotlib.apply()` -- FigureConfig to matplotlib calls | 1078 |
| `src/web/rendering/__init__.py` | Public API surface for rendering layer | 43 |

### 3.5 Core Models

| File | Purpose | LOC |
|------|---------|-----|
| `src/core/models/visualization/figure_config.py` | `FigureConfig`, `DimensionConfig`, `MarginsConfig`, `SeparatorConfig` | 301 |
| `src/core/models/visualization/typography_config.py` | `TypographyConfig` with sentinel inheritance chain | 72 |
| `src/core/services/visualization/config_resolver.py` | `resolve_config()` -- sentinel -1 resolution | 185 |

### 3.6 UI Integration

| File | Purpose | LOC |
|------|---------|-----|
| `src/web/pages/ui/plotting/settings_pills.py` | `render_preset_pills()` -- preset selector UI | 125 |
| `src/web/components/common/chart_display.py` | `ChartDisplayComponent` -- wires download section into chart display | 293 |
| `src/web/pages/ui/plotting/plot_service.py` | `PlotService.export_plot_to_file()` -- programmatic file export | 153 |
| `src/web/components/plotting/settings/engine_settings.py` | LaTeX preamble + TeX system controls (matplotlib mode) | 60+ |
| `src/web/components/plotting/settings/layout_settings.py` | Layout dimensions component with single/double column quick presets | 60+ |

### 3.7 Reference Documentation

| File | Purpose |
|------|---------|
| `.agent/context/visualization-best-practices.md` | Venue-specific rcParams, DPI rules, PGF usage, font size guidelines |

---

## 4. Preset Catalog

All 13 presets are defined in `src/web/pages/ui/plotting/export/presets/latex_presets.json`.

### 4.1 Computer Architecture Conference Presets

#### `single_column` -- Standard IEEE/ACM Single Column
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 1.96875 in |
| Aspect ratio | ~16:9 |
| Font family | serif |
| Font size (base/title/labels/ticks) | 10 / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | `\usepackage[varqu,scaled=0.95]{zi4}` |

#### `double_column` -- Full Width for Two-Column Papers
| Property | Value |
|----------|-------|
| Width | 7.0 in |
| Height | 5.25 in |
| Aspect ratio | 4:3 |
| Font family | serif |
| Font size (base/title/labels/ticks) | 10 / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | `\usepackage[varqu,scaled=0.95]{zi4}` |

#### `micro` -- MICRO Conference Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 2.5 in |
| Font family | serif |
| Font size (base/title/labels/ticks) | 10 / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | `\usepackage[varqu,scaled=0.95]{zi4}` |

#### `isca` -- ISCA Conference Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 2.5 in |
| Font family | serif |
| Font size (base/title/labels/ticks) | 10 / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | `\usepackage[varqu,scaled=0.95]{zi4}` |

#### `asplos` -- ASPLOS Conference Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 2.5 in |
| Font family | serif |
| Font size (base/title/labels/ticks) | 10 / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | `\usepackage[varqu,scaled=0.95]{zi4}` |

#### `hpca` -- HPCA Conference Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 2.5 in |
| Font family | serif |
| Font size (base/title/labels/ticks) | 10 / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | `\usepackage[varqu,scaled=0.95]{zi4}` |

#### `taco` -- ACM TACO Journal Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 2.5 in |
| Font family | serif |
| Font size (base/title/labels/ticks) | 10 / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | `\usepackage[varqu,scaled=0.95]{zi4}` |

### 4.2 High-Impact Journal Presets

#### `nature` -- Nature Journal Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 3.5 in |
| Aspect ratio | 1:1 (square) |
| Font family | **Arial** |
| Font size (base/title/labels/ticks) | 7 / 8 / 7 / 6 pt |
| Line width / marker size | 0.5 pt / 2.0 |
| DPI | **600** |
| LaTeX preamble | (none) |

#### `science` -- Science Journal Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 2.5 in |
| Font family | **sans-serif** |
| Font size (base/title/labels/ticks) | 8 / 9 / 8 / 7 pt |
| Line width / marker size | 0.5 pt / 2.0 |
| DPI | **600** |
| LaTeX preamble | (none) |

### 4.3 IEEE/ACM Standard Presets

#### `ieee_single` -- IEEE Transactions Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 2.5 in |
| Font family | serif |
| Font size (base/title/labels/ticks) | 10 / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | (none) |

#### `acm` -- ACM Proceedings Style
| Property | Value |
|----------|-------|
| Width | 3.5 in |
| Height | 2.5 in |
| Font family | serif |
| Font size (base/title/labels/ticks) | **9** / 10 / 9 / 8 pt |
| Line width / marker size | 1.0 pt / 4.0 |
| DPI | 300 |
| LaTeX preamble | `\usepackage[varqu,scaled=0.95]{zi4}` |

### 4.4 Presentation Presets

#### `poster` -- Poster Style (Large)
| Property | Value |
|----------|-------|
| Width | **10.0 in** |
| Height | **7.0 in** |
| Font family | **sans-serif** |
| Font size (base/title/labels/ticks) | **24 / 28 / 24 / 20 pt** |
| Line width / marker size | **2.0 pt / 8.0** |
| DPI | **150** |
| LaTeX preamble | (none) |

#### `slides` -- Presentation Slides Style
| Property | Value |
|----------|-------|
| Width | **8.0 in** |
| Height | **4.5 in** |
| Aspect ratio | 16:9 |
| Font family | **sans-serif** |
| Font size (base/title/labels/ticks) | **18 / 22 / 18 / 14 pt** |
| Line width / marker size | **1.5 pt / 6.0** |
| DPI | **150** |
| LaTeX preamble | (none) |

### 4.5 Preset Differentiation Summary

| Preset | Width | Height | DPI | Font | Base Size | Preamble |
|--------|-------|--------|-----|------|-----------|----------|
| single_column | 3.5 | 1.97 | 300 | serif | 10 | zi4 |
| double_column | 7.0 | 5.25 | 300 | serif | 10 | zi4 |
| micro | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| isca | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| asplos | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| hpca | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| taco | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| nature | 3.5 | 3.5 | 600 | Arial | 7 | -- |
| science | 3.5 | 2.5 | 600 | sans-serif | 8 | -- |
| ieee_single | 3.5 | 2.5 | 300 | serif | 10 | -- |
| acm | 3.5 | 2.5 | 300 | serif | 9 | zi4 |
| poster | 10.0 | 7.0 | 150 | sans-serif | 24 | -- |
| slides | 8.0 | 4.5 | 150 | sans-serif | 18 | -- |

### 4.6 Legend Spacing (Shared Across All Presets)

All 13 presets share identical legend spacing:

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

## 5. Export Pipeline

### 5.1 Preset Loading and Validation

**File**: `src/web/pages/ui/plotting/export/presets/preset_manager.py`

```
PresetManager.load_preset("isca")
    │
    ├── Check in-memory cache (_cache dict)
    │
    ├── If miss: _initialize() → load latex_presets.json (once)
    │
    ├── Extract LaTeXPreset fields from raw JSON
    │   (with defaults via .get() for optional fields)
    │
    ├── validate_preset(preset) → checks required fields,
    │   positive dimensions, positive font sizes, positive DPI
    │
    └── Cache in _cache for subsequent lookups → return LaTeXPreset dict
```

**Validation rules** (enforced in `validate_preset()`):
- 19 required fields must be present
- `width_inches` > 0
- `height_inches` > 0
- `font_size_base` > 0
- `font_size_title` > 0
- `font_size_xlabel` > 0
- `font_size_ylabel` > 0
- `font_size_legend` > 0
- `font_size_ticks` > 0
- `line_width` > 0
- `marker_size` > 0
- `dpi` > 0

### 5.2 Preset Selection UI

**File**: `src/web/pages/ui/plotting/settings_pills.py`

`render_preset_pills(plot_id)`:
- Lists all presets via `PresetManager.list_presets()`
- Prepends `"none"` option
- Renders `st.pills()` with `selection_mode="single"`, `default="none"`
- Format function: "None" for no preset, UPPERCASE for preset names (e.g., "ISCA")
- Returns selected preset name (`str | None`)

### 5.3 Preset Application to FigureConfig

**File**: `src/web/rendering/preset_applicator.py`

The `PresetApplicator` provides two static methods:

#### `PresetApplicator.apply(spec, preset_info)` -- Full Overlay

1. Calls `PresetSpecBuilder.from_preset(preset_info)` to build a complete `FigureConfig` from the preset dict.
2. Uses `dataclasses.replace()` to produce a **new** `FigureConfig` that overlays:
   - `dimensions` (width, height, DPI, bar_width_scale)
   - `typography` (all font sizes + bold flags)
   - `axes` (tick rotation, padding, margins, group label settings)
   - `legends` (primary + secondary + tertiary, with full spacing)
   - `separator` (group separator enabled/style/color)
   - `font_family` (serif / sans-serif / Arial)
   - `latex_extra_preamble` (zi4 package, etc.)
3. **Preserved from user config** (NOT overridden):
   - `traces`, `annotations`, `data_labels`
   - `series_styles`, `trace_overrides`
   - `color_palette`, `hatching_sequence`
   - `reference_lines`, `hovermode`
   - `enable_stripes`, `show_error_bars`
   - `title`, `paper_bgcolor`, `plot_bgcolor`
   - `metadata`, `barmode`

#### `PresetApplicator.apply_partial(spec, preset_info)` -- Selective Overlay

Only overrides FigureConfig fields whose corresponding preset keys are *actually present*
in the input dict.  Uses set intersection to determine which field groups to replace:

- `_DIMENSION_KEYS` = {width_inches, height_inches, dpi, bar_width_scale}
- `_TYPO_KEYS` = {font_size_*, bold_*} (26 keys)
- `_AXES_KEYS` = {xtick_*, ylabel_*, group_label_*} (11 keys)
- `_LEGEND_KEYS` = {legend_*, legend2_*, legend3_*} (20 keys)
- `_SEPARATOR_KEYS` = {group_separator, group_separator_style, group_separator_color}
- Scalar keys: `font_family`, `latex_extra_preamble`

### 5.4 PresetSpecBuilder -- Preset Dict to FigureConfig

**File**: `src/web/rendering/config_builder.py`, class `PresetSpecBuilder`

`PresetSpecBuilder.from_preset(preset)` converts the flat `LaTeXPreset` dictionary
into a structured `FigureConfig` by constructing:

1. **DimensionConfig**: width, height, DPI, bar_width_scale (margins left as defaults).
2. **TypographyConfig**: All 13 font sizes + 10 bold flags, with sentinel `-1` for
   secondary/tertiary values that inherit from primaries.
3. **AxesConfig**: X-axis (tick rotation, tick padding, horizontal alignment, offset, margin)
   and Y-axis (label padding, label position, tick padding). Group label offset/alternate/spacing.
4. **Three LegendConfigs** (primary, secondary, tertiary): Each with its own
   `LegendSpacingConfig` (columnspacing, handletextpad, labelspacing, handlelength,
   handleheight, borderpad, borderaxespad). Secondary and tertiary default to sentinel
   `-1.0` values that resolve to primary values.
5. **SeparatorConfig**: enabled, style, color.
6. **Scalars**: font_family, latex_extra_preamble.

### 5.5 Sentinel Resolution

**File**: `src/core/services/visualization/config_resolver.py`

`resolve_config(spec)` performs a deep copy then resolves all `-1` sentinels:

**Typography chain**:
```
font_size_base
├── font_size_y2label  → inherits font_size_ylabel
├── font_size_yticks   → inherits font_size_ticks
├── font_size_y2ticks  → inherits font_size_yticks
├── font_size_legend2  → inherits font_size_legend
└── font_size_legend3  → inherits font_size_legend
    ├── legend3_number_fontsize → inherits font_size_legend3
    └── legend3_text_fontsize   → inherits font_size_legend3
```

**Legend spacing chain**:
```
legend[0].spacing      → concrete values
legend[1].spacing      → inherits legend[0].spacing (where -1.0)
legend[2].spacing      → inherits legend[0].spacing (where -1.0)
```

**Axes chain**:
```
y.label_pad            → concrete
y2.label_pad           → inherits y.label_pad (where -1.0)
y2.tick_pad            → inherits y.tick_pad (where -1.0)
```

---

## 6. LaTeX Generation

### 6.1 PGF Export Path (Native LaTeX)

**File**: `src/web/pages/ui/plotting/download_section.py`, function `matplotlib_download_bytes()`

The PGF format produces native LaTeX vector commands that can be `\input{}`-ed
directly into a LaTeX document. The font automatically matches the surrounding document.

```python
if fmt == "pgf":
    preamble = spec.latex_extra_preamble if spec else ""
    with plt.rc_context({
        "pgf.texsystem": "xelatex",
        "pgf.preamble": preamble,
        "pgf.rcfonts": True,
    }):
        fig.savefig(buf, format="pgf", backend="pgf")
```

Key settings:
- **TeX system**: XeLaTeX (supports Unicode, system fonts)
- **Preamble**: Injected from preset's `latex_extra_preamble` (e.g., `\usepackage[varqu,scaled=0.95]{zi4}` for Inconsolata monospace font)
- **rcfonts**: True (use matplotlib's rc font settings in PGF output)
- **Fallback**: When PGF fails (e.g., raster graphics in heatmaps), falls back to PDF with a user warning

### 6.2 PDF Export Path (LaTeX-Quality Vector)

```python
elif fmt == "pdf":
    fig.savefig(buf, format="pdf", dpi=dpi, bbox_inches="tight")
```

- Uses matplotlib's PDF backend
- `bbox_inches="tight"` prevents label/legend clipping
- DPI parameter controls raster element resolution inside the PDF

### 6.3 PNG Export Path (Raster)

```python
elif fmt == "png":
    with plt.rc_context({"text.usetex": False}):
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", backend="agg")
```

- Explicitly disables `usetex` to avoid dvipng dependency issues
- Uses the `agg` backend for anti-aliased raster output
- DPI from the preset (300 for papers, 600 for Nature/Science, 150 for presentations)

### 6.4 SVG Export Path

```python
elif fmt == "svg":
    fig.savefig(buf, format="svg", bbox_inches="tight")
```

- Vector output; DPI irrelevant for geometry
- Text rendered as SVG text elements (not paths)

### 6.5 LaTeX Preamble Configuration

The `latex_extra_preamble` field flows through the system as follows:

1. **Stored in preset JSON**: `"latex_extra_preamble": "\\usepackage[varqu,scaled=0.95]{zi4}"`
2. **Loaded into LaTeXPreset dict** by `PresetManager.load_preset()`
3. **Mapped to FigureConfig.latex_extra_preamble** by `PresetSpecBuilder.from_preset()`
4. **Overlaid onto user spec** by `PresetApplicator.apply()`
5. **Consumed at export time** by `matplotlib_download_bytes()` for PGF rc_context

The `zi4` package (used by 7 of 13 presets) provides the Inconsolata monospace font
scaled to 95%, matching typical IEEE/ACM document typewriter fonts.

### 6.6 Engine Settings UI for LaTeX

**File**: `src/web/components/plotting/settings/engine_settings.py`

When the rendering engine is Matplotlib, the "Advanced" settings section shows:
- **Extra LaTeX preamble**: `st.text_area` for manual preamble entry
- This value is stored in `config["latex_extra_preamble"]` and flows into `FigureConfig`

### 6.7 LaTeX-Safe Text Escaping

**File**: `src/web/rendering/matplotlib_connector.py`, method `_escape_latex()`

All user-provided text (titles, labels, tick text, annotations) is passed through
`_escape_latex()` before rendering into matplotlib:

```python
special_chars = ["&", "%", "$", "#", "_", "{", "}"]
```

The method preserves existing LaTeX commands (`\textbf`, `\texttt`, `\textit`, `\mathrm`)
and only escapes raw special characters, allowing users to embed LaTeX formatting
in their labels.

---

## 7. Download UI Integration

### 7.1 Download Section Component

**File**: `src/web/pages/ui/plotting/download_section.py`

`render_download_section(plot_id, plot_name, fig)` wraps everything in a
collapsed `st.expander("Download", expanded=False)` and branches on engine:

#### Plotly Path (`_render_plotly_download`)

1. **Format pills**: `st.pills("Format", options=["html", "png", "svg", "pdf"], default="html")`
2. **Byte generation**: `plotly_download_bytes(fig, fmt, width=700, height=400, scale=2)`
   - HTML: `fig.to_html(include_plotlyjs=True, full_html=True)` encoded to UTF-8
   - PNG/SVG/PDF: `fig.to_image(format=fmt, width=width, height=height, scale=scale)` via Kaleido v1
3. **Download button**: `st.download_button(label, data, file_name, mime, use_container_width=True)`

#### Matplotlib Path (`_render_mpl_download`)

1. **Figure retrieval**: `st.session_state.get(f"plot.{plot_id}.mpl_fig")`
2. **Format pills**: `st.pills("Format", options=["pdf", "pgf", "png", "svg"], default="pdf")`
3. **Byte generation**: `matplotlib_download_bytes(fig, fmt, dpi=300, spec=None)`
4. **PGF fallback**: If PGF fails with "raster" error (heatmaps), auto-fallback to PDF with warning
5. **Download button**: Same `st.download_button` pattern

### 7.2 Chart Display Integration

**File**: `src/web/components/common/chart_display.py`

Both `render_plotly_chart()` and `render_matplotlib_chart()` call
`render_download_section()` after displaying the chart:

```python
# In render_plotly_chart():
relayout_data = interactive_plotly_chart(fig, config=plotly_config, key=...)
render_download_section(plot_id, plot_name, fig)   # ← download section follows chart

# In render_matplotlib_chart():
st.pyplot(mpl_fig)
st.session_state[mpl_state_key] = mpl_fig          # ← store for download
render_download_section(plot_id, plot_name, plotly_fig)
```

Note: The matplotlib download section stores the `MplFigure` in session state
at key `plot.{plot_id}.mpl_fig`. The download section retrieves it from there.
The figure is closed (`plt.close()`) on the next render cycle.

### 7.3 Plotly Built-In Export Button

**File**: `src/web/components/common/chart_display.py`

The Plotly interactive chart also has a built-in "Download as SVG" button in the
modebar, configured via `toImageButtonOptions`:

```python
"toImageButtonOptions": {
    "format": "svg",
    "filename": f"{plot_name}_view",
    "height": config.get("height", 500),
    "width": config.get("width", 800),
    "scale": config.get("export_scale", 1),
}
```

This provides a quick one-click SVG export separate from the formal download section.

### 7.4 Programmatic File Export

**File**: `src/web/pages/ui/plotting/plot_service.py`

`PlotService.export_plot_to_file(plot, directory, format)`:
- Supports HTML, PDF, PNG, SVG
- Uses `plotly_download_bytes()` for PDF/PNG/SVG
- Uses `fig.write_html()` for HTML
- Input validation: format must be in `["html", "pdf", "png", "svg"]`
- Path sanitization: `normalize_user_path()` + `validate_path_within()` prevent path traversal
- Safe filename: strips non-alphanumeric characters from plot name

---

## 8. Supported Export Formats

### 8.1 Format Support Matrix

| Format | Plotly Engine | Matplotlib Engine | Method | Notes |
|--------|:------------:|:-----------------:|--------|-------|
| **PNG** | Yes | Yes | Kaleido `to_image()` / `savefig(backend="agg")` | Raster; scale param for Plotly, DPI for Matplotlib |
| **SVG** | Yes | Yes | Kaleido `to_image()` / `savefig()` | Vector; text as elements |
| **PDF** | Yes | Yes | Kaleido `to_image()` / `savefig(bbox_inches="tight")` | Vector; `bbox_inches="tight"` for Matplotlib |
| **HTML** | Yes | No | `to_html(include_plotlyjs=True)` | Interactive; self-contained with plotly.js bundled |
| **PGF** | No | Yes | `savefig(format="pgf", backend="pgf")` | Native LaTeX commands; fonts match document |

### 8.2 MIME Types

| Format | MIME Type |
|--------|-----------|
| PNG | `image/png` |
| SVG | `image/svg+xml` |
| PDF | `application/pdf` |
| HTML | `text/html` |
| PGF | `application/x-pgf` |

### 8.3 File Extensions

| Format | Extension |
|--------|-----------|
| PNG | `.png` |
| SVG | `.svg` |
| PDF | `.pdf` |
| HTML | `.html` |
| PGF | `.pgf` |

### 8.4 Default Export Parameters

| Parameter | Plotly Default | Matplotlib Default |
|-----------|---------------|-------------------|
| Width | 700 px | From FigureConfig (inches) |
| Height | 400 px | From FigureConfig (inches) |
| Scale | 2x | N/A |
| DPI | N/A (Kaleido) | 300 (from preset) |
| Default format | HTML | PDF |

### 8.5 Format Selection by Use Case

| Use Case | Recommended Format | Engine | Why |
|----------|-------------------|--------|-----|
| LaTeX paper (`\input{}`) | PGF | Matplotlib | Native LaTeX commands, fonts auto-match |
| LaTeX paper (`\includegraphics{}`) | PDF | Matplotlib | Vector, `bbox_inches="tight"` |
| High-DPI print (Nature, Science) | PDF or PNG@600DPI | Matplotlib | Preset has DPI=600 |
| Interactive web report | HTML | Plotly | Plotly.js bundled, zoom/pan/hover |
| Quick screenshot | PNG | Either | Raster, widely compatible |
| Editing in Illustrator/Inkscape | SVG | Either | Editable vector paths |

---

## 9. Downstream Dependencies

### 9.1 Documentation Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` -> `export/export-system.md` (export pipeline architecture)
- `DEVELOPER_GUIDE_PLAN.md` -> `export/adding-export-format.md` (extension guide)
- `USER_GUIDE_PLAN.md` -> `webapp/export-download.md` (user-facing export docs)

### 9.2 Step Dependencies

| Step | Dependency Relationship |
|------|------------------------|
| Step 1 (Architecture) | Export system spans web/rendering and web/pages/ui layers |
| Step 3 (FigureConfig) | FigureConfig is the central data contract for preset application |
| Step 4 (Typography) | TypographyConfig sentinel chain is resolved before export |
| Step 7 (Legends) | LegendConfig spacing inherits within preset system |
| Step 11 (Matplotlib Connector) | `FigureSpecToMatplotlib` is the rendering endpoint for LaTeX exports |
| Step 12 (Plotly Connector) | `FigureSpecToPlotly` is the rendering endpoint for interactive exports |
| Step 18 (Data Flow) | Export is the final output step in the data flow |
| Step 19 (Extension Points) | Preset system is a key extension point (add new presets via JSON) |

### 9.3 Runtime Dependencies

| Component | External Dependency | Version Constraint |
|-----------|--------------------|--------------------|
| Plotly PNG/SVG/PDF export | Kaleido v1 | Uses `fig.to_image()` |
| Plotly HTML export | plotly.js | Bundled via `include_plotlyjs=True` |
| Matplotlib PGF export | XeLaTeX | System install required |
| Matplotlib PNG export | matplotlib agg backend | Built-in |
| Matplotlib PDF/SVG export | matplotlib backends | Built-in |
| Download buttons | Streamlit `st.download_button` | Streamlit >= 1.0 |
| Format pills | Streamlit `st.pills` | Streamlit >= 1.33 |

### 9.4 Extension Points for New Presets

To add a new preset (e.g., for a new conference):

1. Add a new entry to `src/web/pages/ui/plotting/export/presets/latex_presets.json`
2. The preset is auto-discovered by `PresetManager.list_presets()` (reads from JSON `presets` key)
3. The preset appears in `render_preset_pills()` automatically
4. No code changes required -- purely data-driven via JSON configuration

Required fields for a new preset entry:
- `description` (metadata only, not used in rendering)
- `width_inches`, `height_inches` (physical dimensions)
- `font_family` (serif / sans-serif / specific font name)
- `font_size_base`, `font_size_title`, `font_size_labels`, `font_size_ticks` (typography)
- `line_width`, `marker_size` (trace styling)
- `dpi` (raster resolution)
- 7 legend spacing parameters (columnspacing, handletextpad, labelspacing,
  handlelength, handleheight, borderpad, borderaxespad)

Optional fields (with defaults): all bold flags, secondary/tertiary legend spacing,
positioning parameters, axis margins, bar width scale, group separator settings,
LaTeX preamble.

---

## 10. Key Design Decisions

### 10.1 Immutable Preset Application

Presets never mutate the existing `FigureConfig`. `PresetApplicator.apply()` uses
`dataclasses.replace()` to produce a new instance.  This ensures:
- No side effects on the user's interactive config
- Clean undo semantics (just discard the preset-applied spec)
- Thread safety in concurrent Streamlit sessions

### 10.2 Sentinel-Based Inheritance

The `-1` / `-1.0` sentinel pattern allows presets to declare "inherit from primary"
for secondary/tertiary legends, y2 axes, etc. without complex configuration.
Resolution happens in a single `resolve_config()` pass before any connector
touches the spec.

### 10.3 Engine-Agnostic Preset Model

Presets produce a `FigureConfig` that is consumed identically by both the Plotly
and Matplotlib connectors.  The same preset works for interactive preview (Plotly)
and publication export (Matplotlib/PGF) without any engine-specific preset variants.

### 10.4 PGF as the Primary LaTeX Export

PGF output is preferred over PDF for LaTeX papers because:
- Text is rendered as native LaTeX commands (not embedded fonts)
- Fonts automatically match the surrounding document
- File sizes are smaller than PDF with embedded fonts
- Full LaTeX math mode support in labels/annotations

### 10.5 Session-State Figure Lifecycle

The Matplotlib figure is stored in `st.session_state[f"plot.{plot_id}.mpl_fig"]`
for download access, but is explicitly closed with `plt.close()` on the next
render cycle to prevent memory leaks.  This is a compromise between immediate
disposal and the need for the download section to access the figure bytes on demand.

### 10.6 JSON-Driven Preset Storage

Presets are stored in a single JSON file rather than in Python code or YAML because:
- JSON is stdlib-parseable (`json.load()`) with no external dependency
- The project explicitly removed PyYAML in favor of stdlib JSON (commit `801098f`)
- JSON is easily human-editable for adding new venue presets
- In-memory caching in `PresetManager._cache` avoids repeated disk I/O
