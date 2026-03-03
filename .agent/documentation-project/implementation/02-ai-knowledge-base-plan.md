# AI Knowledge Base Implementation Plan

> Source analysis: Steps 01-20. Optimized for AI assistant consumption (Claude, Copilot, etc.)

---

## 1. Design Principles

The AI Knowledge Base differs from the Developer Guide in structure and purpose:

- **Flat hierarchy**: Minimize nesting depth so AI tools can find content quickly
- **Self-contained pages**: Each page should be independently useful without requiring other pages
- **Decision-oriented**: Frame content as "how to decide" rather than "how it works"
- **Pattern-focused**: Emphasize recurring patterns that apply across the codebase
- **Code-heavy**: Include actual code snippets, not just descriptions

---

## 2. Output Structure

```
docs/ai-knowledge-base/
├── index.md                            # System overview + quick navigation
├── architecture/
│   ├── system-overview.md              # Complete system in one page (Step 01)
│   ├── layer-boundaries.md             # Import rules, what goes where (Step 01)
│   ├── design-patterns.md              # Pattern catalog with when-to-use (Step 01)
│   └── data-flow.md                    # End-to-end data transformation chain (Step 18)
├── reference/
│   ├── models-catalog.md               # Every model with fields (Step 02)
│   ├── services-catalog.md             # Every service with methods (Step 03)
│   ├── state-keys.md                   # All session_state keys (Steps 04, 09)
│   ├── factory-registry.md             # All factories and registries (Step 01 §7-8)
│   └── protocol-catalog.md             # All 19 protocols (Step 01 §6)
├── quick-reference/
│   ├── file-locations.md               # "Where is X?" quick lookup
│   ├── common-tasks.md                 # "How do I..." recipes
│   ├── naming-conventions.md           # Naming patterns across codebase
│   └── error-patterns.md              # Error handling patterns per layer (Step 03 §11)
├── development/
│   ├── adding-a-parser.md              # Step-by-step (Step 19)
│   ├── adding-a-plot-type.md           # Step-by-step (Step 19)
│   ├── adding-a-shaper.md              # Step-by-step (Step 19)
│   ├── adding-a-renderer.md            # Step-by-step (Step 19)
│   └── testing-patterns.md             # How to write tests (Step 16)
├── visualization/
│   ├── figure-config-guide.md          # FigureConfig hierarchy (Step 07)
│   ├── rendering-pipeline.md           # Config → Figure flow (Step 11)
│   ├── sentinel-resolution.md          # -1 sentinel system (Step 07, 11)
│   └── preset-system.md               # Export presets (Step 14)
└── troubleshooting/
    ├── common-issues.md                # Known gotchas
    ├── debugging-guide.md              # How to debug each layer
    └── performance.md                  # Performance considerations
```

---

## 3. Key Pages Detail

### `architecture/system-overview.md`
**Sources**: Step 01, Step 18
**Must contain**:
- 3-layer ASCII diagram (no Mermaid — AI tools don't render it)
- File count per layer (Core: 81, Parsing: 36, Web: ~120)
- Entry point: `app.py` → `ApplicationAPI` → `ServicesAPI` → sub-APIs
- The 4 registries, 4 factories, 19 protocols, 4 ABCs
- Complete `__init__` chain from `app.py` to all service instantiation

### `reference/models-catalog.md`
**Source**: Step 02
**Format**: One section per model, sorted alphabetically
```
### StatConfig
- **File**: `src/core/models/parsing_models.py`
- **Type**: frozen dataclass
- **Fields**: name (str), type (str), is_regex (bool), ...
- **Used by**: Gem5Parser, VariableService
```

### `reference/services-catalog.md`
**Source**: Step 03
**Format**: One section per service, sorted by sub-API
```
### ArithmeticService
- **File**: `src/core/services/managers/arithmetic_service.py`
- **Methods**: list_operators(), apply_operation(), apply_mixer(), validate_merge_inputs()
- **All static methods**: Yes
- **Key behavior**: Division replaces zero with NaN
```

### `reference/state-keys.md`
**Source**: Steps 04, 09
**Format**: Table of all st.session_state keys
```
| Key | Type | Set By | Used By | Purpose |
|-----|------|--------|---------|---------|
| api | ApplicationAPI | app.py | All pages | Singleton facade |
| current_plot | int | PlotRepository | manage_plots | Active plot index |
```

### `quick-reference/file-locations.md`
**Source**: Step 01 §3
**Format**: "I want to find..." lookup
```
- **Plot rendering**: src/web/rendering/
- **Shaper definitions**: src/core/services/shapers/impl/
- **Palette colors**: src/core/models/visualization/palettes.py
- **Export presets**: src/web/pages/ui/plotting/export/presets/
- **Portfolio save/load**: src/core/services/data_services/portfolio_service.py
```

### `quick-reference/common-tasks.md`
**Source**: Step 19
**Format**: Recipe-style instructions
```
## Add a new column operation to ArithmeticService
1. Open `src/core/services/managers/arithmetic_service.py`
2. Add to _OPERATORS dict in list_operators()
3. Add case in apply_operation() switch
4. Add tests in tests/unit/services/managers/test_arithmetic.py
```

---

## 4. Writing Guidelines for AI Knowledge Base

1. **No narrative prose** — Use tables, bullet points, and code blocks
2. **Include file paths** — Always reference `src/path/file.py:line`
3. **Show real signatures** — Copy actual method signatures from source
4. **Document gotchas** — "Warning: X looks like Y but actually does Z"
5. **Cross-reference sparingly** — Each page should be self-sufficient
6. **Use ASCII diagrams** — Not Mermaid (AI tools render text, not diagrams)

---

## 5. Estimated Totals

| Section | Files | Est. Lines |
|---------|-------|------------|
| Architecture | 4 | 1,600 |
| Reference | 5 | 2,500 |
| Quick Reference | 4 | 800 |
| Development | 5 | 1,000 |
| Visualization | 4 | 1,200 |
| Troubleshooting | 3 | 600 |
| **Total** | **25 files** | **~7,700 lines** |

---

## 6. Implementation Order

1. `architecture/system-overview.md` — Foundation for everything
2. `reference/` pages — Most-referenced by AI tools
3. `quick-reference/` — High-value for daily use
4. `development/` — Extension guides
5. `visualization/` — Complex subsystem docs
6. `troubleshooting/` — Accumulated over time

---

## 7. Implementation Log

### ALL SECTIONS -- COMPLETE (2026-03-03)

| File | Lines | Status |
|------|-------|--------|
| `index.md` | 95 | Written |
| **Architecture** | | |
| `architecture/system-overview.md` | 562 | Written |
| `architecture/layer-boundaries.md` | 261 | Written |
| `architecture/design-patterns.md` | 407 | Written |
| `architecture/data-flow.md` | 258 | Written |
| **Reference** | | |
| `reference/models-catalog.md` | 803 | Written |
| `reference/services-catalog.md` | 584 | Written |
| `reference/state-keys.md` | 470 | Written |
| `reference/factory-registry.md` | 275 | Written |
| `reference/protocol-catalog.md` | 449 | Written |
| **Quick Reference** | | |
| `quick-reference/file-locations.md` | 324 | Written |
| `quick-reference/common-tasks.md` | 585 | Written |
| `quick-reference/naming-conventions.md` | 161 | Written |
| `quick-reference/error-patterns.md` | 227 | Written |
| **Development** | | |
| `development/adding-a-parser.md` | 204 | Written |
| `development/adding-a-plot-type.md` | 247 | Written |
| `development/adding-a-shaper.md` | 231 | Written |
| `development/adding-a-renderer.md` | 282 | Written |
| `development/testing-patterns.md` | 348 | Written |
| **Visualization** | | |
| `visualization/figure-config-guide.md` | 416 | Written |
| `visualization/rendering-pipeline.md` | 325 | Written |
| `visualization/sentinel-resolution.md` | 224 | Written |
| `visualization/preset-system.md` | 308 | Written |
| **Troubleshooting** | | |
| `troubleshooting/common-issues.md` | 176 | Written |
| `troubleshooting/debugging-guide.md` | 259 | Written |
| `troubleshooting/performance.md` | 302 | Written |

### Final Summary

| Section | Files | Lines |
|---------|-------|-------|
| Index | 1 | 95 |
| Architecture | 4 | 1,488 |
| Reference | 5 | 2,581 |
| Quick Reference | 4 | 1,297 |
| Development | 5 | 1,312 |
| Visualization | 4 | 1,273 |
| Troubleshooting | 3 | 737 |
| **Total** | **26** | **8,783** |
