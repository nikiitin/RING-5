# Step 10 — Plotting System, Types & Factory Analysis

> **Objective**: Document the complete plotting subsystem — the plot factory, base plot
> pattern, every plot type implementation, the plot renderer, and the relationship
> between plot types and their configuration/rendering.

---

## Scope

This step analyzes the **plot type system** — how different kinds of visualizations are
defined, created, configured, and rendered. This is critical for the "Adding a New Plot"
developer guide.

---

## Files to Analyze

### Plot Factory & Core
```
src/web/pages/ui/plotting/plot_factory.py          (creates plot type instances)
src/web/pages/ui/plotting/base_plot.py             (base plot class/pattern)
src/web/pages/ui/plotting/plot_renderer.py         (rendering orchestration)
src/web/pages/ui/plotting/plot_service.py          (plot service layer)
src/web/pages/ui/plotting/plot_config_ui.py        (configuration UI)
```

### Plot Types
```
src/web/pages/ui/plotting/types/__init__.py
src/web/pages/ui/plotting/types/bar_plot.py
src/web/pages/ui/plotting/types/dual_axis_bar_dot_plot.py
src/web/pages/ui/plotting/types/grouped_bar_plot.py
src/web/pages/ui/plotting/types/grouped_stacked_bar_plot.py
src/web/pages/ui/plotting/types/heatmap_plot.py
src/web/pages/ui/plotting/types/histogram_plot.py
src/web/pages/ui/plotting/types/line_plot.py
src/web/pages/ui/plotting/types/scatter_plot.py
src/web/pages/ui/plotting/types/stacked_bar_plot.py
src/web/pages/ui/plotting/types/_trace_helpers.py
```

### Plot Configuration Components
```
src/web/components/plotting/config/base_plot_config.py
src/web/components/plotting/config/dual_axis_config.py
src/web/components/plotting/config/dual_axis_settings.py
src/web/components/plotting/config/grouped_bar_config.py
src/web/components/plotting/config/grouped_stacked_bar_config.py
src/web/components/plotting/config/grouped_stacked_bar_theme.py
src/web/components/plotting/config/heatmap_config.py
src/web/components/plotting/config/histogram_config.py
src/web/components/plotting/config/plot_config_components.py
src/web/components/plotting/config/stacked_bar_config.py
```

### Style System
```
src/web/pages/ui/plotting/styles/__init__.py
src/web/pages/ui/plotting/styles/applicator.py
src/web/pages/ui/plotting/styles/bar_ui.py
src/web/pages/ui/plotting/styles/base_ui.py
src/web/pages/ui/plotting/styles/colors.py
src/web/pages/ui/plotting/styles/factory.py
src/web/pages/ui/plotting/styles/line_ui.py
```

### Plot Models & Protocols
```
src/core/models/plot_config.py
src/core/models/plot_protocol.py
src/web/models/plot_models.py
src/web/models/plot_protocols.py
```

### Plot Utility Helpers
```
src/web/pages/ui/plotting/utils/__init__.py
src/web/pages/ui/plotting/utils/grouped_bar_utils.py
src/web/pages/ui/plotting/utils/grouped_stacked_bar_helpers.py
```

---

## Questions to Answer

### Plot Factory:
- [ ] How does the factory create plot instances?
- [ ] What is the registry of available plot types?
- [ ] How is the plot type string mapped to a class?
- [ ] What parameters does the factory need?
- [ ] Is there a default plot type?

### Base Plot Pattern:
- [ ] What is the BasePlot class/protocol?
- [ ] What methods must every plot type implement?
- [ ] What is the render lifecycle? (setup → configure → render → cleanup?)
- [ ] How does a plot type declare its required settings?
- [ ] How does a plot type declare its data requirements?

### For Each Plot Type:
- [ ] What class does it define?
- [ ] What base class/protocol does it extend?
- [ ] What trace type does it use? (bar, scatter, line, etc.)
- [ ] What type-specific configuration does it support?
- [ ] What data shape does it expect? (columns, dtypes)
- [ ] How does it build traces from data?
- [ ] What rendering engine features does it use?
- [ ] Does it have type-specific settings pills?
- [ ] What helpers/utilities does it use?

### Plot Configuration:
- [ ] How does plot_config_ui.py orchestrate configuration?
- [ ] How are type-specific config widgets rendered?
- [ ] How do config components interact with config models?
- [ ] What is the base_plot_config doing vs. type-specific configs?

### Style System:
- [ ] What is the style applicator?
- [ ] How does the style factory work?
- [ ] What styles are available per plot type?
- [ ] How do styles interact with series/trace configuration?
- [ ] What is the color assignment logic?

### Trace Helpers:
- [ ] What does _trace_helpers.py provide?
- [ ] What functionality is shared across plot types?
- [ ] How are trace objects constructed?

---

## Information to Extract

### Plot Type Catalog

For each plot type:
```
### PlotTypeName
- **File**: src/web/pages/ui/plotting/types/xxx.py:NN
- **Class**: XxxPlot
- **Extends**: BasePlot
- **Purpose**: [what kind of visualization]
- **Trace Type**: [bar, scatter, line, heatmap, etc.]
- **Required Data Shape**:
  | Column | Type | Description |
  |--------|------|-------------|
  | ...    | ...  | ...         |
- **Config Component**: src/web/components/plotting/config/xxx_config.py
- **Style UI**: src/web/pages/ui/plotting/styles/xxx_ui.py
- **Unique Settings**: [type-specific settings not in base]
- **Rendering Notes**: [any engine-specific behavior]
- **Shaper Pipeline**: [typical shaper pipeline for this plot type]
```

### Plot Lifecycle
```
1. User selects plot type in UI
2. Factory creates plot instance
3. Plot declares required configuration
4. Config UI renders settings
5. User configures settings (via pills)
6. Data is shaped through pipeline
7. Plot builds traces from shaped data
8. Traces are rendered via connector (Plotly/Matplotlib)
9. Result displayed in chart_display
```

---

## Output Template

### 1. Plot Factory Documentation
```
[To be filled]
```

### 2. Base Plot Pattern
```
[To be filled]
```

### 3. Plot Type Catalog (one per type)
```
[To be filled]
```

### 4. Plot Configuration System
```
[To be filled]
```

### 5. Style System Documentation
```
[To be filled]
```

### 6. Trace Helpers Documentation
```
[To be filled]
```

### 7. Plot Lifecycle Flow
```
[To be filled]
```

### 8. Extension Guide Draft
```
[To be filled: Step-by-step "how to add a new plot type"]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `visualization/plotting-system.md`, `visualization/adding-a-new-plot.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `development/adding-a-plot.md`
- `USER_GUIDE_PLAN.md` → `plots/*` (all plot type guides)
- Step 11 (rendering) — rendering consumes plot traces
- Step 18 (data flow) — plot is the visualization step
- Step 19 (extension points) — plot factory is a key extension point
