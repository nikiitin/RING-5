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

### P1.2 [WIP] SimpleCache has NO thread locks (Track 5.1)

- **Severity**: CRITICAL
- **File**: `src/core/performance.py` (199 lines)
- **Bug**: SimpleCache uses plain `dict` for storage with no synchronization. Docstring falsely claims "Thread-safe". Concurrent access from CSV pool and plot cache causes race conditions: lost writes, corrupted dict during resize, stale reads during eviction. Stats counters `_hits`/`_misses` also unprotected.
- **Fix**: Added `self._lock = threading.Lock()` in `__init__`. Wrapped `get()`, `set()`, `clear()`, `stats()` with `with self._lock:`.
- **Status**: Code modified, NOT yet committed.

### P1.3 [TODO] CsvPoolService `_pool_index` has no lock (Track 5.2)

- **Severity**: CRITICAL
- **File**: `src/core/services/data_services/csv_pool_service.py` (314 lines), line 91
- **Bug**: `_pool_index` dict has no lock. `_metadata_cache` and `_dataframe_cache` inherit SimpleCache's lack of locks (will be fixed by P1.2). File header comment falsely claims "Thread-safe (SimpleCache uses locks)".
- **Fix**: Add `_pool_lock = threading.Lock()` class attribute. Wrap all `_pool_index` reads/writes with `with cls._pool_lock:`. Fix false documentation.

### P1.4 [TODO] Scalar `int()` truncation silently corrupts data (Track 2.10)

- **Severity**: HIGH
- **File**: `src/parsing/gem5/types/scalar.py`, line 60
- **Bug**: `int(self._content[i])` truncates decimal values during reduce. Example: [1.5, 2.7, 3.1] -> sum=6 instead of 7.3. Silent data corruption.
- **Fix**: Replace `int()` with `float()` in the summation loop.

### P1.5 [TODO] Shallow copy shares mutable state between aliased variables (Track 2.6)

- **Severity**: HIGH
- **File**: `src/parsing/gem5/impl/strategies/simple.py`, line 184
- **Bug**: `copy.copy(stat_obj)` shares nested mutable state (`_content` is list or dict[str,list]) between aliased variables. Mutation via `balance_content()` corrupts aliased variables.
- **Fix**: Replace `copy.copy(stat_obj)` with `copy.deepcopy(stat_obj)`.

### P1.6 [TODO] Unchecked array index crashes worker on malformed Perl output (Track 2.1)

- **Severity**: HIGH
- **File**: `src/parsing/gem5/impl/strategies/gem5_parse_work.py`, line 103
- **Bug**: `parts = line.split("/")` then `parts[0], parts[1], parts[2]` accessed without bounds check. Malformed Perl output causes IndexError, killing the worker and failing the entire parse batch.
- **Fix**: Add `if len(parts) < 3: logger.warning(...); continue`.

### P1.7 [TODO] Mean NaN handling inconsistent across algorithms (Track 14.2)

- **Severity**: HIGH
- **File**: `src/core/services/shapers/impl/mean.py`, lines 218-226
- **Bug**: `arithmean` uses `grouped.mean()` (skipna=True — correct). `geomean` uses `scipy.stats.gmean` which does NOT skip NaN (propagates NaN). `hmean` uses `scipy.stats.hmean` which does NOT skip NaN. A single NaN in a group causes geomean/hmean to return NaN for entire group while arithmean skips it.
- **Fix**: Filter NaN before scipy calls:
  ```python
  def _safe_gmean(series):
      clean = series.dropna()
      if clean.empty or (clean <= 0).any():
          return np.nan
      return gmean(clean)
  ```

### P1.8 [TODO] Mixer None checks crash on widget None returns (Track 4.2)

- **Severity**: HIGH
- **File**: `src/web/components/data_managers/mixer.py` (173 lines)
- **Bug**: Line 69 `st.segmented_control()` returns `str | None`; line 95 `st.selectbox()` also nullable. Line 105 calls `.lower()` on potentially None `operation` -> AttributeError crash.
- **Fix**: Add early returns: `if mode is None: return cfg` after line 69; `if operation is None: return cfg` after line 95.

### P1.9 [TODO] Normalize NaN denominator not checked (Track 14.1)

- **Severity**: MEDIUM (but data-correctness impact)
- **File**: `src/core/services/shapers/impl/normalize.py`, line 230
- **Bug**: Zero check exists but NaN check missing. If baseline values contain NaN, `sum()` returns NaN, the zero-check fails (NaN != 0), and division produces NaN throughout all normalized columns. No warning emitted.
- **Fix**: Add `pd.isna(denominator)` check alongside zero check:
  ```python
  if pd.isna(denominator) or denominator == 0:
      # ... zero/NaN handling
  ```

### P1.10 [TODO] DataFrame stored by reference when no type casting needed (Track 3.9)

- **Severity**: HIGH
- **File**: `src/core/state/repository_state_manager.py`, line 68
- **Bug**: DataFrame only `.copy()`-ed if type casting is needed (cols_to_cast non-empty). When no casting needed, stored as reference. External mutations propagate to stored data.
- **Fix**: Always copy DataFrame before storing: `data = data.copy()` before try block.

---

## Phase 2: Thread Safety & Lifecycle

### P2.1 [TODO] WorkPool has NO shutdown mechanism (Track 5.4, 5.10)

- **Severity**: HIGH
- **File**: `src/parsing/gem5/impl/pool/work_pool.py`
- **Bug**: No `shutdown()` method. No `__del__`, no `atexit` handler. On Streamlit hot-reload, `_instance` reset to None, new executors created, old ones orphaned. N hot-reloads = N orphaned process pools. Executor shutdown cascade: ScanWorkPool -> WorkPool -> Executors reference chain breaks.
- **Fix**: Add `shutdown()` method to WorkPool. Register `atexit.register(shutdown_worker_pool)` inside `get_worker_pool()`. Add `__del__` to PerlWorkerPool that calls `self.shutdown()`.

### P2.2 [TODO] Health monitor shutdown uses plain bool instead of Event (Track 5.8, 2.4)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 353, 404-411
- **Bug**: Plain `bool` `_shutdown` with 30s `time.sleep()` poll. On `shutdown()`, monitor may sleep up to 30s before checking flag. No `thread.join()` in shutdown.
- **Fix**: Replace `bool` with `threading.Event()`. Use `event.wait(timeout=interval)` for interruptible sleep. Add `thread.join(timeout=interval+1)` in `shutdown()`.

### P2.3 [TODO] Three unprotected singleton patterns (Track 5.5, 5.7, 5.9)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/pool/work_pool.py`
- **Bug**: `__new__` check-then-act on `_instance` is not atomic. No lock. GIL mostly prevents races but pattern is fragile. Affects WorkPool, ScanWorkPool, ParseWorkPool.
- **Fix**: Add `threading.Lock` to all three `get_instance()` / `__new__` methods.

### P2.4 [TODO] Thread accumulation on timeout (Track 2.3)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, line 134
- **Bug**: Spawns daemon thread per `_read_line_with_timeout()` call. On timeout, thread stays alive. No max limit. Rapid timeouts accumulate leaked threads.
- **Fix**: Replace with `selectors` module or `select.select()` for non-blocking reads.

### P2.5 [TODO] is_busy TOCTOU and health monitor I/O collision (Track 5.3, 5.11)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 417-442, 467-487
- **Bug**: Health monitor checks `is_busy=False` without lock, then calls `health_check()`. Between check and ping, parse can start. Health monitor ping interferes with active parse I/O causing spurious timeouts and protocol desync. Not data corruption, but triggers unnecessary restarts.
- **Fix**: Acquire worker lock before checking is_busy. Or skip health_check entirely if worker was recently active (preferred).

### P2.6 [TODO] Queue starvation on all-worker fail (Track 5.6)

- **Severity**: MEDIUM
- **File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 460-485
- **Bug**: `worker_queue.get(timeout=120)` blocks full timeout per attempt. Worst case: 4 workers x 120s = 480s wait. No circuit-breaker.
- **Fix**: Implement circuit-breaker: shorter queue timeout, count failures, fail fast when >50% workers unhealthy.

---

## Phase 3: Dead Code Removal

### P3.1 [TODO] Remove 12 dead utility functions (Track 1.1)

- **Severity**: HIGH
- **File**: `src/core/common/utils.py`, lines 21-224
- **Dead functions**: `getElementValue`, `checkElementExists`, `checkElementExistNoException`, `checkEnumExistsNoException`, `getEnumValue`, `checkFilesExistOrException`, `checkFileExists`, `checkDirExistsOrException`, `checkDirExists`, `createDir`, `createTmpFile`, `checkVarType`
- **Keep alive**: `checkFileExistsOrException` (used by gem5_parse_work.py:285), `sanitize_log_value`, `sanitize_filename`, `validate_path_within`, `sanitize_glob_pattern`, `normalize_user_path`
- **Also remove**: `JsonValue` type alias (only used by dead functions), unused imports (enum, tempfile)
- **Impact**: ~200 lines removed

### P3.2 [TODO] Delete dead test file or update to only test alive functions (Track 1.1)

- **File**: `tests/unit/test_utils.py` (252 lines)
- **Action**: Remove tests for dead functions. Keep tests for `checkFileExistsOrException` and other alive functions.
- **Impact**: ~200 lines of dead test code removed

### P3.3 [TODO] Delete dead duplicate: plot_manager_components.py (Track 1.2)

- **File**: `src/web/pages/ui/components/plot_manager_components.py` (~200 lines)
- **Finding**: pages/ui copy CONFIRMED DEAD (MD5 identical, zero imports). components/plotting copy is ALIVE.
- **Impact**: ~200 lines removed

### P3.4 [TODO] Delete dead duplicate: split_apply_config.py (Track 1.3, 7.2)

- **File**: `src/web/pages/ui/components/shapers/split_apply_config.py` (~361 lines)
- **Finding**: pages/ui copy CONFIRMED DEAD (byte-for-byte identical). Canonical: `src/web/components/shapers/split_apply_config.py` (imported by shaper_config.py).
- **Impact**: ~361 lines removed

### P3.5 [TODO] Delete dead duplicate: ChartPresenter (Track 7.1, 4.7)

- **Files to delete**: `src/web/presenters/plot/chart_presenter.py` (~240 lines)
- **Also update**: `src/web/presenters/plot/__init__.py` — remove ChartPresenter export
- **Finding**: ChartDisplayComponent is canonical (imported by render_controller.py:30). ChartPresenter is unused but exported from presenters/__init__.py.
- **Impact**: ~240 lines removed

### P3.6 [TODO] Delete dead duplicate data_manager directories (Track 1.4, 1.8)

- **Directories**: `src/web/pages/ui/components/data_managers/` and parent dirs with no `__init__.py`
- **Note**: Track 7.3 found these are NOT duplicates (different classes/responsibilities in different directories).
- **Action**: Re-verify before deleting. Only delete if truly dead (no imports).

### P3.7 [TODO] Remove unused list comprehension in mixer.py (Track 4.10)

- **File**: `src/web/components/data_managers/mixer.py`, line 43
- **Bug**: `[c for c in numeric_cols if not c.endswith((".sd", "_stdev"))]` result not assigned to any variable. Dead code from refactoring.
- **Fix**: Either assign to variable or remove the line.

### P3.8 [TODO] Remove extract_with_pattern duplication (Track 7.6)

- **Files**: Defined in BOTH `src/core/services/shapers/impl/pivot.py` (core) and `src/web/components/shapers/pivot_config.py` (UI)
- **Fix**: UI version should import from core. Remove duplicate. ~30 lines removed.

---

## Phase 4: Matplotlib Memory Leak Fixes

### P4.1 [TODO] Zero plt.close() calls in entire codebase (Track 10.2)

- **Severity**: HIGH
- **File**: `src/web/rendering/matplotlib_connector.py` (711 lines), line 706
- **Bug**: Figure created via `plt.subplots()` but never closed. Memory leak in long-running Streamlit sessions.
- **Fix**: Add `plt.close(fig)` after every matplotlib figure use. Use try/finally blocks.

### P4.2 [TODO] Figure objects stored in session_state (Track 10.3)

- **Severity**: HIGH
- **File**: `src/web/components/common/chart_display.py`, line 172
- **Bug**: Matplotlib Figure object stored in `st.session_state[f"plot.{plot_id}.mpl_fig"]`. Non-serializable, heavy, never garbage collected. Each rerender adds new Figure while old persists.
- **Fix**: Remove Figure from session_state. Store only metadata or rendered image bytes. Regenerate on-demand for downloads.

### P4.3 [TODO] st.pyplot() without cleanup (Track 10.4)

- **Severity**: HIGH
- **Files**: `chart_display.py:168`, `chart_presenter.py:243` (chart_presenter to be deleted in P3.5)
- **Bug**: `st.pyplot(mpl_fig)` with no subsequent `plt.close()`. Figures accumulate in matplotlib's global registry.
- **Fix**: Add `plt.close(mpl_fig)` after every `st.pyplot()` call. Also add in export paths (Track 10.6).

### P4.4 [TODO] Plot cache eviction doesn't close figures (Track 10 related)

- **File**: `src/core/performance.py`, line 88 — `_plot_cache` stores figure references
- **Bug**: When cache evicts entries, matplotlib figures aren't closed.
- **Fix**: Add eviction callback or close figures on evict.

---

## Phase 5: Pandas Cleanup

### P5.1 [TODO] Remove 26 redundant pd.DataFrame() wrappers (Track 13.5, 3.3)

- **Severity**: HIGH (unnecessary copies across 12 files)
- **Files and lines**:
  - `outlier_service.py`: lines 24, 27 (already fixed in Phase 1)
  - `condition_selector.py`: lines 92, 98, 102, 104, 106, 109
  - `item_selector.py`: line 72
  - `column_selector.py`: line 62
  - `split_apply.py`: line 252
  - `normalize.py`: line 229
  - `reduction_service.py`: line 31
  - `data_manager_components.py`: lines 89, 96, 116
  - `bar_plot.py`: lines 57, 79
  - `stacked_bar_plot.py`: line 61
  - `dual_axis_bar_dot_plot.py`: line 108
  - `grouped_stacked_bar_plot.py`: line 260
  - `grouped_bar_plot.py`: lines 32, 112, 114, 157
- **Fix**: Change `pd.DataFrame(data_frame[mask])` to `data_frame[mask]` everywhere. Zero behavior change.

### P5.2 [TODO] Replace iterrows() with itertuples() (Track 13.3)

- **Severity**: MEDIUM
- **File**: `src/web/pages/ui/plotting/types/stacked_bar_plot.py`, line 162
- **Bug**: `for _, row in data.iterrows()` in `_build_totals_annotations()`. iterrows() is slowest DataFrame iteration method.
- **Fix**: Replace with `.itertuples()` for 10-50x speedup on large datasets.

### P5.3 [TODO] Use .pipe() for shaper pipeline (Track 13.1)

- **Severity**: MEDIUM
- **File**: `src/core/services/shapers/pipeline_service.py`, lines 153-167
- **Bug**: Manual for-loop instead of pandas `.pipe()`.
- **Fix**: Refactor to use `.pipe()` for each shaper application. All 10 shapers have compatible `__call__(self, data_frame: pd.DataFrame) -> pd.DataFrame` signatures.

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
