"""Page Object for the Portfolio page.

Covers:
- Save portfolio
- Load portfolio
- Manage saved portfolios
- Pipeline templates (save / apply)
"""

from __future__ import annotations

from playwright.sync_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

from tests.visual.pages.base_page import BasePage


class PortfolioPage(BasePage):
    """POM for the *Save/Load Portfolio* page."""

    PAGE_NAME: str = "Save/Load Portfolio"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # Navigation

    def navigate(self) -> None:
        """Open the Portfolio page via sidebar."""
        self.navigate_to(self.PAGE_NAME)
        expect(self.page_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    # Locators

    @property
    def page_header(self) -> Locator:
        """The 'Portfolio Management' heading."""
        return self.page.get_by_text("Portfolio Management")

    @property
    def save_name_input(self) -> Locator:
        """Text input for portfolio save name."""
        return self.page.get_by_label("Portfolio Name")

    @property
    def save_button(self) -> Locator:
        """'Save Portfolio' button."""
        return self.page.get_by_role("button", name="Save Portfolio")

    @property
    def load_selector(self) -> Locator:
        """Select box for choosing a portfolio to load."""
        return self.page.locator("[data-testid='stSelectbox']").filter(
            has=self.page.get_by_role("combobox", name="Select Portfolio", exact=True)
        )

    @property
    def load_button(self) -> Locator:
        """'Load Portfolio' button."""
        return self.page.get_by_role("button", name="Load Portfolio")

    @property
    def environment_expander(self) -> Locator:
        """Saved-versus-current reproducibility environment details."""
        return self.page.locator("[data-testid='stExpander']").filter(
            has_text="Reproducibility environment"
        )

    @property
    def integrity_expander(self) -> Locator:
        """Checksum and optional signature evidence for the selected portfolio."""
        return self.page.locator("[data-testid='stExpander']").filter(
            has_text="Portfolio integrity"
        )

    @property
    def report_expander(self) -> Locator:
        """Analysis-report composition workflow."""
        return self.page.locator("[data-testid='stExpander']").filter(has_text="Analysis report")

    @property
    def portable_bundle_expander(self) -> Locator:
        """Portable analysis bundle preparation and download workflow."""
        return self.page.locator("[data-testid='stExpander']").filter(
            has_text="Portable analysis bundle"
        )

    @property
    def prepare_bundle_button(self) -> Locator:
        """Prepare the selected portfolio's portable bundle."""
        return self.portable_bundle_expander.get_by_role("button", name="Prepare portable bundle")

    @property
    def download_bundle_button(self) -> Locator:
        """Download a previously prepared portable bundle."""
        return self.portable_bundle_expander.get_by_role("button", name="Download portable bundle")

    @property
    def report_title_input(self) -> Locator:
        """Report title input."""
        return self.page.get_by_label("Report title")

    @property
    def report_narrative_input(self) -> Locator:
        """Plain-language report narrative input."""
        return self.page.get_by_label("Narrative text")

    @property
    def build_report_button(self) -> Locator:
        """Build-report action."""
        return self.page.get_by_role("button", name="Build report")

    @property
    def download_html_report_button(self) -> Locator:
        """HTML report download action."""
        return self.page.get_by_role("button", name="Download HTML report")

    @property
    def download_html_gallery_button(self) -> Locator:
        """Interactive HTML gallery download action."""
        return self.page.get_by_role("button", name="Download HTML gallery")

    @property
    def analysis_recipes_expander(self) -> Locator:
        """Analysis-recipe capture and management workflow."""
        return self.page.locator("[data-testid='stExpander']").filter(has_text="Analysis recipes")

    @property
    def recipe_name_input(self) -> Locator:
        """Current-workspace recipe name."""
        return self.analysis_recipes_expander.get_by_label("Recipe name")

    @property
    def save_recipe_button(self) -> Locator:
        """Save-current-workspace recipe action."""
        return self.analysis_recipes_expander.get_by_role("button", name="Save analysis recipe")

    @property
    def recipe_saved_success(self) -> Locator:
        """Persistent recipe-save confirmation."""
        return self.page.locator("[data-testid='stAlertContentSuccess']").filter(
            has_text="Saved analysis recipe"
        )

    @property
    def saved_recipes_tab(self) -> Locator:
        """Saved recipe inspection tab."""
        return self.analysis_recipes_expander.get_by_role("tab", name="Saved", exact=True)

    @property
    def download_recipe_button(self) -> Locator:
        """Portable versioned recipe download action."""
        return self.analysis_recipes_expander.get_by_role("button", name="Download recipe JSON")

    @property
    def download_recipe_script_button(self) -> Locator:
        """Standalone public-API Python recipe download action."""
        return self.analysis_recipes_expander.get_by_role("button", name="Download Python script")

    @property
    def download_recipe_notebook_button(self) -> Locator:
        """Editable public-API notebook recipe download action."""
        return self.analysis_recipes_expander.get_by_role(
            "button", name="Download Jupyter notebook"
        )

    def managed_portfolio(self, name: str) -> Locator:
        """Return the management expander for one named portfolio."""
        return self.page.locator("[data-testid='stExpander']").filter(has_text=name)

    def compare_saved_versions_button(self, name: str) -> Locator:
        """Return the history comparison action for one named portfolio."""
        return self.managed_portfolio(name).get_by_role("button", name="Compare saved versions")

    @property
    def version_change_summary(self) -> Locator:
        """Successful field-level difference summary."""
        return self.page.locator("[data-testid='stAlertContentSuccess']").filter(
            has_text="setup change"
        )

    # Assertions

    def assert_page_header_visible(self) -> None:
        """Assert the portfolio heading is displayed."""
        expect(self.page_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_environment_match_visible(self) -> None:
        """Expand and verify the exact save-time environment match."""
        expect(self.environment_expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.environment_expander.get_by_text("Reproducibility environment", exact=True).click()
        expect(
            self.environment_expander.get_by_text(
                "Saved environment matches this RING-5 runtime exactly.", exact=True
            )
        ).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_checksum_integrity_visible(self) -> None:
        """Expand and verify honest checksum-only integrity wording."""
        expect(self.integrity_expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.integrity_expander.get_by_text("Portfolio integrity", exact=True).click()
        expect(
            self.integrity_expander.get_by_text(
                "Checksums match. This portfolio is unchanged but not signed.",
                exact=True,
            )
        ).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def open_report_composer(self) -> None:
        """Open the collapsed analysis-report workflow."""
        expect(self.report_expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.report_expander.locator("summary").click()
        expect(self.report_title_input).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def prepare_portable_bundle(self) -> None:
        """Prepare and expose a downloadable bundle for the selected portfolio."""
        expect(self.portable_bundle_expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if not self.prepare_bundle_button.is_visible():
            self.portable_bundle_expander.locator("summary").click()
        self.prepare_bundle_button.click()
        self.wait_for_streamlit(expect_rerun=True)
        if not self.download_bundle_button.is_visible():
            self.portable_bundle_expander.locator("summary").click()
        expect(self.download_bundle_button).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.page.wait_for_timeout(1_000)

    def open_analysis_recipes(self) -> None:
        """Open the recipe workflow when it is collapsed."""
        if not self.recipe_name_input.is_visible():
            self.analysis_recipes_expander.locator("summary").click()
        expect(self.recipe_name_input).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def save_current_as_recipe(self, name: str) -> None:
        """Capture the current source and plots under *name*."""
        self.open_analysis_recipes()
        self.recipe_name_input.fill(name)
        self.save_recipe_button.click()
        self.wait_for_streamlit(expect_rerun=True)
        self.page.wait_for_timeout(500)

    def open_saved_portfolio(self, name: str) -> None:
        """Expand the management panel for *name*."""
        expander = self.managed_portfolio(name)
        expect(expander).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if not self.compare_saved_versions_button(name).is_visible():
            expander.locator("summary").click()
        expect(self.compare_saved_versions_button(name)).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def compare_default_saved_versions(self, name: str) -> None:
        """Compare the default earlier and later versions for *name*."""
        self.open_saved_portfolio(name)
        self.compare_saved_versions_button(name).click()
        self.wait_for_streamlit()

    def select_portfolio(self, name: str) -> None:
        """Select *name* through the labeled portfolio control."""
        combobox = self.page.get_by_role("combobox", name="Select Portfolio", exact=True)
        expect(combobox).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if (combobox.text_content() or "").strip() == name:
            return
        option = self.page.get_by_role("option", name=name, exact=True)
        for attempt in range(3):
            combobox.click()
            try:
                option.wait_for(state="visible", timeout=5_000)
                option.click(timeout=5_000)
            except PlaywrightTimeoutError:
                self.page.keyboard.press("Escape")
                if attempt == 2:
                    raise
                continue
            self.wait_for_streamlit()
            return
