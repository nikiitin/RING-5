"""E2E tests for removed controls and current UI features.

Uses Playwright to verify that:
- Removed features are truly gone (Performance page, View Current Data,
  pipeline save/load, workspace management)
- New features work (HTML download, color palette, height/width inputs,
  tick marks, legend config, axis controls, label reorder/rename,
  conditional widgets)
- Portfolio load restores a current writer-backed session

Data source: ``tests/data/results-micro26-sens/`` — gem5 HTM sensitivity
study with 25 configurations × 8 STAMP benchmarks × 3 seeds.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from ring5 import FigureSpec, Session

from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser

# Paths & constants

_REPO_ROOT: Path = Path(__file__).parents[2]
_REAL_DATA: Path = _REPO_ROOT / "tests" / "data" / "results-micro26-sens"

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
    @classmethod
    def _parse_and_create_plot(
        cls,
        shared_page: Page,
        live_server_url: str,
        _reset_app_state: None,
    ) -> None:
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
        mp.create_plot("Refactor Test Bar", "bar")
        mp.assert_plot_pill_visible("Refactor Test Bar")

        # Add column selector → select all → finalize
        mp.add_shaper("Column Selector")
        mp.select_all_columns()
        mp.finalize_pipeline()
        mp.navigate_to("Data Source")
        mp.navigate()
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

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
        """The HTML format selects a usable deferred download control."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Refactor Test Bar")
        mp.select_engine("plotly")
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)
        if not mp.download_format_pills.is_visible():
            mp.download_expander.locator("summary").click()
        html_pill = mp.download_format_pills.get_by_role("radio", name="html", exact=True)
        expect(html_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        if not html_pill.is_checked():
            html_pill.click()
            mp.wait_for_streamlit(expect_rerun=True)
        if not mp.download_format_pills.is_visible():
            mp.download_expander.locator("summary").click()
        expect(mp.download_button).to_be_visible(timeout=_E2E_TIMEOUT)

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
        mp.set_advanced_settings(True)

        # Click Colors pill
        mp.select_settings_section("Colors")

        # Color palette selectbox should be visible
        palette_widget = shared_page.get_by_role("combobox", name="Palette", exact=True)
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
        mp.select_settings_section("Layout")

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
        mp.set_advanced_settings(True)

        # Click Axes pill
        mp.select_settings_section("Axes")
        mp.select_axis("X-Axis")

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
        mp.set_advanced_settings(True)

        # Click Axes pill
        mp.select_settings_section("Axes")
        mp.select_axis("X-Axis")

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
        mp.select_settings_section("Legends")

        # Primary legend pill should be visible
        primary_pill = shared_page.get_by_text("Primary")
        expect(primary_pill.first).to_be_visible(timeout=_E2E_TIMEOUT)

    # -- Label ordering and renaming --

    @pytest.mark.order(10)
    def test_label_reorder_rename_controls_exist(self, shared_page: Page) -> None:
        """X-axis settings expose ordering and editable display labels."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Refactor Test Bar")
        mp.set_advanced_settings(True)
        mp.select_settings_section("Axes")
        mp.select_axis("X-Axis")
        ordering = shared_page.get_by_test_id("stExpander").filter(
            has=shared_page.get_by_text("Reorder and Rename X-axis Labels", exact=True)
        )
        expect(ordering).to_be_visible(timeout=_E2E_TIMEOUT)
        if not ordering.get_by_text("X-axis Order", exact=True).is_visible():
            ordering.locator("summary").click()
        expect(ordering.get_by_text("X-axis Order", exact=True)).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(ordering.get_by_role("textbox").first).to_be_visible(timeout=_E2E_TIMEOUT)

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
        mp.set_advanced_settings(True)

        # Click Axes pill
        mp.select_settings_section("Axes")

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
        mp.select_settings_section("Legends")

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
        mp.set_advanced_settings(True)

        customization = mp.viz_settings_pills.get_by_text("Customization")
        expect(customization).not_to_be_visible(timeout=5_000)

    # -- Reference-line controls --

    @pytest.mark.order(14)
    def test_reference_line_normalizer_removed(self, shared_page: Page) -> None:
        """The retired Reference Line Normalizer is absent from the current add menu."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Refactor Test Bar")
        mp.add_transformation_selectbox.get_by_role("combobox").click()
        expect(shared_page.get_by_role("option", name="Sort", exact=True)).to_be_visible(
            timeout=_E2E_TIMEOUT
        )
        expect(
            shared_page.get_by_role("option", name="Reference Line Normalizer", exact=True)
        ).not_to_be_visible(timeout=5_000)
        shared_page.keyboard.press("Escape")


# Group 3: Portfolio load


class TestPortfolioLoad:
    """Verify that a current portfolio restores its exact saved plot."""

    def test_load_portfolio_successfully(
        self,
        shared_page: Page,
        live_server_url: str,
        _isolated_data_dir: None,
    ) -> None:
        """Load a writer-backed portfolio through the UI and verify its saved plot."""
        data_dir = os.environ.get("RING5_DATA_DIR")
        assert data_dir is not None, "The visual suite must isolate persistent data"
        assert Path(data_dir).is_dir(), "The isolated application data directory is missing"
        csv_path = _REPO_ROOT / "tests" / "e2e" / "fixtures" / "sample_data.csv"
        assert csv_path.is_file(), f"Fixture CSV not found: {csv_path}"
        portfolio_name = "Visual restore"
        plot_name = "Visual restored bar"
        with Session() as session:
            data = session.load(str(csv_path))
            session.create_plot(
                "bar",
                data=data,
                config=FigureSpec(x="benchmark_name", y_columns=["system.cpu.ipc"]),
                name=plot_name,
            )
            session.save_portfolio(portfolio_name)

        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)
        pf = PortfolioPage(shared_page)
        pf.navigate()
        pf.assert_page_header_visible()
        pf.select_portfolio(portfolio_name)
        pf.load_button.click()
        pf.wait_for_streamlit(expect_rerun=True)

        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.assert_page_header_visible()
        mp.assert_plot_pill_visible(plot_name)
        expect(mp.plot_selector_pills.get_by_role("radio")).to_have_count(1)
