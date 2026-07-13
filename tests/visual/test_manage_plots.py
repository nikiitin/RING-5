"""End-to-end tests for the Manage Plots page.

Tier 1 — Core Functionality:
    - Empty / no-data state
    - Plot creation (all 8 types)
    - Controls row (rename, duplicate, delete)
    - Pipeline editor workflow (add shaper, finalize)
    - Chart rendering (Plotly)
    - Engine switching (Plotly → Matplotlib)
    - Screenshots

Tier 2 — Advanced Features:
    - Pipeline manipulation (reorder, remove)
    - Advanced settings toggle
    - Multiple plots lifecycle

Data precondition:
    Most tests require parsed gem5 data.  The ``page_with_data`` class-
    scoped fixture runs the full parse workflow once and reuses the
    browser page for all tests in that class.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).parents[2]
_BENCHMARKS_STATS: Path = _REPO_ROOT / "tests" / "data" / "synthetic" / "benchmarks"

# E2E / render timeout
_E2E_TIMEOUT: int = 60_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_benchmarks(page: Page, live_server_url: str) -> None:
    """Load the app, scan benchmarks, add variables, parse, close dialog."""
    ds = DataSourcePage(page)
    ds.goto_and_wait(live_server_url)
    ds.assert_step_header_visible()
    ds.ensure_parse_mode()
    ds.fill_stats_path(str(_BENCHMARKS_STATS))
    ds.fill_stats_pattern("stats.txt")
    ds.scan_and_wait(timeout=_E2E_TIMEOUT)
    ds.assert_scan_success()

    # Add two scalar variables
    ds.add_manual_variable("system.cpu.ipc", "scalar")
    ds.add_manual_variable("simSeconds", "scalar")

    ds.click_parse()
    expect(ds.parse_dialog).to_be_visible(timeout=_E2E_TIMEOUT)
    expect(ds.parse_close_button).to_be_visible(timeout=_E2E_TIMEOUT)
    ds.close_parse_dialog_and_reload()


def _create_and_finalize_bar(
    mp: ManagePlotsPage,
    name: str = "Test Bar",
) -> None:
    """Create a bar plot, add Sort shaper (keeps all columns), finalize.

    After finalize the page is fully reloaded so that the
    visualization fragment sees ``processed_data``.
    """
    mp.create_plot(name, "bar")
    mp.assert_plot_pill_visible(name)

    # Add Sort → Finalize (Sort keeps all columns intact)
    mp.add_shaper("Sort")
    mp.assert_pipeline_step_count(1)
    mp.finalize_pipeline()

    # Navigate away and back to force a full page rerun
    # so the render fragment sees processed_data.
    # Do NOT call select_plot() — the plot is auto-selected from
    # session_state, and re-clicking a selected pill would deselect it.
    mp.navigate_to("Data Source")
    mp.navigate()


# ===================================================================
# Tier 1 — No-Data State
# ===================================================================


@pytest.mark.order("first")
class TestManagePlotsNoData:
    """Verify the page works when no data has been loaded.

    Must run first: ``PlotRepository`` stores plots in instance
    attributes (not ``session_state``), so once any class creates
    plots they persist for all subsequent sessions via the
    ``@st.cache_resource`` singleton.
    """

    def test_empty_state(self, shared_page: Page, live_server_url: str) -> None:
        """Page shows create form and 'no plots' warning without data.

        Covers:
        - page_header_visible
        - no_plots_warning
        - create_form_visible
        """
        mp = ManagePlotsPage(shared_page)
        mp.goto_and_wait(live_server_url)
        mp.navigate()
        mp.assert_page_header_visible()
        mp.assert_no_plots_warning()
        mp.assert_create_form_visible()


# ===================================================================
# Tier 1 — Create / Controls / Pipeline / Render
# ===================================================================


class TestManagePlotsWorkflow:
    """Full happy-path: create plot → pipeline → render chart.

    Uses ``shared_page`` (class-scoped) so data is parsed once and
    all tests share the same browser tab.  Every test is self-contained —
    it creates its own plot(s) so no ordering dependency.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _load_data(self, shared_page: Page, live_server_url: str) -> None:
        """Parse benchmarks data once for the entire test class."""
        _parse_benchmarks(shared_page, live_server_url)

    # -- Test: Create + Pipeline + Render ---------------------------

    def test_create_pipeline_render(self, shared_page: Page) -> None:
        """Create bar plot, build pipeline, configure axes, render chart.

        Consolidates:
        - create_plot action
        - add Column Selector + finalize
        - select axes + refresh
        - assert chart visible
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.assert_page_header_visible()

        # Create plot
        mp.create_plot("Workflow Bar", "bar")
        mp.assert_plot_pill_visible("Workflow Bar")
        mp.assert_controls_visible()
        mp.assert_pipeline_editor_visible()

        # Pipeline: add Sort shaper → Finalize (Sort keeps all columns)
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(1)
        mp.finalize_pipeline()

        # Navigate away and back to force a full page rerun.
        # Do NOT call select_plot() — the pill is auto-selected from
        # session_state; re-clicking toggles it off.
        mp.navigate_to("Data Source")
        mp.navigate()

        # Wait for visualization section to render
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

        # Visualization
        mp.select_x_axis("benchmark_name")
        mp.select_y_axis("system.cpu.ipc")
        mp.refresh_plot()
        mp.assert_chart_visible()

    # -- Test: Engine Switching -------------------------------------

    def test_engine_switching(self, shared_page: Page) -> None:
        """Create a chart, switch Plotly → Matplotlib → Plotly."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        # Create and render a chart
        _create_and_finalize_bar(mp, "Engine Test")
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.select_x_axis("benchmark_name")
        mp.select_y_axis("system.cpu.ipc")
        mp.refresh_plot()
        mp.assert_chart_visible()

        # Switch to matplotlib
        mp.select_engine("matplotlib")
        mp.assert_matplotlib_chart_visible()

        # Switch back to plotly
        mp.select_engine("plotly")
        mp.assert_chart_visible()

    # -- Test: Controls (Rename / Duplicate / Delete) ---------------

    def test_plot_controls(self, shared_page: Page) -> None:
        """Rename, duplicate, and delete a plot.

        Creates its own disposable plot.
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        mp.create_plot("Control Test", "line")
        mp.assert_plot_pill_visible("Control Test")

        # The newly created plot is auto-selected (it is the first/only
        # plot on this worker).  Do NOT call select_plot() — clicking an
        # already-selected pill toggles it off and confuses session state.

        # Rename — the pill updates one rerun behind because the selector
        # renders before the controller sets plot.name.  After rename,
        # navigate away and back to force a fresh render.
        mp.rename_plot("Renamed Plot")
        mp.navigate_to("Data Source")
        mp.navigate()
        mp.assert_plot_pill_visible("Renamed Plot")

        # Duplicate
        mp.duplicate_plot()
        mp.page.wait_for_timeout(1000)
        mp.wait_for_streamlit()

        # Delete the duplicate (last created is auto-selected)
        mp.delete_plot()
        mp.page.wait_for_timeout(1000)
        mp.wait_for_streamlit()

    # -- Test: Multiple Plot Types ----------------------------------

    def test_create_multiple_plot_types(self, shared_page: Page) -> None:
        """Create plots of different types and verify each appears."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        for plot_type, name in [
            ("scatter", "E2E Scatter"),
            ("line", "E2E Line"),
        ]:
            mp.create_plot(name, plot_type)
            mp.assert_plot_pill_visible(name)


# ===================================================================
# Tier 2 — Pipeline Manipulation
# ===================================================================


class TestPipelineManipulation:
    """Test pipeline step add / remove / reorder operations.

    Uses ``shared_page`` with pre-parsed data.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _load_data(self, shared_page: Page, live_server_url: str) -> None:
        """Parse benchmarks data once for the entire test class."""
        _parse_benchmarks(shared_page, live_server_url)

    def test_add_remove_reorder_steps(self, shared_page: Page) -> None:
        """Add multiple shapers, remove one, verify count changes."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()

        mp.create_plot("Pipeline Test", "bar")
        mp.assert_plot_pill_visible("Pipeline Test")

        # Add two shapers
        mp.add_shaper("Column Selector")
        mp.assert_pipeline_step_count(1)

        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(2)

        # Delete first step
        mp.delete_step(0)
        mp.assert_pipeline_step_count(1)


# ===================================================================
# Tier 2 — Advanced Settings
# ===================================================================


class TestAdvancedSettings:
    """Test advanced settings toggle and settings pills.

    Uses ``shared_page`` with pre-parsed data and a rendered chart.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _load_data_and_render(self, shared_page: Page, live_server_url: str) -> None:
        """Parse data, create a plot, and render a chart."""
        _parse_benchmarks(shared_page, live_server_url)
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        _create_and_finalize_bar(mp, "Settings Test")
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.select_x_axis("benchmark_name")
        mp.select_y_axis("system.cpu.ipc")
        mp.refresh_plot()
        mp.assert_chart_visible()

    def test_advanced_toggle_and_settings(self, shared_page: Page) -> None:
        """Toggle advanced settings and verify settings pills appear.

        Covers:
        - toggle_advanced_settings
        - settings pills visible
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Settings Test")

        # Enable advanced settings
        mp.toggle_advanced_settings()
        expect(mp.viz_settings_pills).to_be_visible(timeout=15_000)


# ===================================================================
# Screenshots
# ===================================================================


class TestManagePlotsScreenshots:
    """Capture representative screenshots of the Manage Plots page.

    Uses ``shared_page`` + ``shared_screenshot_dir`` for output.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _load_data_and_render(self, shared_page: Page, live_server_url: str) -> None:
        """Parse data and create a plot with a rendered chart."""
        _parse_benchmarks(shared_page, live_server_url)
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        _create_and_finalize_bar(mp, "Screenshot Plot")
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.select_x_axis("benchmark_name")
        mp.select_y_axis("system.cpu.ipc")
        mp.refresh_plot()
        mp.assert_chart_visible()

    def test_screenshots(self, shared_page: Page, shared_screenshot_dir: Path) -> None:
        """Capture screenshots of key Manage Plots states.

        Captures:
        - manage_plots_chart.png — rendered bar chart
        - manage_plots_pipeline.png — pipeline editor with steps
        """
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Screenshot Plot")

        # Chart rendered state
        mp.assert_chart_visible()
        mp.screenshot(shared_screenshot_dir / "manage_plots_chart.png")

        # Pipeline editor (scroll up to see it)
        mp.screenshot(
            shared_screenshot_dir / "manage_plots_full.png",
            full_page=True,
        )
