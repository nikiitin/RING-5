"""Base Page Object for all Playwright page models.

Provides common operations:
- Sidebar navigation between app pages
- Waiting for Streamlit to finish rendering
- Screenshot helpers
- Common locators (header, sidebar)
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
import re
import time

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect

_APP_IDLE = """() => {
    const app = document.querySelector('[data-testid="stApp"]');
    return app?.getAttribute('data-test-script-state') === 'notRunning' &&
        app.getAttribute('data-test-connection-state') === 'CONNECTED';
}"""


class BasePage:
    """Common functionality shared by all page objects."""

    # Default timeout for Streamlit rendering (ms)
    RENDER_TIMEOUT: int = 15_000

    def __init__(self, page: Page) -> None:
        self.page = page

    # Common locators

    @property
    def sidebar(self) -> Locator:
        """The Streamlit sidebar container."""
        return self.page.locator("[data-testid='stSidebar']")

    @property
    def main_header(self) -> Locator:
        """The main ``RING-5 Interactive Analyzer`` title."""
        return self.page.locator("h1.main-header")

    @property
    def background_jobs_expander(self) -> Locator:
        """The session-owned background-job center in the sidebar."""
        return self.sidebar.locator("[data-testid='stExpander']").filter(
            has_text=re.compile(r"Background jobs")
        )

    @property
    def background_jobs_content(self) -> Locator:
        """Visible content within the background-job center."""
        return self.background_jobs_expander.locator("[data-testid='stExpanderDetails']")

    def open_background_jobs(self) -> None:
        """Expand the job center while preserving an already-open state."""
        expect(self.background_jobs_expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if not self.background_jobs_content.is_visible():
            self.background_jobs_expander.locator("summary").click()
        expect(self.background_jobs_content).to_be_visible(timeout=self.RENDER_TIMEOUT)

    # Navigation

    def navigate_to(self, page_name: str) -> None:
        """Click a sidebar navigation button to switch pages.

        Args:
            page_name: Exact label of the sidebar nav button
                (e.g. "Data Source", "Data Managers").
        """
        btn = self.sidebar.get_by_role("button", name=page_name, exact=True)
        if btn.get_attribute("data-testid") == "stBaseButton-primary":
            self.wait_for_streamlit()
            return
        with self.expect_script_rerun():
            btn.click()
        # The route change requests another app run after the button's own run.
        expect(btn).to_have_attribute(
            "data-testid", "stBaseButton-primary", timeout=self.RENDER_TIMEOUT
        )

    def reset_all(self) -> None:
        """Wait for the reset's replacement Data Source projection to finish rendering."""
        deadline = time.monotonic() + self.RENDER_TIMEOUT / 1000

        def remaining() -> int:
            milliseconds = int((deadline - time.monotonic()) * 1000)
            assert milliseconds > 0, "Workspace reset exceeded the render budget"
            return milliseconds

        source_mode = self.page.get_by_role(
            "radiogroup", name="Select your data source:", exact=True
        )
        projection = self.page.get_by_test_id("stElementContainer").filter(has=source_mode)
        previous_identity = None
        count = projection.count()
        assert count in {0, 1}, "Expected at most one current Data Source projection"
        if count:
            classes = projection.get_attribute("class", timeout=remaining()) or ""
            identities = [
                token for token in classes.split() if token.startswith("st-key-data_source_choice")
            ]
            assert len(identities) == 1, "The source mode must expose its owned widget identity"
            previous_identity = identities[0]

        with self.expect_script_rerun(timeout=remaining()):
            self.sidebar.get_by_role("button", name="Reset All", exact=True).click(
                timeout=remaining()
            )
        # Reset retires the mode's widget key and requests a second app render.
        expect(projection).to_have_count(1, timeout=remaining())
        if previous_identity is not None:
            expect(projection).not_to_have_class(
                re.compile(rf"(?:^|\s){re.escape(previous_identity)}(?:\s|$)"),
                timeout=remaining(),
            )
        expect(
            self.sidebar.get_by_role("button", name="Data Source", exact=True)
        ).to_have_attribute("data-testid", "stBaseButton-primary", timeout=remaining())
        expect(
            source_mode.get_by_role("radio", name="Parse gem5 Stats Files", exact=True)
        ).to_be_checked(timeout=remaining())
        expect(
            self.page.get_by_role("textbox", name="Stats directory path", exact=True)
        ).to_have_value("/path/to/stats", timeout=remaining())
        rows = self.page.get_by_test_id("stMetric").filter(
            has=self.page.get_by_text("Rows", exact=True)
        )
        expect(rows).to_have_count(0, timeout=remaining())
        self.page.wait_for_function(_APP_IDLE, timeout=remaining())

    def _owned_listbox(
        self, control: Locator, *, timeout: int | None = None
    ) -> tuple[str, Locator]:
        """Capture a popup identity and locator before polling its rendered state."""
        effective_timeout = timeout or self.RENDER_TIMEOUT
        expect(control).to_have_attribute(
            "aria-controls", re.compile(r"\S+"), timeout=effective_timeout
        )
        popup_id = control.get_attribute("aria-controls", timeout=effective_timeout)
        assert popup_id is not None, "The combobox must own its open listbox"
        escaped_id = popup_id.replace("\\", "\\\\").replace('"', '\\"')
        listbox = self.page.get_by_role("listbox").and_(self.page.locator(f'[id="{escaped_id}"]'))
        return popup_id, listbox

    def _open_and_select(self, widget: Locator, value: str, *, multiple: bool = False) -> None:
        """Commit an exact owned option, retrying only an interrupted popup.

        Retry a closed or replaced popup within the existing render budget.
        An option missing from an intact popup fails without trying another one.
        Completion proves the closed control value or selected chips. Callers
        verify the resulting backend operation; fragment widgets need not emit
        a global script-running cycle.
        """
        control = widget.get_by_role("combobox")
        chip = widget.locator("[data-tag]").filter(has=self.page.get_by_text(value, exact=True))
        deadline = time.monotonic() + self.RENDER_TIMEOUT / 1000

        def remaining() -> int:
            milliseconds = int((deadline - time.monotonic()) * 1000)
            assert milliseconds > 0, f"Selection of {value!r} exceeded the render budget"
            return milliseconds

        def selected() -> bool:
            if multiple:
                return chip.count() == 1
            return (
                control.count() == 1
                and control.get_attribute("aria-expanded", timeout=remaining()) != "true"
                and control.input_value(timeout=remaining()) == value
            )

        def settle() -> None:
            self.wait_for_streamlit(timeout=remaining())

        def verify() -> None:
            if multiple:
                expect(control).to_have_attribute("aria-expanded", "false", timeout=remaining())
                expect(chip).to_have_count(1, timeout=remaining())
            else:
                expect(widget.get_by_role("combobox", expanded=False)).to_have_value(
                    value, timeout=remaining()
                )

        for attempt in range(3):
            expect(control).to_have_count(1, timeout=remaining())
            expect(control).to_be_visible(timeout=remaining())
            # Typed search text can survive a popup interruption without an option commit.
            if (multiple or attempt == 0) and selected():
                if (
                    multiple
                    and control.get_attribute("aria-expanded", timeout=remaining()) == "true"
                ):
                    control.press("Tab", timeout=remaining())
                settle()
                verify()
                return
            popup_id: str | None = None

            def interrupted() -> bool:
                if control.count() == 0:
                    return True
                current_popup = control.get_attribute("aria-controls", timeout=remaining())
                return control.get_attribute("aria-expanded", timeout=remaining()) != "true" or (
                    popup_id is not None and current_popup != popup_id
                )

            try:
                control.click(timeout=remaining())
                control.fill(value, timeout=remaining())
                popup_id, listbox = self._owned_listbox(control, timeout=min(1000, remaining()))
                expect(listbox).to_have_count(1, timeout=min(1000, remaining()))
                expect(listbox).to_be_visible(timeout=min(1000, remaining()))
                option = listbox.get_by_role("option", name=value, exact=True)
                expect(option).to_have_count(1, timeout=min(5000, remaining()))
                option.click(timeout=min(5000, remaining()))
            except (AssertionError, PlaywrightTimeoutError):
                if not interrupted():
                    raise
                settle()
                continue

            # Single selects close themselves; Escape can clear their committed value.
            # Tab closes an open multiselect without changing its selected chips.
            if multiple and control.get_attribute("aria-expanded", timeout=remaining()) == "true":
                control.press("Tab", timeout=remaining())
            settle()
            verify()
            return
        raise AssertionError(f"Could not select {value!r} after interrupted rerenders")

    @contextmanager
    def expect_script_rerun(self, *, timeout: int | None = None) -> Iterator[None]:
        """Observe a committed running/idle cycle after arming the triggering action.

        Streamlit delays the visual spinner for fast runs. Its own frontend
        message records completion after React commits, including runs too short
        to display the spinner. The host event has no request or fragment ID:
        callers must also verify an operation-specific result, such as finalized
        rows, a new pipeline step, or the current native chart values.
        """
        deadline = time.monotonic() + (timeout or self.RENDER_TIMEOUT) / 1000

        def remaining() -> int:
            milliseconds = int((deadline - time.monotonic()) * 1000)
            assert milliseconds > 0, "Streamlit script completion exceeded the render budget"
            return milliseconds

        generation: int | None = None
        while generation is None:
            self.page.wait_for_function(_APP_IDLE, timeout=remaining())
            generation = self.page.evaluate("""async () => {
                const key = '__ring5BrowserScriptCompletions';
                if (!window[key]) {
                    const observed = {next: 0, active: 0, completed: 0, running: false};
                    window[key] = observed;
                    window.addEventListener('message', event => {
                        if (event.source !== window || event.origin !== location.origin ||
                            event.data?.stCommVersion !== 1 ||
                            event.data.type !== 'SCRIPT_RUN_STATE_CHANGED' ||
                            !observed.active) return;
                        if (event.data.scriptRunState === 'running') observed.running = true;
                        if (event.data.scriptRunState === 'notRunning' && observed.running) {
                            observed.completed = observed.active;
                            observed.running = false;
                        }
                    });
                }
                const observed = window[key];
                observed.active = 0;
                observed.running = false;
                // A message on the same task source follows already-posted host events.
                await new Promise(resolve => {
                    const token = crypto.randomUUID();
                    const barrier = event => {
                        if (event.source === window && event.origin === location.origin &&
                            event.data?.ring5BrowserScriptBarrier === token) {
                            window.removeEventListener('message', barrier);
                            resolve();
                        }
                    };
                    window.addEventListener('message', barrier);
                    window.postMessage({ring5BrowserScriptBarrier: token}, location.origin);
                });
                const app = document.querySelector('[data-testid="stApp"]');
                if (app?.getAttribute('data-test-script-state') !== 'notRunning' ||
                    app.getAttribute('data-test-connection-state') !== 'CONNECTED') return null;
                observed.active = ++observed.next;
                return observed.active;
            }""")
        try:
            yield
            self.page.wait_for_function(
                """generation => {
                    const observed = window.__ring5BrowserScriptCompletions;
                    const app = document.querySelector('[data-testid="stApp"]');
                    return observed.completed === generation &&
                        app?.getAttribute('data-test-script-state') === 'notRunning' &&
                        app.getAttribute('data-test-connection-state') === 'CONNECTED';
                }""",
                arg=generation,
                timeout=remaining(),
            )
        finally:
            self.page.evaluate(
                """generation => {
                    const observed = window.__ring5BrowserScriptCompletions;
                    if (observed.active === generation) {
                        observed.active = 0;
                        observed.running = false;
                    }
                }""",
                generation,
            )

    # Streamlit sync helpers

    def wait_for_streamlit(self, *, timeout: int | None = None, expect_rerun: bool = False) -> None:
        """Wait until Streamlit finishes its current script run.

        When ``expect_rerun`` is true, wait briefly for Streamlit's running
        indicator to appear before waiting for it to disappear. Network-idle
        is unsuitable here because Streamlit and its chart components maintain
        long-lived connections.
        """
        effective_timeout = timeout or self.RENDER_TIMEOUT
        running = self.page.locator("[data-testid='stStatusWidget']")
        if expect_rerun:
            try:
                running.wait_for(state="visible", timeout=6_000)
            except PlaywrightTimeoutError:
                pass
        running.wait_for(state="hidden", timeout=effective_timeout)
        if expect_rerun:
            # Fast Streamlit reruns can appear and disappear between Playwright
            # polls.  Give the frontend one event-loop turn to apply the final
            # widget tree before another interaction starts a competing rerun.
            self.page.wait_for_timeout(250)

    def goto_and_wait(self, url: str) -> None:
        """Navigate to *url* and wait for Streamlit to render."""
        self.page.goto(url, wait_until="domcontentloaded")
        self.wait_for_streamlit()

    # Screenshot helpers

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

    # GIF generation

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

    # Assertion helpers

    def assert_page_loaded(self) -> None:
        """Assert the main app header is visible (basic health check)."""
        expect(self.main_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_on_page(self, page_name: str) -> None:
        """Assert the requested navigation button has Streamlit's active marker."""
        btn = self.sidebar.get_by_role("button", name=page_name, exact=True)
        expect(btn).to_be_visible()
        expect(btn).to_have_attribute("data-testid", "stBaseButton-primary")
