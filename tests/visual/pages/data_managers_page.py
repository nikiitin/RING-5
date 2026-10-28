"""Page Object for the Data Managers page.

Covers all 11 tabs:
- Summary
- Data Visualization
- Workspace
- Seeds Reducer
- Outlier Remover
- Preprocessor
- Mixer
- Compare
- Data Quality
- Schema Contract
- Operations History
"""

from __future__ import annotations

from playwright.sync_api import (
    Download,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

from tests.visual.pages.base_page import BasePage


class DataManagersPage(BasePage):
    """POM for the *Data Managers* page."""

    PAGE_NAME: str = "Data Managers"

    TAB_NAMES: tuple[str, ...] = (
        "Summary",
        "Data Visualization",
        "Workspace",
        "Seeds Reducer",
        "Outlier Remover",
        "Preprocessor",
        "Mixer",
        "Compare",
        "Data Quality",
        "Schema Contract",
        "Operations History",
    )

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # Helpers — tab-aware locators

    def _by_label(self, test_id: str, label_text: str) -> Locator:
        """Return a locator for a widget with ``data-testid`` filtered by label.

        Streamlit renders all tab panels in the DOM simultaneously and hides
        inactive ones via CSS, so a label can appear in several panels at once
        (e.g. "Group by columns" / "New Column Name" exist in more than one tab).
        Scoping to ``:visible`` restricts the match to the **active** tab panel,
        preventing strict-mode "resolved to N elements" failures. Callers must
        ``select_tab(...)`` the relevant tab first (the tests do).
        """
        return self.page.locator(f"[data-testid='{test_id}']:visible").filter(has_text=label_text)

    # Navigation

    def navigate(self) -> None:
        """Open the Data Managers page via sidebar."""
        self.navigate_to(self.PAGE_NAME)
        expect(self.page_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    # Locators

    @property
    def page_header(self) -> Locator:
        """The 'Data Managers & Transformations' heading."""
        return self.page.get_by_text("Data Managers & Transformations")

    @property
    def no_data_warning(self) -> Locator:
        """The 'No data loaded' warning shown when data is absent."""
        return self.page.get_by_text("No data loaded")

    @property
    def tab_bar(self) -> Locator:
        """The tab bar container."""
        return self.page.locator("[role='tablist']")

    # Tab navigation

    def select_tab(self, tab_name: str) -> None:
        """Click a tab by its label.

        Args:
            tab_name: One of ``TAB_NAMES``.
        """
        tab = self.page.get_by_role("tab", name=tab_name)
        for _ in range(3):
            try:
                tab.click(timeout=5_000)
                expect(tab).to_have_attribute("aria-selected", "true", timeout=5_000)
                return
            except (AssertionError, PlaywrightTimeoutError):
                # Navigation can replace the complete tab list while this click
                # is in flight. Wait for that run and retry through the locator.
                self.wait_for_streamlit()
        expect(tab).to_have_attribute("aria-selected", "true", timeout=self.RENDER_TIMEOUT)

    def get_tab(self, tab_name: str) -> Locator:
        """Return the tab locator by name."""
        return self.page.get_by_role("tab", name=tab_name)

    # Data Visualization downloads

    @property
    def prepare_view_download_button(self) -> Locator:
        """Return the action that prepares the visible table for CSV download."""
        return self.page.get_by_role("button", name="Download Current View as CSV", exact=True)

    @property
    def current_view_download_button(self) -> Locator:
        """Return the download for the prepared visualization table."""
        return self.page.get_by_role("button", name="Click to Download", exact=True)

    def download_current_view(self) -> Download:
        """Download the current Data Visualization table through its visible UI."""
        self.select_tab("Data Visualization")
        self.prepare_view_download_button.click()
        with self.page.expect_download() as pending:
            self.current_view_download_button.click()
        return pending.value

    def clear_multiselect(self, widget: Locator) -> None:
        """Remove selected options with the multiselect's normal keyboard control."""
        control = widget.get_by_role("combobox")
        tags = widget.locator("[data-tag]")
        count = tags.count()
        for remaining in range(count - 1, -1, -1):
            control.fill("")
            control.press("Backspace")
            expect(tags).to_have_count(remaining, timeout=self.RENDER_TIMEOUT)
            self.wait_for_streamlit(expect_rerun=True)
        control.press("Escape")

    # Summary tab locators

    @property
    def summary_rows_metric(self) -> Locator:
        """Rows metric in the summary tab."""
        return self.page.get_by_text("Total Rows")

    @property
    def summary_columns_metric(self) -> Locator:
        """Columns metric in the summary tab."""
        return self.page.get_by_text("Total Columns")

    # Seeds Reducer tab locators

    @property
    def seeds_categorical_select(self) -> Locator:
        """Categorical column selector in Seeds Reducer."""
        return self._by_label("stMultiSelect", "Group by columns")

    @property
    def apply_seeds_button(self) -> Locator:
        """Apply Seeds Reducer button."""
        return self.page.get_by_role("button", name="Apply")

    @property
    def reducer_target_selectbox(self) -> Locator:
        """'Column to reduce over' selectbox in Seeds Reducer."""
        return self._by_label("stSelectbox", "Column to reduce over")

    # Data Visualization tab

    @property
    def search_input(self) -> Locator:
        """Column search input in Data Visualization tab."""
        return self.page.get_by_placeholder("Search")

    @property
    def dataframe_view(self) -> Locator:
        """The dataframe rendered in Data Visualization tab.

        Scoped by label to avoid picking dataframes from hidden tabs.
        """
        return self._by_label("stDataFrame", "Data Table")

    # Operations History tab

    @property
    def history_container(self) -> Locator:
        """Container for operation history entries."""
        return self.page.get_by_text("Operations History")

    # Assertions

    def assert_page_header_visible(self) -> None:
        """Assert the main page heading is shown."""
        expect(self.page_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_no_data_warning(self) -> None:
        """Assert the 'no data' warning is displayed."""
        expect(self.no_data_warning).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_tabs_visible(self) -> None:
        """Assert all 11 tabs are present."""
        expect(self.tab_bar).to_be_visible(timeout=self.RENDER_TIMEOUT)
        for tab_name in self.TAB_NAMES:
            expect(self.get_tab(tab_name)).to_be_visible()

    def assert_tab_active(self, tab_name: str) -> None:
        """Assert a specific tab is selected."""
        tab = self.get_tab(tab_name)
        expect(tab).to_have_attribute("aria-selected", "true")

    def assert_has_data(self) -> None:
        """Assert that data is loaded (Summary tab shows metrics, not warnings)."""
        self.select_tab("Summary")
        # Use stMetric to find the "Rows" metric specifically
        rows_metric = self.page.locator("[data-testid='stMetric']").filter(has_text="Rows")
        expect(rows_metric.first).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_summary_has_rows(self, expected: int | None = None) -> None:
        """Assert Summary tab shows row count, optionally exact value."""
        self.select_tab("Summary")
        rows_metric = self.page.locator("[data-testid='stMetric']").filter(has_text="Rows")
        expect(rows_metric.first).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if expected is not None:
            expect(rows_metric.first).to_contain_text(str(expected), timeout=self.RENDER_TIMEOUT)

    def assert_summary_has_columns(self, expected: int | None = None) -> None:
        """Assert Summary shows a column count, optionally an exact value.

        Scopes to the ``st.metric`` card; a bare ``get_by_text("Columns")``
        matched ~23 elements on the page (strict-mode violation).
        """
        cols_metric = self.page.locator("[data-testid='stMetric']").filter(has_text="Columns")
        expect(cols_metric.first).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if expected is not None:
            value = cols_metric.first.locator("[data-testid='stMetricValue']")
            expect(value).to_have_text(str(expected), timeout=self.RENDER_TIMEOUT)

    # E2E: Seeds Reducer

    @property
    def seeds_no_random_seed_warning(self) -> Locator:
        """Warning when no suitable columns exist for reduction."""
        return self.page.locator("[data-testid='stAlertContentWarning']").filter(
            has_text="No suitable columns"
        )

    @property
    def seeds_apply_button(self) -> Locator:
        """'Apply Seeds Reducer' button."""
        return self.page.get_by_role("button", name="Apply Seeds Reducer")

    @property
    def seeds_confirm_button(self) -> Locator:
        """'Confirm and Apply Seeds Reducer' primary button."""
        return self.page.get_by_role("button", name="Confirm and Apply Seeds Reducer")

    @property
    def seeds_categorical_multiselect(self) -> Locator:
        """Categorical columns multiselect in Seeds Reducer tab."""
        return self._by_label("stMultiSelect", "Group by columns")

    @property
    def seeds_numeric_multiselect(self) -> Locator:
        """Numeric columns multiselect in Seeds Reducer tab."""
        return self._by_label("stMultiSelect", "Calculate stats for")

    def assert_seeds_requires_random_seed(self) -> None:
        """Assert Seeds Reducer shows the 'no suitable columns' warning."""
        expect(self.seeds_no_random_seed_warning).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_reducer_ready(self) -> None:
        """Assert Seeds Reducer is ready (target column selector visible)."""
        expect(self.reducer_target_selectbox).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def apply_seeds_reducer(self) -> None:
        """Click 'Apply Seeds Reducer' and wait."""
        self.seeds_apply_button.click()
        self.wait_for_streamlit()

    def confirm_seeds_reducer(self) -> None:
        """Publish the preview and await its consumed confirmation after app refresh."""
        with self.expect_script_rerun():
            self.seeds_confirm_button.click()
        expect(self.seeds_confirm_button).to_have_count(0, timeout=self.RENDER_TIMEOUT)

    # E2E: Outlier Remover

    @property
    def outlier_column_selectbox(self) -> Locator:
        """Column selector for outlier detection."""
        return self._by_label("stSelectbox", "Column to check for outliers")

    @property
    def outlier_apply_button(self) -> Locator:
        """'Apply Outlier Remover' button."""
        return self.page.get_by_role("button", name="Apply Outlier Remover")

    @property
    def outlier_confirm_button(self) -> Locator:
        """'Confirm and Apply Outlier Remover' primary button."""
        return self.page.get_by_role("button", name="Confirm and Apply Outlier Remover")

    @property
    def outlier_metrics(self) -> Locator:
        """Metric widgets showing Min/Q3/Max/Mean for the selected column."""
        return self.page.locator("[data-testid='stMetric']")

    def assert_outlier_shows_metrics(self) -> None:
        """Assert Outlier Remover shows distribution metrics."""
        metrics = self.page.locator("[data-testid='stMetric']")
        expect(metrics.filter(has_text="Min").first).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(metrics.filter(has_text="Q3").first).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def select_outlier_column(self, column: str) -> None:
        """Select the exact numeric column for outlier detection."""
        self._open_and_select(self.outlier_column_selectbox, column)

    def apply_outlier_remover(self) -> None:
        """Click 'Apply Outlier Remover' and wait."""
        self.outlier_apply_button.click()
        self.wait_for_streamlit()

    def confirm_outlier_remover(self) -> None:
        """Publish the preview and await its consumed confirmation after app refresh."""
        with self.expect_script_rerun():
            self.outlier_confirm_button.click()
        expect(self.outlier_confirm_button).to_have_count(0, timeout=self.RENDER_TIMEOUT)

    # E2E: Preprocessor

    @property
    def preproc_src1_selectbox(self) -> Locator:
        """Source Column 1 selectbox in Preprocessor (found by label)."""
        return self._by_label("stSelectbox", "Source Column 1")

    @property
    def preproc_operation_selectbox(self) -> Locator:
        """Operation selectbox in Preprocessor.

        Both Preprocessor (tab 5) and Mixer (tab 6) have an
        ``"Operation"`` selectbox.  Preprocessor appears first in DOM
        order, so ``.first`` selects the correct one.
        """
        return self._by_label("stSelectbox", "Operation").first

    @property
    def preproc_src2_selectbox(self) -> Locator:
        """Source Column 2 selectbox in Preprocessor."""
        return self._by_label("stSelectbox", "Source Column 2")

    @property
    def preproc_name_input(self) -> Locator:
        """New column name text input in Preprocessor."""
        return self._by_label("stTextInput", "New column name").locator("input")

    @property
    def preproc_preview_button(self) -> Locator:
        """'Preview Result' button in Preprocessor."""
        return self.page.get_by_role("button", name="Preview Result")

    @property
    def preproc_confirm_button(self) -> Locator:
        """'Confirm and Add Column to Dataset' primary button."""
        return self.page.get_by_role("button", name="Confirm and Add Column to Dataset")

    def apply_preprocessor_preview(self) -> None:
        """Click 'Preview Result' and wait."""
        self.preproc_preview_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    def confirm_preprocessor(self) -> None:
        """Publish the preview and await its consumed confirmation after app refresh."""
        with self.expect_script_rerun():
            self.preproc_confirm_button.click()
        expect(self.preproc_confirm_button).to_have_count(0, timeout=self.RENDER_TIMEOUT)

    # E2E: Mixer

    @property
    def mixer_mode_control(self) -> Locator:
        """Mixer Mode segmented control."""
        return self.page.get_by_role("radiogroup", name="Mixer Mode")

    @property
    def mixer_columns_multiselect(self) -> Locator:
        """Select columns to merge multiselect (found by label)."""
        return self._by_label("stMultiSelect", "Select columns to merge")

    @property
    def mixer_operation_selectbox(self) -> Locator:
        """Operation selectbox for Mixer.

        Both Preprocessor (tab 5) and Mixer (tab 6) have an
        ``"Operation"`` selectbox.  Mixer appears last in DOM order.
        """
        return self._by_label("stSelectbox", "Operation").last

    @property
    def mixer_preview_button(self) -> Locator:
        """'Preview Merge' button."""
        return self.page.get_by_role("button", name="Preview Merge")

    @property
    def mixer_confirm_button(self) -> Locator:
        """'Confirm and Merge' primary button."""
        return self.page.get_by_role("button", name="Confirm and Merge")

    @property
    def mixer_new_name_input(self) -> Locator:
        """New column name text input in Mixer."""
        return self._by_label("stTextInput", "New Column Name").locator("input")

    @property
    def mixer_separator_input(self) -> Locator:
        """Separator between values in a configuration merge."""
        return self.page.get_by_role("textbox", name="Separator", exact=True)

    def add_mixer_column(self, column: str) -> None:
        """Add the exact source column and verify its selected chip."""
        self._open_and_select(self.mixer_columns_multiselect, column, multiple=True)

    def apply_mixer_preview(self) -> None:
        """Click 'Preview Merge' and wait."""
        self.mixer_preview_button.click()
        self.wait_for_streamlit()

    def confirm_mixer(self) -> None:
        """Publish the preview and await its consumed confirmation after app refresh."""
        with self.expect_script_rerun():
            self.mixer_confirm_button.click()
        expect(self.mixer_confirm_button).to_have_count(0, timeout=self.RENDER_TIMEOUT)

    # E2E: Baseline comparison

    @property
    def comparison_group_selectbox(self) -> Locator:
        """Experiment-group column selector."""
        return self._by_label("stSelectbox", "Experiment column")

    @property
    def comparison_method_selectbox(self) -> Locator:
        """Threshold or statistical comparison selector."""
        return self._by_label("stSelectbox", "Comparison method")

    @property
    def comparison_metrics_multiselect(self) -> Locator:
        """Metrics selected for comparison."""
        return self._by_label("stMultiSelect", "Metrics")

    @property
    def comparison_keys_multiselect(self) -> Locator:
        """Columns used to align baseline and candidate rows."""
        return self._by_label("stMultiSelect", "Alignment keys")

    def add_comparison_metric(self, column: str) -> None:
        """Add the exact metric and verify its selected chip."""
        self._open_and_select(self.comparison_metrics_multiselect, column, multiple=True)

    def add_comparison_key(self, column: str) -> None:
        """Add the exact alignment column and verify its selected chip."""
        self._open_and_select(self.comparison_keys_multiselect, column, multiple=True)

    @property
    def comparison_apply_button(self) -> Locator:
        """Button that calculates the comparison preview."""
        return self.page.get_by_role("button", name="Compare", exact=True)

    @property
    def comparison_confirm_button(self) -> Locator:
        """Button that replaces the active data with the comparison result."""
        return self.page.get_by_role("button", name="Use Comparison Result")

    @property
    def comparison_json_download_button(self) -> Locator:
        """Download button for the versioned regression JSON document."""
        return self.page.get_by_role("button", name="Download results JSON")

    @property
    def comparison_junit_download_button(self) -> Locator:
        """Download button for the regression JUnit XML document."""
        return self.page.get_by_role("button", name="Download JUnit XML")

    def download_comparison(self, file_format: str) -> Download:
        """Transfer one current comparison artifact through its visible download control."""
        labels = {
            "csv": "Download comparison CSV",
            "json": "Download results JSON",
            "junit": "Download JUnit XML",
        }
        with self.page.expect_download(timeout=self.RENDER_TIMEOUT) as pending:
            self.page.get_by_role("button", name=labels[file_format], exact=True).click()
        return pending.value

    @property
    def regression_plot(self) -> Locator:
        """Accessible regression-outcome chart in the comparison preview."""
        return self.page.locator("[data-testid='stCustomComponentV1']:visible")

    def apply_comparison(self) -> None:
        """Calculate the comparison and wait for the preview."""
        self.comparison_apply_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    # E2E: Named dataset workspace

    @property
    def workspace_name_input(self) -> Locator:
        """Name used to retain the current active dataset."""
        return self._by_label("stTextInput", "Name for current data").locator("input")

    @property
    def workspace_retain_button(self) -> Locator:
        """Button that stores the current table under a workspace name."""
        return self.page.get_by_role("button", name="Retain Current Dataset")

    @property
    def workspace_dataset_metric(self) -> Locator:
        """Count of retained named datasets."""
        return self.page.locator("[data-testid='stMetric']").filter(has_text="Retained datasets")

    @property
    def workspace_dataset_metric_value(self) -> Locator:
        """Numeric retained-dataset count inside the workspace metric."""
        return self.workspace_dataset_metric.locator("[data-testid='stMetricValue']")

    @property
    def workspace_snapshots_panel(self) -> Locator:
        """Persistent dataset snapshot controls."""
        return self.page.get_by_text("Reusable dataset snapshots", exact=True)

    @property
    def workspace_snapshot_name_input(self) -> Locator:
        """Local reusable snapshot name."""
        return self.page.get_by_role("textbox", name="Snapshot name", exact=True)

    @property
    def workspace_snapshot_save_button(self) -> Locator:
        """Save the selected dataset as a reusable snapshot."""
        return self.page.get_by_role("button", name="Save Reusable Snapshot")

    @property
    def workspace_snapshot_output_input(self) -> Locator:
        """Workspace dataset name for a loaded snapshot."""
        return self.page.get_by_role("textbox", name="Loaded dataset name", exact=True)

    @property
    def workspace_snapshot_load_button(self) -> Locator:
        """Verify and load the selected reusable snapshot."""
        return self.page.get_by_role("button", name="Verify and Load Snapshot")

    @property
    def workspace_lineage_panel(self) -> Locator:
        """Expanded lineage and recovery panel for the selected dataset."""
        return self.page.get_by_text("Lineage & recovery", exact=True)

    @property
    def workspace_undo_button(self) -> Locator:
        """Restore the preceding dataset revision."""
        return self.page.get_by_role("button", name="Undo Last Change")

    @property
    def workspace_redo_button(self) -> Locator:
        """Reapply the most recently undone dataset revision."""
        return self.page.get_by_role("button", name="Redo Change")

    @property
    def workspace_restore_button(self) -> Locator:
        """Restore the revision selected for inspection."""
        return self.page.get_by_role("button", name="Restore This Revision")

    @property
    def workspace_operation_selectbox(self) -> Locator:
        """Workspace compare, join, or append operation selector."""
        return self._by_label("stSelectbox", "Workspace operation")

    @property
    def workspace_dataset_selectbox(self) -> Locator:
        """Currently inspected named dataset selector."""
        return self._by_label("stSelectbox", "Workspace dataset")

    @property
    def workspace_activate_button(self) -> Locator:
        """Make the inspected dataset active without changing other retained tables."""
        return self.page.get_by_role("button", name="Activate Dataset", exact=True)

    @property
    def workspace_remove_button(self) -> Locator:
        """Remove the inspected named dataset."""
        return self.page.get_by_role("button", name="Remove Dataset", exact=True)

    @property
    def workspace_append_name_input(self) -> Locator:
        """Name assigned to a newly appended dataset."""
        return self.page.get_by_role("textbox", name="Appended dataset name", exact=True)

    @property
    def workspace_append_button(self) -> Locator:
        """Append the selected sources under a new name."""
        return self.page.get_by_role("button", name="Append Retained Datasets", exact=True)

    @property
    def workspace_revision_selectbox(self) -> Locator:
        """Immutable revision inspected in the lineage panel."""
        return self._by_label("stSelectbox", "Inspect revision")

    @property
    def workspace_snapshot_source_selectbox(self) -> Locator:
        """Named source whose exact data will be saved in a reusable snapshot."""
        return self._by_label("stSelectbox", "Dataset to snapshot")

    def activate_workspace_dataset(self, name: str) -> None:
        """Select and explicitly activate one named dataset."""
        self.select_tab("Workspace")
        self._open_and_select(self.workspace_dataset_selectbox, name)
        self.workspace_activate_button.click()
        self.wait_for_streamlit(expect_rerun=True)
        expect(self.workspace_dataset_selectbox.get_by_role("combobox")).to_have_value(name)

    @property
    def workspace_join_left(self) -> Locator:
        """Left named dataset selector."""
        return self._by_label("stSelectbox", "Left dataset")

    @property
    def workspace_join_right(self) -> Locator:
        """Right named dataset selector."""
        return self._by_label("stSelectbox", "Right dataset")

    @property
    def workspace_join_mode(self) -> Locator:
        """Inner, left, right or outer join selected for the composed dataset."""
        return self._by_label("stSelectbox", "Join mode")

    @property
    def workspace_join_keys(self) -> Locator:
        """Shared key-column selector for retained-dataset joins."""
        return self._by_label("stMultiSelect", "Join keys")

    def add_workspace_join_key(self, column: str) -> None:
        """Add the exact join column and verify its selected chip."""
        self._open_and_select(self.workspace_join_keys, column, multiple=True)

    @property
    def workspace_join_cardinality(self) -> Locator:
        """Expected left/right key relationship selector."""
        return self._by_label("stSelectbox", "Expected key relationship")

    @property
    def workspace_join_button(self) -> Locator:
        """Cardinality-gated join action."""
        return self.page.get_by_role("button", name="Validate and Join Datasets")

    @property
    def workspace_join_output_input(self) -> Locator:
        """Name for the validated join output."""
        return self._by_label("stTextInput", "Joined dataset name").locator("input")

    @property
    def workspace_cardinality_metric(self) -> Locator:
        """Current join-cardinality diagnostic status."""
        return self.page.locator("[data-testid='stMetric']").filter(has_text="Cardinality")

    def retain_current_dataset(self, name: str) -> None:
        """Retain the active dataset under ``name`` and wait for rerendering."""
        previous_count = 0
        if self.workspace_dataset_metric_value.count():
            expect(self.workspace_dataset_metric_value).to_be_visible(timeout=self.RENDER_TIMEOUT)
            previous_count = int(self.workspace_dataset_metric_value.inner_text())
        self.workspace_name_input.fill(name)
        self.workspace_retain_button.click()
        self.wait_for_streamlit(expect_rerun=True)
        expect(self.workspace_dataset_metric_value).to_have_text(
            str(previous_count + 1), timeout=self.RENDER_TIMEOUT
        )

    def open_workspace_snapshots(self) -> None:
        """Expand the reusable snapshot controls when collapsed."""
        if not self.workspace_snapshot_name_input.is_visible():
            self.workspace_snapshots_panel.click()
            expect(self.workspace_snapshot_name_input).to_be_visible()
        self.page.wait_for_timeout(300)

    def save_workspace_snapshot(self, name: str) -> None:
        """Save the selected workspace dataset and wait for rerendering."""
        self.open_workspace_snapshots()
        self.workspace_snapshot_name_input.fill(name)
        self.page.keyboard.press("Tab")
        self.wait_for_streamlit()
        self.open_workspace_snapshots()
        self.workspace_snapshot_save_button.click()
        self.wait_for_streamlit()

    def load_workspace_snapshot(self, dataset_name: str) -> None:
        """Verify the selected snapshot, load it, and wait for rerendering."""
        self.open_workspace_snapshots()
        self.workspace_snapshot_output_input.fill(dataset_name)
        self.page.keyboard.press("Tab")
        self.wait_for_streamlit()
        self.open_workspace_snapshots()
        self.workspace_snapshot_load_button.click()
        self.wait_for_streamlit()

    def undo_workspace_dataset(self) -> None:
        """Undo one named-dataset revision and wait for the rerender."""
        self.workspace_undo_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    def redo_workspace_dataset(self) -> None:
        """Redo one named-dataset revision and wait for the rerender."""
        self.workspace_redo_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    def join_workspace_datasets(self) -> None:
        """Execute the validated join and wait for the workspace rerender."""
        self.workspace_join_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    # E2E: Data quality

    @property
    def quality_profile_button(self) -> Locator:
        """Button that calculates the data-quality report."""
        return self.page.get_by_role("button", name="Profile Dataset")

    @property
    def quality_schema_metric(self) -> Locator:
        """Schema-violation summary metric."""
        return self.page.locator("[data-testid='stMetric']").filter(has_text="Schema violations")

    def download_quality_profile(self) -> Download:
        """Transfer the per-column quality report through its ordinary CSV download."""
        with self.page.expect_download(timeout=self.RENDER_TIMEOUT) as pending:
            self.page.get_by_role("button", name="Download quality profile", exact=True).click()
        return pending.value

    def profile_data(self) -> None:
        """Calculate the data-quality report and wait for rendering."""
        self.quality_profile_button.click()
        self.wait_for_streamlit()

    # E2E: Dataset schema contract

    @property
    def schema_contract_panel(self) -> Locator:
        """The active schema editor, validation report and unit-conversion controls."""
        return self.page.get_by_role("tabpanel", name="Schema Contract", exact=True)

    @property
    def schema_contract_editor(self) -> Locator:
        """The explicitly keyed rule editor, excluding read-only report tables."""
        return self.schema_contract_panel.locator(
            ".st-key-manager-schema_contract-rules"
        ).get_by_test_id("stDataFrame")

    def _select_schema_rule_cell(self, column: str, field: str) -> tuple[Locator, Locator]:
        """Navigate owned grid cells by their global IDs and virtualized ARIA headers."""
        editor = self.schema_contract_editor
        expect(editor).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        canvas = editor.get_by_test_id("data-grid-canvas")
        # Glide's scroller owns pointer events above its keyboard-focus canvas.
        scroller = editor.locator(".dvn-scroller")
        expect(scroller).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        scroller.hover()
        canvas.focus()
        grid = editor.locator('table[role="grid"]')
        expect(grid).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        selected = grid.locator('[role="gridcell"][aria-selected="true"]')
        expect(selected).to_have_count(1, timeout=self.RENDER_TIMEOUT)

        def position(cell: Locator) -> tuple[int, int]:
            cell_id = cell.get_attribute("id")
            assert cell_id is not None and cell_id.startswith("glide-cell-"), cell_id
            coordinates = cell_id.removeprefix("glide-cell-").split("-")
            assert len(coordinates) == 2, cell_id
            return int(coordinates[0]), int(coordinates[1])

        def await_cell(column_index: int, row_index: int) -> Locator:
            cell = grid.get_by_test_id(f"glide-cell-{column_index}-{row_index}")
            expect(cell).to_have_attribute("aria-selected", "true", timeout=self.RENDER_TIMEOUT)
            return cell

        current_column, current_row = position(selected)
        # Read source-column labels at the left edge. Avoid a no-op Home command
        # and await each React selection before sending its next navigation key.
        for column_index in range(current_column - 1, -1, -1):
            canvas.press("ArrowLeft")
            await_cell(column_index, current_row)
        for row_index in range(current_row - 1, -1, -1):
            canvas.press("ArrowUp")
            await_cell(0, row_index)
        first_column = grid.locator('tbody [role="gridcell"][aria-colindex="1"]')
        names = first_column.all_text_contents()
        assert names.count(column) == 1, f"Expected one schema source column {column!r}: {names}"
        _, target_row = position(first_column.nth(names.index(column)))

        header = grid.get_by_role("columnheader", name=field, exact=True, include_hidden=True)
        if header.count() == 0:
            column_count = grid.get_attribute("aria-colcount")
            assert column_count is not None
            last_column = int(column_count) - 1
            current_column, current_row = position(selected)
            if current_column != last_column:
                canvas.press("End")
                await_cell(last_column, current_row)
            expect(header).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        header_index = header.get_attribute("aria-colindex")
        assert header_index is not None, f"Schema rule header {field!r} has no global column index"
        target_column = int(header_index) - 1
        current_column, current_row = position(selected)
        horizontal_key = "ArrowRight" if target_column > current_column else "ArrowLeft"
        horizontal_step = 1 if target_column > current_column else -1
        for column_index in range(
            current_column + horizontal_step, target_column + horizontal_step, horizontal_step
        ):
            canvas.press(horizontal_key)
            await_cell(column_index, current_row)
        for row_index in range(current_row + 1, target_row + 1):
            canvas.press("ArrowDown")
            await_cell(target_column, row_index)
        return canvas, await_cell(target_column, target_row)

    def edit_schema_rule(self, column: str, field: str, value: str) -> None:
        """Commit a rule through the grid's printable-key overlay without canvas coordinates."""
        assert value and value[0].isprintable() and not value[0].isspace()
        canvas, cell = self._select_schema_rule_cell(column, field)
        expect(cell).to_have_attribute("aria-readonly", "false")
        canvas.press(value[0])
        overlay = self.page.locator("input.gdg-input:visible, textarea.gdg-input:visible")
        expect(overlay).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        overlay.fill(value)
        overlay.press("Enter")
        expect(overlay).to_have_count(0, timeout=self.RENDER_TIMEOUT)
        canvas.focus()
        expect(cell).to_have_text(value, timeout=self.RENDER_TIMEOUT)

    def schema_rule_value(self, column: str, field: str) -> str:
        """Read an exact accessible rule cell through the grid's native horizontal scroller."""
        editor = self.schema_contract_editor
        expect(editor).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        scroller = editor.locator(".dvn-scroller")
        expect(scroller).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        grid = editor.locator('table[role="grid"]')
        expect(grid).to_have_count(1, timeout=self.RENDER_TIMEOUT)

        def scroll_to_edge(*, right: bool) -> None:
            position = scroller.evaluate(
                "element => ({current: element.scrollLeft, "
                "last: element.scrollWidth - element.clientWidth})"
            )
            target = position["last"] if right else 0
            if position["current"] != target:
                scroller.hover()
                self.page.mouse.wheel(target - position["current"], 0)
                expect(scroller).to_have_js_property(
                    "scrollLeft", target, timeout=self.RENDER_TIMEOUT
                )

        source = grid.get_by_role("gridcell", name=column, exact=True, include_hidden=True).and_(
            grid.locator('[aria-colindex="1"]')
        )
        if source.count() == 0:
            scroll_to_edge(right=False)
        expect(source).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        source_id = source.get_attribute("id")
        assert source_id is not None and source_id.startswith("glide-cell-0-"), source_id
        row_index = int(source_id.removeprefix("glide-cell-0-"))

        header = grid.get_by_role("columnheader", name=field, exact=True, include_hidden=True)
        if header.count() == 0:
            scroll_to_edge(right=True)
        expect(header).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        header_index = header.get_attribute("aria-colindex")
        assert header_index is not None, f"Schema rule header {field!r} has no global column index"
        cell = grid.get_by_test_id(f"glide-cell-{int(header_index) - 1}-{row_index}")
        expect(cell).to_have_count(1, timeout=self.RENDER_TIMEOUT)
        return cell.inner_text()

    @property
    def schema_failed_rules_metric(self) -> Locator:
        """Number of rejected schema rules for the current validation."""
        return self.schema_contract_panel.get_by_test_id("stMetric").filter(has_text="Failed rules")

    @property
    def schema_affected_rows_metric(self) -> Locator:
        """Number of row-level failures in the current schema report."""
        return self.schema_contract_panel.get_by_test_id("stMetric").filter(
            has_text="Affected rows"
        )

    @property
    def schema_unit_column_selectbox(self) -> Locator:
        """Declared metric selected for physical unit conversion."""
        return self._by_label("stSelectbox", "Column to convert")

    @property
    def schema_unit_target_selectbox(self) -> Locator:
        """Target unit selector whose label states the retained source unit."""
        return self._by_label("stSelectbox", "Target unit (currently")

    def convert_schema_unit(self, column: str, target: str) -> None:
        """Submit an explicit unit conversion through the schema controls."""
        self._open_and_select(self.schema_unit_column_selectbox, column)
        self._open_and_select(self.schema_unit_target_selectbox, target)
        with self.expect_script_rerun():
            self.schema_contract_panel.get_by_role(
                "button", name="Convert Unit", exact=True
            ).click()

    @property
    def schema_contract_validate_button(self) -> Locator:
        """Button that validates the editable schema contract."""
        return self.page.get_by_role("button", name="Validate Schema Contract")

    @property
    def schema_contract_status_metric(self) -> Locator:
        """Validation status for the active schema contract."""
        return self.page.locator("[data-testid='stMetric']").filter(has_text="Contract status")

    @property
    def schema_semantics_apply_button(self) -> Locator:
        """Button that retains semantic labels and units with active data."""
        return self.page.get_by_role("button", name="Apply Labels and Units")

    @property
    def schema_semantics_success(self) -> Locator:
        """Confirmation that semantic metadata entered the data lifecycle."""
        return self.page.get_by_text(
            "Semantic labels and units are retained with the active dataset."
        )

    def validate_schema_contract(self) -> None:
        """Validate the inferred contract and wait for rendering."""
        self.schema_contract_validate_button.click()
        self.wait_for_streamlit()

    def apply_schema_semantics(self) -> None:
        """Apply the current labels/units and wait for the rerender."""
        self.schema_semantics_apply_button.click()
        self.wait_for_streamlit()

    # E2E: Data Visualization tab

    @property
    def viz_search_column_selectbox(self) -> Locator:
        """'Search in column' selectbox in Data Visualization."""
        return self._by_label("stSelectbox", "Search in column")

    @property
    def viz_search_term_input(self) -> Locator:
        """Search term text input in Data Visualization."""
        return self._by_label("stTextInput", "Search term").locator("input")

    @property
    def viz_display_columns_multiselect(self) -> Locator:
        """Columns included in the visible table and its CSV download."""
        return self._by_label("stMultiSelect", "Select columns to display")

    def assert_dataframe_visible(self) -> None:
        """Assert the visualization tab's heading and data table are visible."""
        heading = self.page.locator("h3").filter(has_text="Data Table")
        expect(heading).to_be_visible(timeout=30_000)
        panel = self.page.get_by_role("tabpanel", name="Data Visualization", exact=True)
        expect(panel.get_by_test_id("stDataFrame")).to_be_visible(timeout=30_000)

    # E2E: Operations History tab

    @property
    def history_no_ops_warning(self) -> Locator:
        """Warning when no operations have been performed."""
        return self.page.locator("[data-testid='stAlertContentWarning']").filter(
            has_text="No operations"
        )

    @property
    def history_total_metric(self) -> Locator:
        """'Total Operations' metric in history tab."""
        return self.page.get_by_text("Total Operations")

    def assert_history_empty(self) -> None:
        """Assert no operations have been recorded."""
        expect(self.history_no_ops_warning).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_history_has_operations(self, count: int | None = None) -> None:
        """Assert operations history is populated."""
        expect(self.history_total_metric).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if count is not None:
            expect(self.page.get_by_text(str(count))).to_be_visible(timeout=self.RENDER_TIMEOUT)

    # E2E: Common assertions

    def assert_success_message_visible(self) -> None:
        """Assert a success alert is visible somewhere on the page."""
        success = self.page.locator("[data-testid='stAlertContentSuccess']").first
        expect(success).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_error_message_visible(self) -> None:
        """Assert an error alert is visible somewhere on the page."""
        error = self.page.locator("[data-testid='stAlertContentError']").first
        expect(error).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_warning_message_visible(self) -> None:
        """Assert a warning alert is visible somewhere on the page."""
        warning = self.page.locator("[data-testid='stAlertContentWarning']").first
        expect(warning).to_be_visible(timeout=self.RENDER_TIMEOUT)
