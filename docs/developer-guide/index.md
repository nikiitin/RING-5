---
title: "Developer Guide"
nav_order: 3
has_children: true
---

# RING-5 Unified Engine v2 -- Developer Guide

> Comprehensive technical documentation for developers contributing to RING-5,
> a scientific data analysis tool for simulator output (gem5) targeting ISCA,
> MICRO, and ASPLOS conferences.

---

## Quick Start

```bash
# Clone and install
git clone <repo-url>
cd RING-5-unified-engine-v2
python -m venv python_venv
source python_venv/bin/activate
pip install -e ".[dev]"

# Run the app
streamlit run app.py

# Run quality checks
./python_venv/bin/mypy src/
./python_venv/bin/black --check src/
./python_venv/bin/flake8 src/
pytest tests/
```

---

## Guide Structure

### Architecture

Understand the system's 3-layer design, boundary rules, patterns, and dependency injection.

| Document | Description |
|----------|-------------|
| [Architecture Overview](architecture/overview.md) | 3-layer architecture, entry point, key elements |
| [Layer Boundaries](architecture/layer-boundaries.md) | Import rules, cross-layer analysis, validation |
| [Design Patterns](architecture/design-patterns.md) | 12 patterns catalog with code references |
| [Dependency Injection](architecture/dependency-injection.md) | Constructor injection, composition root |

### API Reference

Complete reference for the public APIs and service contracts.

| Document | Description |
|----------|-------------|
| [ApplicationAPI](api-reference/application-api.md) | Facade with 35 public methods in 8 groups |
| [ServicesAPI](api-reference/services-api.md) | Sub-API protocols: Managers, DataServices, Shapers |
| [StateManager](api-reference/state-manager.md) | State management protocol with 40+ methods |

### Core

Domain models, services, state management, and visualization configuration.

| Document | Description |
|----------|-------------|
| [Models Reference](core/models-reference.md) | Complete type catalog: dataclasses, TypedDicts, Protocols |
| [Services Reference](core/services-reference.md) | All services with method signatures |
| [State Management](core/state-management.md) | Repository pattern, 7 child repositories |
| [Visualization Configs](core/visualization-configs.md) | FigureConfig hierarchy, sentinel resolution |

### Visualization

Plotting, rendering, data transformation, settings, and export systems.

| Document | Description |
|----------|-------------|
| [Plotting System](visualization/plotting-system.md) | 9 plot types, BasePlot, PlotFactory |
| [Rendering Engines](visualization/rendering-engines.md) | Dual engine (Plotly + Matplotlib), connectors |
| [Shaper Pipeline](visualization/shaper-pipeline.md) | 10 shaper types, pipeline execution |
| [Settings System](visualization/settings-system.md) | 11 settings pills, widget factory |
| [Export & Presets](visualization/export-presets.md) | 13 presets, download system, format support |

### Parsing

Data ingestion subsystem with multi-simulator architecture.

| Document | Description |
|----------|-------------|
| [Parsing Architecture](parsing/parsing-architecture.md) | Registry, protocol, strategies, CSV contract |
| [gem5 Deep Dive](parsing/gem5-deep-dive.md) | Scanner, parser, Perl modules, type evolution |
| [Adding a New Parser](parsing/adding-a-new-parser.md) | Step-by-step extension guide |

### Web Layer

Streamlit pages, reusable components, controllers, and portfolio system.

| Document | Description |
|----------|-------------|
| [Pages & Navigation](web/pages-navigation.md) | 5 pages, navigation flow, session state |
| [Components Catalog](web/components-catalog.md) | Common, data source, data manager components |
| [Controllers](web/controllers.md) | Creation, pipeline, render controllers |
| [Portfolio System](web/portfolio-system.md) | Save/load, migration, enrichment |

### Extension Guides

Step-by-step guides for extending the system with new features.

| Document | Description |
|----------|-------------|
| [Adding a Plot Type](extension-guides/adding-a-plot-type.md) | PlotFactory, BasePlot implementation |
| [Adding a Shaper](extension-guides/adding-a-shaper.md) | ShaperFactory, Shaper ABC |
| [Adding a Renderer](extension-guides/adding-a-renderer.md) | ConnectorProtocol implementation |
| [Adding a Data Manager](extension-guides/adding-a-data-manager.md) | DataManager ABC |
| [Adding a Settings Panel](extension-guides/adding-a-settings-panel.md) | Settings pill integration |

### Development

Setup, testing, CI/CD, and code quality tooling.

| Document | Description |
|----------|-------------|
| [Development Setup](development/setup.md) | Dependencies, virtual env, pyproject.toml |
| [Testing Guide](development/testing.md) | pytest config, fixtures, mock patterns |
| [CI/CD](development/ci-cd.md) | GitHub Actions, pre-commit hooks |
| [Code Quality](development/code-quality.md) | Ruff, black, isort, mypy configuration |

---

## Architecture at a Glance

```
Layer C (Presentation)  -->  src/web/         -->  Streamlit UI, Plotly/Matplotlib rendering
                              |  (calls)
Layer B (Domain)        -->  src/core/        -->  Business logic, NO UI imports
                              |  (calls)
Layer A (Data)          -->  src/parsing/     -->  File I/O, parsing, scanning
```

**Import rule**: `Web --> Core <-- Parsing` (no violations).

**Tech stack**: Python 3.12+, Streamlit, Plotly Graph Objects, Matplotlib (PGF/PDF), Pandas.

---

## Canonical AI guide

For the maintained, single-source project guide aimed at AI coding agents (architecture, hard rules,
commands, conventions, and extension recipes), see [`CLAUDE.md`](../../CLAUDE.md) at the repository
root, with task-specific guides under [`.claude/skills/`](../../.claude/skills/).
