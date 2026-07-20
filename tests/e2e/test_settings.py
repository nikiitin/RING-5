"""E2E tests for settings pills, config inputs, and engine switching.

Uses ``tier2_page`` which provides: CSV loaded + bar plot "E2E Bar" created
with Sort pipeline finalized, axes configured, and Plotly chart visible.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


# Settings pills & config inputs


@pytest.mark.xdist_group("e2e_settings")
class TestSettingsPills:
    """Tier 2: Advanced settings pills and config inputs (ordered)."""

    @pytest.mark.order(1)
    def test_01_advanced_settings_toggle(self, tier2_page: Page) -> None:
        """Toggle advanced settings on; the advanced-section pills appear.

        The basic Layout/Typography/Legends pills are always visible, so we
        assert on an advanced-only section pill ('Colors') to verify the
        toggle's effect.
        """
        mp = ManagePlotsPage(tier2_page)
        mp.toggle_advanced_settings()
        expect(mp.viz_advanced_section_pill).to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_layout_settings_visible(self, tier2_page: Page) -> None:
        """Layout pill is the default; title and axis-label inputs are visible."""
        mp = ManagePlotsPage(tier2_page)
        layout_pill = mp.viz_settings_pills.get_by_role("radio", name="Layout")
        expect(layout_pill).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.viz_title_input).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.viz_x_label_input).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.viz_y_label_input).to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(3)
    def test_03_edit_title(self, tier2_page: Page) -> None:
        """Fill title input, refresh plot, chart still visible."""
        mp = ManagePlotsPage(tier2_page)
        mp.viz_title_input.fill("Test Title")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    @pytest.mark.order(4)
    def test_04_edit_axis_labels(self, tier2_page: Page) -> None:
        """Fill X and Y axis labels, refresh, chart renders."""
        mp = ManagePlotsPage(tier2_page)
        mp.viz_x_label_input.fill("X Label")
        mp.viz_y_label_input.fill("Y Label")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    @pytest.mark.order(5)
    def test_05_title_value_persisted(self, tier2_page: Page) -> None:
        """Title input retains the value set in test_03."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.viz_title_input).to_have_value("Test Title", timeout=E2E_TIMEOUT)

    @pytest.mark.order(6)
    def test_06_axis_labels_persisted(self, tier2_page: Page) -> None:
        """Axis label inputs retain the values from test_04."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.viz_x_label_input).to_have_value("X Label", timeout=E2E_TIMEOUT)
        expect(mp.viz_y_label_input).to_have_value("Y Label", timeout=E2E_TIMEOUT)

    @pytest.mark.order(7)
    def test_07_clear_title(self, tier2_page: Page) -> None:
        """Clear the title, refresh, chart still renders without a title."""
        mp = ManagePlotsPage(tier2_page)
        mp.viz_title_input.fill("")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
        expect(mp.viz_title_input).to_have_value("", timeout=E2E_TIMEOUT)

    @pytest.mark.order(8)
    def test_08_engine_pills_visible(self, tier2_page: Page) -> None:
        """Engine selector pills are visible with plotly and matplotlib."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)
        plotly_pill = mp.viz_engine_pills.get_by_role("radio", name="plotly")
        expect(plotly_pill).to_be_visible(timeout=E2E_TIMEOUT)
        mpl_pill = mp.viz_engine_pills.get_by_role("radio", name="matplotlib")
        expect(mpl_pill).to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(9)
    def test_09_switch_to_matplotlib(self, tier2_page: Page) -> None:
        """Select matplotlib engine and verify matplotlib chart renders."""
        mp = ManagePlotsPage(tier2_page)
        mp.select_engine("matplotlib")
        mp.refresh_plot()
        mp.assert_matplotlib_chart_visible()

    @pytest.mark.order(10)
    def test_10_matplotlib_no_plotly_chart(self, tier2_page: Page) -> None:
        """While matplotlib is active, plotly chart iframe is not visible."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.plotly_chart.first).not_to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(11)
    def test_11_switch_back_to_plotly(self, tier2_page: Page) -> None:
        """Switch back to plotly engine and verify plotly chart renders."""
        mp = ManagePlotsPage(tier2_page)
        mp.select_engine("plotly")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    @pytest.mark.order(12)
    def test_12_plotly_no_matplotlib_chart(self, tier2_page: Page) -> None:
        """While plotly is active, matplotlib image is not visible."""
        mp = ManagePlotsPage(tier2_page)
        expect(mp.matplotlib_chart.first).not_to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(13)
    def test_13_toggle_advanced_off(self, tier2_page: Page) -> None:
        """Toggle advanced settings off; the advanced-section pills disappear.

        The basic Layout/Typography/Legends pills remain visible (they are not
        gated by the toggle), so we assert the advanced-only 'Colors' pill is
        gone rather than the whole pills group.
        """
        mp = ManagePlotsPage(tier2_page)
        mp.toggle_advanced_settings()
        expect(mp.viz_advanced_section_pill).not_to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(14)
    def test_14_chart_visible_without_advanced(self, tier2_page: Page) -> None:
        """Chart remains visible after disabling advanced settings."""
        mp = ManagePlotsPage(tier2_page)
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    @pytest.mark.order(15)
    def test_15_toggle_advanced_back_on(self, tier2_page: Page) -> None:
        """Re-enable advanced settings; the advanced-section pills reappear."""
        mp = ManagePlotsPage(tier2_page)
        mp.toggle_advanced_settings()
        expect(mp.viz_advanced_section_pill).to_be_visible(timeout=E2E_TIMEOUT)


@pytest.mark.xdist_group("e2e_accessible_theme")
class TestAccessibleTheme:
    """Human-facing accessible-theme workflow."""

    def test_enable_theme_selects_safe_palette_and_passes_visible_audit(
        self,
        tier2_page: Page,
    ) -> None:
        # [test->req~ring5.figure.accessible-themes~1]
        mp = ManagePlotsPage(tier2_page)
        mp.toggle_advanced_settings()
        mp.viz_advanced_section_pill.click()
        mp.wait_for_streamlit()

        expect(mp.accessible_theme_checkbox).to_be_visible(timeout=E2E_TIMEOUT)
        mp.accessible_theme_control.locator("label").click()
        mp.wait_for_streamlit(timeout=E2E_TIMEOUT, expect_rerun=True)

        expect(mp.accessible_theme_checkbox).to_be_checked(timeout=E2E_TIMEOUT)
        expect(mp.color_palette_selectbox.get_by_role("combobox")).to_have_value(
            "✓ Ring5 Accessible",
            timeout=E2E_TIMEOUT,
        )
        expect(mp.accessibility_check_success).to_be_visible(timeout=E2E_TIMEOUT)
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)


@pytest.mark.xdist_group("e2e_figure_theme")
class TestFigureThemePreset:
    """Human-facing built-in theme and exchange controls."""

    def test_apply_dark_theme_keeps_plot_and_exposes_import_export(
        self,
        tier2_page: Page,
    ) -> None:
        # [test->req~ring5.figure.theme-presets~1]
        mp = ManagePlotsPage(tier2_page)
        expect(mp.viz_theme_section_pill).to_be_visible(timeout=E2E_TIMEOUT)
        mp.viz_theme_section_pill.click()
        mp.wait_for_streamlit()

        mp.select_figure_theme("Dark background")
        mp.apply_figure_theme_button.click()
        mp.wait_for_streamlit(timeout=E2E_TIMEOUT, expect_rerun=True)

        expect(mp.figure_theme_selectbox.get_by_role("combobox")).to_have_value(
            "Dark background",
            timeout=E2E_TIMEOUT,
        )
        expect(mp.figure_theme_applied_success).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.import_figure_theme_uploader).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.export_figure_theme_button).to_be_visible(timeout=E2E_TIMEOUT)
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
