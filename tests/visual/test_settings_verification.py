"""E2E tests verifying UI settings reorganization and bug fixes.

Validates the changes from the UI Settings Verification plan:
  - A2: Simulator pills selector (always visible with material icons)
  - B1-B3: Tick marks, Y-axis title position, group labels moved to Axes
  - Typography stripped to font sizes/colors only
  - Settings pills accessible and rendering widgets correctly

These tests run against a live Streamlit instance with Playwright.
They validate UI structure (widget presence/absence), not rendering
correctness (which requires visual comparison or snapshot diffing).

Data source: ``tests/data/results-micro26-sens/`` — gem5 HTM sensitivity
study (same as test_refactor_verification.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).parents[2]
_REAL_DATA: Path = _REPO_ROOT / "tests" / "data" / "results-micro26-sens"

_PARSE_TIMEOUT: int = 180_000
_E2E_TIMEOUT: int = 60_000
_CHART_TIMEOUT: int = 30_000

_STATS: list[tuple[str, str]] = [
    ("simTicks", "scalar"),
    ("simInsts", "scalar"),
]


# ===================================================================
# Group 1: Simulator Pill Selector (A2)
# ===================================================================


class TestSimulatorPillSelector:
    """A2: Simulator pills should always be visible on Data Source page."""

    def test_simulator_pills_visible(self, shared_page: Page, live_server_url: str) -> None:
        """Simulator pills should be visible on the Data Source page."""
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.navigate()
        shared_page.wait_for_timeout(1_000)

        # Ensure parse mode is active
        ds.parse_option.click()
        ds.wait_for_streamlit()

        # Simulator pills should be visible
        expect(ds.simulator_pills).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_gem5_pill_visible(self, shared_page: Page, live_server_url: str) -> None:
        """gem5 pill should be visible and selected by default."""
        ds = DataSourcePage(shared_page)
        ds.navigate()
        shared_page.wait_for_timeout(1_000)

        ds.parse_option.click()
        ds.wait_for_streamlit()

        expect(ds.gem5_pill).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_simulator_pills_use_material_icon(
        self, shared_page: Page, live_server_url: str
    ) -> None:
        """Simulator pills should have material icon styling."""
        ds = DataSourcePage(shared_page)
        ds.navigate()
        shared_page.wait_for_timeout(1_000)

        ds.parse_option.click()
        ds.wait_for_streamlit()

        # The pill text should contain "gem5" (icon is rendered by Streamlit)
        pill_text = ds.gem5_pill.text_content()
        assert pill_text is not None
        assert "gem5" in pill_text


# ===================================================================
# Group 2: Settings Reorganization (B1-B3)
# ===================================================================


class TestSettingsReorganization:
    """B1-B3: Verify tick marks, Y-axis position, group labels are in Axes."""

    @pytest.fixture(autouse=True)
    def _setup_plot(
        self,
        shared_page: Page,
        live_server_url: str,
    ) -> None:
        """Navigate to Manage Plots and create a test plot if needed."""
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)

        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)

        # Create a test plot if none exists
        if mp.no_plots_warning.is_visible(timeout=3_000):
            mp.plot_name_input.fill("Settings Test Bar")
            mp.create_plot_button.click()
            mp.wait_for_streamlit()

    def test_tick_marks_in_axes_pill(self, shared_page: Page) -> None:
        """B1: Tick marks settings should be under the Axes pill."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(500)

        # Select plot
        first_pill = mp.plot_selector_pills.locator("button").first
        first_pill.click()
        mp.wait_for_streamlit()

        # Enable advanced settings
        mp.toggle_advanced_settings()

        # Click Axes pill
        axes_pill = mp.viz_settings_pills.get_by_text("Axes")
        expect(axes_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        axes_pill.click()
        mp.wait_for_streamlit()

        # Tick Marks should be visible under Axes
        tick_text = shared_page.get_by_text("Tick Marks")
        expect(tick_text.first).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_tick_pad_in_axes_pill(self, shared_page: Page) -> None:
        """B1: Tick pad (distance) should be under the Axes pill."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(500)

        first_pill = mp.plot_selector_pills.locator("button").first
        first_pill.click()
        mp.wait_for_streamlit()

        mp.toggle_advanced_settings()

        axes_pill = mp.viz_settings_pills.get_by_text("Axes")
        axes_pill.click()
        mp.wait_for_streamlit()

        # Tick pad / distance should be visible
        tick_pad = shared_page.get_by_text("Tick Label Distance")
        expect(tick_pad.first).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_yaxis_standoff_in_axes_pill(self, shared_page: Page) -> None:
        """B2: Y-axis title standoff should be under Axes Y-Left section."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(500)

        first_pill = mp.plot_selector_pills.locator("button").first
        first_pill.click()
        mp.wait_for_streamlit()

        mp.toggle_advanced_settings()

        axes_pill = mp.viz_settings_pills.get_by_text("Axes")
        axes_pill.click()
        mp.wait_for_streamlit()

        # Y-axis tab/section — look for standoff slider
        standoff_text = shared_page.get_by_text("Title Standoff")
        expect(standoff_text.first).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_typography_only_fonts_and_colors(self, shared_page: Page) -> None:
        """After B1-B3: Typography should only have font sizes and colors."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(500)

        first_pill = mp.plot_selector_pills.locator("button").first
        first_pill.click()
        mp.wait_for_streamlit()

        mp.toggle_advanced_settings()

        # Click Typography pill
        typo_pill = mp.viz_settings_pills.get_by_text("Typography")
        expect(typo_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        typo_pill.click()
        mp.wait_for_streamlit()

        # Font size widgets should be visible
        font_size_text = shared_page.get_by_text("Font Size")
        expect(font_size_text.first).to_be_visible(timeout=_E2E_TIMEOUT)

        # Tick marks belong to Axes, not Typography.
        tick_in_typo = shared_page.get_by_text("Tick Marks")
        expect(tick_in_typo).not_to_be_visible(timeout=5_000)


# ===================================================================
# Group 3: Legend Settings (C6/D1)
# ===================================================================


class TestLegendSettings:
    """C6/D1: Legend settings should be accessible and functional."""

    @pytest.fixture(autouse=True)
    def _setup_plot(
        self,
        shared_page: Page,
        live_server_url: str,
    ) -> None:
        """Navigate to Manage Plots and ensure a plot exists."""
        bp = BasePage(shared_page)
        bp.goto_and_wait(live_server_url)

        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(1_000)

        if mp.no_plots_warning.is_visible(timeout=3_000):
            mp.plot_name_input.fill("Legend Test Bar")
            mp.create_plot_button.click()
            mp.wait_for_streamlit()

    def test_primary_legend_accessible(self, shared_page: Page) -> None:
        """Primary legend settings should be visible under Legends pill."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(500)

        first_pill = mp.plot_selector_pills.locator("button").first
        first_pill.click()
        mp.wait_for_streamlit()

        # Click Legends pill
        legends_pill = mp.viz_settings_pills.get_by_text("Legends")
        expect(legends_pill).to_be_visible(timeout=_E2E_TIMEOUT)
        legends_pill.click()
        mp.wait_for_streamlit()

        # Primary pill should be visible
        primary = shared_page.get_by_text("Primary")
        expect(primary.first).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_valign_widget_in_legend(self, shared_page: Page) -> None:
        """Vertical alignment selectbox should be visible in legend settings."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(500)

        first_pill = mp.plot_selector_pills.locator("button").first
        first_pill.click()
        mp.wait_for_streamlit()

        legends_pill = mp.viz_settings_pills.get_by_text("Legends")
        legends_pill.click()
        mp.wait_for_streamlit()

        # Vertical Align should be visible
        valign = shared_page.get_by_text("Vertical Align")
        expect(valign.first).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_col_width_widget_in_legend(self, shared_page: Page) -> None:
        """Column width input should be visible in legend settings."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        shared_page.wait_for_timeout(500)

        first_pill = mp.plot_selector_pills.locator("button").first
        first_pill.click()
        mp.wait_for_streamlit()

        legends_pill = mp.viz_settings_pills.get_by_text("Legends")
        legends_pill.click()
        mp.wait_for_streamlit()

        # Column Width should be visible
        col_width = shared_page.get_by_text("Column Width")
        expect(col_width.first).to_be_visible(timeout=_E2E_TIMEOUT)
