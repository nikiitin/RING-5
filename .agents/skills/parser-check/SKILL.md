---
name: parser-check
description: Gate the gem5 parsing/scanning subsystem for correctness — no data fabrication, async-only API, the StatType lifecycle invariant, shared Perl classification, and worker-pool lifecycle. Use to verify parser/scanner/Perl/stat-type changes before merging (complements the parsing-and-variable-types build skill).
---

# Parser check (the parsing correctness gate)

Parsing lives in `src/parsing/`, with gem5 in `src/parsing/gem5/`: async over singleton pools, with a
persistent Perl worker pool. To *build/extend* parsing use `parsing-and-variable-types`; this skill
is the correctness gate. The cardinal sins here are **fabricating data** and **breaking the async
contract**.

## Checklist
1. **Never fabricate.** On a regex non-match the parser **raises or logs** — it must
   never default to `0`/a guessed value. Review every new parse branch for a silent fallback.
   The required invariants are defined in [AGENTS.md](../../../AGENTS.md).
2. **Asynchronous work.** The facade surface is `submit_scan_async` / `finalize_scan` /
   `submit_parse_async` / `finalize_parsing`; backends implement the complete `SimulationParser`
   protocol, including incremental and playground submission/finalization and scan aggregation.
   Public `Session.parse` composes the submit/finalize contract; it does not introduce another
   parser execution path. Preserve that ownership when adding orchestration.
   Full finalization requires its submitted `ParseBatchResult` and returns `ParsedOutput`.
   Incremental finalization requires its own submitted batch. Both use `complete: bool = True`;
   partial output still requires non-empty accepted results with exact planned provenance.
   Incremental partial mode retains valid cached/changed rows without promoting the success cache.
   Preserve fingerprint verification and accepted-row counts against the planned file total.
3. **Explicit source metadata.** Every runnable config declares `params.source_type`; numeric
   patterns require `scanned_vars` with concrete `SourceInstance` names and numeric coordinates.
   `selected_sources` contains concrete names only. Resolve once before workers, never reconstruct
   names from indices, infer missing kinds, or route through shared accumulator identities.
4. **StatType lifecycle invariant** (`src/parsing/gem5/types/`): `balance_content()` then
   `reduce_duplicates()` **must** run before `reduced_content` is read. New/edited stat types must
   honor it. `add_observation` accepts one numeric point, literal configuration string or
   numeric entry mapping. The worker converts numeric wire text once. No assignment setter,
   list-valued frame or dynamic attribute dispatch is an ingestion route. Collection closes
   after balancing; reduction before balancing raises; successful balance/reduce calls are
   idempotent. Content/result inspection returns defensive snapshots. Store actual observations
   only; `padded_count` and `missing_measurement_count` remain exact logical presence counts.
   Balancing/reduction must not allocate or iterate over absent frames proportional to `repeat`.
   Complete disjoint histogram frames may rebin missing raw buckets to justified zero contributions
   even with positive raw missing counts; a whole absent frame propagates NaN. Bound active rebin
   geometry and exact emitted width with the existing physical-column budget before mappings,
   preserving explicit-entry/statistics-only precedence and unemitted discovered summaries.
   Compact representations never copy raw observation content. Ingestion/reduction
   must not truncate floats (no `int()` coercion). Numeric population means share one owner;
   exercise finite sums beyond float range, cancellation with tiny residuals, subnormal values,
   measured zero, NaN and both signs of infinity without skipping missing observations.
   Missing-output diagnostics use actual observation presence, not derived NaN views; measured
   NaN values must remain distinguishable from absent entry/source measurements.
5. **One Perl classifier.** `TypesFormatRegex::classifyLine` produces semantic records for both
   scanning and persistent parsing. Preserve raw source entries separately from inclusive scan
   labels, summary roles, deferred geometry, and dump events. Keep histogram classification before
   distribution/vector classification. Test the same raw fixtures through both consumers.
6. **Worker-pool lifecycle.** `WorkPool` and `PerlWorkerPool` own `shutdown()` and `atexit`
   cleanup. Typed `WorkPool.submit`/`submit_many` accept callable commands and return caller-owned
   futures without retaining batches. Global shutdown joins executor retirement outside the
   submission lock; reject new work during drain and recreate only after retirement completes.
   Session cancellation affects only owned futures, not the shared executor. Preserve those
   ownership boundaries and prevent orphaned Perl processes on hot-reload.
   Drain stderr independently of stdout: a full stderr pipe can block Perl before it can produce
   its next stdout record. Keep each reader bound to its exact process generation.
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
- **Aggregation** — numeric pattern variables reduce the actual matching source/dump observations
  by their configured statistic semantics. Compare a population mean with all matching observations,
  rather than one concrete instance. Preserve measured zero and NaN independently from absent
  observations; numeric schema-union gaps appear as NaN, while missing text requires an explicit
  producer value. Never substitute a numeric default for missing measurements.

## Keep this skill sharp
Canon, not history — edit in place when the parser contract moves:
- The protocol methods, the lifecycle invariant, and `internal_stats` above mirror
  `parser_protocol.py`, `gem5/types/`, and `registry.py`. If those change, update this list.
- New correctness failure caught? Add its check here and to `parsing-and-variable-types` when it
  affects implementation. Document durable contracts in the repository developer guide.

## Verify after
`make arch-check && ./python_venv/bin/pytest tests/unit -k "parse or scan or gem5" -q` (add
`tests/integration/test_real_gem5_data.py` when touching real parsing; needs `make test-data` + Perl).
