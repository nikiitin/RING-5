"""E2E tests for the download expander and format options.

Tier 2 -- Export / Download:
    - Download expander presence and labelling
    - Opening the expander reveals format pills
    - PDF, SVG, PNG format pills activate the download button
    - Matplotlib-specific PGF format availability

Data precondition:
    Uses ``tier2_page`` which provides a fully rendered bar plot
    ("E2E Bar") with Plotly engine active by default.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT, EXPORT_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


# ---------------------------------------------------------------------------
# Export / download tests
# ---------------------------------------------------------------------------


@pytest.mark.xdist_group("e2e_export")
class TestExportDownload:
    """Tier 2: Download expander and format options (ordered).

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

    @staticmethod
    def _open_download_expander(mp: ManagePlotsPage) -> None:
        """Click the download expander to reveal its contents.

        Streamlit renders the expander as ``<details><summary>…`` — the
        ``summary`` element is the clickable header (there is no
        ``stExpanderToggleDetails`` testid). Clicking it opens the body so the
        format pills and download button become visible. Opening a ``<details>``
        is a client-side toggle (no Streamlit rerun), so we verify-then-act by
        waiting for the format pills to become visible.
        """
        if not mp.download_format_pills.is_visible():
            mp.download_expander.locator("summary").first.click()
            expect(mp.download_format_pills).to_be_visible(timeout=E2E_TIMEOUT)

    @staticmethod
    def _select_format_pill(mp: ManagePlotsPage, format_name: str) -> None:
        """Click a format pill inside the download expander by name.

        Selecting a format reruns the script (to rebuild the download for that
        format), so we wait for the rerun to actually start before its end.
        """
        pill = mp.download_format_pills.get_by_role("button", name=format_name)
        pill.click()
        # The rerun runs the (eager) Kaleido export for raster formats, which can
        # be slow under -n 3 — allow extra time for the rerun to finish.
        mp.wait_for_streamlit(timeout=EXPORT_TIMEOUT, expect_rerun=True)

    # -- tests -------------------------------------------------------------

    def test_01_download_expander_exists(self, tier2_page: Page) -> None:
        """The download expander is present and shows "Download" text.

        The expander widget should exist in the DOM with the expected
        label, even when collapsed.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        expect(mp.download_expander).to_be_visible(timeout=E2E_TIMEOUT)
        expect(mp.download_expander).to_contain_text("Download")

    def test_02_open_download_expander(self, tier2_page: Page) -> None:
        """Opening the download expander reveals the format pills.

        After clicking the expander header, a button group with format
        options (PDF, SVG, PNG, etc.) should become visible.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        self._open_download_expander(mp)
        expect(mp.download_format_pills).to_be_visible(timeout=E2E_TIMEOUT)

    def test_03_pdf_format_available(self, tier2_page: Page) -> None:
        """Selecting the PDF format pill makes the download button appear.

        PDF export is available for both Plotly and Matplotlib engines.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        self._open_download_expander(mp)

        # Select PDF format
        pdf_pill = mp.download_format_pills.get_by_role("button", name="pdf")
        expect(pdf_pill).to_be_visible(timeout=E2E_TIMEOUT)
        self._select_format_pill(mp, "pdf")

        # Download button should appear
        expect(mp.download_button).to_be_visible(timeout=EXPORT_TIMEOUT)

    def test_04_svg_format_available(self, tier2_page: Page) -> None:
        """Selecting the SVG format pill makes the download button appear.

        SVG export is available for both Plotly and Matplotlib engines.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        self._open_download_expander(mp)

        # Select SVG format
        svg_pill = mp.download_format_pills.get_by_role("button", name="svg")
        expect(svg_pill).to_be_visible(timeout=E2E_TIMEOUT)
        self._select_format_pill(mp, "svg")

        # Download button should appear
        expect(mp.download_button).to_be_visible(timeout=EXPORT_TIMEOUT)

    def test_05_png_format_available(self, tier2_page: Page) -> None:
        """Selecting the PNG format pill makes the download button appear.

        PNG is a raster format available for both engine types.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        self._open_download_expander(mp)

        # Select PNG format
        png_pill = mp.download_format_pills.get_by_role("button", name="png")
        expect(png_pill).to_be_visible(timeout=E2E_TIMEOUT)
        self._select_format_pill(mp, "png")

        # Download button should appear
        expect(mp.download_button).to_be_visible(timeout=EXPORT_TIMEOUT)

    def test_06_matplotlib_pgf_format(self, tier2_page: Page) -> None:
        """After switching to Matplotlib, the PGF format pill is available.

        PGF (LaTeX-native vector format) is only offered when the
        Matplotlib engine is active. This test switches engines, opens
        the download expander, and verifies the PGF option exists.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")

        # Switch to Matplotlib engine
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_engine("matplotlib")
        mp.assert_matplotlib_chart_visible()

        # Open download expander
        self._open_download_expander(mp)
        expect(mp.download_format_pills).to_be_visible(timeout=E2E_TIMEOUT)

        # PGF pill should be present under Matplotlib
        pgf_pill = mp.download_format_pills.get_by_role("button", name="pgf")
        expect(pgf_pill).to_be_visible(timeout=E2E_TIMEOUT)

    def test_07_download_button_label(self, tier2_page: Page) -> None:
        """The download button inside the expander has the correct role + is enabled.

        Uses the **html** format deliberately: it is plotly's native, kaleido-free
        export, so the download button renders immediately. The raster formats
        (png/svg/pdf) require a kaleido render whose data must be ready before
        ``st.download_button`` appears — under ``-n 3`` three concurrent kaleido
        exports starve and the button can lag past the timeout (raster coverage
        lives in test_03/04/05). This test only checks the button role/enabled,
        for which html is sufficient and deterministic.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        # The preceding test switches to Matplotlib; restore Plotly so the
        # plotly-chart precondition below holds (select_engine is idempotent).
        mp.select_engine("plotly")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        self._open_download_expander(mp)

        # Select a kaleido-free format so the button appears deterministically.
        self._select_format_pill(mp, "html")

        # Verify the button has the expected accessible name + is enabled.
        expect(mp.download_button).to_be_visible(timeout=EXPORT_TIMEOUT)
        expect(mp.download_button).to_be_enabled(timeout=EXPORT_TIMEOUT)
