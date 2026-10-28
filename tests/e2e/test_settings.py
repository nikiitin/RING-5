"""E2E tests for settings pills, config inputs, and engine switching.

Uses ``tier2_page`` which provides: CSV loaded + bar plot "E2E Bar" created
with Sort pipeline finalized, axes configured, and Plotly chart visible.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.helpers.browser_plot_data import read_native_plotly
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.plot_interactions_page import PlotInteractionsPage

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
    """Apply, exchange and reject themes while retaining the underlying observations."""

    def test_theme_json_round_trip_changes_appearance_and_rejects_data_bindings(
        self,
        tier2_page: Page,
    ) -> None:
        # [test->req~ring5.figure.theme-presets~1]
        mp = ManagePlotsPage(tier2_page)
        interactions = PlotInteractionsPage(tier2_page)
        source_rows = interactions.download_workspace_rows()
        mp.navigate()
        title = mp.viz_title_input.input_value()
        original = read_native_plotly(tier2_page, title, expected_trace_count=1)
        observations = [(trace["x"], trace["y"]) for trace in original["traces"]]

        def assert_appearance(paper: str, plot: str) -> None:
            rendered = read_native_plotly(
                tier2_page,
                title,
                expected_trace_count=1,
                expected_layout={"paper_bgcolor": paper, "plot_bgcolor": plot},
            )
            assert rendered["layout"]["paper_bgcolor"] == paper
            assert rendered["layout"]["plot_bgcolor"] == plot
            assert [(trace["x"], trace["y"]) for trace in rendered["traces"]] == observations
            expect(mp.viz_x_axis_selectbox.get_by_role("combobox")).to_have_value("benchmark_name")
            expect(mp.viz_y_axis_selectbox.get_by_role("combobox")).to_have_value("system.cpu.ipc")

        def download_theme() -> dict[str, Any]:
            with tier2_page.expect_download(timeout=E2E_TIMEOUT) as pending:
                mp.export_figure_theme_button.click()
            return json.loads(pending.value.path().read_bytes())

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
        assert_appearance("#161a24", "#202633")
        name = tier2_page.get_by_role("textbox", name="Theme name", exact=True)
        name.fill("Browser round-trip theme")
        name.press("Enter")
        mp.wait_for_streamlit(expect_rerun=True)
        exported = download_theme()
        assert set(exported) == {
            "identifier",
            "name",
            "context",
            "description",
            "config",
            "schema_version",
        }
        assert exported["schema_version"] == 1
        assert exported["name"] == "Browser round-trip theme"
        assert exported["context"] == "dark"
        assert exported["config"]["paper_bgcolor"] == "#161a24"
        assert exported["config"]["plot_bgcolor"] == "#202633"
        assert exported["config"]["color_palette"] == "ring5_accessible_dark"
        assert not {"x", "y", "data", "filter", "color"}.intersection(exported["config"])

        mp.select_figure_theme("Publication paper")
        mp.apply_figure_theme_button.click()
        mp.wait_for_streamlit(expect_rerun=True)
        assert_appearance("#ffffff", "#ffffff")
        uploader = mp.import_figure_theme_uploader.locator('input[type="file"]')
        uploader.set_input_files(
            {
                "name": "browser-round-trip.ring5-theme.json",
                "mimeType": "application/json",
                "buffer": json.dumps(exported).encode(),
            }
        )
        expect(
            tier2_page.get_by_test_id("stAlertContentSuccess").filter(
                has_text="Imported Browser round-trip theme. Review it before applying."
            )
        ).to_be_visible(timeout=E2E_TIMEOUT)
        assert_appearance("#ffffff", "#ffffff")
        tier2_page.get_by_role("button", name="Apply imported theme", exact=True).click()
        mp.wait_for_streamlit(expect_rerun=True)
        assert_appearance("#161a24", "#202633")
        assert download_theme()["config"] == exported["config"]

        invalid = {**exported, "config": {**exported["config"], "x": "simTicks"}}
        uploader.set_input_files(
            {
                "name": "invalid-data-binding.ring5-theme.json",
                "mimeType": "application/json",
                "buffer": json.dumps(invalid).encode(),
            }
        )
        expect(tier2_page.get_by_test_id("stAlertContentError")).to_contain_text(
            "Figure themes cannot contain data or unsupported keys: x", timeout=E2E_TIMEOUT
        )
        expect(
            tier2_page.get_by_role("button", name="Apply imported theme", exact=True)
        ).to_have_count(0)
        assert_appearance("#161a24", "#202633")
        assert download_theme()["config"] == exported["config"]
        assert interactions.download_workspace_rows() == source_rows
