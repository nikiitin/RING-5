# Step 01 — Architecture & Layer Boundaries Analysis

> **Objective**: Map the complete 3-layer architecture, verify all import boundaries,
> document dependency directions, and catalog every violation or deviation.

---

## Scope

This step analyzes the **structural skeleton** of the entire application — the layer
separation that every other component depends on.

---

## Files to Analyze

### Layer A — Data / Infrastructure
```
src/parsing/__init__.py
src/parsing/parser_protocol.py
src/parsing/parse_service.py
src/parsing/registry.py
src/parsing/scanner_service.py
src/parsing/gem5/**/*.py                   (all ~25 files)
src/core/state/**/*.py                     (state_manager.py, repository_state_manager.py)
src/core/state/repositories/**/*.py        (all 9 repository files)
src/core/models/config/config_manager.py
src/core/models/config/schemas/**/*
```

### Layer B — Domain / Business Logic
```
src/core/__init__.py
src/core/application_api.py
src/core/performance.py
src/core/common/utils.py
src/core/models/**/*.py                    (all model files except config/)
src/core/services/**/*.py                  (all service files)
```

### Layer C — Presentation / Web
```
src/web/__init__.py
src/web/pages/**/*.py                      (all page files)
src/web/components/**/*.py                 (all component files)
src/web/controllers/**/*.py                (all controller files)
src/web/models/**/*.py                     (web-layer models)
src/web/presenters/**/*.py                 (remaining presenters)
src/web/rendering/**/*.py                  (all rendering files)
src/web/state/**/*.py                      (UI state manager)
```

### Entry Point
```
app.py                                     (Streamlit entry point)
```

---

## Questions to Answer

### Architecture Structure
- [ ] What is the exact boundary between each layer?
- [ ] Which `__init__.py` files define public APIs for each layer?
- [ ] What are the allowed import directions? (C → B → A, never A → C)
- [ ] Are there any circular dependencies between layers?
- [ ] Is there a clear dependency injection mechanism?

### Import Analysis
- [ ] List every cross-layer import (file → file, with exact import statement)
- [ ] Identify any violations (lower layer importing from higher layer)
- [ ] Document any "bridge" patterns used to cross boundaries
- [ ] Map the `application_api.py` facade — what does it expose from Layer B to Layer C?

### Package Structure
- [ ] Document every `__init__.py` and what it re-exports
- [ ] Identify the public API surface of each package
- [ ] Note any private modules (prefixed with `_`)
- [ ] Map sub-package relationships

### Dependency Direction
- [ ] Draw the complete dependency graph (package-level)
- [ ] Verify the Dependency Rule (dependencies point inward)
- [ ] Document any Dependency Inversion (protocols/ABCs at boundaries)
- [ ] Identify where protocols/interfaces define contracts between layers

---

## Information to Extract

### For Each Layer, Document:
1. **All packages and modules** (with file paths)
2. **Public API** (classes, functions, constants exported)
3. **Internal dependencies** (imports within the same layer)
4. **Cross-layer dependencies** (imports to/from other layers)
5. **Protocols/interfaces** used at boundaries
6. **Entry points** (how each layer is accessed from the outside)

### Architecture Patterns to Catalog:
1. **Facade Pattern** — `ApplicationAPI` as the single entry to business logic
2. **Repository Pattern** — how state is abstracted
3. **Protocol Pattern** — how interfaces are defined (Python Protocols)
4. **Factory Pattern** — where factories are used for polymorphic creation
5. **Service Layer** — how business operations are organized
6. **Dependency Injection** — how components get their dependencies

### Specific Artifacts to Produce:
- Complete import graph (package-level)
- Layer boundary matrix (who can import from whom)
- Public API catalog per layer
- Protocol/interface catalog
- Factory catalog
- Violation list (if any)

---

## Output Template

When this analysis is executed, this file will be populated with:

### 1. Layer Map
```
[To be filled: Full catalog of every module in each layer]
```

### 2. Import Graph
```
[To be filled: Package-level dependency graph]
```

### 3. Public APIs per Layer
```
[To be filled: Every public class/function per layer]
```

### 4. Protocol Catalog
```
[To be filled: Every Protocol class with its methods]
```

### 5. Factory Catalog
```
[To be filled: Every factory with what it creates]
```

### 6. Boundary Violations
```
[To be filled: Any import rule violations]
```

### 7. Architecture Patterns Found
```
[To be filled: Every design pattern instance found]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `architecture/overview.md`, `architecture/layer-boundaries.md`, `architecture/design-patterns.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `architecture/system-overview.md`, `architecture/layer-boundaries.md`, `architecture/design-patterns.md`
- Step 18 (end-to-end data flow) — needs the layer map
- Step 19 (extension points) — needs protocol and factory catalogs
