# Thorough Deep-Dive Review — Master Investigation Plan

> **Created**: 2026-02-27
> **Branch**: `005/unified-engine-ui-v2`
> **Baseline**: All research scan fixes applied, 3446 tests passing (commit `362106e`)
> **Previous Work**: `.agent/research-scan/` (10 tracks, all COMPLETE)

---

## Original Prompt (Verbatim)

> "Please complete the analysis plan with a thorough check for duplicated paths.
> Remember, this is the plan for the analysis, but you had really interesting
> findings in the research you performed, so include all these findings in the
> investigation plan, then prepare the plan for the thoroughful deep investigation
> please. That investigation must be incredibly deep, with high reasoning
> capabilities and actually line by line even following dependencies. Please,
> remember to write the plan with what would be the investigation step by step and
> create a document for every one of those researchs as we did for the
> research-scan. Call this one thorough-review. The created files must contain what
> is needed to look at, how to do it, what we think we will find and the outcome
> of the research. That last part must be pending as the next step will be to
> perform the investigation and research. Include in that analysis plan to fix all
> the trunk issues the project has when all the refactors are done"

---

## Methodology

1. **9 parallel deep-scan agents** analyzed every file in `src/`:
   - Dead code sweep (files, functions, backward-compat shims)
   - Parsing layer correctness (gem5_parse_work, perl_worker_pool, strategies)
   - Core layer correctness (services, models, shapers)
   - Web/UI layer correctness (components, controllers, pages)
   - Thread safety & performance (locks, singletons, hot-reload)
   - Type safety & duplication (dict[str, Any], @override, protocols)
   - Test coverage gaps (zero-coverage files, brittle tests, missing edge cases)
   - Streamlit patterns (caching, session state, widget anti-patterns)
   - Plotly & Matplotlib patterns (connectors, figure cleanup, duplication)
2. **trunk check --all** ran across 733 files for lint/format issues.
3. Findings consolidated into **16 investigation tracks** ordered by severity.
4. **Duplicated paths** from the previous DEEP_DIVE_PLAN.md identified and resolved.

---

## Duplicated Paths Identified & Resolved

These items were duplicated in the original DEEP_DIVE_PLAN.md and are now consolidated:

| Duplicate A | Duplicate B | Resolution |
| --- | --- | --- |
| Phase 2.5 (CSV header incompleteness) | Phase 5.4 (same CSV header issue) | Merged into Track 02, item 2.8 |
| Phase 6.4 (@override decorator) | Phase 8.2 (@override annotations) | Merged into Track 08, item 8.4 |
| Phase 3.4 (@st.cache_data for CSV) | Phase 7.3 (@st.cache_data) | Merged into Track 09, item 9.3 |
| Phase 12.1 (Use Plotly Express) | Project rule: No Plotly Express | **REMOVED** - contradicts `.github/copilot-instructions.md` |

---

## Summary Dashboard

| Category | Items | Severity | Track |
| --- | --- | --- | --- |
| Dead code / unused files | 18 items | CRITICAL | Track 01 |
| Parsing layer correctness | 15 findings | CRITICAL-HIGH | Track 02 |
| Core layer correctness | 8 findings | HIGH-MEDIUM | Track 03 |
| Web/UI correctness | 14 findings | HIGH-MEDIUM | Track 04 |
| Thread safety & concurrency | 10 findings | CRITICAL-HIGH | Track 05 |
| Type safety improvements | 496+ dict[str,Any], 80+ Any | MEDIUM | Track 06 |
| Code duplication consolidation | 8 major areas | HIGH | Track 07 |
| Modern Python 3.12+ upgrades | 12 patterns | MEDIUM | Track 08 |
| Streamlit best practices | 7 anti-patterns | MEDIUM | Track 09 |
| Plotly & Matplotlib patterns | 6 items | MEDIUM | Track 10 |
| Architecture improvements | 6 patterns | MEDIUM | Track 11 |
| Test coverage expansion | 15+ gaps | HIGH | Track 12 |
| Pandas best practices | 5 patterns | MEDIUM | Track 13 |
| Data science quality | 4 items | MEDIUM | Track 14 |
| Extensibility frameworks | 3 items | LOW | Track 15 |
| Trunk lint/format fixes | 20 unformatted + 119 lint | MEDIUM | Track 16 |

**Total**: ~180 investigation items across 16 tracks

---

## Investigation Tracks

| Track | Title | Research File | Status | Priority |
| --- | --- | --- | --- | --- |
| 01 | Dead Code & Unused Files | [track_01_dead_code.md](track_01_dead_code.md) | PENDING | CRITICAL |
| 02 | Parsing Layer Correctness | [track_02_parsing_correctness.md](track_02_parsing_correctness.md) | PENDING | CRITICAL |
| 03 | Core Layer Correctness | [track_03_core_correctness.md](track_03_core_correctness.md) | PENDING | HIGH |
| 04 | Web/UI Layer Correctness | [track_04_web_ui_correctness.md](track_04_web_ui_correctness.md) | PENDING | HIGH |
| 05 | Thread Safety & Concurrency | [track_05_thread_safety.md](track_05_thread_safety.md) | PENDING | CRITICAL |
| 06 | Type Safety Improvements | [track_06_type_safety.md](track_06_type_safety.md) | PENDING | MEDIUM |
| 07 | Code Duplication Consolidation | [track_07_code_duplication.md](track_07_code_duplication.md) | PENDING | HIGH |
| 08 | Modern Python 3.12+ | [track_08_modern_python.md](track_08_modern_python.md) | PENDING | MEDIUM |
| 09 | Streamlit Best Practices | [track_09_streamlit_patterns.md](track_09_streamlit_patterns.md) | PENDING | MEDIUM |
| 10 | Plotly & Matplotlib Patterns | [track_10_plotly_matplotlib.md](track_10_plotly_matplotlib.md) | PENDING | MEDIUM |
| 11 | Architecture & Extensibility | [track_11_architecture.md](track_11_architecture.md) | PENDING | MEDIUM |
| 12 | Test Coverage Expansion | [track_12_test_coverage.md](track_12_test_coverage.md) | PENDING | HIGH |
| 13 | Pandas Best Practices | [track_13_pandas_best_practices.md](track_13_pandas_best_practices.md) | PENDING | MEDIUM |
| 14 | Data Science Quality | [track_14_data_science.md](track_14_data_science.md) | PENDING | MEDIUM |
| 15 | Extensibility Frameworks | [track_15_extensibility.md](track_15_extensibility.md) | PENDING | LOW |
| 16 | Trunk Lint & Format Fixes | [track_16_trunk_fixes.md](track_16_trunk_fixes.md) | PENDING | MEDIUM |

---

## Execution Order (Dependency-Aware)

```text
Phase A (No dependencies — can start immediately):
  Track 01: Dead Code Removal
  Track 02: Parsing Correctness
  Track 03: Core Correctness
  Track 04: Web/UI Correctness
  Track 05: Thread Safety

Phase B (Depends on Phase A):
  Track 07: Code Duplication (needs dead code removed first)
  Track 06: Type Safety (needs correctness fixes stable)

Phase C (Depends on Phase B):
  Track 08: Modern Python 3.12+ (needs duplication resolved)
  Track 09: Streamlit Patterns (needs duplication resolved)
  Track 10: Plotly/Matplotlib (needs duplication resolved)
  Track 11: Architecture (needs duplication resolved)

Phase D (Depends on Phase C):
  Track 13: Pandas Best Practices (needs modern patterns in place)
  Track 14: Data Science Quality (needs shaper improvements)
  Track 15: Extensibility (needs architecture stable)

Phase E (Depends on ALL above):
  Track 12: Test Coverage (tests for all changes)
  Track 16: Trunk Fixes (final formatting pass)
```

---

## Cross-Reference: Previously Fixed Issues (research-scan)

These issues from `.agent/research-scan/` have already been fixed and should NOT be re-investigated:

| ID | Issue | Fix Applied | Commit |
| --- | --- | --- | --- |
| C1 | is_busy race condition | GIL atomicity documented | 362106e |
| C2 | Sequential f.result() freezes | as_completed() | 362106e |
| C3 | rglob() scans entire tree | Early-stop iteration | 362106e |
| C4 | Regex config multiplication | Warning when >50 | 362106e |
| C5 | Repeat count compounding | Warning when >50 | 362106e |
| C6 | Variable aliasing mutable | copy.copy() | 362106e |
| C7 | Distribution reduce O(DxR) | .items() iteration | 362106e |
| C8 | DataFrame copy compounds | Removed redundant copies | 362106e |
| H2 | was_healthy logic wrong | Capture before health_check | 362106e |
| H3 | apply() not vectorizable | Series.str.extract() | 362106e |
| H4 | PivotWider missing aggfunc | pivot_table(aggfunc="first") | 362106e |
| H6 | Histogram rebinning O(B^2) | Pre-computed bin mapping | 362106e |

---

## Previously Skipped (Now Included)

| ID | Issue | Originally Skipped Because | Now In |
| --- | --- | --- | --- |
| C9 | No concurrent thread-safety tests | Requires live Perl | Track 12, item 12.7 |
| H1 | Queue starvation on all-worker fail | Edge case + existing timeout | Track 05, item 5.6 |
| H5 | Singleton re-init on hot-reload | Handled by @st.cache_resource | Track 05, item 5.5 |

---

## NEW Findings (Not in Original DEEP_DIVE_PLAN.md)

These were discovered by deeper analysis agents and are now tracked:

| Finding | Severity | Track |
| --- | --- | --- |
| SimpleCache (performance.py) not thread-safe | CRITICAL | Track 05, 5.1 |
| CsvPoolService module-level mutable caches without locks | HIGH | Track 05, 5.2 |
| Shallow copy bug in simple.py:182-184 (copy.copy vs deepcopy) | HIGH | Track 02, 2.6 |
| vector.py:145-159 missing entry init before padding | MEDIUM | Track 02, 2.9 |
| scalar.py:58-61 integer truncation in sum | MEDIUM | Track 02, 2.10 |
| gem5_parser.py:306 unchecked column_map[var_name] | HIGH | Track 02, 2.7 |
| 3 upward import violations (web -> parsing) | HIGH | Track 11, 11.1 |
| stacked_bar_plot.py:162 DataFrame.iterrows() perf | MEDIUM | Track 13, 13.3 |
| Grouped stacked bar bypasses FigureSpecToPlotly pipeline | MEDIUM | Track 10, 10.5 |
| ZERO @st.cache_data/@st.cache_resource decorators | HIGH | Track 09, 9.3 |
| No plt.close() calls anywhere — memory leak | HIGH | Track 10, 10.3 |
| Matplotlib figures stored in session_state | MEDIUM | Track 10, 10.4 |
| 496 dict[str,Any] across 60+ files | MEDIUM | Track 06, 6.1 |
| 10 Protocol classes missing @runtime_checkable | MEDIUM | Track 06, 6.3 |
| pivot_config.py:256-258 — 3 pyright "possibly unbound" errors | HIGH | Track 04, 4.8 |

---

## Progress Tracking

| Track | Status | Items Done | Items Total | Notes |
| --- | --- | --- | --- | --- |
| 01 | PENDING | 0 | 8 | |
| 02 | PENDING | 0 | 15 | |
| 03 | PENDING | 0 | 8 | |
| 04 | PENDING | 0 | 9 | |
| 05 | PENDING | 0 | 8 | |
| 06 | PENDING | 0 | 6 | |
| 07 | PENDING | 0 | 8 | |
| 08 | PENDING | 0 | 8 | |
| 09 | PENDING | 0 | 7 | |
| 10 | PENDING | 0 | 6 | |
| 11 | PENDING | 0 | 6 | |
| 12 | PENDING | 0 | 10 | |
| 13 | PENDING | 0 | 5 | |
| 14 | PENDING | 0 | 4 | |
| 15 | PENDING | 0 | 3 | |
| 16 | PENDING | 0 | 8 | |
| **TOTAL** | | **0** | **119** | |
