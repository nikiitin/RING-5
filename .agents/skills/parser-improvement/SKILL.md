---
name: parser-improvement
description: Improve RING-5's gem5 parsing/scanning — performance (Perl worker pool, pattern aggregation, async pools), robustness, and new strategies — without breaking the correctness invariants. Use when asked to speed up, harden, or extend the parser (for adding a stat type, use parsing-and-variable-types; to gate it, use parser-check).
---

# Parser improvement (make parsing faster / tougher, safely)

Parsing is the hot path and the place data integrity can silently break. Improve it **only** behind
the correctness invariants in the `parser-check` skill (never fabricate; async-only; lifecycle
invariant). To add a new stat type or wire Perl, use `parsing-and-variable-types`.

## Where the speed comes from (don't regress these)
- **Persistent Perl worker pool** (`gem5/impl/strategies/perl_worker_pool.py`) — long-lived Perl
  processes via `fileParserServer.pl`, ≈54× over per-variable subprocesses. The win is *process
  reuse*; anything that respawns Perl per variable destroys it.
- **Pattern aggregation** (`gem5/impl/scanning/pattern_aggregator.py`) — collapses
  `system.cpu0..15.numCycles` → one `system.cpu\d+.numCycles` regex variable with `entries`
  (≈94% variable reduction). Keep scan output aggregated; expand to concrete names only at parse
  time using `scanned_vars`.
- **One shared `WorkPool`** (`src/parsing/framework/work_pool.py`) — a singleton `ThreadPoolExecutor`
  over `concurrent.futures` (`shutdown()` + `atexit`); backends submit `Job`s through the
  `gem5/impl/pool/` facades (`ScanWorkPool`/`ParseWorkPool`).

## Where the time actually goes (measured — see [[ring5-parser-perf-profile]])
Profiled on the real 586-file bench (16-core host). Start from these facts, not intuition:
- **Parse is Perl-pool-bound.** `WorkPool` is one `ThreadPoolExecutor(cpu_count*2)` (no process pool);
  parse threads dispatch to the persistent `PerlWorkerPool`, size **hard-coded 4**
  (`perl_worker_pool.py:432,664`). So parse concurrency = 4 no matter the core count. Raising it is the
  one validated win: 40 vars × 586 files = 14.8s @4 → 10.2s @8 (1.45×) → 8.9s @14 (1.66×). Sub-linear
  (per-file Python work is GIL-bound). Make the size adaptive + RAM-capped (each worker is a live Perl
  process; CI is RAM-bound — see the `make test-e2e` note).
- **Scan spawns a fresh `perl` per file** (`scanner.py:96`, no pool) → ~195 ms/file, 90% Perl, ~12.6k
  vars/file pre-aggregation. It runs ~3× parallel on the thread pool. **A process pool does NOT help**
  (measured 1.03–1.12× — scan is Perl-work-bound, not GIL/thread-bound), so a scan pool (process or
  persistent-Perl) is **not worth building**. Default UI scan is `limit=5` (~0.6s); only full-catalog
  scans (limit=-1 → ~51s) are slow, and the only real lever there is a faster Perl scanner itself.
- **CSV assembly is NOT a bottleneck** — measured 0.01–0.04s. Do **not** "vectorize reduce_duplicates"
  or "dedup the header scan" for speed; it saves nothing. Optimize it only for correctness/clarity.
- **Huge-repeat pattern vars are a RAM cliff, not a throughput target** — e.g.
  `…ctrl_traffic_distribution.n\d+.n\d+` has repeat=2704; selecting many such vars → multi-GB RAM and
  per-file timeouts. Guard/stream them; don't benchmark with them as a "normal" load.

## Improvement playbook
1. **Profile first.** Use real data (`make test-data`) and a headless `ApplicationAPI()` parse over the
   586-file bench; measure scan vs. parse separately (different bottlenecks, above). `tests/performance/`
   has the `benchmark` marker.
2. **Concurrency** — tune the Perl pool size (`perl_worker_pool.py`) / batching, not ad-hoc threads.
   Watch the stderr-drain path: a blocking read of a worker pipe re-creates the old high-concurrency
   deadlock ([[perl-pool-highconc-stall]]). Keep the drainer thread.
3. **Strategy work** — `simple` (stats.txt only) and `config_aware` (also reads `config.ini`) via
   `StrategyFactory`. New strategies go here; they must still produce no-fabrication output.
4. **CSV assembly** — `construct_final_csv` unions headers across files; if you touch it, keep the
   immutability rule (no `inplace=True`) — but it's not where the time is.
5. **Retire cruft as you go** — substitute, don't adapt ([[substitute-not-adapt-ring5]]): one canonical
   path, no parallel/legacy code. (There are no production `ParseService`/`ScannerService` shims — that
   was verified absent; the only `as ParseService` aliases are test-local cosmetics.)

## Guardrails (every change must hold)
- No fabrication, async-only, StatType lifecycle (`balance_content`→`reduce_duplicates` before
  `reduced_content`), Perl regex updated in **both** `parseAndPrintLineWithFormat` and `classifyLine`
  (histogram before distribution). Run the `parser-check` gate before declaring done.
- A speedup that changes any parsed value is a **bug**, not a win — diff CSV output against a baseline
  on real data.

## Keep this skill sharp
Canon, not history — edit in place when the parser internals move:
- The pool/strategy/aggregator paths above mirror `src/parsing/gem5/impl/`. If a module moves or a new
  bottleneck/optimization is found, update this playbook; durable facts → a memory.
- When a "speedup" turns out to silently alter values, record the trap here so it isn't repeated.

## Verify after
`make arch-check && ./python_venv/bin/pytest tests/unit -k "parse or scan or gem5" -q && ./python_venv/bin/pytest tests/performance -q`
(diff real-data CSV output against a pre-change baseline; run the `parser-check` gate).
