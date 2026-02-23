"""End-to-end tests: scan, configure variables, parse, then verify data managers.

These tests exercise the FULL workflow of RING-5:
1. Set a real stats directory path pointing to ``tests/data/synthetic/``
2. Scan for variables (Quick Scan)
3. Add variables — from scan results and manually
4. Parse the gem5 stats files
5. Navigate to Data Managers and verify loaded data
6. Exercise data manager tabs (Seeds Reducer, Outlier Remover,
   Preprocessor, Mixer)

Timeouts are higher than normal visual tests because scanning and parsing
involve real file I/O.

NOTE: These tests use ``tests/data/synthetic/`` which contains controlled,
small gem5 stats files — NOT the large ``results-micro26-sens/`` dataset.

IMPORTANT — Streamlit segmented-control toggle behaviour:
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
# Paths — resolved at import time so they work regardless of cwd
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).parents[2]
_SINGLE_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "single"
_HISTOGRAM_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "histogram"
_MULTI_CPU_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "multi_cpu"
_BENCHMARKS_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "benchmarks"

# E2E timeout — longer than normal visual tests
_E2E_TIMEOUT: int = 60_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_data_source(page: Page, live_server_url: str) -> DataSourcePage:
    """Navigate to Data Source page and ensure Parse mode is active.

    Uses ``ensure_parse_mode`` to avoid toggling-off the already-active
    default mode.
    """
    ds = DataSourcePage(page)
    ds.goto_and_wait(live_server_url)
    ds.assert_step_header_visible()
    # Parse is the default — ensure_parse_mode only clicks if not active
    ds.ensure_parse_mode()
    return ds


def _scan_add_parse_close(
    ds: DataSourcePage,
    stats_path: Path,
    variables: list[str],
) -> None:
    """Reusable helper: scan → add variables → parse → close dialog.

    Args:
        ds: Already-navigated DataSourcePage.
        stats_path: Absolute path to the stats directory.
        variables: List of scalar variable names to add.
    """
    ds.fill_stats_path(str(stats_path))
    ds.fill_stats_pattern("stats.txt")
    ds.scan_and_wait(timeout=_E2E_TIMEOUT)
    ds.assert_scan_success()

    for var in variables:
        ds.add_manual_variable(var, "scalar")

    ds.click_parse()
    expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
    # Wait for "Close & Reload" button (appears on successful parse)
    expect(ds.parse_close_button).to_be_visible(timeout=_E2E_TIMEOUT)
    ds.close_parse_dialog_and_reload()


# ===================================================================
# 1. Scanning workflow — real gem5 stats
# ===================================================================


class TestScanWorkflow:
    """Verify scanning real gem5 stats files discovers variables."""

    def test_scan_single_stats(self, page: Page, live_server_url: str) -> None:
        """Quick Scan on single/stats.txt discovers scalar variables."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")

        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()

        count = ds.get_scan_result_count()
        assert count > 0, f"Expected scanner to find variables, got {count}"

    def test_scan_histogram_stats(self, page: Page, live_server_url: str) -> None:
        """Quick Scan on histogram/stats.txt discovers histogram variables."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_HISTOGRAM_STATS))
        ds.fill_stats_pattern("stats.txt")

        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()

        count = ds.get_scan_result_count()
        assert count > 0, f"Expected scanner to find variables, got {count}"

    def test_scan_multi_cpu_stats(self, page: Page, live_server_url: str) -> None:
        """Quick Scan on multi_cpu/stats.txt discovers CPU-indexed variables."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_MULTI_CPU_STATS))
        ds.fill_stats_pattern("stats.txt")

        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()

    def test_scan_benchmarks_directory(self, page: Page, live_server_url: str) -> None:
        """Quick Scan on benchmarks/ discovers variables across subdirs."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_BENCHMARKS_STATS))
        ds.fill_stats_pattern("stats.txt")

        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()

    def test_scan_nonexistent_path_fails_gracefully(self, page: Page, live_server_url: str) -> None:
        """Scanning a nonexistent path shows an error, not a crash."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path("/nonexistent/path/to/nowhere")
        ds.fill_stats_pattern("stats.txt")

        ds.click_quick_scan()
        # Source code catches the exception and calls st.exception(e)
        error_or_exception = page.locator(
            "[data-testid='stException'], " "[data-testid='stAlertContentError']"
        ).first
        expect(error_or_exception).to_be_visible(timeout=_E2E_TIMEOUT)


# ===================================================================
# 2. Variable configuration after scanning
# ===================================================================


class TestVariableConfiguration:
    """After scanning, test adding variables from scan results and manually."""

    def _scan_first(self, page: Page, live_server_url: str) -> DataSourcePage:
        """Helper: navigate + scan single stats directory."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()
        return ds

    def test_add_variable_from_scan_results(self, page: Page, live_server_url: str) -> None:
        """User can add a variable from the scanned results list."""
        ds = self._scan_first(page, live_server_url)

        # add_variable_from_scan opens the dialog, selects, and adds
        ds.add_variable_from_scan(index=0)
        # Dialog auto-closes via st.rerun() after adding
        ds.assert_dialog_hidden()

    def test_add_manual_scalar_variable(self, page: Page, live_server_url: str) -> None:
        """User can manually add a scalar variable by typing the name."""
        ds = self._scan_first(page, live_server_url)

        ds.add_manual_variable("system.cpu.ipc", "scalar")
        # Dialog auto-closes via st.rerun()
        ds.assert_dialog_hidden()

    def test_add_manual_variable_wrong_name(self, page: Page, live_server_url: str) -> None:
        """Attempting to add a variable with empty name shows error."""
        ds = self._scan_first(page, live_server_url)

        ds.open_add_variable_dialog()
        ds.switch_dialog_to_manual()
        # Leave name empty and click Add → should show error
        ds.click_dialog_add()
        expect(ds.dialog_name_error).to_be_visible(timeout=10_000)

    def test_add_multiple_variables(self, page: Page, live_server_url: str) -> None:
        """User can add multiple variables sequentially."""
        ds = self._scan_first(page, live_server_url)

        # Add first scalar
        ds.add_manual_variable("simSeconds", "scalar")
        ds.assert_dialog_hidden()

        # Add second scalar
        ds.add_manual_variable("system.cpu.ipc", "scalar")
        ds.assert_dialog_hidden()

    def test_config_preview_updates_with_variables(self, page: Page, live_server_url: str) -> None:
        """After adding a variable, the JSON preview reflects it."""
        ds = self._scan_first(page, live_server_url)

        ds.add_manual_variable("simSeconds", "scalar")
        ds.assert_dialog_hidden()

        # The configuration preview should now contain the variable name
        expect(ds.config_json_view).to_contain_text("simSeconds", timeout=15_000)


# ===================================================================
# 3. Parse workflow — correct and incorrect scenarios
# ===================================================================


class TestParseWorkflow:
    """Test the full parse cycle: scan → add variables → parse."""

    def _prepare_for_parse(self, page: Page, live_server_url: str) -> DataSourcePage:
        """Scan + add a scalar variable, ready to parse."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.assert_scan_success()

        # Add a known scalar variable
        ds.add_manual_variable("simSeconds", "scalar")
        ds.assert_dialog_hidden()
        return ds

    def test_parse_with_correct_scalar_variable(self, page: Page, live_server_url: str) -> None:
        """Parsing with a correct scalar variable succeeds."""
        ds = self._prepare_for_parse(page, live_server_url)

        ds.click_parse()
        expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
        # "Close & Reload" button appears on successful parse
        expect(ds.parse_close_button).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_parse_with_nonexistent_variable_name(self, page: Page, live_server_url: str) -> None:
        """Parsing with a made-up variable that doesn't exist in stats."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")

        # Don't need to scan — just add a bogus variable directly
        ds.add_manual_variable("totally.fake.variable.that.doesnt.exist", "scalar")
        ds.assert_dialog_hidden()

        ds.click_parse()
        expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
        # The parser will either:
        # - produce no results → st.warning("No results generated.")
        # - encounter errors → st.error(...)
        # - or succeed but with empty data → "Close & Reload" appears
        # Any of these outcomes is acceptable for "bad variable" test
        dialog_outcome = ds.parse_dialog.locator(
            "[data-testid='stAlertContentWarning'], " "[data-testid='stAlertContentError']"
        ).or_(ds.parse_close_button)
        expect(dialog_outcome).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_parse_empty_path_shows_error(self, page: Page, live_server_url: str) -> None:
        """Parsing with empty path shows validation error (no dialog)."""
        ds = _setup_data_source(page, live_server_url)
        # Clear the stats path
        ds.stats_path_input.fill("")
        ds.stats_path_input.press("Tab")
        ds.wait_for_streamlit()
        ds.page.wait_for_timeout(500)

        ds.click_parse()
        expect(ds.parser_error_message).to_be_visible(timeout=10_000)
        expect(ds.parser_error_message).to_contain_text("Please specify a stats directory path")

    def test_parse_with_multiple_scalar_variables(self, page: Page, live_server_url: str) -> None:
        """Parsing with multiple scalar variables succeeds."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)

        # Add multiple scalars
        ds.add_manual_variable("simSeconds", "scalar")
        ds.assert_dialog_hidden()
        ds.add_manual_variable("system.cpu.ipc", "scalar")
        ds.assert_dialog_hidden()

        ds.click_parse()
        expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(ds.parse_close_button).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_parse_benchmarks_multi_seed(self, page: Page, live_server_url: str) -> None:
        """Parsing benchmarks/ with multiple seeds produces multi-row data."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_BENCHMARKS_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)

        ds.add_manual_variable("system.cpu.ipc", "scalar")
        ds.assert_dialog_hidden()

        ds.click_parse()
        expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(ds.parse_close_button).to_be_visible(timeout=_E2E_TIMEOUT)


# ===================================================================
# 4. Parse → Data Managers navigation
# ===================================================================


class TestParseToDataManagers:
    """After a successful parse, verify Data Managers shows the data."""

    def _parse_and_load(self, page: Page, live_server_url: str) -> DataSourcePage:
        """Full scan → add variable → parse → close dialog."""
        ds = _setup_data_source(page, live_server_url)
        _scan_add_parse_close(ds, _BENCHMARKS_STATS, ["system.cpu.ipc"])
        return ds

    def test_data_managers_shows_data_after_parse(self, page: Page, live_server_url: str) -> None:
        """After parsing, Data Managers Summary tab shows loaded data."""
        self._parse_and_load(page, live_server_url)

        dm = DataManagersPage(page)
        dm.navigate()
        dm.assert_page_header_visible()

        # Should NOT show "no data" warning
        expect(dm.no_data_warning).not_to_be_visible(timeout=15_000)

    def test_data_managers_summary_shows_rows(self, page: Page, live_server_url: str) -> None:
        """After parsing, Summary tab shows row count metric."""
        self._parse_and_load(page, live_server_url)

        dm = DataManagersPage(page)
        dm.navigate()
        dm.assert_has_data()

    def test_data_managers_visualization_tab_has_dataframe(
        self, page: Page, live_server_url: str
    ) -> None:
        """After parsing, Data Visualization tab renders a dataframe."""
        self._parse_and_load(page, live_server_url)

        dm = DataManagersPage(page)
        dm.navigate()
        dm.select_tab("Data Visualization")
        dm.assert_dataframe_visible()

    def test_data_managers_history_is_empty_initially(
        self, page: Page, live_server_url: str
    ) -> None:
        """After parsing but before any transforms, history is empty."""
        self._parse_and_load(page, live_server_url)

        dm = DataManagersPage(page)
        dm.navigate()
        dm.select_tab("Operations History")
        dm.assert_history_empty()


# ===================================================================
# 5. Data Managers — Seeds Reducer (requires random_seed column)
# ===================================================================


class TestSeedsReducerNoSeedColumn:
    """Seeds Reducer with data that has no random_seed column."""

    def test_seeds_reducer_shows_no_random_seed_warning(
        self, page: Page, live_server_url: str
    ) -> None:
        """Seeds Reducer shows warning when no random_seed column exists."""
        ds = _setup_data_source(page, live_server_url)
        _scan_add_parse_close(ds, _SINGLE_STATS, ["simSeconds", "system.cpu.ipc"])

        dm = DataManagersPage(page)
        dm.navigate()
        dm.select_tab("Seeds Reducer")
        dm.assert_seeds_requires_random_seed()


# ===================================================================
# 6. Data Managers — Outlier Remover
# ===================================================================


class TestOutlierRemover:
    """Outlier Remover with parsed data."""

    def _parse_and_navigate(self, page: Page, live_server_url: str) -> DataManagersPage:
        """Parse benchmarks (multiple rows) then go to Data Managers."""
        ds = _setup_data_source(page, live_server_url)
        _scan_add_parse_close(ds, _BENCHMARKS_STATS, ["system.cpu.ipc", "simSeconds"])

        dm = DataManagersPage(page)
        dm.navigate()
        dm.assert_page_header_visible()
        return dm

    def test_outlier_tab_shows_metrics(self, page: Page, live_server_url: str) -> None:
        """Outlier Remover tab shows Min/Q3/Max/Mean metrics."""
        dm = self._parse_and_navigate(page, live_server_url)
        dm.select_tab("Outlier Remover")
        dm.assert_outlier_shows_metrics()

    def test_outlier_apply_shows_result(self, page: Page, live_server_url: str) -> None:
        """Clicking 'Apply Outlier Remover' shows success and preview."""
        dm = self._parse_and_navigate(page, live_server_url)
        dm.select_tab("Outlier Remover")
        dm.apply_outlier_remover()
        dm.assert_success_message_visible()


# ===================================================================
# 7. Data Managers — Preprocessor
# ===================================================================


class TestPreprocessor:
    """Preprocessor creates new columns via arithmetic operations."""

    def _parse_and_navigate(self, page: Page, live_server_url: str) -> DataManagersPage:
        """Parse benchmarks then go to Data Managers."""
        ds = _setup_data_source(page, live_server_url)
        _scan_add_parse_close(ds, _BENCHMARKS_STATS, ["system.cpu.ipc", "simSeconds"])

        dm = DataManagersPage(page)
        dm.navigate()
        dm.assert_page_header_visible()
        return dm

    def test_preprocessor_shows_selectboxes(self, page: Page, live_server_url: str) -> None:
        """Preprocessor tab shows source column and operation selectboxes."""
        dm = self._parse_and_navigate(page, live_server_url)
        dm.select_tab("Preprocessor")
        expect(dm.preproc_src1_selectbox).to_be_visible(timeout=15_000)
        expect(dm.preproc_operation_selectbox).to_be_visible()

    def test_preprocessor_preview_creates_column(self, page: Page, live_server_url: str) -> None:
        """Clicking 'Preview Result' in Preprocessor shows success."""
        dm = self._parse_and_navigate(page, live_server_url)
        dm.select_tab("Preprocessor")
        dm.apply_preprocessor_preview()
        dm.assert_success_message_visible()


# ===================================================================
# 8. Data Managers — Mixer
# ===================================================================


class TestMixer:
    """Mixer merges multiple columns into one."""

    def _parse_and_navigate(self, page: Page, live_server_url: str) -> DataManagersPage:
        """Parse benchmarks then go to Data Managers."""
        ds = _setup_data_source(page, live_server_url)
        _scan_add_parse_close(ds, _BENCHMARKS_STATS, ["system.cpu.ipc", "simSeconds"])

        dm = DataManagersPage(page)
        dm.navigate()
        dm.assert_page_header_visible()
        return dm

    def test_mixer_shows_mode_control(self, page: Page, live_server_url: str) -> None:
        """Mixer tab shows the mode segmented control."""
        dm = self._parse_and_navigate(page, live_server_url)
        dm.select_tab("Mixer")
        expect(dm.mixer_mode_control).to_be_visible(timeout=15_000)

    def test_mixer_shows_column_multiselect(self, page: Page, live_server_url: str) -> None:
        """Mixer tab shows the column selection multiselect."""
        dm = self._parse_and_navigate(page, live_server_url)
        dm.select_tab("Mixer")
        expect(dm.mixer_columns_multiselect).to_be_visible(timeout=15_000)


# ===================================================================
# 9. Cross-page E2E — parse then load from Recent
# ===================================================================


class TestParseAndRecentPool:
    """After parsing, the result CSV appears in Load from Recent."""

    def test_parsed_csv_appears_in_recent(self, page: Page, live_server_url: str) -> None:
        """After parsing, switching to 'Load from Recent' shows the CSV."""
        ds = _setup_data_source(page, live_server_url)
        _scan_add_parse_close(ds, _SINGLE_STATS, ["simSeconds"])

        # Now switch to Recent mode
        ds.select_recent_mode()
        ds.assert_recent_header_visible()
        # Should show at least one CSV file in the pool
        expect(ds.pool_file_count_info).to_be_visible(timeout=15_000)


# ===================================================================
# 10. Screenshots for E2E documentation
# ===================================================================


class TestE2EScreenshots:
    """Capture screenshots of E2E states for documentation."""

    def test_capture_after_scan(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the Data Source page after a successful scan."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.screenshot(screenshot_dir / "e2e_after_scan.png")

    def test_capture_with_variables_added(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the page with variables added after scanning."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.add_manual_variable("simSeconds", "scalar")
        ds.add_manual_variable("system.cpu.ipc", "scalar")
        ds.screenshot(screenshot_dir / "e2e_variables_added.png")

    def test_capture_parse_in_progress(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture the parse dialog during/after parsing."""
        ds = _setup_data_source(page, live_server_url)
        ds.fill_stats_path(str(_SINGLE_STATS))
        ds.fill_stats_pattern("stats.txt")
        ds.scan_and_wait(timeout=_E2E_TIMEOUT)
        ds.add_manual_variable("simSeconds", "scalar")
        ds.click_parse()
        expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
        page.wait_for_timeout(2000)
        ds.screenshot(screenshot_dir / "e2e_parse_dialog.png")

    def test_capture_data_managers_with_data(
        self,
        page: Page,
        live_server_url: str,
        screenshot_dir: Path,
    ) -> None:
        """Capture Data Managers with loaded data."""
        ds = _setup_data_source(page, live_server_url)
        _scan_add_parse_close(ds, _BENCHMARKS_STATS, ["system.cpu.ipc"])

        dm = DataManagersPage(page)
        dm.navigate()
        dm.assert_has_data()
        dm.screenshot(screenshot_dir / "e2e_data_managers_summary.png")
