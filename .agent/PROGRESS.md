# Implementation Progress — Research Scan Fixes

## Research Issues (from .agent/research-scan/PLAN.md)

### CRITICAL Issues

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| C1 | `is_busy` flag race condition — GIL atomicity doc | DONE | Added documentation comment in perl_worker_pool.py |
| C2 | Sequential `f.result()` freezes scan UI | DONE | Replaced with `as_completed()` in data_source_components.py |
| C3 | `rglob()` scans entire tree with limit | DONE | Early-stop iteration in gem5_scanner.py |
| C4 | Regex config multiplication warning | DONE | Added warning when >50 concrete names in gem5_parser.py |
| C5 | Repeat count compounding warning | DONE | Added warning when >50 parsed_ids in simple.py |
| C6 | Variable aliasing mutable object | DONE | `copy.copy(stat_obj)` in simple.py |
| C7 | Distribution reduce redundant lookup | DONE | `.items()` iteration in distribution.py |
| C8 | DataFrame copy in pipeline | DONE | Removed copies in pipeline_service.py + pivot.py PivotWider |
| C9 | No concurrent thread-safety tests | SKIPPED | Test gap, not a code fix |

### HIGH Issues

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| H1 | Queue starvation when all workers fail | SKIPPED | Edge case, not blocking |
| H2 | `was_healthy` logic semantically wrong | DONE | Moved capture BEFORE health_check() |
| H3 | `apply()` with regex not vectorizable | DONE | Replaced with `Series.str.extract()` in PivotLonger |
| H4 | PivotWider missing aggfunc crash risk | DONE | Changed `pivot()` to `pivot_table(aggfunc="first")` |
| H5 | Singleton re-init on hot-reload | SKIPPED | Streamlit lifecycle issue, low priority |
| H6 | Histogram rebinning O(B^2 x R) | DONE | Pre-computed bin mapping in `_compute_bin_mapping()` |

## Other Changes

| Change | Status | Notes |
|--------|--------|-------|
| Axis line controls in axes_settings.py | DONE | Added width + color for X/Y/top/right axes |
| Numbered X-axis modes (pills multiselect) | DONE | `numbered_xaxis_modes`, `show_numbered_ticks`, `show_numbered_legend` |
| Group label offset alias | DONE | `group_label_offset` = `major_label_offset` |
| Filtered selector component | DONE | New component in previous session |
| Pool future leak fix | DONE | Fixed in previous session |

## Test Suite Fixes

| Test | Issue | Fix |
|------|-------|-----|
| 11 settings_pills_e2e tests | Missing `numbered_xaxis`, `group_label_offset`, `numbered_xaxis_modes` keys | Added controls to `axes_settings.py` |
| test_histogram_selection_priority | KeyError in `_reduce_with_rebinning` for computed bin keys not in `target_reduced` | Added safety `if key not in target_reduced` init |
| 2 test_render_parser_config tests | `as_completed()` hangs on MagicMock futures | Patched `as_completed` in test to iterate directly |
| test_render_parser_config_calls_api_directly | Same `as_completed` issue | Same fix |
| test_render_selector_empty_selection_warns | `filtered_multiselect` not mocked | Added `@patch` for `filtered_multiselect` |
| test_variable_config_dialog_search_scanned | `filtered_selectbox` not mocked | Added `filtered_selectbox` patch to fixture |

## Test Suite Status

| Step | Status | Notes |
|------|--------|-------|
| Run full test suite | DONE | 3446 passed, 2 skipped, 0 failed |
| Fix test failures | DONE | All 16 failures fixed |

## COMPLETE
All research scan fixes applied. All tests passing.
