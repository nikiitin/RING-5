# Common Tasks -- Quick Reference

## 1. Add a New Plot Type

**Pattern**: Factory + ABC. Files to modify: 5.

1. Create the plot class in `src/web/pages/ui/plotting/types/<name>_plot.py`:
   ```python
   class MyPlot(BasePlot):
       def __init__(self, plot_id: int, name: str):
           super().__init__(plot_id, name, "my_plot")

       @override
       def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
           return my_config.render(data, saved_config, self.plot_id)

       @override
       def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
           # Build engine-agnostic TraceConfig objects
           return TraceBuildResult(traces=[...])

       @override
       def get_legend_column(self, config: PlotConfig) -> str | None:
           return config.get("color")
   ```

2. Create a config component in `src/web/components/plotting/config/<name>_config.py`:
   ```python
   def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
       # Render Streamlit selectboxes for X, Y, Color columns
       return {"x": x_col, "y": y_col, "color": color_col, ...}
   ```

3. Register in `src/web/pages/ui/plotting/plot_factory.py`:
   ```python
   # Add to _plot_classes dict:
   "my_plot": MyPlot,
   # Add to _plot_metadata dict:
   "my_plot": {"display_name": "My Plot", "icon": "auto_graph", "category": "basic"},
   ```

4. Export from `src/web/pages/ui/plotting/types/__init__.py`:
   ```python
   from .my_plot import MyPlot
   ```

5. Add tests in `tests/unit/test_<name>_plot.py`:
   - Test `create_traces()` returns valid `TraceBuildResult`.
   - Test `get_legend_column()` returns correct column.
   - Test `PlotFactory.create_plot("my_plot", 1, "test")` returns correct type.

**Optional**: If the plot needs a new `TraceConfig` subclass, add it to
`src/core/models/visualization/trace_config.py` and handle it in
`src/web/rendering/trace_to_plotly.py` (`_convert_trace()` dispatcher).

**Optional**: For custom style UI, extend `BaseStyleUI` in
`src/web/pages/ui/plotting/styles/` and update
`src/web/pages/ui/plotting/styles/factory.py`.

---

## 2. Add a New Shaper

**Pattern**: Factory + ABC. Files to modify: 5-6.

1. Define the config model in `src/core/models/shaper_models.py`:
   ```python
   class MyShaperConfig(BaseShaperConfig, total=False):
       my_param: Required[str]
       threshold: float
   ```
   Add `MyShaperConfig` to the `ShaperStepConfig` union type in the same file.

2. Create the shaper class in `src/core/services/shapers/impl/<name>.py`:
   ```python
   class MyShaper(UniDfShaper):
       def __init__(self, params: dict[str, Any]) -> None:
           config = cast(MyShaperConfig, params)
           self.my_param = config["my_param"]
           super().__init__(params)

       @override
       def _verify_params(self) -> bool:
           super()._verify_params()
           if "my_param" not in self.params:
               raise ValueError("Missing 'my_param'.")
           return True

       @override
       def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
           self._verify_preconditions(data_frame)
           result = data_frame.copy()
           # Transform result
           return result
   ```

3. Register in `src/core/services/shapers/factory.py`:
   ```python
   # Add to _registry dict:
   "myShaper": MyShaper,
   # Add to _display_names dict:
   "myShaper": "My Shaper",
   ```

4. Add validation in `src/core/services/shapers/validation.py`:
   ```python
   # Add to _REQUIRED_PARAMS dict:
   "myShaper": ["my_param"],
   ```

5. Create UI config component in `src/web/components/shapers/<name>_config.py`:
   ```python
   class MyShaperConfig:
       @staticmethod
       def render(data, existing_config, key_prefix, shaper_id) -> ShaperStepConfig:
           # Render Streamlit widgets
           return cast(ShaperStepConfig, {"type": "myShaper", "my_param": value})
   ```
   Register in dispatcher at `src/web/pages/ui/shaper_config.py`:
   ```python
   # Add to config_dispatch dict:
   "myShaper": MyShaperConfig.render,
   ```

6. Add tests in `tests/unit/test_<name>_shaper.py`:
   - Test `_verify_params()` with valid and invalid configs.
   - Test `__call__()` transforms DataFrame correctly.
   - Test `ShaperFactory.create_shaper("myShaper", config)` works.

**Naming**: Shaper type identifiers use `camelCase` (e.g., `conditionSelector`).

---

## 3. Add a New Data Manager

**Pattern**: ABC + page registration. Files to modify: 4.

1. Create the manager class in `src/web/components/data_managers/<name>.py`:
   ```python
   from src.web.components.data_managers.data_manager import DataManager

   class MyManager(DataManager):
       @property
       def name(self) -> str:
           return "My Manager"

       def render(self) -> None:
           st.markdown("### My Manager")
           data = self.get_data()
           if data is None:
               st.error("No data available.")
               return
           # Render Streamlit UI
           # Call self.api.managers.<method>() for transformations
           # Call self.set_data(result) to persist changes
   ```

2. Implement the backend service method (if needed) in
   `src/core/services/managers/<service>.py`, then add the method signature to
   `src/core/services/managers/managers_api.py` and wire delegation in
   `src/core/services/managers/managers_impl.py`.

3. Register in the page at `src/web/pages/data_managers.py`:
   ```python
   from src.web.components.data_managers.<name> import MyManager
   # Add a new tab in the st.tabs() call
   # Add a fragment that calls MyManager(api).render()
   ```

4. Add tests:
   - Unit test for the service method in `tests/unit/test_<service>.py`.
   - UI unit test in `tests/ui_unit/test_data_manager_logic.py`.

**Existing managers**: `PreprocessorManager`, `MixerManager`,
`OutlierRemoverManager`, `SeedsReducerManager`.

---

## 4. Add a New Rendering Engine

**Pattern**: Manager + Protocol. Files to modify: 4.

1. Extend `EngineMode` in `src/web/rendering/engine_manager.py`:
   ```python
   EngineMode = Literal["plotly", "matplotlib", "bokeh"]
   _VALID_MODES: frozenset[str] = frozenset({"plotly", "matplotlib", "bokeh"})
   ```

2. Create a trace renderer in `src/web/rendering/trace_to_<engine>.py`:
   ```python
   def traces_to_bokeh(result: TraceBuildResult) -> BokehFigure:
       # Convert each TraceConfig to engine-specific artists
   ```

3. Create a connector in `src/web/rendering/<engine>_connector.py`:
   ```python
   from src.web.rendering._connector_protocol import STYLING_PIPELINE_ORDER

   class FigureSpecToBokeh:
       @staticmethod
       def apply(spec: FigureConfig, fig: BokehFigure) -> BokehFigure:
           # Apply styles in STYLING_PIPELINE_ORDER (16 steps)
           for step in STYLING_PIPELINE_ORDER:
               handler = getattr(FigureSpecToBokeh, f"_apply_{step}", None)
               if handler:
                   handler(spec, fig)
           return fig
   ```

4. Update chart display in `src/web/components/common/chart_display.py`:
   - Add a `render_<engine>_chart()` method.
   - Update `render_engine_selector()` to include the new option.

**Required**: Follow `STYLING_PIPELINE_ORDER` from
`src/web/rendering/_connector_protocol.py` (16 steps: backgrounds, font_family,
color_palette, title, axis_labels, axis_ticks, axis_ranges, axis_colors, grids,
legends, reference_lines, data_labels, annotations, separators, hatching, margins).

---

## 5. Add a New Settings Panel

**Pattern**: Data descriptor + component. Files to modify: 3.

1. Add the section descriptor in `src/web/pages/ui/plotting/settings_pills.py`:
   ```python
   # Append to SETTINGS_SECTIONS list:
   SettingsSection("my_section", "My Section", "icon_name", advanced=True),
   ```

2. Create the component in `src/web/components/plotting/settings/<name>_settings.py`:
   ```python
   from src.web.components.plotting.settings.widget_factory import (
       select_option, numeric_input, toggle, color_picker, slider,
   )

   class MySectionSettingsComponent:
       def __init__(self, plot_id: int, plot_type: str):
           self.plot_id = plot_id
           self.plot_type = plot_type

       def render(self, saved_config: PlotConfig, **kwargs) -> PlotConfig:
           config: dict[str, Any] = {}
           config["my_key"] = select_option(
               "Label", ["opt1", "opt2"], saved_config, "my_key", self.plot_id
           )
           return config
   ```

3. Add the dispatch case in `src/web/pages/ui/plotting/plot_config_ui.py`
   (`render_settings_section` method):
   ```python
   if section == "my_section":
       return MySectionSettingsComponent(self.plot_id, self.plot_type).render(saved_config)
   ```

**Widget factory** (`src/web/components/plotting/settings/widget_factory.py`)
provides: `select_option()`, `numeric_input()`, `color_picker()`, `toggle()`,
`slider()`.

**Existing sections**: layout, typography, legends, axes, data_labels, colors,
advanced.

---

## 6. Add a New Export Preset

**Pattern**: JSON config. Files to modify: 1.

1. Add the preset entry in
   `src/web/pages/ui/plotting/export/presets/latex_presets.json`:
   ```json
   {
     "presets": {
       "my_venue": {
         "description": "My Venue format",
         "typical_use": "Single column for My Venue papers",
         "width_inches": 3.5,
         "height_inches": 2.625,
         "dpi": 300,
         "font_family": "serif",
         "font_size_base": 9,
         "font_size_title": 10,
         "font_size_ticks": 7,
         "font_size_annotations": 6,
         "line_width": 1.0,
         "marker_size": 4,
         "legend_columnspacing": 2.0,
         "legend_handletextpad": 0.8,
         "legend_labelspacing": 0.5,
         "legend_handlelength": 2.0,
         "legend_handleheight": 0.7,
         "legend_borderpad": 0.4,
         "legend_borderaxespad": 0.5
       }
     }
   }
   ```

2. Clear cache if testing interactively:
   ```python
   from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager
   PresetManager._cache.clear()
   PresetManager._initialized = False
   ```

3. The preset auto-appears in `render_preset_pills()` via
   `PresetManager.list_presets()`. Validation runs on first load via
   `PresetManager.validate_preset()`.

**Schema**: `src/web/pages/ui/plotting/export/presets/preset_schema.py`
(`LaTeXPreset` TypedDict, 70+ fields).

**Tests**: `tests/unit/export/test_preset_manager.py`,
`tests/unit/test_preset_applicator.py`.

---

## 7. Add a New Simulator Backend

**Pattern**: Registry + Protocol. Files to modify: 3-4.

1. Create the parser implementing `SimulationParser` protocol
   (`src/parsing/parser_protocol.py`):
   ```python
   # src/parsing/my_sim/parser.py
   class MySimParser:
       def submit_parse_async(self, stats_path, stats_pattern, variables,
                              output_dir, strategy_type="default",
                              scanned_vars=None) -> ParseBatchResult: ...
       def finalize_parsing(self, output_dir, results,
                            strategy_type="default", var_names=None) -> str | None: ...
       def submit_scan_async(self, stats_path,
                             stats_pattern="results.log", limit=5): ...
       def aggregate_scan_results(self, results): ...
   ```

2. Create a `SimulatorInfo` descriptor and register in
   `src/parsing/my_sim/__init__.py`:
   ```python
   from src.parsing.registry import SimulatorRegistry, SimulatorInfo, ParsingStrategy

   MY_SIM_INFO = SimulatorInfo(
       name="my_sim",
       display_name="My Simulator",
       description="Description for UI",
       file_pattern="results.log",
       variable_types=["scalar", "vector"],
       internal_stats=frozenset({"__internal"}),
       parsing_strategies=[
           ParsingStrategy(name="default", display_name="Default",
                           description="Standard parsing"),
       ],
   )

   def _create_parser():
       from src.parsing.my_sim.parser import MySimParser
       return MySimParser()

   SimulatorRegistry.register(MY_SIM_INFO, _create_parser)
   ```

3. Ensure the module is imported at startup so `SimulatorRegistry.register()`
   executes. Wire into `src/core/application_api.py` if needed.

4. Add tests:
   - Unit tests for parse/scan methods.
   - Integration test: `SimulatorRegistry.get_parser("my_sim")` returns instance.

**Reference**: gem5 registration at bottom of `src/parsing/registry.py`.

**Naming**: Simulator names use lowercase (e.g., `gem5`).

---

## 8. Fix a Rendering Bug

**Debug workflow**: Trace the data path from config to visual output.

1. Check the config builder -- is the `FigureConfig` built correctly?
   ```
   src/web/rendering/config_builder.py  (ConfigSpecBuilder.from_config)
   ```
   Print the `FigureConfig` fields relevant to the bug. Verify the flat config
   dict has the expected keys.

2. Check sentinel resolution -- are `-1` values being resolved?
   ```
   src/core/services/visualization/config_resolver.py  (resolve_config)
   ```
   Verify the inheritance chain resolves correctly (typography, legend spacing,
   axis properties).

3. Check the connector -- is the styling applied correctly?
   ```
   src/web/rendering/plotly_connector.py   (FigureSpecToPlotly.apply)
   src/web/rendering/matplotlib_connector.py (FigureSpecToMatplotlib.apply)
   ```
   The connectors follow `STYLING_PIPELINE_ORDER` from
   `src/web/rendering/_connector_protocol.py`.

4. Check trace rendering -- are traces built correctly?
   ```
   src/web/rendering/trace_to_plotly.py           (traces_to_plotly)
   src/web/rendering/matplotlib_trace_renderer.py (MatplotlibTraceRenderer.render)
   ```
   Verify `TraceBuildResult` has correct traces, barmode, shapes, annotations.

5. Check plot type `create_traces()`:
   ```
   src/web/pages/ui/plotting/types/<type>_plot.py
   ```
   Verify the `PlotConfig` keys are read correctly and `TraceConfig` objects
   have expected field values.

**Common issues**:
- Wrong axis: check `yaxis="y"` vs `yaxis="y2"` on `TraceConfig`.
- Missing colors: verify `color_palette` resolution in `ConfigSpecBuilder`.
- Layout not applied: verify `StyleApplicator` in
  `src/web/pages/ui/plotting/styles/applicator.py` calls `resolve_config()`.

---

## 9. Add a New Arithmetic Operation

**Pattern**: Static service method. Files to modify: 3.

1. Add the operation to `list_operators()` and `apply_operation()` in
   `src/core/services/managers/arithmetic_service.py`:
   ```python
   @staticmethod
   def list_operators() -> list[str]:
       return ["Division", "Sum", "Subtraction", "Multiplication", "Modulo"]

   @staticmethod
   def apply_operation(df, operation, src1, src2, dest) -> pd.DataFrame:
       result = df.copy()
       s1, s2 = result[src1], result[src2]
       op = operation.lower()
       # ... existing cases ...
       elif op in ["modulo", "mod", "%"]:
           result[dest] = s1 % s2.replace(0, np.nan)
       else:
           raise ValueError(f"Unknown operation: {operation}")
       return result
   ```

2. Update the default name generation in the UI component at
   `src/web/components/data_managers/preprocessor.py`:
   ```python
   elif op_lower in ["modulo", "mod"]:
       default_name = f"{src_col1}_mod_{src_col2}"
   ```

3. Add tests:
   - Unit test: call `ArithmeticService.apply_operation(df, "Modulo", ...)`.
   - Edge case: division/modulo by zero produces `NaN`.
   - Integration: `DefaultManagersAPI().apply_operation()` delegates correctly.

**Existing operators**: Division, Sum, Subtraction, Multiplication.

**Delegation chain**: `PreprocessorManager` -> `api.managers.apply_operation()`
-> `DefaultManagersAPI.apply_operation()` ->
`ArithmeticService.apply_operation()`.

---

## 10. Debug Shaper Pipeline Issues

**Diagnostic workflow**: Follow the pipeline from config to output.

1. Check validation -- does the config pass pre-flight checks?
   ```
   src/core/services/shapers/validation.py
   ```
   Call `validate_shaper_config(shaper_type, config)` manually. Check the
   `_REQUIRED_PARAMS` dict for the shaper type.

2. Check factory instantiation -- does the shaper create successfully?
   ```
   src/core/services/shapers/factory.py
   ```
   Call `ShaperFactory.create_shaper(type, config)`. If it raises `ValueError`,
   the type is not in `_registry`. If the constructor raises, check
   `_verify_params()` in the shaper class.

3. Check execution order -- are shapers applied in correct sequence?
   ```
   src/core/services/shapers/pipeline_service.py  (PipelineService.process_pipeline)
   ```
   Pipeline iterates `list[ShaperStepConfig]` in order. Each shaper's
   `__call__(df)` receives the output of the previous shaper.

4. Check the web-layer runner for UI-specific issues:
   ```
   src/web/pages/ui/shaper_config.py  (apply_shapers)
   ```
   This path pre-validates each step and shows `st.error()` / `st.warning()`
   for failures. Incomplete configs are skipped with a warning.

5. Check individual shaper logic:
   ```
   src/core/services/shapers/impl/<shaper>.py
   ```
   Verify `_verify_preconditions(df)` passes (columns exist, types match).
   Verify `__call__(df)` produces expected output.

**Common issues**:
- Column not found: a previous shaper renamed or dropped the column.
- Empty DataFrame: a filter shaper removed all rows. Check
  `ConditionSelector` or `ItemSelector` parameters.
- Wrong order: Normalize before Mean will fail if mean rows are not yet
  appended. Mean should run before Normalize in most pipelines.
- Cache stale: Mean and Normalize use `@cached`. Fingerprint includes data
  shape and params. If data changes but fingerprint collides, clear cache.

**Shaper type identifiers** (camelCase): `mean`, `columnSelector`,
`conditionSelector`, `itemSelector`, `normalize`, `pivotLonger`, `pivotWider`,
`sort`, `splitApply`, `transformer`.

---

## Quick File Reference

### Core Layer (Layer B)

| Purpose | File |
|---------|------|
| Shaper ABC | `src/core/services/shapers/shaper.py` |
| Shaper factory | `src/core/services/shapers/factory.py` |
| Shaper validation | `src/core/services/shapers/validation.py` |
| Pipeline execution | `src/core/services/shapers/pipeline_service.py` |
| Shaper config models | `src/core/models/shaper_models.py` |
| Arithmetic service | `src/core/services/managers/arithmetic_service.py` |
| Managers API protocol | `src/core/services/managers/managers_api.py` |
| Managers implementation | `src/core/services/managers/managers_impl.py` |
| Trace config models | `src/core/models/visualization/trace_config.py` |
| TraceBuildResult | `src/core/models/visualization/trace_build_result.py` |
| Config resolver | `src/core/services/visualization/config_resolver.py` |
| Services API protocol | `src/core/services/services_api.py` |
| Services composition root | `src/core/services/services_impl.py` |
| Simulator registry | `src/parsing/registry.py` |
| Parser protocol | `src/parsing/parser_protocol.py` |

### Web Layer (Layer C)

| Purpose | File |
|---------|------|
| Plot factory | `src/web/pages/ui/plotting/plot_factory.py` |
| Base plot ABC | `src/web/pages/ui/plotting/base_plot.py` |
| Plot config UI mixin | `src/web/pages/ui/plotting/plot_config_ui.py` |
| Plot types directory | `src/web/pages/ui/plotting/types/` |
| Settings pills | `src/web/pages/ui/plotting/settings_pills.py` |
| Settings components | `src/web/components/plotting/settings/` |
| Widget factory | `src/web/components/plotting/settings/widget_factory.py` |
| Style UI factory | `src/web/pages/ui/plotting/styles/factory.py` |
| Style applicator | `src/web/pages/ui/plotting/styles/applicator.py` |
| Shaper config UI | `src/web/pages/ui/shaper_config.py` |
| Engine manager | `src/web/rendering/engine_manager.py` |
| Plotly connector | `src/web/rendering/plotly_connector.py` |
| Matplotlib connector | `src/web/rendering/matplotlib_connector.py` |
| Trace to Plotly | `src/web/rendering/trace_to_plotly.py` |
| Matplotlib trace renderer | `src/web/rendering/matplotlib_trace_renderer.py` |
| Config builder | `src/web/rendering/config_builder.py` |
| Connector protocol | `src/web/rendering/_connector_protocol.py` |
| Preset manager | `src/web/pages/ui/plotting/export/presets/preset_manager.py` |
| Preset schema | `src/web/pages/ui/plotting/export/presets/preset_schema.py` |
| Preset JSON | `src/web/pages/ui/plotting/export/presets/latex_presets.json` |
| Data manager ABC | `src/web/components/data_managers/data_manager.py` |
| Data managers page | `src/web/pages/data_managers.py` |
| Preprocessor manager | `src/web/components/data_managers/preprocessor.py` |

### Test Locations

| Area | Test Files |
|------|-----------|
| Plot types | `tests/unit/test_plot_types.py`, `tests/unit/test_plot_factory.py` |
| Shapers | `tests/unit/test_shapers_extended.py`, `tests/unit/test_shaper_edge_cases.py` |
| Shaper validation | `tests/unit/test_shaper_config_validate.py` |
| Shaper factory | `tests/unit/test_shaper_factory_display.py` |
| Data managers | `tests/unit/test_data_managers_page.py`, `tests/integration/test_service_managers.py` |
| Presets | `tests/unit/export/test_preset_manager.py`, `tests/unit/test_preset_applicator.py` |
| Rendering | `tests/unit/test_trace_to_plotly.py`, `tests/unit/test_matplotlib_trace_renderer.py` |
| Plot lifecycle | `tests/integration/test_plot_lifecycle.py` |
| E2E managers+shapers | `tests/integration/test_e2e_managers_shapers.py` |
