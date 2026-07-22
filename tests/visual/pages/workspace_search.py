"""Page object for the persistent workspace search sidebar."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage


class WorkspaceSearch(BasePage):
    """Interact with search without coupling tests to Streamlit's widget order."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    @property
    def expander(self) -> Locator:
        return self.sidebar.locator("[data-testid='stExpander']").filter(
            has_text="Search workspace"
        )

    @property
    def input(self) -> Locator:
        return self.expander.get_by_placeholder("Type two or more letters…")

    def open(self) -> None:
        """Expand the search interface if it is currently collapsed."""
        expect(self.expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        details = self.expander.locator("[data-testid='stExpanderDetails']")
        if not details.is_visible():
            self.expander.locator("summary").click()
        expect(details).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def search(self, query: str) -> None:
        """Replace the query and wait for Streamlit to return results."""
        self.open()
        self.input.fill(query)
        self.input.press("Enter")
        self.wait_for_streamlit(expect_rerun=True)

    def link_result(self, label: str) -> Locator:
        """Return an exact documentation result link."""
        return self.expander.get_by_role("link", name=label, exact=True)

    def button_result(self, label: str) -> Locator:
        """Return an exact workspace result button."""
        return self.expander.get_by_role("button", name=label, exact=True)
