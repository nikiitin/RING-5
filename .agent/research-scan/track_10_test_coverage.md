# Track 10: Existing Test Coverage Audit

**Status**: DONE
**Priority**: P9
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_10_test_coverage.md`

---

## Goal

Identify which paths are tested and which are untested gaps.

## Scope

Audited all test files under `tests/unit/` and `tests/integration/`.
**Total**: ~260 test files, ~3,559 test cases.

---

## Existing Test Coverage

### Core Parsing Tests

| Test File | Coverage |
|-----------|----------|
| `test_perl_worker_pool.py` | PerlWorker startup, health checks, parse_file, pool recovery, shutdown |
| `test_pool_future_leak.py` | Future cleanup between batches, cancel_all(), empty batch |
| `test_scanner_comprehensive.py` | Scanner init, scan_file, singleton pattern |
| `test_scanning.py` | ScanWorkPool singleton, async flow, batch submission |
| `test_async_fail.py` | Async scan flow, cancellation, multiple batch independence |
| `test_parser_strategies.py` | SimpleStatsStrategy, ConfigAwareStrategy |
| `test_parse_batch_result.py` | ParseBatchResult immutability, futures + var_names |

### Pattern Aggregation Tests

| Test File | Coverage |
|-----------|----------|
| `test_pattern_aggregator.py` (102 tests) | Single/multi-numeric, vector/distribution/histogram, 16-CPU aggregate, mixed widths, complex multi-index |
| `test_pattern_aggregation_integration.py` | CPU/controller patterns, non-pattern preservation |

### Pivot/Shaping Tests

| Test File | Coverage |
|-----------|----------|
| `test_pivot_selective.py` | Pivot longer: discard, merge, multi-group extraction |
| `test_shapers_extended.py` | Various shaper implementations |
| Multiple plot-specific tests | Normalize, split_apply, sorting |

### Full Pipeline Tests

| Test File | Coverage |
|-----------|----------|
| `test_full_parser_workflow.py` | Scan → Select → Parse → CSV → Load (facade integration) |
| `test_worker_pool_integration.py` | Gem5ParseWork using worker pool |
| `test_statistics_only_integration.py` | Distribution stats-only mode vs full mode |
| `test_gem5_parsing.py` | Real gem5 data with `limit=-1` (deep scan) |
| `test_histogram_with_stats.py` | Full histogram workflow with deep scans |
| `test_real_gem5_data.py` | Real benchmarks (mcf, omnetpp, xalancbmk) |

### Performance Tests

| Test File | Coverage |
|-----------|----------|
| `test_worker_pool_performance.py` | Worker pool vs subprocess (20 files) |
| `test_performance_regression.py` | Plot speed thresholds (<500ms/<800ms), shaper perf |

---

## CRITICAL GAPS

### Gap 1: No Concurrent Thread Access Tests for PerlWorkerPool

**What's missing**: Tests with multiple threads calling `parse_file()` simultaneously. Race conditions on `is_busy`, queue starvation under concurrent load, worker crash during concurrent requests.

**Why it matters**: Track 2 found a CRITICAL `is_busy` race condition. No tests verify thread-safety.

**Severity**: CRITICAL

### Gap 2: No Thread-Safety Verification Tests

**What's missing**: Tests proving data isolation under concurrent access. No test demonstrates that concurrent parse batches produce correct, non-corrupted results.

**Why it matters**: Thread migration (Process→Thread) changed concurrency model. Silent data corruption is the worst possible bug.

**Severity**: CRITICAL

### Gap 3: No Large-Scale `construct_final_csv()` Tests

**What's missing**: Tests with 1000+ files, 100+ variables. No sparse data tests (different variable subsets per file). No tests for distribution variables with large ranges.

**Why it matters**: Track 4 found O(F×V×D×R) complexity that can reach billions of operations.

**Severity**: HIGH

### Gap 4: No PivotLonger Performance Regression Tests

**What's missing**: Tests with 10K+ rows, 100+ value_vars. No memory usage tests during pivot operations.

**Why it matters**: Track 5 found non-vectorizable `apply()` with regex that scales O(rows × vars).

**Severity**: MEDIUM

### Gap 5: No Deep Scan Scaling Tests (100+ files)

**What's missing**: Explicit test with 100+ files and `limit=0`. No scan time baseline. No memory growth verification.

**Why it matters**: Track 8 found `limit=0` can be catastrophic at scale.

**Severity**: MEDIUM

### Gap 6: No PatternAggregator Scale Tests

**What's missing**: Tests with 1000+ variables, 1000+ CPU instances. No performance scaling verification.

**Why it matters**: Track 8 confirmed O(n log n) theoretically, but no empirical validation at scale.

**Severity**: MEDIUM

---

## Positive Findings

- **Test suite is comprehensive in breadth** — most feature paths are covered
- **Real data coverage is good** — integration tests use actual gem5 files
- **Pattern aggregation is well-tested** — 102 test cases in `test_pattern_aggregator.py`
- **CSV pool service is well-tested** — LRU eviction, cache clearing, listing
- **Future leak regression is covered** — dedicated `test_pool_future_leak.py`

---

## Recommended New Tests (Prioritized)

### CRITICAL Priority

1. **`tests/unit/test_concurrent_thread_safety.py`** (~60 tests)
   - Concurrent `parse_file()` calls
   - Worker pool under thread contention
   - Data isolation between concurrent batches

2. **`tests/unit/test_construct_final_csv_large.py`** (~30 tests)
   - 1000+ files × 100+ variables
   - Memory efficiency measurement
   - Sparse data with mixed variable sets

### HIGH Priority

3. **`tests/unit/test_pivot_performance.py`** (~15 tests)
   - Large DataFrame pivots (10K+ rows)
   - Memory usage during pipeline

4. **`tests/unit/test_deep_scan_scaling.py`** (~20 tests)
   - 100+ file scans with `limit=0`
   - Error recovery when one file fails

### MEDIUM Priority

5. **`tests/unit/test_pattern_aggregator_scale.py`** (~15 tests)
   - 1000+ variables, scaling verification

6. **`tests/integration/test_strategy_end_to_end.py`** (~25 tests)
   - Full strategy execution with real data

## Conclusions

The test suite is **strong in breadth but weak in concurrency and scale testing**. The CRITICAL gaps are:
1. No thread-safety tests despite thread migration
2. No concurrent access tests for the PerlWorkerPool
3. No large-scale CSV construction tests

These gaps directly align with the CRITICAL issues found in Tracks 2, 4, and 7.
