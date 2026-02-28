# Comprehensive Implementation Plan & Log

> **Source**: 16-track thorough investigation of the entire codebase
> **Total findings**: 126 items across 16 tracks
> **Created**: 2026-02-27
> **Final state**: ALL phases complete. 14 commits, 3492 tests passing, 0 regressions.
> **Last updated**: 2026-02-28

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
- **Commit**: `e509782`

### P2.2 [DONE] Health monitor shutdown uses plain bool instead of Event (Track 5.8, 2.4)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- **Fix**: Replaced `self._shutdown = False` with `self._shutdown_event = threading.Event()`. Monitor loop uses `event.wait(timeout=interval)` for interruptible sleep (wakes instantly on shutdown). Added `thread.join(timeout=interval+1)` in `shutdown()`.
- **Commit**: `e509782`

### P2.3 [DONE] Three unprotected singleton patterns (Track 5.5, 5.7, 5.9)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/pool/work_pool.py`, `src/parsing/gem5/impl/pool/pool.py`
- **Fix**: Added `_new_lock = threading.Lock()` to WorkPool `__new__`. Added `_singleton_lock` to ScanWorkPool and `_instance_lock` to ParseWorkPool. All `get_instance()` and `reset()` methods now use `with cls._lock:`.
- **Commit**: `e509782`

### P2.4 [DONE] Thread accumulation on timeout (Track 2.3)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- **Fix**: Replaced per-read thread spawn with a persistent reader thread per worker. `_start_reader_thread()` creates ONE daemon thread that reads stdout into a `queue.Queue`. `_read_line_with_timeout()` simply pulls from the queue with timeout. 4 workers = 4 reader threads (constant), instead of N threads per parse.
- **Commit**: `e509782`

### P2.5 [DONE] is_busy TOCTOU and health monitor I/O collision (Track 5.3, 5.11)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- **Fix**: Added `time.time() - worker.last_used < 60.0` skip in `_check_worker_health()`. Workers used within the last 60s are skipped, eliminating the TOCTOU window where health check PING/PONG could interfere with an imminent parse.
- **Commit**: `e509782`

### P2.6 [DONE] Queue starvation on all-worker fail (Track 5.6)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- **Fix**: Implemented circuit-breaker pattern: total timeout split across retries (`per_attempt_timeout = max(5s, timeout / max_retries)`). Added `failures` counter and healthy-worker check before each attempt. If `healthy_count == 0 and failures > 0`, raises immediately instead of blocking for N × timeout.
- **Commit**: `e509782`

---

## Phase 3: Dead Code Removal

### P3.1 [DONE] Remove 12 dead utility functions (Track 1.1)

- **Severity**: HIGH
- **File**: `src/core/common/utils.py`
- **Fix**: Removed 12 dead functions, `JsonValue` type alias, and unused `enum`/`tempfile` imports. Kept alive: `checkFileExistsOrException`, `sanitize_log_value`, `sanitize_filename`, `validate_path_within`, `sanitize_glob_pattern`, `normalize_user_path`. File reduced from 368 to 171 lines (~200 lines removed).
- **Commit**: `a916548`

### P3.2 [DONE] Rewrite test_utils.py for alive functions only (Track 1.1)

- **File**: `tests/unit/test_utils.py`
- **Fix**: Rewrote to only test alive functions: `checkFileExistsOrException`, `sanitize_log_value`, `sanitize_filename`, `validate_path_within`, `sanitize_glob_pattern`, `normalize_user_path`. File reduced from 252 to 148 lines.
- **Commit**: `a916548`

### P3.3 [DONE] Delete dead duplicate: plot_manager_components.py (Track 1.2)

- **File deleted**: `src/web/pages/ui/components/plot_manager_components.py`
- **Verified**: Byte-identical to canonical `src/web/components/plotting/plot_manager_components.py`. Zero production imports. Test files reference the canonical path.
- **Commit**: `a916548`

### P3.4 [DONE] Delete dead duplicate: split_apply_config.py (Track 1.3, 7.2)

- **File deleted**: `src/web/pages/ui/components/shapers/split_apply_config.py`
- **Verified**: Byte-identical to canonical `src/web/components/shapers/split_apply_config.py`. Zero production imports. Also removed empty parent directories.
- **Commit**: `a916548`

### P3.5 [DONE] Delete dead duplicate: ChartPresenter (Track 7.1, 4.7)

- **File deleted**: `src/web/presenters/plot/chart_presenter.py`
- **Also updated**: `src/web/presenters/plot/__init__.py` — removed ChartPresenter import and export.
- **Verified**: Zero imports anywhere in codebase or tests.
- **Commit**: `a916548`

### P3.6 [SKIP] Dead data_manager directories (Track 1.4, 1.8)

- **Finding**: Directory `src/web/pages/ui/components/data_managers/` does not exist. No action needed.

### P3.7 [DONE] Remove unused list comprehension in mixer.py (Track 4.10)

- **File**: `src/web/components/data_managers/mixer.py`, line 43
- **Fix**: Removed orphaned list comprehension whose result was never assigned.
- **Commit**: `a916548`

### P3.8 [DONE] Remove extract_with_pattern duplication (Track 7.6)

- **File**: `src/web/components/shapers/pivot_config.py`
- **Fix**: Replaced local `extract_with_pattern` definition with import from `src.core.services.shapers.impl.pivot`. ~14 lines removed.
- **Commit**: `a916548`

---

## Phase 4: Matplotlib Memory Leak Fixes

### P4.1 [DONE] Zero plt.close() calls in entire codebase (Track 10.2)

- **Severity**: HIGH
- **File**: `src/web/components/common/chart_display.py`
- **Bug**: Figure created via `plt.subplots()` but never closed. Memory leak in long-running Streamlit sessions.
- **Fix**: Close previous figure from session_state before creating new one. Added try/except to close figure on render failure. Import `matplotlib.pyplot as plt` and `logging` at module level.
- **Commit**: `da5707d`

### P4.2 [DONE] Figure objects stored in session_state (Track 10.3)

- **Severity**: HIGH
- **File**: `src/web/components/common/chart_display.py`
- **Bug**: Matplotlib Figure object stored in `st.session_state[f"plot.{plot_id}.mpl_fig"]`. Old figures never garbage collected when re-rendered.
- **Fix**: Close and delete old figure from session_state at start of `render_matplotlib_chart()` before creating the new one. Keeps at most 1 unclosed figure per plot. Download path still works via session_state.
- **Commit**: `da5707d`

### P4.3 [DONE] st.pyplot() without cleanup (Track 10.4)

- **Severity**: HIGH
- **File**: `chart_display.py`
- **Bug**: `st.pyplot(mpl_fig)` with no cleanup. chart_presenter.py already deleted in P3.5.
- **Fix**: Figure lifecycle managed: old figure closed before new render, exception path closes on failure.
- **Commit**: `da5707d`

### P4.4 [SKIP] Plot cache eviction doesn't close figures (Track 10 related)

- **File**: `src/core/performance.py` — `_plot_cache` stores Plotly `go.Figure` objects, NOT matplotlib figures
- **Finding**: The `_plot_cache` (used in `render_controller.py:226`) caches Plotly figures which are regular Python objects without file descriptors. No special cleanup needed. Matplotlib figures are managed separately via session_state (fixed in P4.1-P4.3).

---

## Phase 5: Pandas Cleanup

### P5.1 [DONE] Remove 26 redundant pd.DataFrame() wrappers (Track 13.5, 3.3)

- **Severity**: HIGH (unnecessary copies across 12 files)
- **Fix**: Removed redundant `pd.DataFrame()` wrappers from boolean indexing results across 12 files: condition_selector.py (6), item_selector.py (2), column_selector.py (1), split_apply.py (1), normalize.py (1), reduction_service.py (3), data_manager_components.py (3), bar_plot.py (3), stacked_bar_plot.py (1), dual_axis_bar_dot_plot.py (1), grouped_stacked_bar_plot.py (1), grouped_bar_plot.py (5). ~28 wrappers removed total.
- **Commit**: `b1613dc`

### P5.2 [DONE] Replace iterrows() with vectorized zip() (Track 13.3)

- **Severity**: MEDIUM
- **File**: `src/web/pages/ui/plotting/types/stacked_bar_plot.py`, line 162
- **Bug**: `for _, row in data.iterrows()` in `_build_totals_annotations()`.
- **Fix**: Replaced with `zip(data["__total"], data[x_col])` — avoids iterrows overhead and handles dunder column names (which `itertuples` can't).
- **Commit**: `b1613dc`

### P5.3 [DONE] Use .pipe() for shaper pipeline (Track 13.1)

- **Severity**: MEDIUM
- **File**: `src/core/services/shapers/pipeline_service.py`
- **Fix**: Replaced `current_data = shaper(current_data)` with `current_data = current_data.pipe(shaper)` in process_pipeline loop. Per-shaper timing and error context preserved.
- **Commit**: `4a7302f`

---

## Phase 6: Architecture Fixes

### P6.1 [DONE] Fix Web-to-Parsing direct imports — 3 violations (Track 11.1)

- **Severity**: MEDIUM-HIGH
- **Files with violations**:
  - `src/web/pages/data_source.py:9` — imported `SimulatorRegistry`
- **Fix**: Replaced `SimulatorRegistry.available_simulators()` with `ApplicationAPI.available_simulators()` and `SimulatorRegistry.get_info(selected_sim)` with `ApplicationAPI.get_simulator_info(selected_sim)`. Facade methods already existed on ApplicationAPI.
- **Commit**: `2bca9d9`

### P6.2 [DONE] Pivot config unbound variables — real bug (Track 16.1, 4.8)

- **Severity**: MEDIUM
- **File**: `src/web/components/shapers/pivot_config.py`, lines 256-258
- **Bug**: `selection_filters`, `strategy`, `merge_label` only defined inside nested conditional. Used unconditionally. `"x" in locals()` guards were fragile.
- **Fix**: Initialized defaults before the conditional block. Removed `"x" in locals()` checks.
- **Commit**: `2bca9d9`

### P6.3 [SKIP] st.rerun() scope mismatches (Track 9.6)

- **Severity**: MEDIUM
- **Finding**: Investigated all 4 occurrences. Dialogs trigger full page reruns (correct behavior). Fragment reruns cover all relevant UI within the fragment. No scope mismatch exists.
- **Commit**: N/A — no changes needed

---

## Phase 7: Parsing Layer Fixes

### P7.1 [DONE] CSV header built from first result only (Track 2.8)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/gem5_parser.py`, lines 269-282
- **Bug**: Header built from `results[0]` only. If first file is missing a variable that later files have, header is permanently incomplete.
- **Fix**: Build header as union of all results' entries, with consistent column ordering.
- **Commit**: `4469ee7`

### P7.2 [DONE] Mixed return types in scalar.py (Track 2.11)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/types/scalar.py`, lines 49-61
- **Bug**: `_reduced_content` is either "NA" (str) or float. Downstream expecting float gets str.
- **Fix**: Use `math.nan` instead of `"NA"` for missing values. Updated test to use `math.isnan()`.
- **Commit**: `4469ee7`

### P7.3 [DONE] Silent scan error returns empty instead of error (Track 2.13)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/scanning/gem5_scan_work.py`, line 40
- **Fix**: Added `logger.warning` with `exc_info=True` on exception before returning `[]`. Callers can now see why scanning failed in logs.
- **Commit**: `4469ee7`

### P7.4 [DONE] Broad exception in config_aware.py (Track 2.12)

- **Severity**: LOW
- **File**: `src/parsing/gem5/impl/strategies/config_aware.py`, line 73
- **Fix**: Narrowed to `except (configparser.Error, OSError)`. Updated test mock to raise `configparser.Error` instead of `Exception`.
- **Commit**: `4469ee7`

### P7.5 [DONE] Histogram silent range parse failures (Track 2.14)

- **Severity**: LOW
- **File**: `src/parsing/gem5/types/histogram.py`, lines 302-307
- **Fix**: Added `logger.debug` for failed range parses on keys that contain digits (look numeric but aren't parseable).
- **Commit**: `4469ee7`

### P7.6 [DONE] Distribution precision with sum() (Track 14.4)

- **Severity**: LOW
- **File**: `src/parsing/gem5/types/distribution.py`, lines 200-201, 234
- **Fix**: Replaced `sum(float_vals)` with `math.fsum(float_vals)` for Shewchuk compensated summation.
- **Commit**: `4469ee7`

---

## Phase 8: Core Layer Fixes

### P8.1 [DONE] Broad except in pivot.py (Track 3.1)

- **Severity**: MEDIUM
- **File**: `src/core/services/shapers/impl/pivot.py`, line 49
- **Fix**: Narrowed to `except (re.error, TypeError, IndexError)` + `logger.warning(...)`. Added `@override`.
- **Commit**: `8bacd84`

### P8.2 [DONE] Off-by-one CSV row count (Track 3.4)

- **Severity**: LOW
- **File**: `src/core/services/data_services/csv_pool_service.py`, line 277
- **Fix**: `max(0, sum(1 for _ in f) - 1)` guard for empty files.
- **Commit**: `8bacd84`

### P8.3 [DONE] Portfolio migrator mutates input dict (Track 3.5)

- **Severity**: MEDIUM
- **File**: `src/core/services/portfolio_migrator.py`, line 64
- **Fix**: Added `data = copy.deepcopy(data)` at top of migration to prevent mutation of input.
- **Commit**: `8bacd84`

### P8.4 [DONE] Normalize performance: .values vs .unique() (Track 3.6)

- **Severity**: LOW
- **File**: `src/core/services/shapers/impl/normalize.py`, line 189
- **Fix**: Replaced `.values` with `.unique()` for membership check.
- **Commit**: `8bacd84`

### P8.5 [SKIP] Silent type coercion failure in state manager (Track 3.7)

- **Severity**: MEDIUM
- **Finding**: The log-and-continue pattern is appropriate here. The state manager stores the data regardless, and the coercion failure is logged. Re-raising would break the UI flow for a non-critical type annotation issue.

### P8.6 [DONE] Numpy reference in normalize.py (Track 3.10)

- **Severity**: LOW
- **File**: `src/core/services/shapers/impl/normalize.py`, line 318
- **Fix**: Replaced `.values` with `.copy()` to avoid numpy memory sharing.
- **Commit**: `8bacd84`

---

## Phase 9: Plotly Optimization

### P9.1 [SKIP] Batch 11 scattered fig.update_layout() calls (Track 10.1)

- **Severity**: MEDIUM
- **File**: `src/web/rendering/plotly_connector.py`
- **Finding**: Analyzed 11 `fig.update_layout()` calls across 10+ `_apply_*()` methods. Batching would require significant refactoring of the method decomposition for microseconds of Plotly validation overhead. Poor risk/reward ratio.

---

## Phase 10: Python 3.12+ Modernization

### P10.1 [DONE] Add @override decorators to 55+ method overrides (Track 6.4, 8.4)

- **Severity**: MEDIUM
- **Files**: 22 classes across 3 layers:
  - 5 StatType subclasses (`scalar.py`, `vector.py`, `histogram.py`, `distribution.py`, `configuration.py`)
  - 9 Shaper subclasses + 2 Pivot classes (`pivot.py`, `normalize.py`, `selector.py`, `sort.py`, `transformer.py`, `mean.py`, `split_apply.py`, `shaper_config.py`)
  - 9 BasePlot subclasses (all plot types)
- **Fix**: Added `from typing import override` and `@override` to all overridden methods. 55+ decorators total.
- **Commit**: `5f9bf7c`

### P10.2 [SKIP] Create StrEnum for registry keys (Track 8.1)

- **Finding**: Factory string keys are used as dict lookups and match expressions. Adding StrEnum would require changing all callers for marginal type safety gain. Skipped.

### P10.3 [DONE] Convert if/elif chains to match/case (Track 8.2)

- **Severity**: MEDIUM-HIGH
- **File**: `src/core/services/shapers/impl/selector_algorithms/condition_selector.py`
- **Fix**: Converted 4-branch mode dispatch (`greater_than`, `less_than`, `equals`, `contains`) from if/elif to match/case.
- **Commit**: `5f9bf7c`

### P10.4 [SKIP] Add @runtime_checkable to 10 protocols (Track 6.3)

- **Finding**: Protocols work correctly without `@runtime_checkable`. Adding it enables `isinstance()` checks but none of the existing code uses them. Skipped — no behavioral benefit.

### P10.5 [SKIP] PEP 695 type statements (Track 8.3)

- **Finding**: Low-priority syntax modernization. Existing `TypeAlias` annotations work fine. Skipped.

### P10.6 [SKIP] PEP 695 generics: single TypeVar (Track 8.5)

- **Finding**: Single `TypeVar` in `performance.py`. Converting to PEP 695 syntax provides no functional benefit. Skipped.

### P10.7 [DONE] f-string cleanup (Track 8.7)

- **Severity**: LOW
- **File**: `src/web/pages/ui/shaper_config.py`
- **Fix**: Removed 3 redundant `str()` calls in f-strings.
- **Commit**: `5f9bf7c`

---

## Phase 11: Lint & Format

### P11.1 [SKIP] isort fixes for source files (Track 16.2)

- **Finding**: Pre-commit hooks (black, isort, flake8) run on every commit. All flagged files already pass isort checks. No action needed.

### P11.2 [SKIP] isort fixes for test files (Track 16.3)

- **Finding**: Pre-commit hooks enforce isort on all files. All test files pass. No action needed.

### P11.3 [SKIP] trunk fmt for markdown files (Track 16.4, 16.5, 16.6)

- **Finding**: Markdown formatting is not enforced by pre-commit hooks. `.agent/` markdown files are documentation artifacts, not production code. Skipped.

### P11.4 [SKIP] Final trunk check verification (Track 16.7, 16.8)

- **Finding**: All pre-commit hooks pass on every commit (black, flake8, mypy, isort, bandit, pyupgrade, and custom hooks). Trunk is not configured in this project. No action needed.

---

## Phase 12: Comprehensive Test Writing

### P12.1 [DONE] SimpleCache thread safety tests (Track 12.1, 5.1)

- **File**: `tests/unit/test_simple_cache.py` (NEW — 14 tests)
- **Coverage**: Basic ops (get/set/clear/stats), TTL expiration, LRU eviction, thread safety with `threading.Barrier` concurrent access.
- **Commit**: `89011f5`

### P12.2 [DONE] Architecture import boundary tests (P6.1)

- **File**: `tests/unit/test_architecture_boundary.py` (NEW — 2 tests)
- **Coverage**: AST-based scanning to verify zero `from src.parsing` imports in `src/web/`. Verifies architecture invariant at test time.
- **Commit**: `89011f5`

### P12.3 [DONE] Selector algorithm tests (P5.1, P12.6)

- **File**: `tests/unit/test_selector_algorithms.py` (NEW — 9 tests)
- **Coverage**: All 4 selector types (condition, item, column, range) return DataFrame. Tests all condition_selector modes (greater_than, less_than, equals, contains).
- **Commit**: `89011f5`

### P12.4 [DONE] Refactoring coverage tests (P7.1-P7.6, P8.1, P1.7, P1.9)

- **File**: `tests/unit/test_refactor_coverage.py` (NEW — 26 tests)
- **Coverage**: Mean NaN handling (gmean/hmean), scalar nan return, distribution fsum precision, extract_with_pattern, CSV header union, normalize NaN baseline.
- **Commit**: `89011f5`

### P12.5-P12.10 [DONE] Consolidated into above test files

- **Finding**: All test requirements from P12.5-P12.10 were covered by the 4 new test files above. 50 new tests total, test suite went from 3441 to 3492.
- **Commit**: `89011f5`

---

## Phase 13: Architecture Improvements (Optional but Recommended)

### P13.1 [SKIP] Create ParserBackend protocol (Track 11.3)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py` (560 lines)
- **Finding**: PerlWorkerPool has no protocol/abstraction. Hardcoded to subprocess-based Perl execution. No other parser backends exist, so an abstraction would be premature.

### P13.2 [SKIP] ColumnBasedSelector mixin (Track 11.2)

- **Severity**: LOW
- **Files**: `column_selector.py`, `item_selector.py`, `condition_selector.py`
- **Finding**: All 3 selectors duplicate `super()._verify_params()` + cast pattern. However, the duplication is just 1 line per file — not worth a mixin abstraction.

### P13.3 [DONE] Cached shaper fingerprint consolidation (Track 15.1)

- **Severity**: MEDIUM
- **Files**: `mean.py`, `normalize.py`, `performance.py`
- **Fix**: Extracted identical `_compute_data_fingerprint()` static methods from Mean and Normalize into shared `compute_data_fingerprint()` in `src/core/performance.py`. ~60 lines of duplication removed. Updated test files to use the shared function.
- **Commit**: `50423ab`

### P13.4 [SKIP] Centralize UIStateManager usage (Track 7.4, 4.1)

- **Severity**: LOW-MEDIUM
- **Finding**: 10-13 direct `st.session_state[` bypasses across UI files. Large UI refactor with high regression risk and low ROI.

### P13.5 [SKIP] Centralize widget key builder (Track 11.6)

- **Severity**: LOW-MEDIUM
- **Finding**: 94+ unique key patterns, 120+ total `key=` statements. Centralizing would touch 12+ settings files. Risk/reward not justified.

### P13.6 [SKIP] Standardize settings components (Track 11.5)

- **Severity**: LOW
- **Finding**: 7 class-based, 4 function-based across 11 settings files. Standardizing would be a large UI refactor with minimal benefit.

---

## Phase 14: Test Coverage Expansion (Track 12)

### P14.1 [SKIP] SimpleCache unit test suite (Track 12.1)

- **Priority**: HIGH
- **Finding**: Already implemented in P12.1 — `tests/unit/test_simple_cache.py` with 14 tests.

### P14.2 [SKIP] Config builder unit tests (Track 12.1)

- **Priority**: MEDIUM
- **Finding**: config_builder.py has integration tests. Dedicated unit suite not warranted — existing coverage is adequate.

### P14.3 [SKIP] Reorderable list and filtered selector unit tests (Track 12.2)

- **Priority**: MEDIUM
- **Finding**: Tested through E2E/UI-logic tests. Dedicated unit tests would test Streamlit widgets, adding complexity without value.

### P14.4 [SKIP] Refactor private attribute test accesses (Track 12.3)

- **Priority**: HIGH
- **Finding**: 370+ private attribute accesses across test suite. Refactoring would require adding public accessors to 20+ production classes. Risk/reward ratio does not justify the scope.

### P14.5 [SKIP] Replace flaky timing tests (Track 12.4)

- **Priority**: MEDIUM-HIGH
- **Finding**: 13 `time.sleep()` calls across tests. Most are for file timestamp granularity (1.1s). Replacing with event-based waits would change test semantics without clear benefit.

### P14.6 [DONE] Shaper edge case tests (Track 12.5)

- **Priority**: MEDIUM
- **File**: `tests/unit/test_shaper_edge_cases.py` (NEW — 17 tests)
- **Coverage**: Unicode column names (selectors, mean), numeric precision (very small/large baselines), NaN propagation chains (all-NaN gmean, zero hmean, NaN baseline), large DataFrame smoke tests (10k rows), mixed int/float types.
- **Commit**: `a8dc19e`

### P14.7 [SKIP] Concurrent PerlWorkerPool tests (Track 12.7)

- **Priority**: MEDIUM
- **Finding**: No concurrent access tests. Would require mock-subprocess infrastructure that doesn't exist. Sequential tests in integration suite provide adequate coverage.

### P14.8 [DONE] E2E integration test: Parse -> Load -> Transform -> Plot (Track 12.8)

- **Priority**: MEDIUM
- **File**: `tests/integration/test_full_pipeline_e2e.py` (NEW — 9 tests)
- **Coverage**: Multi-shaper pipeline chains (column select→sort, filter→normalize, filter→normalize→geomean, item select→columns), empty pipeline, null type skipping, invalid shaper error, persistence save/load/delete lifecycle.
- **Commit**: `a8dc19e`

### P14.9 [DONE] Binary file rejection tests (Track 12.10)

- **Priority**: MEDIUM
- **File**: `tests/unit/test_parser_robustness.py` (NEW — 11 tests)
- **Coverage**: Binary file handling (null bytes, pure binary, PNG/ZIP magic bytes, PDF header), encoding edge cases (Latin-1, UTF-16, UTF-8 BOM), CsvPoolService rejection (binary, empty, directory), path edge cases (nonexistent, empty, whitespace).
- **Commit**: `a8dc19e`

### P14.10 [SKIP] Fixture consolidation (Track 12.9)

- **Priority**: LOW
- **Finding**: No true duplicates. Naming inconsistency is cosmetic. Low value.

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

| Phase | Status | Commit | Description |
|-------|--------|--------|-------------|
| 1 | DONE | `da2bf11`, `9b60a95`, `6aff643` | CRITICAL bug fixes (P1.1-P1.10) |
| 2 | DONE | `e509782` | Thread safety & lifecycle (P2.1-P2.6) |
| 3 | DONE | `a916548` | Dead code removal — ~1000 lines (P3.1-P3.8) |
| 4 | DONE | `da5707d` | Matplotlib memory leak fixes (P4.1-P4.3) |
| 5 | DONE | `b1613dc`, `4a7302f` | Pandas cleanup + .pipe() (P5.1-P5.3) |
| 6 | DONE | `2bca9d9` | Architecture boundary + unbound vars (P6.1-P6.2) |
| 7 | DONE | `4469ee7` | Parsing layer robustness (P7.1-P7.6) |
| 8 | DONE | `8bacd84` | Core layer robustness (P8.1-P8.6) |
| 9 | SKIP | — | Plotly batching — marginal gain |
| 10 | DONE | `5f9bf7c` | @override (55+), match/case, f-string cleanup |
| 11 | SKIP | — | Pre-commit hooks already enforce |
| 12 | DONE | `89011f5` | 50 new tests (cache, boundary, selector, coverage) |
| 13 | DONE | `50423ab` | Fingerprint consolidation (P13.3); P13.1-2,4-6 skipped |
| 14 | DONE | `a8dc19e` | 37 new tests: edge cases, E2E pipeline, binary rejection |
| Final | DONE | `92f9627` | Dead code sweep — 3 duplicate files removed |

**Final metrics**:
- 16 commits on branch
- 3529 tests passing (up from 3441 — 88 new tests)
- ~1400+ lines of dead code removed
- ~60 lines of duplication consolidated (fingerprint helper)
- 55+ `@override` decorators added
- All pre-commit hooks pass (black, flake8, mypy, isort, bandit, custom hooks)
- Zero regressions throughout

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
