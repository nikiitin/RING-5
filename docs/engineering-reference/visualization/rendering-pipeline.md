---
title: "Rendering Pipeline"
parent: Visualization
grand_parent: Engineering Reference
nav_order: 2
---

# Rendering Pipeline

> **Scope**: End-to-end flow from `FigureConfig` to rendered figure, covering both Plotly and Matplotlib engines.
> **Key files**: `src/web/rendering/plotly_connector.py`, `src/web/rendering/matplotlib_connector.py`, `src/web/rendering/trace_to_plotly.py`, `src/web/rendering/matplotlib_trace_renderer.py`, `src/web/rendering/config_builder.py`

---

## Pipeline Overview (ASCII)

```
UI Widgets (Streamlit)
       |
       v  Dict[str, Any]
ConfigSpecBuilder.from_config()        config_builder.py:362
       |
       v  FigureConfig (with sentinels)
PlotlyFigureSpecBuilder                config_builder.py:112
  .enrich_from_plotly(spec, fig)       (merges tick positions, annotations)
       |
       v  FigureConfig (enriched)
resolve_config(spec)                   config_resolver.py:60
       |
       v  FigureConfig (all sentinels resolved)
       |
       +---------- EngineManager.get_engine() ----------+
       |                                                |
       v  "plotly"                              "matplotlib"  v
+------------------+                    +----------------------+
| traces_to_plotly |                    | create_figure(spec)  |
|   (TraceBuildResult                   |   -> (Figure, Axes)  |
|    -> go.Figure)                      |                      |
+--------+---------+                    +----------+-----------+
         |                                         |
         v  unstyled go.Figure             styled  v
+------------------+                    +----------------------+
| FigureSpecToPlotly                    | MatplotlibTraceRenderer
|   .apply(spec,fig)                    |   .render(traces, ax)|
|   18-step pipeline                    |   -> RenderResult    |
+--------+---------+                    +----------+-----------+
         |                                         |
         v  styled go.Figure                       v
+------------------+                    +----------------------+
| interactive_     |                    | FigureSpecToMatplotlib
| plotly_chart()   |                    |   .apply(spec,ax,rr) |
+--------+---------+                    |   16-step pipeline   |
         |                              +----------+-----------+
         v                                         |
   Streamlit display                     st.pyplot(fig)
```

---

## Config Builders

| Builder | Source | Output | File:Line |
|---------|--------|--------|-----------|
| `ConfigSpecBuilder.from_config()` | UI widget dict | `FigureConfig` (dpi=1 px-passthrough) | `config_builder.py:362` |
| `PlotlyFigureSpecBuilder.from_plotly()` | `go.Figure` + config dict | `FigureConfig` (dpi=96) | `config_builder.py:51` |

### ConfigSpecBuilder Build Sections

| Step | Config Keys Read | FigureConfig Field Built |
|------|-----------------|-------------------------|
| 1. Dimensions | `width`, `height`, `margin_*`, `bargap`, `bargroupgap` | `dimensions: DimensionConfig` (dpi=1) |
| 2. Typography | `title_font_size`, `xaxis_title_font_size`, `yaxis_title_font_size`, `xaxis_tickfont_size`, `yaxis_tickfont_size`, `legend_font_size`, `text_font_size` | `typography: TypographyConfig` |
| 3. X-Axis | `xlabel`/`xaxis_title`, `xaxis_tickangle`, `range_x`, `xaxis_order`, `xaxis_labels`, `show_x_grid`, `grid_color`, `show_xtick_marks`, `xtick_dash`, `axis_color`, `x_axis_line_*` | `axes.x: AxisConfig` |
| 4. Y-Axis | `ylabel`/`yaxis_title`, `yaxis_tickangle`, `range_y`, `yaxis_dtick`, `show_y_grid`, `yaxis_title_standoff`, `yaxis_title_vshift` | `axes.y: AxisConfig` |
| 5. Axes Extra | `group_label_*`, `top_axis_line_*`, `right_axis_line_*` | `axes: AxesConfig` |
| 6. Legends | `legend_*` (primary), `legend2_*` (secondary), `legend3_*` (tertiary) | `legends: list[LegendConfig]` |
| 7. Data Labels | `show_values`, `text_*` keys | `data_labels: DataLabelConfig` |
| 8. Reference Lines | `reference_line_*` keys | `reference_lines` |
| 9. Series Styles | `bar_border_width`, `marker_size`, `line_width` | `series_styles` |
| 10. Trace Overrides | `series_styles` dict | `trace_overrides` |
| 11. Color Palette | `color_palette` (name -> hex via `resolve_palette()`) | `color_palette` |
| 12. Flags | `show_error_bars`, `enable_stripes`, `hovermode`, `barmode` | Direct fields |

**Key design**: `dpi=1` means widget pixel values (e.g. `width=800`) pass through FigureConfig without conversion. (`800 / 1 = 800` inches conceptually, `800 * 1 = 800` px when connectors multiply.)

---

## STYLING_PIPELINE_ORDER

Defined in `src/web/rendering/_connector_protocol.py` (lines 1-29). Both connectors MUST apply styles in this order:

```
Step  Name              Plotly Method                     Matplotlib Method
----  ----              -------------                     -----------------
 1    backgrounds       _apply_backgrounds()              _apply_backgrounds()
 2    font_family       _apply_font_family()              _apply_font_family()
 3    color_palette     _apply_color_palette()            _apply_color_palette()
 4    title             _apply_title()                    _apply_title()
 5    axis_labels       _apply_xaxis/_yaxis/_y2axis       _apply_axis_labels()
 6    axis_ticks        (within axis methods)             _apply_axis_ticks()
 7    axis_ranges       (within axis methods)             _apply_axis_ranges()
 8    axis_colors       _apply_axis_colors()              _apply_axis_colors()
 9    grids             (within axis methods)             _apply_grids()
10    legends           _apply_legends()                  _apply_legends()
11    reference_lines   _apply_reference_lines()          _apply_reference_lines()
12    data_labels       _apply_data_labels()              _apply_data_labels()
13    annotations       (via trace_to_plotly)             _apply_annotations()
14    separators        _apply_separator_lines()          _apply_separators()
15    hatching          _apply_stripes()                  _apply_hatching()
16    margins           _apply_dimensions()               _apply_margins()
```

---

## Plotly Connector: FigureSpecToPlotly

**File**: `src/web/rendering/plotly_connector.py` (~890 lines)
- All methods are `@staticmethod` -- fully stateless
- Expects **resolved** FigureConfig (no -1 sentinels)

### apply() Execution (18 steps)

```
 1. _apply_dimensions(spec, fig)       Width/height px, margins, bargap
 2. _apply_backgrounds(spec, fig)      paper_bgcolor, plot_bgcolor
 3. _apply_title(spec, fig)            Title text + font size
 4. _apply_xaxis(spec, fig)            X-axis: label, ticks, range, grid, aliases
 5. _apply_yaxis(spec, fig)            Y-axis: same pattern, selector=overlaying=None
 6. _apply_y2axis(spec, fig)           Y2-axis: overlaying="y", side="right"
 7. _apply_legends(spec, fig)          Up to 3 legends (legend, legend2, legend3)
 8. _apply_heatmap_colorbars(spec,fig) Colorbar: shared/individual, nice range
 9. _apply_color_palette(spec, fig)    colorway + per-trace marker.color
10. _apply_hovermode(spec, fig)        hovermode
11. _apply_font_family(spec, fig)      Global font.family
12. _apply_reference_lines(spec, fig)  add_hline / add_vline
13. _apply_data_labels(spec, fig)      texttemplate, textposition per trace
14. _apply_series_styling(spec, fig)   opacity, line.width, marker.size
15. _apply_trace_overrides(spec, fig)  Per-trace: color, symbol, display_name
16. _apply_separator_lines(spec, fig)  Vertical shapes between bar groups
17. _apply_stripes(spec, fig)          Hatching: marker.pattern.shape
18. _apply_axis_colors(spec, fig)      Tick colors, spine visibility, mirror
```

---

## Matplotlib Connector: FigureSpecToMatplotlib

**File**: `src/web/rendering/matplotlib_connector.py` (~1078 lines)
- All methods are `@staticmethod` -- fully stateless
- Matplotlib imported lazily inside methods

### Public API

```python
create_figure(spec) -> (Figure, Axes)          # Properly-sized blank figure
create_multi_figure(spec, nrows) -> (Figure, list[Axes])  # Stacked subplots
apply(spec, ax, render_result=None) -> None    # 16-step styling pipeline
apply_multi_heatmap_colorbars(spec, fig, axes_list, render_results) -> None
```

### apply() Execution (16 steps + conditional colorbar)

```
 1. _apply_backgrounds(spec, ax)       fig.patch + ax facecolor
 2. _apply_font_family(spec, ax)       rcParams["font.family"]
 3. _apply_color_palette(spec, ax)     set_prop_cycle (css_rgb -> hex)
 4. _apply_title(spec, ax)             set_title with fontweight
 5. _apply_axis_labels(spec, ax)       set_xlabel, set_ylabel, y2 label
 6. _apply_axis_ticks(spec, ax, rr)    tick_params, set_xticks, rotation, pad
 7. _apply_axis_ranges(spec, ax)       set_xlim, set_ylim, set_xscale
 8. _apply_axis_colors(spec, ax)       spine colors + visibility
 9. _apply_grids(spec, ax)             xaxis.grid, yaxis.grid + dash mapping
10. _apply_legends(spec, ax)           primary on ax, secondary on twinx ax
11. _apply_reference_lines(spec, ax)   axhline / axvline
12. _apply_data_labels(spec, ax)       ax.bar_label() for BarContainers
13. _apply_annotations(spec, ax)       ax.annotate with coordinate transforms
14. _apply_separators(spec, ax)        Vertical midpoint lines
15. _apply_hatching(spec, ax)          patch.set_hatch() on containers
16. _apply_margins(spec, ax)           subplots_adjust (px -> fraction)
-- conditional: _apply_colorbar(spec, ax, mappable)
```

### dpi=1 Convention in create_figure

```
if dpi <= 1:
    render_dpi = 96
    fig_w = width / 96    # pixel count -> inches at 96dpi
    fig_h = height / 96
else:
    render_dpi = dpi
    fig_w = width         # already inches
    fig_h = height
```

This prevents `MemoryError` from passing raw pixel values as matplotlib inches.

---

## Trace Rendering

### Plotly: traces_to_plotly()

**File**: `src/web/rendering/trace_to_plotly.py` (~492 lines)

```python
def traces_to_plotly(result: TraceBuildResult) -> go.Figure
```

**Layout modes** (auto-detected):
- Multi-heatmap: all traces are `HeatmapTraceConfig` and count > 1 -> `make_subplots(rows=N)`
- Secondary Y: any trace has `yaxis="y2"` -> `make_subplots(secondary_y=True)`
- Standard: plain `go.Figure()`

**Trace dispatch table**:

| TraceConfig Subclass | Plotly Type | Converter |
|---------------------|-------------|-----------|
| `BarTraceConfig` | `go.Bar` | `_bar_trace()` |
| `LineTraceConfig` | `go.Scatter` (lines/lines+markers) | `_line_trace()` |
| `ScatterTraceConfig` | `go.Scatter` (markers) | `_scatter_trace()` |
| `HistogramTraceConfig` | `go.Histogram` | `_histogram_trace()` |
| `HeatmapTraceConfig` | `go.Heatmap` | `_heatmap_trace()` |
| `TraceConfig` (base) | `go.Bar` (fallback) | `_bar_trace_from_base()` |

**Post-trace layout**: barmode, custom_x_ticks, shapes, annotations + layout_annotations, heatmap cell annotations, heatmap separator lines.

### Matplotlib: MatplotlibTraceRenderer

**File**: `src/web/rendering/matplotlib_trace_renderer.py` (~506 lines)

```python
@staticmethod
def render(traces, ax, barmode, palette_colors, bargap, bargroupgap,
           bar_border_width, heatmap_vmin, heatmap_vmax) -> MatplotlibRenderResult
```

**Drawing dispatch**:

| Method | matplotlib Call | Key Detail |
|--------|---------------|------------|
| `_draw_bar()` | `ax.bar()` | Pre-computed x_positions or categorical |
| `_draw_line()` | `ax.plot()` | Dash mapping, NaN sanitization |
| `_draw_scatter()` | `ax.scatter()` | `s=marker_size`, NaN cleanup |
| `_draw_histogram()` | `ax.hist()` | NaN per-value cleanup |
| `_draw_heatmap()` | `ax.pcolormesh()` | Vector (PGF-safe), inverted y-axis |

**Secondary Y**: if any trace has `yaxis="y2"`, creates `ax2 = ax.twinx()`.

**Bar positioning** (categorical):
- Stacked: all at integer positions, `group_width = max(0.05, 1.0 - bargap)`
- Grouped: offset around integer ticks with `bar_w = group_width / n_traces * (1.0 - bargroupgap)`

**Heatmap**: uses `pcolormesh()` (NOT `imshow()`) for pure vector graphics compatible with PGF/TikZ.

---

## MatplotlibRenderResult

**File**: `src/web/rendering/_render_result.py` (lines 1-17)

```python
@dataclass
class MatplotlibRenderResult:
    trace_count: int = 0
    heatmap_col_labels: list[str] | None = None
    heatmap_row_labels: list[str] | None = None
    heatmap_image: Any = None   # pcolormesh mappable for colorbar
```

Bridges trace rendering and style application:
- `trace_count` -- how many traces were drawn
- `heatmap_col_labels`/`heatmap_row_labels` -- for tick placement in `_apply_axis_ticks()`
- `heatmap_image` -- consumed by `_apply_colorbar()` to create the colorbar

---

## Engine Manager

**File**: `src/web/rendering/engine_manager.py` (~85 lines)

```python
EngineMode = Literal["plotly", "matplotlib"]

class EngineManager:          # Fully static, no instance state
    STATE_KEY = "ring5_engine_mode"
    DEFAULT_MODE = "plotly"

    get_engine() -> EngineMode
    set_engine(mode) -> None   # Idempotent
    is_plotly() -> bool
    is_matplotlib() -> bool
```

- Engine selection is **per-plot** (keyed by `plot_id` in widget key)
- State stored in `st.session_state`
- Validation via `frozenset` of valid modes

---

## Heatmap Shared Utilities

**File**: `src/web/rendering/_heatmap_utils.py` (~112 lines)

| Function | Purpose |
|----------|---------|
| `is_dark_cell(z, row, col) -> bool` | Auto-contrast: white text on dark cells |
| `compute_z_extent(traces) -> (min, max)` | Global z range across all heatmap traces |
| `compute_nice_range(min, max, nticks) -> (nice_min, nice_max, step)` | Rounded range for even tick spacing |

Used by both Plotly and Matplotlib rendering paths.

---

## Engine Feature Parity

| Feature | Plotly | Matplotlib |
|---------|--------|------------|
| Interactive zoom/pan | Yes | No |
| Hover tooltips | Yes | No |
| PGF/TikZ LaTeX output | No | Yes |
| Bold fontweight | Limited | Yes |
| LaTeX math mode | No | Yes |
| Error bars | Yes | No (not implemented) |
| Fill/area charts | Yes | No (not implemented) |
| Heatmap rendering | `go.Heatmap` | `pcolormesh` (vector) |
| Multi-legend (3) | legend/legend2/legend3 | primary + secondary (twinx) |
| Memory cleanup | GC | Explicit `plt.close()` |
