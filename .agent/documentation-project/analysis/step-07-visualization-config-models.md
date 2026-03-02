# Step 07 — Visualization Configuration Models Analysis

> **Objective**: Document the complete visualization configuration model hierarchy — every
> config class, its fields, resolution logic, defaults, and how configs flow from user
> settings to rendered plots.

---

## Scope

This step deep-dives into the **visualization data model layer** — the typed configuration
objects that describe every visual aspect of a plot. This is the bridge between user
settings and rendering engines.

---

## Files to Analyze

### Visualization Models (Core)
```
src/core/models/visualization/__init__.py
src/core/models/visualization/annotation_config.py
src/core/models/visualization/axis_config.py
src/core/models/visualization/data_label_config.py
src/core/models/visualization/figure_config.py
src/core/models/visualization/legend_config.py
src/core/models/visualization/palettes.py
src/core/models/visualization/resolvers.py
src/core/models/visualization/series_style_config.py
src/core/models/visualization/trace_build_result.py
src/core/models/visualization/trace_config.py
src/core/models/visualization/typography_config.py
```

### Visualization Services
```
src/core/services/visualization/__init__.py
src/core/services/visualization/config_resolver.py
src/core/services/visualization/palette_service.py
src/core/services/visualization/plot_interaction.py
```

### Config Builder (Rendering Layer)
```
src/web/rendering/config_builder.py
```

### Plot Configuration Models
```
src/core/models/plot_config.py
src/core/models/plot_protocol.py
```

---

## Questions to Answer

### Config Hierarchy:
- [ ] What is the complete hierarchy of configuration models?
- [ ] What is FigureConfig and what does it contain?
- [ ] How does FigureConfig relate to all other config classes?
- [ ] Is there an inheritance hierarchy or is it composition?
- [ ] What is the relationship between TraceConfig and TraceBuildResult?

### For Each Config Class:
- [ ] What fields does it define?
- [ ] What are the types and defaults?
- [ ] Is it mutable or immutable? (frozen dataclass?)
- [ ] Does it have factory methods or builders?
- [ ] Does it have validation logic?
- [ ] What is its serialization format? (for portfolio save/load)

### Resolution Logic:
- [ ] What does the config resolver do?
- [ ] How are user settings merged with defaults?
- [ ] What is the resolution order? (user → plot-type defaults → global defaults)
- [ ] How are engine-specific settings handled? (Plotly vs Matplotlib)
- [ ] What is the "resolvers.py" module doing?

### Color Palettes:
- [ ] What palettes are available?
- [ ] How is the default palette selected?
- [ ] How does the palette service work?
- [ ] Are palettes colorblind-safe? Which ones?
- [ ] How are custom colors applied?

### Config Builder:
- [ ] How does the config builder construct a FigureConfig?
- [ ] What inputs does it need?
- [ ] How does it collect settings from the UI?
- [ ] What is the build sequence?

### TraceBuildResult:
- [ ] What is a TraceBuildResult?
- [ ] How is it different from TraceConfig?
- [ ] What data does it carry to the rendering engine?
- [ ] How does it map data columns to visual properties?

---

## Information to Extract

### Config Model Hierarchy
```
FigureConfig
├── title: str
├── axes: AxisConfig
│   ├── x_label, y_label, x_range, y_range, ...
├── legend: LegendConfig
│   ├── show, position, font, naming_mode, ...
├── typography: TypographyConfig
│   ├── title_font, axis_font, legend_font, ...
├── annotations: list[AnnotationConfig]
│   ├── text, position, style, ...
├── data_labels: DataLabelConfig
│   ├── show, format, position, ...
├── traces: list[TraceConfig]
│   ├── name, type, data, style, ...
├── series_styles: list[SeriesStyleConfig]
│   ├── color, marker, line_style, ...
└── [other fields to be discovered]
```

### For Each Config Class:
```
### ConfigName
- **File**: src/core/models/visualization/xxx.py:NN
- **Type**: dataclass (frozen/mutable)
- **Purpose**: [what visual aspect it configures]
- **Fields**:
  | Field | Type | Default | Description |
  |-------|------|---------|-------------|
  | ...   | ...  | ...     | ...         |
- **Validators**: [any post_init or validation]
- **Serialization**: [how it's saved/loaded]
- **Consumers**: [which rendering code reads this]
- **Producers**: [which UI/builder code creates this]
```

### Resolution Flow
```
User UI settings → Config Builder → FigureConfig → Connector → Rendered Plot
```

---

## Output Template

### 1. Config Hierarchy Tree
```
[To be filled]
```

### 2. FigureConfig Documentation
```
[To be filled]
```

### 3. Individual Config Class Docs (one per class)
```
[To be filled]
```

### 4. Palette Catalog
```
[To be filled]
```

### 5. Resolution Logic Documentation
```
[To be filled]
```

### 6. Config Builder Flow
```
[To be filled]
```

### 7. TraceBuildResult Pipeline
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `visualization/config-models.md`, `visualization/adding-a-new-plot.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `architecture/visualization-pipeline.md`
- Step 10 (plotting system) — plot types consume these configs
- Step 11 (rendering engines) — connectors render from FigureConfig
- Step 12 (settings pills) — UI sets values that become these configs
- Step 18 (data flow) — config is built mid-pipeline
