# Test Consolidation Map

> **Purpose**: Detailed mapping for consolidating 147 tests to ~55-60 tests,
> reducing redundant browser context creation and saving an estimated ~350-400s.

---

## 1. Problem Statement

**Current**: Every test function creates a new browser tab (function-scoped `page`).
Each test navigates to the app and sets up its state independently.

**Setup:Assertion ratio** is extreme:
- Simple UI tests: ~10:1 (3s setup for 0.3s assertion)
- E2E workflow tests: ~50:1 to ~100:1 (25-50s setup for 0.5-2s assertion)

**Worst offenders**:
- `TestParseToDataManagers` (4 tests × ~25s setup each = 100s total, <2s of assertions)
- `TestOutlierRemover` (2 tests × ~30s setup each = 60s total, <1s of assertions)
- `TestPreprocessor` (2 tests × ~30s setup each = 60s total, <1s of assertions)

---

## 2. Consolidation Strategy

### Approach: Class-Scoped Page + Ordered Tests

Instead of function-scoped `page`, use a **class-scoped page fixture** that
shares the browser tab across all tests in a class. Tests are **ordered** (top
to bottom) and each builds on the prior state.

**Key insight**: Streamlit's `@st.cache_resource` singleton means the server state
persists across all browser sessions anyway. A class-scoped page just avoids
re-navigating and re-setting up the same state multiple times.

### New Fixture

```python
@pytest.fixture(scope="class")
def shared_page(
    browser: Browser,
    browser_context_args: dict[str, object],
) -> Generator[Page, None, None]:
    """Class-scoped page — one browser tab per test class."""
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    yield page
    context.close()
```

---

## 3. File-by-File Consolidation Plan

### 3.1 `test_ds_rendering.py` — 20 tests → 3 tests

| Current | Tests | Setup | Consolidation |
|---------|------:|------:|---------------|
| `TestDataSourceRendering` | 8 | 8×5s = 40s | → 1 test with all 8 assertions |
| `TestSegmentedControl` | 5 | 5×5s = 25s | → 1 test: mode cycling with intermediate assertions |
| `TestModeSwitching` | 7 | 7×5s = 35s | → 1 test: mode content toggling with assertions |
| **Total** | **20** | **~100s** | **3 tests, ~15s** |

**Savings**: ~85s (17 eliminated setups × 5s)

### 3.2 `test_ds_parser_config.py` — 33 tests → 6 tests

| Current | Tests | Setup | Consolidation |
|---------|------:|------:|---------------|
| `TestFileLocationInputs` | 8 | 8×5s = 40s | → 1 test with all label/input checks |
| `TestParsingStrategy` | 5 | 5×5s = 25s | → 1 test: strategy cycling |
| `TestVariablesSection` | 10 | 10×5s = 50s | → 1 test: all element visibility checks |
| `TestConfigPreview` | 7 | 7×5s = 35s | → 2 tests: static checks + dynamic update checks |
| `TestParseButton` | 6 | 6×5s = 30s | → 1 test: visibility + error scenarios |
| **Total** | **33** | **~180s** | **6 tests, ~30s** |

**Savings**: ~150s (27 eliminated setups × ~5s)

### 3.3 `test_ds_csv_recent.py` — 14 tests → 3 tests

| Current | Tests | Setup | Consolidation |
|---------|------:|------:|---------------|
| `TestCSVMode` | 5 | 5×5s = 25s | → 1 test: all CSV mode checks |
| `TestRecentMode` | 4 | 4×5s = 20s | → 1 test: all Recent mode checks |
| `TestCrossModeIsolation` | 5 | 5×5s = 25s | → 1 test: full round-trip |
| **Total** | **14** | **~70s** | **3 tests, ~15s** |

**Savings**: ~55s

### 3.4 `test_ds_add_variable.py` — 18 tests → 4 tests

| Current | Tests | Setup | Consolidation |
|---------|------:|------:|---------------|
| `TestAddVariableDialogLifecycle` | 6 | 6×5s = 30s | → 1 test: open/close/reopen cycle |
| `TestAddVariableDialogSearch` | 3 | 3×5s = 15s | → 1 test: search mode checks |
| `TestAddVariableDialogManual` | 7 | 7×5s = 35s | → 1 test: manual entry workflow |
| `TestAddVariableDialogValidation` | 2 | 2×5s = 10s | → 1 test: validation checks |
| **Total** | **18** | **~90s** | **4 tests, ~20s** |

**Savings**: ~70s

### 3.5 `test_ds_screenshots.py` — 10 tests → 2-3 tests

| Current | Tests | Setup | Consolidation |
|---------|------:|------:|---------------|
| `TestDataSourceScreenshots` | 10 | 10×5s = 50s | → 2-3 tests grouped by mode |
| **Total** | **10** | **~50s** | **3 tests, ~15s** |

**Savings**: ~35s

### 3.6 `test_data_managers.py` — 11 tests → 3 tests

| Current | Tests | Setup | Consolidation |
|---------|------:|------:|---------------|
| `TestDataManagersNoData` | 2 | 2×5s = 10s | → 1 test with both assertions |
| `TestDataManagersTabs` | 3+6p | 9×5s = 45s | → 1 test: tab cycling + presence |
| `TestDataManagersScreenshots` | 3 | 3×5s = 15s | → 1 test: all screenshots |
| **Total** | **11** | **~70s** | **3 tests, ~15s** |

**Savings**: ~55s

### 3.7 `test_e2e_parse_workflow.py` — 31 tests → 8-10 tests

This is the most complex file. Consolidation requires careful state management:

| Current | Tests | Setup | Consolidation |
|---------|------:|------:|---------------|
| `TestScanWorkflow` | 5 | 5×15s = 75s | Keep 5 (each uses different test data) |
| `TestVariableConfiguration` | 5 | 5×20s = 100s | → 2 tests: scan+add and manual+add |
| `TestParseWorkflow` | 5 | 5×30s = 150s | → 2 tests: success + error scenarios |
| `TestParseToDataManagers` | 4 | 4×35s = 140s | → **1 test** (biggest savings!) |
| `TestSeedsReducerNoSeedColumn` | 1 | 1×35s = 35s | Absorb into ParseToDataManagers |
| `TestOutlierRemover` | 2 | 2×35s = 70s | → 1 test |
| `TestPreprocessor` | 2 | 2×35s = 70s | → 1 test |
| `TestMixer` | 2 | 2×35s = 70s | → 1 test |
| `TestParseAndRecentPool` | 1 | 1×30s = 30s | Keep 1 |
| `TestE2EScreenshots` | 4 | 4×25s = 100s | → 2 tests |
| **Total** | **31** | **~840s** | **10 tests, ~200s** |

**Savings**: ~640s (!)

### 3.8 `test_navigation.py` — 3 tests → 2 tests

| Current → Consolidated |
|------------------------|
| `test_navigate_all_pages` + `test_return_to_home` → 1 combined navigation test |
| `test_generate_navigation_gif` → Keep as-is (GIF generation) |

**Savings**: ~10s

### 3.9 `test_remaining_pages.py` — 8 tests → 3 tests

| Current | Tests | Consolidation |
|---------|------:|---------------|
| `TestManagePlots` | 3 | → 1 test |
| `TestPortfolio` | 2 | → 1 test |
| `TestPerformance` | 3 | → 1 test |

**Savings**: ~25s

---

## 4. Summary

| File | Before | After | Saved Time |
|------|-------:|------:|-----------:|
| `test_ds_rendering.py` | 20 | 3 | ~85s |
| `test_ds_parser_config.py` | 33 | 6 | ~150s |
| `test_ds_csv_recent.py` | 14 | 3 | ~55s |
| `test_ds_add_variable.py` | 18 | 4 | ~70s |
| `test_ds_screenshots.py` | 10 | 3 | ~35s |
| `test_data_managers.py` | 11 | 3 | ~55s |
| `test_e2e_parse_workflow.py` | 31 | 10 | ~640s |
| `test_navigation.py` | 3 | 2 | ~10s |
| `test_remaining_pages.py` | 8 | 3 | ~25s |
| **TOTAL** | **148** | **37** | **~1125s** |

**That's a 75% reduction in test count and ~18+ minutes of saved execution time.**

---

## 5. Implementation Notes

### 5.1 Ordering Strategy

Tests within a class execute top-to-bottom. Use `pytest-order` markers
or rely on pytest's deterministic ordering:

```python
class TestDataSourceRendering:
    """Consolidated test class — tests run in definition order."""

    def test_page_loads_and_renders(self, shared_page, live_server_url):
        """First test: navigate and verify initial state."""
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        # All 8 assertions from the original class
        ...

    def test_mode_cycling(self, shared_page, live_server_url):
        """Second test: mode switching (page already loaded)."""
        ds = DataSourcePage(shared_page)
        # No navigation needed — page already loaded from test above
        ...
```

### 5.2 Test Independence vs. Performance

**Trade-off**: Consolidated tests are NOT independent. If test 1 fails,
tests 2-N in the same class may fail cascade. This is acceptable because:
1. These are visual/E2E tests (already slow, already ordered)
2. The consolidated tests are semantically related
3. We can use `@pytest.mark.dependency` to skip dependent tests
4. CI already runs sequential visual tests

### 5.3 Screenshot Tests Stay Separate

Screenshot tests can be consolidated into fewer tests, but each
screenshot should still be captured. Group by mode/state.

### 5.4 conftest.py Changes

Add the `shared_page` fixture to conftest.py as class-scoped:

```python
@pytest.fixture(scope="class")
def shared_page(
    browser: Browser,
    browser_context_args: dict[str, object],
) -> Generator[Page, None, None]:
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    yield page
    context.close()
```
