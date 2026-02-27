# Track 02: Parsing Layer Correctness

> **Priority**: CRITICAL
> **Status**: PENDING
> **Estimated items**: 15
> **Scope**: `src/parsing/` — all gem5 parsing, strategy, type, and pool files

---

## What to Look At

### 2.1 Unchecked array index in `_parseLine()` — CRITICAL

**File**: `src/parsing/gem5/impl/strategies/gem5_parse_work.py`, line 103
**What**: `parts = line.split("/")` then `parts[2]` accessed without bounds check. Malformed Perl output (e.g., missing value field) causes `IndexError`, killing the worker and failing the entire parse batch.
**Dependencies**: Called by `_process_stat_line()` which is called for every line of Perl output.

### 2.2 Subprocess pipe leak on process death

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 306-315
**What**: `shutdown()` only closes pipes if `process.poll() is None`. If process died before shutdown, stdin/stdout pipes remain open as file descriptor leaks.
**Dependencies**: Affects all PerlWorkerPool usage. Over time, leaked FDs can exhaust OS limits.

### 2.3 Timeout thread accumulation

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 134-136
**What**: Spawns a daemon thread per `_read_line_with_timeout()` call. Rapid timeouts (unresponsive Perl) accumulate leaked threads holding file handles. No join/cleanup.
**Dependencies**: Called in `_send_and_receive()` main parsing hot path.

### 2.4 Health monitor thread graceful stop

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 404-411
**What**: Health monitor is a daemon thread with `_shutdown` flag but no `thread.join()`. Dangling thread can interfere with subsequent pool creation.
**Dependencies**: Pool shutdown → next pool creation sequence.

### 2.5 Silent exception suppression in parse work

**File**: `src/parsing/gem5/impl/strategies/gem5_parse_work.py`, lines 220-224
**What**: Broad `except Exception` catches ALL errors, logs them, but silently continues. A critical bug (like corrupted data) would be hidden.
**Dependencies**: Affects data integrity — wrong/missing results silently passed downstream.

### 2.6 Shallow copy bug in strategy — copy.copy vs copy.deepcopy

**File**: `src/parsing/gem5/impl/strategies/simple.py`, lines 182-184
**What**: After the C6 fix applied `copy.copy(stat_obj)` for aliases, need to verify this is sufficient. If `stat_obj` contains nested mutable state (lists, dicts), `copy.copy()` would share those references. Need to check `StatType` subclass internals (scalar, vector, distribution, histogram, configuration) for nested mutables.
**Dependencies**: ALL stat type classes: `scalar.py`, `vector.py`, `distribution.py`, `histogram.py`, `config_aware.py`.

### 2.7 Unchecked dictionary access in gem5_parser.py

**File**: `src/parsing/gem5/impl/gem5_parser.py`, line 306
**What**: `column_map[var_name]` accessed without `.get()`. If `var_name` not in `column_map`, `KeyError` crashes the CSV assembly step.
**Dependencies**: Called during result finalization; failure here loses ALL parsed data.

### 2.8 CSV header built from first result only

**File**: `src/parsing/gem5/impl/gem5_parser.py`, lines 269-282
**What**: Header built from the first parse result. If the first file is missing a variable that later files have, header is permanently incomplete. The fix should build header from the variable config (source of truth).
**Dependencies**: Downstream CSV consumers (data loading, shapers, plot pipeline).

### 2.9 Vector balance_content() missing entry initialization

**File**: `src/parsing/gem5/types/vector.py`, lines 145-159
**What**: `balance_content()` may access entries before they are properly initialized. Need to trace the exact code path: does `_content` always have all expected keys before `balance_content()` is called?
**Dependencies**: Vector type reduce → CSV output for vector variables.

### 2.10 Scalar reduce_duplicates integer truncation

**File**: `src/parsing/gem5/types/scalar.py`, lines 58-61
**What**: When summing scalar values, potential integer truncation if values are stored as int but result overflows. Need to verify the numeric types used.
**Dependencies**: Scalar reduce → mean calculation accuracy.

### 2.11 Mixed return types in scalar.py

**File**: `src/parsing/gem5/types/scalar.py`, lines 49-61
**What**: `reduce()` may return either `str` or `float` depending on path. Type inconsistency.
**Dependencies**: Type safety of downstream consumers.

### 2.12 Overly broad exception in config_aware.py

**File**: `src/parsing/gem5/types/config_aware.py`, line 73
**What**: `except Exception` when parsing configuration values. Should catch specific exceptions.
**Dependencies**: Configuration variable parsing correctness.

### 2.13 Silent exception in gem5_scan_work.py

**File**: `src/parsing/gem5/impl/scanning/gem5_scan_work.py`, lines 40-42
**What**: Scan work items suppress exceptions silently. Failed scans return incomplete results with no error indication.
**Dependencies**: Variable discovery completeness.

### 2.14 Histogram silent range parse failures

**File**: `src/parsing/gem5/types/histogram.py`, lines 302-307
**What**: Range parsing failures are silently ignored. A malformed histogram range string produces incorrect bin boundaries.
**Dependencies**: Histogram visualization accuracy.

### 2.15 Unsynchronized health check access

**File**: `src/parsing/gem5/impl/strategies/perl_worker_pool.py`, lines 417-442
**What**: Health check reads worker state while parse operations may be modifying it. While GIL provides some protection for simple attributes, complex state transitions (restart sequence) are not atomic.
**Dependencies**: Worker pool reliability under concurrent load.

---

## How to Investigate

1. **For 2.1**: Read `_parseLine()` and all callers. Trace the Perl output format to understand what valid/invalid lines look like. Write a test with malformed input.
2. **For 2.2**: Read `shutdown()` method. Check all paths where `process` can die. Verify pipe closing logic with `try/finally`.
3. **For 2.3**: Read `_read_line_with_timeout()`. Count thread creation rate under timeout conditions. Evaluate `selectors`/`poll()` alternative.
4. **For 2.6**: Read ALL StatType subclass `__init__` methods. Check for `list`, `dict`, or other mutable nested attributes. If found, `copy.copy()` is insufficient.
5. **For 2.7**: Search for all `column_map[` access patterns. Check if `column_map` is guaranteed to contain all variable names.
6. **For 2.8**: Read header construction code. Trace what happens when file 1 has vars {A,B} but file 2 has vars {A,B,C}.
7. **For 2.9-2.14**: Read each file at the specified lines. Trace the data flow to understand edge cases.
8. **After fixes**: Run full test suite + parsing-specific tests.

---

## What We Expect to Find

- **2.1**: CONFIRMED crash on malformed lines — `parts[2]` at line 103, no bounds check. Fix: bounds check + skip with warning.
- **2.2**: NOT A BUG — pipes ARE closed unconditionally at lines 306-315. Hypothesis was wrong.
- **2.3**: CONFIRMED thread accumulation — daemon thread per `_read_line_with_timeout()` call, never joined on timeout.
- **2.6**: CONFIRMED — ALL StatType subclasses have `_content` as nested list/dict. `copy.copy()` shares nested mutable state. `copy.deepcopy()` needed.
- **2.7**: NOT A BUG — `column_map` populated for all `ordered_names` before access. Key guaranteed present.
- **2.8**: CONFIRMED by design — header built from `results[0]` only. Later files with extra entries lose data.
- **2.10**: CONFIRMED HIGH — `int()` conversion at scalar.py:60 silently truncates decimal values during reduce.

---

## Outcome

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 2.1 Unchecked index | **CONFIRMED** — `_parseLine()` at line 103: `parts[0], parts[1], parts[2]` with no bounds check. Malformed Perl output → IndexError → worker crash. | HIGH | Add `if len(parts) < 3: log warning + skip line`. |
| 2.2 Pipe leak | **NOT A BUG** — Lines 306-315 close pipes unconditionally regardless of process state. Code is correct. | N/A | No action needed. |
| 2.3 Thread accumulation | **CONFIRMED** — Line 134 spawns daemon thread per call. On timeout (line 136), thread stays alive. No max limit. | MEDIUM | Replace with `selectors` module or `select.select()` for non-blocking reads. |
| 2.4 Health monitor stop | **CONFIRMED** — No `thread.join()` on `_health_monitor_thread` in `shutdown()`. Thread may outlive pool. | MEDIUM | Add `self._health_monitor_thread.join(timeout=health_check_interval+1)` in shutdown(). |
| 2.5 Silent exception | **NOT A BUG** — Lines 215-225 properly raise RuntimeError for unknown types. No broad except block. | N/A | No action needed. |
| 2.6 Shallow copy depth | **CONFIRMED HIGH** — ALL StatType subclasses have mutable nested state (`_content` is list or dict[str,list]). `copy.copy()` at simple.py:184 shares nested references. Mutation via `balance_content()` corrupts aliased variables. | HIGH | Replace `copy.copy(stat_obj)` with `copy.deepcopy(stat_obj)`. |
| 2.7 Dict access safety | **NOT A BUG** — `column_map` is populated for all `ordered_names` before access loop. Key is guaranteed present. | N/A | No action needed. |
| 2.8 CSV header completeness | **CONFIRMED** — Header built from `results[0]` only (line 263). Later files with different entries lose columns. Fix complex — union of all results changes header size. | MEDIUM | Build header as union of all results' entries, with consistent column ordering. |
| 2.9 Vector init | **NOT A BUG** — `_content` initialized for all entries in `__init__`. `balance_content()` uses defensive `.get()`. | N/A | No action needed. |
| 2.10 Scalar truncation | **CONFIRMED HIGH** — scalar.py:60 `int(self._content[i])` truncates decimals. e.g., [1.5, 2.7, 3.1] → sum=6 instead of 7.3. Silent data corruption. | HIGH | Replace `int()` with `float()` in the summation loop. |
| 2.11 Mixed return types | **CONFIRMED** — `_reduced_content` is either "NA" (str) or float. Downstream expecting float gets str. | MEDIUM | Use `float('nan')` instead of "NA" for missing values, or use `None` with explicit type. |
| 2.12 Broad exception | **CONFIRMED** — config_aware.py:73 catches `except Exception`. Should be `except (configparser.Error, OSError)`. | LOW | Narrow exception type. |
| 2.13 Silent scan error | **CONFIRMED** — gem5_scan_work.py:40 returns `[]` on any exception. Callers can't distinguish empty vs failed. | MEDIUM | Return a result object with error field, or re-raise with context. |
| 2.14 Histogram range | **CONFIRMED** — `_parse_range_key()` returns `[]` silently on non-numeric keys. Intentional for summary stats (mean, stdev) but no warning for failed real ranges. | LOW | Add logger.debug for failed range parses on keys that look numeric. |
| 2.15 Health check sync | **PARTIALLY CONFIRMED** — `is_busy` read without lock. GIL provides atomicity for simple bool in CPython. But not portable to other Python impls. | LOW | Already documented. Consider `threading.Event` for portability. |

### Corrections from Initial Hypotheses
- **2.2 was NOT a bug** — hypothesis about pipe leak was wrong, code properly closes pipes
- **2.5 was NOT a bug** — hypothesis about silent exception suppression was wrong
- **2.7 was NOT a bug** — hypothesis about dict KeyError was wrong, key always present
- **2.9 was NOT a bug** — hypothesis about missing init was wrong, entries initialized in __init__

### Critical Findings Summary (items requiring fix)
1. **scalar.py:60 `int()` truncation** — Silent data corruption in reducing scalar stats
2. **simple.py:184 shallow copy** — Mutable state shared between aliased variables
3. **gem5_parse_work.py:103 unchecked index** — Crash on malformed Perl output
