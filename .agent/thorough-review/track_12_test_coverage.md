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

**Status**: PENDING

| Item | Result | Tests Added | Notes |
| --- | --- | --- | --- |
| 12.1 Zero-coverage files | PENDING | | |
| 12.2 Indirect-only coverage | PENDING | | |
| 12.3 Private attribute tests | PENDING | | |
| 12.4 Flaky timing tests | PENDING | | |
| 12.5 Shaper edge cases | PENDING | | |
| 12.6 Stat type edge cases | PENDING | | |
| 12.7 Concurrency tests | PENDING | | |
| 12.8 E2E integration | PENDING | | |
| 12.9 Fixture consolidation | PENDING | | |
| 12.10 Binary file test | PENDING | | |
