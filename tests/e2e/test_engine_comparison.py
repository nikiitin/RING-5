"""E2E tests for engine switching between Plotly and Matplotlib.

Tier 2 -- Engine Comparison:
    - Default engine is Plotly (chart renders via custom component iframe)
    - Switch to Matplotlib (chart renders via st.pyplot / stImage)
    - Switch back to Plotly
    - Verify Matplotlib image element presence
    - Verify engine selector pills widget

Data precondition:
    Uses ``tier2_page`` which provides a fully rendered bar plot
    ("E2E Bar") with Plotly engine active by default.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


# Engine switching tests


@pytest.mark.xdist_group("e2e_engine")
class TestEngineSwitching:
    """Tier 2: Switch between Plotly and Matplotlib engines (ordered).

    All tests share the same ``tier2_page`` (class-scoped) which already
    has:
    - CSV data loaded (18 rows)
    - Bar plot "E2E Bar" created with Sort pipeline finalized
    - Axes configured (x=benchmark_name, y=system.cpu.ipc)
    - Plotly chart rendered and visible

    Tests are numbered to enforce execution order within the class.
    """

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _ensure_on_manage_plots(page: Page) -> ManagePlotsPage:
        """Return a ManagePlotsPage POM, navigating if needed."""
        mp = ManagePlotsPage(page)
        mp.navigate()
        mp.assert_page_header_visible()
        return mp

    # -- tests -------------------------------------------------------------

    @pytest.mark.order(1)
    def test_01_default_engine_is_plotly(self, tier2_page: Page) -> None:
        """The default engine is Plotly; chart iframe should be visible.

        tier2_page already rendered a Plotly chart during fixture setup.
        We verify the custom component (iframe) is present and has a
        non-zero height, confirming the Plotly chart loaded successfully.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_switch_to_matplotlib(self, tier2_page: Page) -> None:
        """Switch from Plotly to Matplotlib and verify the chart renders.

        After clicking the "matplotlib" engine pill, the chart output
        should change from a custom component iframe to an stImage
        element rendered by st.pyplot.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")

        # Wait for visualization section to be ready
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)

        # Switch engine
        mp.select_engine("matplotlib")
        mp.assert_matplotlib_chart_visible()

    @pytest.mark.order(3)
    def test_03_switch_back_to_plotly(self, tier2_page: Page) -> None:
        """Switch back from Matplotlib to Plotly and verify the chart.

        After selecting "plotly" in the engine pills, the Plotly custom
        component iframe should reappear with non-zero height.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")

        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)

        # Switch to plotly (may already be plotly from previous test
        # state reset; the action is idempotent)
        mp.select_engine("plotly")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    @pytest.mark.order(4)
    def test_04_matplotlib_chart_renders(self, tier2_page: Page) -> None:
        """Switch to Matplotlib and verify the stImage DOM element.

        This test directly checks for the ``[data-testid='stImage']``
        locator that Streamlit emits for ``st.pyplot`` output, providing
        a lower-level assertion than ``assert_matplotlib_chart_visible``.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")

        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)

        mp.select_engine("matplotlib")

        # Verify the stImage element directly
        st_image = tier2_page.locator("[data-testid='stImage']").first
        expect(st_image).to_be_visible(timeout=CHART_TIMEOUT)

        # The image should contain an <img> tag with actual content
        img_tag = st_image.locator("img").first
        expect(img_tag).to_be_attached(timeout=CHART_TIMEOUT)

    @pytest.mark.order(5)
    def test_05_engine_pills_visible(self, tier2_page: Page) -> None:
        """The engine selector pills widget is visible with expected options.

        The pills widget should display at least the "plotly" label,
        confirming that the engine selector is rendered in the
        visualization section.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")

        # Engine pills should be visible
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)

        # Verify "plotly" option exists within the pills
        plotly_button = mp.viz_engine_pills.get_by_role("radio", name="plotly")
        expect(plotly_button).to_be_visible(timeout=E2E_TIMEOUT)

        # Verify "matplotlib" option exists within the pills
        matplotlib_button = mp.viz_engine_pills.get_by_role("radio", name="matplotlib")
        expect(matplotlib_button).to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(6)
    def test_06_plotly_iframe_has_nonzero_height(self, tier2_page: Page) -> None:
        """After switching to Plotly, the iframe height attribute is > 0.

        This validates that the custom Plotly component fully initialised
        its internal JS and resized the iframe beyond the default 0px.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")

        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_engine("plotly")

        # assert_chart_visible already checks non-zero height internally
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        # Double-check via a direct attribute read
        chart = mp.plotly_chart.first
        height = chart.get_attribute("height")
        assert height is not None
        assert int(height) > 0, f"Expected iframe height > 0, got {height}"
