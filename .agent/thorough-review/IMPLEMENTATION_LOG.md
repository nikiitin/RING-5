# Comprehensive Implementation Plan & Log

> **Source**: 16-track thorough investigation of the entire codebase
> **Total findings**: 126 items across 16 tracks
> **Created**: 2026-02-27
> **Departing state**: Phase 1 (outlier IQR fix) committed, Phase 2A (SimpleCache locks) in progress (uncommitted)

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| DONE | Implemented and committed |
| WIP | Work in progress (uncommitted changes exist) |
| TODO | To be implemented |
| DEFER | Deferred to a future phase or separate effort |
| SKIP | Not a bug / no action needed (investigation disproved hypothesis) |

---

## Phase 1: CRITICAL Bug Fixes

### P1.1 [DONE] Outlier detection removes top 25% instead of actual outliers (Track 14.3)

- **Severity**: CRITICAL
- **File**: `src/core/services/managers/outlier_service.py`
- **Bug**: Lines 23-24 used `df[df[col] <= q3]` which removes ALL values above Q3 (top 25%). Not IQR-based at all.
- **Fix**: Replaced with proper IQR method: Q1, Q3, IQR = Q3-Q1, lower = Q1 - 1.5*IQR, upper = Q3 + 1.5*IQR. Added configurable `multiplier` parameter. Applied same fix for grouped mode using `groupby().transform()`. Removed redundant `pd.DataFrame()` wrappers.
- **Tests**: Updated `tests/unit/test_outlier_service_coverage.py` for IQR behavior. Added `test_custom_multiplier`, `test_iqr_keeps_values_within_bounds`.
- **Commit**: `da2bf11`

### P1.2 [DONE] SimpleCache has NO thread locks (Track 5.1)

- **Severity**: CRITICAL
- **File**: `src/core/performance.py` (199 lines)
- **Fix**: Added `self._lock = threading.Lock()` in `__init__`. Wrapped `get()`, `set()`, `clear()`, `stats()` with `with self._lock:`.
- **Commit**: `9b60a95`

### P1.3 [DONE] CsvPoolService `_pool_index` has no lock (Track 5.2)

- **Severity**: CRITICAL
- **File**: `src/core/services/data_services/csv_pool_service.py`
- **Fix**: Added `_pool_lock = threading.Lock()` class attribute. Wrapped all `_pool_index` reads/writes.
- **Commit**: `6aff643`

### P1.4 [DONE] Scalar `int()` truncation silently corrupts data (Track 2.10)

- **Severity**: HIGH
- **File**: `src/parsing/gem5/types/scalar.py`, line 60
- **Fix**: Replaced `int()` with `float()` in the summation loop.
- **Commit**: `6aff643`

### P1.5 [SKIP] Shallow copy in simple.py is intentional (Track 2.6)

- **Severity**: N/A (investigation hypothesis disproved)
- **File**: `src/parsing/gem5/impl/strategies/simple.py`, line 184
- **Finding**: The shallow copy at line 184 is INTENTIONAL — aliases share `_content` with the parent variable so parsed values flow to the parent for regex-based aggregation. Per-file isolation is already handled by `copy.deepcopy(template_map)` at line 115. Changing to deepcopy breaks the aggregation pipeline (test `test_reduction_end_to_end` fails with [0.0, 0.0] instead of [15.0, 20.0]). Added clarifying comment.
- **Commit**: `6aff643`

### P1.6 [DONE] Unchecked array index crashes worker on malformed Perl output (Track 2.1)

- **Severity**: HIGH
- **File**: `src/parsing/gem5/impl/strategies/gem5_parse_work.py`, line 103
- **Fix**: Added bounds check `if len(parts) < 3` with warning log and early return. Also added guard in `_processLine` to skip empty rawType.
- **Commit**: `6aff643`

### P1.7 [DONE] Mean NaN handling inconsistent across algorithms (Track 14.2)

- **Severity**: HIGH
- **File**: `src/core/services/shapers/impl/mean.py`
- **Fix**: Created `_safe_gmean()` and `_safe_hmean()` wrappers that filter NaN before scipy calls and handle non-positive values. Replaced direct `gmean`/`hmean` usage in `agg()`.
- **Commit**: `6aff643`

### P1.8 [DONE] Mixer None checks crash on widget None returns (Track 4.2)

- **Severity**: HIGH
- **File**: `src/web/components/data_managers/mixer.py`
- **Fix**: Added `if mode is None: return` after segmented_control and `if operation is None: return` after selectbox.
- **Commit**: `6aff643`

### P1.9 [DONE] Normalize NaN denominator not checked (Track 14.1)

- **Severity**: MEDIUM
- **File**: `src/core/services/shapers/impl/normalize.py`, line 232
- **Fix**: Added `pd.isna(denominator)` check alongside zero check.
- **Commit**: `6aff643`

### P1.10 [DONE] DataFrame stored by reference when no type casting needed (Track 3.9)

- **Severity**: HIGH
- **File**: `src/core/state/repository_state_manager.py`
- **Fix**: Always copy DataFrame before storing with `data = data.copy()` before the try block.
- **Commit**: `6aff643`

---

## Phase 2: Thread Safety & Lifecycle

### P2.1 [DONE] WorkPool has NO shutdown mechanism (Track 5.4, 5.10)

- **Severity**: HIGH
- **File**: `src/parsing/gem5/impl/pool/work_pool.py`
- **Fix**: Added `shutdown()` method to WorkPool (shuts down process/thread executors). Added `_new_lock` for thread-safe singleton `__new__`. Registered `atexit.register(_shutdown_workpool)` at module level. Added `__del__` to PerlWorkerPool that calls `self.shutdown()`. Registered `atexit.register(shutdown_worker_pool)` in `get_worker_pool()` on first creation.
- **Commit**: Phase 2 commit

### P2.2 [DONE] Health monitor shutdown uses plain bool instead of Event (Track 5.8, 2.4)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- **Fix**: Replaced `self._shutdown = False` with `self._shutdown_event = threading.Event()`. Monitor loop uses `event.wait(timeout=interval)` for interruptible sleep (wakes instantly on shutdown). Added `thread.join(timeout=interval+1)` in `shutdown()`.
- **Commit**: Phase 2 commit

### P2.3 [DONE] Three unprotected singleton patterns (Track 5.5, 5.7, 5.9)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/pool/work_pool.py`, `src/parsing/gem5/impl/pool/pool.py`
- **Fix**: Added `_new_lock = threading.Lock()` to WorkPool `__new__`. Added `_singleton_lock` to ScanWorkPool and `_instance_lock` to ParseWorkPool. All `get_instance()` and `reset()` methods now use `with cls._lock:`.
- **Commit**: Phase 2 commit

### P2.4 [DONE] Thread accumulation on timeout (Track 2.3)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- **Fix**: Replaced per-read thread spawn with a persistent reader thread per worker. `_start_reader_thread()` creates ONE daemon thread that reads stdout into a `queue.Queue`. `_read_line_with_timeout()` simply pulls from the queue with timeout. 4 workers = 4 reader threads (constant), instead of N threads per parse.
- **Commit**: Phase 2 commit

### P2.5 [DONE] is_busy TOCTOU and health monitor I/O collision (Track 5.3, 5.11)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- **Fix**: Added `time.time() - worker.last_used < 60.0` skip in `_check_worker_health()`. Workers used within the last 60s are skipped, eliminating the TOCTOU window where health check PING/PONG could interfere with an imminent parse.
- **Commit**: Phase 2 commit

### P2.6 [DONE] Queue starvation on all-worker fail (Track 5.6)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- **Fix**: Implemented circuit-breaker pattern: total timeout split across retries (`per_attempt_timeout = max(5s, timeout / max_retries)`). Added `failures` counter and healthy-worker check before each attempt. If `healthy_count == 0 and failures > 0`, raises immediately instead of blocking for N × timeout.
- **Commit**: Phase 2 commit

---

## Phase 3: Dead Code Removal

### P3.1 [DONE] Remove 12 dead utility functions (Track 1.1)

- **Severity**: HIGH
- **File**: `src/core/common/utils.py`
- **Fix**: Removed 12 dead functions, `JsonValue` type alias, and unused `enum`/`tempfile` imports. Kept alive: `checkFileExistsOrException`, `sanitize_log_value`, `sanitize_filename`, `validate_path_within`, `sanitize_glob_pattern`, `normalize_user_path`. File reduced from 368 to 171 lines (~200 lines removed).
- **Commit**: Phase 3 commit

### P3.2 [DONE] Rewrite test_utils.py for alive functions only (Track 1.1)

- **File**: `tests/unit/test_utils.py`
- **Fix**: Rewrote to only test alive functions: `checkFileExistsOrException`, `sanitize_log_value`, `sanitize_filename`, `validate_path_within`, `sanitize_glob_pattern`, `normalize_user_path`. File reduced from 252 to 148 lines.
- **Commit**: Phase 3 commit

### P3.3 [DONE] Delete dead duplicate: plot_manager_components.py (Track 1.2)

- **File deleted**: `src/web/pages/ui/components/plot_manager_components.py`
- **Verified**: Byte-identical to canonical `src/web/components/plotting/plot_manager_components.py`. Zero production imports. Test files reference the canonical path.
- **Commit**: Phase 3 commit

### P3.4 [DONE] Delete dead duplicate: split_apply_config.py (Track 1.3, 7.2)

- **File deleted**: `src/web/pages/ui/components/shapers/split_apply_config.py`
- **Verified**: Byte-identical to canonical `src/web/components/shapers/split_apply_config.py`. Zero production imports. Also removed empty parent directories.
- **Commit**: Phase 3 commit

### P3.5 [DONE] Delete dead duplicate: ChartPresenter (Track 7.1, 4.7)

- **File deleted**: `src/web/presenters/plot/chart_presenter.py`
- **Also updated**: `src/web/presenters/plot/__init__.py` — removed ChartPresenter import and export.
- **Verified**: Zero imports anywhere in codebase or tests.
- **Commit**: Phase 3 commit

### P3.6 [SKIP] Dead data_manager directories (Track 1.4, 1.8)

- **Finding**: Directory `src/web/pages/ui/components/data_managers/` does not exist. No action needed.

### P3.7 [DONE] Remove unused list comprehension in mixer.py (Track 4.10)

- **File**: `src/web/components/data_managers/mixer.py`, line 43
- **Fix**: Removed orphaned list comprehension whose result was never assigned.
- **Commit**: Phase 3 commit

### P3.8 [DONE] Remove extract_with_pattern duplication (Track 7.6)

- **File**: `src/web/components/shapers/pivot_config.py`
- **Fix**: Replaced local `extract_with_pattern` definition with import from `src.core.services.shapers.impl.pivot`. ~14 lines removed.
- **Commit**: Phase 3 commit

---

## Phase 4: Matplotlib Memory Leak Fixes

### P4.1 [DONE] Zero plt.close() calls in entire codebase (Track 10.2)

- **Severity**: HIGH
- **File**: `src/web/components/common/chart_display.py`
- **Bug**: Figure created via `plt.subplots()` but never closed. Memory leak in long-running Streamlit sessions.
- **Fix**: Close previous figure from session_state before creating new one. Added try/except to close figure on render failure. Import `matplotlib.pyplot as plt` and `logging` at module level.
- **Commit**: Phase 4 commit

### P4.2 [DONE] Figure objects stored in session_state (Track 10.3)

- **Severity**: HIGH
- **File**: `src/web/components/common/chart_display.py`
- **Bug**: Matplotlib Figure object stored in `st.session_state[f"plot.{plot_id}.mpl_fig"]`. Old figures never garbage collected when re-rendered.
- **Fix**: Close and delete old figure from session_state at start of `render_matplotlib_chart()` before creating the new one. Keeps at most 1 unclosed figure per plot. Download path still works via session_state.
- **Commit**: Phase 4 commit

### P4.3 [DONE] st.pyplot() without cleanup (Track 10.4)

- **Severity**: HIGH
- **File**: `chart_display.py`
- **Bug**: `st.pyplot(mpl_fig)` with no cleanup. chart_presenter.py already deleted in P3.5.
- **Fix**: Figure lifecycle managed: old figure closed before new render, exception path closes on failure.
- **Commit**: Phase 4 commit

### P4.4 [SKIP] Plot cache eviction doesn't close figures (Track 10 related)

- **File**: `src/core/performance.py` — `_plot_cache` stores Plotly `go.Figure` objects, NOT matplotlib figures
- **Finding**: The `_plot_cache` (used in `render_controller.py:226`) caches Plotly figures which are regular Python objects without file descriptors. No special cleanup needed. Matplotlib figures are managed separately via session_state (fixed in P4.1-P4.3).

---

## Phase 5: Pandas Cleanup

### P5.1 [DONE] Remove 26 redundant pd.DataFrame() wrappers (Track 13.5, 3.3)

- **Severity**: HIGH (unnecessary copies across 12 files)
- **Fix**: Removed redundant `pd.DataFrame()` wrappers from boolean indexing results across 12 files: condition_selector.py (6), item_selector.py (2), column_selector.py (1), split_apply.py (1), normalize.py (1), reduction_service.py (3), data_manager_components.py (3), bar_plot.py (3), stacked_bar_plot.py (1), dual_axis_bar_dot_plot.py (1), grouped_stacked_bar_plot.py (1), grouped_bar_plot.py (5). ~28 wrappers removed total.
- **Commit**: Phase 5 commit

### P5.2 [DONE] Replace iterrows() with vectorized zip() (Track 13.3)

- **Severity**: MEDIUM
- **File**: `src/web/pages/ui/plotting/types/stacked_bar_plot.py`, line 162
- **Bug**: `for _, row in data.iterrows()` in `_build_totals_annotations()`.
- **Fix**: Replaced with `zip(data["__total"], data[x_col])` — avoids iterrows overhead and handles dunder column names (which `itertuples` can't).
- **Commit**: Phase 5 commit

### P5.3 [SKIP] Use .pipe() for shaper pipeline (Track 13.1)

- **Severity**: MEDIUM
- **File**: `src/core/services/shapers/pipeline_service.py`
- **Finding**: The existing loop pattern is cleaner for this use case — it needs per-shaper timing, error handling with shaper-type context in the error message, and index tracking. Converting to `.pipe()` would lose the per-step timing and error context. The current pattern is idiomatic and readable.

---

## Phase 6: Architecture Fixes

### P6.1 [TODO] Fix Web-to-Parsing direct imports — 3 violations (Track 11.1)

- **Severity**: MEDIUM-HIGH
- **Files with violations**:
  - `src/web/components/data_source/data_source_components.py:20-21` — imports `ScanWorkPool` + `SimulatorRegistry` from `src.parsing`
  - `src/web/components/data_source/variable_editor.py:536` — imports `ScanWorkPool` dynamically
  - `src/web/pages/data_source.py:9` — imports `SimulatorRegistry`
- **Fix**:
  1. Create facade methods in `src/core/application_api.py`:
     - `cancel_pending_scans()` — wraps ScanWorkPool.cancel_all()
     - `available_simulators()` — wraps SimulatorRegistry
     - `available_simulator_info()` — wraps SimulatorRegistry
     - `get_simulator_info(name)` — wraps SimulatorRegistry
  2. Update web imports to use ApplicationAPI

### P6.2 [TODO] Pivot config unbound variables — real bug (Track 16.1, 4.8)

- **Severity**: MEDIUM
- **File**: `src/web/components/shapers/pivot_config.py`, lines 256-258
- **Bug**: `selection_filters`, `strategy`, `merge_label` only defined inside `if extract_pattern: ... if num_groups > 0:` nested block. Used unconditionally at lines 256-258. Current workaround uses `"x" in locals()` which pyright cannot track.
- **Fix**: Initialize defaults before the conditional block:
  ```python
  selection_filters: dict[int, list[str]] = {}
  strategy: str = "discard"
  merge_label: str = "other"
  ```
  Remove `if "x" in locals()` checks.

### P6.3 [TODO] st.rerun() scope mismatches (Track 9.6)

- **Severity**: MEDIUM
- **Files**: 47 total calls: 46 default scope, 1 scope="app"
- **Bug**: 3-4 calls should use `scope="app"` but don't: app.py:87 (navigation), app.py:100 (clear data), app.py:109 (reset all), portfolio.py:53 (save).
- **Fix**: Change navigation and global-state rerun calls to `st.rerun(scope="app")`.

---

## Phase 7: Parsing Layer Fixes

### P7.1 [TODO] CSV header built from first result only (Track 2.8)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/gem5_parser.py`, lines 269-282
- **Bug**: Header built from `results[0]` only. If first file is missing a variable that later files have, header is permanently incomplete.
- **Fix**: Build header as union of all results' entries, with consistent column ordering.

### P7.2 [TODO] Mixed return types in scalar.py (Track 2.11)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/types/scalar.py`, lines 49-61
- **Bug**: `_reduced_content` is either "NA" (str) or float. Downstream expecting float gets str.
- **Fix**: Use `float('nan')` instead of "NA" for missing values, or use `None` with explicit type.

### P7.3 [TODO] Silent scan error returns empty instead of error (Track 2.13)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/scanning/gem5_scan_work.py`, line 40
- **Bug**: Returns `[]` on any exception. Callers can't distinguish empty scanner results vs failed.
- **Fix**: Return a result object with error field, or re-raise with context.

### P7.4 [TODO] Broad exception in config_aware.py (Track 2.12)

- **Severity**: LOW
- **File**: `src/parsing/gem5/types/config_aware.py`, line 73
- **Bug**: `except Exception` catches everything. Should be `except (configparser.Error, OSError)`.
- **Fix**: Narrow exception type.

### P7.5 [TODO] Histogram silent range parse failures (Track 2.14)

- **Severity**: LOW
- **File**: `src/parsing/gem5/types/histogram.py`, lines 302-307
- **Bug**: `_parse_range_key()` returns `[]` silently on non-numeric keys. Intentional for summary stats, but no warning for failed real ranges.
- **Fix**: Add `logger.debug` for failed range parses on keys that look numeric.

### P7.6 [TODO] Distribution precision with sum() (Track 14.4)

- **Severity**: LOW
- **File**: `src/parsing/gem5/types/distribution.py`, lines 200-201, 234
- **Bug**: Uses Python `sum()` (no Kahan summation). For typical gem5 stats (<10K values), error is <0.0001%. For 100K+, error may be noticeable.
- **Fix**: Replace `sum(float_vals)` with `math.fsum(float_vals)` for compensated summation.

---

## Phase 8: Core Layer Fixes

### P8.1 [TODO] Broad except in pivot.py (Track 3.1)

- **Severity**: MEDIUM
- **File**: `src/core/services/shapers/impl/pivot.py`, line 49
- **Bug**: `except Exception` catches `re.error` and `TypeError`. No error logging.
- **Fix**: Narrow to `except (re.error, TypeError) as e:` + `logger.warning(...)`.

### P8.2 [TODO] Off-by-one CSV row count (Track 3.4)

- **Severity**: LOW
- **File**: `src/core/services/data_services/csv_pool_service.py`, line 277
- **Bug**: `sum(1 for _ in f) - 1` returns -1 for empty files (0 lines). Edge case only (normal CSVs always have headers).
- **Fix**: `max(0, total_lines - 1)` guard.

### P8.3 [TODO] Portfolio migrator mutates input dict (Track 3.5)

- **Severity**: MEDIUM
- **File**: `src/core/services/portfolio_migrator.py`, line 64
- **Bug**: `_migrate_v1_to_v2` mutates input dict via `config.setdefault()` and `del config[k]`. Input comes from `json.load()` so fresh dict, but pattern is fragile.
- **Fix**: Add `data = data.copy()` at top or document mutation intent.

### P8.4 [TODO] Normalize performance: .values vs .unique() (Track 3.6)

- **Severity**: LOW
- **File**: `src/core/services/shapers/impl/normalize.py`, line 189
- **Bug**: `.values` returns all values including duplicates for membership check. `.unique()` would be more efficient.
- **Fix**: Replace `.values` with `.unique()`.

### P8.5 [TODO] Silent type coercion failure in state manager (Track 3.7)

- **Severity**: MEDIUM
- **File**: `src/core/state/repository_state_manager.py`, lines 74-82
- **Bug**: Exception caught, logged, but `set_data()` called with potentially partial-typed data.
- **Fix**: Consider re-raising or ensuring full coercion before proceeding.

### P8.6 [TODO] Numpy reference in normalize.py (Track 3.10)

- **Severity**: LOW
- **File**: `src/core/services/shapers/impl/normalize.py`, line 318
- **Bug**: `result[col] = data_frame[col].values` uses numpy array reference instead of copy. Could share memory.
- **Fix**: Use `data_frame[col].copy()` instead of `.values`.

---

## Phase 9: Plotly Optimization

### P9.1 [TODO] Batch 11 scattered fig.update_layout() calls (Track 10.1)

- **Severity**: MEDIUM
- **File**: `src/web/rendering/plotly_connector.py`
- **Bug**: 11 scattered `fig.update_layout()` calls across 10+ `_apply_*()` methods (lines 86, 103, 115, 266, 277, 285, 379, 408, 414, 494, 662). Each triggers Plotly's internal validation.
- **Fix**: Collect all layout kwargs in a single dict, call `fig.update_layout(**all)` once at end of `apply()`.

---

## Phase 10: Python 3.12+ Modernization

### P10.1 [TODO] Add @override decorators to 30+ method overrides (Track 6.4, 8.4)

- **Severity**: MEDIUM
- **Files**: All method overrides in:
  - `BasePlot` subclasses (8 plot types in `src/web/pages/ui/plotting/types/`)
  - `Shaper` subclasses (10 shapers in `src/core/services/shapers/impl/`)
  - `StatType` subclasses (5 types in `src/parsing/gem5/types/`)
- **Fix**: Add `from typing import override` and `@override` to all overridden methods.

### P10.2 [TODO] Create StrEnum for registry keys (Track 8.1)

- **Severity**: MEDIUM
- **Files**: `src/core/services/shapers/factory.py`, `src/parsing/gem5/impl/strategies/factory.py`
- **Fix**: Create `ShaperType(StrEnum)` with 10 members, `StrategyType(StrEnum)` with 2 members. Replace string literals.

### P10.3 [TODO] Convert if/elif chains to match/case (Track 8.2)

- **Severity**: MEDIUM-HIGH
- **Files**:
  - `src/core/services/shapers/impl/condition_selector.py`, lines 100-109 (4-branch mode dispatch)
  - `src/parsing/gem5/impl/strategies/gem5_parse_work.py`, lines 216-225 (type normalization)
  - `src/parsing/gem5/impl/strategies/factory.py`, lines 21-49 (strategy selection)
- **Fix**: Convert each if/elif chain to match/case with exhaustive `case _: assert_never()`.

### P10.4 [TODO] Add @runtime_checkable to 10 protocols (Track 6.3)

- **Severity**: LOW
- **File**: `src/web/controllers/plot/plot_protocols.py` and others
- **Missing on**: ConfigRenderer, PlotLifecycleService, PlotTypeRegistry, PipelineExecutor, ReferenceLineRenderer, ShapesRenderer, EngineControlsRenderer, SpecificOptionsRenderer, OrderingRenderer, FileParserStrategy
- **Fix**: Add `@runtime_checkable` to all for consistency.

### P10.5 [TODO] PEP 695 type statements (Track 8.3)

- **Severity**: LOW
- **Files**: `src/core/models/shaper_models.py`, `src/core/models/data_models.py`, `src/core/models/visualization/plot_models.py`
- **Fix**: Convert 3-5 manual type aliases to `type X = ...` syntax.

### P10.6 [TODO] PEP 695 generics: single TypeVar (Track 8.5)

- **Severity**: LOW
- **File**: `src/core/performance.py`
- **Fix**: Convert `T = TypeVar("T")` to `def cached[T](...)` syntax. Single change.

### P10.7 [TODO] f-string cleanup (Track 8.7)

- **Severity**: LOW
- **Fix**: Remove ~15-20 redundant `str()` calls in f-strings across codebase. f-strings auto-call `str()`.

---

## Phase 11: Lint & Format

### P11.1 [TODO] isort fixes for source files (Track 16.2)

- **Severity**: LOW
- **Files**: `src/web/components/data_source/variable_editor.py`, `src/web/rendering/matplotlib_connector.py`
- **Fix**: `isort --profile=black --line-length=100`

### P11.2 [TODO] isort fixes for test files (Track 16.3)

- **Severity**: LOW
- **Files**: `tests/unit/test_mixer.py`, `tests/unit/test_web_modules.py`
- **Fix**: `isort --profile=black --line-length=100`

### P11.3 [TODO] trunk fmt for markdown files (Track 16.4, 16.5, 16.6)

- **Severity**: LOW
- **Fix**: Run `trunk fmt --all` for auto-fixable markdown table formatting, code block language specifiers, and heading issues in `.agent/` files.

### P11.4 [TODO] Final trunk check verification (Track 16.7, 16.8)

- **Severity**: LOW
- **Fix**: Run `trunk fmt --all` then `trunk check --all --no-fix` to verify zero issues. Must be done LAST after all code changes.

---

## Phase 12: Comprehensive Test Writing

### P12.1 [TODO] SimpleCache thread safety tests (Track 12.1, 5.1)

- Test concurrent get/set from multiple threads
- Test TTL expiration under concurrency
- Test LRU eviction correctness
- Test stats counters under concurrency

### P12.2 [TODO] Outlier IQR method tests (extends P1.1)

- Test with normal distribution (keeps ~95%)
- Test with small dataset (n<5)
- Test grouped mode with IQR
- Test with no outliers (all data kept)
- Test with extreme outliers
- Test custom multiplier parameter

### P12.3 [TODO] Mean NaN handling tests (P1.7)

- Test arithmean with NaN (skips NaN)
- Test geomean with NaN (should skip NaN post-fix)
- Test hmean with NaN (should skip NaN post-fix)
- Test geomean with zero values (returns NaN)
- Test hmean with zero values (returns NaN)

### P12.4 [TODO] Normalize NaN baseline tests (P1.9)

- Test with NaN baseline
- Test with zero baseline
- Test with valid baseline

### P12.5 [TODO] Mixer None check tests (P1.8)

- Test with mode=None
- Test with operation=None
- Test normal flow still works

### P12.6 [TODO] Selector tests post-wrapper removal (P5.1)

- Verify all condition_selector paths still return DataFrame
- Verify item_selector modes
- Verify column_selector

### P12.7 [TODO] Architecture import test (P6.1)

- Verify no `from src.parsing` imports in `src/web/` (grep-based test)

### P12.8 [TODO] Scalar reduce tests (P1.4)

- Test float values aren't truncated to int
- Test sum accuracy with decimal values

### P12.9 [TODO] Deep copy tests for stat types (P1.5)

- Test that copied stat objects don't share mutable state
- Test that balance_content on copy doesn't affect original

### P12.10 [TODO] Parse line bounds check tests (P1.6)

- Test with properly formatted line
- Test with malformed line (fewer than 3 parts)
- Test with empty line

---

## Phase 13: Architecture Improvements (Optional but Recommended)

### P13.1 [TODO] Create ParserBackend protocol (Track 11.3)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py` (560 lines)
- **Finding**: PerlWorkerPool has no protocol/abstraction. Hardcoded to subprocess-based Perl execution.
- **Fix**: Create `ParserBackend(Protocol)` with parse/health_check/shutdown methods. Make PerlWorkerPool implement it.

### P13.2 [TODO] ColumnBasedSelector mixin (Track 11.2)

- **Severity**: LOW
- **Files**: `column_selector.py`, `item_selector.py`, `condition_selector.py`
- **Finding**: All 3 selectors duplicate `super()._verify_params()` + cast pattern. ~30 lines duplicated.
- **Fix**: Create `ColumnValidationMixin` or centralize in Selector base class.

### P13.3 [TODO] Cached shaper fingerprint consolidation (Track 15.1)

- **Severity**: MEDIUM
- **Files**: `mean.py`, `normalize.py`
- **Finding**: Both implement identical `_compute_data_fingerprint()` static methods (~30 lines each, 95% identical). Difference: cache sizes (16 vs 32).
- **Fix**: Create shared fingerprint function in `src/core/services/shapers/` or `src/core/performance.py`.

### P13.4 [TODO] Centralize UIStateManager usage (Track 7.4, 4.1)

- **Severity**: LOW-MEDIUM
- **Finding**: 10-13 direct `st.session_state[` bypasses in seeds_reducer.py, mixer.py, preprocessor.py, outlier_remover.py, render_controller.py, base_ui.py, manage_plots.py.
- **Fix**: Create widget-level transient state namespace in UIStateManager. Migrate direct accesses.

### P13.5 [TODO] Centralize widget key builder (Track 11.6)

- **Severity**: LOW-MEDIUM
- **Finding**: 94+ unique key patterns, 120+ total `key=` statements across 12 settings files.
- **Fix**: Create `WidgetKeyBuilder` utility. Migrate all key construction.

### P13.6 [TODO] Standardize settings components (Track 11.5)

- **Severity**: LOW
- **Finding**: 7 class-based, 4 function-based across 11 settings files.
- **Fix**: Standardize all to class-based pattern with `__init__(plot_id, plot_type)` + `render()`.

---

## Phase 14: Test Coverage Expansion (Track 12)

### P14.1 [TODO] SimpleCache unit test suite (Track 12.1)

- **Priority**: HIGH
- **Finding**: ZERO dedicated unit tests for SimpleCache. Only indirect `clear_all_caches` call.
- **Action**: Create 10+ tests covering get/set, TTL, LRU eviction, stats, edge cases.

### P14.2 [TODO] Config builder unit tests (Track 12.1)

- **Priority**: MEDIUM
- **Finding**: config_builder.py has integration tests but no unit suite.
- **Action**: Create 15+ config builder unit tests.

### P14.3 [TODO] Reorderable list and filtered selector unit tests (Track 12.2)

- **Priority**: MEDIUM
- **Finding**: Tested only through E2E/UI-logic tests. No dedicated unit tests.
- **Action**: Add 8+ dedicated unit tests.

### P14.4 [TODO] Refactor private attribute test accesses (Track 12.3)

- **Priority**: HIGH
- **Finding**: 370+ private attribute accesses across test suite. test_configuration_type.py: 30+ accesses (`._repeat`, `._content`, `._on_empty`, `._balanced`, `._reduced`). test_matplotlib_trace_renderer.py:86 uses `cast(Any, ax)._ring5_twin`.
- **Action**: Refactor 10-15 test files. Add public accessors where needed. Target <50 private accesses.

### P14.5 [TODO] Replace flaky timing tests (Track 12.4)

- **Priority**: MEDIUM-HIGH
- **Finding**: 13 `time.sleep()` calls across tests. 2 use 1.1s for file timestamp granularity. 5 benchmark tests rely on sleep-based timing.
- **Action**: Replace sleep-based waits with `threading.Event` or `unittest.mock.patch` for deterministic behavior.

### P14.6 [TODO] Shaper edge case tests (Track 12.5)

- **Priority**: MEDIUM
- **Finding**: 66 shaper test methods exist. Missing: binary/malformed CSV, unicode column names, large datasets, numeric precision loss.
- **Action**: Add 5+ tests for data format robustness.

### P14.7 [TODO] Concurrent PerlWorkerPool tests (Track 12.7)

- **Priority**: MEDIUM
- **Finding**: No concurrent access tests. test_perl_worker_pool.py exists but tests sequential access only.
- **Action**: Add mock-based concurrent parse tests with ThreadPoolExecutor.

### P14.8 [TODO] E2E integration test: Parse -> Load -> Transform -> Plot (Track 12.8)

- **Priority**: MEDIUM
- **Finding**: No parse->load->transform->plot integration test.
- **Action**: Create `tests/integration/test_full_pipeline_e2e.py` with small fixture data.

### P14.9 [TODO] Binary file rejection tests (Track 12.10)

- **Priority**: MEDIUM
- **Finding**: Zero tests for binary (.bin, .pkl, .dat) file rejection. No encoding error tests. No permission denied tests.
- **Action**: Add 6+ parser robustness tests for malformed/binary input.

### P14.10 [TODO] Fixture consolidation (Track 12.9)

- **Priority**: LOW
- **Finding**: No true duplicates but naming inconsistency. Root `mock_state_manager` vs integration `state_manager`. `sample_data` (6 rows) vs `rich_sample_data` (9 rows).
- **Action**: Document fixtures. Create shared data fixture library. Standardize naming.

---

## Deferred Items

### D1 [DEFER] Split BasePlot 690-line god class (Track 11.4)

- **Severity**: MEDIUM-HIGH
- **Reason for deferral**: 690 lines, 26 methods mixing config-gathering (18 methods) with rendering (8 methods). Splitting into PlotConfigUI + PlotRenderer is a massive refactor that touches all 8 plot types. High regression risk.
- **Action**: Separate effort. Split into PlotConfigUI (Streamlit) and PlotRenderer (figure creation + styling).

### D2 [DEFER] Migrate dict[str,Any] to TypedDicts progressively (Track 6.1, 6.6)

- **Severity**: MEDIUM
- **Finding**: 497 occurrences across 111 files. PlotDisplayConfig TypedDict already exists (89 lines, 70+ fields). Progressive typing alias with intentional migration path.
- **Action**: Gradual migration in future PRs.

### D3 [DEFER] Replace Any annotations with specific types (Track 6.2)

- **Severity**: LOW
- **Finding**: 53 occurrences in 15 files. Most justified: matplotlib lazy imports, plotly heterogeneous data, external API compat.
- **Action**: Add type comments or use `TYPE_CHECKING` imports gradually.

### D4 [DEFER] Multipage API evaluation (Track 9.7)

- **Severity**: LOW
- **Finding**: Manual SPA via session_state with custom styling. st.navigation (1.26+) would lose custom styling and lazy loading.
- **Action**: Keep current approach. More control.

### D5 [DEFER] ExceptionGroup for batch parsing (Track 8.8)

- **Severity**: N/A (not warranted)
- **Finding**: Current fail-fast pattern is appropriate. ExceptionGroup would require architectural change.
- **Action**: Only implement if batch error reporting becomes a requirement.

### D6 [DEFER] StringDtype for string columns (Track 13.4)

- **Severity**: N/A (optional optimization)
- **Finding**: Default object dtype is stable. StringDtype would be optional for memory-heavy datasets.
- **Action**: Only implement if memory profiling shows overhead.

### D7 [DEFER] Legend settings split (Track 15.2)

- **Severity**: LOW (not warranted)
- **Finding**: 338 lines but well-decomposed internally. Splitting would add boilerplate.
- **Action**: No action. Current design is manageable.

### D8 [DEFER] Plugin architecture for plot types (Track 15.3)

- **Severity**: LOW (not warranted at 9 types)
- **Finding**: 9 plot types, manual registration optimal. `register_plot_type()` already exists.
- **Action**: Revisit when count exceeds 15-20.

### D9 [DEFER] E2E Playwright test investigation

- **Finding**: User mentioned revisiting E2E tests with Playwright MCP for DOM checking and POM updates.
- **Action**: Separate investigation and effort.

---

## Items Confirmed as NOT Bugs (No Action Needed)

| Track | Item | Finding |
|-------|------|---------|
| 1.5 | Backward compat shims | ALL 3 ALIVE — used by 15+ tests as stable import targets |
| 1.6 | Widget framework | ALIVE — WidgetRenderer used in production by base_ui.py:23 |
| 2.2 | Pipe leak on process death | NOT A BUG — pipes closed unconditionally |
| 2.5 | Silent exception in parse work | NOT A BUG — properly raises RuntimeError |
| 2.7 | Dict access in gem5_parser | NOT A BUG — key guaranteed present |
| 2.9 | Vector balance_content init | NOT A BUG — entries initialized in __init__ |
| 3.2 | Broad except (portfolio) | NOT A BUG — intentionally broad for injected callback |
| 3.8 | Config validation safety | NOT A BUG — nested dicts always initialized |
| 4.3 | None checks (data_source) | NOT A BUG — all widget returns properly guarded |
| 4.4 | Widget pre-init | NOT A BUG — intentional Streamlit workaround |
| 4.6 | Key collision (editor) | NOT A BUG — UUID-based keys |
| 6.5 | Return type annotations | NOT A BUG — no violations found |
| 7.3 | Data manager duplicates | NOT duplicates — different classes/responsibilities |
| 7.5 | SettingsComponentBase | Not needed — consistent architecture |
| 7.7 | Caching duplication | Acceptable pattern reuse |
| 7.8 | Connector duplication | Proper separation of concerns |
| 9.1 | Widget pre-init (revisit) | Documented workaround |
| 9.2 | st.status() progress | Scanner already uses it well. Plots fast enough. |
| 9.3 | @st.cache decorators | @st.cache_resource IS used for ApplicationAPI. Custom figure cache exists. |
| 9.4 | Empty state messages | 36+ messages consistent across app |
| 9.5 | st.write_stream() | Not applicable — for LLM streaming, not progress |
| 10.5 | Grouped stacked bar bypass | NOT A BUG — uses standard FigureSpec pipeline |
| 13.2 | CategoricalDtype | NOT A BUG — already using pd.Categorical(ordered=True) |

---

## Execution Order Summary

1. **Phase 1**: CRITICAL bug fixes (P1.1 DONE, P1.2 WIP, P1.3-P1.10)
2. **Phase 2**: Thread safety & lifecycle (P2.1-P2.6)
3. **Phase 3**: Dead code removal (P3.1-P3.8)
4. **Phase 4**: Matplotlib memory fixes (P4.1-P4.4)
5. **Phase 5**: Pandas cleanup (P5.1-P5.3)
6. **Phase 6**: Architecture fixes (P6.1-P6.3)
7. **Phase 7**: Parsing layer fixes (P7.1-P7.6)
8. **Phase 8**: Core layer fixes (P8.1-P8.6)
9. **Phase 9**: Plotly optimization (P9.1)
10. **Phase 10**: Python 3.12+ modernization (P10.1-P10.7)
11. **Phase 11**: Lint & format (P11.1-P11.4)
12. **Phase 12**: Comprehensive test writing (P12.1-P12.10)
13. **Phase 13**: Architecture improvements (P13.1-P13.6)
14. **Phase 14**: Test coverage expansion (P14.1-P14.10)

**Estimated total**:
- ~80+ TODO items to implement
- ~1,200+ lines of dead code to remove
- ~30+ new test methods to write
- ~370+ private attribute test accesses to refactor (Phase 14.4)
- 26 redundant pd.DataFrame() wrappers to remove

---

## Verification Commands

```bash
# Quick check (after each phase)
./python_venv/bin/pytest tests/ -o "addopts=" -x -q

# Full check (after all phases)
./python_venv/bin/pytest tests/ -o "addopts=" -v
./python_venv/bin/mypy src/ --show-error-codes
./python_venv/bin/black --check src/ tests/
./python_venv/bin/isort --check --profile=black --line-length=100 src/ tests/
```
