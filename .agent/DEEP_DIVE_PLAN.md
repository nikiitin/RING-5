# Deep-Dive Codebase Review — Master Plan

> **Created**: 2026-02-27
> **Branch**: `005/unified-engine-ui-v2`
> **Baseline**: All research scan fixes applied, 3446 tests passing (commit `899abcb`)

---

## Original Prompt (Verbatim)

> "We need to perform a really deep dive review of the whole codebase. I know it is a
> really tough and extensive task, but I know you can do it and trust in you! We need to
> look for any correctness error or any possible minimal gap in the application. We need
> to check for dead code too and to see if there is something in the UI that could be made
> more modular and easier to extend. Not only in the UI but in the core too. Actually, we
> need to check the whole src directory. The project is really big by now so, it is best if
> we first perform a modular analysis, looking for any improvement that we could do and
> then continue with a more general architectural analysis. Let's prepare the full plan for
> this. It must be a really big, deep and thoroughful plan, we cannot leave a minimal gap
> and we need to apply the best programming we can, best architecture we can and best data
> science knowledge we have into this! Please, together with this plan include a preface
> for the improvements that you skipped in the last plan, we will include them in this plan
> to fix. We need to apply the most modern approaches for everything, modern python
> techniques >=3.12, most updated, modern and better approaches and techniques for
> streamlit and the same applies for plotly and matplotlib. As before, we need to persist
> the plan into a file that will be updated with every minimal step. Include this same
> prompt into that file so we can remember from where are we departing."

---

## Preface: Previously Skipped Issues

These 3 issues were explicitly skipped in the research scan fix plan. They are now
included in this deep-dive as actionable items.

| ID | Issue | Original Reason Skipped | This Plan |
|----|-------|------------------------|-----------|
| **C9** | No concurrent thread-safety tests for PerlWorkerPool | Requires live Perl processes; deprioritized | Phase 10 — Add mock-based concurrency tests |
| **H1** | Queue starvation when all workers fail simultaneously | Edge case, existing timeout + retry | Phase 5 — Add circuit-breaker pattern |
| **H5** | Singleton re-init fails on Streamlit hot-reload | Handled by `@st.cache_resource` | Phase 5 — Add defensive re-init guard |

---

## Methodology

1. **5 parallel deep-scan agents** analyzed every file in `src/`:
   - **Core layer** (82 files) — models, services, state, shapers
   - **Parsing layer** (37 files) — gem5, types, strategies, pools
   - **Web/UI layer** (124 files) — components, controllers, pages, rendering
   - **Test coverage** (260 test files) — gaps, quality, infrastructure
   - **Architecture** — app.py, dependency flow, state management
2. Findings consolidated into **13 phases** ordered by impact and dependency.

---

## Summary Dashboard

| Category | Items Found | Severity |
|----------|------------|----------|
| Dead code to remove | 15 files/functions | CRITICAL |
| Correctness bugs | 8 issues | CRITICAL–HIGH |
| Performance improvements | 6 items | HIGH–MEDIUM |
| Code duplication to consolidate | 5 major areas | HIGH |
| Modern Python 3.12+ upgrades | 12 patterns | MEDIUM |
| Streamlit best practices | 7 anti-patterns | MEDIUM |
| Type safety improvements | 5 areas | MEDIUM |
| Test coverage gaps | 10+ untested modules | HIGH |
| Architectural improvements | 4 patterns | MEDIUM |
| Extensibility enhancements | 3 frameworks | LOW |

---

# PHASE 1: Dead Code Removal

**Priority**: CRITICAL — Remove unused code to reduce maintenance burden.

## 1.1 Remove 13 dead utility functions in `src/core/common/utils.py`

**Lines 21–224** contain legacy utility functions never called anywhere:

| Function | Lines | Replacement |
|----------|-------|-------------|
| `getElementValue()` | 21–49 | Not needed |
| `checkElementExists()` | 52–64 | Not needed |
| `checkElementExistNoException()` | 67–78 | Not needed |
| `checkEnumExistsNoException()` | 81–95 | Not needed |
| `getEnumValue()` | 98–114 | Not needed |
| `checkFilesExistOrException()` | 117–128 | `Path.exists()` |
| `checkFileExistsOrException()` | 131–142 | `Path.exists()` |
| `checkFileExists()` | 145–155 | `Path.exists()` |
| `checkDirExistsOrException()` | 158–169 | `Path.is_dir()` |
| `checkDirExists()` | 172–182 | `Path.is_dir()` |
| `createDir()` | 185–195 | `Path.mkdir()` |
| `createTmpFile()` | 198–209 | `tempfile` |
| `checkVarType()` | 212–224 | `isinstance()` |

**Action**: Remove all 13 functions. Verify no imports reference them. Keep
`normalize_user_path()` and `sanitize_glob_pattern()` which ARE used.

- [ ] Remove dead functions from utils.py
- [ ] Update `__all__` if present
- [ ] Run tests to verify no breakage

## 1.2 Delete dead UI file: `plot_manager_components.py`

**File**: `src/web/pages/ui/components/plot_manager_components.py` (~200 lines)
**Reason**: Completely replaced by controller architecture (`PlotCreationController`,
`PipelineController`, `PlotRenderController`). No imports found anywhere.

- [ ] Delete `src/web/pages/ui/components/plot_manager_components.py`
- [ ] Verify no imports reference it

## 1.3 Consolidate duplicate shaper configs

**Duplicate pair**:
- `src/web/components/shapers/split_apply_config.py`
- `src/web/pages/ui/components/shapers/split_apply_config.py`

**Action**: Keep the one in `components/shapers/`, delete the one in `pages/ui/`.
Update any imports.

- [ ] Identify which copy is imported
- [ ] Delete the unused copy
- [ ] Update imports if needed

## 1.4 Deprecate unused widget framework

**Files**:
- `src/web/rendering/widgets/widget_def.py`
- `src/web/rendering/widgets/widget_renderer.py`

**Status**: Defined but never used in web layer (only in test file).

- [ ] Evaluate if widget framework has future utility
- [ ] If not, remove files and corresponding test

**Status**: [ ] NOT STARTED

---

# PHASE 2: Correctness Fixes

**Priority**: CRITICAL — Fix bugs that can produce wrong results or crashes.

## 2.1 Malformed stats line crash in `gem5_parse_work.py`

**File**: `src/parsing/gem5/impl/strategies/gem5_parse_work.py:92–103`
**Bug**: `_parseLine()` splits on `/` and accesses `parts[2]` without bounds check.
Malformed Perl output (e.g., missing value) causes `IndexError`, killing the worker
and failing the entire batch.

```python
# Current (unsafe):
parts = line.split("/")
return parts[0], parts[1], parts[2]

# Fix:
parts = line.split("/")
if len(parts) < 3:
    logger.warning("Malformed line skipped: %s", line[:100])
    return None  # Caller must handle None
return parts[0], parts[1], parts[2]
```

- [ ] Add bounds check in `_parseLine()`
- [ ] Update caller to handle `None` return
- [ ] Add test for malformed input

## 2.2 Worker pipe leak on process death

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py:306–315`
**Bug**: `shutdown()` only closes pipes if `process.poll() is None`. If process died
before shutdown, pipes remain open.

**Fix**: Close pipes unconditionally in a `finally` block.

- [ ] Move pipe closing to `finally` block
- [ ] Add test for dead-process cleanup

## 2.3 Timeout thread accumulation in `_read_line_with_timeout()`

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py:134–136`
**Bug**: Spawns daemon thread per read with no explicit cleanup. Rapid timeouts
(e.g., unresponsive Perl) accumulate leaked threads holding file handles.

**Fix**: Use `selectors` module or `poll()` with timeout instead of threads.

- [ ] Replace threaded read with `select`/`poll` approach
- [ ] Add test for rapid timeout scenario

## 2.4 Dictionary access safety in `config_validation_service.py`

**File**: `src/core/services/config_validation_service.py:198–223`
**Bug**: Direct dict access `plot_config["data"]["hue"]` without validation. `KeyError`
if `"data"` key missing.

**Fix**: Use `.get()` with defaults or validate structure first.

- [ ] Add defensive `.get()` access
- [ ] Add test for missing keys

## 2.5 CSV header incompleteness in `gem5_parser.py`

**File**: `src/parsing/gem5/impl/gem5_parser.py:269–282`
**Bug**: Header built from first result only. If first file is missing a variable that
later files have, header is permanently incomplete.

**Fix**: Build header from union of all results, or validate against all results.

- [ ] Build header from variable config, not first result sample
- [ ] Add test for files with different variable sets

## 2.6 Broad exception handlers — add specificity

| File | Line | Current | Should Be |
|------|------|---------|-----------|
| `portfolio_service.py` | 139 | `except Exception:` | `except (TypeError, KeyError, ValueError):` |
| `pivot.py` | 49 | `except Exception:` | `except (re.error, IndexError):` |

- [ ] Narrow exception types in portfolio_service.py
- [ ] Narrow exception types in pivot.py

## 2.7 `is_busy` flag needs threading lock

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py:467–487`
**Bug**: `is_busy` set/read without lock. Health monitor can read `is_busy=False` at
exact moment parse starts, attempting to ping worker mid-parse.

**Fix**: Use `threading.Lock` around `is_busy` access in both parse and health check.

- [ ] Add `threading.Lock` for `is_busy` flag
- [ ] Update health monitor to acquire lock
- [ ] Add test for concurrent access

## 2.8 Health monitor thread graceful stop

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py:404–411`
**Bug**: Health monitor is daemon thread with `_shutdown` flag but no `thread.join()`.
Dangling thread can interfere with subsequent pool creation.

**Fix**: Call `thread.join(timeout=5)` in `shutdown()`.

- [ ] Add `thread.join()` to shutdown
- [ ] Add test verifying clean shutdown

**Status**: [ ] NOT STARTED

---

# PHASE 3: Performance Optimizations

**Priority**: HIGH — Improve responsiveness for large datasets.

## 3.1 Pre-compile regex patterns in parser

**File**: `src/parsing/gem5/impl/gem5_parser.py:125`
**Issue**: `re.compile(config.name)` called inside loop for each config, each parse job.
With 20 regex variables: compiles 20 patterns per file.

**Fix**: Pre-compile patterns once in strategy initialization, cache in dict.

- [ ] Cache compiled patterns in strategy `__init__`
- [ ] Pass cache to parse work items

## 3.2 Remove unnecessary `pd.DataFrame()` wrapping

| File | Line | Current | Fix |
|------|------|---------|-----|
| `outlier_service.py` | 24, 27 | `pd.DataFrame(df[...])` | `df[...]` |
| `reduction_service.py` | 31 | `pd.DataFrame(result_df[cols])` | `result_df[cols]` |

Boolean indexing already returns a DataFrame.

- [ ] Remove unnecessary `pd.DataFrame()` wraps
- [ ] Add type annotations to confirm return types

## 3.3 Reduce path normalization duplication

**Files**: `gem5_parser.py:109` + `simple.py:132`
**Issue**: `normalize_user_path()` called in both `submit_parse_async()` and
`get_work_items()` (duplicate).

**Fix**: Normalize once, pass the normalized path.

- [ ] Remove duplicate normalization call

## 3.4 Use `@st.cache_data` for CSV loading

**File**: `src/web/components/data_source/data_source_components.py`
**Issue**: CSV files loaded without caching. Re-parsed on every rerun.

**Fix**: Wrap with `@st.cache_data(ttl=3600)`.

- [ ] Add `@st.cache_data` to CSV load function
- [ ] Handle cache invalidation on file change

## 3.5 Replace Matplotlib figure in session state

**File**: `src/web/components/common/chart_display.py:172`
**Issue**: Stores `matplotlib.figure.Figure` in `st.session_state`. Can't serialize,
breaks on page reload.

**Fix**: Use `@st.cache_data(ttl=3600)` or re-render on demand.

- [ ] Remove mpl figure from session state
- [ ] Cache or re-render as needed

## 3.6 Previously skipped H5 — Singleton re-init guard

**File**: `src/parsing/gem5/impl/pool/work_pool.py:43`
**Issue**: Singleton pools fail to reinitialize after Streamlit hot-reload clears
`@st.cache_resource`.

**Fix**: Add defensive check in `get_instance()` — if executor is shut down, create new.

- [ ] Add `_is_alive()` check in singleton accessor
- [ ] Test hot-reload scenario

**Status**: [ ] NOT STARTED

---

# PHASE 4: Code Duplication Consolidation

**Priority**: HIGH — Reduce maintenance surface.

## 4.1 Merge `ChartDisplayComponent` and `ChartPresenter`

**Files**:
- `src/web/components/common/chart_display.py` (~260 lines)
- `src/web/presenters/plot/chart_presenter.py` (~260 lines)

**Status**: Nearly identical implementations. Duplicate rendering logic.

**Action**: Keep `ChartDisplayComponent`, delete `ChartPresenter`, update imports.

- [ ] Identify all imports of `ChartPresenter`
- [ ] Redirect to `ChartDisplayComponent`
- [ ] Delete `chart_presenter.py`
- [ ] Run tests

## 4.2 Centralize session state access through `UIStateManager`

**Files with direct `st.session_state[]` access** (bypassing UIStateManager):
- `seeds_reducer.py:110–112`
- `mixer.py:50–65`
- `preprocessor.py:54–65`
- `outlier_remover.py:59–66`
- `colors_settings.py:242–244`
- `base_ui.py:358–360`

**Action**: Extend `UIStateManager` with `_ManagerUIState` methods for data managers.

- [ ] Add data manager state methods to UIStateManager
- [ ] Migrate 6 files to use UIStateManager
- [ ] Run tests

## 4.3 Create `SettingsComponentBase` class

**Issue**: Every settings component reimplements widget key building:
```python
key=f"{key_prefix}show_val_{self.plot_id}"
```

**Action**: Create base class with `widget_key(suffix)` method, standardized
`render() -> dict[str, Any]` signature.

- [ ] Create `SettingsComponentBase` in `src/web/components/plotting/settings/`
- [ ] Migrate axes, legend, layout, data_labels settings to inherit from it
- [ ] Remove duplicated key-building code

## 4.4 Extract shaper UI utilities

**Functions in `pivot_config.py`** that should be shared:
- `extract_with_pattern()` (line 30)
- `detect_common_pattern()` (line 17)

**Action**: Move to `src/web/components/shapers/utils.py`.

- [ ] Create `utils.py` with shared functions
- [ ] Update imports in `pivot_config.py`

## 4.5 Centralize widget key builder

**Issue**: 4 different key naming patterns across components. No consistency.

**Action**: Create `src/web/components/common/widget_keys.py`:
```python
def build_widget_key(component: str, plot_id: int, suffix: str = "") -> str:
    parts = [component, str(plot_id)]
    if suffix:
        parts.append(suffix)
    return "_".join(parts)
```

- [ ] Create widget key builder module
- [ ] Gradually migrate components to use it

**Status**: [ ] NOT STARTED

---

# PHASE 5: Parsing Layer Robustness

**Priority**: HIGH — Harden the parsing subsystem.

## 5.1 Previously skipped H1 — Circuit breaker for worker failures

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py:460–485`
**Issue**: If all workers fail simultaneously, queue starves. Current timeout + retry
eventually raises `RuntimeError`, but recovery is slow.

**Fix**: Implement circuit-breaker pattern:
- After N consecutive failures within T seconds, fail fast with clear error
- Auto-reset after cooldown period

- [ ] Add circuit breaker counter
- [ ] Fail fast when threshold reached
- [ ] Add cooldown and auto-reset
- [ ] Add test for all-workers-fail scenario

## 5.2 Abstract `ParserBackend` protocol

**Current**: Perl worker pool tightly coupled to subprocess management, health checks,
and parsing logic.

**Action**: Create `ParserBackend` protocol:
```python
class ParserBackend(Protocol):
    def parse_file(self, file_path: str, variables: list[str]) -> list[str]: ...
    def health_check(self) -> bool: ...
    def shutdown(self) -> None: ...
```

- [ ] Define `ParserBackend` protocol
- [ ] Refactor `PerlWorkerPool` to implement it
- [ ] Update strategy to depend on protocol

## 5.3 Tighten `type_mapper.py` typing

**File**: `src/parsing/gem5/types/type_mapper.py:61`
**Issue**: `var_config: ... | Any` — overly loose. Duck-typing fallback at lines 76–101
accepts any object with 4 attributes.

**Fix**: Remove `Any` from union. Add proper `StatConfig` protocol check.

- [ ] Remove `Any` from `create_stat()` signature
- [ ] Replace `hasattr()` chain with protocol check

## 5.4 Validate CSV header completeness

**File**: `src/parsing/gem5/impl/gem5_parser.py:269–282`
**Issue**: Header built from first file's variables. Missing variables from other files
create incomplete CSV.

**Fix**: Build header from the variable config (source of truth), not sample data.

- [ ] Change header source to variable config list
- [ ] Add warning when file lacks expected variables

**Status**: [ ] NOT STARTED

---

# PHASE 6: Modern Python 3.12+ Upgrades

**Priority**: MEDIUM — Modernize codebase for maintainability.

## 6.1 `StrEnum` for registry keys

**Files**: `src/core/services/shapers/factory.py`, `src/parsing/gem5/impl/strategies/factory.py`

```python
# Before:
_registry: dict[str, type[Shaper]] = {"mean": Mean, "columnSelector": ColumnSelector, ...}

# After:
from enum import StrEnum

class ShaperType(StrEnum):
    MEAN = "mean"
    COLUMN_SELECTOR = "columnSelector"
    NORMALIZE = "normalize"
    SORT = "sort"
    PIVOT_LONGER = "pivotLonger"
    PIVOT_WIDER = "pivotWider"
    ITEM_SELECTOR = "itemSelector"
    COLUMN_SELECTOR_TYPE = "columnSelector"
    CONDITION_SELECTOR = "conditionSelector"
    TRANSFORMER = "transformer"
    SPLIT_APPLY = "splitApply"
```

- [ ] Create `ShaperType` StrEnum
- [ ] Create `StrategyType` StrEnum for parsing
- [ ] Update factories to use enums
- [ ] Update config models to reference enums

## 6.2 `match` statements for dispatch

**Files to convert**:
| File | Current | Lines |
|------|---------|-------|
| `condition_selector.py` | if/elif chain for mode | 100–109 |
| `gem5_parse_work.py` | if/elif for type dispatch | 216–225 |
| `factory.py` (parsing) | if/elif for strategy | 21–49 |

- [ ] Convert `condition_selector.py` to `match`
- [ ] Convert `gem5_parse_work.py` to `match`
- [ ] Convert parsing `factory.py` to `match`

## 6.3 PEP 695 `type` statements

```python
# Before:
from typing import TypeAlias
ShaperStepConfig: TypeAlias = Union[MeanShaperConfig, ...]

# After (Python 3.12+):
type ShaperStepConfig = MeanShaperConfig | NormalizeShaperConfig | ...
```

**Files**: `shaper_models.py`, `data_models.py`, `plot_models.py`

- [ ] Convert `TypeAlias` declarations to `type` statements
- [ ] Update imports

## 6.4 `typing.override` decorator (Python 3.12+)

Add `@override` to all method overrides in:
- `BasePlot` subclasses (8 plot types)
- `Shaper` subclasses (10 shapers)
- `StatType` subclasses (5 types)

- [ ] Add `@override` to all overridden methods
- [ ] Verify mypy catches missing overrides

## 6.5 Replace `TypeVar` with PEP 695 generics where applicable

```python
# Before:
T = TypeVar("T")
def func(x: T) -> T: ...

# After (Python 3.12+):
def func[T](x: T) -> T: ...
```

- [ ] Identify all `TypeVar` usages
- [ ] Convert to PEP 695 syntax where appropriate

## 6.6 Use `Never` type for exhaustive checks

```python
from typing import Never

def assert_never(x: Never) -> Never:
    raise AssertionError(f"Unhandled: {x}")
```

Add to `match` statements for exhaustive dispatch.

- [ ] Add `case _: assert_never(x)` to all match statements

**Status**: [ ] NOT STARTED

---

# PHASE 7: Streamlit Best Practices

**Priority**: MEDIUM — Fix anti-patterns, adopt modern patterns.

## 7.1 Fix widget value pre-initialization anti-pattern

**File**: `src/web/components/common/filtered_selector.py:160`

```python
# Anti-pattern:
st.session_state[key] = widget_default  # Set BEFORE widget render
visible_selection = st.multiselect(...)  # Then render

# Fix: Use widget's value= parameter:
visible_selection = st.multiselect(..., default=widget_default)
```

- [ ] Remove pre-initialization of session state before widgets
- [ ] Use `default=` / `value=` parameters instead

## 7.2 Add `st.status()` to plot generation

**File**: `src/web/controllers/plot/render_controller.py:192`
**Issue**: Plot generation shows no progress feedback.

**Fix**: Wrap figure generation in `with st.status("Generating plot..."):`.

- [ ] Add `st.status()` around plot generation
- [ ] Include step progress (data prep, trace creation, layout)

## 7.3 Add `@st.cache_data` for expensive computations

**Opportunities**:
- CSV file loading
- Trace generation for unchanged data+config
- Figure spec building

- [ ] Identify cacheable functions
- [ ] Add `@st.cache_data` with appropriate TTL
- [ ] Add hash functions for custom objects

## 7.4 Standardize empty state messaging

**Issue**: Inconsistent empty state messages across components.

**Convention**:
```
"No [items] available. [Action to resolve]."
```

- [ ] Audit all empty state messages
- [ ] Standardize format and tone

## 7.5 Use `st.write_stream()` for scanner output

**File**: `src/web/components/data_source/data_source_components.py`
**Issue**: Manual loop with `as_completed()` for file scanning progress.

**Fix**: Use `st.write_stream()` (Streamlit 1.32+) for cleaner streaming.

- [ ] Evaluate `st.write_stream()` for scanner output
- [ ] Implement if cleaner than current approach

## 7.6 Fix `st.rerun(scope="app")` usage

**File**: `src/web/pages/portfolio.py:80`
**Issue**: `scope="app"` triggers full app rerun, may reset unrelated state.

**Fix**: Use `scope="fragment"` where possible, or document why `"app"` is needed.

- [ ] Audit all `st.rerun()` calls
- [ ] Narrow scope where possible

## 7.7 Consider Streamlit multipage app API

**Current**: Manual SPA navigation in `app.py` lines 75–87.
**Opportunity**: Streamlit's built-in multipage (`st.navigation`/`st.page`) API.

- [ ] Evaluate if migration to `st.navigation` is beneficial
- [ ] If yes, plan migration in separate phase

**Status**: [ ] NOT STARTED

---

# PHASE 8: Type Safety Improvements

**Priority**: MEDIUM — Strengthen type contracts.

## 8.1 Replace `dict[str, Any]` with specific TypedDicts

**Major offenders**:
- `PlotConfig = dict[str, Any]` in `plot_models.py:297`
- `render_config_ui() -> dict[str, Any]` in all plot types
- Settings components returning `dict[str, Any]`

**Action**: Create specific TypedDicts for each return type:
```python
class AxesConfig(TypedDict, total=False):
    x_title: str
    y_title: str
    x_min: float | None
    ...

class LegendConfig(TypedDict, total=False):
    show: bool
    position: str
    ...
```

- [ ] Define section-specific TypedDicts
- [ ] Update settings components return types
- [ ] Update plot config assembly to use typed dicts

## 8.2 Add `@override` annotations

As specified in Phase 6.4.

## 8.3 Fix incomplete return type annotations

**Files with `-> None` but actually returning values**:
- `data_source_components.py:96` — returns `dict | None`

- [ ] Audit return types across web layer
- [ ] Fix incorrect annotations

## 8.4 Add `@runtime_checkable` protocols where missing

**Files**: Controller protocols in `plot_protocols.py`

- [ ] Verify all protocols are `@runtime_checkable`
- [ ] Add where missing

## 8.5 Fix `PlotConfig` type alias

```python
# Current:
PlotConfig = dict[str, Any]  # Anything passes

# Better:
type PlotConfig = PlotDisplayConfig  # Specific TypedDict
```

- [ ] Update type alias
- [ ] Fix callers that pass non-conforming dicts

**Status**: [ ] NOT STARTED

---

# PHASE 9: Architectural Improvements

**Priority**: MEDIUM — Improve extensibility and separation.

## 9.1 Create `ColumnBasedSelector` mixin

**Issue**: `column_selector.py`, `item_selector.py`, `condition_selector.py` all have
identical column validation patterns.

**Action**: Extract shared validation into a mixin:
```python
class ColumnBasedSelector(Selector):
    def _verify_column_exists(self, name: str, df: pd.DataFrame) -> bool:
        if name not in df.columns:
            raise ValueError(f"Column '{name}' not in DataFrame")
        return True
```

- [ ] Create `ColumnBasedSelector` mixin
- [ ] Refactor 3 selector implementations to use it

## 9.2 Create `@cached_shaper()` decorator

**Issue**: `mean.py` and `normalize.py` use identical fingerprint-based caching patterns.

**Action**: Extract into reusable decorator:
```python
def cached_shaper(ttl: int = 300):
    def decorator(fn):
        @cached(ttl=ttl, key_func=lambda self, df: self._fingerprint(df))
        def wrapper(self, df):
            return fn(self, df)
        return wrapper
    return decorator
```

- [ ] Create `cached_shaper` decorator
- [ ] Apply to Mean and Normalize shapers

## 9.3 Split `BasePlot` into data + renderer

**File**: `src/web/pages/ui/plotting/base_plot.py` (~150 lines)
**Issue**: Mixes configuration gathering and rendering.

**Action**: Split into:
- `BasePlotData` — config gathering, trace building
- `BasePlotRenderer` — Plotly/Matplotlib rendering concerns

- [ ] Design split interface
- [ ] Implement `BasePlotData` and `BasePlotRenderer`
- [ ] Migrate 8 plot types

## 9.4 Split `LegendSettingsComponent`

**File**: `src/web/components/plotting/settings/legend_settings.py` (~180 lines)
**Issue**: 3-level navigation in single class.

**Action**: Split into:
- `PrimaryLegendSettings`
- `SecondaryLegendSettings`
- `LegendSettingsAggregator`

- [ ] Split legend settings into sub-components
- [ ] Compose via aggregator

**Status**: [ ] NOT STARTED

---

# PHASE 10: Test Coverage Expansion

**Priority**: HIGH — Fill critical gaps.

## 10.1 Add tests for untested modules

| Module | Priority | Test File to Create |
|--------|----------|-------------------|
| `filtered_selector.py` | HIGH | `tests/unit/test_filtered_selector.py` |
| `reorderable_list.py` | HIGH | `tests/unit/test_reorderable_list.py` |
| `plotly_connector.py` | HIGH | `tests/unit/test_plotly_connector.py` |
| `config_builder.py` | HIGH | `tests/unit/test_config_builder.py` |
| `pipeline.py` (component) | MEDIUM | `tests/unit/test_pipeline_component.py` |
| `chart_display.py` | MEDIUM | `tests/unit/test_chart_display.py` |

- [ ] Create test files for HIGH priority modules
- [ ] Create test files for MEDIUM priority modules

## 10.2 Previously skipped C9 — Concurrent thread-safety tests

**Issue**: No tests for PerlWorkerPool under concurrent load.

**Action**: Create mock-based concurrency tests that don't require live Perl:
```python
def test_concurrent_parse_requests():
    """Verify thread-safety under concurrent parse load."""
    pool = PerlWorkerPool(num_workers=3)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(pool.parse_file, f) for f in test_files]
        # Verify no data corruption
```

- [ ] Create `tests/unit/test_perl_pool_concurrency.py`
- [ ] Test concurrent parse requests
- [ ] Test health check during active parsing
- [ ] Test shutdown during active parsing

## 10.3 Fix brittle private-attribute tests

**Files with private access**:
- `test_configuration_type.py:30–205` — accesses `._repeat`, `._content`
- `test_matplotlib_trace_renderer.py:86` — accesses `._ring5_twin`
- `test_repository_state_manager.py:40` — accesses `._session_repo`

**Action**: Add public accessor methods or refactor to behavior-based assertions.

- [ ] Add public accessors for test-needed state
- [ ] Refactor tests to use public API only

## 10.4 Add edge case tests for shaping pipeline

Missing scenarios:
- Pipeline with 10+ sequential shapers
- Shaper returning empty DataFrame
- NaN/infinity values in pipeline
- Type mismatches between shaper output/input

- [ ] Create `tests/unit/test_pipeline_edge_cases.py`
- [ ] Test all edge scenarios

## 10.5 Add E2E integration test

**Missing**: Parse → Load → Transform → Plot → Export pipeline test.

- [ ] Create `tests/integration/test_full_pipeline_e2e.py`
- [ ] Cover complete workflow

## 10.6 Consolidate fixture duplication

**Issue**: `mock_state_manager`, `sample_data` defined differently in 3+ conftest files.

**Action**: Create shared fixtures in `tests/fixtures/` module.

- [ ] Create `tests/fixtures/` package
- [ ] Consolidate duplicate fixtures
- [ ] Update conftest files to import from shared fixtures

**Status**: [ ] NOT STARTED

---

# PHASE 11: Data Science / Pandas Best Practices

**Priority**: MEDIUM — Modern pandas patterns.

## 11.1 Use `.pipe()` for shaper pipeline

**File**: `src/core/services/shapers/pipeline_service.py`

```python
# Current:
for shaper in shapers:
    current_data = shaper(current_data)

# Better (more composable):
result = data.pipe(shaper1).pipe(shaper2).pipe(shaper3)
```

- [ ] Evaluate `.pipe()` compatibility with shaper interface
- [ ] If compatible, adopt pattern

## 11.2 Use `pd.CategoricalDtype` consistently

**Issue**: Several shapers convert to categorical using `.astype("category")` without
preserving order.

**Fix**: Use `pd.CategoricalDtype(categories=order, ordered=True)`.

- [ ] Audit categorical usage across shapers
- [ ] Add explicit category ordering where needed

## 11.3 Use `pd.StringDtype()` for string columns

**Issue**: String columns use default `object` dtype.

**Fix**: Use `pd.StringDtype()` for better memory and performance.

- [ ] Identify string columns in data pipeline
- [ ] Convert to `pd.StringDtype()` at load time

**Status**: [ ] NOT STARTED

---

# PHASE 12: Plotly & Matplotlib Best Practices

**Priority**: MEDIUM — Modern visualization patterns.

## 12.1 Use Plotly Express where appropriate

**Issue**: All traces built manually with `go.Bar()`, `go.Scatter()`, etc.
For simple cases, `px.bar()` is more concise and handles defaults.

- [ ] Evaluate if any plot types benefit from `px` shortcuts
- [ ] Convert where it simplifies code without losing flexibility

## 12.2 Use `fig.update_layout()` chaining

```python
# Current (multiple calls):
fig.update_layout(title="...")
fig.update_layout(xaxis=dict(...))
fig.update_layout(yaxis=dict(...))

# Better (single chained call):
fig.update_layout(
    title="...",
    xaxis=dict(...),
    yaxis=dict(...),
)
```

- [ ] Audit for multiple `update_layout()` calls
- [ ] Consolidate into single calls

## 12.3 Ensure Matplotlib cleanup

**Issue**: Matplotlib figures may not be properly closed after rendering.

**Fix**: Always use `plt.close(fig)` after saving/displaying.

- [ ] Audit all Matplotlib figure creation
- [ ] Ensure `plt.close()` called in `finally` blocks

## 12.4 Use `fig.write_image()` for exports

**Issue**: Export may use different methods across engines.

**Fix**: Standardize on Plotly's `fig.write_image()` with kaleido backend.

- [ ] Audit export code paths
- [ ] Standardize approach

**Status**: [ ] NOT STARTED

---

# PHASE 13: Final Validation

**Priority**: CRITICAL — Verify everything works.

## 13.1 Run full test suite

```bash
pytest tests/ -o "addopts=" --timeout=30 -x -q
```

- [ ] All tests pass
- [ ] No new warnings introduced
- [ ] No test regressions

## 13.2 Run pre-commit hooks

```bash
pre-commit run --all-files
```

- [ ] black passes
- [ ] flake8 passes
- [ ] mypy passes
- [ ] isort passes
- [ ] bandit passes

## 13.3 Verify type checking

```bash
mypy src/ --strict
```

- [ ] No new type errors
- [ ] Improved type coverage

## 13.4 Manual smoke test

- [ ] Application starts without errors
- [ ] Data source page loads
- [ ] CSV upload works
- [ ] Plot creation works
- [ ] Portfolio save/load works

**Status**: [ ] NOT STARTED

---

# Execution Order

| Phase | Name | Dependencies | Priority |
|-------|------|-------------|----------|
| 1 | Dead Code Removal | None | CRITICAL |
| 2 | Correctness Fixes | None | CRITICAL |
| 3 | Performance Optimizations | None | HIGH |
| 4 | Code Duplication Consolidation | Phase 1 | HIGH |
| 5 | Parsing Layer Robustness | Phase 2 | HIGH |
| 10 | Test Coverage Expansion | Phases 1–5 | HIGH |
| 6 | Modern Python 3.12+ | Phase 4 | MEDIUM |
| 7 | Streamlit Best Practices | Phase 4 | MEDIUM |
| 8 | Type Safety | Phase 6 | MEDIUM |
| 9 | Architectural Improvements | Phases 4, 6 | MEDIUM |
| 11 | Pandas Best Practices | Phase 3 | MEDIUM |
| 12 | Plotly/Matplotlib | Phase 9 | MEDIUM |
| 13 | Final Validation | ALL | CRITICAL |

---

# Progress Tracking

**NOTE**: This plan has been SUPERSEDED by the thorough-review investigation plan.

See: **`.agent/thorough-review/PLAN.md`** — the comprehensive, de-duplicated, 16-track
investigation plan with 119 items and individual research files for each track.

## Duplicated Paths Fixed in Thorough Review

| Original (This File) | Duplicate | Resolution |
| --- | --- | --- |
| Phase 2.5 (CSV header) | Phase 5.4 (same issue) | Merged → Track 02, item 2.8 |
| Phase 6.4 (@override) | Phase 8.2 (same item) | Merged → Track 08, item 8.4 |
| Phase 3.4 (@st.cache_data) | Phase 7.3 (overlap) | Merged → Track 09, item 9.3 |
| Phase 12.1 (Plotly Express) | Project rule: No PX | **REMOVED** — violates rules |

## New Findings Added in Thorough Review

15+ new findings not in this plan were discovered by deeper analysis agents.
See `.agent/thorough-review/PLAN.md` "NEW Findings" section for the complete list.
