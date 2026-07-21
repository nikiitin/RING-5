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

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT, EXPORT_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


# Export / download tests


@pytest.mark.serial
@pytest.mark.xdist_group("e2e_export")
class TestExportDownload:
    """Tier 2: Download expander and format options (ordered).

    Marked ``serial`` because the ordered checks intentionally share one
    ``tier2_page`` while changing its format and rendering-engine state. The
    byte-producing exporters are covered separately; these checks only verify
    that each browser control is available and responsive.

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

        Selecting a format reruns the script to register a deferred download
        for that format. The rerun can also re-collapse the ``<details>``
        expander, which would hide the download button, so this helper reopens
        it when needed.
        """
        pill = mp.download_format_pills.get_by_role("radio", name=format_name)
        pill.click()
        mp.wait_for_streamlit(timeout=EXPORT_TIMEOUT, expect_rerun=True)
        # Re-open the expander if the rerun collapsed it, so the download button
        # (rendered inside it) is reachable.
        if not mp.download_format_pills.is_visible():
            mp.download_expander.locator("summary").first.click()
            expect(mp.download_format_pills).to_be_visible(timeout=E2E_TIMEOUT)

    # -- tests -------------------------------------------------------------

    @pytest.mark.order(1)
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

    @pytest.mark.order(2)
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

    @pytest.mark.order(3)
    def test_03_pdf_format_available(self, tier2_page: Page) -> None:
        """Selecting the PDF format pill makes the download button appear.

        PDF export is available for both Plotly and Matplotlib engines.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        self._open_download_expander(mp)

        # Select PDF format
        pdf_pill = mp.download_format_pills.get_by_role("radio", name="pdf")
        expect(pdf_pill).to_be_visible(timeout=E2E_TIMEOUT)
        self._select_format_pill(mp, "pdf")

        # Download button should appear
        expect(mp.download_button).to_be_visible(timeout=EXPORT_TIMEOUT)

    @pytest.mark.order(4)
    def test_04_svg_format_available(self, tier2_page: Page) -> None:
        """Selecting the SVG format pill makes the download button appear.

        SVG export is available for both Plotly and Matplotlib engines.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        self._open_download_expander(mp)

        # Select SVG format
        svg_pill = mp.download_format_pills.get_by_role("radio", name="svg")
        expect(svg_pill).to_be_visible(timeout=E2E_TIMEOUT)
        self._select_format_pill(mp, "svg")

        # Download button should appear
        expect(mp.download_button).to_be_visible(timeout=EXPORT_TIMEOUT)

    @pytest.mark.order(5)
    def test_05_png_format_available(self, tier2_page: Page) -> None:
        """Selecting the PNG format pill makes the download button appear.

        PNG is a raster format available for both engine types.
        """
        mp = self._ensure_on_manage_plots(tier2_page)
        mp.select_plot("E2E Bar")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)

        self._open_download_expander(mp)

        # Select PNG format
        png_pill = mp.download_format_pills.get_by_role("radio", name="png")
        expect(png_pill).to_be_visible(timeout=E2E_TIMEOUT)
        self._select_format_pill(mp, "png")

        # Download button should appear
        expect(mp.download_button).to_be_visible(timeout=EXPORT_TIMEOUT)

    @pytest.mark.order(6)
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
        pgf_pill = mp.download_format_pills.get_by_role("radio", name="pgf")
        expect(pgf_pill).to_be_visible(timeout=E2E_TIMEOUT)

    @pytest.mark.order(7)
    def test_07_html_download_completes(self, tier2_page: Page, tmp_path: Path) -> None:
        """The HTML download completes and yields a self-contained document.

        HTML keeps this assertion independent of the optional Chrome-backed
        exporters; PDF, SVG, and PNG controls are covered above, and their byte
        output is verified by the dedicated export tests.
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
        with tier2_page.expect_download(timeout=E2E_TIMEOUT) as download_info:
            mp.download_button.click()
        download = download_info.value
        assert download.failure() is None
        output = tmp_path / download.suggested_filename
        download.save_as(str(output))
        assert output.read_bytes().lower().startswith(b"<html")
