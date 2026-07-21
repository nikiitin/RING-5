"""Page object for browser-private automatic workspace recovery."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage


class AutosaveRecovery(BasePage):
    """Inspect and explicitly restore browser-owned local drafts."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    @property
    def expander(self) -> Locator:
        return self.sidebar.locator("[data-testid='stExpander']").filter(
            has_text="Autosave & recovery"
        )

    @property
    def recovery_point(self) -> Locator:
        return self.expander.get_by_role("combobox", name="Recovery point", exact=True)

    @property
    def recover_button(self) -> Locator:
        return self.expander.get_by_role("button", name="Recover", exact=True)

    def open(self) -> None:
        expect(self.expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        details = self.expander.locator("[data-testid='stExpanderDetails']")
        if not details.is_visible():
            self.expander.locator("summary").click()
        expect(details).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_draft_available(self) -> None:
        self.open()
        expect(self.recovery_point).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def recover(self) -> None:
        self.assert_draft_available()
        self.recover_button.click()
        self.wait_for_streamlit(expect_rerun=True)
