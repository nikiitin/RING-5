"""E2E tests for plot type creation, rendering, and management controls.

Covers:
- Tier 1 (TestPlotCreation): Create each supported plot type, finalize
  pipeline, configure axes, and assert the chart renders successfully.
- Tier 2 (TestPlotControls): Rename, duplicate, delete plots and verify
  the create-plot form is accessible.

Each test within a class is ordered; state accumulates across tests in the
same class via the shared class-scoped page fixture.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


# Helpers


def _create_and_finalize(mp: ManagePlotsPage, name: str, plot_type: str) -> None:
    """Create a plot, add a Sort shaper, and finalize the pipeline."""
    mp.navigate()
    mp.create_plot(name, plot_type)
    mp.assert_plot_pill_visible(name)
    mp.add_shaper("Sort")
    mp.finalize_pipeline()


def _trigger_render_fragment(mp: ManagePlotsPage) -> None:
    """Navigate away and back to force the visualization fragment to mount."""
    mp.navigate_to("Data Source")
    mp.navigate()


def _configure_and_assert_chart(
    mp: ManagePlotsPage,
    *,
    x: str = "benchmark_name",
    y: str = "system.cpu.ipc",
    group_by: str | None = None,
) -> None:
    """Wait for viz controls, set axes, refresh, and assert chart visible."""
    expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=E2E_TIMEOUT)
    mp.select_x_axis(x)
    mp.select_y_axis(y)
    if group_by is not None:
        mp.select_group_by(group_by)
    mp.refresh_plot()
    mp.assert_chart_visible(timeout=CHART_TIMEOUT)


# Tier 1 -- Plot creation & rendering


@pytest.mark.xdist_group("e2e_plot_types")
class TestPlotCreation:
    """Tier 1: Create each plot type and verify rendering (ordered).

    State accumulates -- every test adds a new plot to the session.
    """

    # -- Bar -----------------------------------------------------------------

    def test_01_create_bar_plot(self, tier1_page: Page) -> None:
        """Create a basic bar plot and verify chart renders."""
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Bar", "bar")
        _trigger_render_fragment(mp)
        _configure_and_assert_chart(mp, x="benchmark_name", y="system.cpu.ipc")

    # -- Grouped Bar ---------------------------------------------------------

    def test_02_create_grouped_bar(self, tier1_page: Page) -> None:
        """Create a grouped bar plot with a group_by dimension."""
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Grouped", "grouped_bar")
        _trigger_render_fragment(mp)
        _configure_and_assert_chart(
            mp,
            x="benchmark_name",
            y="system.cpu.ipc",
            group_by="config_description",
        )

    # -- Stacked Bar ---------------------------------------------------------

    def test_03_create_stacked_bar(self, tier1_page: Page) -> None:
        """Create a stacked bar plot and verify it renders.

        Unlike grouped bar, the app's stacked bar has no Y-axis or 'Stack by'
        selector — it stacks multiple numeric *statistics* chosen via a
        'Statistics to Stack' multiselect (which defaults to the first numeric
        columns). We set the X categories and rely on the default statistics.
        """
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Stacked", "stacked_bar")
        _trigger_render_fragment(mp)
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_x_axis("benchmark_name")
        # Statistics multiselect renders with sensible defaults (≥1 numeric col).
        expect(mp.stacked_statistics_multiselect).to_be_visible(timeout=E2E_TIMEOUT)
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    # -- Line ----------------------------------------------------------------

    def test_04_create_line_plot(self, tier1_page: Page) -> None:
        """Create a line plot with benchmark_name vs simTicks."""
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Line", "line")
        _trigger_render_fragment(mp)
        _configure_and_assert_chart(mp, x="benchmark_name", y="simTicks")

    # -- Scatter -------------------------------------------------------------

    def test_05_create_scatter_plot(self, tier1_page: Page) -> None:
        """Create a scatter plot with simTicks vs system.cpu.ipc."""
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Scatter", "scatter")
        _trigger_render_fragment(mp)
        _configure_and_assert_chart(mp, x="simTicks", y="system.cpu.ipc")

    # -- Histogram -----------------------------------------------------------

    def test_06_create_histogram(self, tier1_page: Page) -> None:
        """Create a histogram; with scalar data it shows the no-vars guidance.

        The histogram plot needs gem5 histogram-bucket columns (e.g.
        ``latency..0-10``, ``latency..10-20``). The e2e fixture has only scalar
        columns, so a chart cannot render — the app surfaces an informative
        warning instead of crashing, and that graceful behaviour is what we
        verify (the histogram plot type is exercised end-to-end, sans data).
        """
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Histogram", "histogram")
        _trigger_render_fragment(mp)
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=E2E_TIMEOUT)
        expect(tier1_page.get_by_text("No histogram variables detected").first).to_be_visible(
            timeout=E2E_TIMEOUT
        )

    # -- Box -----------------------------------------------------------------

    def test_07_create_box_plot(self, tier1_page: Page) -> None:
        # [test->req~ring5.plot.box~1]
        """Create a box plot and expose its human-readable distribution controls."""
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Box", "box")
        _trigger_render_fragment(mp)
        _configure_and_assert_chart(mp, x="benchmark_name", y="system.cpu.ipc")
        expect(tier1_page.get_by_text("Distribution summary", exact=True)).to_be_visible(
            timeout=E2E_TIMEOUT
        )

    # -- Violin --------------------------------------------------------------

    def test_08_create_violin_plot(self, tier1_page: Page) -> None:
        # [test->req~ring5.plot.violin~1]
        """Create a violin plot and expose its human-readable density controls."""
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Violin", "violin")
        _trigger_render_fragment(mp)
        _configure_and_assert_chart(mp, x="benchmark_name", y="system.cpu.ipc")
        expect(tier1_page.get_by_text("Density shape", exact=True)).to_be_visible(
            timeout=E2E_TIMEOUT
        )

    # -- ECDF ----------------------------------------------------------------

    def test_09_create_ecdf_plot(self, tier1_page: Page) -> None:
        # [test->req~ring5.plot.ecdf~1]
        """Create an ECDF and expose cumulative meaning controls."""
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E ECDF", "ecdf")
        _trigger_render_fragment(mp)
        expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_x_axis("system.cpu.ipc")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
        expect(tier1_page.get_by_text("Cumulative display", exact=True)).to_be_visible(
            timeout=E2E_TIMEOUT
        )

    # -- Area ----------------------------------------------------------------

    def test_10_create_area_plot(self, tier1_page: Page) -> None:
        # [test->req~ring5.plot.area~1]
        """Create an area chart and expose arrangement and interpolation controls."""
        mp = ManagePlotsPage(tier1_page)
        _create_and_finalize(mp, "E2E Area", "area")
        _trigger_render_fragment(mp)
        _configure_and_assert_chart(mp, x="benchmark_name", y="system.cpu.ipc")
        expect(tier1_page.get_by_text("Area display", exact=True)).to_be_visible(
            timeout=E2E_TIMEOUT
        )


# Tier 2 -- Plot management controls


@pytest.mark.xdist_group("e2e_plot_controls")
class TestPlotControls:
    """Tier 2: Plot management controls (rename, delete, duplicate).

    Starts with a pre-existing bar plot created by the ``tier2_page`` fixture.
    """

    @pytest.mark.order(1)
    def test_01_rename_plot(self, tier2_page: Page) -> None:
        """Rename 'E2E Bar' to 'Renamed Bar' and verify the selector updates."""
        mp = ManagePlotsPage(tier2_page)
        mp.navigate()
        mp.select_plot("E2E Bar")
        mp.rename_plot("Renamed Bar")
        mp.assert_plot_pill_visible("Renamed Bar")

    @pytest.mark.order(2)
    def test_02_duplicate_plot(self, tier2_page: Page) -> None:
        """Duplicate 'Renamed Bar' and verify a new pill appears."""
        mp = ManagePlotsPage(tier2_page)
        mp.navigate()
        mp.select_plot("Renamed Bar")
        mp.duplicate_plot()
        # Streamlit appends " (copy)" or similar; just check we have more pills
        expect(mp.plot_selector_pills.get_by_role("radio")).to_have_count(2, timeout=E2E_TIMEOUT)

    @pytest.mark.order(3)
    def test_03_delete_plot(self, tier2_page: Page) -> None:
        """Delete the duplicated plot and verify its pill disappears."""
        mp = ManagePlotsPage(tier2_page)
        mp.navigate()
        # Select the second pill (the duplicate) — index 1
        pills = mp.plot_selector_pills.get_by_role("radio")
        duplicate_name = pills.nth(1).inner_text()
        mp.select_plot(duplicate_name)
        mp.delete_plot()
        mp.assert_plot_pill_not_visible(duplicate_name)

    @pytest.mark.order(4)
    def test_04_create_form_visible(self, tier2_page: Page) -> None:
        """Assert the plot creation form is accessible."""
        mp = ManagePlotsPage(tier2_page)
        mp.navigate()
        mp.assert_create_form_visible()
