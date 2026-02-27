# Track 01: Dead Code & Unused Files

> **Priority**: CRITICAL
> **Status**: PENDING
> **Estimated items**: 8

---

## What to Look At

### 1.1 Dead utility functions in `src/core/common/utils.py`

**File**: `src/core/common/utils.py`, lines 21-224
**What**: 13 legacy utility functions that are never called anywhere in the codebase:
- `getElementValue()` (lines 21-49)
- `checkElementExists()` (lines 52-64)
- `checkElementExistNoException()` (lines 67-78)
- `checkEnumExistsNoException()` (lines 81-95)
- `getEnumValue()` (lines 98-114)
- `checkFilesExistOrException()` (lines 117-128)
- `checkFileExistsOrException()` (lines 131-142)
- `checkFileExists()` (lines 145-155)
- `checkDirExistsOrException()` (lines 158-169)
- `checkDirExists()` (lines 172-182)
- `createDir()` (lines 185-195)
- `createTmpFile()` (lines 198-209)
- `checkVarType()` (lines 212-224)

**Keep**: `normalize_user_path()` and `sanitize_glob_pattern()` which ARE used.

### 1.2 Dead UI file: `plot_manager_components.py`

**File**: `src/web/pages/ui/components/plot_manager_components.py` (~200 lines)
**What**: Completely replaced by controller architecture. Has imports FROM `web.pages.ui` (plotting, shaper_config) but no other file imports FROM it.

### 1.3 Duplicate shaper config file: `split_apply_config.py`

**Files**:
- `src/web/components/shapers/split_apply_config.py`
- `src/web/pages/ui/components/shapers/split_apply_config.py`

**What**: Two copies of the same file. Need to determine which one is imported and delete the other.

### 1.4 Duplicate data manager files

**Files**:
- `src/web/components/data_managers/seeds_reducer.py` vs `src/web/pages/ui/components/data_managers/seeds_reducer.py`
- `src/web/components/data_managers/outlier_remover.py` vs `src/web/pages/ui/components/data_managers/outlier_remover.py`

**What**: Same duplication pattern as split_apply_config. One copy in components/, one in pages/ui/.

### 1.5 Backward compatibility shim files

**Files**:
- `src/parsing/gem5/impl/parse_service.py` — re-exports from where?
- `src/parsing/gem5/impl/scanning/scanner_service.py` — re-exports from where?
- `src/parsing/csv_contract.py` — re-export shim (canonical: `core/models/csv_contract.py`)

**What**: Backward compat shims that may no longer be needed if all callers have been updated.

### 1.6 Unused widget framework

**Files**:
- `src/web/rendering/widgets/widget_def.py`
- `src/web/rendering/widgets/widget_renderer.py`

**What**: Defined but never used in the web layer (only in test file).

### 1.7 Upward imports from components to pages/ui

**Files with suspicious import patterns**:
- `src/web/components/common/chart_display.py` — imports from `web.pages.ui` (download_section)
- `src/web/components/plotting/settings/colors_settings.py` — imports `to_hex` from `web.pages.ui`

**What**: Components should NOT import from pages/ui. This suggests dead or misplaced code.

### 1.8 Verify `__all__` exports in utils.py

**File**: `src/core/common/utils.py`
**What**: After removing dead functions, verify `__all__` (if present) is updated.

---

## How to Investigate

1. **For each dead function (1.1)**: Run `grep -rn "function_name" src/ tests/` to confirm zero usage. Check both direct calls and any dynamic dispatch.
2. **For duplicate files (1.3, 1.4)**: Diff the two copies (`diff file_a file_b`). Run `grep -rn "from.*import" src/` to find which copy is actually imported.
3. **For backward compat shims (1.5)**: Read each shim file. Check if any current import path uses the shim. If all imports go direct, the shim is dead.
4. **For widget framework (1.6)**: Search for any imports of `widget_def` or `widget_renderer` outside of tests. If only tests use it, evaluate if the test is testing dead code.
5. **For upward imports (1.7)**: Read the import lines. Trace what they actually import. Determine if that import target should be moved to a shared location instead.
6. **After all deletions**: Run `pytest tests/ -o "addopts=" --timeout=30 -x -q` to verify no breakage.

---

## What We Expect to Find

- **1.1**: All 13 functions are completely dead — no callers anywhere. Safe to delete entirely.
- **1.2**: `plot_manager_components.py` is fully dead — the controller architecture replaced it.
- **1.3, 1.4**: One copy is the canonical import target; the other is a leftover from a refactoring move.
- **1.5**: At least 1-2 shims are still imported by external code; the rest are dead.
- **1.6**: Widget framework is dead code — no production usage.
- **1.7**: The upward imports exist because functionality wasn't properly extracted to a shared location during refactoring.
- **Net effect**: ~400-600 lines of dead code removed, cleaner dependency graph.

---

## Outcome

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 1.1 Dead utils | **12 of 13 CONFIRMED DEAD**. Only `checkFileExistsOrException` is alive (gem5_parse_work.py:285). Dead: getElementValue, checkElementExists, checkElementExistNoException, checkEnumExistsNoException, getEnumValue, checkFilesExistOrException, checkFileExists, checkDirExistsOrException, checkDirExists, createDir, createTmpFile, checkVarType. `JsonValue` type alias also only used by dead functions. | HIGH | Remove 12 functions + JsonValue + unused imports (enum, tempfile). Update test_utils.py to only test checkFileExistsOrException. ~200 lines removed. |
| 1.2 plot_manager_components | **pages/ui copy CONFIRMED DEAD** (MD5 identical, zero imports). components/plotting copy is ALIVE (imported by src/web/pages/data_managers.py). | MEDIUM | Delete `src/web/pages/ui/components/plot_manager_components.py`. ~200 lines. |
| 1.3 split_apply_config dup | **pages/ui copy CONFIRMED DEAD** (MD5 identical, zero imports). Canonical: components/shapers/ (imported by shaper_config.py:11). | MEDIUM | Delete `src/web/pages/ui/components/shapers/split_apply_config.py`. ~360 lines. |
| 1.4 data_manager dups | **Both pages/ui copies CONFIRMED DEAD** (MD5 identical, zero imports). Canonical: components/data_managers/ (re-exported in __init__.py). | MEDIUM | Delete `pages/ui/data_managers/impl/seeds_reducer.py` (~200 lines) and `pages/ui/data_managers/impl/outlier_remover.py` (~190 lines). |
| 1.5 backward compat shims | **ALL 3 ALIVE**. csv_contract.py is a re-export shim. parse_service.py used by 15+ tests. scanner_service.py used by 8+ tests. | N/A | Keep all 3. They serve as stable import targets for test suites. |
| 1.6 widget framework | **ALIVE**. `WidgetRenderer` used in production by `base_ui.py:23`. Hypothesis was wrong. | N/A | Keep. Not dead code. |
| 1.7 upward imports | **5 VIOLATIONS in 3 files**: plot_manager_components.py:16-18 (3 imports), colors_settings.py:185 (to_hex), chart_display.py:24 (download_section). 42 total upward imports across codebase. | HIGH | Deferred to Track 11 (Architecture). These need extraction to shared locations. |
| 1.8 Other dead files | **4 dead directories found**: `pages/ui/components/` and `pages/ui/data_managers/impl/` have no `__init__.py` — not importable packages. They only contain the 4 duplicate files above. | LOW | Delete dead directories after removing their contents (items 1.2-1.4). |

### NEW FINDING: csv_contract.py re-evaluation
The initial agent scan predicted csv_contract.py was dead. Investigation confirms it IS imported in test paths and serves as a backward-compat re-export. **Keep it.**

### Estimated Implementation Impact
- **~950 lines removable** (12 functions + 4 duplicate files + associated dead test code)
- **0 production behavior change** — all removed items are unused
- **Test count will drop** by ~30 (tests for dead utility functions)
