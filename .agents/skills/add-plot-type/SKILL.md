---
name: add-plot-type
description: Add a new plot/chart type to RING-5 (subclass BasePlot, emit engine-agnostic traces, register in PlotFactory, wire config UI, test). Use when the user asks to add or modify a visualization/chart/plot type.
---

# Add a new plot type

Plots are **engine-agnostic**: a plot builds `TraceConfig` objects (a `TraceBuildResult`), and the
rendering layer converts those to Plotly or Matplotlib. You almost never touch Plotly/Matplotlib
directly when adding a plot type.

**Best starting move:** copy the nearest existing type in
`src/web/pages/ui/plotting/types/` (e.g. `bar_plot.py` for a simple one, `stacked_bar_plot.py` /
`grouped_stacked_bar_plot.py` for composites) and adapt. `grouped_stacked_bar` shows the
"extend another plot type" pattern (`GroupedStackedBarPlot(StackedBarPlot)`).

## Steps

1. **Create the class** — `src/web/pages/ui/plotting/types/<name>_plot.py`:
   ```python
   from src.web.pages.ui.plotting.base_plot import BasePlot
   # ... TraceBuildResult / TraceConfig imports from src.core.models.visualization

   class MyPlot(BasePlot):
       def __init__(self, plot_id: int, name: str) -> None:
           super().__init__(plot_id, name, "my_plot")

       def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
           return render_common_with_color(data, saved_config, self.plot_id)

       def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
           # build TraceConfig objects from data + config; return TraceBuildResult
           ...
   ```
   Import `render_common_with_color` from
   `src/web/components/plotting/config/base_plot_config.py` for shared X/Y/color controls.
   `create_figure()` is provided by `BasePlot` (delegates to `create_traces` + `trace_to_plotly`);
   `apply_common_layout()` applies shared Plotly styling. Headless callers use public
   `Session.render(plot, engine=...)` for the complete sequence.

2. **Export** the class from `src/web/pages/ui/plotting/types/__init__.py`.

3. **Register** in `src/web/pages/ui/plotting/plot_factory.py`:
   - add to `PlotFactory._plot_classes` with a **snake_case** key (e.g. `"my_plot"`);
   - add a matching entry to `_plot_metadata` (`display_name`, `icon`, `category` ∈
     `basic|comparison|distribution`).

4. **Config UI** (only if the plot needs options beyond the shared X/Y/color selectors):
   add a component under `src/web/components/plotting/config/` and wire it through
   `plot_config_ui.py` / the `PlotConfigUIMixin`. Reuse helpers in `config/base_plot_config.py`
   (`detect_column_types`, `render_xy_selectors`, …). Keep widget keys per-plot-unique:
   `f"{prefix}_{field}_{plot_id}"`.

5. **Serialization** uses `BasePlot.to_dict` + `PlotFactory.from_dict`. Plot tables use the shared
   typed table codec. Adding persistent state updates the writer, the field contract in
   `src/core/common/plot_payload.py`, and restoration together; extra serialized fields are rejected.

6. **Tests:**
   - unit in `tests/unit/` — exercise `create_traces`/`create_figure` with `sample_data`
     (root conftest fixture) for the new type;
   - render configured and restored plots through public `Session.render` with both engines;
   - integration in `tests/integration/` for non-trivial workflows;
   - keep `mypy`/`black`/`flake8` clean.

## Rules & gotchas
- Engine-agnostic only: build `TraceConfig`, never call `go.*`/`plt.*` inside the plot class.
- Styling is **not** the plot's job — it lives in `FigureConfig` + the connectors
  (see the `rendering-figureconfig` skill).
- Default palette is `wong` (colorblind-safe). Error-bar columns use the `{y}.sd` suffix.
- Verify after: `make arch-check && ./python_venv/bin/mypy src/ && make test-unit`.
