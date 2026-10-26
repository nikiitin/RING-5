---
name: parser-improvement
description: Improve RING-5's gem5 parsing/scanning — performance (Perl worker pool, pattern aggregation, async pools), robustness, and new strategies — without breaking the correctness invariants. Use when asked to speed up, harden, or extend the parser (for adding a stat type, use parsing-and-variable-types; to gate it, use parser-check).
---

# Improve parser performance and robustness

Preserve the contracts in [parser-check](../parser-check/SKILL.md). Use
[parsing-and-variable-types](../parsing-and-variable-types/SKILL.md) when adding a statistic type.
The repository [parsing guide](../../../docs/developer-guide/subsystems/parsing.md) documents the
current execution and data contracts.

## Execution owners

- `src/parsing/gem5/impl/strategies/perl_worker_pool.py` owns persistent extraction processes and
  `fileParserServer.pl` requests. Preserve process reuse across variables and files.
- `src/parsing/gem5/impl/scanning/scanner.py` invokes `statsScanner.pl` for each scanned file.
  Measure subprocess startup, Perl classification and Python decoding separately.
- `src/parsing/gem5/impl/scanning/pattern_aggregator.py` groups concrete numeric sources into
  patterns with explicit source-instance records. Preserve those records through submission.
- `src/parsing/framework/work_pool.py` owns the shared thread executor. Its typed commands return
  caller-owned Futures. Session cancellation affects owned work; global shutdown drains accepted
  work before another executor generation starts.

`RING5_WORK_POOL_SIZE` and `RING5_PERL_POOL_SIZE` configure separate pools. Both default to two
workers. Measure resident memory, process counts, latency and throughput before increasing them.

## Investigation and change

1. Reproduce with a fixed input set and explicit parser configuration. Use `make test-data` for the
   shared corpus and keep that corpus unchanged. Record interpreter, tool versions, pool sizes,
   file counts and input selection with the measurements.
2. Measure scan, source resolution, extraction, reduction and output publication separately.
   Compare cold and warm runs; inspect peak memory as well as elapsed time. Performance checks in
   `tests/performance/` use the `benchmark` marker. Do not infer a current bottleneck from an older
   workload's timings or assume a different executor improves Perl-bound work.
3. Preserve the single backend submit/finalize route. Strategy changes belong in `StrategyFactory`;
   `simple` reads statistics and `config_aware` also reads companion configuration.
4. Keep stderr draining independent of stdout. Readers own one process generation, and shutdown
   must settle its processes and threads. Exercise cancellation, timeouts, failed startup and
   concurrent shutdown when changing pool ownership.
5. Bound dynamic source expansion and retained results before expensive allocation. High-repeat
   patterns need resource-admission checks, rather than treating multi-gigabyte output as an
   ordinary throughput benchmark. Rejection must remain visible and leave prior output intact.
6. Compare results with the same inputs and configuration. Preserve exact literal text, numeric
   values, column ownership, missing-observation diagnostics, tails and summaries. A faster path
   that changes these semantics fails the correctness gate.

## Verification

Run `make arch-check`, type-check the touched owners and run focused parsing, scanner, lifecycle
and strategy tests. Add real-worker integration checks for behavior crossing the Perl boundary.
Run the relevant performance cases against the recorded baseline, then the full quality and test
gates before merging. Keep new measurements with the review evidence; document durable contracts
in the repository developer guide.
