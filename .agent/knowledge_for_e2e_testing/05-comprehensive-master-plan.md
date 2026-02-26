# RING-5 E2E Testing — Comprehensive Master Plan

> **Version**: 1.0
> **Status**: PLANNING (awaiting approval)
> **Scope**: Test consolidation, Seeds Reducer refactoring, Manage Plots testing

---

## Executive Summary

This plan covers 5 phases of work:

| Phase | Description                               | Estimated Effort | Priority |
| ----- | ----------------------------------------- | ---------------- | -------- |
| **A** | Test Consolidation                        | 3-4 hours        | HIGH     |
| **B** | Seeds Reducer → Generic Reducer           | 2-3 hours        | MEDIUM   |
| **C** | Manage Plots POM Expansion                | 2-3 hours        | HIGH     |
| **D** | Manage Plots E2E Tests (Tier 1)           | 4-6 hours        | HIGH     |
| **E** | Manage Plots E2E Tests (Tier 2: Advanced) | 4-6 hours        | MEDIUM   |

**Total**: ~15-22 hours of implementation

---

## Phase A: Test Consolidation

**Goal**: Reduce 148 tests to ~37, saving ~18+ minutes of execution time.

### A.1 — Add `shared_page` Fixture to conftest.py

Create a class-scoped page fixture alongside the existing function-scoped one:

```python
@pytest.fixture(scope="class")
def shared_page(browser, browser_context_args):
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    yield page
    context.close()
```

### A.2 — Consolidate `test_ds_rendering.py` (20 → 3 tests)

Merge three classes into workflow-style tests:

1. `test_initial_rendering` — All 8 rendering assertions in one test
2. `test_segmented_control_cycling` — All 5 mode cycling assertions
3. `test_mode_content_switching` — All 7 mode content assertions

### A.3 — Consolidate `test_ds_parser_config.py` (33 → 6 tests)

Merge five sections:

1. `test_file_location_inputs` — 8 assertions
2. `test_parsing_strategy` — 5 assertions
3. `test_variables_section` — 10 assertions
4. `test_config_preview_static` — 5 assertions
5. `test_config_preview_dynamic` — 2 assertions (changes reflected)
6. `test_parse_button_behavior` — 6 assertions

### A.4 — Consolidate `test_ds_csv_recent.py` (14 → 3 tests)

1. `test_csv_mode_elements` — 5 assertions
2. `test_recent_mode_elements` — 4 assertions
3. `test_cross_mode_isolation` — 5 assertions (round-trip)

### A.5 — Consolidate `test_ds_add_variable.py` (18 → 4 tests)

1. `test_dialog_lifecycle` — open/close/reopen/escape cycle
2. `test_search_mode` — warning + search + pill checks
3. `test_manual_entry_workflow` — switch/fill/config/back
4. `test_validation_and_add` — error/success scenarios

### A.6 — Consolidate `test_ds_screenshots.py` (10 → 3 tests)

1. `test_parse_mode_screenshots` — initial, config-aware, paths, error
2. `test_other_mode_screenshots` — CSV, Recent, segmented control
3. `test_dialog_screenshots` — Add Variable (search + manual)

### A.7 — Consolidate `test_data_managers.py` (11 → 3 tests)

1. `test_no_data_state` — header + warning
2. `test_tabs_and_switching` — all 7 tabs visible + switch cycle
3. `test_screenshots` — all 3 screenshot captures

### A.8 — Consolidate `test_e2e_parse_workflow.py` (31 → 10 tests)

This is the biggest file. Keep scan tests separate (different data paths):

1. `test_scan_single_stats` (keep)
2. `test_scan_histogram` (keep)
3. `test_scan_multi_cpu` (keep)
4. `test_scan_benchmarks` (keep)
5. `test_scan_error` (keep)
6. `test_variable_add_and_configure` — merge 5 var config tests
7. `test_parse_success_and_data_managers` — merge parse + DM checks
8. `test_parse_error_scenarios` — merge error tests
9. `test_data_manager_operations` — merge outlier + preprocessor + mixer + seeds
10. `test_e2e_screenshots` — merge 4 screenshot tests

### A.9 — Consolidate `test_navigation.py` (3 → 2 tests)

1. `test_navigate_all_pages_and_return` — merge navigation + return
2. `test_navigation_gif` — keep GIF generation

### A.10 — Consolidate `test_remaining_pages.py` (8 → 3 tests)

1. `test_manage_plots_empty` — header + warning + screenshot
2. `test_portfolio_page` — header + screenshot
3. `test_performance_page` — header + cache stats + screenshot

### A.11 — Verify All Consolidated Tests Pass

Run full test suite, ensure 37 tests pass with same coverage.

---

## Phase B: Seeds Reducer → Generic Reducer

**Goal**: Replace `random_seed` hard gate with generic column selector.

### B.1 — Update `seeds_reducer.py` UI

- Remove hard gate (L43-52)
- Add `st.selectbox("Column to reduce over")` with auto-detection
- Pre-select `random_seed` when present (backward compatibility)
- Update help text to be generic

### B.2 — Rename Identifiers

- Class: `SeedsReducerManager` → `ReducerManager`
- Tab label: `"Seeds Reducer"` → `"Reducer"` (in `data_managers.py`)
- Buttons: "Apply Seeds Reducer" → "Apply Reducer"
- Preview key: `"seeds_reduction"` → `"column_reduction"`

### B.3 — Update `data_managers.py` Registration

- Import rename
- Tab label change

### B.4 — Update `outlier_remover.py` Smart Defaults

- Generalize `random_seed` exclusion logic

### B.5 — Update POM (`data_managers_page.py`)

- Rename locators and add new `reducer_target_column_selectbox`
- Update assertion methods

### B.6 — Update E2E Tests

- `TestSeedsReducerNoSeedColumn` → `TestReducerGenericColumn`
- Update assertions for new warning text

### B.7 — Update Unit/UI Tests

- Any tests referencing Seeds Reducer widgets

### B.8 — Quality Gate

- Architecture boundary check
- Type check (mypy)
- Format (black)
- Lint (flake8)

---

## Phase C: Manage Plots POM Expansion

**Goal**: Expand `ManagePlotsPage` POM from 82 to ~500+ lines with comprehensive locators.

### C.1 — Create Section

```python
# Locators
@property
def plot_name_input(self) -> Locator  # already exists
@property
def plot_type_selectbox(self) -> Locator
@property
def create_button(self) -> Locator  # already exists

# Actions
def create_plot(self, name: str, plot_type: str) -> None
def assert_create_form_visible(self) -> None
```

### C.2 — Selector Section

```python
@property
def plot_selector_pills(self) -> Locator
def select_plot(self, name: str) -> None
def assert_plot_selected(self, name: str) -> None
def get_plot_count(self) -> int
```

### C.3 — Controls Section

```python
@property
def rename_input(self) -> Locator
@property
def save_pipe_button(self) -> Locator
@property
def load_pipe_button(self) -> Locator
@property
def delete_button(self) -> Locator
@property
def duplicate_button(self) -> Locator

def rename_plot(self, new_name: str) -> None
def delete_current_plot(self) -> None
def duplicate_current_plot(self) -> None
```

### C.4 — Pipeline Editor Section

```python
@property
def shaper_selectbox(self) -> Locator
@property
def add_to_pipeline_button(self) -> Locator
@property
def finalize_button(self) -> Locator
@property
def pipeline_steps(self) -> Locator  # expanders

def add_shaper(self, shaper_name: str) -> None
def finalize_pipeline(self) -> None
def get_pipeline_step_count(self) -> int
def assert_pipeline_empty(self) -> None
def assert_finalize_button_visible(self) -> None
```

### C.5 — Visualization Section

```python
@property
def plot_type_selector(self) -> Locator
@property
def x_axis_selectbox(self) -> Locator
@property
def y_axis_selectbox(self) -> Locator
@property
def auto_refresh_toggle(self) -> Locator
@property
def refresh_button(self) -> Locator
@property
def engine_selector(self) -> Locator
@property
def plotly_chart(self) -> Locator  # already exists
@property
def advanced_settings_toggle(self) -> Locator
@property
def settings_pills(self) -> Locator

def select_x_axis(self, column: str) -> None
def select_y_axis(self, column: str) -> None
def refresh_plot(self) -> None
def switch_engine(self, engine: str) -> None  # "plotly" | "matplotlib"
def assert_chart_visible(self) -> None  # already exists
def assert_no_data_warning(self) -> None
```

### C.6 — Download Section

```python
@property
def download_expander(self) -> Locator
@property
def download_format_pills(self) -> Locator
@property
def download_button(self) -> Locator

def download_plot(self, format: str) -> Download
def assert_download_section_visible(self) -> None
```

### C.7 — Shaper Configuration Widgets

For each shaper type, create configuration methods:

```python
# Column Selector
def configure_column_selector(self, columns: list[str]) -> None
# Sort
def configure_sort(self, column: str, order: str) -> None
# Filter
def configure_filter(self, column: str, operator: str, value: str) -> None
# etc.
```

### C.8 — Workspace Management

```python
@property
def export_path_input(self) -> Locator
@property
def export_format_selectbox(self) -> Locator
@property
def download_all_button(self) -> Locator

def assert_workspace_management_visible(self) -> None
```

---

## Phase D: Manage Plots E2E Tests — Tier 1 (Core Functionality)

**Goal**: Test the critical happy paths for plot creation and rendering.

### D.1 — Shared Fixture: Parsed Data

Create a class-scoped fixture that prepares data via the parse workflow:

```python
@pytest.fixture(scope="class")
def page_with_data(browser, browser_context_args, live_server_url):
    """Browser page with parsed gem5 data loaded."""
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    ds = DataSourcePage(page)
    ds.goto_and_wait(live_server_url)
    ds.fill_stats_path("[synthetic data path]")
    ds.scan_and_wait()
    ds.add_variable_from_scan(0)
    ds.parse_and_wait()
    ds.close_parse_dialog_and_reload()
    yield page
    context.close()
```

### D.2 — Test: No-Data State

```python
class TestManagePlotsNoData:
    def test_page_renders_without_data(self, shared_page, live_server_url):
        # Navigate to Manage Plots without loading data
        # Assert warning shown, create form may be visible but pipeline/viz not
```

### D.3 — Test: Create Plot

```python
class TestCreatePlot:
    def test_create_bar_plot(self, page_with_data, live_server_url):
        # Navigate to Manage Plots
        # Fill name, select "bar" type, click Create
        # Assert plot appears in selector pills
        # Assert pipeline section visible
```

### D.4 — Test: Pipeline Configuration

```python
class TestPipelineWorkflow:
    def test_add_column_selector_and_finalize(self, page_with_data):
        # Create plot → Add "Column Selector" shaper
        # Configure columns
        # Click Finalize
        # Assert visualization section appears
```

### D.5 — Test: Chart Rendering (Bar)

```python
class TestChartRendering:
    def test_bar_chart_renders(self, page_with_data):
        # Full workflow: Create → Pipeline → Configure X/Y → Refresh
        # Assert Plotly chart visible
```

### D.6 — Test: Chart Rendering (All 8 Types)

Parametrize across plot types for basic rendering verification:

```python
@pytest.mark.parametrize("plot_type", [
    "bar", "line", "scatter", "grouped_bar",
    "stacked_bar", "histogram",
])
def test_plot_type_renders(self, page_with_data, plot_type):
    # Create plot of type → Pipeline → Config → Render
    # Assert chart visible
```

Note: `grouped_stacked_bar` and `dual_axis_bar_dot` require special config.

### D.7 — Test: Plot Controls (Rename, Delete, Duplicate)

```python
class TestPlotControls:
    def test_rename_plot(self, page_with_data):
    def test_duplicate_plot(self, page_with_data):
    def test_delete_plot(self, page_with_data):
```

### D.8 — Test: Engine Switching

```python
class TestEngineSwitching:
    def test_switch_to_matplotlib(self, page_with_data):
        # After chart renders in Plotly, switch to Matplotlib
        # Assert matplotlib chart visible (st.pyplot canvas)
    def test_switch_back_to_plotly(self, page_with_data):
```

### D.9 — Screenshots

Capture key screenshots for documentation:

- Empty state
- Plot creation form
- Pipeline editor with steps
- Bar chart rendered
- Multiple plots

---

## Phase E: Manage Plots E2E Tests — Tier 2 (Advanced)

**Goal**: Test advanced features, edge cases, and cross-cutting concerns.

### E.1 — Test: Download Section

```python
class TestDownload:
    def test_download_png(self, page_with_data):
        # Render chart → Open download expander → Select PNG → Download
        # Assert file downloaded with correct extension
    def test_download_svg(self, page_with_data):
    def test_download_pdf_matplotlib(self, page_with_data):
```

### E.2 — Test: Pipeline Manipulation

```python
class TestPipelineManipulation:
    def test_reorder_pipeline_steps(self, page_with_data):
        # Add two shapers → Reorder → Verify order changed
    def test_remove_pipeline_step(self, page_with_data):
        # Add shaper → Remove → Verify removed
    def test_multiple_shapers(self, page_with_data):
        # Add Column Selector + Sort → Finalize → Verify
```

### E.3 — Test: Advanced Settings

```python
class TestAdvancedSettings:
    def test_advanced_toggle(self, page_with_data):
        # Enable advanced settings → Check new pills appear
    def test_settings_pills_navigation(self, page_with_data):
        # Click through Layout, Typography, Legends, Axes pills
```

### E.4 — Test: Save/Load Pipeline

```python
class TestPipelinePersistence:
    def test_save_pipeline(self, page_with_data):
        # Configure pipeline → Click "Save Pipe" → Enter name → Save
    def test_load_pipeline(self, page_with_data):
        # Create new plot → Click "Load Pipe" → Select → Load
```

### E.5 — Test: Multiple Plots

```python
class TestMultiplePlots:
    def test_create_multiple_plots(self, page_with_data):
        # Create 3 plots → Switch between them → Each has independent config
    def test_workspace_management(self, page_with_data):
        # With multiple plots → Test "Download All" button
```

### E.6 — Test: Error Handling

```python
class TestPlotErrors:
    def test_invalid_axis_columns(self, page_with_data):
    def test_empty_pipeline_finalize(self, page_with_data):
    def test_duplicate_plot_name(self, page_with_data):
```

### E.7 — Test: Shaper-Specific Configurations

```python
class TestShaperConfigs:
    def test_column_selector_config(self, page_with_data):
    def test_sort_config(self, page_with_data):
    def test_filter_config(self, page_with_data):
    def test_normalize_config(self, page_with_data):
    def test_mean_calculator_config(self, page_with_data):
```

---

## Implementation Sequence

```
Phase A (consolidation) ──prerequisite──▶ Phase B (seeds reducer)
                              │
                              ├──▶ Phase C (POM expansion) ──▶ Phase D (manage plots Tier 1)
                              │                                      │
                              │                                      ▼
                              │                               Phase E (manage plots Tier 2)
                              │
                              └──▶ Update rules & workflows
```

**Recommended execution order**:

1. **A** first (consolidation) — improves test speed, establishes patterns
2. **C** next (POM) — infrastructure for all Manage Plots tests
3. **B** in parallel or after A (seeds reducer) — independent work
4. **D** after C (Tier 1 tests) — core functionality coverage
5. **E** last (Tier 2 tests) — advanced features after core is solid

---

## Quality Gate (After Each Phase)

```bash
# Architecture check
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__

# Type + format + lint
./python_venv/bin/mypy src/ --show-error-codes
./python_venv/bin/black --check src/ tests/
./python_venv/bin/flake8 src/ tests/

# Tests
./python_venv/bin/pytest tests/visual/ -m requires_browser -v
```

---

## Risk Register

| Risk                                 | Phase | Likelihood | Impact | Mitigation                         |
| ------------------------------------ | ----- | ---------- | ------ | ---------------------------------- |
| Consolidated tests cascade-fail      | A     | Medium     | Low    | Use `@pytest.mark.dependency`      |
| Class-scoped page leaks state        | A     | Low        | Medium | Test cleanup in fixture teardown   |
| Seeds Reducer rename breaks imports  | B     | Medium     | Low    | Global search-replace + tests      |
| Manage Plots POM locators fragile    | C     | Medium     | Medium | Use `_by_label()` pattern          |
| Plot rendering timeout in CI         | D     | Medium     | High   | Generous timeouts, retry decorator |
| Matplotlib needs LaTeX for PGF       | E     | High       | Low    | Skip PGF tests without LaTeX       |
| Singleton state between test classes | D,E   | Medium     | Medium | Document state requirements        |

---

## Success Criteria

1. **Phase A complete**: 37 tests pass with ≤5 minutes total execution
2. **Phase B complete**: Reducer works with any column, `random_seed` auto-detected
3. **Phase C complete**: ManagePlotsPage POM covers all interactive widgets
4. **Phase D complete**: 8 plot types render, CRUD operations work, screenshots captured
5. **Phase E complete**: Downloads, pipeline save/load, advanced settings verified
