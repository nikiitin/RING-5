# Documentation Project — Master Plan

> **Goal**: Produce a comprehensive, deeply detailed, fully up-to-date documentation
> suite for the RING-5 Unified Engine v2 project, covering three audiences:
> **users**, **developers**, and **AI agents**.

---

## 1. Project Overview

This documentation project has **three phases**:

| Phase | Description | Output Location |
|-------|-------------|-----------------|
| **Phase A** | Deep codebase analysis (30 steps) | `.agent/documentation-project/analysis/` |
| **Phase B0** | Documentation media generation (screenshots, GIFs, videos via E2E tests) | `docs/user-guide/media/` |
| **Phase B** | Documentation generation | `docs/` and `.agent/knowledge/` |
| **Phase C** | Existing docs audit & update | `docs/` (in-place updates) |

---

## 2. Target Directory Structure

After completion, the documentation will follow this hierarchy:

```
docs/
├── index.md                         # Documentation homepage
├── user-guide/                      # For end-users of the application
│   ├── getting-started/
│   │   ├── installation.md
│   │   ├── quick-start.md
│   │   └── first-analysis.md
│   ├── webapp/
│   │   ├── web-interface-overview.md
│   │   ├── data-source.md
│   │   ├── data-managers.md
│   │   ├── manage-plots.md
│   │   ├── plot-settings.md
│   │   ├── export-download.md
│   │   └── portfolios.md
│   ├── plots/
│   │   ├── bar-charts.md
│   │   ├── line-plots.md
│   │   ├── scatter-plots.md
│   │   ├── histogram-plot.md
│   │   ├── heatmap-plot.md
│   │   ├── grouped-stacked-bars.md
│   │   └── dual-axis-bar-dot.md
│   └── data-transformations/
│       └── shaper-user-guide.md
│
├── developer-guide/                 # For developers extending the application
│   ├── architecture/
│   │   ├── overview.md              # High-level 3-layer architecture
│   │   ├── layer-boundaries.md      # Import rules, dependency directions
│   │   ├── design-patterns.md       # Repository, DI, FCIS, protocols
│   │   ├── data-flow.md             # End-to-end data flow diagrams
│   │   └── visualization-pipeline.md # FigureConfig → Connector → Render
│   ├── core/
│   │   ├── models-reference.md      # All models, dataclasses, protocols
│   │   ├── services-reference.md    # All services, APIs, method signatures
│   │   ├── state-management.md      # Repositories, state manager, session
│   │   └── configuration.md         # Config manager, schemas, validation
│   ├── parsing/
│   │   ├── parsing-architecture.md  # Parser protocol, registry, strategies
│   │   ├── gem5-parser-deep-dive.md # gem5-specific implementation details
│   │   └── adding-a-new-parser.md   # Step-by-step guide
│   ├── visualization/
│   │   ├── config-models.md         # TraceConfig, AxisConfig, FigureConfig...
│   │   ├── rendering-engines.md     # Plotly vs Matplotlib connectors
│   │   ├── plotting-system.md       # PlotFactory, BasePlot, plot types
│   │   └── adding-a-new-plot.md     # Step-by-step guide
│   ├── web/
│   │   ├── streamlit-patterns.md    # Fragments, state, caching, key mgmt
│   │   ├── pages-and-navigation.md  # Page structure, routing, adapters
│   │   ├── components.md            # Reusable component catalog
│   │   ├── settings-pills.md        # Settings pill pattern deep-dive
│   │   ├── controllers.md           # Controller layer patterns
│   │   └── adding-a-new-component.md # Step-by-step guide
│   ├── data-pipeline/
│   │   ├── shaper-architecture.md   # Factory, pipeline, validation
│   │   ├── shaper-implementations.md # All built-in shapers
│   │   └── adding-a-new-shaper.md   # Step-by-step guide
│   ├── export/
│   │   ├── export-system.md         # Presets, download, format support
│   │   └── adding-export-format.md  # Step-by-step guide
│   ├── portfolio/
│   │   └── portfolio-system.md      # Save, load, migration
│   ├── testing/
│   │   ├── testing-architecture.md  # Pyramid, fixtures, strategies
│   │   ├── writing-tests.md         # How to write tests for each layer
│   │   └── ci-cd-pipeline.md        # GitHub Actions, quality gates
│   ├── api-reference/
│   │   ├── application-api.md       # ApplicationAPI facade
│   │   ├── parsing-api.md           # ParseService, ScannerService
│   │   ├── shaper-api.md            # ShaperFactory, pipeline
│   │   └── plotting-api.md          # PlotFactory, renderers
│   └── extending/
│       ├── extension-overview.md    # Extension points summary
│       ├── adding-a-new-parser.md   # (symlink or copy from parsing/)
│       ├── adding-a-new-plot.md     # (symlink or copy from visualization/)
│       ├── adding-a-new-shaper.md   # (symlink or copy from data-pipeline/)
│       ├── adding-a-new-component.md # (symlink or copy from web/)
│       └── adding-a-new-service.md  # Step-by-step guide
│
.agent/
├── knowledge/                       # AI knowledge base (always up-to-date)
│   ├── README.md                    # Index and usage guide for AI agents
│   ├── architecture/
│   │   ├── system-overview.md       # Complete architecture reference
│   │   ├── layer-boundaries.md      # Import rules with file-level detail
│   │   ├── design-patterns.md       # All patterns with code examples
│   │   ├── data-flow.md             # End-to-end data flow
│   │   └── visualization-pipeline.md # Rendering pipeline detail
│   ├── development/
│   │   ├── adding-a-parser.md       # Machine-actionable parser guide
│   │   ├── adding-a-plot.md         # Machine-actionable plot guide
│   │   ├── adding-a-shaper.md       # Machine-actionable shaper guide
│   │   ├── adding-a-component.md    # Machine-actionable component guide
│   │   ├── adding-a-service.md      # Machine-actionable service guide
│   │   └── adding-export-format.md  # Machine-actionable export guide
│   ├── reference/
│   │   ├── models-catalog.md        # Every model with fields and types
│   │   ├── services-catalog.md      # Every service with methods/signatures
│   │   ├── components-catalog.md    # Every UI component with parameters
│   │   ├── file-index.md            # Every source file with purpose summary
│   │   └── test-catalog.md          # Test structure and fixture reference
│   └── standards/
│       ├── coding-standards.md      # All coding rules and conventions
│       ├── testing-standards.md     # Testing rules and patterns
│       └── quality-gate.md          # Definition of Done checklist
```

---

## 3. Phase A — Deep Codebase Analysis (30 Steps)

Each analysis step has its own file in `analysis/` and will be filled with **exhaustive
detail** during execution. The files serve as the raw knowledge base from which all
documentation is generated.

### Analysis Steps

| Step | File | Scope | Key Files |
|------|------|-------|-----------|
| 01 | `step-01-architecture-layer-boundaries.md` | 3-layer architecture, import graph, dependency rules | All `__init__.py`, import statements |
| 02 | `step-02-core-models-and-types.md` | Every model, dataclass, protocol, enum, TypeVar | `src/core/models/**/*.py` |
| 03 | `step-03-core-services-api.md` | Every service class, method, parameter, return type | `src/core/services/**/*.py` |
| 04 | `step-04-state-management-repositories.md` | State manager, all repositories, session handling | `src/core/state/**/*.py` |
| 05 | `step-05-parsing-system.md` | Parser protocol, registry, gem5 impl, Perl, strategies | `src/parsing/**/*.py` |
| 06 | `step-06-shaper-pipeline-transformations.md` | Factory, pipeline, all shapers, validation | `src/core/services/shapers/**/*.py` |
| 07 | `step-07-visualization-config-models.md` | All visualization configs (trace, axis, legend, figure) | `src/core/models/visualization/**/*.py` |
| 08 | `step-08-web-pages-navigation-flow.md` | All Streamlit pages, routing, UI flow | `src/web/pages/**/*.py` |
| 09 | `step-09-web-components-common.md` | Reusable components: cards, charts, selectors, lists | `src/web/components/common/**/*.py` |
| 10 | `step-10-plotting-system-types-factory.md` | Plot types, BasePlot, factory, renderer, settings | `src/web/pages/ui/plotting/**/*.py` |
| 11 | `step-11-rendering-engines-connectors.md` | Plotly/Matplotlib connectors, trace rendering, config builder | `src/web/rendering/**/*.py` |
| 12 | `step-12-settings-pills-widget-factory.md` | Settings pill pattern, widget factory, all settings | `src/web/components/plotting/settings/**/*.py` |
| 13 | `step-13-controllers-web-patterns.md` | Controllers, models, protocols, web-layer patterns | `src/web/controllers/**/*.py`, `src/web/models/**/*.py` |
| 14 | `step-14-export-download-presets.md` | Export system, presets, download section | `src/web/pages/ui/plotting/export/**/*.py`, `download_section.py` |
| 15 | `step-15-portfolio-system.md` | Portfolio models, service, migration, persistence | `src/core/services/data_services/portfolio_service.py`, models |
| 16 | `step-16-testing-architecture.md` | Test structure, conftest, fixtures, markers, strategies | `tests/**/*.py` |
| 17 | `step-17-configuration-build-ci.md` | pyproject.toml, Makefile, pre-commit, CI/CD, scripts | Root config files, `.github/workflows/` |
| 18 | `step-18-end-to-end-data-flow.md` | Complete data journey: parse → shape → configure → render | Cross-cutting analysis |
| 19 | `step-19-extension-points-patterns.md` | All extension hooks: new parsers, plots, shapers, etc. | Protocols, factories, registries |
| 20 | `step-20-existing-docs-audit.md` | Audit every existing doc for accuracy vs. current code | `docs/**/*.md` |
| **21** | **`step-21-playwright-e2e-current-state.md`** | **Playwright infra audit + state snapshot tier strategy (Tier 0-4)** | **`tests/visual/**/*.py`, POMs, conftest** |
| **22** | **`step-22-serenity-e2e-expansion.md`** | **Serenity BDD / Allure / reporting toolchain evaluation** | **Research + evaluation matrix** |
| **23** | **`step-23-e2e-data-source.md`** | **E2E tests: Data Source page (3 modes), produces Tier 1 snapshot** | **`src/web/pages/data_source.py`, POMs** |
| **24** | **`step-24-e2e-data-managers.md`** | **E2E tests: 5 Data Managers, uses Tier 1 snapshot** | **`src/web/pages/data_managers.py`, POMs** |
| **25** | **`step-25-e2e-plot-types.md`** | **E2E tests: 9 plot types, produces 9 Tier 2 snapshots** | **`src/web/pages/ui/plotting/types/`, POMs** |
| **26** | **`step-26-e2e-settings-pills.md`** | **E2E tests: 11 settings × 9 types × 2 engines (~198 combos)** | **`src/web/components/plotting/settings/`, POMs** |
| **27** | **`step-27-e2e-shaper-pipeline.md`** | **E2E tests: 6 shapers × pipeline combinations** | **`src/web/components/shapers/`, POMs** |
| **28** | **`step-28-e2e-engine-comparison.md`** | **E2E tests: Plotly vs Matplotlib (9 types × 2 engines)** | **`src/web/rendering/`, POMs** |
| **29** | **`step-29-e2e-export-presets.md`** | **E2E tests: 13 presets × formats × engines export** | **`src/web/pages/ui/plotting/export/`, POMs** |
| **30** | **`step-30-e2e-portfolio-cross-page-media.md`** | **E2E tests: portfolio, cross-page journeys, media assembly** | **`src/web/pages/portfolio.py`, cross-cutting** |

### Analysis Execution Order

The steps should be executed in the listed order because later steps build on knowledge
from earlier ones:

- **Steps 01-07**: Core layer analysis (architecture → models → services → state → parsing → shapers → viz config)
- **Steps 08-14**: Web layer analysis (pages → components → plotting → rendering → settings → controllers → export)
- **Steps 15-17**: Cross-cutting concerns (portfolio → testing → build/CI)
- **Steps 18-19**: Synthesis (data flow → extension points — these need knowledge from ALL prior steps)
- **Step 20**: Audit (compare existing docs against analysis findings)
- **Steps 21-22**: E2E tooling (Playwright infrastructure audit + reporting tool evaluation)
- **Steps 23-30**: E2E tests by feature area (data source → data managers → plot types → settings → shapers → engines → export → portfolio/media assembly)

> **CRITICAL**: Steps 21-30 must be completed, E2E tests implemented, and media assets
> generated (Phase B0) **BEFORE** Phase B user guide webapp sections are written. The user
> guide references specific screenshots and GIFs that must exist first.

> **STATE SNAPSHOT STRATEGY**: Steps 23-30 use a tiered state snapshot approach:
> - **Tier 0**: App launched, no data
> - **Tier 1**: Data parsed (expensive ~3 min setup, created ONCE in step 23)
> - **Tier 2**: Tier 1 + plot created (9 snapshots, one per plot type, from step 25)
> - **Tier 3**: Tier 2 + shaper pipeline applied (from step 27)
> - **Tier 4**: Tier 2 + export preset applied (from step 29)
>
> This avoids repeating expensive setup. Steps share snapshots via Portfolio save/load
> or Playwright storageState.

---

## 4. Phase B0 — Documentation Media Generation (BEFORE Phase B)

> **This phase runs AFTER analysis steps 21-30 are designed and BEFORE any user guide content is written.**

Phase B0 implements and executes the E2E tests designed in steps 21-30:

1. **Expand POMs** — Add missing locators and methods to Page Object Models (from step 21 gaps)
2. **Implement state snapshot infrastructure** — Tiered snapshot system (from step 21 design)
3. **Create E2E test suites by feature area**:
   - Data Source tests (step 23) → produce Tier 1 snapshot + media
   - Data Managers tests (step 24) → media
   - Plot Types tests (step 25) → produce 9 Tier 2 snapshots + media
   - Settings Pills tests (step 26) → media (largest surface: ~198 combos)
   - Shaper Pipeline tests (step 27) → media
   - Engine Comparison tests (step 28) → media (side-by-side comparisons)
   - Export & Presets tests (step 29) → media
   - Portfolio & Cross-page tests (step 30) → media + final validation
4. **Evaluate and integrate reporting tool** — Serenity BDD or Allure (from step 22 decision)
5. **Generate all screenshots** — 54+ static screenshots covering every page and setting
6. **Generate all GIFs** — 20+ animated GIFs showing user workflows step-by-step
7. **CI integration** — Media regeneration as part of CI pipeline
8. **Media assembly validation** — Verify all 74+ assets exist and meet quality criteria (step 30)

Output: `docs/user-guide/media/` populated with all 74+ media assets.

See steps 23-30 analysis files for the complete test specifications and media asset manifests per feature area.

---

## 5. Phase B — Documentation Generation

After all 30 analysis steps and Phase B0 media are complete, documentation is generated:

### B.1: Developer Guide (`docs/developer-guide/`)
See `DEVELOPER_GUIDE_PLAN.md` for detailed structure.

Generation order:
1. Architecture section (from steps 01, 18)
2. Core section (from steps 02, 03, 04, 06, 07)
3. Parsing section (from step 05)
4. Visualization section (from steps 07, 10, 11)
5. Web section (from steps 08, 09, 12, 13)
6. Data pipeline section (from step 06)
7. Export section (from step 14)
8. Portfolio section (from step 15)
9. Testing section (from step 16, 21)
10. API reference section (from steps 03, 05, 06, 10)
11. Extending section (from step 19)

### B.2: User Guide (`docs/user-guide/`)
See `USER_GUIDE_PLAN.md` for detailed structure.

**Requires Phase B0 complete (media assets must exist).**

Generation order:
1. Getting started — with screenshots (from steps 17, 20, 23)
2. Web application guide — with screenshots and GIFs (from steps 08, 20, 23-30)
3. Plot types — with rendered plot examples (from steps 10, 20, 25, 28)
4. Data transformations (from steps 06, 20, 27)

### B.3: AI Knowledge Base (`.agent/knowledge/`)
See `AI_KNOWLEDGE_BASE_PLAN.md` for detailed structure.

Generation order:
1. Architecture section (from steps 01, 07, 11, 18)
2. Development guides (from step 19)
3. Reference catalogs (from steps 02, 03, 09, 10, 16, 21-30)
4. Standards (from steps 16, 17)

---

## 6. Phase C — Existing Docs Audit & Migration

Based on analysis step 20, all existing documentation will be:

1. **Audited** against current codebase state
2. **Migrated** into the new hierarchy (user-guide/ or developer-guide/)
3. **Updated** with corrections from the analysis
4. **Deprecated references removed** (Performance page, old presenter pattern, etc.)
5. **New content added** where gaps are identified

---

## 7. Quality Criteria

Every generated document must satisfy:

- [ ] **Accuracy**: Every code reference verified against current source
- [ ] **Completeness**: No public API, model, or component left undocumented
- [ ] **Actionability**: Extension guides must be copy-paste-and-modify ready
- [ ] **Cross-referencing**: Every doc links to related docs
- [ ] **Up-to-date**: Reflects the current state of the `005/unified-engine-ui-v2` branch
- [ ] **No dead references**: No links to removed files, deprecated features, or old patterns
- [ ] **Visual documentation**: Every webapp page has screenshots; every multi-step workflow has a GIF
- [ ] **Reproducible media**: Every image/GIF is generated by an E2E test (no manual screenshots)

---

## 8. File Inventory

This project will produce the following files:

### Analysis files (30):
```
.agent/documentation-project/analysis/step-01-architecture-layer-boundaries.md
.agent/documentation-project/analysis/step-02-core-models-and-types.md
.agent/documentation-project/analysis/step-03-core-services-api.md
.agent/documentation-project/analysis/step-04-state-management-repositories.md
.agent/documentation-project/analysis/step-05-parsing-system.md
.agent/documentation-project/analysis/step-06-shaper-pipeline-transformations.md
.agent/documentation-project/analysis/step-07-visualization-config-models.md
.agent/documentation-project/analysis/step-08-web-pages-navigation-flow.md
.agent/documentation-project/analysis/step-09-web-components-common.md
.agent/documentation-project/analysis/step-10-plotting-system-types-factory.md
.agent/documentation-project/analysis/step-11-rendering-engines-connectors.md
.agent/documentation-project/analysis/step-12-settings-pills-widget-factory.md
.agent/documentation-project/analysis/step-13-controllers-web-patterns.md
.agent/documentation-project/analysis/step-14-export-download-presets.md
.agent/documentation-project/analysis/step-15-portfolio-system.md
.agent/documentation-project/analysis/step-16-testing-architecture.md
.agent/documentation-project/analysis/step-17-configuration-build-ci.md
.agent/documentation-project/analysis/step-18-end-to-end-data-flow.md
.agent/documentation-project/analysis/step-19-extension-points-patterns.md
.agent/documentation-project/analysis/step-20-existing-docs-audit.md
.agent/documentation-project/analysis/step-21-playwright-e2e-current-state.md
.agent/documentation-project/analysis/step-22-serenity-e2e-expansion.md
.agent/documentation-project/analysis/step-23-e2e-data-source.md
.agent/documentation-project/analysis/step-24-e2e-data-managers.md
.agent/documentation-project/analysis/step-25-e2e-plot-types.md
.agent/documentation-project/analysis/step-26-e2e-settings-pills.md
.agent/documentation-project/analysis/step-27-e2e-shaper-pipeline.md
.agent/documentation-project/analysis/step-28-e2e-engine-comparison.md
.agent/documentation-project/analysis/step-29-e2e-export-presets.md
.agent/documentation-project/analysis/step-30-e2e-portfolio-cross-page-media.md
```

### Plan files (4):
```
.agent/documentation-project/MASTER_PLAN.md          (this file)
.agent/documentation-project/DEVELOPER_GUIDE_PLAN.md
.agent/documentation-project/USER_GUIDE_PLAN.md
.agent/documentation-project/AI_KNOWLEDGE_BASE_PLAN.md
```

### Documentation media (74+ assets):
```
docs/user-guide/media/                               (54+ screenshots + 20+ GIFs)
```
See steps 23-30 analysis files for per-feature media asset manifests.

### Final documentation (~83+ files):
See individual generation plans for complete file lists.
