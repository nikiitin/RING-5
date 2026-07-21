"""Page object for workspace favorites and tags."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage


class WorkspaceOrganizer(BasePage):
    """Drive the persistent organizer through visible controls."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    @property
    def expander(self) -> Locator:
        return self.sidebar.locator("[data-testid='stExpander']").filter(
            has_text="Favorites & tags"
        )

    @property
    def tags_input(self) -> Locator:
        return self.expander.get_by_role("textbox", name="Tags")

    @property
    def artifact_control(self) -> Locator:
        return self.expander.locator("[data-testid='stSelectbox']").filter(
            has=self.page.get_by_text("Artifact", exact=True)
        )

    @property
    def artifact_select(self) -> Locator:
        return self.artifact_control.get_by_role("combobox", name="Artifact", exact=True)

    @property
    def favorite_checkbox(self) -> Locator:
        return self.expander.get_by_role("checkbox", name="Favorite", exact=True)

    @property
    def save_button(self) -> Locator:
        return self.expander.get_by_role("button", name="Save organization", exact=True)

    def open(self) -> None:
        expect(self.expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        details = self.expander.locator("[data-testid='stExpanderDetails']")
        if not details.is_visible():
            self.expander.locator("summary").click()
        expect(details).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def select_artifact(self, label: str) -> None:
        self.artifact_control.get_by_role("button", name="Open").click()
        option = self.page.get_by_role("option", name=label, exact=True)
        expect(option).to_be_visible(timeout=self.RENDER_TIMEOUT)
        option.click()
        self.wait_for_streamlit(expect_rerun=True)

    def organize(
        self,
        tags: str,
        *,
        favorite: bool = True,
        artifact_label: str | None = None,
    ) -> None:
        self.open()
        if artifact_label is not None:
            self.select_artifact(artifact_label)
        self.tags_input.fill(tags)
        self.tags_input.press("Enter")
        self.wait_for_streamlit(expect_rerun=True)
        if self.favorite_checkbox.is_checked() != favorite:
            self.favorite_checkbox.set_checked(favorite, force=True)
            self.wait_for_streamlit(expect_rerun=True)
        self.save_button.click()
        self.wait_for_streamlit(expect_rerun=True)
