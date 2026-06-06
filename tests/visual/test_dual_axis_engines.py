"""Visual test: the dual-axis bar+dot plot rendered in both engines.

Loads the shared 18-row fixture CSV, builds a finalized ``dual_axis_bar_dot``
plot, and captures a screenshot of the chart in **both** the Plotly and the
matplotlib engine. This is the visual companion to ``tests/e2e/test_dual_axis``:
the e2e suite asserts the chart *renders*; this one captures the pixels so
dual-engine parity of the decomposed trace builders (Theme-B B6) can be eyeballed
and used as a manual visual-regression reference.

Screenshots land in ``tests/visual/screenshots/<ClassName>/`` (gitignored).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser

# The same 18×8 fixture the e2e suite uses (has system.cpu.ipc + numCycles).
_E2E_CSV: Path = Path(__file__).parents[1] / "e2e" / "fixtures" / "sample_data.csv"
_CHART_TIMEOUT: int = 30_000
_E2E_TIMEOUT: int = 60_000


@pytest.mark.requires_browser
class TestDualAxisEngines:
    """Render the dual-axis bar+dot plot and screenshot each engine (ordered)."""

    @pytest.fixture(scope="class", autouse=True)
    def _setup_dual_axis_plot(self, shared_page: Page, live_server_url: str) -> None:
        """Load CSV → create + finalize a dual_axis_bar_dot plot once per class."""
        assert _E2E_CSV.exists(), f"Fixture CSV not found: {_E2E_CSV}"

        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.upload_csv(_E2E_CSV)
        ds.wait_for_streamlit()

        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.create_plot("Visual Dual", "dual_axis_bar_dot")
        mp.assert_plot_pill_visible("Visual Dual")
        mp.add_shaper("Sort")
        mp.finalize_pipeline()
        # Full rerun so the render fragment sees processed_data.
        mp.navigate_to("Data Source")
        mp.navigate()

    def test_01_plotly_screenshot(self, shared_page: Page, shared_screenshot_dir: Path) -> None:
        """Capture the dual-axis chart in the Plotly engine."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)
        shared_page.screenshot(
            path=str(shared_screenshot_dir / "dual_axis_plotly.png"),
            full_page=True,
        )

    def test_02_matplotlib_screenshot(self, shared_page: Page, shared_screenshot_dir: Path) -> None:
        """Switch to matplotlib (twinx) and capture the dual-axis chart."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        expect(mp.viz_engine_pills).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.select_engine("matplotlib")
        mp.assert_matplotlib_chart_visible()
        shared_page.screenshot(
            path=str(shared_screenshot_dir / "dual_axis_matplotlib.png"),
            full_page=True,
        )
