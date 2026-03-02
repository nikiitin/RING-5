# Step 13 — Controllers & Web-Layer Patterns Analysis

> **Objective**: Document the controller layer, web-layer models, protocols, and all
> architectural patterns used in the presentation layer to organize business logic
> orchestration.

---

## Scope

This step analyzes the **web-layer architectural patterns** — how the presentation layer
organizes its interaction with the business logic, beyond simple component rendering.

---

## Files to Analyze

### Controllers
```
src/web/controllers/__init__.py
src/web/controllers/plot/__init__.py
src/web/controllers/plot/creation_controller.py    (plot creation orchestration)
src/web/controllers/plot/pipeline_controller.py    (pipeline orchestration)
src/web/controllers/plot/render_controller.py      (render orchestration)
```

### Web Models
```
src/web/models/__init__.py
src/web/models/plot_models.py                      (web-layer plot models)
src/web/models/plot_protocols.py                   (web-layer protocols)
```

### Presenters (remaining — note deleted files)
```
src/web/presenters/__init__.py
src/web/presenters/plot/__init__.py
# NOTE: config_presenter.py, controls_presenter.py, pipeline_presenter.py
#       have been DELETED in the current branch
```

### Plot Adapters
```
src/web/pages/plot_adapters.py                     (adapter between page and rendering)
```

### UI State
```
src/web/state/__init__.py
src/web/state/ui_state_manager.py                  (UI-specific state management)
```

### Tests (for understanding contracts)
```
tests/ui_logic/test_creation_controller.py
tests/ui_logic/test_render_controller.py
tests/ui_logic/test_plot_adapters.py
tests/ui_logic/test_protocols_and_models.py
```

---

## Questions to Answer

### Controller Pattern:
- [ ] What is the role of controllers in this architecture?
- [ ] How do controllers differ from presenters? (note: presenters were deleted)
- [ ] What does each controller orchestrate?
- [ ] How do controllers interact with services?
- [ ] How do controllers interact with components?
- [ ] Do controllers read/write state directly?
- [ ] Are controllers stateless or stateful?
- [ ] What is the controller lifecycle? (created per request? singleton?)

### For Each Controller:
- [ ] What is its class/function signature?
- [ ] What methods does it expose?
- [ ] What services does it depend on?
- [ ] What components/pages call it?
- [ ] What data transformations does it perform?
- [ ] What errors does it handle?

### Web Models:
- [ ] What models exist in the web layer? (vs core layer)
- [ ] Why are these separate from core models?
- [ ] How do they relate to core models? (wrappers? adapters? views?)
- [ ] What fields do they have?

### Web Protocols:
- [ ] What protocols does the web layer define?
- [ ] What do they abstract?
- [ ] What implements them?

### Plot Adapters:
- [ ] What does plot_adapters.py do?
- [ ] What adaptation is needed between pages and rendering?
- [ ] What interface does it provide?

### Presenter Deletion:
- [ ] What presenters were deleted? (config, controls, pipeline)
- [ ] What replaced them? (components? controllers?)
- [ ] What pattern shift does this represent?
- [ ] Are there any remaining references to deleted presenters?

### UI State Manager:
- [ ] What presentation-specific state does it manage?
- [ ] How does it differ from core state manager?
- [ ] What keys does it own?

---

## Information to Extract

### Controller Catalog

For each controller:
```
### ControllerName
- **File**: src/web/controllers/plot/xxx_controller.py:NN
- **Class**: XxxController
- **Purpose**: [what flow it orchestrates]
- **Dependencies**: [injected services]
- **Methods**:
  | Method | Parameters | Return | Description |
  |--------|-----------|--------|-------------|
  | ...    | ...       | ...    | ...         |
- **Called by**: [which pages/components]
- **State mutations**: [what it changes]
```

### Web Architecture Pattern Documentation
```
Document the Component-Based architecture (no presenters):
- Pages call controllers for orchestration
- Controllers call services for business logic
- Components render UI (receiving data, emitting state changes)
- Models define web-specific data shapes
- Protocols define contracts
```

---

## Output Template

### 1. Controller Catalog
```
[To be filled]
```

### 2. Web Models Documentation
```
[To be filled]
```

### 3. Web Protocols Documentation
```
[To be filled]
```

### 4. Plot Adapters Documentation
```
[To be filled]
```

### 5. Presenter Removal Analysis
```
[To be filled: What was removed, what replaced it, why]
```

### 6. UI State Manager Documentation
```
[To be filled]
```

### 7. Web Architecture Pattern Summary
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `web/controllers.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `architecture/system-overview.md` (web layer section)
- Step 18 (data flow) — controllers orchestrate the flow
- Step 19 (extension points) — controller pattern for new features
