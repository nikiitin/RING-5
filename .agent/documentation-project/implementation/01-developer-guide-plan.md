# Developer Guide Implementation Plan

> Source analysis: Steps 01-20 (architecture, models, services, state, parsing, shapers,
> visualization, pages, components, plotting, rendering, settings, controllers, export,
> portfolio, testing, config/build, data flow, extension points, existing docs).

---

## 1. Output Structure

```
docs/developer-guide/
├── index.md                            # Landing page with quick-start
├── architecture/
│   ├── overview.md                     # 3-layer architecture (from Step 01)
│   ├── layer-boundaries.md             # Import rules, boundary analysis (Step 01)
│   ├── design-patterns.md              # 12 patterns catalog (Step 01 §10)
│   └── dependency-injection.md         # Constructor injection, composition root (Step 01 §12)
├── core/
│   ├── models-reference.md             # Complete type catalog (Step 02)
│   ├── services-reference.md           # All services with signatures (Step 03)
│   ├── state-management.md             # Repository pattern, 7 repos (Step 04)
│   └── visualization-configs.md        # FigureConfig hierarchy (Step 07)
├── parsing/
│   ├── parsing-architecture.md         # Registry, protocol, Perl integration (Step 05)
│   ├── gem5-deep-dive.md               # Scanner, parser, type evolution (Step 05)
│   └── adding-a-new-parser.md          # Extension guide (Step 19)
├── visualization/
│   ├── plotting-system.md              # 9 plot types, BasePlot, factory (Step 10)
│   ├── rendering-engines.md            # Dual engine, connectors (Step 11)
│   ├── shaper-pipeline.md              # 10 shaper types, pipeline execution (Step 06)
│   ├── settings-system.md              # 11 settings pills, widget factory (Step 12)
│   └── export-presets.md               # 13 presets, download system (Step 14)
├── web/
│   ├── pages-navigation.md             # 5 pages, navigation flow (Step 08)
│   ├── components-catalog.md           # Common, data source, data manager components (Step 09)
│   ├── controllers.md                  # Creation, pipeline, render controllers (Step 13)
│   └── portfolio-system.md             # Save/load, migration, enrichment (Step 15)
├── api-reference/
│   ├── application-api.md              # 35 public methods, 8 groups (Step 03 §2)
│   ├── services-api.md                 # ServicesAPI, ManagersAPI, DataServicesAPI, ShapersAPI (Step 03)
│   └── state-manager.md               # 40+ methods on StateManager protocol (Step 04)
├── development/
│   ├── setup.md                        # pyproject.toml, dependencies (Step 17)
│   ├── testing.md                      # pytest config, fixtures, patterns (Step 16)
│   ├── ci-cd.md                        # GitHub Actions, pre-commit (Step 17)
│   └── code-quality.md                 # Ruff, black, isort, mypy (Step 17)
└── extension-guides/
    ├── adding-a-plot-type.md           # PlotFactory, BasePlot (Step 19)
    ├── adding-a-shaper.md              # ShaperFactory, Shaper ABC (Step 19)
    ├── adding-a-renderer.md            # ConnectorProtocol (Step 19)
    ├── adding-a-data-manager.md        # DataManager ABC (Step 19)
    └── adding-a-settings-panel.md      # Settings pills (Step 19)
```

---

## 2. Writing Plan Per File

### Phase 1: Architecture (from Steps 01, 12)

| File | Source Steps | Key Content | Est. Lines |
|------|-------------|-------------|------------|
| `architecture/overview.md` | 01 §1-3 | 3-layer diagram, file counts, responsibilities | 200 |
| `architecture/layer-boundaries.md` | 01 §4 | Import matrix, boundary violations (none), coupling analysis | 250 |
| `architecture/design-patterns.md` | 01 §10 | 12 patterns with code examples | 400 |
| `architecture/dependency-injection.md` | 01 §12 | Constructor injection, composition root | 150 |

### Phase 2: Core (from Steps 02, 03, 04, 07)

| File | Source Steps | Key Content | Est. Lines |
|------|-------------|-------------|------------|
| `core/models-reference.md` | 02 | Every dataclass, TypedDict, Protocol with fields | 600 |
| `core/services-reference.md` | 03 §4-8 | All service classes with method signatures | 500 |
| `core/state-management.md` | 04 | SessionRepository, 7 child repos, state lifecycle | 400 |
| `core/visualization-configs.md` | 07 | FigureConfig tree, sentinel resolution, inheritance | 350 |

### Phase 3: Parsing (from Steps 05, 19)

| File | Source Steps | Key Content | Est. Lines |
|------|-------------|-------------|------------|
| `parsing/parsing-architecture.md` | 05 §1-5 | Registry, protocol, strategies, CSV contract | 300 |
| `parsing/gem5-deep-dive.md` | 05 §6-10 | Scanner, parser, Perl modules, type evolution | 400 |
| `parsing/adding-a-new-parser.md` | 19 §3 | Step-by-step extension guide | 200 |

### Phase 4: Visualization (from Steps 06, 10, 11, 12, 14)

| File | Source Steps | Key Content | Est. Lines |
|------|-------------|-------------|------------|
| `visualization/plotting-system.md` | 10 | 9 plot types, BasePlot, PlotFactory, trace building | 500 |
| `visualization/rendering-engines.md` | 11 | Dual engine, STYLING_PIPELINE_ORDER, connectors | 400 |
| `visualization/shaper-pipeline.md` | 06 | 10 shapers, pipeline execution, validation | 350 |
| `visualization/settings-system.md` | 12 | 11 pills, WidgetDef hierarchy, widget factory | 400 |
| `visualization/export-presets.md` | 14 | 13 presets, download section, format support | 300 |

### Phase 5: Web (from Steps 08, 09, 13, 15)

| File | Source Steps | Key Content | Est. Lines |
|------|-------------|-------------|------------|
| `web/pages-navigation.md` | 08 | 5 pages, navigation, session state flow | 300 |
| `web/components-catalog.md` | 09 | Common, data source, data manager components | 400 |
| `web/controllers.md` | 13 | 3 controllers, orchestration patterns | 250 |
| `web/portfolio-system.md` | 15 | Save/load, V1→V2 migration, enrichment | 300 |

### Phase 6: API Reference (from Steps 03, 04)

| File | Source Steps | Key Content | Est. Lines |
|------|-------------|-------------|------------|
| `api-reference/application-api.md` | 03 §2 | 35 methods in 8 groups with signatures | 400 |
| `api-reference/services-api.md` | 03 §3-6 | Sub-API protocols and implementations | 300 |
| `api-reference/state-manager.md` | 04 | StateManager protocol, 40+ methods | 350 |

### Phase 7: Development (from Steps 16, 17)

| File | Source Steps | Key Content | Est. Lines |
|------|-------------|-------------|------------|
| `development/setup.md` | 17 | pyproject.toml, dependencies, install instructions | 200 |
| `development/testing.md` | 16 | pytest config, fixtures, mock patterns, coverage | 300 |
| `development/ci-cd.md` | 17 | GitHub Actions, workflows, pre-commit hooks | 200 |
| `development/code-quality.md` | 17 | Linting, formatting, type checking tools | 150 |

### Phase 8: Extension Guides (from Step 19)

| File | Source Steps | Key Content | Est. Lines |
|------|-------------|-------------|------------|
| `extension-guides/adding-a-plot-type.md` | 19 §5 | Step-by-step with code | 250 |
| `extension-guides/adding-a-shaper.md` | 19 §4 | Step-by-step with code | 200 |
| `extension-guides/adding-a-renderer.md` | 19 §6 | ConnectorProtocol implementation | 200 |
| `extension-guides/adding-a-data-manager.md` | 19 §7 | DataManager ABC implementation | 150 |
| `extension-guides/adding-a-settings-panel.md` | 19 §8 | Settings pill extension | 150 |

---

## 3. Estimated Totals

| Phase | Files | Est. Lines |
|-------|-------|------------|
| Architecture | 4 | 1,000 |
| Core | 4 | 1,850 |
| Parsing | 3 | 900 |
| Visualization | 5 | 1,950 |
| Web | 4 | 1,250 |
| API Reference | 3 | 1,050 |
| Development | 4 | 850 |
| Extension Guides | 5 | 950 |
| **Total** | **32 files** | **~9,800 lines** |

---

## 4. Implementation Order

1. **Architecture** first — provides the mental model for everything else
2. **API Reference** second — the most-referenced section for developers
3. **Core** third — models and services are the foundation
4. **Visualization** fourth — the largest subsystem
5. **Parsing** fifth — isolated subsystem with clear boundaries
6. **Web** sixth — presentation layer documentation
7. **Extension Guides** seventh — uses patterns from all previous sections
8. **Development** last — setup/tooling can reference all other docs

---

## 5. Cross-Reference Strategy

Each document should include:
- **See Also** section linking to related documents
- **Source Analysis** reference to the step(s) that feed it
- **Code References** using `file_path:line_number` format
- **Mermaid diagrams** where architectural relationships are shown

---

## 6. Implementation Log

### Phase 1: Architecture -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `index.md` | 131 | Written |
| `architecture/overview.md` | 291 | Written |
| `architecture/layer-boundaries.md` | 356 | Written |
| `architecture/design-patterns.md` | 792 | Written |
| `architecture/dependency-injection.md` | 196 | Written |
| **Phase 1 total** | **1,766** | **Complete** |

### Phase 2: API Reference -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `api-reference/application-api.md` | 915 | Written |
| `api-reference/services-api.md` | 286 | Written |
| `api-reference/state-manager.md` | 336 | Written |
| **Phase 2 total** | **1,537** | **Complete** |

### Phase 3: Core -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `core/models-reference.md` | 1,250 | Written |
| `core/services-reference.md` | 1,227 | Written |
| `core/state-management.md` | 560 | Written |
| `core/visualization-configs.md` | 631 | Written |
| **Phase 3 total** | **3,668** | **Complete** |

### Phase 4: Visualization -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `visualization/plotting-system.md` | 490 | Written |
| `visualization/rendering-engines.md` | 589 | Written |
| `visualization/shaper-pipeline.md` | 505 | Written |
| `visualization/settings-system.md` | 517 | Written |
| `visualization/export-presets.md` | 357 | Written |
| **Phase 4 total** | **2,458** | **Complete** |

### Phase 5: Parsing -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `parsing/parsing-architecture.md` | 379 | Written |
| `parsing/gem5-deep-dive.md` | 559 | Written |
| `parsing/adding-a-new-parser.md` | 437 | Written |
| **Phase 5 total** | **1,375** | **Complete** |

### Phase 6: Web -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `web/pages-navigation.md` | 359 | Written |
| `web/components-catalog.md` | 428 | Written |
| `web/controllers.md` | 290 | Written |
| `web/portfolio-system.md` | 343 | Written |
| **Phase 6 total** | **1,420** | **Complete** |

### Phase 7: Extension Guides -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `extension-guides/adding-a-plot-type.md` | 462 | Written |
| `extension-guides/adding-a-shaper.md` | 424 | Written |
| `extension-guides/adding-a-renderer.md` | 289 | Written |
| `extension-guides/adding-a-data-manager.md` | 317 | Written |
| `extension-guides/adding-a-settings-panel.md` | 283 | Written |
| **Phase 7 total** | **1,775** | **Complete** |

### Phase 8: Development -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `development/setup.md` | 223 | Written |
| `development/testing.md` | 501 | Written |
| `development/ci-cd.md` | 240 | Written |
| `development/code-quality.md` | 243 | Written |
| **Phase 8 total** | **1,207** | **Complete** |

---

## 7. Final Summary

| Phase | Files | Lines | Status |
|-------|-------|-------|--------|
| 1. Architecture | 5 | 1,766 | Complete |
| 2. API Reference | 3 | 1,537 | Complete |
| 3. Core | 4 | 3,668 | Complete |
| 4. Visualization | 5 | 2,458 | Complete |
| 5. Parsing | 3 | 1,375 | Complete |
| 6. Web | 4 | 1,420 | Complete |
| 7. Extension Guides | 5 | 1,775 | Complete |
| 8. Development | 4 | 1,207 | Complete |
| **Total** | **33** | **15,206** | **ALL COMPLETE** |
