# Step 02 — Core Models & Type System Analysis

> **Objective**: Catalog every model, dataclass, protocol, enum, type alias, and TypeVar
> in the core layer. Document every field, its type, default value, and purpose.

---

## Scope

This step provides the **complete type catalog** of the application — every data structure
that flows through the system.

---

## Files to Analyze

### Primary Models
```
src/core/models/__init__.py
src/core/models/csv_contract.py
src/core/models/data_models.py
src/core/models/history_models.py
src/core/models/parsing_models.py
src/core/models/plot_config.py
src/core/models/plot_protocol.py
src/core/models/portfolio_models.py
src/core/models/shaper_models.py
```

### Visualization Models
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

### Configuration Models
```
src/core/models/config/__init__.py
src/core/models/config/config_manager.py
src/core/models/config/schemas/**/*
```

### Web-Layer Models (for cross-reference)
```
src/web/models/__init__.py
src/web/models/plot_models.py
src/web/models/plot_protocols.py
```

### Parsing Models (for cross-reference)
```
src/parsing/parser_protocol.py
src/parsing/gem5/models.py
```

---

## Questions to Answer

### For Every Model/Dataclass:
- [ ] What is its full qualified name and file location?
- [ ] Is it a dataclass, Pydantic model, NamedTuple, TypedDict, or plain class?
- [ ] What fields does it have? (name, type, default, required?)
- [ ] Does it have any methods? (including __post_init__, validators)
- [ ] What is its purpose in the domain?
- [ ] Where is it instantiated? Where is it consumed?
- [ ] Does it participate in any inheritance hierarchy?

### For Every Protocol:
- [ ] What methods does it define?
- [ ] What classes implement it?
- [ ] Where is it used as a type annotation?
- [ ] Is it runtime-checkable?

### For Every Enum:
- [ ] What are its members and values?
- [ ] Where is it used in the codebase?
- [ ] Is it a string enum, int enum, or standard?

### Type System Patterns:
- [ ] Are there discriminated unions? (Literal type discriminators)
- [ ] Are there generic types? (TypeVar usage)
- [ ] Are there type aliases?
- [ ] How are optional fields handled? (Optional vs | None)

---

## Information to Extract

### Complete Model Catalog

For each model, produce an entry like:

```
### ModelName
- **File**: src/core/models/xxx.py:NN
- **Type**: dataclass / Protocol / Enum / ...
- **Purpose**: [one sentence]
- **Fields**:
  | Field | Type | Default | Description |
  |-------|------|---------|-------------|
  | name  | str  | —       | ...         |
- **Methods**: [if any]
- **Used by**: [list of consumers]
- **Created by**: [list of creators]
- **Relationships**: [references to other models]
```

### Visualization Config Hierarchy

Document the complete hierarchy of visualization configuration models:
- FigureConfig (top-level)
  - AxisConfig
  - LegendConfig
  - TypographyConfig
  - AnnotationConfig
  - TraceConfig
  - DataLabelConfig
  - SeriesStyleConfig
  - TraceBuildResult

### Data Flow Types

Document how data types flow through the system:
- Parsing types → DataModels → ShaperModels → PlotConfig → VisualizationConfig

---

## Output Template

### 1. Model Inventory
```
[To be filled: Complete list of all models with file locations]
```

### 2. Model Detail Catalog
```
[To be filled: Full field-level documentation for every model]
```

### 3. Protocol Catalog
```
[To be filled: Every protocol with methods and implementors]
```

### 4. Enum Catalog
```
[To be filled: Every enum with members]
```

### 5. Type Alias Catalog
```
[To be filled: Every type alias and its expansion]
```

### 6. Visualization Config Hierarchy
```
[To be filled: Complete tree of visualization config models]
```

### 7. Model Relationship Map
```
[To be filled: Which models reference which other models]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `core/models-reference.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `reference/models-catalog.md`
- Step 07 (visualization config) — deep-dives into the visualization subset
- Step 18 (data flow) — needs model relationships
- Step 19 (extension points) — needs protocol catalog
