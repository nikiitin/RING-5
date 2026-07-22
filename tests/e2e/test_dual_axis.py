"""E2E tests for the dual-axis bar+dot plot across both rendering engines.

``test_engine_comparison`` covers a bar plot; this suite covers the dual-axis
bar-and-dot path in both Plotly and Matplotlib.

Data precondition: ``tier1_page`` (18-row CSV). ``y_bar`` / ``y_dot`` auto-
default to the first two numeric columns (``system.cpu.ipc`` /
``system.cpu.numCycles``); ``test_02`` also sets them explicitly via the POM.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


@pytest.fixture(scope="class")
def dual_axis_page(tier1_page: Page) -> Page:
    """Tier 1 (CSV loaded) + a finalized ``dual_axis_bar_dot`` plot.

    Mirrors the ``_create_and_finalize_bar`` pattern: create the plot, add a
    Sort shaper (keeps every column so both numeric Y candidates survive),
    finalize, then navigate away and back to force a full rerun so the render
    fragment sees ``processed_data``. The freshly created plot stays selected
    in session state, so tests must NOT re-click its pill (that would deselect).
    """
    mp = ManagePlotsPage(tier1_page)
    mp.navigate()
    mp.create_plot("E2E Dual", "dual_axis_bar_dot")
    mp.assert_plot_pill_visible("E2E Dual")

    mp.add_shaper("Sort")
    mp.finalize_pipeline()

    mp.navigate_to("Data Source")
    mp.navigate()
    return tier1_page


@pytest.mark.xdist_group("e2e_dual_axis")
class TestDualAxisRendering:
    """Tier 2: render the dual-axis bar+dot plot in both engines (ordered).

    Shares ``dual_axis_page`` (class-scoped). "E2E Dual" is the most recently
    created plot, so it is auto-selected; tests rely on that and only switch
    the engine — never re-selecting the pill.
    """

    # [test->req~ring5.figure.dual-axis-controls~1]
    # [test->req~ring5.figure.dual-axis-dot-layout~1]

    @pytest.mark.order(1)
    def test_01_plotly_renders_with_auto_axes(self, dual_axis_page: Page) -> None:
        """Default (Plotly) engine renders the dual-axis chart from auto-picked axes."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
        # Title auto-populates as "<y_bar> vs <y_dot>" once both Y columns resolve,
        # proving the dual-axis config picked a bar column and a dot column.
        expect(mp.viz_title_input).to_have_value(re.compile(r"\bvs\b"))

    @pytest.mark.order(2)
    def test_02_explicit_axis_config_renders(self, dual_axis_page: Page) -> None:
        """Explicitly mapping bars→ipc and dots→numCycles still renders (Plotly)."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        expect(mp.viz_y_bar_selectbox).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_y_bar("system.cpu.ipc")
        mp.select_y_dot("system.cpu.numCycles")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
        expect(mp.viz_title_input).to_have_value("system.cpu.ipc vs system.cpu.numCycles")
        expect(mp.viz_y_label_input).to_have_value("system.cpu.ipc")
        expect(dual_axis_page.get_by_role("textbox", name="Right Y-axis Label")).to_have_value(
            "system.cpu.numCycles"
        )

    @pytest.mark.order(3)
    def test_03_matplotlib_renders(self, dual_axis_page: Page) -> None:
        """Switching to matplotlib renders the dual-axis chart via twinx (st.pyplot)."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_engine("matplotlib")
        mp.assert_matplotlib_chart_visible()

    @pytest.mark.order(4)
    def test_04_bar_aligned_within_group_mode_renders(self, dual_axis_page: Page) -> None:
        """Human-facing alignment and within-group controls render in Matplotlib."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        mp.select_color_by("config_description")
        mp.select_dual_dot_placement("Aligned with each bar")
        mp.select_dual_line_scope("Only within each benchmark group")
        mp.refresh_plot()
        mp.assert_matplotlib_chart_visible()

    @pytest.mark.order(5)
    def test_05_switch_back_to_plotly(self, dual_axis_page: Page) -> None:
        """Switching back to Plotly re-renders the interactive dual-axis chart."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_engine("plotly")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
