"""Page object for the global command palette and keyboard shortcuts."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage


class CommandPalette(BasePage):
    """Drive the palette through user-visible keyboard and dialog semantics."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    @property
    def launcher(self) -> Locator:
        return self.sidebar.get_by_role("button", name="Command palette", exact=True)

    @property
    def dialog(self) -> Locator:
        return self.page.get_by_role("dialog", name="Command palette")

    @property
    def input(self) -> Locator:
        return self.dialog.get_by_placeholder("Type a task or destination…")

    def open_with_shortcut(self) -> None:
        expect(self.launcher).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.page.keyboard.press("Control+k")
        self.wait_for_streamlit(expect_rerun=True)
        expect(self.dialog).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def search(self, query: str) -> None:
        self.input.fill(query)
        self.input.press("Enter")
        self.wait_for_streamlit(expect_rerun=True)

    def command(self, label: str) -> Locator:
        return self.dialog.get_by_role("button", name=label, exact=True)
