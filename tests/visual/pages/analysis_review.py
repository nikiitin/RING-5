"""Page object for the persistent portable analysis review panel."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage


class AnalysisReview(BasePage):
    """Drive review authorship and status controls through visible labels."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    @property
    def expander(self) -> Locator:
        return self.sidebar.locator("[data-testid='stExpander']").filter(has_text="Analysis review")

    @property
    def author_input(self) -> Locator:
        return self.expander.get_by_role("textbox", name="Author ID", exact=True)

    @property
    def status_select(self) -> Locator:
        return self.expander.get_by_role("combobox", name="Review status", exact=True)

    @property
    def comment_input(self) -> Locator:
        return self.expander.get_by_role("textbox", name="Review comment", exact=True)

    @property
    def add_button(self) -> Locator:
        return self.expander.get_by_role("button", name="Add review update", exact=True)

    def open(self) -> None:
        expect(self.expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        details = self.expander.locator("[data-testid='stExpanderDetails']")
        if not details.is_visible():
            self.expander.locator("summary").click()
        expect(details).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def add_update(self, author: str, comment: str, status: str) -> None:
        self.open()
        self.author_input.fill(author)
        self.author_input.press("Enter")
        self.wait_for_streamlit(expect_rerun=True)
        self.open()
        self.status_select.click()
        self.status_select.press("ArrowDown")
        self.status_select.press("Enter")
        self.wait_for_streamlit(expect_rerun=True)
        expect(self.status_select).to_have_value(status)
        self.open()
        self.comment_input.fill(comment)
        self.comment_input.press("Control+Enter")
        self.wait_for_streamlit(expect_rerun=True)
        self.open()
        self.add_button.click()
        self.wait_for_streamlit(expect_rerun=True)
