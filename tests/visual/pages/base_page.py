"""Base Page Object for all Playwright page models.

Provides common operations:
- Sidebar navigation between app pages
- Waiting for Streamlit to finish rendering
- Screenshot helpers
- Common locators (header, sidebar)
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from playwright.sync_api import Locator, Page, expect


class BasePage:
    """Common functionality shared by all page objects."""

    # Default timeout for Streamlit rendering (ms)
    RENDER_TIMEOUT: int = 15_000

    def __init__(self, page: Page) -> None:
        self.page = page

    # ------------------------------------------------------------------
    # Common locators
    # ------------------------------------------------------------------

    @property
    def sidebar(self) -> Locator:
        """The Streamlit sidebar container."""
        return self.page.locator("[data-testid='stSidebar']")

    @property
    def main_header(self) -> Locator:
        """The main ``RING-5 Interactive Analyzer`` title."""
        return self.page.locator("h1.main-header")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate_to(self, page_name: str) -> None:
        """Click a sidebar navigation button to switch pages.

        Args:
            page_name: Exact label of the sidebar nav button
                (e.g. "Data Source", "Data Managers").
        """
        btn = self.sidebar.get_by_role("button", name=page_name)
        btn.click()
        self.wait_for_streamlit()

    def reset_all(self) -> None:
        """Click the sidebar 'Reset All' button to clear all app state.

        Drives ``api.reset_session()`` (clears plots + data + config). Used to
        give each browser-test class a clean slate, since ``ApplicationAPI`` is
        a process-wide ``@st.cache_resource`` singleton whose ``PlotRepository``
        keeps plots in plain instance attributes (not ``st.session_state``), so
        state otherwise persists across browser sessions on the same server.
        """
        self.sidebar.get_by_role("button", name="Reset All").click()
        self.wait_for_streamlit()

    # ------------------------------------------------------------------
    # Streamlit sync helpers
    # ------------------------------------------------------------------

    def wait_for_streamlit(self, *, timeout: int | None = None, expect_rerun: bool = False) -> None:
        """Wait until Streamlit finishes its current script run.

        Strategy:
        1. (optional) When ``expect_rerun`` is set, first wait for the
           "Running..." status indicator to APPEAR. A rerun starts a beat
           after the triggering click (client→server round-trip), so without
           this we can observe the *pre-rerun* idle state and return too early
           — letting a follow-up action abort the rerun before it commits its
           state (e.g. a rename/delete silently lost). Only pass this for
           actions that are GUARANTEED to trigger a rerun.
        2. Try ``networkidle`` with a short timeout (pages with custom
           component iframes may never reach true *networkidle*).
        3. Ensure the "Running..." status indicator is gone — this is
           the authoritative signal that the Streamlit script has finished.
        """
        effective_timeout = timeout or self.RENDER_TIMEOUT
        running = self.page.locator("[data-testid='stStatusWidget']")
        if expect_rerun:
            try:
                # Bounded so a very fast rerun (already finished) doesn't stall.
                running.wait_for(state="visible", timeout=3_000)
            except Exception:
                pass
        try:
            self.page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception:
            # Custom components (iframes) or WebSocket heartbeats may
            # keep activity going indefinitely — fall through to the
            # status-widget check which is the reliable indicator.
            pass
        # Streamlit shows a status element while re-running
        running.wait_for(state="hidden", timeout=effective_timeout)

    def goto_and_wait(self, url: str) -> None:
        """Navigate to *url* and wait for Streamlit to render."""
        self.page.goto(url, wait_until="networkidle")
        self.wait_for_streamlit()

    # ------------------------------------------------------------------
    # Screenshot helpers
    # ------------------------------------------------------------------

    def screenshot(
        self,
        path: str | Path,
        *,
        full_page: bool = True,
    ) -> None:
        """Capture a screenshot of the current viewport.

        Args:
            path: Destination file path (PNG).
            full_page: If True, capture the entire scrollable area.
        """
        self.page.screenshot(path=str(path), full_page=full_page)

    def screenshot_element(
        self,
        locator: Locator,
        path: str | Path,
    ) -> None:
        """Screenshot a single element.

        Args:
            locator: Playwright locator for the target element.
            path: Destination file path (PNG).
        """
        locator.screenshot(path=str(path))

    # ------------------------------------------------------------------
    # GIF generation
    # ------------------------------------------------------------------

    @staticmethod
    def create_gif(
        frames: Sequence[str | Path],
        output: str | Path,
        *,
        duration_ms: int = 1500,
    ) -> None:
        """Combine PNG frames into an animated GIF.

        Args:
            frames: Ordered list of PNG file paths.
            output: Destination GIF path.
            duration_ms: Per-frame display duration in milliseconds.
        """
        import imageio.v3 as iio

        images = [iio.imread(str(f)) for f in frames]
        iio.imwrite(
            str(output),
            images,
            duration=duration_ms,
            loop=0,
        )

    # ------------------------------------------------------------------
    # Assertion helpers
    # ------------------------------------------------------------------

    def assert_page_loaded(self) -> None:
        """Assert the main app header is visible (basic health check)."""
        expect(self.main_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_on_page(self, page_name: str) -> None:
        """Assert that a specific sidebar nav button is active (primary type).

        Streamlit renders the active nav button with ``type="primary"``,
        which maps to ``data-testid="stBaseButton-primary"`` or the primary
        CSS class.
        """
        btn = self.sidebar.get_by_role("button", name=page_name)
        expect(btn).to_be_visible()
