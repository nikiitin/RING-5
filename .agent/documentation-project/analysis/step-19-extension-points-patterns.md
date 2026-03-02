# Step 19 — Extension Points & Patterns Analysis

> **Objective**: Identify and document every extension point in the application — every
> protocol, factory, registry, and pattern that enables developers to add new functionality
> without modifying existing code. Produce step-by-step guides for each extension type.

---

## Scope

This is the **most critical step for the developer guide**. It synthesizes knowledge from
ALL prior steps to produce actionable "how to extend" guides.

---

## Prerequisites

This step requires completed analysis from ALL steps 01-18, specifically:
- Step 01 (architecture) — protocols and factories
- Step 05 (parsing) — parser protocol and registry
- Step 06 (shapers) — shaper protocol and factory
- Step 07 (viz config) — config model patterns
- Step 10 (plotting) — plot factory and base plot
- Step 11 (rendering) — connector protocol
- Step 12 (settings) — settings panel pattern
- Step 13 (controllers) — controller pattern

---

## Extension Points to Document

### 1. Adding a New Parser

#### Files Involved
```
src/parsing/parser_protocol.py                     (protocol to implement)
src/parsing/registry.py                            (where to register)
src/parsing/parse_service.py                       (entry point)
src/parsing/gem5/                                  (reference implementation)
```

#### Questions
- [ ] What protocol must a new parser implement?
- [ ] What methods, with exact signatures?
- [ ] How does it register with the registry?
- [ ] What scanning vs. parsing split should it follow?
- [ ] What data model must it produce? (DataFrame schema)
- [ ] What tests must be written?
- [ ] What UI changes are needed (if any)?

#### Step-by-Step Guide
```
1. Define your parser's data model (if different from gem5)
2. Implement the parser protocol
3. Implement scanning (pattern discovery)
4. Implement parsing (data extraction)
5. Register in the parser registry
6. Add tests for scanning
7. Add tests for parsing
8. Add integration test for full workflow
9. Update documentation
```

---

### 2. Adding a New Plot Type

#### Files Involved
```
src/web/pages/ui/plotting/types/                   (plot type implementations)
src/web/pages/ui/plotting/base_plot.py             (base class to extend)
src/web/pages/ui/plotting/plot_factory.py          (register here)
src/web/components/plotting/config/                (type-specific config)
src/web/pages/ui/plotting/styles/                  (type-specific styling)
src/web/rendering/trace_to_plotly.py               (Plotly rendering)
src/web/rendering/matplotlib_trace_renderer.py     (Matplotlib rendering)
```

#### Questions
- [ ] What base class/protocol must a new plot extend?
- [ ] What methods must it implement?
- [ ] How does it register with the plot factory?
- [ ] What config component does it need?
- [ ] How does it declare its data requirements?
- [ ] What trace type does it use?
- [ ] Does it need new rendering logic in connectors?
- [ ] What style UI does it need?
- [ ] What tests must be written?

#### Step-by-Step Guide
```
1. Create plot type class in types/ directory
2. Extend BasePlot
3. Implement required methods (build_traces, declare_config, etc.)
4. Create config component in config/ directory
5. Create style UI in styles/ directory (if needed)
6. Register in plot_factory.py
7. Add trace rendering in trace_to_plotly.py
8. Add trace rendering in matplotlib_trace_renderer.py
9. Add unit tests for the plot type
10. Add integration test for rendering
11. Update documentation
```

---

### 3. Adding a New Shaper (Data Transformation)

#### Files Involved
```
src/core/services/shapers/shaper.py                (base class/protocol)
src/core/services/shapers/factory.py               (register here)
src/core/services/shapers/impl/                    (implementations)
src/core/models/shaper_models.py                   (config model)
src/web/components/shapers/                        (UI config component)
```

#### Questions
- [ ] What base class/protocol must a new shaper implement?
- [ ] What is the execute/transform method signature?
- [ ] How does it register with the factory?
- [ ] What config model does it need?
- [ ] What UI config component does it need?
- [ ] How does it validate its configuration?
- [ ] What tests must be written?

#### Step-by-Step Guide
```
1. Define shaper config model in shaper_models.py
2. Create shaper implementation in impl/ directory
3. Implement the shaper protocol (execute/transform)
4. Register in factory.py
5. Create UI config component in web/components/shapers/
6. Add validation logic
7. Add unit tests with DataFrame input/output
8. Add integration test within a pipeline
9. Update documentation
```

---

### 4. Adding a New Web Component

#### Files Involved
```
src/web/components/common/                         (common components)
src/web/components/plotting/                       (plotting components)
```

#### Questions
- [ ] What is the component pattern? (function with Streamlit calls?)
- [ ] How should components handle state?
- [ ] How should components handle keys?
- [ ] How should components be tested?
- [ ] Where should common vs. feature-specific components live?

---

### 5. Adding a New Service

#### Files Involved
```
src/core/services/                                 (service layer)
src/core/application_api.py                        (facade registration)
```

#### Questions
- [ ] How should a new service be structured?
- [ ] Should it follow the API/Impl pattern?
- [ ] How should it be injected into the ApplicationAPI?
- [ ] How should it interact with repositories?
- [ ] How should it be tested?

---

### 6. Adding a New Settings Panel

#### Files Involved
```
src/web/components/plotting/settings/              (settings panels)
src/web/pages/ui/plotting/settings_pills.py        (pill registration)
```

#### Questions
- [ ] How should a new settings panel function be structured?
- [ ] How should it use the widget factory?
- [ ] How does it register as a pill?
- [ ] How do its values flow to FigureConfig?

---

### 7. Adding a New Export Preset

#### Files Involved
```
src/web/pages/ui/plotting/export/presets/           (preset system)
```

#### Questions
- [ ] What is the preset schema?
- [ ] How does a new preset define dimensions, fonts, etc.?
- [ ] How is it registered?
- [ ] How is it applied?

---

### 8. Adding a New Repository

#### Files Involved
```
src/core/state/repositories/                       (all repositories)
src/core/state/state_manager.py                    (wire new repository)
```

#### Questions
- [ ] What pattern should a new repository follow?
- [ ] How should it integrate with session state?
- [ ] How should it be registered in the state manager?

---

## Cross-Cutting Extension Concerns

- [ ] What naming conventions must be followed?
- [ ] What import rules must be respected? (layer boundaries)
- [ ] What testing requirements apply?
- [ ] What documentation must be updated?
- [ ] What CI checks will validate the extension?

---

## Output Template

### 1. Extension Points Inventory
```
[To be filled: Summary table of all extension points]
```

### 2. Adding a New Parser — Complete Guide
```
[To be filled]
```

### 3. Adding a New Plot Type — Complete Guide
```
[To be filled]
```

### 4. Adding a New Shaper — Complete Guide
```
[To be filled]
```

### 5. Adding a New Component — Complete Guide
```
[To be filled]
```

### 6. Adding a New Service — Complete Guide
```
[To be filled]
```

### 7. Adding a New Settings Panel — Complete Guide
```
[To be filled]
```

### 8. Adding an Export Preset — Complete Guide
```
[To be filled]
```

### 9. Adding a New Repository — Complete Guide
```
[To be filled]
```

### 10. Common Extension Checklist
```
[To be filled: Universal checklist for any extension]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → ALL files in `extending/` directory
- `AI_KNOWLEDGE_BASE_PLAN.md` → ALL files in `development/` directory
- This is the single most important step for the developer guide
