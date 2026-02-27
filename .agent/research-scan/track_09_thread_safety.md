# Track 9: Thread-Safety Correctness Check

**Status**: DONE
**Priority**: P7
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_09_thread_safety.md`

---

## Goal

Verify no data corruption from the thread migration (ProcessPoolExecutor → ThreadPoolExecutor).

## Files Analyzed

- `src/parsing/gem5/impl/strategies/simple.py`
- `src/parsing/gem5/impl/strategies/perl_worker_pool.py`
- `src/parsing/gem5/impl/strategies/gem5_parse_work.py`
- `src/parsing/gem5/impl/pool/work_pool.py`
- `src/parsing/gem5/impl/pool/pool.py`

---

## Findings

### 1. SAFE — Shared State in `Gem5ParseWork._entry_buffer`

**Location**: `gem5_parse_work.py:52`

Each `Gem5ParseWork` instance has its own `_entryBuffer: EntryBufferType = {}`. The deepcopy at `simple.py:116` ensures full isolation. Buffer is also reset to `{}` at line 262 in `_processOutput()` before each parse.

**Verified**: No shared references between work items.

**Severity**: NONE

### 2. SAFE — Worker Return Guarantee in PerlWorkerPool

**Location**: `perl_worker_pool.py:457-493`

The `finally` block (lines 477-485) guarantees workers are either:
- Returned to queue if `is_healthy` (line 482)
- Left for health monitor if unhealthy (line 484)

Even if `worker.parse_file()` raises an exception, the finally block executes. Pool cannot permanently leak workers.

**Severity**: NONE

### 3. SAFE — StatType Mutation After All Threads Complete

**Location**: `simple.py:72`, `gem5_parser.py:285-311`

```python
results = [f.result() for f in futures]     # Line 72: BLOCKS until all complete
# ... later in construct_final_csv():
for file_stats in results:
    var.balance_content()                   # Line 296: After all threads done
    var.reduce_duplicates()                 # Line 297: After all threads done
```

The list comprehension at line 72 blocks until ALL futures resolve. Mutations in CSV construction happen strictly after all parsing threads have completed. No concurrent mutation risk.

**Severity**: NONE

### 4. HIGH — Singleton Re-Initialization Fails on Streamlit Hot-Reload

**Location**: `work_pool.py:43-56`, `pool.py:131`, `perl_worker_pool.py:522-551`

**WorkPool**: `if self._initialized: return` (line 43) — skips re-initialization after hot-reload. Old executors persist.

**ParseWorkPool**: `if cls._instance is None:` (line 131) — returns stale instance with dead executor.

**PerlWorkerPool**: Module-level global `_worker_pool_instance` persists across Streamlit reruns, keeping old Perl worker processes alive.

**Risk scenario**:
1. User parses → Perl workers start (PID 1234-1237)
2. Streamlit hot-reload → singletons persist with stale processes
3. Old Perl processes may be zombies
4. Memory leak: 4 old + 4 new = 8 processes

**Severity**: HIGH (resource leak and zombie processes on hot-reload)

### 5. SAFE — deepcopy Correctly Isolates All State

**Location**: `simple.py:116`

`copy.deepcopy(template_map)` performs recursive copy. All `StatType` attributes use `object.__setattr__()` (base.py:74-79), are primitives or containers. No external references (file handles, sockets). Fully isolated.

**No reference leaks detected.**

**Severity**: NONE

### 6. SAFE (with caveat) — Future.result() Ordering Preserved

**Location**: `pool.py:173-183`, `simple.py:72`

Futures appended to list in work item order (lines 173-181). Results collected via `[f.result() for f in futures]` in same order. `results[i]` corresponds to `works[i]`.

**Caveat**: Results contain `{var_name: StatType}` dicts but NO file path metadata. There's no way to verify which result came from which file without relying on ordering.

**Severity**: MEDIUM (ordering is preserved but not verifiable — fragile)

---

## Severity Summary

| Check | Status | Severity |
|-------|--------|----------|
| `_entry_buffer` isolation | SAFE | NONE |
| Worker return guarantee | SAFE | NONE |
| StatType mutation sequencing | SAFE | NONE |
| Singleton hot-reload | **UNSAFE** | **HIGH** |
| deepcopy correctness | SAFE | NONE |
| Future ordering | SAFE (fragile) | MEDIUM |

## Conclusions

**Thread migration is sound.** The deepcopy isolation, future blocking, and worker return guarantees are all correct. No data corruption risk from the ProcessPool → ThreadPool switch.

**One HIGH issue**: Singleton re-initialization on Streamlit hot-reload can leak Perl processes and hold stale executors. This doesn't cause data corruption but causes resource exhaustion over time.

**One MEDIUM issue**: Results ordering is preserved but lacks metadata verification. This is fragile but not currently causing bugs.

## Recommendations

1. Implement `reset()` methods on all singleton pools
2. Register atexit hook in `app.py` to call `shutdown_worker_pool()`
3. Add file path metadata to parse results for traceability
4. Consider using `@st.cache_resource` cleanup callback for pool lifecycle
