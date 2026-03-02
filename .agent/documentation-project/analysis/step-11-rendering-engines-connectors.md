# Step 11 — Rendering Engines & Connectors Analysis

> **Objective**: Document the dual-engine rendering system — the connector protocol,
> Plotly connector, Matplotlib connector, trace rendering, config building, and the
> complete flow from FigureConfig to rendered output.

---

## Scope

This step analyzes the **rendering pipeline** — the final stage that transforms abstract
plot configuration into actual visual output using Plotly or Matplotlib.

---

## Files to Analyze

### Rendering Core
```
src/web/rendering/__init__.py
src/web/rendering/engine_manager.py                (engine selection/management)
src/web/rendering/_connector_protocol.py           (connector protocol/interface)
src/web/rendering/_render_result.py                (render result type)
```

### Connectors
```
src/web/rendering/plotly_connector.py              (Plotly rendering)
src/web/rendering/matplotlib_connector.py          (Matplotlib rendering)
```

### Trace Rendering
```
src/web/rendering/trace_to_plotly.py               (trace → Plotly mapping)
src/web/rendering/matplotlib_trace_renderer.py     (trace → Matplotlib mapping)
```

### Config Building
```
src/web/rendering/config_builder.py                (builds FigureConfig from UI state)
```

### Utilities
```
src/web/rendering/_heatmap_utils.py                (heatmap-specific rendering utils)
src/web/rendering/preset_applicator.py             (applies export presets)
```

### Widgets
```
src/web/rendering/widgets/__init__.py
src/web/rendering/widgets/widget_def.py            (widget definitions)
src/web/rendering/widgets/widget_renderer.py       (widget rendering)
```

### Chart Display (Consumer)
```
src/web/components/common/chart_display.py         (displays rendered charts)
```

### Interactive Plot
```
src/web/components/plotting/interactive_plot.py    (interactive Plotly features)
```

---

## Questions to Answer

### Connector Protocol:
- [ ] What is the connector protocol/interface?
- [ ] What methods must every connector implement?
- [ ] What input does a connector receive? (FigureConfig? TraceBuildResult?)
- [ ] What output does a connector produce?
- [ ] How does engine switching work?
- [ ] Can both engines render the same plot identically?

### Engine Manager:
- [ ] How is the active engine selected?
- [ ] Can the user switch engines at runtime?
- [ ] What are the capabilities/limitations of each engine?
- [ ] Is engine selection per-plot or global?

### Plotly Connector:
- [ ] How does it translate FigureConfig → Plotly Figure?
- [ ] How does trace_to_plotly.py work?
- [ ] What Plotly graph objects are used?
- [ ] How are layout, axes, legend, annotations mapped?
- [ ] What Plotly-specific features are supported?
- [ ] How is interactivity handled?

### Matplotlib Connector:
- [ ] How does it translate FigureConfig → Matplotlib Figure?
- [ ] How does matplotlib_trace_renderer.py work?
- [ ] What Matplotlib API is used? (OO API only, no pyplot?)
- [ ] How are layout, axes, legend, annotations mapped?
- [ ] What Matplotlib-specific features are supported?
- [ ] How is the figure exported? (formats, DPI, backend)
- [ ] Is PGF backend used for LaTeX?

### Config Builder:
- [ ] How does the config builder construct FigureConfig?
- [ ] What sources does it read from? (UI state, plot config, defaults)
- [ ] What is the build sequence?
- [ ] How does it handle engine-specific configuration?
- [ ] How does it handle plot-type-specific configuration?

### Preset Applicator:
- [ ] What export presets are available?
- [ ] How does a preset modify the FigureConfig?
- [ ] What venue-specific presets exist? (IEEE, ISCA, etc.)
- [ ] How does the preset system interact with download?

### Render Result:
- [ ] What does a render result contain?
- [ ] How is it consumed by chart_display?
- [ ] Does it include both figure object and image bytes?
- [ ] How are errors in rendering handled?

### Heatmap Utils:
- [ ] What heatmap-specific rendering logic exists?
- [ ] Why is it separated from the main connectors?

### Widget System:
- [ ] What are widget definitions?
- [ ] How does the widget renderer work?
- [ ] How do widgets interact with plotting?

---

## Information to Extract

### Rendering Pipeline Flow
```
UI Settings → Config Builder → FigureConfig → Engine Manager → Connector → Render Result → Chart Display

Detailed steps:
1. Config builder collects all settings from UI state
2. Config builder creates FigureConfig (with all sub-configs)
3. Engine manager selects the appropriate connector
4. Connector receives FigureConfig
5. Connector maps each TraceConfig to engine-specific trace objects
6. Connector applies layout, axes, legend, typography settings
7. Connector produces render result (figure object + optional bytes)
8. Chart display presents the result to the user
```

### Engine Comparison Matrix
```
| Feature | Plotly | Matplotlib |
|---------|--------|------------|
| Interactive | Yes | No |
| Export PNG | Yes | Yes |
| Export SVG | Yes | Yes |
| Export PDF | ? | Yes |
| Export PGF | No | Yes |
| LaTeX text | No | Yes |
| Colorbar | ? | ? |
| Annotations | ? | ? |
| ...         | ? | ? |
```

---

## Output Template

### 1. Connector Protocol Documentation
```
[To be filled]
```

### 2. Engine Manager Documentation
```
[To be filled]
```

### 3. Plotly Connector Documentation
```
[To be filled]
```

### 4. Matplotlib Connector Documentation
```
[To be filled]
```

### 5. Trace Rendering Documentation
```
[To be filled]
```

### 6. Config Builder Documentation
```
[To be filled]
```

### 7. Preset System Documentation
```
[To be filled]
```

### 8. Render Result Documentation
```
[To be filled]
```

### 9. Widget System Documentation
```
[To be filled]
```

### 10. Engine Comparison Matrix
```
[To be filled]
```

### 11. Complete Rendering Pipeline Flow
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `visualization/rendering-engines.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `architecture/visualization-pipeline.md`
- Step 14 (export) — export uses rendering output
- Step 18 (data flow) — rendering is the final visualization step
- Step 19 (extension points) — connector protocol for new engines
