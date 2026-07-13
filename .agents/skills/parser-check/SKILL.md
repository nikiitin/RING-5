---
name: parser-check
description: Gate the gem5 parsing/scanning subsystem for correctness — no data fabrication, async-only API, the StatType lifecycle invariant, Perl regex duplication, and worker-pool lifecycle. Use to verify parser/scanner/Perl/stat-type changes before merging (complements the parsing-and-variable-types build skill).
---

# Parser check (the parsing correctness gate)

Parsing is Layer A (`src/parsing/`, gem5 in `src/parsing/gem5/`): async over singleton pools, with a
persistent Perl worker pool. To *build/extend* parsing use `parsing-and-variable-types`; this skill
is the correctness gate. The cardinal sins here are **fabricating data** and **breaking the async
contract**.

## Checklist
1. **Never fabricate (hard rule #6).** On a regex non-match the parser **raises or logs** — it must
   never default to `0`/a guessed value. This is the highest-stakes invariant (see
   [[ring5-arch-audit-2026-06]]). Review every new parse branch for a silent fallback.
2. **Async-only (hard rule #7).** The public surface is `submit_scan_async` / `finalize_scan` /
   `submit_parse_async` / `finalize_parsing`; the backend implements the 4 `SimulationParser`
   protocol methods (`submit_parse_async`, `finalize_parsing`, `submit_scan_async`,
   `aggregate_scan_results`). **No synchronous wrapper** may be added.
3. **Pass `scanned_vars`** when parsing regex/pattern variables (reconstructs concrete names like
   `system.cpu\d+.numCycles` → `cpu0..N`).
4. **StatType lifecycle invariant** (`src/parsing/gem5/types/`): `balance_content()` then
   `reduce_duplicates()` **must** run before `reduced_content` is read. New/edited stat types must
   honor it. Ingestion/reduction must not truncate floats (no `int()` coercion).
5. **Perl regex is duplicated — update both.** A type's regex appears in **both**
   `parseAndPrintLineWithFormat` **and** `classifyLine` in
   `src/parsing/gem5/perl/libs/TypesFormatRegex.pm`. Ordering matters: **histogram before
   distribution**. A change to one without the other is a silent classification bug.
6. **Worker-pool lifecycle.** `WorkPool`/`ScanWorkPool`/`ParseWorkPool` and `PerlWorkerPool` each have
   `shutdown()` + an `atexit` handler — preserve them (no orphaned Perl processes on hot-reload).
   High-concurrency hangs were an undrained-stderr-pipe deadlock, now fixed by a drainer thread —
   don't reintroduce a blocking read (see [[perl-pool-highconc-stall]]).
7. **Internal/meta stats excluded** from selection (`GEM5_INFO.internal_stats` in
   `src/parsing/registry.py`): `total, mean, gmean, stdev, samples, sample_period, min_val, max_val,
   min_bucket, max_bucket, num_buckets, underflows, overflows`.

```bash
# fabrication smell: a bare 0 / empty default on a parse path
grep -rn "return 0\|= 0  #\|or 0\b" src/parsing/gem5/impl --include=*.py
# sync-wrapper smell
grep -rn "def .*parse\b\|def .*scan\b" src/parsing --include=*.py | grep -v async
```

## Dynamic check (real gem5 data on disk)
With `tests/data/results-micro26-sens/` present (`make test-data`), exercise the parser end-to-end via
a headless `ApplicationAPI()` (no Streamlit) — scan→`finalize_scan`, then `submit_parse_async`→
`finalize_parsing` — not just statically:
- **Classification** — scan one real `stats.txt` and assert a histogram var (`*.loadToUse::N-M`)
  classifies as `histogram` and a distribution var (`*.numIssuedDist::N`) as `distribution`. This is
  the live test of invariant 5 across **both** Perl paths. Then parse the histogram and confirm the
  output columns are **range** entries (`::N-M`), never single-int distribution entries.
- **Aggregation, not fabrication** — pattern/regex variables (`system.cpu\d+…`) are reduced across
  their concrete instances by **mean**. A parsed value cross-checked against a *single* instance looks
  wrong; verify it against the **mean of all matching instances** (a 16-core mean carries a `…/16`
  fraction, e.g. `386577.0625`). A value that traces to that mean is correct, not fabricated — don't
  raise a false alarm. Missing stats surface as **NaN, never 0** (rule #6 in action).

## Keep this skill sharp
Canon, not history — edit in place when the parser contract moves:
- The protocol methods, the lifecycle invariant, and `internal_stats` above mirror
  `parser_protocol.py`, `gem5/types/`, and `registry.py`. If those change, update this list.
- New correctness failure caught? Add it here (and to `parsing-and-variable-types` if it's a build
  step); durable facts → a memory.

## Verify after
`make arch-check && ./python_venv/bin/pytest tests/unit -k "parse or scan or gem5" -q` (add
`tests/integration/test_real_gem5_data.py` when touching real parsing; needs `make test-data` + Perl).
