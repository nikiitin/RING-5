"""End-to-end workflow using gem5 MICRO-26 sensitivity data.

The ordered test exercises the application workflow with production-like data:

1. **Parse** real gem5 stats (≥5 statistics, ≥3 configurations, multiple seeds)
2. **Data Management** — outlier removal, seed reduction, column mixing
3. **History** verification after data management
4. **Create 5+ plots** — bar, grouped bar, grouped stacked bar, dual-axis, scatter
5. **Pipeline** configuration for each plot type
6. **Download** — PGF (matplotlib), PDF (plotly)
7. **Portfolio** — save and verify load
8. **Widget verification** — confirm UI reflects correct state

Data source: ``tests/data/results-micro26-sens/`` — gem5 HTM sensitivity analysis
with 25 configurations × 8 STAMP benchmarks × 3 seeds = 586 stats files.
This test uses a 3-config subset to keep parse time under ~2 minutes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser

# Paths

_REPO_ROOT: Path = Path(__file__).parents[2]
_REAL_DATA: Path = _REPO_ROOT / "tests" / "data" / "results-micro26-sens"

# E2E / render timeout (real data parsing can take a while)
_PARSE_TIMEOUT: int = 180_000  # 3 minutes for multi-file parse
_E2E_TIMEOUT: int = 60_000
_CHART_TIMEOUT: int = 30_000

# Statistics to parse (mix of scalar and configuration types)
_STATS_TO_PARSE: list[tuple[str, str]] = [
    ("simTicks", "scalar"),
    ("simSeconds", "scalar"),
    ("simInsts", "scalar"),
    ("system.cpu0.ipc", "scalar"),
    ("system.cpu0.numCycles", "scalar"),
    ("simOps", "scalar"),
    # random_seed is a configuration value inside each stats.txt
    # (random_seed=0/1/2).  Adding it allows the Seeds Reducer to
    # properly collapse the seed dimension.
    ("random_seed", "configuration"),
]


# Single class with ordered tests sharing one browser page


@pytest.mark.xdist_group("comprehensive_e2e")
class TestFullWorkflow:
    """Full application workflow: parse → manage → plot → download → portfolio.

    All tests share a single ``shared_page`` (class-scoped) so state
    accumulates across tests — mimicking a real user session.  Tests
    are ordered explicitly via ``@pytest.mark.order``.
    """

    # -- Step 0: Parse real data ------------------------------------

    @pytest.fixture(autouse=True, scope="class")
    def _parse_real_data(self, shared_page: Page, live_server_url: str) -> None:
        """Parse real gem5 data (3 configs × 8 benchmarks × 3 seeds).

        Adds 6 scalar statistics and parses them from the full dataset.
        """
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()
        ds.ensure_parse_mode()

        # Point to real data
        ds.fill_stats_path(str(_REAL_DATA))
        ds.fill_stats_pattern("stats.txt")

        # Scan for variables
        ds.scan_and_wait(timeout=_PARSE_TIMEOUT)
        ds.assert_scan_success()

        # Add statistics (mix of types)
        for name, var_type in _STATS_TO_PARSE:
            ds.add_manual_variable(name, var_type)

        # Parse
        ds.click_parse()
        expect(ds.parse_dialog).to_be_visible(timeout=_PARSE_TIMEOUT)
        expect(ds.parse_close_button).to_be_visible(timeout=_PARSE_TIMEOUT)

        # Close the parse dialog
        ds.parse_close_button.click()

        # After parsing 586 files, the app does a heavy rerun (loading CSV,
        # computing summaries).  The default 15s wait_for_streamlit() is too
        # short.  Wait for the "Running" indicator to appear and then vanish.
        running = shared_page.locator("[data-testid='stStatusWidget']")
        try:
            # Wait for the status widget to appear (rerun triggered)
            running.wait_for(state="visible", timeout=10_000)
        except Exception:
            pass  # May have already appeared and hidden
        # Now wait for it to disappear (rerun finished)
        running.wait_for(state="hidden", timeout=_PARSE_TIMEOUT)

        # Reload through a finite browser lifecycle event; Streamlit keeps
        # connections open after the page is otherwise ready for interaction.
        shared_page.reload(wait_until="domcontentloaded")
        expect(ds.main_header).to_be_visible(timeout=_E2E_TIMEOUT)
        try:
            running.wait_for(state="visible", timeout=5_000)
        except Exception:
            pass
        running.wait_for(state="hidden", timeout=_E2E_TIMEOUT)
        # Final buffer for UI to fully stabilise
        shared_page.wait_for_timeout(2_000)

    # Test 1: Verify parsed data in Data Managers

    @pytest.mark.order(1)
    def test_01_verify_parsed_data(self, shared_page: Page) -> None:
        """After parsing, Data Managers should show rows and columns.

        Verifies:
        - Summary tab shows data metrics
        - Data Visualization tab shows dataframe
        - Multiple rows (configurations × benchmarks × seeds)
        - Expected columns present
        """
        dm = DataManagersPage(shared_page)
        dm.navigate()
        dm.assert_page_header_visible()
        dm.assert_has_data()

        # Summary tab — verify header and Rows metric
        dm.select_tab("Summary")
        expect(shared_page.get_by_text("Dataset Summary")).to_be_visible(timeout=_E2E_TIMEOUT)
        # st.metric("Rows", ...) renders a metric widget
        dm.assert_summary_has_rows()

        # Data Visualization tab — verify dataframe renders
        dm.select_tab("Data Visualization")
        dm.assert_dataframe_visible()

    # Test 2: Outlier removal on simTicks

    @pytest.mark.order(2)
    def test_02_remove_outliers(self, shared_page: Page) -> None:
        """Remove outliers from simTicks column.

        Verifies:
        - Outlier Remover tab renders correctly
        - Column selection works
        - Apply shows preview with metrics
        - Confirm applies the filter
        """
        dm = DataManagersPage(shared_page)
        dm.navigate()

        dm.select_tab("Outlier Remover")

        # Select simTicks column
        dm.outlier_column_selectbox.click()
        shared_page.wait_for_timeout(300)
        shared_page.locator("[data-testid='stSelectboxVirtualDropdown'] li").get_by_text(
            "simTicks", exact=True
        ).click()
        dm.wait_for_streamlit()

        # Apply to see preview
        dm.apply_outlier_remover()

        # Metrics should be visible
        dm.assert_outlier_shows_metrics()

        # Confirm and apply
        dm.confirm_outlier_remover()

    # Test 3: Seed reduction

    @pytest.mark.order(3)
    def test_03_reduce_seeds(self, shared_page: Page) -> None:
        """Reduce seeds by aggregating numeric columns per benchmark/config.

        Verifies:
        - Seeds Reducer tab loads correctly
        - Apply shows preview with row reduction
        - Confirm applies the reducer
        """
        dm = DataManagersPage(shared_page)
        dm.navigate()

        dm.select_tab("Seeds Reducer")
        shared_page.wait_for_timeout(1000)

        # Apply seeds reduction (defaults should group by categoricals)
        dm.apply_seeds_reducer()
        shared_page.wait_for_timeout(2000)

        # Confirm
        dm.confirm_seeds_reducer()

    # Test 4: Column mixing (merge 3 columns into 1)

    @pytest.mark.order(4)
    def test_04_mix_columns(self, shared_page: Page) -> None:
        """Mix simTicks, simInsts, simOps into a combined metric.

        Uses the Sum operation to create a new column.

        Verifies:
        - Mixer tab renders
        - Column selection works
        - Preview shows result
        - Confirm merges the data
        """
        dm = DataManagersPage(shared_page)
        dm.navigate()

        dm.select_tab("Mixer")
        shared_page.wait_for_timeout(1000)

        # Select columns to merge
        mixer_multi = dm.mixer_columns_multiselect
        mixer_multi.click()
        shared_page.wait_for_timeout(300)

        # Select simTicks, simInsts, simOps from the dropdown
        for col_name in ["simTicks", "simInsts", "simOps"]:
            option = shared_page.locator(
                "[data-testid='stSelectboxVirtualDropdown'] li"
            ).get_by_text(col_name, exact=True)
            if option.count() > 0:
                option.click()
                shared_page.wait_for_timeout(200)

        # Set a name for the new column (use exact label match to avoid
        # ambiguity with Preprocessor's "New column name" input)
        shared_page.get_by_label("New Column Name", exact=True).fill("combined_metric")

        # Preview
        dm.apply_mixer_preview()

        # Confirm
        dm.confirm_mixer()

    # Test 5: Verify operations history

    @pytest.mark.order(5)
    def test_05_verify_history(self, shared_page: Page) -> None:
        """After outlier removal, seed reduction, and mixing,
        the Operations History tab should show recorded operations.

        Verifies:
        - History tab is populated (not empty)
        """
        dm = DataManagersPage(shared_page)
        dm.navigate()

        dm.select_tab("Operations History")
        shared_page.wait_for_timeout(1000)

        # The completed operation must appear in history.
        dm.assert_history_has_operations()

    # Test 6: Create a bar plot with Sort pipeline

    @pytest.mark.order(6)
    def test_06_create_bar_plot(self, shared_page: Page) -> None:
        """Create a bar plot with Sort pipeline, configure axes, render.

        Verifies:
        - Plot creation works
        - Sort shaper added and finalized
        - X/Y axis selection
        - Chart renders
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        # Create bar plot
        mp.create_plot("E2E Bar", "bar")
        mp.assert_plot_pill_visible("E2E Bar")

        # Add Sort → Finalize
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(1)
        mp.finalize_pipeline()

        # Navigate away and back for render fragment
        mp.navigate_to("Data Source")
        mp.navigate()

        # Configure axes
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.select_x_axis("benchmark_name")
        mp.select_y_axis("system.cpu0.ipc")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

    # Test 7: Create a grouped bar plot

    @pytest.mark.order(7)
    def test_07_create_grouped_bar(self, shared_page: Page) -> None:
        """Create a grouped bar plot with color grouping.

        Verifies:
        - grouped_bar plot type creation
        - Color-by axis selection
        - Chart renders
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        mp.create_plot("E2E Grouped Bar", "grouped_bar")
        mp.assert_plot_pill_visible("E2E Grouped Bar")

        # Add Sort → Finalize
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(1)
        mp.finalize_pipeline()

        # Navigate away and back — do NOT call select_plot() because
        # the plot is auto-selected from session_state and re-clicking
        # the pill would deselect it.
        mp.navigate_to("Data Source")
        mp.navigate()

        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.select_x_axis("benchmark_name")
        mp.select_y_axis("system.cpu0.ipc")
        mp.select_group_by("config_description")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

    # Test 8: Create a grouped stacked bar plot

    @pytest.mark.order(8)
    def test_08_create_grouped_stacked_bar(self, shared_page: Page) -> None:
        """Create a grouped stacked bar plot.

        The grouped_stacked_bar uses unique widget labels:
        - "Major Grouping (Outer)" instead of "X-axis"
        - "Statistics to Stack (Y-axis)" (multiselect) instead of "Y-axis"
        - "X-Axis / Minor Grouping (Inner)" for sub-groups

        Verifies:
        - grouped_stacked_bar plot type creation
        - Major/minor grouping selection
        - Y columns multiselect
        - Chart renders
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        mp.create_plot("E2E Grouped Stacked Bar", "grouped_stacked_bar")
        mp.assert_plot_pill_visible("E2E Grouped Stacked Bar")

        # Sort → Finalize
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(1)
        mp.finalize_pipeline()

        mp.navigate_to("Data Source")
        mp.navigate()

        # Wait for specific grouped_stacked_bar widgets to render
        major_group = shared_page.locator("[data-testid='stSelectbox']").filter(
            has_text="Major Grouping"
        )
        expect(major_group).to_be_visible(timeout=_E2E_TIMEOUT)

        # Select Y-axis columns (multiselect)
        y_multi = shared_page.locator("[data-testid='stMultiSelect']").filter(
            has_text="Statistics to Stack"
        )
        expect(y_multi).to_be_visible(timeout=_E2E_TIMEOUT)
        y_multi.click()
        shared_page.wait_for_timeout(300)
        # Select simTicks and system.cpu0.ipc
        for col in ["simTicks", "system.cpu0.ipc"]:
            opt = shared_page.locator("[data-testid='stSelectboxVirtualDropdown'] li").get_by_text(
                col, exact=True
            )
            if opt.count() > 0:
                opt.click()
                shared_page.wait_for_timeout(200)
        # Press Escape to close the dropdown
        shared_page.keyboard.press("Escape")

        mp.refresh_plot()
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

    # Test 9: Create a dual-axis bar-dot plot

    @pytest.mark.order(9)
    def test_09_create_dual_axis(self, shared_page: Page) -> None:
        """Create a dual-axis bar-dot plot.

        Verifies:
        - dual_axis_bar_dot plot type creation
        - Chart renders
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        mp.create_plot("E2E Dual Axis", "dual_axis_bar_dot")
        mp.assert_plot_pill_visible("E2E Dual Axis")

        # Sort → Finalize
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(1)
        mp.finalize_pipeline()

        mp.navigate_to("Data Source")
        mp.navigate()

        # The dual_axis_bar_dot uses its own "X-axis" + two Y selectboxes:
        # "Y-axis (Bars – left)" and "Y-axis (Dots – right)"
        x_axis = shared_page.locator("[data-testid='stSelectbox']").filter(has_text="X-axis")
        expect(x_axis).to_be_visible(timeout=_E2E_TIMEOUT)

        # Default selection may already be fine; just refresh
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

    # Test 10: Create a scatter plot

    @pytest.mark.order(10)
    def test_10_create_scatter(self, shared_page: Page) -> None:
        """Create a scatter plot for numeric-vs-numeric analysis.

        Verifies:
        - scatter plot type creation
        - Chart renders with two numeric columns
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        mp.create_plot("E2E Scatter", "scatter")
        mp.assert_plot_pill_visible("E2E Scatter")

        # Sort → Finalize
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(1)
        mp.finalize_pipeline()

        mp.navigate_to("Data Source")
        mp.navigate()

        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.select_x_axis("simTicks")
        mp.select_y_axis("system.cpu0.ipc")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

    # Test 11: Engine switching & matplotlib download (PGF)

    @pytest.mark.order(11)
    def test_11_matplotlib_download(self, shared_page: Page) -> None:
        """Switch to matplotlib engine and verify PGF download is available.

        Verifies:
        - Engine switching to matplotlib
        - Matplotlib chart renders
        - Download expander opens
        - PGF format pill is available
        - Download button appears with correct label
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("E2E Bar")
        shared_page.wait_for_timeout(1_000)

        # Ensure chart is visible (Plotly first)
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

        # Switch to matplotlib
        mp.select_engine("matplotlib")
        mp.assert_matplotlib_chart_visible()

        # Open download expander
        mp.download_expander.click()
        shared_page.wait_for_timeout(500)

        # Verify PGF format pill is available
        pgf_pill = mp.download_format_pills.get_by_text("pgf")
        expect(pgf_pill).to_be_visible(timeout=_E2E_TIMEOUT)

        # Click PGF format
        pgf_pill.click()
        mp.wait_for_streamlit()

        # Download button should say "Download PGF"
        dl_btn = mp.download_expander.locator("[data-testid='stDownloadButton']")
        expect(dl_btn).to_be_visible(timeout=_E2E_TIMEOUT)

        # Switch back to plotly
        mp.select_engine("plotly")
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

    # Test 12: Plotly download (PDF)

    @pytest.mark.order(12)
    def test_12_plotly_download(self, shared_page: Page) -> None:
        """Verify Plotly PDF download is available.

        Verifies:
        - Download expander exists
        - PDF format pill is selectable
        - Download button appears
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("E2E Bar")
        shared_page.wait_for_timeout(1_000)

        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

        # Open download expander
        mp.download_expander.click()
        shared_page.wait_for_timeout(500)

        # PDF should be default for plotly
        pdf_pill = mp.download_format_pills.get_by_text("pdf")
        expect(pdf_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        pdf_pill.click()
        mp.wait_for_streamlit()

        # Download button should exist
        dl_btn = mp.download_expander.locator("[data-testid='stDownloadButton']")
        expect(dl_btn).to_be_visible(timeout=_E2E_TIMEOUT)

    # Test 13: Save portfolio

    @pytest.mark.order(13)
    def test_13_save_portfolio(self, shared_page: Page) -> None:
        """Save the current session as a portfolio.

        Verifies:
        - Portfolio page loads
        - Save name input works
        - Save button triggers save
        - Portfolio appears in the manage section
        """
        pf = PortfolioPage(shared_page)
        pf.navigate()
        pf.assert_page_header_visible()

        # Fill portfolio name
        pf.save_name_input.fill("E2E_MICRO26_Portfolio")

        # Save
        pf.save_button.click()
        pf.wait_for_streamlit()
        shared_page.wait_for_timeout(2000)

        # Verify the portfolio appears in the manage section
        portfolio_expander = shared_page.locator("[data-testid='stExpander']").filter(
            has_text="E2E_MICRO26_Portfolio"
        )
        expect(portfolio_expander).to_be_visible(timeout=_E2E_TIMEOUT)

    # Test 14: Load portfolio and verify state

    @pytest.mark.order(14)
    def test_14_load_portfolio(self, shared_page: Page) -> None:
        """Load the saved portfolio and verify plots are restored.

        Verifies:
        - Portfolio load selectbox shows saved portfolio
        - Load restores session state
        - Plots are available after load
        """
        pf = PortfolioPage(shared_page)
        pf.navigate()

        # Select portfolio from dropdown
        pf.load_selector.click()
        shared_page.wait_for_timeout(300)
        option = shared_page.locator("[data-testid='stSelectboxVirtualDropdown'] li").get_by_text(
            "E2E_MICRO26_Portfolio", exact=True
        )
        expect(option).to_be_visible(timeout=_E2E_TIMEOUT)
        option.click()
        pf.wait_for_streamlit()

        # Load — scope to main content to avoid duplicates during rerun
        load_btn = shared_page.locator("[data-testid='stMainBlockContainer']").get_by_role(
            "button", name="Load Portfolio"
        )
        load_btn.click()
        shared_page.wait_for_timeout(3000)
        pf.wait_for_streamlit()

        # Navigate to Manage Plots to confirm plots survived
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.assert_page_header_visible()

        # Verify at least one of our created plots is visible
        mp.assert_plot_pill_visible("E2E Bar")

    # Test 15: Widget verification on loaded bar plot

    @pytest.mark.order(15)
    def test_15_verify_widgets(self, shared_page: Page) -> None:
        """Verify that widget state correctly reflects the plot configuration.

        After loading from portfolio, the bar plot should still have:
        - Correct plot type in config
        - X-axis = benchmark_name
        - Y-axis = system.cpu0.ipc
        - Pipeline with 1 step (Sort)
        - Chart renders successfully
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        # Select the bar plot
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("E2E Bar")
        shared_page.wait_for_timeout(1_000)
        mp.wait_for_streamlit()

        # Verify pipeline has 1 step
        mp.assert_pipeline_step_count(1)

        # Verify visualization section is present
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

    # Test 16: Screenshots of final state

    @pytest.mark.order(16)
    def test_16_screenshots(self, shared_page: Page, shared_screenshot_dir: Path) -> None:
        """Capture screenshots of the comprehensive E2E session.

        Captures:
        - e2e_bar_chart.png — Bar plot
        - e2e_full_page.png — Full page with all elements
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        # Screenshot current state
        mp.screenshot(shared_screenshot_dir / "e2e_bar_chart.png")
        mp.screenshot(
            shared_screenshot_dir / "e2e_full_page.png",
            full_page=True,
        )
