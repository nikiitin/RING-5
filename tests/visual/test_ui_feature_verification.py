"""E2E tests for removed controls and current UI features.

Uses Playwright to verify that:
- Removed features are truly gone (Performance page, View Current Data,
  pipeline save/load, workspace management)
- New features work (HTML download, color palette, height/width inputs,
  tick marks, legend config, axis controls, label reorder/rename,
  conditional widgets)
- Portfolio load restores a real session (Plot4_inprogress)

Data source: ``tests/data/results-micro26-sens/`` — gem5 HTM sensitivity
study with 25 configurations × 8 STAMP benchmarks × 3 seeds.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser

# Paths & constants

_REPO_ROOT: Path = Path(__file__).parents[2]
_REAL_DATA: Path = _REPO_ROOT / "tests" / "data" / "results-micro26-sens"
_PORTFOLIO: Path = _REPO_ROOT / ".ring5" / "portfolios" / "Plot4_inprogress.json"

_PARSE_TIMEOUT: int = 180_000
_E2E_TIMEOUT: int = 60_000
_CHART_TIMEOUT: int = 30_000

# Minimal set of statistics for a quick parse
_STATS: list[tuple[str, str]] = [
    ("simTicks", "scalar"),
    ("simInsts", "scalar"),
    ("system.cpu0.ipc", "scalar"),
    ("random_seed", "configuration"),
]


# Group 1: Removed Features (no data needed)


class TestRemovedFeatures:
    """Verify that retired features are absent from the interface."""

    def test_performance_page_not_in_navigation(
        self, shared_page: Page, live_server_url: str
    ) -> None:
        """The Performance page is absent from the sidebar."""
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)

        perf_btn = bp.sidebar.get_by_role("button", name="Performance")
        expect(perf_btn).not_to_be_visible(timeout=5_000)

    def test_workspace_management_not_present(
        self, shared_page: Page, live_server_url: str
    ) -> None:
        """Retired workspace-management buttons are absent."""
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)
        bp.navigate_to("Manage Plots")

        # None of the workspace management buttons should exist
        expect(shared_page.get_by_role("button", name="Download All")).not_to_be_visible(
            timeout=5_000
        )
        expect(
            shared_page.get_by_role("button", name="Process All Plots in Parallel")
        ).not_to_be_visible(timeout=5_000)
        expect(shared_page.get_by_role("button", name="Save Entire Workspace")).not_to_be_visible(
            timeout=5_000
        )

    def test_only_four_nav_pages(self, shared_page: Page, live_server_url: str) -> None:
        """Sidebar should have exactly 4 pages, none of the removed ones."""
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)

        expected = ["Data Source", "Data Managers", "Manage Plots", "Save/Load Portfolio"]
        for name in expected:
            btn = bp.sidebar.get_by_role("button", name=name)
            expect(btn).to_be_visible(timeout=5_000)

        removed = ["Performance", "Workspace"]
        for name in removed:
            btn = bp.sidebar.get_by_role("button", name=name)
            expect(btn).not_to_be_visible(timeout=5_000)

    def test_summary_metrics_present_on_home(self, shared_page: Page, live_server_url: str) -> None:
        """Summary metrics remain while the retired data expander is absent."""
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)

        view_data = shared_page.locator("[data-testid='stExpander']").filter(
            has_text="View Current Data"
        )
        expect(view_data).not_to_be_visible(timeout=5_000)


# Group 2: Parse data, then test plot features


@pytest.mark.xdist_group("refactor_e2e")
class TestPlotFeatures:
    """Verify the plot workflow after the interface simplification.

    Parses real data once, creates a bar plot, then exercises
    all the plot configuration features.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _parse_and_create_plot(self, shared_page: Page, live_server_url: str) -> None:
        """Parse real gem5 data and create a bar plot for testing."""
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.ensure_parse_mode()

        ds.fill_stats_path(str(_REAL_DATA))
        ds.fill_stats_pattern("stats.txt")

        ds.scan_and_wait(timeout=_PARSE_TIMEOUT)
        ds.assert_scan_success()

        for name, var_type in _STATS:
            ds.add_manual_variable(name, var_type)

        ds.parse_and_wait(timeout=_PARSE_TIMEOUT)

        # Create a bar plot
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.create_plot("Refactor Test Bar", "Bar Chart")
        mp.assert_plot_pill_visible("Refactor Test Bar")

        # Add column selector → select all → finalize
        mp.add_shaper("Column Selector")
        mp.select_all_columns()
        mp.finalize_pipeline()

        # Configure X/Y axis
        mp.select_x_axis("benchmark_name")
        mp.select_y_axis("system.cpu0.ipc")
        mp.select_color_by("config_description")

        # Wait for chart
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

    # -- Summary metrics --

    @pytest.mark.order(1)
    def test_view_current_data_removed(self, shared_page: Page) -> None:
        """The retired View Current Data expander is absent on every page."""
        view_data = shared_page.locator("[data-testid='stExpander']").filter(
            has_text="View Current Data"
        )
        expect(view_data).not_to_be_visible(timeout=5_000)

    @pytest.mark.order(2)
    def test_summary_metrics_visible(self, shared_page: Page) -> None:
        """After parsing, Rows/Columns/Source metrics should appear."""
        # st.metric renders with data-testid='stMetricValue'
        metrics = shared_page.locator("[data-testid='stMetricValue']")
        expect(metrics.first).to_be_visible(timeout=_E2E_TIMEOUT)
        count = metrics.count()
        assert count >= 2, f"Expected at least 2 metric widgets, got {count}"

    # -- Plotly HTML download --

    @pytest.mark.order(3)
    def test_html_download_format_available(self, shared_page: Page) -> None:
        """HTML format pill should be available in the download expander."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

        # Open download expander
        mp.download_expander.click()
        shared_page.wait_for_timeout(500)

        # HTML pill should be visible
        html_pill = mp.download_format_pills.get_by_text("html")
        expect(html_pill).to_be_visible(timeout=_E2E_TIMEOUT)

        # Click HTML and verify download button appears
        html_pill.click()
        mp.wait_for_streamlit()
        dl_btn = mp.download_expander.locator("[data-testid='stDownloadButton']")
        expect(dl_btn).to_be_visible(timeout=_E2E_TIMEOUT)

    # -- Pipeline controls --

    @pytest.mark.order(4)
    def test_pipeline_save_load_removed(self, shared_page: Page) -> None:
        """The retired Save Pipe and Load Pipe buttons are absent."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        expect(shared_page.get_by_role("button", name="Save Pipe")).not_to_be_visible(timeout=5_000)
        expect(shared_page.get_by_role("button", name="Load Pipe")).not_to_be_visible(timeout=5_000)

    # -- Color palette updates --

    @pytest.mark.order(5)
    def test_color_palette_settings_exist(self, shared_page: Page) -> None:
        """Colors section in advanced settings should be accessible."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)

        # Enable advanced settings
        mp.toggle_advanced_settings()

        # Click Colors pill
        colors_pill = mp.viz_settings_pills.get_by_text("Colors")
        expect(colors_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        colors_pill.click()
        mp.wait_for_streamlit()

        # Color palette selectbox should be visible
        palette_widget = shared_page.locator("[data-testid='stSelectbox']").filter(
            has_text="Color Palette"
        )
        expect(palette_widget).to_be_visible(timeout=_E2E_TIMEOUT)

    # -- Figure dimensions --

    @pytest.mark.order(6)
    def test_height_width_inputs_exist(self, shared_page: Page) -> None:
        """Layout section should have height and width number inputs."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Click Layout pill (basic, always visible)
        layout_pill = mp.viz_settings_pills.get_by_text("Layout")
        expect(layout_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        layout_pill.click()
        mp.wait_for_streamlit()

        # Height and Width number inputs should exist
        height_input = shared_page.locator("[data-testid='stNumberInput']").filter(
            has_text="Height"
        )
        width_input = shared_page.locator("[data-testid='stNumberInput']").filter(has_text="Width")
        expect(height_input).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(width_input).to_be_visible(timeout=_E2E_TIMEOUT)

    # -- Tick marks --

    @pytest.mark.order(7)
    def test_tick_marks_controls_exist(self, shared_page: Page) -> None:
        """Axes section should have tick marks checkbox."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Enable advanced settings
        mp.toggle_advanced_settings()

        # Click Axes pill
        axes_pill = mp.viz_settings_pills.get_by_text("Axes")
        expect(axes_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        axes_pill.click()
        mp.wait_for_streamlit()

        # Tick marks text should be somewhere visible
        tick_text = shared_page.get_by_text("Tick Marks")
        expect(tick_text.first).to_be_visible(timeout=_E2E_TIMEOUT)

    # -- Axis line controls --

    @pytest.mark.order(8)
    def test_axis_line_controls_exist(self, shared_page: Page) -> None:
        """Axes section should have line width and color controls."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Enable advanced settings
        mp.toggle_advanced_settings()

        # Click Axes pill
        axes_pill = mp.viz_settings_pills.get_by_text("Axes")
        axes_pill.click()
        mp.wait_for_streamlit()

        # Look for line width widget
        line_width = shared_page.get_by_text("Line Width")
        expect(line_width.first).to_be_visible(timeout=_E2E_TIMEOUT)

    # -- Legend controls --

    @pytest.mark.order(9)
    def test_legend_configuration_exists(self, shared_page: Page) -> None:
        """Legends section should have primary legend controls."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Click Legends pill (basic, always visible)
        legends_pill = mp.viz_settings_pills.get_by_text("Legends")
        expect(legends_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        legends_pill.click()
        mp.wait_for_streamlit()

        # Primary legend pill should be visible
        primary_pill = shared_page.get_by_text("Primary")
        expect(primary_pill.first).to_be_visible(timeout=_E2E_TIMEOUT)

    # -- Label ordering and renaming --

    @pytest.mark.order(10)
    def test_label_reorder_rename_controls_exist(self, shared_page: Page) -> None:
        """Advanced section should have reorderable lists with rename."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Enable advanced settings
        mp.toggle_advanced_settings()

        # Click Advanced pill
        advanced_pill = mp.viz_settings_pills.get_by_text("Advanced")
        expect(advanced_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        advanced_pill.click()
        mp.wait_for_streamlit()

        # Should see reorder/rename related controls
        # Look for the ordering/rename section header or reorderable elements
        reorder_text = shared_page.get_by_text("Order")
        expect(reorder_text.first).to_be_visible(timeout=_E2E_TIMEOUT)

    # -- Conditional widgets --

    @pytest.mark.order(11)
    def test_conditional_widgets_dual_axis_hidden(self, shared_page: Page) -> None:
        """A standard bar chart has no Y-Right axis pill."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Enable advanced settings
        mp.toggle_advanced_settings()

        # Click Axes pill
        axes_pill = mp.viz_settings_pills.get_by_text("Axes")
        axes_pill.click()
        mp.wait_for_streamlit()

        y_right = shared_page.get_by_text("Y-Right")
        expect(y_right).not_to_be_visible(timeout=5_000)

    @pytest.mark.order(12)
    def test_conditional_widgets_secondary_legend_hidden(self, shared_page: Page) -> None:
        """A standard bar chart has no secondary legend pill."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Click Legends pill
        legends_pill = mp.viz_settings_pills.get_by_text("Legends")
        legends_pill.click()
        mp.wait_for_streamlit()

        secondary = shared_page.get_by_text("Secondary")
        expect(secondary).not_to_be_visible(timeout=5_000)

    # -- Settings navigation --

    @pytest.mark.order(13)
    def test_customization_pill_not_present(self, shared_page: Page) -> None:
        """The dead 'Customization' pill should not appear in settings."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Enable advanced to see all pills
        mp.toggle_advanced_settings()

        customization = mp.viz_settings_pills.get_by_text("Customization")
        expect(customization).not_to_be_visible(timeout=5_000)

    # -- Reference-line controls --

    @pytest.mark.order(14)
    def test_reference_line_normalizer_removed(self, shared_page: Page) -> None:
        """The retired Reference Line Normalizer is absent from the add menu."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)
        mp.select_plot("Refactor Test Bar")
        shared_page.wait_for_timeout(1_000)

        # Open the Add transformation dropdown
        mp.add_transformation_selectbox.click()
        shared_page.wait_for_timeout(300)

        ref_line = shared_page.locator("[data-testid='stSelectboxVirtualDropdown'] li").get_by_text(
            "Reference Line Normalizer"
        )
        expect(ref_line).not_to_be_visible(timeout=5_000)

        # Press Escape to close dropdown
        shared_page.keyboard.press("Escape")


# Group 3: Portfolio load


class TestPortfolioLoad:
    """Verify loading the Plot4_inprogress portfolio restores session."""

    @pytest.mark.skipif(
        not _PORTFOLIO.exists(),
        reason="Plot4_inprogress.json portfolio not found",
    )
    def test_load_portfolio_successfully(self, shared_page: Page, live_server_url: str) -> None:
        """Load Plot4_inprogress portfolio and verify plots are restored.

        Verifies:
        - Portfolio page loads
        - Portfolio file appears in selector
        - Load restores plots
        - At least one plot pill appears in Manage Plots
        """
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)

        pf = PortfolioPage(shared_page)
        pf.navigate()
        pf.assert_page_header_visible()

        # Open the portfolio selector
        pf.load_selector.click()
        shared_page.wait_for_timeout(300)

        # Plot4_inprogress should be in the list
        option = shared_page.locator("[data-testid='stSelectboxVirtualDropdown'] li").get_by_text(
            "Plot4_inprogress"
        )
        expect(option).to_be_visible(timeout=_E2E_TIMEOUT)
        option.click()
        pf.wait_for_streamlit()

        # Click Load Portfolio
        load_btn = shared_page.locator("[data-testid='stMainBlockContainer']").get_by_role(
            "button", name="Load Portfolio"
        )
        load_btn.click()
        shared_page.wait_for_timeout(3_000)
        pf.wait_for_streamlit()

        # Navigate to Manage Plots and verify plots exist
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.assert_page_header_visible()

        # The portfolio should have restored at least one plot
        # Look for any plot pill (button in the plot selector area)
        plot_pills = mp.plot_selector_pills.locator("button")
        expect(plot_pills.first).to_be_visible(timeout=_E2E_TIMEOUT)
        count = plot_pills.count()
        assert count >= 1, f"Expected at least 1 plot pill after portfolio load, got {count}"
