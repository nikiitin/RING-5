# Track 1: Profile the Actual Bottleneck

**Status**: DONE
**Priority**: P0 (Critical path — all other tracks depend on this)
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_01_profiling.md`

---

## Goal

Identify exactly where time is spent — parsing, scanning, CSV construction, shaping, or UI rendering.

## Method

Added `time.perf_counter()` instrumentation around each phase of the pipeline:
- File discovery
- Parsing (Perl worker pool + future collection)
- CSV construction (`construct_final_csv()`)
- Shaper pipeline (PivotLonger, etc.)

## Results

| Phase                          | Duration   | Notes                           |
|--------------------------------|------------|---------------------------------|
| Parsing 586 files              | ~5.9s      | Main time consumer              |
| PivotLonger (586 rows)         | ~0.002s    | Negligible                      |
| CSV Aggregation                | ~0.005s    | Negligible                      |
| `copy.deepcopy(template_map)`  | ~0.04s     | Negligible (586 copies)         |

## Key Findings

1. **Parsing dominates** — 5.9s for 586 files is the primary time cost.
2. **Post-parsing operations are fast** — PivotLonger, CSV aggregation, and deepcopy are all sub-100ms.
3. **The bottleneck is in the Perl worker pool** — Each file requires a Perl subprocess call, and the throughput depends on pool size, worker health, and I/O patterns.

## Implications

- Tracks 3, 4, and 5 are unlikely to be the root cause (confirmed by timing).
- Track 2 (Perl worker pool) and Track 7 (data volume) are the highest-value follow-ups.
- Track 8 (scanning) may also be relevant if the symptom is "deep scan" specific.

## Next Steps

- Investigate Perl worker pool throughput (Track 2).
- Quantify data volume (Track 7) to understand if 586 files is typical or if the user is hitting thousands.
