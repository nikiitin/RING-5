"""E2E tests for settings pills, config inputs, engine switching, and presets.

Uses ``tier2_page`` which provides: CSV loaded + bar plot "E2E Bar" created
with Sort pipeline finalized, axes configured, and Plotly chart visible.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


# ---------------------------------------------------------------------------
# Settings pills & config inputs
# ---------------------------------------------------------------------------


@pytest.mark.xdist_group("e2e_settings")
class TestSettingsPills:
    """Tier 2: Advanced settings pills and config inputs (ordered)."""

    def test_01_advanced_settings_toggle(self, tier2_page: Page) -> None:
        """Toggle advanced settings on and verify settings pills appear."""
        mp = ManagePlotsPage(tier2_page)
        mp.toggle_advanced_settings()
        expect(mp.viz_settings_pills).to_be_visible(timeout=E2E_TIMEOUT)

    def test_02_layout_settings_visible(self, tier2_page: Page) -> None:
        """Layout pill is the default; title and axis-label inputs are visible."""
        mp = ManagePlotsPage(tier2_page)
        layout_pill = mp.viz_settings_pills.get_by_role("button", name="layout")
        expect(layout_pill).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.viz_title_input).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.viz_x_label_input).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.viz_y_label_input).to_be_visible(timeout=E2E_TIMEOUT)

    def test_03_edit_title(self, tier2_page: Page) -> None:
        """Fill title input, refresh plot, chart still visible."""
        mp = ManagePlotsPage(tier2_page)
        mp.viz_title_input.fill("Test Title")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    def test_04_edit_axis_labels(self, tier2_page: Page) -> None:
        """Fill X and Y axis labels, refresh, chart renders."""
        mp = ManagePlotsPage(tier2_page)
        mp.viz_x_label_input.fill("X Label")
        mp.viz_y_label_input.fill("Y Label")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    def test_05_title_value_persisted(self, tier2_page: Page) -> None:
        """Title input retains the value set in test_03."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.viz_title_input).to_have_value("Test Title", timeout=E2E_TIMEOUT)

    def test_06_axis_labels_persisted(self, tier2_page: Page) -> None:
        """Axis label inputs retain the values from test_04."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.viz_x_label_input).to_have_value("X Label", timeout=E2E_TIMEOUT)
        expect(mp.viz_y_label_input).to_have_value("Y Label", timeout=E2E_TIMEOUT)

    def test_07_clear_title(self, tier2_page: Page) -> None:
        """Clear the title, refresh, chart still renders without a title."""
        mp = ManagePlotsPage(tier2_page)
        mp.viz_title_input.fill("")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
        expect(mp.viz_title_input).to_have_value("", timeout=E2E_TIMEOUT)

    def test_08_engine_pills_visible(self, tier2_page: Page) -> None:
        """Engine selector pills are visible with plotly and matplotlib."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)
        plotly_pill = mp.viz_engine_pills.get_by_role("button", name="plotly")
        expect(plotly_pill).to_be_visible(timeout=E2E_TIMEOUT)
        mpl_pill = mp.viz_engine_pills.get_by_role("button", name="matplotlib")
        expect(mpl_pill).to_be_visible(timeout=E2E_TIMEOUT)

    def test_09_switch_to_matplotlib(self, tier2_page: Page) -> None:
        """Select matplotlib engine and verify matplotlib chart renders."""
        mp = ManagePlotsPage(tier2_page)
        mp.select_engine("matplotlib")
        mp.refresh_plot()
        mp.assert_matplotlib_chart_visible()

    def test_10_matplotlib_no_plotly_chart(self, tier2_page: Page) -> None:
        """While matplotlib is active, plotly chart iframe is not visible."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.plotly_chart.first).not_to_be_visible(timeout=E2E_TIMEOUT)

    def test_11_switch_back_to_plotly(self, tier2_page: Page) -> None:
        """Switch back to plotly engine and verify plotly chart renders."""
        mp = ManagePlotsPage(tier2_page)
        mp.select_engine("plotly")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    def test_12_plotly_no_matplotlib_chart(self, tier2_page: Page) -> None:
        """While plotly is active, matplotlib image is not visible."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.matplotlib_chart.first).not_to_be_visible(timeout=E2E_TIMEOUT)

    def test_13_toggle_advanced_off(self, tier2_page: Page) -> None:
        """Toggle advanced settings off; settings pills disappear."""
        mp = ManagePlotsPage(tier2_page)
        mp.toggle_advanced_settings()
        expect(mp.viz_settings_pills).not_to_be_visible(timeout=E2E_TIMEOUT)

    def test_14_chart_visible_without_advanced(self, tier2_page: Page) -> None:
        """Chart remains visible after disabling advanced settings."""
        mp = ManagePlotsPage(tier2_page)
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    def test_15_toggle_advanced_back_on(self, tier2_page: Page) -> None:
        """Re-enable advanced settings; pills reappear."""
        mp = ManagePlotsPage(tier2_page)
        mp.toggle_advanced_settings()
        expect(mp.viz_settings_pills).to_be_visible(timeout=E2E_TIMEOUT)


# ---------------------------------------------------------------------------
# Preset application
# ---------------------------------------------------------------------------


@pytest.mark.xdist_group("e2e_settings_presets")
class TestPresetApplication:
    """Tier 2: Preset selection and application."""

    def test_01_enable_advanced_settings(self, tier2_page: Page) -> None:
        """Enable advanced settings so presets become visible."""
        mp = ManagePlotsPage(tier2_page)
        mp.toggle_advanced_settings()
        expect(mp.viz_settings_pills).to_be_visible(timeout=E2E_TIMEOUT)

    def test_02_preset_pills_visible(self, tier2_page: Page) -> None:
        """Preset pills widget is present on the page."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.viz_preset_pills).to_be_visible(timeout=E2E_TIMEOUT)

    def test_03_chart_renders_after_preset(self, tier2_page: Page) -> None:
        """Chart renders correctly after interacting with preset pills."""
        mp = ManagePlotsPage(tier2_page)
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
