# Track 11: Architecture & Extensibility

> **Priority**: MEDIUM
> **Status**: PENDING
> **Estimated items**: 6
> **Scope**: Cross-cutting architectural patterns

---

## What to Look At

### 11.1 Upward import violations: web -> parsing (3 instances) — HIGH

**Files**:
- `src/web/components/data_source/data_source_components.py` — imports from `src/parsing/`
- `src/web/components/data_source/variable_editor.py` — imports from `src/parsing/`
- A third file (to be confirmed)

**What**: The architecture mandates: Web (Layer C) -> Core (Layer B) -> Parsing (Layer A). Web should NOT import directly from Parsing. All parsing access should go through Core services (the `ApplicationAPI` facade).
**Impact**: Tight coupling between UI and parsing implementation. Adding a new simulator backend requires touching UI code.

### 11.2 Create `ColumnBasedSelector` mixin

**Files**:
- `src/core/services/shapers/impl/column_selector.py`
- `src/core/services/shapers/impl/item_selector.py`
- `src/core/services/shapers/impl/condition_selector.py`

**What**: All three implement identical column validation patterns:
```python
if column_name not in df.columns:
    raise ValueError(f"Column '{column_name}' not in DataFrame")
```
**Action**: Extract into a `ColumnBasedSelector` mixin or shared utility function.

### 11.3 Abstract `ParserBackend` protocol

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
**What**: PerlWorkerPool tightly couples subprocess management, health checks, and parsing logic. A `ParserBackend` protocol would allow:
- Testing with mock backends
- Future backends (native Python parser, WASM parser)
```python
class ParserBackend(Protocol):
    def parse_file(self, file_path: str, variables: list[str]) -> list[str]: ...
    def health_check(self) -> bool: ...
    def shutdown(self) -> None: ...
```

### 11.4 Split `BasePlot` into data + renderer

**File**: `src/web/pages/ui/plotting/base_plot.py` (~150 lines)
**What**: Mixes configuration gathering (collecting user settings) and rendering (creating Plotly/Matplotlib figures). These are separate concerns that change for different reasons.
**Action**: Split into `BasePlotData` (config gathering) and `BasePlotRenderer` (figure creation).

### 11.5 Settings component inconsistency (7 class-based, 3 function-based)

**Scope**: `src/web/components/plotting/settings/`
**What**: Of the 11 settings components:
- 7 use class-based pattern: `class XSettingsComponent: def render(self) -> dict`
- 3 use function-based pattern: `def render_x_settings(...) -> dict`
- 1 uses a hybrid

**Action**: Standardize on class-based pattern (aligning with SettingsComponentBase from Track 07).

### 11.6 Centralize widget key builder

**What**: 4 different key naming patterns across components:
- `f"{prefix}{suffix}_{plot_id}"`
- `f"{component}_{plot_id}_{suffix}"`
- `f"{suffix}_{plot_id}"`
- `f"plot_{plot_id}_{suffix}"`

**Action**: Create `src/web/components/common/widget_keys.py` with a single `build_widget_key()` function.

---

## How to Investigate

1. **For 11.1**: `grep -rn "from src.parsing\|from parsing\|import parsing" src/web/`. For each violation, determine what's being imported and whether Core already provides an equivalent accessor.
2. **For 11.2**: Diff the column validation code in all 3 selector files. Extract shared code.
3. **For 11.3**: Read PerlWorkerPool public interface. Design Protocol. Evaluate refactoring effort.
4. **For 11.4**: Read base_plot.py. Identify config-gathering methods vs rendering methods. Design split.
5. **For 11.5**: List all settings files. Categorize by pattern. Plan migration.
6. **For 11.6**: Search for all widget key constructions (`key=f"`). Categorize patterns.

---

## What We Expect to Find

- **11.1**: 2-3 direct parsing imports. Most can be redirected through ApplicationAPI or Core models.
- **11.2**: ~30 lines of duplicated validation extractable into a 10-line utility.
- **11.3**: Protocol is straightforward to define. Full refactoring of PerlWorkerPool is larger (separate phase).
- **11.4**: Split is clean — 60% of base_plot is config, 40% is rendering.
- **11.5**: Function-based components can be wrapped in classes without behavior change.
- **11.6**: 50+ key construction sites. Single utility reduces inconsistency.

---

## Outcome

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 11.1 Upward imports | **CONFIRMED** — 3 files in `src/web/` import directly from `src.parsing`: data_source_components.py:20-21 (ScanWorkPool + SimulatorRegistry), variable_editor.py:536 (ScanWorkPool dynamic), data_source.py:9 (SimulatorRegistry). No Core facade for parser access. | MEDIUM-HIGH | Create `ParsingFacade` Protocol in core. Expose parser APIs through ApplicationAPI. Remove direct web→parsing imports. |
| 11.2 ColumnBasedSelector | **CONFIRMED** — All 3 selectors duplicate `super()._verify_params()` + cast pattern. ~30 lines of duplicated Template Method calls across column_selector.py, item_selector.py, condition_selector.py. | LOW | Create `ColumnValidationMixin` or centralize in Selector base class. |
| 11.3 ParserBackend protocol | **CONFIRMED** — PerlWorkerPool (560 lines) has no protocol/abstraction. Hardcoded to subprocess-based Perl execution. `SimulationParser` protocol exists at parsing layer but doesn't cover worker-level interface. | MEDIUM | Create `ParserBackend(Protocol)` with parse/health_check/shutdown methods. Make PerlWorkerPool implement it. |
| 11.4 BasePlot split | **CONFIRMED** — 690 lines, 26 methods mixing config-gathering (18 methods: render_config_ui, _section_*, _render_*) with rendering (8 methods: create_traces, create_figure, apply_common_layout). Tight coupling to Streamlit everywhere. | MEDIUM-HIGH | Split into PlotConfigUI (all Streamlit methods) and PlotRenderer (figure creation + styling). Pass config dict between them. |
| 11.5 Settings consistency | **CONFIRMED** — 7 class-based, 4 function-based across 11 settings files. No clear rationale for split. Function-based: reference_line, shapes, engine, ordering. Class-based: layout, colors, advanced, legend, typography, data_labels, axes. | LOW | Standardize all to class-based pattern with `__init__(plot_id, plot_type)` + `render()`. |
| 11.6 Widget key builder | **CONFIRMED** — 94+ unique key patterns, 120+ total `key=` statements across 12 settings files. Inconsistent prefix/naming: some use `key_prefix`, some hardcode, some use `self.plot_id`, others `plot_id` parameter. | LOW-MEDIUM | Create `WidgetKeyBuilder` utility. Migrate all key construction to centralized builder. |

### Critical Findings Summary (items requiring fix)
1. **Web→Parsing direct imports** — MEDIUM-HIGH: 3 files violate layer architecture, tight coupling to gem5/Perl
2. **BasePlot 690-line god class** — MEDIUM-HIGH: Config + rendering mixed, 26 methods, hard to test
3. **PerlWorkerPool no abstraction** — MEDIUM: Cannot swap parser backends without code changes
