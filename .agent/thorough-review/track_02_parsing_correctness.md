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

- **2.1**: Confirmed crash on malformed lines. Fix: bounds check + skip with warning.
- **2.2**: Confirmed pipe leak. Fix: unconditional close in `finally` block.
- **2.3**: Confirmed thread accumulation. Fix: replace with `select.select()` or `selectors` module.
- **2.6**: StatType subclasses likely have nested mutables (`_content` dict with list values). `copy.copy()` may be insufficient for some types. Need `copy.deepcopy()` or a custom `__copy__` method.
- **2.7**: Confirmed potential KeyError. Fix: `.get()` with error handling.
- **2.8**: Header is indeed built from first result. Fix: build from config variable list.

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 2.1 Unchecked index | PENDING | | |
| 2.2 Pipe leak | PENDING | | |
| 2.3 Thread accumulation | PENDING | | |
| 2.4 Health monitor stop | PENDING | | |
| 2.5 Silent exception | PENDING | | |
| 2.6 Shallow copy depth | PENDING | | |
| 2.7 Dict access safety | PENDING | | |
| 2.8 CSV header completeness | PENDING | | |
| 2.9 Vector init | PENDING | | |
| 2.10 Scalar truncation | PENDING | | |
| 2.11 Mixed return types | PENDING | | |
| 2.12 Broad exception | PENDING | | |
| 2.13 Silent scan error | PENDING | | |
| 2.14 Histogram range | PENDING | | |
| 2.15 Health check sync | PENDING | | |
