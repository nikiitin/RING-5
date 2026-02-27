## <!-- trunk-ignore-all(markdownlint/MD040) -->

description: Architecture standards, layering, and design patterns.
globs: src/\*_/_.py

---

# 001-architecture-standards.md

## 1. The System Architect

You design systems with strict separation of concerns, clear boundaries, and extensibility in mind.

## 2. The Three Layers (Strict Separation)

You must enforce a strict separation of concerns. The code must be divided into three distinct layers. **Never mix these.**

### Layer A: The Data Layer (Models + Parsing)

- **Location:** `src/core/models/`, `src/parsing/`
- **Responsibility:** Domain models, DTOs, file I/O, parsing.
- **Pattern:** **Protocol + Registry** for parsers (`SimulationParser` protocol, `SimulatorRegistry`). **Discriminated Unions** for models with `type` fields.
- **Output:** Returns strictly typed dataclasses or TypedDicts, NEVER raw dictionaries.
- **Rule:** Models with a `type` discriminator MUST use per-type sub-configs (e.g., `MeanShaperConfig`, `NormalizeShaperConfig`), NEVER flat mega-unions.

### Layer B: The Domain Layer (Services)

- **Location:** `src/core/services/`, `src/core/common/`
- **Responsibility:** Business logic, validation, statistical analysis, data transformations.
- **Pattern:** **Facade** for API simplification. **Factory** for shaper/plot creation.
- **Rule:** This layer knows NOTHING about Streamlit, Plotly, or Matplotlib. Operates purely on data.
- **Rule:** ALL validation logic lives here — shaper validation, config validation, etc.
- **Rule:** Single source of truth — display name mappings, type registries live in the factory only.

### Layer C: The Presentation Layer (Components + Controllers)

- **Location:** `src/web/`
- **Responsibility:** Rendering UI, gathering user input, displaying results.
- **Architecture:** **Component-Based** — NO presenters. Components are the ONLY UI abstraction.
- **Framework:** Streamlit code lives here. Controllers orchestrate components + services.

## 3. Component-Based Architecture (NEW)

### 3.1 NO Presenters

Presenters are ELIMINATED. The web layer uses only:

- **Components**: Render Streamlit widgets, return structured data. Composable.
- **Controllers**: Orchestrate components → services → state. Handle side effects (`st.rerun()`).
- **Pages**: Top-level composition only. Create controllers, inject dependencies.

### 3.2 Component Rules

- A Component renders widgets and returns data — it does NOT call domain services directly.
- Components are composable: complex UIs are built from smaller components.
- Each settings tab is its own component.
- Components NEVER mutate session_state directly — they return values for controllers to act on.

### 3.3 Component Organization (Post-Refactor v2)

```
src/web/components/
├── common/           # card_components, data_components, history_components,
│                     # layout_components, chart_display, pipeline, plot_controls,
│                     # plot_creation, plot_selector, reorderable_list
├── shapers/          # mean_config, normalize_config, selector_transformer_configs,
│                     # sort_config, split_apply_config
├── data_managers/    # data_manager (base), mixer, outlier_remover, preprocessor,
│                     # seeds_reducer, data_manager_components
├── data_source/      # data_source_components, pattern_index_selector, variable_editor
└── plotting/
    ├── config/       # base_plot_config, bar_config, line_config, scatter_config,
    │                 # grouped_bar_config, stacked_bar_config, grouped_stacked_bar_config,
    │                 # histogram_config, dual_axis_config, dual_axis_settings,
    │                 # grouped_stacked_bar_theme, plot_config_components
    ├── settings/     # axes, legend, typography, layout, data_labels, colors,
    │                 # advanced, engine, ordering, reference_line, shapes
    ├── styles/       # (reserved for future series style components)
    ├── custom_plotly/ # Custom Plotly chart component
    ├── interactive_plot.py
    └── plot_manager_components.py
```

### 3.4 Active Plot Type Classes (NOT in components/)

Plot type classes remain in `src/web/pages/ui/plotting/types/` — they are NOT components.
They use the Factory pattern and delegate to extracted component functions for UI rendering.

```
src/web/pages/ui/plotting/
├── base_plot.py              # Base class (685 lines, reduced from 992)
├── types/                    # 8 plot type classes (factory-registered)
│   └── grouped_stacked_bar_plot.py  # 506 lines (down from 1335)
├── styles/                   # base_ui.py (504 lines), applicator, bar_ui, colors, factory, etc.
├── utils/                    # grouped_bar_utils, grouped_stacked_bar_helpers
├── plot_factory.py           # Factory pattern — single source of plot registration
├── plot_renderer.py          # Rendering pipeline
├── plot_service.py           # Plot service orchestration
├── settings_pills.py         # Settings pills with progressive disclosure
├── download_section.py       # Export/download UI
└── export/presets/           # preset_manager, preset_schema
```

## 4. Mandatory Design Patterns

| Pattern                        | Context                        | Implementation                                                         |
| :----------------------------- | :----------------------------- | :--------------------------------------------------------------------- |
| **Strategy**                   | Parsing different file formats | `SimulationParser` protocol, `Gem5ParserAPI` implements it             |
| **Factory**                    | Creating plots/shapers         | `PlotFactory.create()`, `ShaperFactory.create_shaper()`                |
| **Builder**                    | Constructing FigureConfig      | `FigureConfigBuilder.with_axes(...).with_legend(...).build()`          |
| **Facade**                     | Backend API                    | `ApplicationAPI` as single entry point for web→core                    |
| **Singleton**                  | Config/Pool management         | `WorkPool`, `ConfigManager`                                            |
| **Discriminated Union**        | Models with `type` field       | Per-type TypedDicts: `MeanShaperConfig`, `NormalizeShaperConfig`, etc. |
| **Template Method**            | Data managers                  | `BaseManagerComponent`: config → preview → confirm → history           |
| **DTO (Data Transfer Object)** | Moving data between layers     | Python `dataclasses` (frozen). Do not pass raw `dict`.                 |

## 5. Discriminated Union Pattern (MANDATORY for typed models)

```python
# ✅ CORRECT — Per-type configs with discriminator
class BaseShaperConfig(TypedDict):
    type: str

class MeanShaperConfig(BaseShaperConfig):
    meanVars: list[str]
    meanAlgorithm: str
    groupingColumns: list[str]

class NormalizeShaperConfig(BaseShaperConfig):
    normalizeVars: list[str]
    normalizerColumn: str

ShaperConfig = MeanShaperConfig | NormalizeShaperConfig | SortShaperConfig | ...

# ❌ WRONG — Flat mega-union (39 fields)
class ShaperStepConfig(TypedDict, total=False):
    type: str
    meanVars: list[str]  # Only for Mean
    normalizerColumn: str  # Only for Normalize
    order_dict: dict  # Only for Sort
```

## 6. Legend Naming Convention

Legends are named by semantic role, NOT visual appearance:

| Name          | Config Keys | When Visible                              |
| ------------- | ----------- | ----------------------------------------- |
| **Primary**   | `legend_*`  | Always (when legend enabled)              |
| **Secondary** | `legend2_*` | Dual-axis or grouped plots                |
| **Tertiary**  | `legend3_*` | Numbered X-axis with category annotations |

**NEVER** use "boxed" to refer to the tertiary legend.

## 7. Single Source of Truth

Every piece of information exists in exactly ONE place:

- Shaper display names → `ShaperFactory` only
- Plot type registry → `PlotTypeRegistry` only
- Legend configuration → `LegendConfig` model only
- Palette definitions → `PALETTE_REGISTRY` only

## 8. Repository Pattern

- **Port:** The `AbstractRepository` interface (or Protocol) defining the contract.
- **Adapter:** Concrete implementations (e.g., `CsvSimulationRepository`, `SqlAlchemyRepository`).
- **Minimum API:** A repository should ideally only expose `add(entity)` and `get(id)`.
- **One Aggregate = One Repository:** Repositories must strictly return Aggregate Roots.

## 9. Dependency Injection

- **Explicit Dependencies:** Pass dependencies (UoW, Adapters) as arguments to handlers/services.
- **Composition Root:** Main entry point wires the application together.
- **No Hidden Imports:** Avoid patterns that require monkeypatching (`mock.patch`).

## 10. Functional Core, Imperative Shell (FCIS)

- **Functional Core (Domain):** Pure functions/objects that take simple data structures and return them. Infinitely testable without mocks.
- **Imperative Shell (Adapters/Services):** Gathers I/O, feeds it to the core, and applies changes.
- **Hoist I/O:** Move disk access and network calls to the extreme edges of the application (Adapters).

## 11. Backend-Frontend Sync

- Any change to the backend data processing logic **MUST** immediately trigger updates in the Streamlit session state.
- Use `st.cache_data` for expensive parsing operations to keep the UI snappy.
- Ensure cache invalidation happens when source files change.

## 12. Visualization Engine Architecture

### 12.1 FigureConfig as Single Source of Truth

- `FigureConfig` is the canonical representation of a plot's styling. ALL rendering flows through it.
- Building: `ConfigSpecBuilder.from_config(config) → resolve_config(spec) → FigureConfig`
- Applying: `FigureSpecToPlotly.apply(spec, fig)` or `FigureSpecToMatplotlib.apply(spec, ax)`
- Construction: Use `FigureConfigBuilder` for progressive construction with validation.

### 12.2 Engine Connectors are Stateless Translators

- `FigureSpecToPlotly` and `FigureSpecToMatplotlib` are pure functions. No state, no side effects beyond the figure mutation.
- Same `FigureConfig` must produce visually equivalent output in both engines.

### 12.3 Plotly Templates Map 1:1 to LaTeX Presets

- Each LaTeX preset (ISCA, MICRO, etc.) has a corresponding Plotly template: `"ring5_isca"`, `"ring5_micro"`.
- Application: `fig.update_layout(template="plotly_white+ring5_isca")`

### 12.4 Interactive Plotly Component is Sacrosanct

- `interactive_plotly_chart` in `src/web/components/common/interactive_plot.py` must NEVER be replaced with `st.plotly_chart`.

## 13. Refactor Plan Reference

The comprehensive architectural refactor plan is at `.agent/plans/architectural-refactor-v2.md`.
Read this plan before performing any refactoring work.

- It captures `relayoutData` for legend position persistence.

### 9.5 Memory Discipline

- Every `matplotlib.figure.Figure` must be closed after rendering: `plt.close(fig)`.
- In Streamlit: use `st.pyplot(fig, clear_figure=True)`.
- Store figure bytes for download, not figure objects.

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Rule 001**
