# Track 2: Perl Worker Pool Health & Throughput

**Status**: DONE
**Priority**: P3
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_02_perl_worker_pool.md`

---

## Goal

Verify the Perl worker pool processes are healthy and responsive.

## Files Analyzed

- `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- `src/parsing/gem5/impl/pool/pool.py`

---

## Findings

### 1. CRITICAL — `is_busy` Flag Race Condition

**Location**: `perl_worker_pool.py:420, 463, 465, 479`

The `is_busy` flag is written **without lock protection** in `parse_file()` (lines 463, 465, 479) but read **under lock** in `_check_worker_health()` (line 420). This is a classic memory visibility race:

- Thread A acquires worker, sets `is_busy = True` (no lock)
- Thread B (health monitor) acquires `_lock`, reads `is_busy` — may see stale `False`
- Thread B proceeds to call `worker.health_check()` on an actively-used worker
- This can cause lock contention on `worker._lock` and potentially corrupt state

**Severity**: CRITICAL

### 2. HIGH — Queue Starvation When Workers Fail

**Location**: `perl_worker_pool.py:460-485`

When `worker.parse_file()` returns `success=False`:
- Worker is marked `is_healthy=False` (line 484)
- Worker is NOT returned to queue (line 485)
- Health monitor runs asynchronously every 30s (line 407)
- If all 4 workers fail in quick succession, queue empties
- Next `parse_file()` call blocks for up to 120s waiting on `queue.get(timeout=120)`

**Impact**: Under high failure rates, complete pool starvation for 30+ seconds until health monitor restarts workers.

**Severity**: HIGH

### 3. HIGH — `was_healthy` Logic Is Semantically Wrong

**Location**: `perl_worker_pool.py:425-436`

```python
was_healthy = worker.is_healthy  # Gets False (already set by health_check)
if not was_healthy:              # ALWAYS True after failed check
    self.worker_queue.put(worker)
```

`health_check()` sets `is_healthy=False` before returning False, so `was_healthy` is always False after a failed check. The condition `if not was_healthy:` is always True — the code works by accident but is unmaintainable.

**Severity**: HIGH (correctness/maintenance hazard)

### 4. MEDIUM — Busy Workers Excluded from Health Checks

**Location**: `perl_worker_pool.py:420-421`

Health checks explicitly skip workers with `is_busy=True`. If a worker deadlocks during parsing, the health monitor cannot detect it for up to 120s (parse timeout). Only after the parse timeout expires is the worker checked.

**Severity**: MEDIUM (design limitation)

### 5. MEDIUM — Nested/Overlapping Timeout Mechanisms

**Location**: `perl_worker_pool.py:460, 195, 187-193`

Three timeout layers: queue acquisition (120s), per-read timeout (30s), overall parse timeout (120s). The `queue.get(timeout=120)` uses the parse timeout, not a dedicated queue-wait timeout, causing callers to wait 120s even for brief worker unavailability.

**Severity**: MEDIUM

### 6. LOW — No Queue Bounds / Duplicate Worker Safeguard

**Location**: `perl_worker_pool.py:351, 436, 482`

Queue is unbounded (`queue.Queue()`). While unlikely, there is no safeguard against the same worker appearing in the queue twice after concurrent health-check restart + parse completion.

**Severity**: LOW

### 7. INFO — Future Leak Prevention (FIXED)

**Location**: `pool.py:74, 164`

`_futures.clear()` at the start of `submit_batch_async()` prevents unbounded memory growth. Validated by `test_pool_future_leak.py`.

### 8. INFO — Startup Timeout Increased (FIXED)

**Location**: `perl_worker_pool.py:87`

Startup timeout increased from 5s to 30s to handle slow container/host environments.

---

## Severity Summary

| Issue | Severity | Status |
|-------|----------|--------|
| `is_busy` flag race condition | CRITICAL | UNFIXED |
| Queue starvation on worker failures | HIGH | UNFIXED |
| `was_healthy` logic semantically wrong | HIGH | UNFIXED |
| Busy workers excluded from health checks | MEDIUM | BY DESIGN |
| Nested timeout confusion | MEDIUM | BY DESIGN |
| No queue bounds/duplicate safeguards | LOW | LOW RISK |
| Future leak fixed | INFO | FIXED |
| Startup timeout increased | INFO | FIXED |

## Conclusions

The Perl worker pool has **1 CRITICAL and 2 HIGH** severity issues. The `is_busy` race condition could cause health checks to interfere with active parsing. Queue starvation under worker failures could freeze parsing for 30+ seconds. The `was_healthy` logic works by accident. These collectively explain potential intermittent slowdowns and hangs during parsing.

## Recommendations

1. Add lock protection for `is_busy` flag reads/writes
2. Implement immediate worker replacement on failure (not async 30s delay)
3. Capture `was_healthy` BEFORE `health_check()` mutates state
4. Add queue depth monitoring and alerting
