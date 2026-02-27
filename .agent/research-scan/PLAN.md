# Comprehensive Diagnostic Analysis Plan — Deep Scan / Parsing Performance

## Context

The deep scan / parsing performance issue persists after applying:

1. **Memory leak fix** — `_futures.clear()` in `ScanWorkPool` / `ParseWorkPool` singletons
2. **Executor switch** — `ProcessPoolExecutor` → `ThreadPoolExecutor` (~1.9 GB savings)
3. **Thread-safety fix** — `copy.deepcopy(template_map)` per work item in `SimpleStatsStrategy`

None of these resolved the actual problem. This plan exhaustively covers every possible root cause across all three layers.

---

## Investigation Tracks — ALL COMPLETE

| Track | Title                                  | Status   | Severity Found         | Research File |
|-------|----------------------------------------|----------|------------------------|---------------|
| 1     | Profile the Actual Bottleneck          | **DONE** | Parsing = 5.9s (main)  | [track_01_profiling.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_01_profiling.md) |
| 2     | Perl Worker Pool Health & Throughput   | **DONE** | 1 CRITICAL, 2 HIGH     | [track_02_perl_worker_pool.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_02_perl_worker_pool.md) |
| 3     | deepcopy Performance Impact            | **DONE** | NONE (0.04s, negligible)| [track_03_deepcopy.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_03_deepcopy.md) |
| 4     | CSV Construction Bottleneck            | **DONE** | CRITICAL at scale (latent) | [track_04_csv_construction.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_04_csv_construction.md) |
| 5     | Shaper Pipeline — PivotLonger Perf     | **DONE** | 2 CRITICAL, 2 HIGH (latent) | [track_05_pivot_longer.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_05_pivot_longer.md) |
| 6     | Streamlit Rendering & Cache Behavior   | **DONE** | 1 CRITICAL (scan UI freeze) | [track_06_streamlit_rendering.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_06_streamlit_rendering.md) |
| 7     | Data Volume & File Discovery           | **DONE** | 4 CRITICAL (multiplication) | [track_07_data_volume.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_07_data_volume.md) |
| 8     | Scanning Performance (Deep Scan)       | **DONE** | GREEN (1 YELLOW)        | [track_08_scanning.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_08_scanning.md) |
| 9     | Thread-Safety Correctness Check        | **DONE** | 1 HIGH (hot-reload)     | [track_09_thread_safety.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_09_thread_safety.md) |
| 10    | Existing Test Coverage Audit           | **DONE** | 2 CRITICAL gaps          | [track_10_test_coverage.md](/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_10_test_coverage.md) |

---

## Cross-Track Findings Summary

### CRITICAL Issues (Must Fix)

| # | Issue | Track | Location |
|---|-------|-------|----------|
| C1 | `is_busy` flag race condition in PerlWorkerPool | Track 2 | `perl_worker_pool.py:420,463,465,479` |
| C2 | Sequential `f.result()` freezes scan UI | Track 6 | `data_source_components.py:204` |
| C3 | `rglob()` scans entire tree even with `limit=5` | Track 7 | `gem5_scanner.py:52-56`, `simple.py:128-141` |
| C4 | Regex config multiplication (1→N explosion) | Track 7 | `gem5_parser.py:113-177` |
| C5 | Repeat count compounding (CPU×Thread×Controller) | Track 7 | `simple.py:160-166` |
| C6 | Variable aliasing shares mutable object state | Track 7 | `simple.py:172-174` |
| C7 | Distribution reduce with unbounded range O(D×R) | Track 4 | `distribution.py:225-238` |
| C8 | DataFrame copy compounds through pipeline (6x) | Track 5 | `pivot.py:82,202`, `pipeline_service.py:149` |
| C9 | No concurrent thread-safety tests | Track 10 | (gap) |

### HIGH Issues (Should Fix)

| # | Issue | Track | Location |
|---|-------|-------|----------|
| H1 | Queue starvation when all workers fail | Track 2 | `perl_worker_pool.py:460-485` |
| H2 | `was_healthy` logic semantically wrong | Track 2 | `perl_worker_pool.py:425-436` |
| H3 | `apply()` with regex not vectorizable | Track 5 | `pivot.py:150,167-169` |
| H4 | PivotWider missing `aggfunc` (crash risk) | Track 5 | `pivot.py:218-226` |
| H5 | Singleton re-init fails on Streamlit hot-reload | Track 9 | `work_pool.py:43`, `perl_worker_pool.py:522` |
| H6 | Histogram rebinning O(B²×R) | Track 4 | `histogram.py:204-306` |

### GREEN / CONFIRMED SAFE

| Item | Track | Notes |
|------|-------|-------|
| deepcopy performance | Track 3 | 0.04s for 586 copies — negligible |
| Thread data isolation | Track 9 | deepcopy + future blocking = safe |
| Worker return guarantee | Track 9 | finally block ensures no permanent leak |
| PatternAggregator | Track 8 | O(n log n), no cartesian product |
| ScanWorkPool chunking | Track 8 | Correct, memory leak fixed |
| Session state management | Track 6 | No bloat, good architecture |

---

## Root Cause Analysis

**Primary bottleneck**: Parsing 586 files takes 5.9s (Track 1). This is dominated by:
1. Perl subprocess overhead per file × per variable (Track 7, Track 8)
2. Data volume multiplication through 5 pipeline stages (Track 7)
3. Potential UI freeze during scan from sequential future resolution (Track 6)

**Secondary risks** (latent, trigger at scale):
1. CSV construction explodes with wide distributions (Track 4)
2. Shaper pipeline compounds memory with each transformation (Track 5)
3. Singleton stale state after Streamlit hot-reload (Track 9)

**Not the cause**:
- deepcopy (~0.04s)
- PivotLonger (~0.002s at current scale)
- CSV writing (~0.005s)
- PatternAggregator (efficient)
- Session state (well-managed)

---

## Fixes Already Applied (Pre-Investigation)

| Fix | Description | Impact |
|-----|-------------|--------|
| Memory leak | `_futures.clear()` in pool singletons | Prevented unbounded future accumulation |
| Executor switch | `ProcessPoolExecutor` → `ThreadPoolExecutor` | ~1.9 GB memory savings, no speed change |
| Thread-safety | `copy.deepcopy(template_map)` per work item | Prevented data corruption in threaded parsing |

---

## Key Questions for the User

1. **What exactly is the symptom?** Slow UI? Slow scan? Slow parse? Wrong data? Application freeze?
2. **What is the scale?** How many `stats.txt` files? How large are they? How many variables are selected?
3. **Is this a "deep scan" (limit=0) or a regular scan (limit=5)?**
4. **Does the issue reproduce on fresh Streamlit restart, or only after extended use?**
