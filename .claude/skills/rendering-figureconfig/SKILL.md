---
name: rendering-figureconfig
description: Work on RING-5's figure styling / rendering pipeline — FigureConfig (the single styling source of truth), the -1 sentinel inheritance, the 16-step STYLING_PIPELINE_ORDER, the Plotly + Matplotlib connectors, and dual-engine consistency. Use for any figure styling, theming, axes/legend/typography, or LaTeX-export task.
---

# Rendering & FigureConfig (dual-engine styling)

Styling is decoupled from plots. A plot emits engine-agnostic traces; **all visual styling** is
described by one immutable-ish config and applied identically to both engines.

## The pipeline
```
plot.create_traces() ──▶ TraceBuildResult ──▶ trace_to_plotly / matplotlib_trace_renderer
config (flat dict)   ──▶ ConfigSpecBuilder ──▶ FigureConfig ──▶ config_resolver.resolve_config()
                                                                       │ (sentinels removed)
                                                                       ▼
                                   FigureSpecToPlotly  /  FigureSpecToMatplotlib  (connectors)
```
- **`FigureConfig`** and its sub-configs live in `src/core/models/visualization/` (`figure_config.py`,
  `axis_config.py`, `legend_config.py`, `typography_config.py`, `data_label_config.py`,
  `annotation_config.py`, `series_style_config.py`, `trace_config.py`, `palettes.py`, …). It is the
  **single source of truth** and is engine-agnostic (no Plotly/Matplotlib/Streamlit imports here).
- **Sentinels:** numeric fields default to `-1` / `-1.0` meaning "inherit". `config_resolver`
  (`src/core/services/visualization/config_resolver.py`) replaces every sentinel via deepcopy
  **before** any connector runs — connectors never see `-1`. Add new inheritable fields with a
  sentinel default + a rule in `resolve_config`.
- **Connectors** (`src/web/rendering/plotly_connector.py::FigureSpecToPlotly`,
  `matplotlib_connector.py::FigureSpecToMatplotlib`) are **stateless** (`@staticmethod`) and apply
  styles in the **exact same 16-step order** declared in
  `src/web/rendering/_connector_protocol.py::STYLING_PIPELINE_ORDER`:

  `backgrounds → font_family → color_palette → title → axis_labels → axis_ticks → axis_ranges →
  axis_colors → grids → legends → reference_lines → data_labels → annotations → separators →
  hatching → margins`

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
5. Add/extend an export preset in `src/web/pages/ui/plotting/export/presets/` if publication-relevant.

## Engine, palettes, export
- `EngineManager` (`src/web/rendering/engine_manager.py`) toggles `plotly`/`matplotlib` via the
  `ring5_engine_mode` session key. Default palette: **`wong`** (colorblind-safe); resolution via
  `services/visualization/palette_service.py`.
- Matplotlib: lazy-imported inside methods; `chart_display.py` owns figure lifecycle (`plt.close()`
  + session-scoped `plot.{id}.mpl_fig` cache). The connector itself must **not** close figures.
- Publication exports: PDF/SVG/PGF/EPS via Matplotlib+LaTeX (`make install-latex`; `requires_latex`
  marker) and Plotly via Kaleido. `download_section.py` is engine-aware.
- Legend hierarchy config prefixes: `legend_*` / `legend2_*` / `legend3_*` (never "boxed").

## Verify after
`make arch-check && ./python_venv/bin/mypy src/ &&
 ./python_venv/bin/pytest tests/unit/ -k "connector or figure or render or trace or palette" -q`
Roundtrip/connector tests are the safety net — see `CONTRIBUTING.md` "Connector Tests" / "Spec
Roundtrip Tests".
