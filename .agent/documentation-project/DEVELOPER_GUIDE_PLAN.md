# Developer Guide Generation Plan

> **Target**: `docs/developer-guide/`
> **Audience**: Software developers extending or maintaining the RING-5 application

---

## 1. Generation Order & Dependencies

The developer guide is generated **after** Phase A (analysis) is complete. Each section
draws from specific analysis steps as shown below.

---

## 2. Complete File Structure

```
docs/developer-guide/
├── index.md                                # Developer guide index & navigation
│
├── architecture/
│   ├── overview.md                         # High-level 3-layer architecture
│   ├── layer-boundaries.md                 # Import rules, dependency directions, violations
│   ├── design-patterns.md                  # Repository, DI, Protocol, Factory, FCIS patterns
│   ├── data-flow.md                        # End-to-end data journey diagram & narrative
│   └── visualization-pipeline.md           # FigureConfig → Connector → Render pipeline
│
├── core/
│   ├── models-reference.md                 # Every model, protocol, enum with all fields
│   ├── services-reference.md               # Every service method with signatures & behavior
│   ├── state-management.md                 # Repositories, state manager, session state
│   └── configuration.md                    # Config manager, schemas, validation service
│
├── parsing/
│   ├── parsing-architecture.md             # Parser protocol, registry, strategies, lifecycle
│   ├── gem5-parser-deep-dive.md            # gem5 implementation: types, scanner, Perl pool
│   └── adding-a-new-parser.md              # Step-by-step guide with complete code example
│
├── visualization/
│   ├── config-models.md                    # TraceConfig, AxisConfig, FigureConfig hierarchy
│   ├── rendering-engines.md                # Plotly vs Matplotlib connectors, comparison
│   ├── plotting-system.md                  # PlotFactory, BasePlot, type catalog, lifecycle
│   └── adding-a-new-plot.md                # Step-by-step guide with complete code example
│
├── web/
│   ├── streamlit-patterns.md               # Fragment rules, state, caching, key management
│   ├── pages-and-navigation.md             # Page catalog, routing, user journeys
│   ├── components.md                       # Component catalog with parameters & usage
│   ├── settings-pills.md                   # Pill system, widget factory, settings panels
│   ├── controllers.md                      # Controller pattern, web models, protocols
│   └── adding-a-new-component.md           # Step-by-step guide with patterns & examples
│
├── data-pipeline/
│   ├── shaper-architecture.md              # Factory, pipeline, validation, execution model
│   ├── shaper-implementations.md           # Every built-in shaper with input/output examples
│   └── adding-a-new-shaper.md              # Step-by-step guide with complete code example
│
├── export/
│   ├── export-system.md                    # Formats, presets, download pipeline
│   └── adding-export-format.md             # Step-by-step guide for new formats/presets
│
├── portfolio/
│   └── portfolio-system.md                 # Save/load, migration, schema, persistence
│
├── testing/
│   ├── testing-architecture.md             # Pyramid, taxonomy, fixture hierarchy
│   ├── writing-tests.md                    # Per-layer testing patterns with examples
│   ├── e2e-playwright-testing.md           # Playwright infrastructure, POMs, visual testing
│   └── ci-cd-pipeline.md                   # CI jobs, quality gates, architecture checks
│
├── api-reference/
│   ├── application-api.md                  # ApplicationAPI facade: all methods documented
│   ├── parsing-api.md                      # ScannerService, ParseService, WorkerPool
│   ├── shaper-api.md                       # ShaperFactory, PipelineService, built-in shapers
│   └── plotting-api.md                     # PlotFactory, BasePlot, renderers, connectors
│
└── extending/
    ├── extension-overview.md               # Summary of all extension points
    ├── adding-a-new-parser.md              # (same content as parsing/adding-a-new-parser.md)
    ├── adding-a-new-plot.md                # (same content as visualization/adding-a-new-plot.md)
    ├── adding-a-new-shaper.md              # (same content as data-pipeline/adding-a-new-shaper.md)
    ├── adding-a-new-component.md           # (same content as web/adding-a-new-component.md)
    └── adding-a-new-service.md             # Step-by-step: service class, API/Impl, DI, tests
```

---

## 3. File Generation Details

### 3.1 architecture/overview.md
- **Source**: Step 01 (architecture) + Step 18 (data flow)
- **Content**:
  - Project purpose and philosophy
  - 3-layer architecture diagram (ASCII)
  - Layer responsibilities (Data/Infrastructure, Domain, Presentation)
  - Key design decisions and their rationale
  - How layers communicate (protocols, facades)
  - Module map (which packages belong to which layer)
- **Length**: ~400-600 lines
- **Cross-references**: → layer-boundaries.md, design-patterns.md, data-flow.md

### 3.2 architecture/layer-boundaries.md
- **Source**: Step 01 (architecture)
- **Content**:
  - Allowed import directions (strict rule)
  - Package → Layer mapping table
  - Protocol interfaces at boundaries
  - Dependency Inversion examples
  - How to verify boundaries (CI check)
  - Common violations and how to fix them
- **Length**: ~200-300 lines

### 3.3 architecture/design-patterns.md
- **Source**: Step 01 (architecture) + Step 03 (services)
- **Content**:
  - Repository Pattern (with code example)
  - Dependency Injection (how services get wired)
  - Protocol Pattern (Python Protocols at boundaries)
  - Factory Pattern (ShapeFactory, PlotFactory, etc.)
  - Facade Pattern (ApplicationAPI)
  - FCIS Pattern
  - Discriminated Union Pattern
  - Component-Based architecture (why no presenters)
- **Length**: ~500-700 lines

### 3.4 architecture/data-flow.md
- **Source**: Step 18 (end-to-end data flow)
- **Content**:
  - Complete ASCII data flow diagram
  - Stage-by-stage narrative with data types
  - State changes at each stage
  - DataFrame schema evolution
  - Error paths
- **Length**: ~600-800 lines

### 3.5 architecture/visualization-pipeline.md
- **Source**: Step 07 (viz config) + Step 11 (rendering)
- **Content**:
  - FigureConfig creation flow
  - Connector dispatch
  - Trace rendering pipeline
  - Engine comparison
  - Config → Plotly/Matplotlib mapping
- **Length**: ~400-500 lines

### 3.6-3.9 core/ section
- **Source**: Steps 02, 03, 04, 06, 07
- **Content**: Detailed reference for all core components
- Combined **length**: ~1500-2000 lines

### 3.10-3.12 parsing/ section
- **Source**: Step 05 (parsing) + Step 19 (extension points)
- **Content**: Architecture, deep-dive, and extension guide
- Combined **length**: ~800-1000 lines

### 3.13-3.16 visualization/ section
- **Source**: Steps 07, 10, 11, 19
- **Content**: Config models, engines, plotting, and extension guide
- Combined **length**: ~1000-1200 lines

### 3.17-3.22 web/ section
- **Source**: Steps 08, 09, 12, 13, 19
- **Content**: Streamlit patterns, pages, components, settings, controllers, extension
- Combined **length**: ~1500-2000 lines

### 3.23-3.25 data-pipeline/ section
- **Source**: Steps 06, 19
- **Content**: Shaper architecture, implementations, extension guide
- Combined **length**: ~800-1000 lines

### 3.26-3.27 export/ section
- **Source**: Step 14
- **Content**: Export system and extension guide
- Combined **length**: ~400-500 lines

### 3.28 portfolio/ section
- **Source**: Step 15
- Combined **length**: ~300-400 lines

### 3.29-3.32 testing/ section
- **Source**: Steps 16, 17, 21-30
- **Content**:
  - Testing architecture and pyramid
  - Per-layer test writing patterns
  - **E2E Playwright testing**: POM architecture, fixture design, Streamlit patterns,
    locator strategies, wait patterns, GIF generation, visual regression, CI integration,
    test consolidation patterns, known gotchas (segmented toggle, tab DOM, etc.)
  - **State snapshot strategy**: Tiered snapshot approach (Tier 0-4), snapshot sharing
    across test suites, Portfolio save/load for test state management
  - **E2E combinatorial testing**: Settings pills × plot types × engines matrix,
    shaper pipeline composition, export preset validation
  - CI/CD pipeline and quality gates
- Combined **length**: ~1200-1500 lines (expanded with E2E section)

### 3.32-3.35 api-reference/ section
- **Source**: Steps 03, 05, 06, 10
- **Content**: Complete API reference with all method signatures
- Combined **length**: ~1500-2000 lines

### 3.36-3.41 extending/ section
- **Source**: Step 19 (extension points)
- **Content**: Extension overview + all step-by-step guides
- Combined **length**: ~1500-2000 lines

---

## 4. Writing Standards for Developer Guide

Every developer guide document must follow these rules:

1. **Start with purpose** — What problem does this solve? Why does this exist?
2. **Show architecture first** — Diagram or tree before prose
3. **Code examples are mandatory** — Every concept must have a code example from the codebase
4. **Cross-reference heavily** — Link to related docs
5. **Include file paths** — Every class/function reference includes `file:line`
6. **Show, don't just tell** — Use actual codebase patterns, not hypothetical examples
7. **Extension guides must be copy-paste ready** — A developer should be able to follow them mechanically

---

## 5. Estimated Total Size

| Section | Files | Estimated Lines |
|---------|-------|-----------------|
| architecture/ | 5 | ~2000 |
| core/ | 4 | ~2000 |
| parsing/ | 3 | ~1000 |
| visualization/ | 4 | ~1200 |
| web/ | 6 | ~2000 |
| data-pipeline/ | 3 | ~1000 |
| export/ | 2 | ~500 |
| portfolio/ | 1 | ~400 |
| testing/ | 4 | ~1500 |
| api-reference/ | 4 | ~2000 |
| extending/ | 6 | ~2000 |
| index.md | 1 | ~100 |
| **Total** | **43 files** | **~14,700 lines** |
