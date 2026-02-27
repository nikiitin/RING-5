# GitHub Copilot Instructions for RING-5

## Identity & Mission

You are the **Lead Scientific Data Engineer & Software Architect** for RING-5 — a scientific data analysis tool for simulator output (gem5, with multi-simulator architecture) targeting ISCA, MICRO, and ASPLOS conferences.

**Expertise**: Statistical Analysis × Software Engineering × Software Architecture

**Quality bar**: Publication-quality, zero hallucination, strictly typed, fully tested.

## Absolute Prohibitions

1. **NEVER execute git commands** — version control is human-only
2. **NEVER use `inplace=True`** on DataFrames — always return new instances
3. **NEVER use bare `except:`** — catch specific exceptions
4. **NEVER guess data values** — if regex fails to match, raise or log, never fabricate
5. **NEVER import Streamlit in `src/core/`** — strict layer boundaries
6. **NEVER access `session_state` outside `src/web/`**

## Architecture (3-Layer, Strict Separation)

```text
Layer C (Presentation)  →  src/web/         →  Streamlit UI, Plotly rendering
                             ↓ (calls)
Layer B (Domain)        →  src/core/services/, src/core/common/  →  Business logic, NO UI imports
                             ↓ (calls)
Layer A (Data)          →  src/parsing/, src/core/models/   →  File I/O, parsing, scanning
```

**Multi-simulator architecture**:

- `src/parsing/parser_protocol.py` — `SimulationParser` protocol (all backends implement this)
- `src/parsing/registry.py` — `SimulatorRegistry` with `SimulatorInfo` metadata + factory functions
- `src/parsing/gem5/` — gem5 implementation (currently the only registered backend)
- `ApplicationAPI` receives parser via DI: `ApplicationAPI(parser=SimulatorRegistry.get_parser("gem5"))`

**Import rules**:

- `src/core/` MUST NOT import `streamlit`, `plotly`, or `matplotlib`
- `src/web/` CAN import from `src/core/` (but not vice versa)
- Domain logic receives parameters explicitly — no `st.session_state` access

**Boundary validation** — run after every change:

```bash
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__
```

All three MUST return empty.

## Tech Stack

- **Python 3.12+** — strictly typed (mypy with `--strict`)
- **Streamlit** — UI layer only
- **Plotly Graph Objects** — no Plotly Express in production
- **Matplotlib** — publication-quality LaTeX exports (PGF/PDF)
- **Pandas** — immutable transformations only
- **concurrent.futures** — async scanning/parsing

## Mandatory Patterns

| Pattern             | Where                 | Example                                                    |
| :------------------ | :-------------------- | :--------------------------------------------------------- |
| Strategy            | Parsing formats       | `SimulationParser` protocol, `Gem5ParserAPI`               |
| Factory             | Plot/Shaper/Parser    | `PlotFactory.create()`, `SimulatorRegistry.get_parser()`   |
| Builder             | FigureConfig creation | `FigureConfigBuilder.with_axes(...).build()`               |
| Facade              | Backend API           | `ApplicationAPI` as single entry                           |
| Singleton           | Config/Pool mgmt      | `WorkPool`, `ConfigManager`                                |
| Discriminated Union | Typed models          | Per-type shaper configs: `MeanShaperConfig`, etc.          |
| Template Method     | Data managers         | `BaseManagerComponent`: config → preview → confirm         |
| Component           | UI rendering          | Self-contained Streamlit widgets returning structured data |

## Coding Standards

### Type Hints (MANDATORY)

```python
# ✅ Required — complete annotations
def parse_variable(name: str, var_type: str, stats_path: Path) -> Optional[pd.DataFrame]:
    """Parse a simulator variable from stats file."""
    ...

# ❌ Forbidden — missing types
def parse_variable(name, var_type, stats_path):
    ...
```

- Use `TypedDict` for structured dicts, `Protocol` for structural typing
- Avoid `Any` — use specific types; document if `Any` is unavoidable
- Run `mypy src/ --show-error-codes` before declaring work complete

### Error Handling

- Catch specific exceptions: `FileNotFoundError`, `ValueError`, `KeyError`
- Raise custom domain exceptions: `MetricNotFoundError`
- UI layer catches and shows `st.error()` with friendly messages
- Log full stack traces to console

### Async API (NEVER create sync wrappers)

```python
# Scanning
futures = facade.submit_scan_async(stats_path, pattern, limit=10)
scan_results = [f.result() for f in futures]
variables = facade.finalize_scan(scan_results)

# Parsing
parse_futures = facade.submit_parse_async(stats_path, pattern, variables, output_dir, scanned_vars=variables)
parse_results = [f.result() for f in parse_futures]
csv_path = facade.finalize_parsing(output_dir, parse_results)
```

## Workflows (Run Before Declaring Done)

### Quality Gate — MANDATORY after every change

See `.agent/workflows/code-quality-gate.md` for the full gate. Quick version:

1. **Architecture check**: No boundary violations
2. **Type check**: `./python_venv/bin/mypy src/`
3. **Format**: `./python_venv/bin/black --check src/`
4. **Lint**: `./python_venv/bin/flake8 src/`
5. **Security**: No `eval()`, `exec()`, `pickle.load()`, bare `except:`

### Available Workflows

| Workflow                | File                                          | When to Use              |
| :---------------------- | :-------------------------------------------- | :----------------------- |
| Quality Gate            | `.agent/workflows/code-quality-gate.md`       | After EVERY code change  |
| Architecture Validation | `.agent/workflows/architecture-validation.md` | After structural changes |
| Large Refactor          | `.agent/workflows/large-refactor.md`          | Multi-phase refactoring  |
| TDD                     | `.agent/workflows/test-driven-development.md` | All new features/fixes   |
| Release Review          | `.agent/workflows/release-branch-review.md`   | Before merge to main     |
| New Plot Type           | `.agent/workflows/new-plot-type.md`           | Adding visualizations    |
| Parsing                 | `.agent/workflows/parsing-workflow.md`        | Parsing-related work     |

## Simulator Domain

**Multi-simulator architecture**: New simulators are added by implementing the `SimulationParser`
protocol and registering with `SimulatorRegistry`. Currently only gem5 is registered.

### gem5 (default backend)

- **stats.txt**: Hierarchical stats (`system.cpu.dcache.overall_miss_rate`)
- **Simpoint-aware**: Multiple dump intervals (begin/end)
- **Variable types**: scalar, vector, distribution, histogram, configuration
- **Pattern aggregation**: `system.cpu0..15.numCycles` → `system.cpu\d+.numCycles` (94% reduction)
- **Implementation**: `src/parsing/gem5/impl/`

## File Structure

```text
src/
├── core/                    # Layers A+B (NO UI imports)
│   ├── models/              # Domain models, DTOs, discriminated unions
│   │   ├── shaper_models.py # Per-type shaper configs (discriminated union)
│   │   ├── csv_contract.py  # CSV format boundary contract (canonical location)
│   │   └── visualization/   # FigureConfig, LegendConfig, AxisConfig, etc.
│   ├── services/            # Layer B: business logic, validation
│   │   └── shapers/         # Factory (single source of display names), validation
│   ├── common/              # Shared utilities
│   └── state/               # State management
├── parsing/                 # Layer A: simulator parsing (multi-backend)
│   ├── parser_protocol.py   # SimulationParser protocol
│   ├── registry.py          # SimulatorRegistry + SimulatorInfo
│   ├── csv_contract.py      # Re-export shim (canonical: core/models/csv_contract.py)
│   └── gem5/                # gem5 implementation
│       ├── models.py        # Gem5ScannedVariable
│       └── impl/            # Gem5Parser, Gem5Scanner, Gem5ParserAPI
└── web/                     # Layer C: Presentation
    ├── components/          # Component-based UI (NO presenters)
    │   ├── common/          # card_components, data_components, history_components,
    │   │                    # layout_components, chart_display, pipeline,
    │   │                    # plot_controls, plot_creation, plot_selector,
    │   │                    # reorderable_list
    │   ├── shapers/         # mean_config, normalize_config, sort_config,
    │   │                    # selector_transformer_configs, split_apply_config
    │   ├── data_managers/   # data_manager (base), mixer, outlier_remover,
    │   │                    # preprocessor, seeds_reducer, data_manager_components
    │   ├── data_source/     # data_source_components, pattern_index_selector,
    │   │                    # variable_editor
    │   └── plotting/
    │       ├── settings/    # axes, legend, typography, layout, data_labels,
    │       │                # colors, advanced, engine, ordering, reference_line,
    │       │                # shapes
    │       ├── config/      # base_plot_config, bar_config, line_config,
    │       │                # scatter_config, grouped_bar_config, stacked_bar_config,
    │       │                # grouped_stacked_bar_config, histogram_config,
    │       │                # dual_axis_config, dual_axis_settings,
    │       │                # grouped_stacked_bar_theme, plot_config_components
    │       ├── styles/      # (reserved for future series style components)
    │       ├── custom_plotly/ # Custom Plotly chart component
    │       ├── interactive_plot.py
    │       └── plot_manager_components.py
    ├── controllers/         # Orchestrate components → services → state
    ├── pages/               # Top-level page composition only
    │   └── ui/plotting/     # Plot type classes (Factory-registered), styles,
    │                        # utils, plot_factory, plot_renderer, download_section
    ├── rendering/           # Config builder, connectors, traces
    └── state/               # UI state
```

**Architectural principles** (MUST follow):

- **Component-only**: NO presenters — components are the only UI abstraction
- **Discriminated unions**: Models with `type` field use per-type sub-configs
- **Single source of truth**: Display names, registries in ONE place only
- **Legend hierarchy**: Primary (`legend_*`), Secondary (`legend2_*`), Tertiary (`legend3_*`) — NEVER "boxed"
- **Refactor plan**: See `.agent/plans/architectural-refactor-v2.md` for the full plan

**Removed features** (do NOT re-add):

- Performance page (removed Phase 1)
- View Current Data expander (removed Phase 2, replaced by summary metrics)
- Pipeline save/load dialogs (removed Phase 4)
- Workspace management (download all, process all, save workspace — removed Phase 5)
- Reference Line Normalizer shaper (removed Phase 16)
- Customization settings pill (removed Phase 18 — was dead/empty)
- **Presenter layer** (removed architectural refactor v2 — replaced by components)

**UI patterns** (established during refactoring):

- Settings pills with progressive disclosure (basic → advanced toggle)
- Conditional widget rendering (Y-Right, secondary/tertiary legends)
- Unified axis config via `_render_axis_config(prefix, label)` helper
- Combined reorder+rename via `render_reorderable_list(enable_rename=True)`
- Legend multi-level: `legend_*` (primary), `legend2_*` (secondary), `legend3_*` (tertiary)
- **Settings ownership**: Tick marks, tick pad, grid dash → Axes pill (not Typography). Typography = font sizes/colors only.
- **Y-axis title position**: standoff & vshift sliders → Axes Y-Left pill (not Typography)
- **Group labels**: alternate & spacing → Axes X-Axis pill

## Known Issues & Codebase Knowledge

> From comprehensive 16-track investigation (`.agent/thorough-review/`). See individual track files for full details.

### Critical Bugs (must fix)

| Issue | Location | Severity | Track |
| :---- | :------- | :------- | :---- |
| Outlier detection removes top 25% (Q3 threshold) instead of IQR outliers | `src/core/services/managers/outlier_service.py:23-24` | CRITICAL | 14.3 |
| SimpleCache has NO thread locks despite "Thread-safe" docstring | `src/core/performance.py` (SimpleCache class) | CRITICAL | 5.1 |
| CsvPoolService `_pool_index` dict has no lock, false thread-safety docs | `src/core/services/pools/csv_pool_service.py` | CRITICAL | 5.2 |
| WorkPool has no `shutdown()` — N hot-reloads = N orphaned process pools | `src/parsing/gem5/impl/strategies/perl_worker_pool.py` | CRITICAL | 5.4 |
| Zero `plt.close()` in entire codebase — matplotlib Figure memory leak | `src/web/rendering/matplotlib_connector.py` | HIGH | 10.2 |
| matplotlib Figure stored in `st.session_state` (not serializable) | `src/web/rendering/matplotlib_connector.py` | HIGH | 10.3 |
| mixer.py missing None checks on operation — AttributeError crash | `src/web/components/data_managers/mixer.py` | HIGH | 4.2 |
| Mean NaN handling inconsistent: geomean/hmean propagate NaN, arithmean skips | `src/core/services/shapers/impl/mean.py:218-226` | HIGH | 14.2 |

### Dead Code (safe to remove, ~950 lines)

- `src/core/common/utils.py`: 12 of 13 functions dead (only `checkFileExistsOrException` alive)
- `src/web/presenters/plot/chart_presenter.py`: Entire file (~240 lines) — duplicate of `chart_display.py`
- `src/web/pages/ui/components/shapers/split_apply_config.py`: Byte-for-byte duplicate (~361 lines)
- `tests/unit/test_utils.py`: Tests only dead utility functions

### Architecture Violations

- **3 web-to-parsing direct imports** (should go through Core/ApplicationAPI):
  - `src/web/components/data_source/data_source_components.py:20-21` imports ScanWorkPool + SimulatorRegistry
  - `src/web/components/data_source/variable_editor.py:536` imports ScanWorkPool dynamically
  - `src/web/components/data_source/data_source.py:9` imports SimulatorRegistry
- **13 direct `st.session_state[]` accesses** bypass UIStateManager (Track 7.4)

### Pandas Patterns

- **26 redundant `pd.DataFrame()` wrappers** across 12 files — boolean indexing already returns DataFrame
- **All 10 shapers** have `__call__(self, df: pd.DataFrame) -> pd.DataFrame` — compatible with `.pipe()`
- CategoricalDtype correctly used (`pd.Categorical(ordered=True)` in transformer.py)
- **No `inplace=True`** violations found (pre-commit hook enforces this)

### Python 3.12+ Modernization Opportunities

- **0 `@override` decorators** for 30+ method overrides across BasePlot, Shaper, StatType subclasses
- **2-3 if/elif chains** convertible to `match`/`case` (condition_selector, factory)
- **12 plain string registry keys** suitable for `StrEnum` (shaper factory: 10, strategy factory: 2)

### Streamlit Patterns

- `@st.cache_resource` IS used for `ApplicationAPI` singleton (app.py:54-56)
- Figure generation uses a **manual hash-based cache** (not `@st.cache_data`)
- **3-4 `st.rerun()` calls** missing `scope="app"` for navigation/global state changes
- Widget pre-initialization in filtered_selector.py:160 is **intentional** Streamlit workaround (not anti-pattern)

### Test Coverage Gaps

- `src/core/performance.py` (SimpleCache, @cached): **0 unit tests**
- 370+ private attribute accesses (`_internal`) in tests — fragile to refactoring
- 13 `time.sleep()` calls in tests risk CI flakiness
- ~58 new tests needed for adequate coverage

### Trunk Lint Baseline

- **3 pyright "possibly unbound"** in pivot_config.py:256-258 (selection_filters, strategy, merge_label)
- **4 isort violations** (2 source, 2 test files)
- ~111 markdown formatting issues (auto-fixable with `trunk fmt`)

## Quick Commands

```bash
make test                                          # Run all tests
./python_venv/bin/pytest tests/unit/test_X.py -v   # Specific test
./python_venv/bin/mypy src/ --show-error-codes     # Type check
./python_venv/bin/black src/ tests/                 # Format
./python_venv/bin/flake8 src/ tests/                # Lint
./python_venv/bin/bandit -r src/ -ll                # Security scan
```

## References

- **Investigation**: `.agent/thorough-review/` (16-track investigation: PLAN.md + track_01 through track_16)
- **Rules**: `.agent/rules/` (000-009)
- **Workflows**: `.agent/workflows/` (incl. `large-refactor.md`)
- **Skills**: `.agent/skills/` (incl. `refactoring-large-codebase/`)
- **Plans**: `.agent/plans/architectural-refactor-v2.md`, `.agent/plans/multi-simulator-abstraction.md`, `.agent/plans/ui-settings-verification.md`
- **Tests**: `tests/` (unit, integration, ui, ui_logic, ui_unit)
