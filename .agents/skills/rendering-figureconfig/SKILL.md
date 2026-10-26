---
name: rendering-figureconfig
description: Work on RING-5's figure styling / rendering pipeline — FigureConfig (the single styling source of truth), explicit field inheritance, the 15-step STYLING_PIPELINE_ORDER, the Plotly + Matplotlib connectors, and dual-engine consistency. Use for any figure styling, theming, axes/legend/typography, or LaTeX-export task.
---

# Rendering & FigureConfig (dual-engine styling)

Styling is decoupled from plots. A plot emits engine-agnostic traces; **all visual styling** is
described by one engine-independent configuration and projected through both engines.

## The pipeline
```
plot.create_traces() ──▶ TraceBuildResult ──▶ trace_to_plotly / matplotlib_trace_renderer
effective config   ──▶ ConfigSpecBuilder ──▶ FigureConfig ──▶ config_resolver.resolve_config()
                                                                       │ (inheritance resolved)
                                                                       ▼
                                   FigureSpecToPlotly  /  FigureSpecToMatplotlib  (connectors)
```
- **`FigureConfig`** and its sub-configs live in `src/core/models/visualization/` (`figure_config.py`,
  `axis_config.py`, `legend_config.py`, `typography_config.py`, `data_label_config.py`,
  `annotation_config.py`, `series_style_config.py`, `trace_config.py`, `palettes.py`, …). It is the
  **single source of truth** and is engine-agnostic (no Plotly/Matplotlib/Streamlit imports here).
- **Inheritance:** designated typography, legend and axis fields use `-1` / `-1.0` to inherit.
  `src/core/services/visualization/config_resolver.py` resolves those fields on an owned deep copy
  before connectors run. Automatic legend-position sentinels remain for connector placement; a
  negative value is not universally an inheritance request. Give each new field an explicit
  default/omission policy and add a resolver rule only when it inherits.
- **Connectors** (`src/web/rendering/plotly_connector.py::FigureSpecToPlotly`,
  `matplotlib_connector.py::FigureSpecToMatplotlib`) are **stateless** (`@staticmethod`) and apply
  the **15 named styling capabilities** declared in
  `src/web/rendering/_connector_protocol.py::STYLING_PIPELINE_ORDER`:

  `backgrounds → font_family → color_palette → title → axis_labels → axis_ticks → axis_ranges →
  axis_colors → grids → hatching → legends → reference_lines → data_labels →
  annotations → margins`

  Matplotlib executes this sequence directly. Plotly projects combined axis operations and
  heatmap-specific styling in `FigureSpecToPlotly.apply`; preserve palette, explicit override
  and legend precedence when changing either connector.

`prepare_figure` owns effective defaults, one registered trace callback, encodings, raw source names
and one resolved `FigureConfig`. `PreparedFigure` feeds the native builders directly for Session,
report and dashboard rendering. Standalone Matplotlib figures and dashboard panels share
`draw_matplotlib_axes`. Trace `legend_role` selects trace ownership; numbered annotations refer to
a style role independently. Legend font sizes retain fractional points. All flat legend tiers use
`anchor_x`/`anchor_y`; native annotation `xanchor`/`yanchor` remain connector properties.

Native builders return `PlotlyRenderResult` or `MatplotlibFigureResult`. The artifact owns this
one result; figure and engine are derived. Connectors require that explicit result and return
`None`. Matplotlib's private panel helpers require `MatplotlibRenderResult` and derive their axes
from it. A `MatplotlibRenderResult` without source bindings is appropriate for paper annotations or
layout; meaningful data tests use real neutral emissions or explicit known-source/native associations.

`legend_labels` owns display text. Keep neutral names, style keys, order, group and role identity
unchanged; apply styles before projecting text into native legends or facet titles. Per-series
styles contain no name field. Cycle positional styles by original emission ordinal, including
hidden slots. Native membership, unique ownership and generated roles must pass whole-root
preflight before restyling. Native copies need deliberate association transfer; do not discover
identity from labels or attach private source IDs. Export copies consume fully styled figures.

Shared legends merge only matching original identities, roles/groups and known final glyphs.
Unknown or array-valued glyph state keeps separate entries. Owned legend/colorbar outputs are
reused or replaced through their explicit result, preserving foreign outputs. Structural colorbar
changes require callback and layout generation ownership; foreign adoption requires a fresh build.

## Golden rule: change BOTH engines, in order
Any new styling capability must be implemented in **both** connectors and slot into the correct
`STYLING_PIPELINE_ORDER` step (add a step to the tuple if genuinely new). If you only touch one
engine, Plotly and Matplotlib output diverge — that's a bug.

Recipe to add a styling option:
1. Add the field(s) to the relevant `*Config` dataclass in `models/visualization/` (with sentinel
   default if inheritable) + `to_dict`/`from_dict` round-trip.
2. Surface it in the builder (`src/web/rendering/config_builder.py`) and the settings UI under
   `src/web/components/plotting/settings/` (respect Settings-ownership: ticks/grid → Axes pill;
   fonts/colors → Typography pill).
3. Apply it in `FigureSpecToPlotly` **and** `FigureSpecToMatplotlib` at the right pipeline step.
4. Update `trace_to_plotly.py` / `matplotlib_trace_renderer.py` if it's per-trace.
5. Extend `ring5.figure_spec.FigureSpec` when the option belongs in the public publication API.

## Engine, palettes, export
- `EngineManager` (`src/web/rendering/engine_manager.py`) toggles `plotly`/`matplotlib` via the
  `ring5_engine_mode` session key. Default palette: **`wong`** (colorblind-safe); resolution via
  `src/core/services/visualization/palette_service.py`.
- `PlotRenderState` owns one bound artifact or configuration-only detached payload. `BasePlot`
  publishes native figure, configuration, preparation, engine and key atomically. Repository-managed
  retirement drains after the outer Core transaction lock; slot callbacks run outside slot locks
  and preserve borrowed figure content. Publication relinquishes its owned
  Matplotlib manager once; later retirement cannot close a manager registered by the borrower.
  Chart display consumes the artifact
  directly; it does not rebuild figures or maintain a Matplotlib session cache.
- Configuration reads are owned snapshots. Assign a complete edited mapping; do not mutate
  `plot.config[...]` or keep a second configuration/native cache. Composite artifacts retain actual
  per-panel preparations, with no placeholder trace result.
- Publication exports: PDF/SVG/PNG/PGF via Matplotlib (PGF requires LaTeX) (`make install-latex`; `requires_latex`
  marker) and Plotly via Kaleido. `download_section.py` is engine-aware.
- Legend hierarchy config prefixes: `legend_*` / `legend2_*` / `legend3_*` (never "boxed").

## Verify after
`make arch-check && ./python_venv/bin/mypy src/ &&
 ./python_venv/bin/pytest tests/unit/ -k "connector or figure or render or trace or palette" -q`
Roundtrip/connector tests are the safety net — see `CONTRIBUTING.md` "Connector Tests" / "Spec
Roundtrip Tests".
