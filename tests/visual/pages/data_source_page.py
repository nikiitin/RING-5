"""Page Object for the Data Source page.

Covers the three data-source modes:
- Parse gem5 Stats Files  (parser config, scan, variable editor, parse)
- Upload data or portfolio  (validated browser-upload workflow)
- Load from Recent  (CSV pool with Load/Preview/Delete cards)

Every interactable widget on this page is exposed as a locator so that
Playwright tests can exercise it.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect

from tests.visual.pages.base_page import BasePage


class DataSourcePage(BasePage):
    """POM for the *Data Source* page.

    Sections:
    1. Step header + info box (always visible)
    2. Segmented control (3 modes — always visible)
    3. Parser config (Parse mode only)
       a. File Location inputs
       b. Parsing Strategy selector
       c. Variables to Extract (scan, editor, add dialog)
       d. Configuration Preview
       e. Parse button
    4. CSV mode message
    5. Recent CSV pool cards
    """

    PAGE_NAME: str = "Data Source"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # Navigation

    def navigate(self) -> None:
        """Open the Data Source page via sidebar."""
        self.navigate_to(self.PAGE_NAME)

    # SECTION 1: Top-level elements (always visible)

    @property
    def step_header(self) -> Locator:
        """The 'Step 1: Choose Data Source' heading."""
        return self.page.get_by_text("Step 1: Choose Data Source")

    @property
    def info_box(self) -> Locator:
        """The informational blue box describing the 3 data input methods."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stAlert']"
        ).first

    # SECTION 2: Segmented control (mode selector)

    @property
    def segmented_control(self) -> Locator:
        """The segmented control for selecting data source mode."""
        return self.page.get_by_role("radiogroup", name="Select your data source:")

    @property
    def parse_option(self) -> Locator:
        """'Parse gem5 Stats Files' option in the segmented control."""
        return self.segmented_control.get_by_role("radio", name="Parse gem5 Stats Files")

    @property
    def csv_option(self) -> Locator:
        """'Upload data or portfolio' option."""
        return self.segmented_control.get_by_role("radio", name="Upload data or portfolio")

    @property
    def recent_option(self) -> Locator:
        """'Load from Recent' option."""
        return self.segmented_control.get_by_role("radio", name="Load from Recent")

    # SECTION 3: Parser config (Parse mode)

    # 3a — Simulator selector (pills)

    @property
    def simulator_pills(self) -> Locator:
        """The simulator backend pills selector (key=simulator_selector)."""
        return self.page.get_by_role("radiogroup", name="Simulator")

    @property
    def gem5_pill(self) -> Locator:
        """The gem5 simulator pill button."""
        return self.simulator_pills.get_by_role("radio", name="gem5")

    # 3b — File Location

    @property
    def file_location_header(self) -> Locator:
        """The 'File Location' sub-heading."""
        return self.page.get_by_text("File Location", exact=True)

    @property
    def stats_path_input(self) -> Locator:
        """Text input for the stats directory path."""
        return self.page.locator("[data-testid='stTextInput'] input").first

    @property
    def stats_path_label(self) -> Locator:
        """Label for stats directory path."""
        return self.page.get_by_text("Stats directory path")

    @property
    def stats_pattern_input(self) -> Locator:
        """Text input for the file pattern (e.g. stats.txt)."""
        return self.page.locator("[data-testid='stTextInput'] input").nth(1)

    @property
    def stats_pattern_label(self) -> Locator:
        """Label for file pattern input."""
        return self.page.get_by_text("File pattern")

    # 3b — Parsing Strategy

    @property
    def strategy_header(self) -> Locator:
        """The 'Parsing Strategy' sub-heading."""
        return self.page.get_by_text("Parsing Strategy", exact=True)

    @property
    def strategy_segmented_control(self) -> Locator:
        """The strategy segmented control (Simple / Config-Aware)."""
        return self.page.get_by_role("radiogroup", name="Select ingestion strategy:")

    @property
    def strategy_simple_option(self) -> Locator:
        """'Simple (stats.txt only)' strategy button."""
        return self.strategy_segmented_control.get_by_role("radio", name="Simple (stats.txt only)")

    @property
    def strategy_config_aware_option(self) -> Locator:
        """'Config-Aware (Integrates config.ini)' strategy button."""
        return self.strategy_segmented_control.get_by_role(
            "radio", name="Config-Aware (Integrates config.ini)"
        )

    # 3c — Variables to Extract

    @property
    def variables_header(self) -> Locator:
        """The 'Variables to Extract' sub-heading."""
        return self.page.get_by_text("Variables to Extract", exact=True)

    @property
    def variables_description(self) -> Locator:
        """Container holding the variable type descriptions (markdown block)."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stMarkdownContainer']"
        ).filter(has_text="Define which variables to extract")

    @property
    def deep_scan_checkbox(self) -> Locator:
        """Bounded 'Deep Scan' checkbox."""
        return self.page.get_by_text(re.compile(r"Deep Scan \(up to \d+ files\)"))

    @property
    def quick_scan_button(self) -> Locator:
        """'🔍 Quick Scan' button."""
        return self.page.get_by_role("button", name="Quick Scan")

    @property
    def scan_result_message(self) -> Locator:
        """Success alert shown after scanning (e.g. 'Scanner found N variables')."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stAlertContentSuccess']"
        ).filter(has_text="Scanner found")

    @property
    def add_variable_button(self) -> Locator:
        """'➕ Add Variable' button."""
        return self.page.get_by_role("button", name="Add Variable")

    # 3d — Configuration Preview

    @property
    def config_preview_header(self) -> Locator:
        """The 'Configuration Preview' sub-heading."""
        return self.page.get_by_text("Configuration Preview", exact=True)

    @property
    def config_json_view(self) -> Locator:
        """The JSON configuration preview block."""
        return self.page.locator("[data-testid='stJson']")

    # 3e — Parse button (outside fragment)

    @property
    def parse_button(self) -> Locator:
        """'Parse gem5 Stats Files' primary action button."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stBaseButton-primary']"
        ).filter(has_text="Parse gem5 Stats Files")

    @property
    def incremental_parse_checkbox(self) -> Locator:
        """The human-facing changed-file reuse control."""
        return self.page.get_by_role("checkbox", name="Reuse unchanged simulator files")

    @property
    def parser_config_section(self) -> Locator:
        """The entire parser config region (markdown separator to bottom)."""
        return self.page.get_by_text("gem5 Stats Parser Configuration")

    @property
    def parser_error_message(self) -> Locator:
        """Error alert shown when parsing fails or path is empty."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stAlertContentError']"
        )

    # SECTION 4: CSV mode

    @property
    def csv_success_message(self) -> Locator:
        """Success message shown in upload mode."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stAlertContentSuccess']"
        ).filter(has_text="Upload mode selected")

    @property
    def browser_upload_input(self) -> Locator:
        """Browser file chooser for a dataset or portfolio."""
        return self.page.locator("input[type='file']")

    @property
    def upload_origin_control(self) -> Locator:
        """Selector between local browser and remote sources."""
        return self.page.get_by_role("radiogroup", name="Source location")

    @property
    def remote_source_option(self) -> Locator:
        """Remote-source option inside upload mode."""
        return self.upload_origin_control.get_by_role("radio", name="Remote source")

    @property
    def local_source_option(self) -> Locator:
        """Browser-local source option inside upload mode."""
        return self.upload_origin_control.get_by_role("radio", name="This computer")

    @property
    def remote_adapter_select(self) -> Locator:
        """Remote transport adapter selector."""
        return self.page.get_by_text("Remote adapter", exact=True)

    @property
    def remote_https_url_input(self) -> Locator:
        """HTTPS remote-source URL input."""
        return self.page.get_by_label("HTTPS URL")

    # SECTION 5: Recent CSV pool (Load from Recent mode)

    @property
    def recent_header(self) -> Locator:
        """'Recent CSV Files' heading."""
        return self.page.get_by_text("Recent CSV Files", exact=True)

    @property
    def empty_pool_warning(self) -> Locator:
        """Warning when no CSV files exist in the pool."""
        return self.page.get_by_text("No CSV files in the pool yet")

    @property
    def pool_file_count_info(self) -> Locator:
        """Info alert showing CSV file count."""
        return self.page.locator("[data-testid='stAlertContentInfo']").filter(
            has_text="CSV file(s) in the pool"
        )

    def pool_card_load_button(self, index: int = 0) -> Locator:
        """'Review & Load' button for a specific CSV pool card."""
        return self.page.get_by_role("button", name="Review & Load").nth(index)

    def pool_card_preview_button(self, index: int = 0) -> Locator:
        """'Preview' button for a specific CSV pool card."""
        return self.page.get_by_role("button", name="Preview").nth(index)

    def pool_card_delete_button(self, index: int = 0) -> Locator:
        """'Delete' button for a specific CSV pool card."""
        return self.page.get_by_role("button", name="Delete").nth(index)

    @property
    def import_review_header(self) -> Locator:
        """Structured review heading below the recent-file cards."""
        return self.page.get_by_text("Review tabular import", exact=True)

    @property
    def import_detection_summary(self) -> Locator:
        """Detected text encoding and delimiter summary."""
        return self.page.locator("[data-testid='stAlertContentInfo']").filter(has_text="Detected")

    @property
    def import_accepted_metric(self) -> Locator:
        """Accepted-row count from the structured preview."""
        return self.page.locator("[data-testid='stMetric']").filter(has_text="Accepted rows")

    @property
    def load_accepted_import_button(self) -> Locator:
        """Explicit action that loads the reviewed accepted rows."""
        return self.page.get_by_role("button", name="Load accepted rows")

    @property
    def pool_expanders(self) -> Locator:
        """All file card expanders in the Recent section."""
        return self.page.locator("[data-testid='stExpander']")

    # SECTION 6: Add Variable dialog

    @property
    def dialog_overlay(self) -> Locator:
        """The modal dialog overlay container."""
        return self.page.locator("[data-testid='stDialog']")

    @property
    def dialog_title(self) -> Locator:
        """Title bar of the Add Variable dialog ('Add Variable')."""
        return self.dialog_overlay.get_by_text("Add Variable")

    @property
    def dialog_search_pill(self) -> Locator:
        """'Search Scanned Variables' pill in the dialog."""
        return self.dialog_overlay.get_by_role("radio", name="Search Scanned Variables")

    @property
    def dialog_manual_pill(self) -> Locator:
        """'Manual Entry' pill in the dialog."""
        return self.dialog_overlay.get_by_role("radio", name="Manual Entry")

    @property
    def dialog_no_vars_warning(self) -> Locator:
        """Warning when no scanned variables exist."""
        return self.dialog_overlay.locator("[data-testid='stAlertContentWarning']").filter(
            has_text="No variables scanned yet"
        )

    @property
    def dialog_search_selectbox(self) -> Locator:
        """The search selectbox in the dialog."""
        return self.dialog_overlay.locator("[data-testid='stSelectbox']")

    @property
    def dialog_manual_name_input(self) -> Locator:
        """'Variable Name' text input in Manual Entry mode."""
        return self.dialog_overlay.locator("[data-testid='stTextInput'] input").first

    @property
    def dialog_manual_type_selectbox(self) -> Locator:
        """'Type' selectbox in Manual Entry mode."""
        return self.dialog_overlay.locator("[data-testid='stSelectbox']")

    @property
    def dialog_search_info(self) -> Locator:
        """'Start typing...' info message in search mode."""
        return self.dialog_overlay.locator("[data-testid='stAlertContentInfo']").filter(
            has_text="Start typing"
        )

    @property
    def dialog_advanced_expander(self) -> Locator:
        """'Advanced Options' expander in the dialog."""
        return self.dialog_overlay.locator("[data-testid='stExpander']")

    @property
    def dialog_add_button(self) -> Locator:
        """'Add to Configuration' primary button in the dialog."""
        return self.dialog_overlay.locator("[data-testid='stBaseButton-primary']")

    @property
    def dialog_name_error(self) -> Locator:
        """Error when variable name is missing."""
        return self.dialog_overlay.locator("[data-testid='stAlertContentError']").filter(
            has_text="Variable name is required"
        )

    @property
    def dialog_close_button(self) -> Locator:
        """Close (X) button on the dialog header."""
        return self.dialog_overlay.locator("button[aria-label='Close']")

    # SECTION 7: Variable editor (visible when variables are configured)

    @property
    def current_variables_label(self) -> Locator:
        """'Current Variables:' label above the variable list."""
        return self.page.get_by_text("Current Variables:")

    @property
    def variable_search_selectbox(self) -> Locator:
        """'Search available variables' selectbox in the editor."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] [data-testid='stSelectbox']"
        ).filter(has_text="Search available variables")

    @property
    def add_selected_button(self) -> Locator:
        """'Add Selected' button in the variable editor."""
        return self.page.get_by_role("button", name="Add Selected")

    @property
    def add_manual_button(self) -> Locator:
        """'+ Add Manual' button in the variable editor."""
        return self.page.get_by_role("button", name="Add Manual")

    # SECTION 8: Parsing dialog

    @property
    def parse_dialog(self) -> Locator:
        """The 'Parsing gem5 Stats' dialog."""
        return self.page.locator("[data-testid='stDialog']")

    @property
    def parse_dialog_progress(self) -> Locator:
        """Progress bar inside the parse dialog."""
        return self.parse_dialog.locator("[role='progressbar']")

    @property
    def parse_close_button(self) -> Locator:
        """'Close & Reload' button in the parse dialog."""
        return self.parse_dialog.get_by_role("button", name="Close & Reload")

    # Actions

    def _is_mode_active(self, option: Locator) -> bool:
        """Return whether a segmented-control radio option is selected."""
        return option.is_checked()

    def _select_mode(self, option: Locator) -> None:
        """Select a segmented-control option and wait for its rerun."""
        if option.is_checked():
            return
        option.click()
        self.wait_for_streamlit(expect_rerun=True)

    def ensure_parse_mode(self) -> None:
        """Ensure Parse mode is active without toggling it off.

        If Parse mode is already active (default), do nothing.
        If not active, click it to activate.
        """
        self._select_mode(self.parse_option)

    def select_parse_mode(self) -> None:
        """Click the 'Parse gem5 Stats Files' option."""
        self._select_mode(self.parse_option)

    def select_csv_mode(self) -> None:
        """Click the browser-upload option."""
        # A completed fragment rerun can leave the top-level radio checked while its previous
        # parser body is still mounted. A Parse round-trip gives the mode switch a full rerun.
        if self.csv_option.is_checked() and not self.csv_success_message.is_visible():
            self.parse_option.click()
            self.wait_for_streamlit(expect_rerun=True)
        self._select_mode(self.csv_option)
        expect(self.csv_success_message).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def select_remote_source(self) -> None:
        """Open the remote-source form within upload mode."""
        self.select_csv_mode()
        self._select_mode(self.remote_source_option)

    def select_recent_mode(self) -> None:
        """Click the 'Load from Recent' option."""
        self._select_mode(self.recent_option)

    def fill_stats_path(self, path: str) -> None:
        """Type a value into the stats directory path input."""
        self.stats_path_input.fill(path)
        self.stats_path_input.press("Tab")
        self.wait_for_streamlit()
        # Extra stabilisation after fragment rerender
        self.page.wait_for_timeout(500)

    def fill_stats_pattern(self, pattern: str) -> None:
        """Type a value into the file pattern input."""
        self.stats_pattern_input.fill(pattern)
        self.stats_pattern_input.press("Tab")
        self.wait_for_streamlit()
        # Extra stabilisation after fragment rerender
        self.page.wait_for_timeout(500)

    def select_simple_strategy(self) -> None:
        """Select the 'Simple' parsing strategy."""
        self._select_mode(self.strategy_simple_option)

    def ensure_simple_strategy(self) -> None:
        """Ensure 'Simple' strategy is active without toggling it off.

        Same pattern as ``ensure_parse_mode`` — only clicks if not
        already active.
        """
        self._select_mode(self.strategy_simple_option)

    def select_config_aware_strategy(self) -> None:
        """Select the 'Config-Aware' parsing strategy."""
        self._select_mode(self.strategy_config_aware_option)

    def ensure_config_aware_strategy(self) -> None:
        """Ensure 'Config-Aware' strategy is active without toggling it off."""
        self._select_mode(self.strategy_config_aware_option)

    def toggle_deep_scan(self) -> None:
        """Toggle the 'Deep Scan' checkbox."""
        self.deep_scan_checkbox.click()
        self.wait_for_streamlit()

    def click_quick_scan(self) -> None:
        """Click the '🔍 Quick Scan' button."""
        # Wait for button to be stable (fragment may still be rerendering)
        expect(self.quick_scan_button).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.quick_scan_button.click(force=True)
        # Don't wait — scan may take time or fail; the test controls timing

    def click_add_variable(self) -> None:
        """Click '➕ Add Variable' to open the Add Variable dialog."""
        self.add_variable_button.click()
        self.wait_for_streamlit()

    def click_parse(self) -> None:
        """Click the primary 'Parse gem5 Stats Files' button."""
        self.parse_button.click()
        self.wait_for_streamlit()

    def open_add_variable_dialog(self) -> None:
        """Open the Add Variable dialog and wait for it to appear."""
        self.click_add_variable()
        expect(self.dialog_overlay).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def close_dialog(self) -> None:
        """Close the dialog via the X button."""
        self.dialog_close_button.click()
        self.wait_for_streamlit()

    def close_dialog_with_escape(self) -> None:
        """Close the dialog by pressing Escape."""
        self.page.keyboard.press("Escape")
        # Explicitly wait for the dialog overlay to disappear
        self.dialog_overlay.wait_for(state="hidden", timeout=self.RENDER_TIMEOUT)

    def close_dialog_by_clicking_outside(self) -> None:
        """Close the dialog by clicking outside the modal overlay."""
        # Click on the backdrop area (top-left corner, outside dialog)
        self.page.mouse.click(5, 5)
        self.wait_for_streamlit()

    def switch_dialog_to_manual(self) -> None:
        """Switch the Add Variable dialog to Manual Entry mode."""
        self._select_mode(self.dialog_manual_pill)

    def switch_dialog_to_search(self) -> None:
        """Switch the Add Variable dialog to Search Scanned Variables."""
        self._select_mode(self.dialog_search_pill)

    def fill_dialog_manual_name(self, name: str) -> None:
        """Type a variable name in the Manual Entry dialog."""
        self.dialog_manual_name_input.fill(name)
        self.dialog_manual_name_input.press("Tab")
        self.wait_for_streamlit()

    def click_dialog_add(self) -> None:
        """Click 'Add to Configuration' in the dialog."""
        self.dialog_add_button.click()
        self.wait_for_streamlit()

    def load_recent_csv(self, index: int = 0) -> None:
        """Review and load a CSV from the Recent-CSV pool by card index.

        The most-recent card is auto-expanded, so its 'Review & Load' button
        is immediately actionable.

        Args:
            index: Zero-based pool-card index (sorted newest first).
        """
        self.select_recent_mode()
        self.pool_card_load_button(index).click()
        self.wait_for_streamlit()
        expect(self.import_review_header).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.load_accepted_import_button.click()
        self.wait_for_streamlit()

    def load_recent_csv_by_name(self, filename: str) -> None:
        """Load a specific CSV from the Recent-CSV pool by filename.

        Deterministic under load and a large/cluttered pool (the failure mode
        behind the `-n 3` "No data loaded" tier1 errors): waits for the named
        card to render, expands it if collapsed (only the newest card is
        auto-expanded), reviews the file, confirms accepted rows, then
        ASSERTS the load registered. The assertion is essential —
        ``wait_for_streamlit`` returns even when a raced click triggered no
        rerun, so without it a missed click fails silently downstream.

        Args:
            filename: Exact pool filename (e.g. ``e2e_staged_gw0_sample_data.csv``).
        """
        self.select_recent_mode()
        card = self.page.locator("[data-testid='stExpander']").filter(has_text=filename).first
        expect(card).to_be_visible(timeout=30_000)
        load_btn = card.get_by_role("button", name="Review & Load")
        if not load_btn.is_visible():
            # Collapsed (another worker's freshly-staged file is newer) — expand.
            card.locator("summary").click()
            self.wait_for_streamlit()
        expect(load_btn).to_be_visible(timeout=30_000)
        # Dispatch the click straight to the button: the expander's open
        # ``<details>`` element can intercept normal pointer events on the
        # button (mid-open), which otherwise times out the click.
        load_btn.dispatch_event("click")
        self.wait_for_streamlit()
        expect(self.import_review_header).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.load_accepted_import_button.click()
        self.wait_for_streamlit()
        # Confirm the load actually took (guards against a raced no-op click).
        expect(
            self.page.get_by_text(re.compile(r"Loaded\s+\d+\s+(?:reviewed\s+)?rows")).first
        ).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def review_recent_csv_by_name(self, filename: str) -> None:
        """Open the structured import review for a named recent CSV."""
        self.select_recent_mode()
        card = self.page.locator("[data-testid='stExpander']").filter(has_text=filename).first
        expect(card).to_be_visible(timeout=30_000)
        preview_button = card.get_by_role("button", name="Preview")
        if not preview_button.is_visible():
            card.locator("summary").click()
            self.wait_for_streamlit()
        expect(preview_button).to_be_visible(timeout=30_000)
        preview_button.dispatch_event("click")
        self.wait_for_streamlit()
        expect(self.import_review_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def stage_csv(self, csv_path: str | Path) -> str:
        """Copy a local CSV into the server-side recent-file pool."""
        import os

        from src.core.services.data_services.csv_pool_service import CsvPoolService

        pool_dir = CsvPoolService.get_pool_dir()
        pool_dir.mkdir(parents=True, exist_ok=True)
        worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
        staged = pool_dir / f"e2e_staged_{worker}_{Path(csv_path).stem}.csv"
        shutil.copy(str(csv_path), str(staged))
        return staged.name

    def upload_csv(self, csv_path: str | Path) -> None:
        """Upload, review, and explicitly load a CSV from a browser path.

        Args:
            csv_path: Absolute path to the CSV file to load.
        """
        for attempt in range(2):
            try:
                self.select_csv_mode()
                self.upload_origin_control.wait_for(
                    state="visible",
                    timeout=self.RENDER_TIMEOUT,
                )
                self._select_mode(self.local_source_option)
                self.browser_upload_input.set_input_files(str(csv_path))
                self.wait_for_streamlit()
                self.import_review_header.wait_for(
                    state="visible",
                    timeout=self.RENDER_TIMEOUT,
                )
                break
            except PlaywrightTimeoutError:
                if attempt:
                    raise
                self.parse_option.click()
                self.wait_for_streamlit(expect_rerun=True)
        self.load_accepted_import_button.click()
        self.wait_for_streamlit()

    # Assertions

    def assert_step_header_visible(self) -> None:
        """Assert the step header is displayed."""
        expect(self.step_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_info_box_visible(self) -> None:
        """Assert the info box with data input methods is visible."""
        expect(self.info_box).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_segmented_control_visible(self) -> None:
        """Assert the segmented control is rendered."""
        expect(self.segmented_control).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_all_mode_options_visible(self) -> None:
        """Assert all three mode buttons are visible in the segmented control."""
        expect(self.parse_option).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.csv_option).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.recent_option).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_parse_mode_active(self) -> None:
        """Assert Parse mode is the currently active segmented option."""
        expect(self.parse_option).to_be_checked(timeout=self.RENDER_TIMEOUT)

    def assert_csv_mode_active(self) -> None:
        """Assert CSV mode is the currently active segmented option."""
        expect(self.csv_option).to_be_checked(timeout=self.RENDER_TIMEOUT)

    def assert_recent_mode_active(self) -> None:
        """Assert Recent mode is the currently active segmented option."""
        expect(self.recent_option).to_be_checked(timeout=self.RENDER_TIMEOUT)

    def assert_parser_config_visible(self) -> None:
        """Assert the entire parser configuration section is visible."""
        expect(self.parser_config_section).to_be_visible(
            timeout=self.RENDER_TIMEOUT,
        )

    def assert_parser_config_hidden(self) -> None:
        """Assert the parser config section is NOT visible."""
        expect(self.parser_config_section).not_to_be_visible(
            timeout=self.RENDER_TIMEOUT,
        )

    def assert_file_location_visible(self) -> None:
        """Assert both File Location inputs are visible."""
        expect(self.file_location_header).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.stats_path_input).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.stats_pattern_input).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_strategy_section_visible(self) -> None:
        """Assert the Parsing Strategy header and control are visible."""
        expect(self.strategy_header).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.strategy_segmented_control).to_be_visible(
            timeout=self.RENDER_TIMEOUT,
        )

    def assert_variables_section_visible(self) -> None:
        """Assert the Variables to Extract section is visible."""
        expect(self.variables_header).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.quick_scan_button).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.add_variable_button).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_config_preview_visible(self) -> None:
        """Assert the Configuration Preview section is visible."""
        expect(self.config_preview_header).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.config_json_view).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_parse_button_visible(self) -> None:
        """Assert the primary Parse button is visible."""
        expect(self.parse_button).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_csv_mode_message_visible(self) -> None:
        """Assert the upload-mode success message is shown."""
        expect(self.csv_success_message).to_be_visible(
            timeout=self.RENDER_TIMEOUT,
        )

    def assert_csv_mode_message_hidden(self) -> None:
        """Assert CSV mode success message is NOT shown."""
        expect(self.csv_success_message).not_to_be_visible(
            timeout=self.RENDER_TIMEOUT,
        )

    def assert_recent_mode_content_visible(self) -> None:
        """Assert Recent mode rendered — either empty warning or file cards."""
        import re

        # Pool may or may not be empty depending on environment
        content = self.page.locator("[data-testid='stMainBlockContainer']")
        # Either we see the warning or we see file count info
        expect(content).to_contain_text(
            re.compile(r"No CSV files in the pool yet|CSV file\(s\) in the pool"),
            timeout=self.RENDER_TIMEOUT,
        )

    def assert_recent_header_visible(self) -> None:
        """Assert the 'Recent CSV Files' heading is visible."""
        expect(self.recent_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_dialog_visible(self) -> None:
        """Assert the Add Variable dialog is open."""
        expect(self.dialog_overlay).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_dialog_hidden(self) -> None:
        """Assert no modal dialog is open."""
        expect(self.dialog_overlay).not_to_be_visible(
            timeout=self.RENDER_TIMEOUT,
        )

    def assert_data_loaded(self, *, row_count: int | None = None) -> None:
        """Assert that data has been loaded (the data-summary metrics are shown).

        Scopes to the ``st.metric("Rows", …)`` card to avoid the strict-mode
        clash a bare ``get_by_text("Rows")`` hits (multiple matches on the page).

        Args:
            row_count: If provided, verify the 'Rows' metric value matches.
        """
        rows_metric = self.page.locator("[data-testid='stMetric']").filter(has_text="Rows").first
        expect(rows_metric).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if row_count is not None:
            value = rows_metric.locator("[data-testid='stMetricValue']")
            expect(value).to_contain_text(str(row_count), timeout=self.RENDER_TIMEOUT)

    # E2E: Scan workflow

    def scan_and_wait(self, *, timeout: int = 30_000) -> None:
        """Click Quick Scan and wait for the scan to complete.

        After the scan finishes the source code calls ``st.rerun()``,
        which rebuilds the page.  The success message ("Scanner found N
        variables") appears only **after** that rerun.  So we wait for
        that message instead of trying to track the status widget.
        """
        self.click_quick_scan()
        # The scan triggers a status widget, then st.rerun().
        # After rerun the success alert is rendered.
        # Wait for the success message to appear (post-rerun).
        expect(self.scan_result_message).to_be_visible(timeout=timeout)

    def assert_scan_success(self) -> None:
        """Assert that the scan completed and the success message is shown."""
        expect(self.scan_result_message).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def get_scan_result_count(self) -> int:
        """Extract the number of variables found from the scan success msg.

        Returns:
            The number of variables discovered by the scanner.
        """
        import re

        text = self.scan_result_message.text_content() or ""
        match = re.search(r"(\d+)\s+variables", text)
        return int(match.group(1)) if match else 0

    # E2E: Add variable from scanned results (dialog Search mode)

    def add_variable_from_scan(self, index: int = 0) -> None:
        """Open dialog, select a scanned variable by index, and add it.

        After selecting a variable and clicking "Add to Configuration",
        Streamlit calls ``st.rerun()`` which auto-closes the dialog.

        Args:
            index: Zero-based index in the scanned variable list.
        """
        self.open_add_variable_dialog()
        # Wait for the selectbox to appear (scan data available)
        expect(self.dialog_search_selectbox).to_be_visible(timeout=self.RENDER_TIMEOUT)
        # Click the selectbox to open its dropdown
        self.dialog_search_selectbox.get_by_role("button", name="Open").click()
        # Select the option by index
        options = self.page.get_by_role("option")
        expect(options.first).to_be_visible(timeout=self.RENDER_TIMEOUT)
        options.nth(index).click()
        self.wait_for_streamlit()
        # Now the config form appears; click Add
        expect(self.dialog_add_button).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.dialog_add_button.click()
        # Dialog auto-closes via st.rerun() — wait for it to disappear
        expect(self.dialog_overlay).not_to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.wait_for_streamlit()

    def add_manual_variable(self, name: str, var_type: str = "scalar") -> None:
        """Open dialog, enter a manual variable, and add it.

        After clicking "Add to Configuration" Streamlit calls
        ``st.rerun()`` which auto-closes the dialog.

        Args:
            name: Variable name (e.g. ``system.cpu.ipc``).
            var_type: One of scalar, vector, distribution, configuration.
        """
        self.open_add_variable_dialog()
        self.switch_dialog_to_manual()
        self.fill_dialog_manual_name(name)

        # Change type if not scalar (default)
        if var_type != "scalar":
            selectbox = self.dialog_manual_type_selectbox
            selectbox.get_by_role("button", name="Open").click()
            option = self.page.get_by_role("option", name=var_type, exact=True)
            option.click()
            self.wait_for_streamlit()

        # Click "Add to Configuration"
        expect(self.dialog_add_button).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.dialog_add_button.click()

        # Dialog auto-closes via st.rerun() on success. If this helper is called
        # twice in the same session, close the duplicate-variable warning.
        try:
            expect(self.dialog_overlay).not_to_be_visible(timeout=5_000)
        except (AssertionError, Exception):
            # Check if it's the "already exists" warning
            warning = self.dialog_overlay.locator("[data-testid='stAlertContentWarning']")
            if warning.count() > 0 and "already exists" in (warning.inner_text() or ""):
                # Variable already exists in this session.
                self.close_dialog()
                expect(self.dialog_overlay).not_to_be_visible(timeout=self.RENDER_TIMEOUT)
            else:
                # Unknown error — re-raise
                raise
        self.wait_for_streamlit()

    # E2E: Variable editor — verify added variables

    @property
    def variable_name_inputs(self) -> Locator:
        """All variable name inputs in the variable editor."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] "
            "[data-testid='stTextInput'] input[placeholder='stats.name']"
        )

    def get_variable_count(self) -> int:
        """Return the number of currently configured variables."""
        return self.variable_name_inputs.count()

    def assert_variable_exists(self, name: str) -> None:
        """Assert a variable with the given name is in the editor."""
        _ = self.variable_name_inputs.filter(has=self.page.locator(f"[value='{name}']"))
        # Fallback: check by value attribute
        found = False
        for i in range(self.variable_name_inputs.count()):
            val = self.variable_name_inputs.nth(i).get_attribute("value") or ""
            if name in val:
                found = True
                break
        if not found:
            # Use expect for nice error message
            expect(self.page.locator(f"input[value='{name}']")).to_be_visible(
                timeout=self.RENDER_TIMEOUT
            )

    # E2E: Parse workflow

    def parse_and_wait(self, *, timeout: int = 60_000) -> None:
        """Click Parse and wait for the parse dialog to complete.

        Waits for the progress bar to reach 100% and the
        'Close & Reload' button to appear.
        """
        self.click_parse()
        # Wait for the parse dialog to appear
        expect(self.parse_dialog).to_be_visible(timeout=timeout)
        # Wait for "Close & Reload" button (appears on success)
        expect(self.parse_close_button).to_be_visible(timeout=timeout)

    def close_parse_dialog_and_reload(self) -> None:
        """Click 'Close & Reload' in the parse dialog to reload the page."""
        expect(self.parse_close_button).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.parse_close_button.click()
        self.wait_for_streamlit()

    def assert_parse_dialog_shows_errors(self) -> None:
        """Assert the parse dialog shows error messages."""
        error_text = self.parse_dialog.locator("[data-testid='stAlertContentError']")
        expect(error_text).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_parse_dialog_shows_no_results(self) -> None:
        """Assert the parse dialog reports no results generated."""
        warning = self.parse_dialog.locator("[data-testid='stAlertContentWarning']")
        expect(warning).to_be_visible(timeout=self.RENDER_TIMEOUT)
