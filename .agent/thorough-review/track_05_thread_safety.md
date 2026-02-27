# Track 05: Thread Safety & Concurrency

> **Priority**: CRITICAL
> **Status**: PENDING
> **Estimated items**: 8
> **Scope**: All concurrent code — pools, caches, singletons, health monitors

---

## What to Look At

### 5.1 SimpleCache is NOT thread-safe despite claiming so — CRITICAL

**File**: `src/core/common/performance.py`, lines 20-84
**What**: `SimpleCache` class uses a plain `dict` for storage with no synchronization (no `threading.Lock`). Multiple threads (from ThreadPoolExecutor workers) can read/write the cache simultaneously, leading to:
- Lost writes (two threads compute same key, one overwrites the other)
- Corrupted dict state during resize (CPython implementation detail, though GIL helps somewhat)
- Stale reads during eviction
**Dependencies**: Used by `mean.py` and `normalize.py` shaper caching. If cache returns stale/corrupted data, shaper output is wrong.

### 5.2 CsvPoolService module-level mutable caches without locks — HIGH

**File**: `src/core/services/csv_pool_service.py`
**What**: Module-level `dict` caches (`_csv_cache`, `_header_cache`, or similar) are accessed without synchronization. In Streamlit's threaded execution model, concurrent requests can corrupt these caches.
**Dependencies**: CSV data integrity. Corrupted cache → wrong data displayed.

### 5.3 PerlWorkerPool is_busy TOCTOU race — HIGH

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 467-487
**What**: `is_busy` is set/read without lock. While GIL provides atomic bool assignment, there's a TOCTOU (Time-of-Check-Time-of-Use) window: health monitor checks `is_busy=False`, but between check and ping, parse starts and sets `is_busy=True`. Health monitor then pings a busy worker.
**Note**: This was documented in commit 362106e as acceptable. Re-evaluate if it can cause actual data corruption.
**Dependencies**: Worker pool reliability.

### 5.4 WorkPool executors not shut down on hot-reload — HIGH

**File**: `src/parsing/gem5/impl/pool/work_pool.py`
**What**: `ScanWorkPool` and `ParseWorkPool` use `ThreadPoolExecutor`. On Streamlit hot-reload, old executor threads may still be running while new ones are created, leading to resource exhaustion.
**Dependencies**: Application stability during development.

### 5.5 Previously skipped H5: Singleton re-init on hot-reload

**File**: `src/parsing/gem5/impl/pool/work_pool.py`, line 43
**What**: Singleton pool instances fail to reinitialize after Streamlit hot-reload clears `@st.cache_resource`. The `get_instance()` method returns a stale reference.
**Fix approach**: Add `_is_alive()` check in singleton accessor. If executor is shut down, create new instance.
**Dependencies**: Application reliability during development. Not a production issue.

### 5.6 Previously skipped H1: Queue starvation on all-worker fail

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 460-485
**What**: If all workers fail simultaneously, the worker queue is empty. Current behavior: timeout loop retries, eventually raises `RuntimeError`. Recovery is slow (tens of seconds).
**Fix approach**: Circuit-breaker pattern — after N consecutive failures within T seconds, fail fast.
**Dependencies**: Parse reliability. Currently functional but slow to fail.

### 5.7 ScanWorkPool/ParseWorkPool non-atomic singleton access

**File**: `src/parsing/gem5/impl/pool/work_pool.py`
**What**: Singleton pattern uses class-level `_instance` attribute. In theory, two threads could both see `_instance is None` and create duplicate instances. In practice, `@st.cache_resource` prevents this, but the raw singleton is unprotected.
**Dependencies**: Correctness of singleton guarantee.

### 5.8 Health monitor `_shutdown` flag without memory barrier

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 404-411
**What**: `_shutdown` flag is a plain bool set in main thread, read in health monitor thread. While CPython's GIL makes this work, it's technically not guaranteed by the Python memory model. `threading.Event` is the correct primitive.
**Dependencies**: Clean shutdown semantics.

---

## How to Investigate

1. **For 5.1**: Read `SimpleCache.__init__`, `get()`, `set()`, `_evict()`. Verify there's no lock. Check all callers (grep for `SimpleCache`). Determine if concurrent access is possible in practice.
2. **For 5.2**: Read `csv_pool_service.py`. Find all module-level dicts. Trace read/write access patterns. Determine if Streamlit's threaded model can trigger concurrent access.
3. **For 5.3**: Re-read the is_busy documentation added in 362106e. Trace the exact sequence: (a) health monitor reads is_busy=False, (b) parse starts, sets is_busy=True, (c) health monitor sends ping. Determine if ping during parse corrupts data or just causes a timeout.
4. **For 5.4**: Read work_pool.py singleton pattern. Check if `@st.cache_resource` has a `__del__` or cleanup hook. Evaluate adding explicit `shutdown()` on reinit.
5. **For 5.5-5.6**: Read the current code. Design minimal fixes (alive check for 5.5, circuit breaker for 5.6).
6. **For 5.7**: Check if `@st.cache_resource` is the ONLY entry point or if direct `_instance` access exists.
7. **After fixes**: Create mock-based concurrency tests to verify thread safety.

---

## What We Expect to Find

- **5.1**: SimpleCache IS used from concurrent threads via shaper pipeline. Adding `threading.Lock` is necessary. May also consider `functools.lru_cache` with thread-safe wrapper as simpler alternative.
- **5.2**: CsvPoolService caches ARE accessed from multiple Streamlit requests. Need synchronization.
- **5.3**: The TOCTOU window is harmless — ping during parse just times out and worker is restarted. No data corruption. Document this conclusively.
- **5.4**: `@st.cache_resource` handles cleanup via replacement, but old executor threads may linger. Add `atexit` handler or explicit shutdown.
- **5.5-5.6**: Both are edge cases with simple fixes. Low risk of regression.

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 5.1 SimpleCache thread safety | PENDING | | |
| 5.2 CsvPoolService caches | PENDING | | |
| 5.3 is_busy TOCTOU | PENDING | | |
| 5.4 Executor hot-reload | PENDING | | |
| 5.5 Singleton re-init | PENDING | | |
| 5.6 Circuit breaker | PENDING | | |
| 5.7 Non-atomic singleton | PENDING | | |
| 5.8 Shutdown flag | PENDING | | |
