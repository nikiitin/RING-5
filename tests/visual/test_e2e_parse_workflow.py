"""End-to-end tests: scan, configure variables, parse, then verify data managers.

Consolidated from 31 individual tests to 10 workflow-style tests.

These tests exercise the FULL workflow of RING-5:
1. Set a real stats directory path pointing to ``tests/data/synthetic/``
2. Scan for variables (Quick Scan)
3. Add variables -- from scan results and manually
4. Parse the gem5 stats files
5. Navigate to Data Managers and verify loaded data
6. Exercise data manager tabs (Seeds Reducer, Outlier Remover,
   Preprocessor, Mixer)

Timeouts are higher than normal visual tests because scanning and parsing
involve real file I/O.

NOTE: These tests use ``tests/data/synthetic/`` which contains controlled,
small gem5 stats files -- NOT the large ``results-micro26-sens/`` dataset.

IMPORTANT -- Streamlit segmented-control toggle behaviour:
    Clicking an already-active segmented-control option DESELECTS it.
    We must use ``ensure_parse_mode()`` (check-then-click) instead of
    ``select_parse_mode()`` (always click) to avoid accidentally
    deselecting the default "Parse gem5 Stats Files" mode.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser

# ---------------------------------------------------------------------------
# Paths -- resolved at import time so they work regardless of cwd
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).parents[2]
_SINGLE_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "single"
_HISTOGRAM_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "histogram"
_MULTI_CPU_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "multi_cpu"
_BENCHMARKS_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "benchmarks"

# E2E timeout -- longer than normal visual tests
_E2E_TIMEOUT: int = 60_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_data_source(page: Page, live_server_url: str) -> DataSourcePage:
    """Navigate to Data Source page and ensure Parse mode is active."""
    ds = DataSourcePage(page)
    ds.goto_and_wait(live_server_url)
    ds.assert_step_header_visible()
    ds.ensure_parse_mode()
    return ds


def _scan_add_parse_close(
    ds: DataSourcePage,
    stats_path: Path,
    variables: list[str],
) -> None:
    """Reusable helper: scan -> add variables -> parse -> close dialog."""
    ds.fill_stats_path(str(stats_path))
    ds.fill_stats_pattern("stats.txt")
    ds.scan_and_wait(timeout=_E2E_TIMEOUT)
    ds.assert_scan_success()

    for var in variables:
        ds.add_manual_variable(var, "scalar")

    ds.click_parse()
    expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
    expect(ds.parse_close_button).to_be_visible(timeout=_E2E_TIMEOUT)
    ds.close_parse_dialog_and_reload()


# ===================================================================
# 1. Scanning workflow -- each test uses different data (kept separate)
# ===================================================================


class TestScanWorkflow:
    """Verify scanning real gem5 stats files discovers variables.

    Each test uses a different synthetic dataset so they cannot be merged.
    Uses ``shared_page`` to avoid creating a new browser context per scan.
    """

    def test_scan_single_stats(self, shared_page: Page, live_server_url: str) -> None:
        """Quick Scan on single/stats.txt discovers scalar variables."""
        ds = _setup_data_source(shared_page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()
        count = ds.get_scan_result_count()
        assert count > 0, f"Expected scanner to find variables, got {count}"

    def test_scan_histogram_stats(self, shared_page: Page, live_server_url: str) -> None:
        """Quick Scan on histogram/stats.txt discovers histogram variables."""
        ds = _setup_data_source(shared_page, live_server_url)
        ds.fill_stats_path(str(_HISTOGRAM_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()
        count = ds.get_scan_result_count()
        assert count > 0, f"Expected scanner to find variables, got {count}"

    def test_scan_multi_cpu_stats(self, shared_page: Page, live_server_url: str) -> None:
        """Quick Scan on multi_cpu/stats.txt discovers CPU-indexed variables."""
        ds = _setup_data_source(shared_page, live_server_url)
        ds.fill_stats_path(str(_MULTI_CPU_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()

    def test_scan_benchmarks_directory(self, shared_page: Page, live_server_url: str) -> None:
        """Quick Scan on benchmarks/ discovers variables across subdirs."""
        ds = _setup_data_source(shared_page, live_server_url)
        ds.fill_stats_path(str(_BENCHMARKS_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()

    def test_scan_error_handling(self, shared_page: Page, live_server_url: str) -> None:
        """Scanning a nonexistent path shows an error, not a crash."""
        ds = _setup_data_source(shared_page, live_server_url)
        ds.fill_stats_path("/nonexistent/path/to/nowhere")
        ds.fill_stats_pattern("stats.txt")
        ds.click_quick_scan()
        error_or_exception = shared_page.locator(
            "[data-testid='stException'], [data-testid='stAlertContentError']"
        ).first
        expect(error_or_exception).to_be_visible(timeout=_E2E_TIMEOUT)


# ===================================================================
# 2. Variable configuration + Parse -- consolidated
# ===================================================================


class TestVariableAndParse:
    """Consolidated variable configuration and parse workflow tests.

    Merges 10 original tests from TestVariableConfiguration + TestParseWorkflow.
    Uses ``shared_page`` to avoid creating a new browser context per test.
    """

    def test_variable_add_and_configure(self, shared_page: Page, live_server_url: str) -> None:
        """Add variables from scan and manually, verify config preview.

        Consolidates 5 original tests:
        - add_variable_from_scan_results
        - add_manual_scalar_variable
        - add_manual_variable_wrong_name
        - add_multiple_variables
        - config_preview_updates_with_variables
        """
        ds = _setup_data_source(shared_page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()

        # Add from scan results
        ds.add_variable_from_scan(index=0)
        ds.assert_dialog_hidden()

        # Add manual scalar
        ds.add_manual_variable("system.cpu.ipc", "scalar")
        ds.assert_dialog_hidden()

        # Empty name shows error
        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        ds.click_dialog_add()
        expect(ds.dialog_name_error).to_be_visible(timeout=10_000)
        ds.close_dialog()

        # Add another variable and verify config preview
        ds.add_manual_variable("simSeconds", "scalar")
        ds.assert_dialog_hidden()
        expect(ds.config_json_view).to_contain_text("simSeconds", timeout=15_000)

    def test_parse_success_and_data_managers(self, shared_page: Page, live_server_url: str) -> None:
        """Parse with correct variables and verify Data Managers loads data.

        Consolidates 7 original tests:
        - parse_with_correct_scalar_variable
        - parse_with_multiple_scalar_variables
        - parse_benchmarks_multi_seed
        - data_managers_shows_data_after_parse
        - data_managers_summary_shows_rows
        - data_managers_visualization_tab_has_dataframe
        - data_managers_history_is_empty_initially
        """
        ds = _setup_data_source(shared_page, live_server_url)
        _scan_add_parse_close(ds, _BENCHMARKS_STATS, ["system.cpu.ipc"])

        # Navigate to Data Managers
        dm = DataManagersPage(shared_page)
        dm.navigate()
        dm.assert_page_header_visible()

        # No "no data" warning -- data is loaded
        expect(dm.no_data_warning).not_to_be_visible(timeout=15_000)

        # Summary shows row metrics
        dm.assert_has_data()

        # Data Visualization tab has a dataframe
        dm.select_tab("Data Visualization")
        dm.assert_dataframe_visible()

        # Operations History is empty initially
        dm.select_tab("Operations History")
        dm.assert_history_empty()

    def test_parse_error_scenarios(self, shared_page: Page, live_server_url: str) -> None:
        """Parse error handling (empty path, nonexistent variable).

        Consolidates 2 original tests:
        - parse_empty_path_shows_error
        - parse_with_nonexistent_variable_name
        """
        ds = _setup_data_source(shared_page, live_server_url)

        # Empty path shows validation error
        ds.stats_path_input.fill("")
        ds.stats_path_input.press("Tab")
        ds.wait_for_streamlit()
        ds.page.wait_for_timeout(500)
        ds.click_parse()
        expect(ds.parser_error_message).to_be_visible(timeout=10_000)
        expect(ds.parser_error_message).to_contain_text("Please specify a stats directory path")

        # Nonexistent variable
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.add_manual_variable("totally.fake.variable.that.doesnt.exist", "scalar")
        ds.assert_dialog_hidden()
        ds.click_parse()
        expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
        dialog_outcome = ds.parse_dialog.locator(
            "[data-testid='stAlertContentWarning'], [data-testid='stAlertContentError']"
        ).or_(ds.parse_close_button)
        expect(dialog_outcome).to_be_visible(timeout=_E2E_TIMEOUT)


# ===================================================================
# 3. Data Manager operations -- consolidated
# ===================================================================


class TestDataManagerOperations:
    """Consolidated Data Manager tab operations after parsing.

    Merges 7 original tests from TestSeedsReducerNoSeedColumn,
    TestOutlierRemover, TestPreprocessor, TestMixer.
    Uses ``shared_page`` to avoid redundant parse+navigate cycles.
    """

    def test_seeds_outlier_preprocessor_mixer(
        self, shared_page: Page, live_server_url: str
    ) -> None:
        """All data manager tabs work correctly after parsing.

        Consolidates 7 original tests:
        - seeds_reducer_shows_column_selector (generic reducer)
        - outlier_tab_shows_metrics
        - outlier_apply_shows_result
        - preprocessor_shows_selectboxes
        - preprocessor_preview_creates_column
        - mixer_shows_mode_control
        - mixer_shows_column_multiselect
        """
        # Parse benchmarks data (multiple rows for statistical operations)
        ds = _setup_data_source(shared_page, live_server_url)
        _scan_add_parse_close(ds, _BENCHMARKS_STATS, ["system.cpu.ipc", "simSeconds"])

        dm = DataManagersPage(shared_page)
        dm.navigate()
        dm.assert_page_header_visible()

        # Seeds Reducer -- column selector visible (generic reducer)
        dm.select_tab("Seeds Reducer")
        dm.assert_reducer_ready()

        # Outlier Remover -- metrics visible and apply works
        dm.select_tab("Outlier Remover")
        dm.assert_outlier_shows_metrics()
        dm.apply_outlier_remover()
        dm.assert_success_message_visible()

        # Preprocessor -- selectboxes visible and preview works
        dm.select_tab("Preprocessor")
        expect(dm.preproc_src1_selectbox).to_be_visible(timeout=15_000)
        expect(dm.preproc_operation_selectbox).to_be_visible()
        dm.apply_preprocessor_preview()
        # After tab switch, the Outlier Remover's success message is hidden
        # in its tab panel.  Use last visible success to avoid stale DOM hit.
        preproc_success = shared_page.locator("[data-testid='stAlertContentSuccess']").last
        expect(preproc_success).to_be_visible(timeout=15_000)

        # Mixer -- mode control and columns multiselect visible
        dm.select_tab("Mixer")
        expect(dm.mixer_mode_control).to_be_visible(timeout=15_000)
        expect(dm.mixer_columns_multiselect).to_be_visible(timeout=15_000)


# ===================================================================
# 4. Cross-page E2E -- parse then load from Recent
# ===================================================================


class TestParseAndRecentPool:
    """After parsing, the result CSV appears in Load from Recent."""

    def test_parsed_csv_appears_in_recent(self, shared_page: Page, live_server_url: str) -> None:
        """After parsing, switching to 'Load from Recent' shows the CSV."""
        ds = _setup_data_source(shared_page, live_server_url)
        _scan_add_parse_close(ds, _SINGLE_STATS, ["simSeconds"])

        ds.select_recent_mode()
        ds.assert_recent_header_visible()
        expect(ds.pool_file_count_info).to_be_visible(timeout=15_000)


# ===================================================================
# 5. Screenshots for E2E documentation
# ===================================================================


class TestE2EScreenshots:
    """Capture screenshots of E2E states for documentation.

    Consolidated from 4 individual tests to 2 workflow-style tests.
    """

    def test_scan_and_variable_screenshots(
        self,
        shared_page: Page,
        live_server_url: str,
        shared_screenshot_dir: Path,
    ) -> None:
        """Capture screenshots after scan and with variables added.

        Consolidates 2 original tests:
        - capture_after_scan
        - capture_with_variables_added
        """
        ds = _setup_data_source(shared_page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)

        ds.screenshot(shared_screenshot_dir / "e2e_after_scan.png")

        ds.add_manual_variable("simSeconds", "scalar")
        ds.add_manual_variable("system.cpu.ipc", "scalar")
        ds.screenshot(shared_screenshot_dir / "e2e_variables_added.png")

    def test_parse_and_data_managers_screenshots(
        self,
        shared_page: Page,
        live_server_url: str,
        shared_screenshot_dir: Path,
    ) -> None:
        """Capture parse dialog and Data Managers with data screenshots.

        Consolidates 2 original tests:
        - capture_parse_in_progress
        - capture_data_managers_with_data
        """
        ds = _setup_data_source(shared_page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.add_manual_variable("simSeconds", "scalar")

        # Parse dialog screenshot
        ds.click_parse()
        expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
        shared_page.wait_for_timeout(2000)
        ds.screenshot(shared_screenshot_dir / "e2e_parse_dialog.png")

        # Wait for parse to complete, close dialog
        expect(ds.parse_close_button).to_be_visible(timeout=_E2E_TIMEOUT)
        ds.close_parse_dialog_and_reload()

        # Data Managers with data
        dm = DataManagersPage(shared_page)
        dm.navigate()
        dm.assert_has_data()
        dm.screenshot(shared_screenshot_dir / "e2e_data_managers_summary.png")
