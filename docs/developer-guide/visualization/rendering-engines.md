---
title: "Rendering Engines -- Dual-Engine Architecture"
parent: Visualization
grand_parent: Developer Guide
nav_order: 2
---

# Rendering Engines -- Dual-Engine Architecture

This guide documents the rendering layer of RING-5 Unified Engine v2: the
dual-engine system that translates an engine-agnostic `FigureConfig` into
either interactive Plotly figures or publication-quality Matplotlib figures.

## 1. Overview

The rendering system is built around one core idea: **write styling once,
render everywhere**. Plot types produce a `TraceBuildResult` containing
engine-agnostic `TraceConfig` dataclasses. UI widgets produce a flat config
dictionary. Three builder classes convert these inputs into a single
`FigureConfig` dataclass tree -- the only styling specification consumed by
both rendering engines.

The two engines serve different purposes:

- **Plotly** -- Interactive exploration. Supports zoom, pan, hover tooltips,
  editable legends, and drawing tools. Output is an HTML/JS figure rendered
  in the browser.
- **Matplotlib** -- Publication-quality output. Supports LaTeX math mode,
  PGF/TikZ export, bold typography controls, and precise label positioning.
  Output is a static image rendered via `st.pyplot()`.

Both engines are stateless: every method on the connector classes is a
`@staticmethod`. The `FigureConfig` carries all context, so no mutable
state leaks between renders.

### Key Source Files

| File | Purpose |
|------|---------|
| `src/web/rendering/_connector_protocol.py` | Pipeline order contract |
| `src/web/rendering/engine_manager.py` | Engine state in Streamlit session |
| `src/web/rendering/plotly_connector.py` | `FigureConfig` to Plotly `go.Figure` |
| `src/web/rendering/matplotlib_connector.py` | `FigureConfig` to matplotlib Figure/Axes |
| `src/web/rendering/trace_to_plotly.py` | `TraceConfig` to Plotly traces |
| `src/web/rendering/matplotlib_trace_renderer.py` | `TraceConfig` to matplotlib artists |
| `src/web/rendering/config_builder.py` | Three builders: widgets/Plotly/preset to `FigureConfig` |
| `src/web/rendering/_heatmap_utils.py` | Shared heatmap contrast and range utilities |
| `src/web/rendering/_render_result.py` | `MatplotlibRenderResult` bridge dataclass |
| `src/web/rendering/widgets/widget_def.py` | Declarative widget definition hierarchy |
| `src/web/rendering/widgets/widget_renderer.py` | Widget definition to Streamlit widget to config dict |

---

## 2. ConnectorProtocol -- STYLING_PIPELINE_ORDER

Both connectors must apply styling operations in the same canonical order,
defined by the `STYLING_PIPELINE_ORDER` tuple in `_connector_protocol.py`.
This guarantees visual consistency across engines: when a user switches from
Plotly to Matplotlib, overlapping features produce identical visual results.

```python
STYLING_PIPELINE_ORDER: tuple[str, ...] = (
    "backgrounds",       # 1.  Paper and plot area background colors
    "font_family",       # 2.  Global font family (rcParams / layout.font)
    "color_palette",     # 3.  Colorway / property-cycle assignment
    "title",             # 4.  Figure title with typography
    "axis_labels",       # 5.  X, Y, Y2 axis label text and font
    "axis_ticks",        # 6.  Tick positioning, rotation, padding
    "axis_ranges",       # 7.  xlim/ylim, log scale, axis margin
    "axis_colors",       # 8.  Tick/line colors, spine visibility
    "grids",             # 9.  Grid lines, color, dash style
    "legends",           # 10. Legend position, spacing, multi-legend
    "reference_lines",   # 11. Horizontal/vertical reference lines
    "data_labels",       # 12. Bar/point value annotations
    "annotations",       # 13. Freeform text annotations
    "separators",        # 14. Group separator vertical lines
    "hatching",          # 15. Bar hatching patterns
    "margins",           # 16. Figure margins (subplots_adjust / layout.margin)
)
```

The ordering matters because later steps may depend on geometry established by
earlier steps. For example, axis ranges (step 7) must be set before reference
lines (step 11) can be positioned correctly, and margins (step 16) must come
last because `subplots_adjust` can shift elements placed in earlier steps.

Any new rendering connector must apply styles in this order to remain
compatible with the existing config resolution and widget systems.

---

## 3. Engine Manager

**Source:** `src/web/rendering/engine_manager.py`

The `EngineManager` is a fully static class that mediates all engine state
through Streamlit session state. No instance is ever created.

```python
EngineMode = Literal["plotly", "matplotlib"]

class EngineManager:
    STATE_KEY: str = "ring5_engine_mode"
    DEFAULT_MODE: EngineMode = "plotly"

    @staticmethod
    def get_engine() -> EngineMode: ...
    @staticmethod
    def set_engine(mode: EngineMode) -> None: ...
    @staticmethod
    def is_plotly() -> bool: ...
    @staticmethod
    def is_matplotlib() -> bool: ...
```

### Design details

- **Namespaced key** (`ring5_engine_mode`) avoids collisions with other
  Streamlit widgets or session state entries.
- **Idempotent setter** -- `set_engine()` only writes when the value actually
  changes, preventing unnecessary Streamlit reruns.
- **Validation** -- A `frozenset` (`_VALID_MODES`) guards against invalid
  values at both read and write time. `set_engine()` raises `ValueError`
  for unrecognized modes.

### Engine selection flow

Engine selection is **per-plot**, not global. The `ChartDisplayComponent`
renders a `st.pills()` widget keyed by `f"engine_selector_{plot_id}"`. Each
plot instance can independently use a different engine. The controller reads
the selection and branches to either `render_plotly_chart()` or
`render_matplotlib_chart()`.

---

## 4. Plotly Connector

**Source:** `src/web/rendering/plotly_connector.py`

### Class: FigureSpecToPlotly

Stateless translator. All methods are `@staticmethod`. The `FigureConfig`
must be **resolved** (no `-1` sentinels) before calling.

```python
@staticmethod
def apply(spec: FigureConfig, fig: go.Figure) -> go.Figure
```

Applies the full `FigureConfig` to a Plotly figure **in place** and returns
it. The pipeline executes 18 steps:

```
 1. _apply_dimensions       10. _apply_hovermode
 2. _apply_backgrounds      11. _apply_font_family
 3. _apply_title             12. _apply_reference_lines
 4. _apply_xaxis             13. _apply_data_labels
 5. _apply_yaxis             14. _apply_series_styling
 6. _apply_y2axis            15. _apply_trace_overrides
 7. _apply_legends           16. _apply_separator_lines
 8. _apply_heatmap_colorbars 17. _apply_stripes
 9. _apply_color_palette     18. _apply_axis_colors
```

### Key method behaviors

**Dimensions.** Converts `DimensionConfig` inches to pixels
(`width_px = int(dims.width * dpi)`). Sets `fig.update_layout(width, height,
margin, bargap, bargroupgap)`.

**Color palette.** Sets `colorway` on the layout for future traces. For
existing traces, assigns `marker.color` and `line.color` from the palette
using modular indexing, skipping heatmap traces and traces that already have
an explicit `marker.color` set by the plot factory.

**Legends.** The first legend maps to `fig.update_layout(legend=...)`.
Subsequent visible legends map to `legend2`, `legend3`, etc. Multi-column
layout uses `entrywidthmode="fraction"` with `entrywidth = 1.0 / ncol`.

**Heatmap colorbars.** Reads `ColorbarConfig` from the primary legend. In
shared mode, all heatmap traces receive the same `zmin`/`zmax` and only the
last trace displays the colorbar. In individual mode, each trace computes its
own nice range via `compute_nice_range()`.

**Axis colors.** Uses Plotly's `mirror` property to copy bottom/left axis
lines to top/right. When mirror is insufficient (primary axis line hidden but
opposite line wanted), falls back to paper-referenced line shapes.

**Trace overrides.** Maps `spec.trace_overrides` (keyed by original trace
name) to per-trace mutations: color, symbol, marker size, line width,
hatching pattern, and display-name rename.

---

## 5. Matplotlib Connector

**Source:** `src/web/rendering/matplotlib_connector.py`

### Class: FigureSpecToMatplotlib

Stateless translator. Matplotlib is imported lazily inside methods to avoid
import errors when the library is not installed.

```python
@staticmethod
def apply(
    spec: FigureConfig,
    ax: Axes,
    render_result: MatplotlibRenderResult | None = None,
) -> None

@staticmethod
def create_figure(spec: FigureConfig) -> tuple[Figure, Axes]

@staticmethod
def create_multi_figure(spec: FigureConfig, nrows: int) -> tuple[Figure, list[Axes]]
```

The `apply()` method executes 16 steps matching `STYLING_PIPELINE_ORDER`,
plus a conditional colorbar step when heatmap data is present.

### Figure creation and the dpi=1 convention

When the UI produces a config dict with pixel values (`width=800`), the
`ConfigSpecBuilder` sets `dpi=1` as a passthrough convention.
`create_figure()` detects this and normalizes to inches using 96 DPI:

```python
if dims.dpi <= 1:
    render_dpi = 96
    width_in = dims.width / render_dpi   # 800 / 96 = 8.33 inches
    height_in = dims.height / render_dpi
```

Without this normalization, passing raw pixel values as matplotlib inches
would produce an image exceeding 100,000 pixels and cause a `MemoryError`.

### Engine-specific behaviors

Several features behave differently in Matplotlib than in Plotly:

- **Bold typography.** Matplotlib supports `fontweight="bold"` on titles and
  labels. Plotly has limited bold support (only via HTML `<b>` tags in some
  contexts).
- **Y-label vertical shift.** Matplotlib uses `ax.yaxis.set_label_coords()`
  for precise vertical repositioning via `title_vshift`. Plotly only supports
  `standoff` (horizontal distance from the axis).
- **Spine-based axis lines.** Matplotlib controls axis line visibility
  through the `spines` system (`ax.spines["bottom"].set_visible()`), while
  Plotly uses `showline`/`mirror` properties.
- **CSS RGB conversion.** Plotly qualitative palettes return `rgb(r,g,b)`
  strings that Matplotlib cannot parse. The `_css_rgb_to_hex()` utility
  normalizes these to `#rrggbb` format.
- **LaTeX escaping.** The `_escape_latex()` method escapes special characters
  (`&`, `%`, `$`, `#`, `_`, `{`, `}`) while preserving existing LaTeX
  commands like `\textbf`.

---

## 6. Trace Rendering

Trace rendering converts engine-agnostic `TraceConfig` dataclasses into
engine-specific drawing calls. This is a forward-direction pipeline: plot
types produce `TraceBuildResult`, and the renderers consume it directly.
There is no reverse extraction from an existing figure.

### 6.1 Plotly Trace Converter

**Source:** `src/web/rendering/trace_to_plotly.py`

```python
def traces_to_plotly(result: TraceBuildResult) -> go.Figure
```

Handles three layout modes based on trace content:

1. **Multi-heatmap** -- All traces are `HeatmapTraceConfig` (more than one).
   Creates `make_subplots(rows=N, cols=1)` with vertical spacing and subplot
   titles.
2. **Secondary Y** -- At least one trace has `yaxis="y2"`. Creates
   `make_subplots(specs=[[{"secondary_y": True}]])`.
3. **Standard** -- Plain `go.Figure()`.

The trace dispatch table maps each `TraceConfig` subclass to its Plotly
equivalent:

| TraceConfig subclass | Plotly trace type | Key details |
|---------------------|-------------------|-------------|
| `BarTraceConfig` | `go.Bar` | Grouped positioning, error bars, custom data |
| `LineTraceConfig` | `go.Scatter` (lines mode) | Dash, markers, fill for area charts |
| `ScatterTraceConfig` | `go.Scatter` (markers mode) | Bubble sizes, colorscale |
| `HistogramTraceConfig` | `go.Histogram` | Binning, normalization, cumulative |
| `HeatmapTraceConfig` | `go.Heatmap` | Cell annotations via layout, auto-contrast |
| `TraceConfig` (base) | `go.Bar` (fallback) | Minimal bar rendering |

Heatmap cell-value annotations are rendered as layout annotations (not
`texttemplate`) using `_add_heatmap_annotations()`. This guarantees text
renders above cells with per-cell auto-contrast coloring (white text on dark
cells, black on light cells via `is_dark_cell()`).

### 6.2 Matplotlib Trace Renderer

**Source:** `src/web/rendering/matplotlib_trace_renderer.py`

```python
class MatplotlibTraceRenderer:
    @staticmethod
    def render(
        traces: Sequence[TraceConfig],
        ax: Axes,
        barmode: str = "group",
        palette_colors: Sequence[str] | None = None,
        ...
    ) -> MatplotlibRenderResult
```

The renderer has **no Plotly dependency**. It draws data only; all
layout/styling is handled by `FigureSpecToMatplotlib.apply()`.

**Secondary Y-axis.** When any trace has `yaxis="y2"`, creates a twin axis
via `ax.twinx()` and stores it as `ax._ring5_twin`.

**Heatmaps.** Uses `ax.pcolormesh()` instead of `ax.imshow()` for **pure
vector graphics** output compatible with PGF/TikZ LaTeX export. Cell edges
use `np.arange(n + 1)` with `shading="flat"`. The y-axis is inverted
(`ax.invert_yaxis()`) to follow matrix convention (row 0 at top).

**Bar positioning.** For grouped bars, computes offsets around integer ticks:

```python
group_width = max(0.05, 1.0 - bargap)
bar_w = group_width / n_traces * (1.0 - bargroupgap)
step = group_width / n_traces
offset = -(n_traces - 1) * step / 2 + bar_idx * step
```

**Colorscale mapping.** A 22-entry dictionary maps Plotly colorscale names
(lowercase) to Matplotlib equivalents (e.g., `"blues"` to `"Blues"`,
`"rdbu"` to `"RdBu"`). List-based colorscales (`[[pos, hex], ...]`) create
`LinearSegmentedColormap.from_list()`.

### MatplotlibRenderResult

The `MatplotlibRenderResult` dataclass bridges trace rendering and style
application:

```python
@dataclass
class MatplotlibRenderResult:
    trace_count: int = 0
    heatmap_col_labels: list[str] | None = None
    heatmap_row_labels: list[str] | None = None
    heatmap_image: Any = None   # pcolormesh mappable for colorbar
```

The Plotly engine does not need an equivalent because `go.Figure` serves as
both render target and styling target. Matplotlib requires this bridge because
trace rendering (`render()`) and style application (`apply()`) are separate
phases that operate on the same `Axes` object.

---

## 7. Config Builder System

**Source:** `src/web/rendering/config_builder.py`

Three builder classes construct `FigureConfig` from different input sources.

### 7.1 ConfigSpecBuilder -- UI Widgets to FigureConfig

```python
class ConfigSpecBuilder:
    @staticmethod
    def from_config(config: dict[str, Any], plot_type: str = "") -> FigureConfig
```

The primary builder for the interactive UI path. Reads the flat `config` dict
produced by Streamlit widgets and constructs a typed `FigureConfig`.

Key design: uses `dpi=1` as a pixel-passthrough convention. Width and height
in the config dict are pixel values (e.g., `800`). By setting `dpi=1`, these
pass through `FigureConfig` without conversion. Each connector handles the
actual unit conversion.

The builder constructs all major config sections from prefixed keys:
dimensions, typography, axes (X, Y, Y2), up to three legends, data labels,
reference lines, series styles, trace overrides, color palette, and feature
flags (error bars, stripes, hovermode, barmode).

### 7.2 PlotlyFigureSpecBuilder -- Plotly Figure to FigureConfig

```python
class PlotlyFigureSpecBuilder:
    @staticmethod
    def from_plotly(fig: go.Figure, config: dict[str, Any]) -> FigureConfig

    @staticmethod
    def enrich_from_plotly(spec: FigureConfig, fig: go.Figure) -> None
```

`from_plotly()` extracts state from an existing Plotly figure for
round-tripping. `enrich_from_plotly()` merges computed layout data into an
existing spec in place -- transferring tick positions, annotation objects,
barmode, and tertiary legend positioning that `ConfigSpecBuilder` cannot
capture because this data is set programmatically in `create_figure()`
methods rather than stored in the config dict.

### 7.3 PresetSpecBuilder -- LaTeX Preset to FigureConfig

```python
class PresetSpecBuilder:
    @staticmethod
    def from_preset(preset: dict[str, Any]) -> FigureConfig
```

Builds a `FigureConfig` from a publication-specific preset dictionary.
Each preset defines 40+ keys covering dimensions (width/height in inches,
DPI), all typography sizes and bold flags, axis tick positioning, legend
spacing parameters, separator styling, font family, and
`latex_extra_preamble`.

The `PresetApplicator` overlays a preset onto an existing spec using
`dataclasses.replace()`. It overrides layout-related fields (dimensions,
typography, axes, legends, separator, font) while preserving data-derived
fields (title, backgrounds, data labels, series styles, trace overrides,
color palette, annotations).

---

## 8. Widget Definition System

**Source:** `src/web/rendering/widgets/widget_def.py` and
`src/web/rendering/widgets/widget_renderer.py`

### WidgetDef hierarchy

The widget system uses frozen dataclasses to declare UI controls:

```
WidgetDef (base)
  key: str           -- flat-config key and Streamlit widget key suffix
  label: str         -- human-readable label
  default: Any       -- default value
  spec_path: str     -- mapping to FigureConfig field path
  |
  +-- NumberWidgetDef    -> st.number_input
  +-- SliderWidgetDef    -> st.slider
  +-- SelectWidgetDef    -> st.selectbox
  +-- CheckboxWidgetDef  -> st.checkbox
  +-- ColorWidgetDef     -> st.color_picker
  +-- TextWidgetDef      -> st.text_input
```

A `WidgetSection` groups related widgets under a collapsible expander with an
ID, label, optional icon, and initial collapse state.

### WidgetRenderer

The `WidgetRenderer` class renders `WidgetSection` definitions into actual
Streamlit widgets and collects their return values into a flat dictionary:

```python
renderer = WidgetRenderer(key_prefix="plot_3_")
config = renderer.render_sections(ALL_SECTIONS, saved_config)
# config == {"width": 800, "height": 500, "title_font_size": 14, ...}
```

The key prefix (e.g., `"plot_3_"`) is prepended to each widget key to avoid
`DuplicateWidgetID` errors when multiple plots coexist. The renderer lazily
imports `streamlit` so the module can be imported and tested without a
running Streamlit server.

Default resolution follows a two-tier pattern: `saved_config.get(key,
widget_def.default)` -- use the saved config value if it exists, otherwise
fall back to the widget definition's default.

---

## 9. Feature Parity Matrix

| Feature | Plotly | Matplotlib |
|---------|--------|------------|
| **Interactivity** | | |
| Zoom/pan | Yes (native) | No (static image) |
| Hover tooltips | Yes | No |
| Editable legends (drag) | Yes | No |
| Drawing tools | Yes | No |
| **Output formats** | | |
| HTML interactive | Yes | No |
| PNG raster | Yes | Yes |
| SVG vector | Yes | Yes |
| PDF vector | Yes | Yes |
| PGF/TikZ LaTeX | No | Yes |
| **Chart types** | | |
| Bar charts | `go.Bar` | `ax.bar()` |
| Line charts | `go.Scatter` (lines) | `ax.plot()` |
| Scatter plots | `go.Scatter` (markers) | `ax.scatter()` |
| Histograms | `go.Histogram` | `ax.hist()` |
| Heatmaps | `go.Heatmap` (raster) | `ax.pcolormesh()` (vector) |
| Multi-heatmap subplots | `make_subplots(rows=N)` | `create_multi_figure(nrows)` |
| Secondary Y-axis | `secondary_y=True` | `ax.twinx()` |
| Error bars | `error_y` dict | Not yet implemented |
| Fill/area charts | `trace.fill` | Not yet implemented |
| Cumulative histograms | `cumulative.enabled` | Not yet implemented |
| **Typography** | | |
| Bold title/labels | Limited (HTML tags) | Yes (`fontweight`) |
| LaTeX math mode | No | Yes |
| Custom font family | Yes (CSS fonts) | Yes (rcParams) |
| Y-label vertical shift | No (standoff only) | Yes (`set_label_coords`) |
| **Styling** | | |
| Color palette | `colorway` + per-trace | `set_prop_cycle` + per-trace |
| Hatching patterns | `marker.pattern.shape` | `patch.set_hatch()` |
| Data labels | `texttemplate` | `ax.bar_label()` |
| Reference lines | `add_hline`/`add_vline` | `axhline`/`axvline` |
| Separator lines | `add_shape` | `ax.plot` + blended transform |
| Grid styling | `gridcolor`/`griddash` | `xaxis.grid()` |
| Axis line visibility | `showline` + `mirror` | Spine visibility |
| **Legend** | | |
| Multi-column | `entrywidth` fraction | `ncol` parameter |
| Multi-legend (up to 3) | `legend`/`legend2`/`legend3` | primary/secondary (twin)/tertiary |
| Custom positioning | `x`/`y` + anchors | `bbox_to_anchor` + `loc` |
| **Colorbar** | | |
| Shared mode | `showscale` on last trace | Single `fig.colorbar` for all axes |
| Individual mode | Per-trace colorbar | Per-axes colorbar |
| Nice range rounding | `compute_nice_range()` | `compute_nice_range()` |
| **Memory** | | |
| Figure cleanup | Garbage collected | Explicit `plt.close()` required |

---

## 10. End-to-End Rendering Pipeline

The complete rendering flow from user interaction to displayed chart:

1. **Widget collection.** `WidgetRenderer.render_sections()` renders
   `WidgetSection` definitions into Streamlit widgets, collecting values
   into a flat `dict[str, Any]`.

2. **Config building.** `ConfigSpecBuilder.from_config(config, plot_type)`
   constructs a `FigureConfig` from the widget values with `dpi=1` pixel
   passthrough.

3. **Plotly enrichment.** `PlotlyFigureSpecBuilder.enrich_from_plotly(spec,
   fig)` merges computed layout data (tick positions, annotations, barmode,
   tertiary legend) from the Plotly figure into the spec.

4. **Preset application (optional).** If a LaTeX export preset is selected,
   `PresetApplicator.apply(spec, preset_dict)` overlays publication-quality
   settings while preserving data-derived fields.

5. **Sentinel resolution.** `resolve_config(spec)` replaces all `-1`
   sentinel values with inherited parent values. After this step, connectors
   never see `-1`.

6. **Engine selection.** `ChartDisplayComponent.render_engine_selector()`
   renders the pills UI. The controller branches on the selection.

7. **Plotly path:**
   - `traces_to_plotly(result)` builds an unstyled `go.Figure` from
     `TraceBuildResult`.
   - `FigureSpecToPlotly.apply(spec, fig)` applies the 18-step pipeline.
   - `interactive_plotly_chart(fig, config)` renders the custom Plotly
     component with relayout event capture.

8. **Matplotlib path:**
   - `FigureSpecToMatplotlib.create_figure(spec)` creates a blank figure
     with correct dimensions.
   - `MatplotlibTraceRenderer.render(traces, ax, ...)` draws all traces,
     returning a `MatplotlibRenderResult`.
   - `FigureSpecToMatplotlib.apply(spec, ax, render_result)` applies the
     16-step pipeline plus conditional colorbar.
   - `st.pyplot(fig)` renders the static figure in Streamlit.

9. **Download.** `render_download_section()` provides export buttons for
   the rendered figure.

---

## 11. See Also

- **FigureConfig model:** `src/core/models/visualization/figure_config.py`
  -- the dataclass tree that both connectors consume.
- **Config resolver:** `src/core/services/visualization/config_resolver.py`
  -- sentinel resolution service (`resolve_config()`).
- **Trace models:** `src/core/models/visualization/trace_config.py` -- the
  `TraceConfig` hierarchy that trace renderers consume.
- **Chart display component:** `src/web/components/common/chart_display.py`
  -- the Streamlit integration that orchestrates rendering.
- **Preset system:** `src/web/rendering/preset_applicator.py` and
  `src/web/pages/ui/plotting/export/presets/latex_presets.json` -- the 13
  venue-specific publication presets.
- **Palette service:** `src/core/services/visualization/palette_service.py`
  -- resolves palette names to hex color lists.
- **Interactive plot component:**
  `src/web/components/plotting/interactive_plot.py` -- custom Streamlit
  component wrapping Plotly with relayout event capture.
