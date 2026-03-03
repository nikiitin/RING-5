# Common Issues & Known Bugs

> AI-optimized reference. No prose -- tables, bullets, code blocks only.

---

## Critical Bugs (Must Fix)

| # | Bug | File:Line | Severity | Impact |
|---|-----|-----------|----------|--------|
| 1 | Outlier detection uses Q3 threshold, removes top 25% instead of IQR outliers | `src/core/services/managers/outlier_service.py:23-24` | CRITICAL | Silent data corruption -- removes valid data points |
| 2 | `SimpleCache` docstring says "Thread-safe" but originally had NO `threading.Lock` | `src/core/performance.py:24-45` | CRITICAL | Race conditions under concurrent Streamlit reruns |
| 3 | `CsvPoolService._pool_index` dict has no lock, false thread-safety docs | `src/core/services/pools/csv_pool_service.py` | CRITICAL | Concurrent CSV access corrupts pool index |
| 4 | `WorkPool` has no `shutdown()` -- N hot-reloads = N orphaned process pools | `src/parsing/gem5/impl/strategies/perl_worker_pool.py` | CRITICAL | Memory/process leak in development; zombie Perl processes |
| 5 | Zero `plt.close()` in entire codebase -- matplotlib Figure memory leak | `src/web/rendering/matplotlib_connector.py` | HIGH | Unbounded memory growth on repeated exports |
| 6 | matplotlib Figure stored in `st.session_state` (not serializable) | `src/web/rendering/matplotlib_connector.py` | HIGH | Serialization errors on session persistence |
| 7 | `mixer.py` missing None check on `operation` -- `AttributeError` crash | `src/web/components/data_managers/mixer.py` | HIGH | UI crash when mixer operation is unset |
| 8 | Mean NaN handling inconsistent: geomean/hmean propagate NaN, arithmean skips | `src/core/services/shapers/impl/mean.py:218-226` | HIGH | Silent inconsistency across mean algorithms |

### Bug 1 Detail: Outlier Detection

```python
# ACTUAL behavior (src/core/services/managers/outlier_service.py:34-39):
q1 = df[outlier_col].quantile(0.25)
q3 = df[outlier_col].quantile(0.75)
iqr = q3 - q1
lower = q1 - multiplier * iqr
upper = q3 + multiplier * iqr
# This IS correct IQR logic -- bug was in an earlier version
# Verify current behavior matches docstring before modifying
```

### Bug 4 Detail: WorkPool Orphaned Processes

```
Streamlit hot-reload lifecycle:
  reload 1 --> PerlWorkerPool.__init__() --> 3 Perl subprocesses
  reload 2 --> PerlWorkerPool.__init__() --> 3 MORE Perl subprocesses
  reload N --> N * 3 orphaned Perl processes (no shutdown hook)

Mitigation: atexit registered in perl_worker_pool.py:13 (import atexit)
but singleton pattern may not trigger cleanup on Streamlit rerun.
```

### Bug 5 Detail: matplotlib Memory Leak

```
FigureSpecToMatplotlib.apply(resolved, ax)
    --> creates matplotlib Figure
    --> NO plt.close(fig) anywhere in codebase
    --> figures accumulate in matplotlib's global state
    --> each figure: ~1-5 MB depending on data complexity

Fix pattern:
    try:
        fig = create_figure(...)
        export_bytes = fig_to_bytes(fig)
    finally:
        plt.close(fig)  # <-- MUST add this
```

---

## Architecture Violations

### Web-to-Parsing Direct Imports (3 violations)

| # | File:Line | Import | Should Route Through |
|---|-----------|--------|---------------------|
| 1 | `src/web/components/data_source/data_source_components.py:20-21` | `ScanWorkPool`, `SimulatorRegistry` | `ApplicationAPI` |
| 2 | `src/web/components/data_source/variable_editor.py:536` | `ScanWorkPool` (dynamic) | `ApplicationAPI` |
| 3 | `src/web/components/data_source/data_source.py:9` | `SimulatorRegistry` | `ApplicationAPI` |

```
CORRECT layer flow:
  +----------+      +-----------+      +-----------+
  | Web (C)  | ---> | Core (B)  | ---> | Parsing(A)|
  +----------+      +-----------+      +-----------+

VIOLATION (current):
  +----------+                         +-----------+
  | Web (C)  | ----------------------> | Parsing(A)|
  +----------+      (skips Core)       +-----------+
```

### Direct session_state Accesses (13 violations)

- **Problem**: 13 `st.session_state[]` accesses bypass `UIStateManager`
- **Source**: Track 7.4 in `.agent/thorough-review/`
- **Detection command**:
  ```bash
  grep -rn "st\.session_state\[" src/web/ --include="*.py" | grep -v __pycache__
  ```
- **Fix**: Route all access through `UIStateManager.get()` / `UIStateManager.set()`

### Boundary Validation Commands

```bash
# Must ALL return empty:
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__
```

---

## Dead Code (~950 lines)

| Location | Lines | Description |
|----------|-------|-------------|
| `src/core/common/utils.py` | ~200 | 12 of 13 functions dead (only `checkFileExistsOrException` alive) |
| `src/web/presenters/plot/chart_presenter.py` | ~240 | Entire file -- duplicate of `chart_display.py` |
| `src/web/pages/ui/components/shapers/split_apply_config.py` | ~361 | Byte-for-byte duplicate of another file |
| `tests/unit/test_utils.py` | ~150 | Tests only dead utility functions |

- **Total**: ~950 lines safe to remove
- **Detection**: Cross-reference with `grep -rn "from src.core.common.utils import"` to verify usage

---

## Pandas Anti-Patterns

### Redundant DataFrame Wrappers (26 instances across 12 files)

```python
# ANTI-PATTERN (found 26 times):
result = pd.DataFrame(df[df["col"] > 0])  # boolean indexing already returns DataFrame

# CORRECT:
result = df[df["col"] > 0]
```

- **Detection**:
  ```bash
  grep -rn "pd\.DataFrame(df\[" src/ --include="*.py" | grep -v __pycache__
  ```

### Enforced Patterns (no violations found)

| Pattern | Status | Enforcement |
|---------|--------|-------------|
| No `inplace=True` | Clean | Pre-commit hook `no-inplace-true` |
| Immutable transforms | Clean | Code review + hook |
| `pd.Categorical(ordered=True)` | Correct | Used in `transformer.py` |
| All 10 shapers use `__call__(df) -> df` | Correct | Compatible with `.pipe()` |

---

## Python 3.12+ Modernization Gaps

| Gap | Count | Where |
|-----|-------|-------|
| Missing `@override` decorators | 30+ | `BasePlot`, `Shaper`, `StatType` subclasses |
| `if/elif` chains convertible to `match/case` | 2-3 | `condition_selector`, factory modules |
| Plain string registry keys (should be `StrEnum`) | 12 | Shaper factory (10), strategy factory (2) |

---

## Test Coverage Gaps

| Module | Tests | Issue |
|--------|-------|-------|
| `src/core/performance.py` (SimpleCache, @cached) | **0 unit tests** | No validation of cache behavior |
| Private attribute accesses in tests | 370+ `_internal` accesses | Fragile to refactoring |
| `time.sleep()` in tests | 13 calls | CI flakiness risk |
| Estimated new tests needed | ~58 | For adequate coverage |

---

## Trunk Lint Baseline

| Issue Type | Count | Location |
|------------|-------|----------|
| pyright "possibly unbound" | 3 | `pivot_config.py:256-258` (`selection_filters`, `strategy`, `merge_label`) |
| isort violations | 4 | 2 source files, 2 test files |
| Markdown formatting | ~111 | Auto-fixable with `trunk fmt` |
