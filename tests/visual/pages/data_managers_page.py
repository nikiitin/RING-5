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

from playwright.sync_api import Locator, Page, expect

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
        tab.click()
        self.wait_for_streamlit()

    def get_tab(self, tab_name: str) -> Locator:
        """Return the tab locator by name."""
        return self.page.get_by_role("tab", name=tab_name)

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

    def assert_summary_has_columns(self) -> None:
        """Assert Summary tab shows a column-count metric.

        Scopes to the ``st.metric`` card; a bare ``get_by_text("Columns")``
        matched ~23 elements on the page (strict-mode violation).
        """
        cols_metric = self.page.locator("[data-testid='stMetric']").filter(has_text="Columns")
        expect(cols_metric.first).to_be_visible(timeout=self.RENDER_TIMEOUT)

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
        """Click 'Confirm and Apply Seeds Reducer' and wait."""
        self.seeds_confirm_button.click()
        self.wait_for_streamlit()

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

    def apply_outlier_remover(self) -> None:
        """Click 'Apply Outlier Remover' and wait."""
        self.outlier_apply_button.click()
        self.wait_for_streamlit()

    def confirm_outlier_remover(self) -> None:
        """Click 'Confirm and Apply Outlier Remover' and wait."""
        self.outlier_confirm_button.click()
        self.wait_for_streamlit()

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
        self.wait_for_streamlit()

    def confirm_preprocessor(self) -> None:
        """Click 'Confirm and Add Column to Dataset' and wait."""
        self.preproc_confirm_button.click()
        self.wait_for_streamlit()

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

    def apply_mixer_preview(self) -> None:
        """Click 'Preview Merge' and wait."""
        self.mixer_preview_button.click()
        self.wait_for_streamlit()

    def confirm_mixer(self) -> None:
        """Click 'Confirm and Merge' and wait."""
        self.mixer_confirm_button.click()
        self.wait_for_streamlit()

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

    @property
    def comparison_apply_button(self) -> Locator:
        """Button that calculates the comparison preview."""
        return self.page.get_by_role("button", name="Compare", exact=True)

    @property
    def comparison_confirm_button(self) -> Locator:
        """Button that replaces the active data with the comparison result."""
        return self.page.get_by_role("button", name="Use Comparison Result")

    @property
    def regression_plot(self) -> Locator:
        """Accessible regression-outcome chart in the comparison preview."""
        return self.page.locator("[data-testid='stCustomComponentV1']:visible")

    def apply_comparison(self) -> None:
        """Calculate the comparison and wait for the preview."""
        self.comparison_apply_button.click()
        self.wait_for_streamlit()

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

    def retain_current_dataset(self, name: str) -> None:
        """Retain the active dataset under ``name`` and wait for rerendering."""
        self.workspace_name_input.fill(name)
        self.workspace_retain_button.click()
        self.wait_for_streamlit()

    def undo_workspace_dataset(self) -> None:
        """Undo one named-dataset revision and wait for the rerender."""
        self.workspace_undo_button.click()
        self.wait_for_streamlit()

    def redo_workspace_dataset(self) -> None:
        """Redo one named-dataset revision and wait for the rerender."""
        self.workspace_redo_button.click()
        self.wait_for_streamlit()

    # E2E: Data quality

    @property
    def quality_profile_button(self) -> Locator:
        """Button that calculates the data-quality report."""
        return self.page.get_by_role("button", name="Profile Dataset")

    @property
    def quality_schema_metric(self) -> Locator:
        """Schema-violation summary metric."""
        return self.page.locator("[data-testid='stMetric']").filter(has_text="Schema violations")

    def profile_data(self) -> None:
        """Calculate the data-quality report and wait for rendering."""
        self.quality_profile_button.click()
        self.wait_for_streamlit()

    # E2E: Dataset schema contract

    @property
    def schema_contract_validate_button(self) -> Locator:
        """Button that validates the editable schema contract."""
        return self.page.get_by_role("button", name="Validate Schema Contract")

    @property
    def schema_contract_status_metric(self) -> Locator:
        """Validation status for the active schema contract."""
        return self.page.locator("[data-testid='stMetric']").filter(has_text="Contract status")

    def validate_schema_contract(self) -> None:
        """Validate the inferred contract and wait for rendering."""
        self.schema_contract_validate_button.click()
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

    def assert_dataframe_visible(self) -> None:
        """Assert a dataframe is rendered and visible.

        The Data Visualization tab renders a ``### Data Table (…)``
        heading immediately before ``st.dataframe()``.  Checking for
        this heading confirms the tab fragment has finished rendering.
        """
        heading = self.page.locator("h3").filter(has_text="Data Table")
        expect(heading).to_be_visible(timeout=30_000)

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
