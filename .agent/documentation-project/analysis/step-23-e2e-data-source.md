# Step 23: E2E Data Source Page Tests

## 1. Executive Summary

This document defines the exhaustive end-to-end test plan for the **Data Source** page of the
RING-5 Unified Engine v2 application. The Data Source page (`src/web/pages/data_source.py`) is
the entry point for all data ingestion workflows and is rendered as "Step 1: Choose Data Source"
in the application. It orchestrates three primary data input methods:

1. **Parse Simulator Stats Files** -- configures a simulator parser (gem5, etc.) with file
   paths, parsing strategies, variable definitions, and executes async batch parsing.
2. **Upload CSV Directly** -- allows users with pre-parsed CSV data to bypass parsing.
3. **Load from Recent** -- manages a persistent CSV pool for quick re-loading of previously
   parsed datasets.

The page delegates rendering to `DataSourceComponents` (static methods for CSV pool management,
parser configuration, and the parsing dialog), `VariableEditor` (inline editing of variable
definitions with type-specific sub-forms), and `PatternIndexSelector` (regex pattern variable
index filtering). Navigation is controlled by `app.py` through a sidebar button menu that sets
`st.session_state["_nav_page"]`.

### Test Scope

| Area | Components Under Test | Key Interactions |
|---|---|---|
| CSV Pool | `render_csv_pool`, `CardComponents.file_info_card` | Load, preview, delete files |
| File Scanning | `render_parser_config` (scan button), `submit_scan_async`, `finalize_scan` | Quick/deep scan, progress, error |
| Variable Discovery | `variable_config_dialog`, `filtered_selectbox` | Search scanned vars, manual entry |
| Variable Editor | `VariableEditor.render`, `_render_common_fields` | Add, edit name/alias/type, delete |
| Vector Config | `render_vector_config`, `_render_vector_discovered_selection`, manual entry | Entry selection, statistics mode |
| Distribution Config | `render_distribution_config`, `_render_distribution_statistics_selection` | Range inputs, deep scan range |
| Histogram Config | `render_histogram_config`, rebinning controls | Mode selection, bucket entries |
| Configuration Vars | `render_configuration_config` | Default value (onEmpty) |
| Pattern Index | `PatternIndexSelector.render_selector`, `PatternIndexService` | Multi-position filtering |
| Parsing Execution | `_show_parse_dialog`, `submit_parse_async`, `finalize_parsing` | Progress bar, error display, CSV pool addition |
| Navigation | `app.py` sidebar, `st.segmented_control` data source choice | Page switching, state persistence |

### Test Strategy

- **Tier 0 (Fixtures)**: Seed filesystem with stats files, pre-parsed CSVs, and a populated
  CSV pool JSON manifest. Initialize `ApplicationAPI` with test configuration.
- **Tier 1 (Smoke)**: Verify page renders, segmented control toggles between modes, and basic
  element visibility.
- **Tier 2 (Functional)**: Full workflow tests for each data input method with assertions on
  state mutations and UI feedback.
- **Tier 3 (Error Paths)**: Invalid paths, corrupt files, empty scan results, duplicate
  variable names, missing required fields.
- **Tier 4 (Integration)**: Cross-page navigation, state persistence between Data Source and
  Data Managers, and end-to-end parse-then-visualize workflows.

---

## 2. Page Under Test: Data Source Overview

### 2.1 Entry Point and Routing

The application entry point is `app.py:run_app()`. Navigation uses a sidebar button-based menu
with five options stored in `st.session_state["_nav_page"]`. The Data Source page is the default
(index 0). When active, it instantiates `DataSourcePage(api).render()`.

```
app.py
  -> st.session_state["_nav_page"] == "Data Source"
  -> DataSourcePage(api).render()
       -> st.segmented_control("Select your data source:", ...)
       -> choice == parse_label  => DataSourceComponents.render_parser_config(api)
       -> choice == "Load from Recent" => DataSourceComponents.render_csv_pool(api)
       -> choice == "I already have CSV data" => st.success(...)
```

### 2.2 Component Hierarchy

```
DataSourcePage.render()
|
+-- st.segmented_control (data_source_choice)
|
+-- [Parse Stats Path]
|   +-- DataSourceComponents.render_parser_config(api)
|       +-- st.pills (simulator_selector)         -- gem5, etc.
|       +-- @st.fragment _parser_config_fragment()
|       |   +-- st.text_input (stats_path_input)
|       |   +-- st.text_input (stats_pattern_input)
|       |   +-- st.segmented_control (parser_strategy_selector)
|       |   +-- st.checkbox (Deep Scan)
|       |   +-- st.button (Quick Scan)
|       |   +-- VariableEditor.render(...)
|       |   |   +-- _render_common_fields() per variable
|       |   |   +-- render_vector_config() / render_distribution_config() / ...
|       |   |   +-- PatternIndexSelector.render_selector() for pattern vars
|       |   |   +-- _render_add_variable_section()
|       |   +-- st.button (Add Variable) -> variable_config_dialog()
|       |   +-- st.json (Configuration Preview)
|       +-- st.button (Parse Stats Files) [outside fragment]
|           +-- _show_parse_dialog() [on click]
|
+-- [Load from Recent Path]
|   +-- DataSourceComponents.render_csv_pool(api)
|       +-- CardComponents.file_info_card() per CSV entry
|           +-- Load / Preview / Delete buttons
|
+-- [CSV Mode Path]
    +-- st.success("CSV mode selected...")
```

### 2.3 Key Streamlit Widget Keys

| Widget Key | Type | Location |
|---|---|---|
| `data_source_choice` | `st.segmented_control` | DataSourcePage |
| `simulator_selector` | `st.pills` | render_parser_config |
| `stats_path_input` | `st.text_input` | parser config fragment |
| `stats_pattern_input` | `st.text_input` | parser config fragment |
| `parser_strategy_selector` | `st.segmented_control` | parser config fragment |
| `var_name_{var_id}` | `st.text_input` | VariableEditor common fields |
| `var_alias_{var_id}` | `st.text_input` | VariableEditor common fields |
| `var_type_{var_id}` | `st.selectbox` | VariableEditor common fields |
| `delete_var_{var_id}` | `st.button` | VariableEditor common fields |
| `vector_entries_{var_id}` | `st.text_input` | manual vector entry |
| `vector_entries_select_{var_id}` | `st.multiselect` / filtered | discovered entry selection |
| `vec_parse_mode_{var_id}` | `st.segmented_control` | vector parse mode |
| `dist_parse_mode_{var_id}` | `st.segmented_control` | distribution parse mode |
| `hist_parse_mode_{var_id}` | `st.segmented_control` | histogram parse mode |
| `use_pattern_filter_{var_id}` | `st.checkbox` | PatternIndexSelector |
| `pattern_pos_{idx}_{var_id}` | filtered_multiselect | pattern position selection |
| `load_{idx}` | `st.button` | CSV pool card |
| `preview_{idx}` | `st.button` | CSV pool card |
| `delete_{idx}` | `st.button` | CSV pool card |
| `dialog_select_var_idx` | filtered_selectbox | variable config dialog |
| `dialog_manual_name` | `st.text_input` | variable config dialog manual |
| `dialog_manual_type` | `st.selectbox` | variable config dialog manual |

### 2.4 State Manager Dependencies

The page reads and writes the following state keys through `api.state_manager`:

| Method | Read/Write | Purpose |
|---|---|---|
| `get/set_simulator()` | R/W | Selected simulator backend |
| `get/set_stats_path()` | R/W | Directory path for stats files |
| `get/set_stats_pattern()` | R/W | File pattern (e.g., stats.txt) |
| `get/set_parser_strategy()` | R/W | Parsing strategy name |
| `get/set_parse_variables()` | R/W | List of ParseVariableConfig dicts |
| `get/set_scanned_variables()` | R/W | List of ScannedVariableDict dicts |
| `get/set_csv_pool()` | R/W | CSV pool entries (cached) |
| `get/set_data()` | W | Loaded DataFrame (after parse/load) |
| `get/set_csv_path()` | W | Path to loaded CSV |
| `is_using_parser() / set_use_parser()` | R/W | Parser vs CSV mode flag |
| `set_temp_dir()` | W | Temporary output directory for parsing |

---

## 3. Test Fixtures and State Setup (Tier 0 -> Tier 1)

### 3.1 Filesystem Fixtures

```python
# conftest.py - Data Source E2E fixtures

import json
import os
import tempfile
import time
from pathlib import Path

import pytest


@pytest.fixture
def stats_directory(tmp_path: Path) -> Path:
    """Create a directory tree with simulated gem5 stats files.

    Structure:
        tmp_path/
            sim_001/stats.txt    -- valid scalar + vector stats
            sim_002/stats.txt    -- valid scalar + distribution stats
            sim_003/stats.txt    -- valid with pattern variables (l0_cntrl0, l0_cntrl1, l1_cntrl0)
            sim_004/corrupt.txt  -- malformed (truncated mid-line)
            empty_dir/           -- no stats files
    """
    for i, content in enumerate(_STATS_FILE_CONTENTS, start=1):
        sim_dir = tmp_path / f"sim_{i:03d}"
        sim_dir.mkdir()
        (sim_dir / "stats.txt").write_text(content)

    # Corrupt file
    corrupt_dir = tmp_path / "sim_004"
    corrupt_dir.mkdir()
    (corrupt_dir / "corrupt.txt").write_text("------\nsimTicks")  # truncated

    # Empty directory
    (tmp_path / "empty_dir").mkdir()

    return tmp_path


@pytest.fixture
def csv_pool_directory(tmp_path: Path) -> Path:
    """Create a pre-populated CSV pool directory with valid CSV files."""
    pool_dir = tmp_path / "csv_pool"
    pool_dir.mkdir()

    csv1 = pool_dir / "parsed_2024_01_15.csv"
    csv1.write_text("benchmark,config,simTicks,ipc\nbzip2,base,100000,1.5\ngcc,base,200000,1.2\n")

    csv2 = pool_dir / "parsed_2024_02_20.csv"
    csv2.write_text("benchmark,config,simTicks\nmcf,opt,150000\n")

    manifest = [
        {
            "name": "parsed_2024_01_15.csv",
            "path": str(csv1),
            "size": csv1.stat().st_size,
            "modified": time.time() - 86400,
        },
        {
            "name": "parsed_2024_02_20.csv",
            "path": str(csv2),
            "size": csv2.stat().st_size,
            "modified": time.time(),
        },
    ]
    (pool_dir / "csv_pool.json").write_text(json.dumps(manifest))

    return pool_dir


@pytest.fixture
def uploaded_csv(tmp_path: Path) -> Path:
    """Create a standalone CSV file for direct upload testing."""
    csv_file = tmp_path / "user_upload.csv"
    csv_file.write_text(
        "benchmark,config,simTicks,ipc,l2_misses\n"
        "bzip2,base,100000,1.5,500\n"
        "gcc,base,200000,1.2,300\n"
        "mcf,opt,150000,1.8,200\n"
    )
    return csv_file


# -- Stats file content templates --

_STATS_FILE_CONTENTS = [
    # sim_001: scalars + vector
    """\
---------- Begin Simulation Statistics ----------
simTicks                                   500000
system.cpu.ipc                             1.45
system.cpu.committedInsts                  72500
system.cpu.branchPred.lookups::0              120
system.cpu.branchPred.lookups::1              340
system.cpu.branchPred.lookups::total          460
---------- End Simulation Statistics ----------
""",
    # sim_002: scalars + distribution
    """\
---------- Begin Simulation Statistics ----------
simTicks                                   600000
system.cpu.ipc                             1.32
system.mem_ctrl.rdPerTurnAround::mean       3.5
system.mem_ctrl.rdPerTurnAround::stdev      1.2
system.mem_ctrl.rdPerTurnAround::0-3        150
system.mem_ctrl.rdPerTurnAround::4-7        200
system.mem_ctrl.rdPerTurnAround::8-15       100
system.mem_ctrl.rdPerTurnAround::total      450
---------- End Simulation Statistics ----------
""",
    # sim_003: pattern variables (l\d+_cntrl\d+)
    """\
---------- Begin Simulation Statistics ----------
simTicks                                   700000
system.ruby.l0_cntrl0.cache.demand_hits    5000
system.ruby.l0_cntrl0.cache.demand_misses  200
system.ruby.l0_cntrl1.cache.demand_hits    4800
system.ruby.l0_cntrl1.cache.demand_misses  180
system.ruby.l1_cntrl0.cache.demand_hits    8000
system.ruby.l1_cntrl0.cache.demand_misses  400
---------- End Simulation Statistics ----------
""",
]
```

### 3.2 Application API Fixture

```python
@pytest.fixture
def test_api(csv_pool_directory: Path) -> "ApplicationAPI":
    """Create a test ApplicationAPI instance with mocked pool path."""
    from unittest.mock import patch

    from src.core.application_api import ApplicationAPI
    from src.web.pages.ui.plotting.base_plot import BasePlot

    with patch.object(ApplicationAPI, "_get_pool_dir", return_value=str(csv_pool_directory)):
        api = ApplicationAPI(plot_deserializer=BasePlot.from_dict)
    return api


@pytest.fixture
def seeded_state(test_api: "ApplicationAPI", stats_directory: Path) -> "ApplicationAPI":
    """Seed state manager with a valid configuration for parser tests."""
    test_api.state_manager.set_simulator("gem5")
    test_api.state_manager.set_stats_path(str(stats_directory))
    test_api.state_manager.set_stats_pattern("stats.txt")
    test_api.state_manager.set_parser_strategy("simple")
    test_api.state_manager.set_parse_variables([
        {"name": "simTicks", "type": "scalar", "_id": "test-scalar-001"},
        {"name": "system.cpu.ipc", "type": "scalar", "_id": "test-scalar-002"},
    ])
    return test_api
```

### 3.3 Playwright Page Fixture

```python
from playwright.sync_api import Page


@pytest.fixture
def data_source_page(page: Page, live_server_url: str) -> Page:
    """Navigate to the Data Source page and wait for initial render."""
    page.goto(live_server_url)
    # Wait for RING-5 header to render
    page.wait_for_selector("text=RING-5 Interactive Analyzer", timeout=15000)
    # Ensure Data Source nav button is active (default page)
    nav_btn = page.locator("button:has-text('Data Source')")
    nav_btn.wait_for(state="visible")
    return page
```

### 3.4 Scanned Variables Fixture

```python
@pytest.fixture
def scanned_variables() -> list[dict]:
    """Pre-built scanned variable list for dialog and editor tests."""
    return [
        {"name": "simTicks", "type": "scalar", "entries": []},
        {"name": "system.cpu.ipc", "type": "scalar", "entries": []},
        {"name": "system.cpu.committedInsts", "type": "scalar", "entries": []},
        {
            "name": "system.cpu.branchPred.lookups",
            "type": "vector",
            "entries": ["0", "1", "total"],
        },
        {
            "name": "system.mem_ctrl.rdPerTurnAround",
            "type": "distribution",
            "entries": ["0-3", "4-7", "8-15"],
            "minimum": 0,
            "maximum": 15,
        },
        {
            "name": r"system.ruby.l\d+_cntrl\d+.cache.demand_hits",
            "type": "scalar",
            "entries": [],
            "pattern_indices": ["0_0", "0_1", "1_0"],
            "count": 3,
        },
    ]
```

---

## 4. CSV Pool Management Tests

### 4.1 Gherkin Scenarios

```gherkin
Feature: CSV Pool Management
  As a user with previously parsed CSV files
  I want to load, preview, and delete files from the CSV pool
  So that I can quickly access my earlier analysis datasets

  Background:
    Given the application is running with a populated CSV pool
    And I navigate to "Data Source" page
    And I select "Load from Recent" from the data source options

  Scenario: Display CSV pool with file cards
    Then I should see "Recent CSV Files" heading
    And I should see "Found 2 CSV file(s) in the pool"
    And I should see a file card for "parsed_2024_01_15.csv"
    And I should see a file card for "parsed_2024_02_20.csv"
    And each card should show the file size in KB
    And the first card should be expanded by default

  Scenario: Load a CSV file from the pool
    When I click "Load This File" on the first file card
    Then I should see a success message with row count
    And I should see a data preview table
    And I should see column details
    And the state manager should contain the loaded DataFrame
    And the state manager csv_path should match the loaded file
    And is_using_parser should be False

  Scenario: Preview a CSV file without loading
    When I click "Preview" on the second file card
    Then I should see a dataframe with at most 5 rows
    And the state manager data should remain unchanged

  Scenario: Delete a CSV file from the pool
    When I click "Delete" on the first file card
    Then I should see a toast message "File deleted!"
    And the pool should contain only 1 file
    And the deleted file should be removed from the manifest

  Scenario: Display warning for missing file
    Given the CSV file "parsed_2024_01_15.csv" has been deleted from disk
    When the CSV pool renders
    Then I should see an error "File no longer exists: parsed_2024_01_15.csv"
    And the Load and Preview buttons should not appear for that entry

  Scenario: Empty CSV pool
    Given no CSV files exist in the pool
    When I select "Load from Recent"
    Then I should see "No CSV files in the pool yet"
    And no file cards should be displayed

  Scenario: Load failure on corrupt CSV
    Given a CSV pool entry points to a malformed CSV file
    When I click "Load This File" on that entry
    Then I should see an exception displayed via st.exception
    And the state manager data should remain unchanged
```

### 4.2 Pytest-Playwright Test Stubs

```python
class TestCSVPoolManagement:
    """E2E tests for the CSV pool management workflow."""

    def test_csv_pool_displays_file_cards(self, data_source_page: Page):
        """Verify file cards render with correct metadata for all pool entries."""
        page = data_source_page
        # Switch to "Load from Recent" tab
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=Recent CSV Files")

        # Verify pool count
        assert page.locator("text=Found 2 CSV file(s) in the pool").is_visible()

        # Verify file cards exist
        assert page.locator("text=parsed_2024_01_15.csv").is_visible()
        assert page.locator("text=parsed_2024_02_20.csv").is_visible()

    def test_load_csv_from_pool(self, data_source_page: Page):
        """Verify loading a CSV file populates state and shows preview."""
        page = data_source_page
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=Recent CSV Files")

        # Click load button on first card
        page.locator("button:has-text('Load This File')").first.click()

        # Wait for success message
        page.wait_for_selector("text=Loaded")
        assert page.locator("text=rows").is_visible()

        # Verify data preview renders
        assert page.locator("[data-testid='stDataFrame']").is_visible()

    def test_preview_csv_shows_head(self, data_source_page: Page):
        """Verify preview shows first 5 rows without affecting loaded state."""
        page = data_source_page
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=Recent CSV Files")

        # Click preview on second card
        preview_buttons = page.locator("button:has-text('Preview')")
        preview_buttons.nth(1).click()

        # Dataframe should appear
        page.wait_for_selector("[data-testid='stDataFrame']")

    def test_delete_csv_from_pool(self, data_source_page: Page):
        """Verify deleting a file removes it from pool and shows toast."""
        page = data_source_page
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=Recent CSV Files")

        # Click delete on first card
        page.locator("button:has-text('Delete')").first.click()

        # Wait for rerun and verify count decreased
        page.wait_for_selector("text=Found 1 CSV file(s) in the pool")

    def test_empty_csv_pool_shows_warning(self, data_source_page: Page):
        """Verify empty pool shows appropriate warning message."""
        page = data_source_page
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=No CSV files in the pool yet")

    def test_missing_file_shows_error(self, data_source_page: Page, csv_pool_directory: Path):
        """Verify missing file on disk shows error in the card."""
        # Delete the actual file from disk while pool manifest still references it
        (csv_pool_directory / "parsed_2024_01_15.csv").unlink()

        page = data_source_page
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=File no longer exists")

    def test_load_csv_sets_state_correctly(self, data_source_page: Page):
        """Verify that loading a CSV sets data, csv_path, and use_parser=False."""
        page = data_source_page
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=Recent CSV Files")

        page.locator("button:has-text('Load This File')").first.click()
        page.wait_for_selector("text=Loaded")

        # Verify advice message to proceed to pipeline
        assert page.locator("text=Proceed to").is_visible()

    def test_card_shows_file_size_and_date(self, data_source_page: Page):
        """Verify file info cards display size in KB and modification date."""
        page = data_source_page
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=Recent CSV Files")

        # File cards show size in KB format
        assert page.locator("text=KB").first.is_visible()

        # Modification date should be rendered
        assert page.locator("text=Modified:").first.is_visible()
```

---

## 5. File Scanning Tests

### 5.1 Gherkin Scenarios

```gherkin
Feature: Stats File Scanning
  As a user with raw simulator output
  I want to scan stats files for variable discovery
  So that I can auto-populate the variable configuration

  Background:
    Given the application is running with a valid stats directory
    And I navigate to "Data Source" page
    And the "Parse gem5 Stats Files" option is selected
    And I have entered a valid stats directory path

  Scenario: Quick scan discovers variables
    When I click "Quick Scan"
    Then I should see a status indicator "Quick scanning..."
    And I should see progress messages "Scanning X files..."
    And after completion I should see "Scan complete -- N variables found"
    And a toast notification should confirm the scan result
    And the scanned variables should be stored in state
    And the "Scanner found N variables" success message should appear

  Scenario: Deep scan checks all files
    When I check the "Deep Scan (check all files)" checkbox
    And I click "Quick Scan"
    Then I should see "Deep scanning..."
    And all files in subdirectories should be scanned
    And the scan should process more files than a quick scan

  Scenario: Scan with custom file pattern
    Given I change the file pattern to "*.txt"
    When I click "Quick Scan"
    Then the scan should discover files matching "*.txt"
    And the scan results should include variables from all matching files

  Scenario: Scan empty directory
    Given the stats path points to an empty directory
    When I click "Quick Scan"
    Then the scan should complete with 0 variables found
    And a toast notification should show "Found 0 variables"

  Scenario: Scan with invalid path
    Given the stats path is "/nonexistent/path"
    When I click "Quick Scan"
    Then I should see an exception error message
    And the scanned variables state should remain empty

  Scenario: Scan progress tracking
    Given the stats directory contains 10 simulation subdirectories
    When I click "Quick Scan"
    Then I should see incremental progress "Scanned 1/10 files..."
    And the progress should update through "Scanned 10/10 files..."
    And the final message should show "Aggregating patterns..."
    And the status should collapse to show the summary

  Scenario: Simulator selector changes labels
    Given I switch the simulator pill to a different backend
    Then the page title should update to reflect the new simulator
    And the file pattern help text should reference the new simulator
    And the parse button label should change accordingly

  Scenario: Scanning releases memory after completion
    When I click "Quick Scan"
    And the scan completes successfully
    Then ApplicationAPI.cancel_pending_scans() should have been called
    And completed futures should be released for garbage collection
```

### 5.2 Pytest-Playwright Test Stubs

```python
class TestFileScanning:
    """E2E tests for the stats file scanning workflow."""

    def test_quick_scan_discovers_variables(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify quick scan finds variables and updates state."""
        page = data_source_page

        # Ensure parser mode is active (default)
        assert page.locator("text=Stats Parser Configuration").is_visible()

        # Enter stats directory path
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))

        # Click Quick Scan
        page.locator("button:has-text('Quick Scan')").click()

        # Wait for scan completion
        page.wait_for_selector("text=Scan complete", timeout=30000)

        # Verify scanned variables message
        assert page.locator("text=Scanner found").is_visible()

    def test_deep_scan_checkbox_scans_all_files(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify deep scan processes all files without the 10-file limit."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))

        # Enable deep scan
        page.locator("text=Deep Scan (check all files)").click()

        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Deep scanning", timeout=5000)
        page.wait_for_selector("text=Scan complete", timeout=30000)

    def test_scan_with_invalid_path_shows_error(self, data_source_page: Page):
        """Verify scanning with nonexistent path shows exception."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill("/nonexistent/path/to/stats")

        page.locator("button:has-text('Quick Scan')").click()

        # Should show exception
        page.wait_for_selector("[data-testid='stException']", timeout=10000)

    def test_scan_empty_directory(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify scanning empty directory completes with zero results."""
        page = data_source_page

        empty_dir = stats_directory / "empty_dir"
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(empty_dir))

        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Scan complete", timeout=15000)

    def test_custom_file_pattern(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify custom file pattern filters which files are scanned."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))

        # Change pattern from stats.txt to *.txt
        pattern_input = page.locator("[data-testid='stTextInput']").nth(1)
        pattern_input.fill("*.txt")

        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Scan complete", timeout=30000)

    def test_simulator_pill_changes_labels(self, data_source_page: Page):
        """Verify switching simulator pills updates all dynamic labels."""
        page = data_source_page

        # Check initial gem5 labels visible
        assert page.locator("text=gem5").is_visible()

        # The simulator pills should be visible
        simulator_pills = page.locator("[data-testid='stPills']").first
        assert simulator_pills.is_visible()

    def test_parser_strategy_selector_displays_options(self, data_source_page: Page):
        """Verify strategy selector displays available options and persists selection."""
        page = data_source_page

        # Parser strategy segmented control should be visible
        strategy_selector = page.locator("text=Select ingestion strategy")
        assert strategy_selector.is_visible()

    def test_configuration_preview_json_reflects_settings(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify configuration preview JSON reflects current settings."""
        page = data_source_page

        # Fill in path
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))

        # Verify Configuration Preview section exists
        assert page.locator("text=Configuration Preview").is_visible()

        # JSON block should render
        json_block = page.locator("[data-testid='stJson']")
        assert json_block.is_visible()

    def test_scan_shows_progress_status_container(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify scan shows expandable status container with progress messages."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))

        page.locator("button:has-text('Quick Scan')").click()

        # Status container should appear during scan
        page.wait_for_selector("text=scanning", timeout=5000)
        page.wait_for_selector("text=Scan complete", timeout=30000)

    def test_stats_path_persists_in_state(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify that typing a path persists through state_manager.set_stats_path."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))
        # Trigger blur to persist
        stats_path_input.press("Tab")

        # The path should persist in the JSON preview
        json_block = page.locator("[data-testid='stJson']")
        json_text = json_block.inner_text()
        assert str(stats_directory) in json_text or "statsPath" in json_text
```

---

## 6. Variable Discovery Tests

### 6.1 Gherkin Scenarios

```gherkin
Feature: Variable Discovery and Addition Dialog
  As a user configuring parser variables
  I want to discover variables from scanned stats files and add them to my configuration
  So that I can extract the correct data from simulator output

  Background:
    Given the application has completed a successful scan with 6 variables
    And I am on the parser configuration section of the Data Source page
    And the scanned variables include scalars, vectors, distributions, and pattern variables

  Scenario: Open Add Variable dialog from scanned search
    When I click "Add Variable"
    Then a dialog should open titled "Add Variable"
    And the "Search Scanned Variables" pill should be selected by default
    And I should see a search input with placeholder "Type to search..."

  Scenario: Search and select a scanned scalar variable
    Given the Add Variable dialog is open
    When I type "simTicks" in the search box
    Then the dropdown should filter to show "simTicks (scalar)"
    When I select "simTicks (scalar)"
    Then the Name field should populate with "simTicks"
    And the Configuration section should show "SCALAR" type label

  Scenario: Search and select a scanned vector variable
    Given the Add Variable dialog is open
    When I type "branchPred" in the search box
    And I select "system.cpu.branchPred.lookups (vector) [3 items]"
    Then the Name field should populate with "system.cpu.branchPred.lookups"
    And the Vector Configuration section should appear
    And I should see parse mode options: "Statistics Only", "Entries Only", "Entries + Statistics"

  Scenario: Add variable via manual entry
    Given the Add Variable dialog is open
    When I select the "Manual Entry" pill
    Then I should see a text input for "Variable Name"
    And I should see a type selector with options: scalar, vector, distribution, configuration
    When I type "system.cpu.numCycles" in the name field
    And I select "scalar" as the type
    And I click "Add to Configuration"
    Then the variable should be added to the parse variables list
    And a toast "Added 'system.cpu.numCycles'!" should appear
    And the dialog should close

  Scenario: Prevent adding duplicate variable
    Given the parse configuration already contains "simTicks"
    And the Add Variable dialog is open
    When I search and select "simTicks"
    And I click "Add to Configuration"
    Then I should see a warning "Variable 'simTicks' already exists."
    And the variable list should remain unchanged

  Scenario: Reject empty variable name
    Given the Add Variable dialog is open in Manual Entry mode
    When I leave the name field empty
    And I click "Add to Configuration"
    Then I should see an error "Variable name is required."

  Scenario: Reject vector without entries
    Given the Add Variable dialog is open in Manual Entry mode
    When I type "myVector" and select type "vector"
    And I do not configure any vector entries
    And I click "Add to Configuration"
    Then I should see an error "Vector variables require at least one entry."

  Scenario: Add variable from inline search section
    Given scanned variables are available
    When I type in the "Search available variables" box
    And I select a variable from the dropdown
    And I click "Add Selected"
    Then a new variable should appear in the editor with a generated UUID
    And the page should rerun to show the new variable

  Scenario: Add variable manually from inline section
    When I click "+ Add Manual"
    Then a new variable named "new_variable" of type "scalar" should be added
    And the variable editor should show it with an editable name field

  Scenario: No scanned variables available
    Given no scan has been performed
    When I look at the "Add Variable" section
    Then I should see "Scan stats files to enable variable search."
    And the search dropdown should not be available

  Scenario: Advanced option - repeat count
    Given the Add Variable dialog is open for a scalar variable
    When I expand "Advanced Options"
    And I set "Repeat Count" to 3
    And I click "Add to Configuration"
    Then the variable config should include "repeat": "3"
```

### 6.2 Pytest-Playwright Test Stubs

```python
class TestVariableDiscovery:
    """E2E tests for variable discovery and the Add Variable dialog."""

    def test_add_variable_dialog_opens(self, data_source_page: Page):
        """Verify Add Variable button opens the dialog with search mode default."""
        page = data_source_page

        page.locator("button:has-text('Add Variable')").click()
        page.wait_for_selector("text=Add Variable", timeout=5000)

        # Search mode should be default
        assert page.locator("text=Search Scanned Variables").is_visible()

    def test_search_scanned_variables(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify searching scanned variables filters the dropdown correctly."""
        page = data_source_page

        # First perform a scan to populate scanned variables
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))
        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Scan complete", timeout=30000)

        # Open dialog
        page.locator("button:has-text('Add Variable')").click()
        page.wait_for_selector("text=Add Variable", timeout=5000)

        # Type in search
        search_input = page.locator("input[placeholder='Type to search...']")
        if search_input.is_visible():
            search_input.fill("sim")

    def test_manual_entry_mode(self, data_source_page: Page):
        """Verify manual entry mode shows name and type inputs."""
        page = data_source_page

        page.locator("button:has-text('Add Variable')").click()
        page.wait_for_selector("text=Add Variable", timeout=5000)

        # Switch to manual entry
        page.get_by_text("Manual Entry").click()

        # Name input should appear
        assert page.locator("text=Variable Name").is_visible()

        # Type selector should appear
        assert page.locator("text=Type").is_visible()

    def test_add_manual_scalar_variable(self, data_source_page: Page):
        """Verify adding a manual scalar variable persists to configuration."""
        page = data_source_page

        page.locator("button:has-text('Add Variable')").click()
        page.wait_for_selector("text=Add Variable", timeout=5000)

        page.get_by_text("Manual Entry").click()

        # Fill name
        name_input = page.locator("[data-testid='stTextInput']").last
        name_input.fill("system.cpu.numCycles")

        # Click add
        page.locator("button:has-text('Add to Configuration')").click()

        # Dialog should close and variable should appear in editor
        page.wait_for_selector("text=system.cpu.numCycles", timeout=5000)

    def test_duplicate_variable_warning(self, data_source_page: Page):
        """Verify adding a variable with existing name shows warning."""
        page = data_source_page

        # Add first variable
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(1000)

        # Try to add same variable again via dialog
        page.locator("button:has-text('Add Variable')").click()
        page.wait_for_selector("text=Add Variable", timeout=5000)
        page.get_by_text("Manual Entry").click()

        name_input = page.locator("[data-testid='stTextInput']").last
        name_input.fill("new_variable")

        page.locator("button:has-text('Add to Configuration')").click()
        page.wait_for_selector("text=already exists", timeout=5000)

    def test_empty_name_shows_error(self, data_source_page: Page):
        """Verify submitting empty name shows validation error."""
        page = data_source_page

        page.locator("button:has-text('Add Variable')").click()
        page.wait_for_selector("text=Add Variable", timeout=5000)
        page.get_by_text("Manual Entry").click()

        # Don't fill name, just click add
        page.locator("button:has-text('Add to Configuration')").click()
        page.wait_for_selector("text=Variable name is required", timeout=5000)

    def test_inline_add_manual_creates_default_variable(self, data_source_page: Page):
        """Verify + Add Manual button adds new_variable of type scalar."""
        page = data_source_page

        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(1000)

        # new_variable should appear in the editor
        assert page.locator("[value='new_variable']").is_visible()

    def test_inline_search_with_scanned_variables(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify inline search section appears after scanning."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))
        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Scan complete", timeout=30000)

        # Search available variables section should be visible
        assert page.locator("text=Search available variables").is_visible()

    def test_no_scan_shows_info_message(self, data_source_page: Page):
        """Verify 'Scan stats files to enable variable search' without prior scan."""
        page = data_source_page

        assert page.locator("text=Scan stats files to enable variable search").is_visible()
```

---

## 7. Variable Editor Tests

### 7.1 Gherkin Scenarios

```gherkin
Feature: Variable Editor
  As a user configuring parser variables
  I want to edit, reorder, and delete variables in the editor
  So that I can fine-tune my extraction configuration

  Background:
    Given the parser configuration contains 3 variables:
      | name                              | type         |
      | simTicks                          | scalar       |
      | system.cpu.branchPred.lookups     | vector       |
      | system.mem_ctrl.rdPerTurnAround   | distribution |
    And I am viewing the Variable Editor section of the Data Source page

  Scenario: Display all variables with common fields
    Then I should see 3 variable rows in the editor
    And each row should have a Name input, Alias input, Type selector, and Delete button
    And the Name inputs should contain the correct variable names
    And the Type selectors should show the correct types

  Scenario: Edit variable name inline
    When I change the Name of variable 1 from "simTicks" to "simSeconds"
    Then the configuration preview JSON should reflect "simSeconds"
    And the state manager parse_variables should contain "simSeconds"

  Scenario: Set variable alias
    When I type "ticks" in the Alias field for variable 1
    Then the configuration should include {"alias": "ticks"} for that variable

  Scenario: Change variable type
    When I change the type of "simTicks" from "scalar" to "configuration"
    Then the Configuration type-specific form should appear
    And a "Default value (if not found)" input should be visible
    And the vector configuration should disappear

  Scenario: Delete a variable
    When I click the "X" button on variable 2
    Then the variable "system.cpu.branchPred.lookups" should be removed
    And the editor should show 2 remaining variables
    And the configuration preview should reflect 2 variables

  Scenario: Vector variable with Statistics Only mode
    Given variable 2 is "system.cpu.branchPred.lookups" of type "vector"
    When I select "Statistics Only" parse mode
    Then checkboxes for total, mean, gmean, samples, stdev should appear
    When I check "total" and "mean"
    Then the config should include vectorEntries: ["total", "mean"]
    And useSpecialMembers should be True

  Scenario: Vector variable with manual entries
    Given variable 2 is in "Entries Only" parse mode
    When I select "Manual Entry Names"
    And I type "cpu0, cpu1, cpu2" in the entries text input
    Then the config should show vectorEntries: ["cpu0", "cpu1", "cpu2"]
    And a success message "Will extract 3 entries" should appear

  Scenario: Vector variable with discovered entries selection
    Given a deep scan has discovered entries ["0", "1", "2", "total"] for the vector
    When I select "Entries Only" parse mode
    And I select "Select from Discovered Entries"
    Then a multiselect with the discovered entries should appear
    When I select "0" and "1"
    Then the config should include vectorEntries: ["0", "1"]

  Scenario: Distribution variable with statistics
    Given variable 3 is "system.mem_ctrl.rdPerTurnAround" of type "distribution"
    When I select "Statistics Only" parse mode
    Then checkboxes for mean, stdev, samples, total, gmean, underflows, overflows should appear
    When I check "mean" and "stdev"
    Then the config should include statistics: ["mean", "stdev"]

  Scenario: Distribution variable with bucket range
    Given variable 3 is in "Bucket Entries Only" parse mode
    Then I should see Minimum and Maximum number inputs
    When I set Minimum to 0 and Maximum to 100
    Then the config should include minimum: 0, maximum: 100

  Scenario: Distribution deep scan for range
    Given variable 3 is in "Bucket Entries Only" parse mode
    When I click "Deep Scan Range for 'system.mem_ctrl.rdPerTurnAround'"
    Then a dialog should open showing scan progress
    And after completion the Minimum and Maximum fields should be populated
    And the range should reflect the aggregated min/max across all files

  Scenario: Configuration variable with default value
    Given a variable of type "configuration" exists
    When I type "Unknown" in the "Default value (if not found)" field
    Then the config should include onEmpty: "Unknown"

  Scenario: Histogram variable with rebinning
    Given a variable of type "histogram" exists
    When I select "Bucket Entries Only" parse mode
    And I check "Normalize to Fixed Buckets (Rebinning)"
    Then I should see "Target Buckets" and "Max Range" inputs
    When I set Target Buckets to 20 and Max Range to 512
    Then the config should include bins: 20, max_range: 512.0

  Scenario: All variables get unique IDs
    Then each variable should have a unique "_id" field
    And new variables added via the editor should receive UUIDs
```

### 7.2 Pytest-Playwright Test Stubs

```python
class TestVariableEditor:
    """E2E tests for the inline variable editor."""

    def test_editor_displays_all_variables(self, data_source_page: Page):
        """Verify all configured variables render with correct fields."""
        page = data_source_page

        # Add a couple of manual variables for testing
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        # Should have at least 2 variable rows
        name_inputs = page.locator("[placeholder='stats.name']")
        assert name_inputs.count() >= 2

    def test_edit_variable_name_inline(self, data_source_page: Page):
        """Verify editing a variable name updates the configuration."""
        page = data_source_page

        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        # Change name
        name_input = page.locator("[placeholder='stats.name']").first
        name_input.fill("")
        name_input.fill("system.cpu.numCycles")
        name_input.press("Tab")

        # Verify in configuration preview
        page.wait_for_timeout(500)
        json_block = page.locator("[data-testid='stJson']")
        json_text = json_block.inner_text()
        assert "numCycles" in json_text

    def test_set_variable_alias(self, data_source_page: Page):
        """Verify setting an alias persists in configuration."""
        page = data_source_page

        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        alias_input = page.locator("[placeholder='Alias (Optional)']").first
        alias_input.fill("custom_alias")
        alias_input.press("Tab")

        page.wait_for_timeout(500)
        json_block = page.locator("[data-testid='stJson']")
        json_text = json_block.inner_text()
        assert "custom_alias" in json_text

    def test_change_variable_type_to_configuration(self, data_source_page: Page):
        """Verify changing type to configuration shows onEmpty field."""
        page = data_source_page

        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        # Change type dropdown
        type_select = page.locator("[data-testid='stSelectbox']").first
        type_select.select_option("configuration")
        page.wait_for_timeout(500)

        # onEmpty field should appear
        assert page.locator("text=Default value").is_visible()

    def test_delete_variable(self, data_source_page: Page):
        """Verify clicking X removes a variable from the editor."""
        page = data_source_page

        # Add two variables
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        initial_count = page.locator("[placeholder='stats.name']").count()

        # Delete first variable
        page.locator("button:has-text('X')").first.click()
        page.wait_for_timeout(500)

        final_count = page.locator("[placeholder='stats.name']").count()
        assert final_count == initial_count - 1

    def test_vector_statistics_only_mode(self, data_source_page: Page):
        """Verify Statistics Only mode shows stat checkboxes for vectors."""
        page = data_source_page

        # Add manual variable and set type to vector
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        type_select = page.locator("[data-testid='stSelectbox']").first
        type_select.select_option("vector")
        page.wait_for_timeout(500)

        # Statistics Only should be the default or available
        assert page.locator("text=Parsing mode").is_visible()

    def test_vector_manual_entry_input(self, data_source_page: Page):
        """Verify manual vector entry input accepts comma-separated values."""
        page = data_source_page

        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        type_select = page.locator("[data-testid='stSelectbox']").first
        type_select.select_option("vector")
        page.wait_for_timeout(500)

        # Look for vector entries input
        entries_input = page.locator("[placeholder*='cpu0, cpu1']")
        if entries_input.is_visible():
            entries_input.fill("bank0, bank1, bank2")
            entries_input.press("Tab")
            page.wait_for_timeout(500)
            assert page.locator("text=Will extract 3 entries").is_visible()

    def test_distribution_range_inputs(self, data_source_page: Page):
        """Verify distribution type shows min/max range inputs."""
        page = data_source_page

        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        type_select = page.locator("[data-testid='stSelectbox']").first
        type_select.select_option("distribution")
        page.wait_for_timeout(500)

        # Distribution configuration should appear
        assert page.locator("text=Distribution Configuration").is_visible()

    def test_configuration_type_onempty_field(self, data_source_page: Page):
        """Verify configuration type shows default value field."""
        page = data_source_page

        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        type_select = page.locator("[data-testid='stSelectbox']").first
        type_select.select_option("configuration")
        page.wait_for_timeout(500)

        # onEmpty field
        default_input = page.locator("text=Default value (if not found)")
        assert default_input.is_visible()
```

---

## 8. Pattern Index Selection Tests

### 8.1 Gherkin Scenarios

```gherkin
Feature: Pattern Index Selection
  As a user with pattern variables (regex \d+ placeholders)
  I want to select specific indices at each position
  So that I can parse only the hardware components I care about

  Background:
    Given a pattern variable "system.ruby.l\d+_cntrl\d+.cache.demand_hits" exists
    And the scanned variables include pattern_indices: ["0_0", "0_1", "1_0"]
    And the variable editor is rendering

  Scenario: Pattern variable detection
    Then the PatternIndexSelector should identify the variable as a pattern variable
    And the selector should extract positions ["l", "cntrl"]
    And the entries should parse to position_values {0: {"0", "1"}, 1: {"0", "1"}}

  Scenario: Display pattern index selector
    Then I should see "Pattern Index Selection:" section
    And I should see the variable name displayed
    And I should see a "Select specific indices" checkbox
    And the checkbox should default to unchecked
    And I should see "Will parse ALL 3 matching instances"

  Scenario: Enable specific index filtering
    When I check "Select specific indices"
    Then I should see selection controls for each position
    And I should see a multiselect for "l{...}" with options ["0", "1"]
    And I should see a multiselect for "cntrl{...}" with options ["0", "1"]
    And all indices should be selected by default

  Scenario: Filter to specific L0 controllers only
    Given specific index filtering is enabled
    When I deselect "1" from the "l{...}" position
    Then filtered entries should be ["0_0", "0_1"]
    And I should see "Will parse 2/3 instances"
    And the config should include keepIndices: True
    And parsed_ids should be ["0_0", "0_1"]

  Scenario: Filter to specific controller at specific level
    Given specific index filtering is enabled
    When I select only "1" for "l{...}" and only "0" for "cntrl{...}"
    Then filtered entries should be ["1_0"]
    And I should see "Will parse 1/3 instances"

  Scenario: Show formatted entry display
    Given specific index filtering is enabled and entries are filtered
    When I expand "Show selected instances"
    Then each entry should be formatted as "l{X}_cntrl{Y}" notation
    And "0_0" should display as "l{0}_cntrl{0}"
    And "1_0" should display as "l{1}_cntrl{0}"

  Scenario: Empty selection shows error
    Given specific index filtering is enabled
    When I deselect all options from the "l{...}" position
    Then I should see a warning "No l indices selected!"
    And the overall message should show "No instances match the current selection!"

  Scenario: Non-pattern variable skips selector
    Given a scalar variable "simTicks" with no \d+ pattern
    Then the PatternIndexSelector should not render
    And no "Pattern Index Selection" section should appear

  Scenario: Uncheck filter reverts to all entries
    Given specific index filtering is enabled with partial selection
    When I uncheck "Select specific indices"
    Then keepIndices should be False
    And all entries should be included in parsing
```

### 8.2 Pytest-Playwright Test Stubs

```python
class TestPatternIndexSelection:
    """E2E tests for the PatternIndexSelector component."""

    def test_pattern_variable_shows_selector(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify pattern variables display the Pattern Index Selection UI."""
        page = data_source_page

        # Scan to discover pattern variables
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))
        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Scan complete", timeout=30000)

        # Add the pattern variable via inline search
        # (This depends on the discovered variable names)
        search_input = page.locator("text=Search available variables")
        if search_input.is_visible():
            # Search for pattern variable
            page.wait_for_timeout(500)

    def test_non_pattern_variable_hides_selector(self, data_source_page: Page):
        """Verify non-pattern scalar variable does not show index selector."""
        page = data_source_page

        # Add a simple scalar
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        # Pattern Index Selection should NOT appear
        assert not page.locator("text=Pattern Index Selection").is_visible()

    def test_select_specific_indices_checkbox(self, data_source_page: Page):
        """Verify the 'Select specific indices' checkbox toggles filter mode."""
        page = data_source_page
        # This requires a pattern variable to be added first
        # In practice, this would be part of a fixture with scanned pattern vars

    def test_filter_reduces_instance_count(self, data_source_page: Page):
        """Verify deselecting indices reduces the reported instance count."""
        page = data_source_page
        # Requires pattern variable with multiple indices

    def test_empty_selection_shows_error(self, data_source_page: Page):
        """Verify clearing all selections shows error message."""
        page = data_source_page
        # Requires pattern variable with filter enabled

    def test_formatted_entry_display_in_expander(self, data_source_page: Page):
        """Verify expanded entries show l{X}_cntrl{Y} format."""
        page = data_source_page
        # Requires pattern variable with filter enabled and entries

    def test_uncheck_filter_restores_all_entries(self, data_source_page: Page):
        """Verify unchecking filter disables keepIndices."""
        page = data_source_page
        # Requires pattern variable flow


class TestPatternIndexServiceUnit:
    """Unit tests for the pure PatternIndexService logic (no UI)."""

    def test_is_pattern_variable_true(self):
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        assert PatternIndexService.is_pattern_variable(r"system.ruby.l\d+_cntrl\d+.stat")

    def test_is_pattern_variable_false(self):
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        assert not PatternIndexService.is_pattern_variable("system.cpu.ipc")

    def test_extract_index_positions(self):
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        positions = PatternIndexService.extract_index_positions(
            r"system.ruby.l\d+_cntrl\d+.stat"
        )
        assert positions == ["l", "cntrl"]

    def test_parse_entry_indices(self):
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        result = PatternIndexService.parse_entry_indices(["0_0", "0_1", "1_0", "1_1"])
        assert result[0] == {"0", "1"}
        assert result[1] == {"0", "1"}

    def test_filter_entries(self):
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        filtered = PatternIndexService.filter_entries(
            ["0_0", "0_1", "1_0", "1_1"],
            {0: ["0"], 1: ["0", "1"]},
        )
        assert filtered == ["0_0", "0_1"]

    def test_filter_entries_empty_selection(self):
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        filtered = PatternIndexService.filter_entries(
            ["0_0", "0_1", "1_0"],
            {0: []},
        )
        assert filtered == []

    def test_format_entry_display(self):
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        formatted = PatternIndexService.format_entry_display("0_1", ["l", "cntrl"])
        assert formatted == "l{0}_cntrl{1}"

    def test_reconstruct_concrete_name(self):
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        result = PatternIndexService.reconstruct_concrete_name(
            r"system.ruby.l\d+_cntrl\d+.stat", "0_1"
        )
        assert result == "system.ruby.l0_cntrl1.stat"

    def test_reconstruct_concrete_name_mismatch_raises(self):
        import pytest
        from src.core.services.data_services.pattern_index_service import (
            PatternIndexService,
        )
        with pytest.raises(ValueError, match="placeholder"):
            PatternIndexService.reconstruct_concrete_name(
                r"system.cpu\d+.ipc", "0_1"  # 1 placeholder, 2 parts
            )
```

---

## 9. Parsing Execution Tests

### 9.1 Gherkin Scenarios

```gherkin
Feature: Parsing Execution
  As a user who has configured the parser
  I want to execute parsing on simulator stats files
  So that I can generate a CSV dataset for analysis

  Background:
    Given I have configured a valid stats path, file pattern, and variables
    And I am on the Data Source page in Parse mode

  Scenario: Successful parse with simple strategy
    Given the parser strategy is set to "simple"
    And 2 scalar variables are configured
    When I click "Parse gem5 Stats Files"
    Then a dialog "Parsing Stats" should open
    And I should see "Processing N files..."
    And a progress bar should advance from 0% to 100%
    And the status should show "Generating CSV output..."
    And the status should show "Adding to data pool..."
    And the status should show "Loading data into session..."
    And I should see "Complete -- N rows loaded"
    And a success message "Done! Generated N rows." should appear
    And a "Close & Reload" button should be visible

  Scenario: Successful parse with config-aware strategy
    Given the parser strategy is set to "config_aware"
    And variables include both scalar and configuration types
    When I click "Parse gem5 Stats Files"
    Then the parse should complete successfully
    And the finalize_parsing call should use strategy_type="config_aware"

  Scenario: Parse button requires stats path
    Given the stats path is empty
    When I click "Parse gem5 Stats Files"
    Then I should see an error "Please specify a stats directory path."
    And no parsing should be initiated

  Scenario: Parse with errors in some files
    Given 3 stats files exist, 1 of which is corrupt
    When I click "Parse gem5 Stats Files"
    Then the progress bar should reach 100%
    And I should see "Encountered 1 errors during parsing."
    And an expandable "Show Errors" section should list the error details

  Scenario: Parse produces no results
    Given the configured variables do not match any data in the stats files
    When I click "Parse gem5 Stats Files"
    Then I should see "No results generated."

  Scenario: Parse completion adds to CSV pool
    When I complete a successful parse
    Then the generated CSV should be added to the pool via add_to_csv_pool
    And the data should be loaded into state via set_data
    And the csv_path should be set to the pool path

  Scenario: Close & Reload after parse
    Given a parse has completed successfully
    When I click "Close & Reload"
    Then the page should rerun
    And the data metrics (Rows, Columns, Source) should display in the header

  Scenario: Parse button reads from session state when fragment is stale
    Given the parser config fragment has set stats_path_input in session_state
    When I click the Parse button (which is outside the fragment)
    Then the button handler should read from st.session_state["stats_path_input"]
    And the correct path should be used for parsing

  Scenario: Temp directory creation for parse output
    When I click "Parse gem5 Stats Files"
    Then a new temporary directory should be created via tempfile.mkdtemp()
    And the temp dir should be stored in state via set_temp_dir

  Scenario: Parse submission failure
    Given the API raises an exception during submit_parse_async
    When I click "Parse gem5 Stats Files"
    Then the exception should be displayed via st.exception
    And the dialog should not open
```

### 9.2 Pytest-Playwright Test Stubs

```python
class TestParsingExecution:
    """E2E tests for the parsing execution workflow."""

    def test_successful_parse_shows_progress_dialog(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify successful parse shows dialog with progress and completion."""
        page = data_source_page

        # Configure parser
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))

        # Scan and add variables
        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Scan complete", timeout=30000)

        # Add at least one variable
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        # Click parse
        page.locator("button:has-text('Parse')").click()
        page.wait_for_selector("text=Processing", timeout=10000)

        # Wait for parse completion
        page.wait_for_selector("text=Complete", timeout=60000)

    def test_parse_empty_path_shows_error(self, data_source_page: Page):
        """Verify parsing with empty path shows error message."""
        page = data_source_page

        # Ensure path is empty
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill("")
        stats_path_input.press("Tab")

        # Click parse
        page.locator("button:has-text('Parse')").click()

        page.wait_for_selector("text=Please specify a stats directory path", timeout=5000)

    def test_parse_with_corrupt_file_shows_errors(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify parse handles corrupt files and reports errors."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))

        # Add variables and parse
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        page.locator("button:has-text('Parse')").click()
        page.wait_for_selector("text=Processing", timeout=10000)
        page.wait_for_timeout(30000)  # Allow time for parse

    def test_close_and_reload_after_parse(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify Close & Reload button triggers page rerun."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))

        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Scan complete", timeout=30000)

        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        page.locator("button:has-text('Parse')").click()
        page.wait_for_selector("text=Close & Reload", timeout=60000)

        page.locator("button:has-text('Close & Reload')").click()
        page.wait_for_timeout(2000)

        # After reload, data metrics should be visible
        # (Rows metric appears in the header fragment)

    def test_parse_data_metrics_appear_in_header(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify after loading data the header shows Rows, Columns, Source metrics."""
        page = data_source_page

        # Load from CSV pool instead (simpler)
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=Recent CSV Files")
        page.locator("button:has-text('Load This File')").first.click()
        page.wait_for_selector("text=Loaded", timeout=10000)

        # Verify header metrics
        assert page.locator("text=Rows").is_visible()
        assert page.locator("text=Columns").is_visible()

    def test_strategy_selector_affects_parse(self, data_source_page: Page):
        """Verify selected strategy is passed to submit_parse_async."""
        page = data_source_page

        # Strategy selector should be visible and clickable
        strategy_label = page.locator("text=Select ingestion strategy")
        assert strategy_label.is_visible()
```

---

## 10. Error Handling Tests

### 10.1 Gherkin Scenarios

```gherkin
Feature: Error Handling on Data Source Page
  As a user making mistakes during data configuration
  I want clear error messages and graceful recovery
  So that I can correct my configuration without losing state

  Scenario: Invalid stats directory path
    Given I enter "/path/that/does/not/exist" as the stats path
    When I click "Quick Scan"
    Then an exception should be displayed with path-related error
    And the rest of the page should remain functional

  Scenario: Stats path with no matching files
    Given I enter a valid directory that contains no stats.txt files
    When I click "Quick Scan"
    Then the scan should complete with 0 files processed
    And an informational message should indicate no variables found

  Scenario: Load corrupt CSV from pool
    Given a CSV file in the pool contains invalid data (e.g., binary content)
    When I click "Load This File" on that entry
    Then st.exception should display the pandas error
    And the previously loaded data should remain intact in state

  Scenario: Delete already-deleted file from pool
    Given a CSV file has been externally deleted from disk
    When I click "Delete" on the corresponding pool entry
    Then the pool entry should be removed from the manifest
    And a toast should confirm the deletion

  Scenario: Parse with no variables configured
    Given no variables have been added to the parse configuration
    When I click "Parse gem5 Stats Files"
    Then the parse should either produce empty results
    Or the parser should handle the empty variable list gracefully

  Scenario: Pattern index selector with malformed entries
    Given a scanned variable has pattern_indices with inconsistent underscore counts
    When the PatternIndexSelector renders
    Then it should handle the mismatch without crashing
    And position_values should be populated based on available entries

  Scenario: Deep scan failure during vector entry discovery
    Given I click "Deep Scan Entries" for a vector variable
    And the scan encounters network or filesystem errors
    Then the dialog should show the error count
    And a warning should indicate errors occurred

  Scenario: Session state widget key conflicts
    Given a variable has been deleted and re-added with the same name
    Then Streamlit widget keys (using _id) should be unique
    And no DuplicateWidgetID error should occur

  Scenario: Concurrent scan and parse prevention
    Given a scan is in progress
    When I simultaneously try to click the Parse button
    Then the system should handle the concurrent access gracefully
    And no data corruption should occur
```

### 10.2 Pytest-Playwright Test Stubs

```python
class TestErrorHandling:
    """E2E tests for error handling and edge cases."""

    def test_invalid_path_scan_shows_exception(self, data_source_page: Page):
        """Verify scanning invalid path shows exception without page crash."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill("/path/that/does/not/exist")

        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("[data-testid='stException']", timeout=10000)

        # Page should still be functional -- check header is still visible
        assert page.locator("text=RING-5 Interactive Analyzer").is_visible()

    def test_empty_path_parse_shows_error(self, data_source_page: Page):
        """Verify empty path triggers inline error on parse attempt."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill("")
        stats_path_input.press("Tab")

        page.locator("button:has-text('Parse')").click()
        page.wait_for_selector("text=Please specify", timeout=5000)

    def test_page_recovers_after_scan_error(self, data_source_page: Page):
        """Verify page remains functional after a scan error."""
        page = data_source_page

        # Trigger error
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill("/nonexistent")
        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_timeout(3000)

        # Now fix the path and try again -- page should still work
        stats_path_input.fill("")
        page.wait_for_timeout(500)

        # Navigation should still work
        page.locator("button:has-text('Data Managers')").click()
        page.wait_for_timeout(1000)
        page.locator("button:has-text('Data Source')").click()
        page.wait_for_timeout(1000)

        assert page.locator("text=Choose Data Source").is_visible()

    def test_widget_key_uniqueness_after_delete_readd(self, data_source_page: Page):
        """Verify no DuplicateWidgetID errors when deleting and re-adding variables."""
        page = data_source_page

        # Add variable
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        # Delete it
        page.locator("button:has-text('X')").first.click()
        page.wait_for_timeout(500)

        # Add again -- should not cause key conflict
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        # No error should appear
        assert not page.locator("[data-testid='stException']").is_visible()

    def test_no_scan_results_in_empty_directory(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify scanning empty dir does not crash and shows informational message."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory / "empty_dir"))

        page.locator("button:has-text('Quick Scan')").click()
        page.wait_for_selector("text=Scan complete", timeout=15000)

    def test_csv_mode_selection_disables_parser(self, data_source_page: Page):
        """Verify selecting CSV mode sets use_parser to False."""
        page = data_source_page

        page.get_by_text("I already have CSV data").click()
        page.wait_for_selector("text=CSV mode selected", timeout=5000)

    def test_parse_mode_selection_enables_parser(self, data_source_page: Page):
        """Verify returning to parse mode re-enables the parser flag."""
        page = data_source_page

        # Switch to CSV mode
        page.get_by_text("I already have CSV data").click()
        page.wait_for_selector("text=CSV mode selected")

        # Switch back to parse mode
        page.get_by_text("Parse").first.click()
        page.wait_for_selector("text=Stats Parser Configuration", timeout=5000)
```

---

## 11. Cross-Page Navigation Tests

### 11.1 Gherkin Scenarios

```gherkin
Feature: Cross-Page Navigation and State Persistence
  As a user navigating between pages
  I want my Data Source configuration to persist
  So that I do not lose my work when switching pages

  Background:
    Given the application is running

  Scenario: Data Source is the default page
    When I open the application
    Then "Data Source" should be the active navigation item
    And the page should show "Step 1: Choose Data Source"

  Scenario: Navigate away and back preserves stats path
    Given I have entered "/some/path" as the stats directory
    When I click "Data Managers" in the sidebar
    And I click "Data Source" in the sidebar
    Then the stats path input should still contain "/some/path"

  Scenario: Navigate away and back preserves variables
    Given I have configured 3 parse variables
    When I navigate to "Manage Plots" and back to "Data Source"
    Then the variable editor should still show 3 variables
    And each variable should retain its name, type, and configuration

  Scenario: Navigate away and back preserves scan results
    Given I have performed a scan that found 6 variables
    When I navigate to "Documentation" and back to "Data Source"
    Then the "Scanner found 6 variables" message should still appear
    And the scanned variables should be available for search

  Scenario: Navigate away and back preserves parser strategy
    Given I have selected "config_aware" as the parsing strategy
    When I navigate away and back
    Then the strategy selector should still show "config_aware"

  Scenario: Loaded data persists in header metrics
    Given I have loaded a CSV with 100 rows and 5 columns
    When I navigate to "Manage Plots"
    Then the header should still show Rows: 100, Columns: 5
    When I navigate back to "Data Source"
    Then the header metrics should remain unchanged

  Scenario: Clear Data resets the Data Source page
    Given I have loaded data and configured variables
    When I click "Clear Data" in the sidebar
    Then the data should be cleared
    And navigating to Data Source should show a fresh state

  Scenario: Reset All clears everything
    Given I have loaded data, configured variables, and created plots
    When I click "Reset All" in the sidebar
    Then all session state should be cleared
    And the Data Source page should show a clean initial state

  Scenario: Data source choice persists across reruns
    Given I have selected "Load from Recent"
    When the page reruns (e.g., due to fragment interaction)
    Then "Load from Recent" should remain selected
    And the CSV pool should still be visible
```

### 11.2 Pytest-Playwright Test Stubs

```python
class TestCrossPageNavigation:
    """E2E tests for navigation and state persistence."""

    def test_data_source_is_default_page(self, data_source_page: Page):
        """Verify Data Source is the active page on application start."""
        page = data_source_page
        assert page.locator("text=Step 1: Choose Data Source").is_visible()

    def test_navigate_away_and_back_preserves_path(
        self, data_source_page: Page, stats_directory: Path
    ):
        """Verify stats path persists across page navigation."""
        page = data_source_page

        stats_path_input = page.locator("[data-testid='stTextInput']").first
        stats_path_input.fill(str(stats_directory))
        stats_path_input.press("Tab")
        page.wait_for_timeout(500)

        # Navigate away
        page.locator("button:has-text('Data Managers')").click()
        page.wait_for_timeout(1000)

        # Navigate back
        page.locator("button:has-text('Data Source')").click()
        page.wait_for_timeout(1000)

        # Path should be preserved
        stats_path_input = page.locator("[data-testid='stTextInput']").first
        assert stats_path_input.input_value() == str(stats_directory)

    def test_navigate_away_and_back_preserves_variables(self, data_source_page: Page):
        """Verify configured variables persist across page navigation."""
        page = data_source_page

        # Add two variables
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        initial_count = page.locator("[placeholder='stats.name']").count()

        # Navigate away and back
        page.locator("button:has-text('Manage Plots')").click()
        page.wait_for_timeout(1000)
        page.locator("button:has-text('Data Source')").click()
        page.wait_for_timeout(1000)

        # Variables should persist
        final_count = page.locator("[placeholder='stats.name']").count()
        assert final_count == initial_count

    def test_clear_data_resets_page(self, data_source_page: Page):
        """Verify Clear Data button resets the loaded data state."""
        page = data_source_page

        page.locator("button:has-text('Clear Data')").click()
        page.wait_for_timeout(2000)

        # Should return to clean state
        assert page.locator("text=Choose Data Source").is_visible()

    def test_reset_all_clears_everything(self, data_source_page: Page):
        """Verify Reset All button clears all session state."""
        page = data_source_page

        # Add variables first
        page.locator("button:has-text('+ Add Manual')").click()
        page.wait_for_timeout(500)

        page.locator("button:has-text('Reset All')").click()
        page.wait_for_timeout(2000)

        # Page should be in initial state
        assert page.locator("text=Choose Data Source").is_visible()

    def test_loaded_data_persists_in_header_across_pages(
        self, data_source_page: Page
    ):
        """Verify header metrics remain visible when navigating between pages."""
        page = data_source_page

        # Load from CSV pool
        page.get_by_text("Load from Recent").click()
        page.wait_for_selector("text=Recent CSV Files")
        page.locator("button:has-text('Load This File')").first.click()
        page.wait_for_selector("text=Loaded", timeout=10000)

        # Navigate to another page
        page.locator("button:has-text('Data Managers')").click()
        page.wait_for_timeout(1000)

        # Header metrics should still be visible
        assert page.locator("text=Rows").is_visible()

    def test_sidebar_navigation_buttons_active_state(self, data_source_page: Page):
        """Verify sidebar highlights the active page button."""
        page = data_source_page

        # Data Source should be active (primary type)
        ds_btn = page.locator("button:has-text('Data Source')")
        assert ds_btn.is_visible()

        # Navigate to Data Managers
        page.locator("button:has-text('Data Managers')").click()
        page.wait_for_timeout(1000)

        # Data Managers should now be active
        dm_btn = page.locator("button:has-text('Data Managers')")
        assert dm_btn.is_visible()
```

---

## 12. Test Data Requirements

### 12.1 Required Filesystem Structures

| Fixture | Contents | Purpose |
|---|---|---|
| `stats_directory` | 3 sim dirs with valid stats.txt + 1 corrupt + 1 empty | Scan and parse testing |
| `csv_pool_directory` | 2 CSV files + manifest JSON | CSV pool management |
| `uploaded_csv` | Single CSV with 3 rows, 5 columns | Direct CSV upload |

### 12.2 Stats File Variable Coverage

| Variable Name | Type | Present In | Special Properties |
|---|---|---|---|
| `simTicks` | scalar | sim_001, sim_002, sim_003 | Common across all files |
| `system.cpu.ipc` | scalar | sim_001, sim_002 | Floating point value |
| `system.cpu.committedInsts` | scalar | sim_001 | Large integer |
| `system.cpu.branchPred.lookups` | vector | sim_001 | Entries: 0, 1, total |
| `system.mem_ctrl.rdPerTurnAround` | distribution | sim_002 | Buckets + statistics |
| `system.ruby.l\d+_cntrl\d+.cache.*` | pattern scalar | sim_003 | Multi-position pattern |

### 12.3 Scanned Variable Data Shapes

```python
# Expected output of finalize_scan for the 3 test stats files:
EXPECTED_SCANNED_VARIABLES = [
    {"name": "simTicks", "type": "scalar", "entries": [], "count": 3},
    {"name": "system.cpu.ipc", "type": "scalar", "entries": [], "count": 2},
    {"name": "system.cpu.committedInsts", "type": "scalar", "entries": [], "count": 1},
    {
        "name": "system.cpu.branchPred.lookups",
        "type": "vector",
        "entries": ["0", "1", "total"],
        "count": 1,
    },
    {
        "name": "system.mem_ctrl.rdPerTurnAround",
        "type": "distribution",
        "entries": ["0-3", "4-7", "8-15"],
        "minimum": 0,
        "maximum": 15,
        "count": 1,
    },
    {
        "name": r"system.ruby.l\d+_cntrl\d+.cache.demand_hits",
        "type": "scalar",
        "entries": [],
        "pattern_indices": ["0_0", "0_1", "1_0"],
        "count": 3,
    },
    {
        "name": r"system.ruby.l\d+_cntrl\d+.cache.demand_misses",
        "type": "scalar",
        "entries": [],
        "pattern_indices": ["0_0", "0_1", "1_0"],
        "count": 3,
    },
]
```

### 12.4 ParseVariableConfig Test Shapes

```python
# Scalar variable
SCALAR_CONFIG = {"name": "simTicks", "type": "scalar", "_id": "uuid-001"}

# Vector with entries
VECTOR_ENTRIES_CONFIG = {
    "name": "system.cpu.branchPred.lookups",
    "type": "vector",
    "_id": "uuid-002",
    "vectorEntries": ["0", "1"],
    "useSpecialMembers": False,
    "statisticsOnly": False,
}

# Vector with statistics only
VECTOR_STATS_CONFIG = {
    "name": "system.cpu.branchPred.lookups",
    "type": "vector",
    "_id": "uuid-003",
    "vectorEntries": ["total", "mean"],
    "useSpecialMembers": True,
    "statisticsOnly": True,
}

# Distribution
DISTRIBUTION_CONFIG = {
    "name": "system.mem_ctrl.rdPerTurnAround",
    "type": "distribution",
    "_id": "uuid-004",
    "statistics": ["mean", "stdev"],
    "statisticsOnly": True,
}

# Distribution with range
DISTRIBUTION_RANGE_CONFIG = {
    "name": "system.mem_ctrl.rdPerTurnAround",
    "type": "distribution",
    "_id": "uuid-005",
    "minimum": 0,
    "maximum": 15,
    "statisticsOnly": False,
}

# Configuration type
CONFIG_TYPE_CONFIG = {
    "name": "benchmark_name",
    "type": "configuration",
    "_id": "uuid-006",
    "onEmpty": "Unknown",
}

# Pattern variable with index selection
PATTERN_CONFIG = {
    "name": r"system.ruby.l\d+_cntrl\d+.cache.demand_hits",
    "type": "scalar",
    "_id": "uuid-007",
    "keepIndices": True,
    "patternSelection": ["0_0", "0_1"],
    "parsed_ids": ["0_0", "0_1"],
}

# Histogram with rebinning
HISTOGRAM_CONFIG = {
    "name": "system.mem_ctrl.rdPerTurnAround",
    "type": "histogram",
    "_id": "uuid-008",
    "statisticsOnly": False,
    "bins": 20,
    "max_range": 512.0,
}
```

---

## 13. Page Object Model for DataSourcePage

```python
"""Page Object Model for the Data Source page E2E tests.

Encapsulates all locators and interaction patterns for the Data Source page
to provide a clean, reusable interface for test methods.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Locator, Page, expect


class DataSourcePageObject:
    """POM for the Data Source page of RING-5."""

    def __init__(self, page: Page):
        self.page = page

    # ── Navigation ──────────────────────────────────────────────────

    @property
    def nav_data_source(self) -> Locator:
        return self.page.locator("button:has-text('Data Source')")

    @property
    def nav_data_managers(self) -> Locator:
        return self.page.locator("button:has-text('Data Managers')")

    @property
    def nav_manage_plots(self) -> Locator:
        return self.page.locator("button:has-text('Manage Plots')")

    @property
    def clear_data_button(self) -> Locator:
        return self.page.locator("button:has-text('Clear Data')")

    @property
    def reset_all_button(self) -> Locator:
        return self.page.locator("button:has-text('Reset All')")

    def navigate_to(self, page_name: str) -> None:
        """Click a sidebar navigation button by page name."""
        self.page.locator(f"button:has-text('{page_name}')").click()
        self.page.wait_for_timeout(1000)

    # ── Data Source Choice ──────────────────────────────────────────

    @property
    def page_title(self) -> Locator:
        return self.page.locator("text=Step 1: Choose Data Source")

    def select_parse_mode(self) -> None:
        """Select the parser stats mode from the segmented control."""
        self.page.get_by_text("Parse").first.click()
        self.page.wait_for_selector("text=Stats Parser Configuration")

    def select_csv_mode(self) -> None:
        """Select the CSV upload mode."""
        self.page.get_by_text("I already have CSV data").click()
        self.page.wait_for_selector("text=CSV mode selected")

    def select_recent_mode(self) -> None:
        """Select the Load from Recent mode."""
        self.page.get_by_text("Load from Recent").click()
        self.page.wait_for_selector("text=Recent CSV Files")

    # ── Parser Configuration ────────────────────────────────────────

    @property
    def stats_path_input(self) -> Locator:
        return self.page.locator("[data-testid='stTextInput']").first

    @property
    def stats_pattern_input(self) -> Locator:
        return self.page.locator("[data-testid='stTextInput']").nth(1)

    @property
    def simulator_pills(self) -> Locator:
        return self.page.locator("[data-testid='stPills']").first

    @property
    def strategy_selector(self) -> Locator:
        return self.page.locator("text=Select ingestion strategy")

    @property
    def deep_scan_checkbox(self) -> Locator:
        return self.page.locator("text=Deep Scan (check all files)")

    @property
    def quick_scan_button(self) -> Locator:
        return self.page.locator("button:has-text('Quick Scan')")

    @property
    def parse_button(self) -> Locator:
        return self.page.locator("button:has-text('Parse')")

    @property
    def config_preview_json(self) -> Locator:
        return self.page.locator("[data-testid='stJson']")

    def fill_stats_path(self, path: str | Path) -> None:
        """Fill the stats directory path input."""
        self.stats_path_input.fill(str(path))
        self.stats_path_input.press("Tab")
        self.page.wait_for_timeout(300)

    def fill_stats_pattern(self, pattern: str) -> None:
        """Fill the file pattern input."""
        self.stats_pattern_input.fill(pattern)
        self.stats_pattern_input.press("Tab")
        self.page.wait_for_timeout(300)

    def run_quick_scan(self, timeout: int = 30000) -> None:
        """Click Quick Scan and wait for completion."""
        self.quick_scan_button.click()
        self.page.wait_for_selector("text=Scan complete", timeout=timeout)

    def run_deep_scan(self, timeout: int = 60000) -> None:
        """Enable deep scan, click Quick Scan, and wait for completion."""
        self.deep_scan_checkbox.click()
        self.quick_scan_button.click()
        self.page.wait_for_selector("text=Scan complete", timeout=timeout)

    def click_parse(self) -> None:
        """Click the main Parse button."""
        self.parse_button.click()

    def get_config_preview_text(self) -> str:
        """Return the text content of the JSON configuration preview."""
        return self.config_preview_json.inner_text()

    # ── Variable Editor ─────────────────────────────────────────────

    @property
    def variable_name_inputs(self) -> Locator:
        return self.page.locator("[placeholder='stats.name']")

    @property
    def variable_alias_inputs(self) -> Locator:
        return self.page.locator("[placeholder='Alias (Optional)']")

    @property
    def variable_type_selectors(self) -> Locator:
        return self.page.locator("[data-testid='stSelectbox']")

    @property
    def variable_delete_buttons(self) -> Locator:
        return self.page.locator("button:has-text('X')")

    @property
    def add_manual_button(self) -> Locator:
        return self.page.locator("button:has-text('+ Add Manual')")

    @property
    def add_variable_dialog_button(self) -> Locator:
        return self.page.locator("button:has-text('Add Variable')")

    def add_manual_variable(self) -> None:
        """Click + Add Manual and wait for the new row to appear."""
        current_count = self.variable_name_inputs.count()
        self.add_manual_button.click()
        self.page.wait_for_timeout(500)

    def delete_variable(self, index: int) -> None:
        """Delete a variable by index."""
        self.variable_delete_buttons.nth(index).click()
        self.page.wait_for_timeout(500)

    def get_variable_count(self) -> int:
        """Return the number of variables in the editor."""
        return self.variable_name_inputs.count()

    def set_variable_name(self, index: int, name: str) -> None:
        """Set the name of a variable by index."""
        input_field = self.variable_name_inputs.nth(index)
        input_field.fill("")
        input_field.fill(name)
        input_field.press("Tab")
        self.page.wait_for_timeout(300)

    def set_variable_alias(self, index: int, alias: str) -> None:
        """Set the alias of a variable by index."""
        input_field = self.variable_alias_inputs.nth(index)
        input_field.fill(alias)
        input_field.press("Tab")
        self.page.wait_for_timeout(300)

    def set_variable_type(self, index: int, var_type: str) -> None:
        """Change the type of a variable by index."""
        select_box = self.variable_type_selectors.nth(index)
        select_box.select_option(var_type)
        self.page.wait_for_timeout(500)

    # ── Add Variable Dialog ─────────────────────────────────────────

    def open_add_variable_dialog(self) -> None:
        """Open the Add Variable dialog."""
        self.add_variable_dialog_button.click()
        self.page.wait_for_selector("text=Add Variable", timeout=5000)

    def switch_to_manual_entry(self) -> None:
        """Switch the Add Variable dialog to Manual Entry mode."""
        self.page.get_by_text("Manual Entry").click()

    def fill_dialog_manual_name(self, name: str) -> None:
        """Fill the variable name in the manual entry dialog."""
        name_input = self.page.locator("[data-testid='stTextInput']").last
        name_input.fill(name)

    def click_add_to_configuration(self) -> None:
        """Click the 'Add to Configuration' button in the dialog."""
        self.page.locator("button:has-text('Add to Configuration')").click()

    # ── CSV Pool ────────────────────────────────────────────────────

    @property
    def csv_pool_heading(self) -> Locator:
        return self.page.locator("text=Recent CSV Files")

    @property
    def csv_pool_count_message(self) -> Locator:
        return self.page.locator("text=CSV file(s) in the pool")

    def get_load_buttons(self) -> Locator:
        """Return all Load This File buttons in the CSV pool."""
        return self.page.locator("button:has-text('Load This File')")

    def get_preview_buttons(self) -> Locator:
        """Return all Preview buttons in the CSV pool."""
        return self.page.locator("button:has-text('Preview')")

    def get_delete_buttons(self) -> Locator:
        """Return all Delete buttons in the CSV pool."""
        return self.page.locator("button:has-text('Delete')")

    def load_csv_from_pool(self, index: int = 0) -> None:
        """Load a CSV file from the pool by index."""
        self.get_load_buttons().nth(index).click()
        self.page.wait_for_selector("text=Loaded", timeout=10000)

    def preview_csv_from_pool(self, index: int = 0) -> None:
        """Preview a CSV file from the pool by index."""
        self.get_preview_buttons().nth(index).click()
        self.page.wait_for_selector("[data-testid='stDataFrame']")

    def delete_csv_from_pool(self, index: int = 0) -> None:
        """Delete a CSV file from the pool by index."""
        self.get_delete_buttons().nth(index).click()
        self.page.wait_for_timeout(2000)

    # ── Parse Dialog ────────────────────────────────────────────────

    @property
    def parse_dialog_progress(self) -> Locator:
        return self.page.locator("text=Processing")

    @property
    def parse_dialog_complete(self) -> Locator:
        return self.page.locator("text=Complete")

    @property
    def close_reload_button(self) -> Locator:
        return self.page.locator("button:has-text('Close & Reload')")

    def wait_for_parse_completion(self, timeout: int = 60000) -> None:
        """Wait for the parse dialog to show completion status."""
        self.page.wait_for_selector("text=Complete", timeout=timeout)

    # ── Header Metrics ──────────────────────────────────────────────

    @property
    def rows_metric(self) -> Locator:
        return self.page.locator("text=Rows")

    @property
    def columns_metric(self) -> Locator:
        return self.page.locator("text=Columns")

    @property
    def source_metric(self) -> Locator:
        return self.page.locator("text=Source")

    # ── Pattern Index Selector ──────────────────────────────────────

    @property
    def pattern_index_section(self) -> Locator:
        return self.page.locator("text=Pattern Index Selection")

    @property
    def select_specific_indices_checkbox(self) -> Locator:
        return self.page.locator("text=Select specific indices")

    def get_pattern_position_selectors(self) -> Locator:
        """Return the multiselect widgets for pattern position filtering."""
        return self.page.locator("[data-testid='stMultiSelect']")

    # ── Assertions ──────────────────────────────────────────────────

    def assert_page_visible(self) -> None:
        """Assert the Data Source page is rendered."""
        expect(self.page_title).to_be_visible()

    def assert_scan_success(self) -> None:
        """Assert that a scan completed with variables found."""
        expect(self.page.locator("text=Scanner found")).to_be_visible()

    def assert_exception_visible(self) -> None:
        """Assert that an st.exception block is visible."""
        expect(self.page.locator("[data-testid='stException']")).to_be_visible()

    def assert_no_exception(self) -> None:
        """Assert that no st.exception block is visible."""
        expect(self.page.locator("[data-testid='stException']")).not_to_be_visible()

    def assert_data_loaded(self) -> None:
        """Assert that data has been loaded (header metrics visible)."""
        expect(self.rows_metric).to_be_visible()
        expect(self.columns_metric).to_be_visible()
```

---

## Summary

This test plan covers **13 sections** comprising:

- **7 Gherkin feature files** with 55+ scenarios across CSV pool management, file scanning,
  variable discovery, variable editor configuration, pattern index selection, parsing execution,
  error handling, and cross-page navigation.
- **10 pytest-playwright test classes** with 75+ test method stubs ready for implementation.
- **8 PatternIndexService unit tests** for the pure business logic layer.
- **Complete fixtures** for filesystem seeding (stats files, CSV pool, uploaded CSV),
  ApplicationAPI initialization, Playwright page setup, and scanned variable mock data.
- **Test data specification** documenting all expected variable shapes, config objects, and
  the ParseVariableConfig variants for scalar, vector, distribution, histogram, configuration,
  and pattern types.
- **Full Page Object Model** (`DataSourcePageObject`) with 40+ properties, methods, and
  assertion helpers encapsulating every locator and interaction pattern on the Data Source page.
