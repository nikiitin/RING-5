"""Browser checks for simulator selection and rendered figure settings.

Verify axes, typography, and legend controls through the current UI. These
checks inspect widget state; screenshot review covers rendering appearance.
The tracked 18-row E2E CSV supplies the finalized settings plots.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser

# Paths & constants

_REPO_ROOT: Path = Path(__file__).parents[2]
_E2E_CSV = _REPO_ROOT / "tests" / "e2e" / "fixtures" / "sample_data.csv"

_E2E_TIMEOUT: int = 60_000
_CHART_TIMEOUT: int = 30_000


def _prepare_settings_plot(page: Page, url: str, name: str) -> None:
    """Upload the real fixture and finalize a bar plot before inspecting its settings."""
    assert _E2E_CSV.is_file(), f"Fixture CSV not found: {_E2E_CSV}"
    source = DataSourcePage(page)
    source.goto_and_wait(url)
    source.upload_csv(_E2E_CSV)
    plot = ManagePlotsPage(page)
    plot.navigate()
    plot.create_plot(name, "bar")
    plot.add_shaper("Sort")
    plot.finalize_pipeline()
    plot.navigate_to("Data Source")
    plot.navigate()
    expect(plot.viz_x_axis_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
    plot.select_x_axis("benchmark_name")
    plot.select_y_axis("system.cpu.ipc")
    plot.refresh_plot()
    plot.assert_chart_visible(timeout=_CHART_TIMEOUT)


# Group 1: Simulator selection


class TestSimulatorPillSelector:
    """Simulator selection is available in the parser interface."""

    def test_simulator_pills_visible(self, shared_page: Page, live_server_url: str) -> None:
        """Simulator pills should be visible on the Data Source page."""
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.navigate()
        shared_page.wait_for_timeout(1_000)

        # Ensure parse mode is active
        ds.ensure_parse_mode()
        ds.wait_for_streamlit()

        # Simulator pills should be visible
        expect(ds.simulator_pills).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_gem5_pill_visible(self, shared_page: Page, live_server_url: str) -> None:
        """gem5 pill should be visible and selected by default."""
        ds = DataSourcePage(shared_page)
        ds.navigate()
        shared_page.wait_for_timeout(1_000)

        ds.ensure_parse_mode()
        ds.wait_for_streamlit()

        expect(ds.gem5_pill).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_simulator_pills_use_material_icon(
        self, shared_page: Page, live_server_url: str
    ) -> None:
        """Simulator pills should have material icon styling."""
        ds = DataSourcePage(shared_page)
        ds.navigate()
        shared_page.wait_for_timeout(1_000)

        ds.ensure_parse_mode()
        ds.wait_for_streamlit()

        # The pill text should contain "gem5" (icon is rendered by Streamlit)
        pill_text = ds.gem5_pill.text_content()
        assert pill_text is not None
        assert "gem5" in pill_text


# Group 2: Axes and typography settings


class TestSettingsReorganization:
    """Tick marks and title position belong to Axes; font controls use Typography."""

    @pytest.fixture(autouse=True, scope="class")
    @classmethod
    def _setup_plot(
        cls,
        shared_page: Page,
        live_server_url: str,
        _reset_app_state: None,
    ) -> None:
        """Prepare a rendered plot for this class's independent settings checks."""
        _prepare_settings_plot(shared_page, live_server_url, "Settings Test Bar")

    def test_tick_marks_in_axes_pill(self, shared_page: Page) -> None:
        """Tick controls are visible in the X-axis section."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Settings Test Bar")
        mp.set_advanced_settings(True)
        mp.select_settings_section("Axes")
        mp.select_axis("X-Axis")
        tick_text = shared_page.get_by_text("Tick Marks & Grid", exact=True)
        expect(tick_text).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_tick_pad_in_axes_pill(self, shared_page: Page) -> None:
        """X-axis tick label distance is editable under Axes."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Settings Test Bar")
        mp.set_advanced_settings(True)
        mp.select_settings_section("Axes")
        mp.select_axis("X-Axis")
        expect(
            shared_page.get_by_label("X-Axis Tick Label Distance (px)", exact=True)
        ).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_yaxis_standoff_in_axes_pill(self, shared_page: Page) -> None:
        """Y-axis title standoff is editable under Y-Left."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Settings Test Bar")
        mp.set_advanced_settings(True)
        mp.select_settings_section("Axes")
        mp.select_axis("Y-Left")
        expect(
            shared_page.get_by_label("Y-Axis Title Standoff (Spacing)", exact=True)
        ).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_typography_only_fonts_and_colors(self, shared_page: Page) -> None:
        """Typography exposes font controls while tick controls belong to Axes."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Settings Test Bar")
        mp.set_advanced_settings(True)
        mp.select_settings_section("Typography")
        expect(shared_page.get_by_label("Plot Title Font Size", exact=True)).to_be_visible(
            timeout=_E2E_TIMEOUT
        )
        expect(shared_page.get_by_text("Tick Marks & Grid", exact=True)).not_to_be_visible(
            timeout=5_000
        )


# Group 3: Legend settings


class TestLegendSettings:
    """Legend settings expose current positioning and column-layout controls."""

    @pytest.fixture(autouse=True, scope="class")
    @classmethod
    def _setup_plot(
        cls,
        shared_page: Page,
        live_server_url: str,
        _reset_app_state: None,
    ) -> None:
        """Prepare a rendered plot for this class's independent settings checks."""
        _prepare_settings_plot(shared_page, live_server_url, "Legend Test Bar")

    def test_primary_legend_accessible(self, shared_page: Page) -> None:
        """The primary legend settings are available for the rendered bar plot."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Legend Test Bar")
        mp.select_settings_section("Legends")
        primary = shared_page.get_by_role("radiogroup", name="Legend", exact=True).get_by_role(
            "radio", name="Primary"
        )
        expect(primary).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_vertical_position_and_orientation_in_legend(self, shared_page: Page) -> None:
        """Legend vertical position and orientation controls are available."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Legend Test Bar")
        mp.select_settings_section("Legends")
        expect(shared_page.get_by_label("Y Position", exact=True)).to_be_visible(
            timeout=_E2E_TIMEOUT
        )
        expect(shared_page.get_by_role("combobox", name="Orientation", exact=True)).to_be_visible(
            timeout=_E2E_TIMEOUT
        )

    def test_column_count_and_spacing_in_legend(self, shared_page: Page) -> None:
        """Legend column count and spacing controls are available."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_plot("Legend Test Bar")
        mp.select_settings_section("Legends")
        expect(shared_page.get_by_label("Columns", exact=True)).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(shared_page.get_by_label("Column Spacing", exact=True)).to_be_visible(
            timeout=_E2E_TIMEOUT
        )
