# Export and Preset System

## Overview

The Unified Engine provides a publication-quality export system built on three pillars:

1. **13 venue-specific presets** stored in `latex_presets.json`, encoding exact
   dimensions, fonts, DPI, and legend spacing for IEEE, ACM, ISCA, MICRO, ASPLOS,
   HPCA, TACO, Nature, Science, poster, and slides targets.
2. **A dual-engine export pipeline** supporting Plotly (Kaleido v1) for
   HTML/PNG/SVG/PDF and Matplotlib (`savefig`) for PDF/PGF/PNG/SVG -- with PGF
   producing native LaTeX vector output.
3. **A Streamlit download UI** (`render_download_section`) that presents
   engine-aware format pills and an `st.download_button`, plus a programmatic
   `export_plot_to_file` API for batch export.

Presets are **immutable**. They are overlaid onto a `FigureConfig` via
`dataclasses.replace()`, producing a new spec with publication-quality
dimensions and typography while preserving all user-defined trace data,
colors, and annotations. Sentinel resolution (`-1` values) ensures clean
inheritance chains before any rendering connector touches the spec.

### Key source files

| File | Role |
|------|------|
| `src/web/pages/ui/plotting/export/presets/preset_schema.py` | `LaTeXPreset` and `ExportResult` TypedDicts |
| `src/web/pages/ui/plotting/export/presets/preset_manager.py` | Loads, validates, and caches presets from JSON |
| `src/web/pages/ui/plotting/export/presets/latex_presets.json` | JSON catalogue of all 13 presets |
| `src/web/rendering/preset_applicator.py` | `PresetApplicator.apply()` and `apply_partial()` |
| `src/web/rendering/config_builder.py` | `PresetSpecBuilder.from_preset()` -- flat dict to `FigureConfig` |
| `src/web/pages/ui/plotting/download_section.py` | Byte-producing functions and download UI |

---

## Preset Catalog

All 13 presets are defined in
`src/web/pages/ui/plotting/export/presets/latex_presets.json`. Adding a new
entry to that file is all that is needed to register a new preset -- no code
changes required.

| Preset | Width (in) | Height (in) | DPI | Font Family | Base Size (pt) | LaTeX Preamble |
|--------|-----------|-------------|-----|-------------|---------------|----------------|
| `single_column` | 3.5 | 1.97 | 300 | serif | 10 | zi4 |
| `double_column` | 7.0 | 5.25 | 300 | serif | 10 | zi4 |
| `micro` | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| `isca` | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| `asplos` | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| `hpca` | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| `taco` | 3.5 | 2.5 | 300 | serif | 10 | zi4 |
| `nature` | 3.5 | 3.5 | 600 | Arial | 7 | -- |
| `science` | 3.5 | 2.5 | 600 | sans-serif | 8 | -- |
| `ieee_single` | 3.5 | 2.5 | 300 | serif | 10 | -- |
| `acm` | 3.5 | 2.5 | 300 | serif | 9 | zi4 |
| `poster` | 10.0 | 7.0 | 150 | sans-serif | 24 | -- |
| `slides` | 8.0 | 4.5 | 150 | sans-serif | 18 | -- |

All 13 presets share identical legend spacing: `columnspacing=1.0`,
`handletextpad=0.5`, `labelspacing=0.3`, `handlelength=1.5`,
`handleheight=0.7`, `borderpad=0.3`, `borderaxespad=0.3`.

The "zi4" preamble refers to `\usepackage[varqu,scaled=0.95]{zi4}`, which
provides the Inconsolata monospace font scaled to 95% -- matching typical
IEEE/ACM document typewriter fonts.

---

## Preset Schema

Presets are typed through the `LaTeXPreset` TypedDict defined in
`src/web/pages/ui/plotting/export/presets/preset_schema.py`. The dict uses
`total=False`, meaning all keys are optional at the type level; required keys
are enforced at runtime by `PresetManager.validate_preset()`.

The schema is organized into these field groups:

- **Dimensions**: `width_inches`, `height_inches`, `dpi`, `bar_width_scale`
- **Typography**: 13 font-size fields (`font_size_base` through
  `font_size_annotations`) and 10 bold flags (`bold_title` through
  `bold_group_labels`)
- **Legend spacing**: 7 primary keys (`legend_columnspacing` ...
  `legend_borderaxespad`), 8 secondary keys (`legend2_*`), and 4 tertiary
  keys (`legend3_*`)
- **Axes**: tick rotation/padding, label padding/position, group label offset
- **Separator**: `group_separator`, `group_separator_style`,
  `group_separator_color`
- **LaTeX**: `latex_extra_preamble`

A companion `ExportResult` TypedDict carries the output of an export
operation:

```python
class ExportResult(TypedDict):
    success: bool
    data: bytes | None
    format: str
    error: str | None
    metadata: dict[str, Any]
```

---

## Preset Manager

`PresetManager` in `src/web/pages/ui/plotting/export/presets/preset_manager.py`
is the single entry point for loading presets. It is a classmethod-only manager
with an in-memory cache.

### Loading a preset

```python
from src.web.pages.ui.plotting.export import PresetManager

preset = PresetManager.load_preset("isca")
print(preset["width_inches"])  # 3.5
```

Internally, `load_preset` follows this sequence:

1. Check `_cache` dict for a hit.
2. On miss, call `_initialize()` which reads `latex_presets.json` once and
   stores the raw data in `_presets_data`.
3. Extract `LaTeXPreset` fields from the raw JSON entry, applying defaults via
   `.get()` for optional fields (sentinel `-1` for secondary/tertiary values).
4. Call `validate_preset()` to enforce required fields and positive-value
   constraints.
5. Store the validated preset in `_cache` and return it.

### Validation rules

`validate_preset()` enforces:

- 19 required fields must be present (dimensions, font sizes, legend spacing).
- `width_inches`, `height_inches` must be positive.
- `font_size_base`, `font_size_title`, `font_size_xlabel`, `font_size_ylabel`,
  `font_size_legend`, `font_size_ticks` must be positive.
- `line_width`, `marker_size`, `dpi` must be positive.

### Listing and metadata

```python
names = PresetManager.list_presets()       # ["single_column", "double_column", ...]
info = PresetManager.get_preset_info("nature")  # {"description": "...", "typical_use": "..."}
```

---

## Preset Applicator

`PresetApplicator` in `src/web/rendering/preset_applicator.py` is a stateless
service that merges a preset onto an existing `FigureConfig`.

### Full overlay -- `apply()`

```python
from src.web.rendering.preset_applicator import PresetApplicator

new_spec = PresetApplicator.apply(config_spec, preset_dict)
```

This method:

1. Converts the flat preset dict into a structured `FigureConfig` via
   `PresetSpecBuilder.from_preset()`.
2. Uses `dataclasses.replace()` to produce a new `FigureConfig` that overrides:
   `dimensions`, `typography`, `axes`, `legends`, `separator`, `font_family`,
   and `latex_extra_preamble`.
3. Preserves from the original spec: `traces`, `annotations`, `data_labels`,
   `series_styles`, `trace_overrides`, `color_palette`, `hatching_sequence`,
   `reference_lines`, `hovermode`, `enable_stripes`, `show_error_bars`,
   `title`, `paper_bgcolor`, `plot_bgcolor`, `metadata`, `barmode`.

### Selective overlay -- `apply_partial()`

```python
new_spec = PresetApplicator.apply_partial(config_spec, partial_dict)
```

Only overrides field groups whose keys are present in the input dict. Uses set
intersection between the input keys and predefined key groups:

| Key group | FigureConfig field | Example keys |
|-----------|--------------------|-------------|
| `_DIMENSION_KEYS` | `dimensions` | `width_inches`, `height_inches`, `dpi` |
| `_TYPO_KEYS` | `typography` | `font_size_base`, `bold_title` |
| `_AXES_KEYS` | `axes` | `xtick_rotation`, `ylabel_pad` |
| `_LEGEND_KEYS` | `legends` | `legend_columnspacing`, `legend2_*` |
| `_SEPARATOR_KEYS` | `separator` | `group_separator`, `group_separator_style` |
| scalar | `font_family` | `font_family` |
| scalar | `latex_extra_preamble` | `latex_extra_preamble` |

If no keys in the input match any group, the original spec is returned
unchanged.

### Sentinel resolution

After preset application, `resolve_config()` from
`src/core/services/visualization/config_resolver.py` replaces all `-1`
sentinel values with inherited concrete values:

- **Typography**: `font_size_y2label` inherits from `font_size_ylabel`;
  `font_size_legend2` and `font_size_legend3` inherit from `font_size_legend`.
- **Legend spacing**: secondary and tertiary legend spacing inherits from the
  primary legend where values are `-1.0`.
- **Axes**: `y2label_pad` and `y2tick_pad` inherit from their primary-axis
  counterparts.

---

## Download Section UI

`render_download_section()` in
`src/web/pages/ui/plotting/download_section.py` provides the download
controls. It renders inside a collapsed `st.expander` and branches on the
active rendering engine.

### Plotly path

`_render_plotly_download()` offers format pills for HTML, PNG, SVG, and PDF
(default: HTML). Byte generation dispatches to `plotly_download_bytes()`:

- **HTML**: `fig.to_html(include_plotlyjs=True, full_html=True)` encoded to
  UTF-8. Produces a self-contained interactive file.
- **PNG / SVG / PDF**: `fig.to_image(format=fmt, width=700, height=400, scale=2)`
  via Kaleido v1.

### Matplotlib path

`_render_mpl_download()` reads the matplotlib figure from
`st.session_state[f"plot.{plot_id}.mpl_fig"]` and offers format pills for PDF,
PGF, PNG, and SVG (default: PDF). Byte generation dispatches to
`matplotlib_download_bytes()`:

- **PDF**: `fig.savefig(buf, format="pdf", dpi=dpi, bbox_inches="tight")`
- **PGF**: Uses `plt.rc_context` to set `pgf.texsystem` to XeLaTeX and inject
  the preset preamble, then `fig.savefig(buf, format="pgf", backend="pgf")`.
  If PGF fails due to raster content (e.g., heatmaps), falls back to PDF with
  a user warning.
- **PNG**: Disables `text.usetex` to avoid dvipng dependency issues, uses the
  `agg` backend.
- **SVG**: `fig.savefig(buf, format="svg", bbox_inches="tight")`

Both paths finish with an `st.download_button` using the appropriate MIME type
and file extension.

---

## Export Formats

### Format support matrix

| Format | Plotly | Matplotlib | Method | Notes |
|--------|:------:|:----------:|--------|-------|
| PNG | Yes | Yes | `to_image()` / `savefig(backend="agg")` | Raster; scale for Plotly, DPI for Matplotlib |
| SVG | Yes | Yes | `to_image()` / `savefig()` | Vector; text as SVG elements |
| PDF | Yes | Yes | `to_image()` / `savefig(bbox_inches="tight")` | Vector |
| HTML | Yes | No | `to_html(include_plotlyjs=True)` | Interactive; self-contained |
| PGF | No | Yes | `savefig(format="pgf", backend="pgf")` | Native LaTeX commands |

### MIME types and extensions

| Format | MIME | Extension |
|--------|------|-----------|
| PNG | `image/png` | `.png` |
| SVG | `image/svg+xml` | `.svg` |
| PDF | `application/pdf` | `.pdf` |
| HTML | `text/html` | `.html` |
| PGF | `application/x-pgf` | `.pgf` |

### Recommended formats by use case

| Use case | Format | Engine | Reason |
|----------|--------|--------|--------|
| LaTeX paper via `\input{}` | PGF | Matplotlib | Native LaTeX; fonts auto-match document |
| LaTeX paper via `\includegraphics{}` | PDF | Matplotlib | Vector; tight bounding box |
| High-DPI print (Nature, Science) | PDF or PNG@600 | Matplotlib | Preset sets DPI to 600 |
| Interactive web report | HTML | Plotly | Bundled plotly.js; zoom/pan/hover |
| Quick screenshot | PNG | Either | Widely compatible raster |
| Editing in Illustrator/Inkscape | SVG | Either | Editable vector paths |

---

## Engine-Specific Export

### Plotly export (Kaleido v1)

The Plotly path uses `plotly_download_bytes()` with these defaults:

| Parameter | Default |
|-----------|---------|
| Width | 700 px |
| Height | 400 px |
| Scale | 2x |
| Default format | HTML |

For PNG, the effective resolution is `width * scale` by `height * scale`
(1400 x 800 pixels at default settings). For vector formats (SVG, PDF),
the scale parameter has no geometric effect but is accepted by the API.

The Plotly modebar also includes a built-in "Download as SVG" button
configured via `toImageButtonOptions` in the chart display component.

### Matplotlib export (savefig)

The Matplotlib path uses `matplotlib_download_bytes()` with these defaults:

| Parameter | Default |
|-----------|---------|
| DPI | 300 (from preset) |
| Default format | PDF |

PGF export is the preferred format for LaTeX papers. The export configures
XeLaTeX as the TeX system and injects the preset's `latex_extra_preamble`
into the PGF rc context. The `pgf.rcfonts` flag is set to `True` so that
matplotlib's font settings carry through to the PGF output.

When PGF export fails -- typically because the figure contains raster
elements like heatmaps that cannot be expressed as LaTeX drawing commands --
the system automatically falls back to PDF and displays a warning to the
user.

The matplotlib figure lifecycle is managed through `st.session_state`:
the figure is stored at key `plot.{plot_id}.mpl_fig` after rendering and
explicitly closed with `plt.close()` on the next render cycle to prevent
memory leaks.

### Adding a new export format

To add a new export format:

1. Add the format string, MIME type, and file extension to the appropriate
   dictionaries in `download_section.py` (`_FORMAT_MIME` / `_FORMAT_EXT` for
   Plotly, `_MPL_FORMAT_MIME` / `_MPL_FORMAT_EXT` for Matplotlib).
2. Update the `Literal` type alias (`PlotlyFormat` or `MatplotlibFormat`).
3. Add a branch in `plotly_download_bytes()` or `matplotlib_download_bytes()`
   that produces bytes for the new format.
4. The format will automatically appear in the UI format pills.

---

## See Also

- `src/core/models/visualization/figure_config.py` -- `FigureConfig`,
  `DimensionConfig`, and `MarginsConfig` dataclasses
- `src/core/models/visualization/typography_config.py` -- `TypographyConfig`
  with sentinel inheritance chain
- `src/core/services/visualization/config_resolver.py` -- `resolve_config()`
  sentinel resolution logic
- `src/web/rendering/config_builder.py` -- `PresetSpecBuilder.from_preset()`
  and `ConfigSpecBuilder.from_config()`
- `src/web/pages/ui/plotting/settings_pills.py` -- `render_preset_pills()`
  preset selector UI component
- `src/web/components/common/chart_display.py` -- `ChartDisplayComponent` that
  wires the download section into chart rendering
- `src/web/pages/ui/plotting/plot_service.py` -- `PlotService.export_plot_to_file()`
  for programmatic batch export
