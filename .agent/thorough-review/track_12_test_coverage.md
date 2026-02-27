# Track 12: Test Coverage Expansion

> **Priority**: HIGH
> **Status**: PENDING
> **Estimated items**: 10
> **Scope**: `tests/` — gaps, quality, fixtures, edge cases

---

## What to Look At

### 12.1 Zero-coverage files (5 files) — HIGH

| File | Lines | Why Untested |
| --- | --- | --- |
| `src/core/common/performance.py` | ~84 | SimpleCache class, no tests |
| `src/web/rendering/config_builder.py` | ~200 | Config assembly, complex |
| `src/web/components/plotting/interactive_plot.py` | ~100 | Interactive Plotly events |
| `src/web/rendering/matplotlib_connector.py` | ~400 | Matplotlib rendering |
| `src/web/controllers/plot/plot_protocols.py` | ~50 | Protocol definitions |

### 12.2 Indirect-only coverage (5 files)

| File | Covered By | Gap |
| --- | --- | --- |
| `src/web/components/common/filtered_selector.py` | UI tests | No unit tests |
| `src/web/components/common/reorderable_list.py` | UI tests | No unit tests |
| `src/web/rendering/plotly_connector.py` | Integration | No unit tests |
| `src/web/components/common/pipeline.py` | Integration | No unit tests |
| `src/web/components/common/chart_display.py` | Integration | No unit tests |

### 12.3 Brittle private-attribute tests (5+ files)

**Files**:
- `tests/unit/test_configuration_type.py`, lines 30-205 — accesses `._repeat`, `._content`
- `tests/unit/test_matplotlib_trace_renderer.py`, line 86 — accesses `._ring5_twin`
- `tests/unit/test_repository_state_manager.py`, line 40 — accesses `._session_repo`

**What**: Accessing private attributes makes tests break on refactoring. Should use public API or add public accessors.

### 12.4 Flaky time-dependent tests (8 files)

**Files**: Tests using `time.sleep()` for synchronization instead of events/conditions.
**What**: These tests are inherently timing-dependent. On slow CI machines, they may fail intermittently.

### 12.5 Missing edge case tests for shapers

**Missing scenarios**:
- Pipeline with 10+ sequential shapers
- Shaper receiving empty DataFrame
- NaN/infinity values in shaper pipeline
- Type mismatches between shaper output/input
- Condition selector with all rows filtered out

### 12.6 Missing edge case tests for stat types

**Missing scenarios**:
- Scalar with NaN values
- Vector with zero entries
- Distribution with single bucket
- Histogram with negative values
- Configuration with unicode characters

### 12.7 Previously skipped C9: Concurrent thread-safety tests

**What**: No tests for PerlWorkerPool under concurrent load. Create mock-based tests:
```python
def test_concurrent_parse_requests():
    pool = PerlWorkerPool(num_workers=3)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(pool.parse_file, f) for f in test_files]
        # Verify no data corruption
```

### 12.8 E2E integration test: Parse -> Load -> Transform -> Plot

**What**: No end-to-end test covering the full pipeline from parsing through plotting.
**Action**: Create `tests/integration/test_full_pipeline_e2e.py`.

### 12.9 Consolidate fixture duplication

**What**: `mock_state_manager`, `sample_data`, `mock_session_state` defined differently in 3+ conftest files.
**Action**: Create `tests/fixtures/` package with shared fixtures.

### 12.10 Missing binary file rejection test

**What**: Scanner/parser should reject binary files (images, compiled objects). No test verifies this.

---

## How to Investigate

1. **For 12.1**: Create test files for each zero-coverage module. Start with SimpleCache (CRITICAL thread safety) and config_builder (HIGH usage).
2. **For 12.2**: Create focused unit tests that test public API without UI.
3. **For 12.3**: For each private access, determine if a public accessor exists or should be added. Refactor test to use public API.
4. **For 12.4**: Identify all `time.sleep()` in tests. Replace with `threading.Event` or `unittest.mock.patch` for deterministic behavior.
5. **For 12.5-12.6**: Create test files with parameterized test cases for each edge scenario.
6. **For 12.7**: Design mock-based tests that simulate concurrent access without requiring live Perl.
7. **For 12.8**: Create a minimal end-to-end test with small fixture data.
8. **For 12.9**: Audit all conftest.py files. Extract common fixtures.
9. **For 12.10**: Create test that passes a binary file to scanner.

---

## What We Expect to Find

- **12.1**: SimpleCache tests will expose the thread-safety bug (Track 05, 5.1). Config builder tests will catch type errors.
- **12.3**: Most private accesses can be replaced with public API assertions.
- **12.5-12.6**: Edge cases will expose 2-3 unhandled scenarios (empty DataFrame, NaN propagation).
- **12.7**: Concurrent tests will exercise the is_busy flag race condition and verify it's harmless.
- **12.9**: ~10 duplicate fixture definitions across 5+ conftest files.

---

## Outcome

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 12.1 Zero-coverage files | **PARTIALLY CONFIRMED** — performance.py has ZERO dedicated unit tests (only indirect clear_all_caches call). config_builder.py has integration tests but no unit suite. interactive_plot.py and matplotlib_connector.py DO have test files (hypothesis wrong). | HIGH | Add SimpleCache unit test suite (10+ tests). Add config builder unit tests (15+ tests). |
| 12.2 Indirect-only coverage | **CONFIRMED** — reorderable_list and filtered_selector tested only through E2E/UI-logic tests. pipeline.py has strong coverage (70 methods). plotly_connector has integration tests only. | MEDIUM | Add dedicated unit tests for reorderable_list and filtered_selector (8+ tests). |
| 12.3 Private attribute tests | **CONFIRMED CRITICAL** — 370+ private attribute accesses across test suite. test_configuration_type.py: 30+ accesses (._repeat, ._content, ._on_empty, ._balanced, ._reduced). test_matplotlib_trace_renderer.py:86 uses `cast(Any, ax)._ring5_twin`. | HIGH | Refactor 10-15 test files to use public APIs. Add public accessors where needed. Target <50 private accesses. |
| 12.4 Flaky timing tests | **CONFIRMED** — 13 `time.sleep()` calls across tests. 2 use 1.1s for file timestamp granularity. 5 benchmark tests rely on sleep-based timing. Risk of CI flakiness on slow machines. | MEDIUM-HIGH | Replace sleep-based waits with threading.Event or unittest.mock.patch for deterministic behavior. |
| 12.5 Shaper edge cases | **PARTIALLY COVERED** — 66 shaper test methods exist. Empty pipeline, None/null fields, NaN/inf, type mismatches ARE tested. Missing: binary/malformed CSV, unicode column names, large datasets, numeric precision loss. | MEDIUM | Add 5+ tests for data format robustness and encoding edge cases. |
| 12.6 Stat type edge cases | **NEEDS INVESTIGATION** — Skipped due to scope overlap with 12.3. Primary gap is testing through public API rather than private attributes. | MEDIUM | Combine with 12.3 refactoring — test stat types through public reduce/balance_content. |
| 12.7 Concurrency tests | **CONFIRMED GAP** — No concurrent access tests for PerlWorkerPool. test_perl_worker_pool.py exists but tests sequential access only. | MEDIUM | Add mock-based concurrent parse tests with ThreadPoolExecutor. |
| 12.8 E2E integration | **CONFIRMED GAP** — No parse→load→transform→plot integration test. integration/ tests exist for individual components but not the full pipeline. | MEDIUM | Create test_full_pipeline_e2e.py with small fixture data. |
| 12.9 Fixture consolidation | **PARTIALLY CONFIRMED** — No true duplicates, but naming inconsistency: root `mock_state_manager` vs integration `state_manager` (mock vs real). `sample_data` (6 rows) vs `rich_sample_data` (9 rows) with different schemas. | LOW | Document fixtures. Create shared data fixture library. Standardize naming. |
| 12.10 Binary file test | **CONFIRMED GAP** — Zero tests for binary (.bin, .pkl, .dat) file rejection. No encoding error tests. No permission denied tests. No corrupted file handling tests. | MEDIUM | Add 6+ parser robustness tests for malformed/binary input. |

### Quantified Coverage Summary
- **~58 new tests needed** across all gaps
- **370→<50 private attribute accesses** to refactor (10-15 files)
- **13 time.sleep() calls** to replace with deterministic synchronization
- **2 modules** (performance.py, config_builder.py) need dedicated test suites

### Critical Findings Summary (items requiring fix)
1. **370+ private attribute accesses in tests** — HIGH: Massive refactoring fragility
2. **SimpleCache has 0 unit tests** — HIGH: Thread-unsafe code (Track 05) completely untested
3. **13 flaky timing tests** — MEDIUM-HIGH: CI reliability risk
