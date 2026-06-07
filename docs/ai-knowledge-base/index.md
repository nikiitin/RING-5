---
title: "AI Knowledge Base"
nav_order: 4
has_children: true
---

# RING-5 AI Knowledge Base

> Optimized for AI assistant consumption (Claude, Copilot, Cursor, etc.).
> Flat hierarchy, self-contained pages, decision-oriented, code-heavy.

---

## System Identity

- **App**: RING-5 Unified Engine v2 -- scientific data analysis for gem5 simulator output
- **Target**: ISCA, MICRO, ASPLOS publication-quality plots
- **Stack**: Python 3.12+, Streamlit, Plotly Graph Objects, Matplotlib (PGF/PDF), Pandas
- **Architecture**: 3-layer (Web -> Core <- Parsing), a few hundred Python modules
- **Entry point**: `app.py` -> `ApplicationAPI` (singleton via `@st.cache_resource`)

---

## Quick Navigation

### Architecture

| Page | Content |
|------|---------|
| [System Overview](architecture/system-overview.md) | 3-layer design, entry point, registries, factories, protocols |
| [Layer Boundaries](architecture/layer-boundaries.md) | Import rules, boundary matrix, what goes where |
| [Design Patterns](architecture/design-patterns.md) | 12 patterns catalog with when-to-use guidance |
| [Data Flow](architecture/data-flow.md) | End-to-end transformation chain: file -> CSV -> DataFrame -> Figure |

### Reference

| Page | Content |
|------|---------|
| [Models Catalog](reference/models-catalog.md) | Every model with fields, types, file locations |
| [Services Catalog](reference/services-catalog.md) | Every service with methods and signatures |
| [State Keys](reference/state-keys.md) | All session_state keys, repositories, lifecycle |
| [Factory & Registry](reference/factory-registry.md) | 4 factories, 4 registries with registered types |
| [Protocol Catalog](reference/protocol-catalog.md) | All 19 protocols with methods and purpose |

### Quick Reference

| Page | Content |
|------|---------|
| [File Locations](quick-reference/file-locations.md) | "Where is X?" lookup by feature |
| [Common Tasks](quick-reference/common-tasks.md) | "How do I...?" step-by-step recipes |
| [Naming Conventions](quick-reference/naming-conventions.md) | Naming patterns across codebase |
| [Error Patterns](quick-reference/error-patterns.md) | Error handling patterns per layer |

### Development Guides

| Page | Content |
|------|---------|
| [Adding a Parser](development/adding-a-parser.md) | SimulationParser protocol + SimulatorRegistry |
| [Adding a Plot Type](development/adding-a-plot-type.md) | BasePlot ABC + PlotFactory registration |
| [Adding a Shaper](development/adding-a-shaper.md) | Shaper ABC + ShaperFactory registration |
| [Adding a Renderer](development/adding-a-renderer.md) | ConnectorProtocol + EngineManager |
| [Testing Patterns](development/testing-patterns.md) | pytest config, fixtures, mock patterns |

### Visualization

| Page | Content |
|------|---------|
| [FigureConfig Guide](visualization/figure-config-guide.md) | FigureConfig hierarchy, all fields |
| [Rendering Pipeline](visualization/rendering-pipeline.md) | Config -> Figure flow, dual engine |
| [Sentinel Resolution](visualization/sentinel-resolution.md) | -1 sentinel system, resolution timing |
| [Preset System](visualization/preset-system.md) | 13 presets, PresetManager, overlay process |

### Troubleshooting

| Page | Content |
|------|---------|
| [Common Issues](troubleshooting/common-issues.md) | Known bugs, architecture violations, dead code |
| [Debugging Guide](troubleshooting/debugging-guide.md) | Per-layer debugging, Streamlit gotchas |
| [Performance](troubleshooting/performance.md) | Caching, bottlenecks, optimization patterns |

---

## Key Facts (for AI context)

- **Import rule**: `Web -> Core <- Parsing` (no violations)
- **Facade**: All UI access goes through `ApplicationAPI` (`src/core/application_api.py`)
- **State**: `RepositoryStateManager` with 7 child repos, stored in `st.session_state`
- **Plot types**: 9 (bar, line, scatter, histogram, heatmap, grouped_bar, stacked_bar, grouped_stacked_bar, dual_axis_bar_dot)
- **Shapers**: 10 registered in `ShaperFactory` (camelCase keys: mean, columnSelector, conditionSelector, itemSelector, normalize, pivotLonger, pivotWider, sort, splitApply, transformer)
- **Protocols**: 19 total (7 Core, 2 Parsing, 10 Web)
- **Factories**: 4 (ShaperFactory, StrategyFactory, StyleUIFactory, PlotFactory)
- **No `inplace=True`**: Enforced by pre-commit hook
- **No bare `except:`**: Enforced by pre-commit hook
- **No Streamlit in Core**: Enforced by pre-commit hook + CI

---

## Source

This knowledge base was generated from a deep, multi-step analysis of the codebase and is kept here
for browsing. The **canonical, continuously-maintained in-repo guide for AI agents is
[`CLAUDE.md`](../../CLAUDE.md)** (with `.claude/skills/`) at the repository root — prefer it when the
two disagree.
