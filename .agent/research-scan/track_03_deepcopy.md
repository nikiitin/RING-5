# Track 3: deepcopy Performance Impact

**Status**: DONE
**Priority**: P4
**Absolute Path**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.agent/research-scan/track_03_deepcopy.md`

---

## Goal

Determine if `copy.deepcopy(template_map)` per file is the bottleneck.

## Relevant Files

- `src/parsing/gem5/impl/strategies/simple.py` — `SimpleStatsStrategy`

## Method

Measured during Track 1 profiling session. The `deepcopy` call was timed independently as part of the overall parsing instrumentation.

## Results

| Metric                     | Value   |
|----------------------------|---------|
| Number of deepcopy calls   | 586     |
| Total deepcopy time        | ~0.04s  |
| Per-copy average            | ~68 μs  |

## Conclusion

**Not a significant bottleneck at this scale.** 586 deep copies of `template_map` take ~40ms total — negligible compared to the 5.9s parsing time.

The deepcopy fix was still correct (thread-safety), but it does not explain the performance issue.

## References

- Full timing data: [Track 1](./track_01_profiling.md)
