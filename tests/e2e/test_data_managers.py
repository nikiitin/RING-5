"""E2E tests for the Data Managers page.

Covers page structure, Outlier Remover, Seeds Reducer, Mixer,
Preprocessor, baseline comparison, and Operations History using the ``tier1_page`` fixture
(18 rows of CSV data pre-loaded: 3 benchmarks x 3 configs x 2 seeds).

Columns: benchmark_name, config_description, seed, system.cpu.ipc,
         system.cpu.numCycles, simTicks, system.cpu.dcache.overall_miss_rate,
         system.cpu.committedInsts
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect

from tests.visual.pages.data_managers_page import DataManagersPage

pytestmark = pytest.mark.requires_browser

_E2E_TIMEOUT: int = 30_000


# Helpers — Streamlit widget interaction


def _select_dropdown_option(page: Page, selectbox: Locator, text: str) -> None:
    """Open a Streamlit selectbox and choose *text*, retrying missed clicks."""
    option = page.get_by_role("option", name=text, exact=True).first
    for attempt in range(3):
        selectbox.get_by_role("combobox").click()
        try:
            option.wait_for(state="visible", timeout=5_000)
            option.click(timeout=5_000)
        except PlaywrightTimeoutError:
            page.keyboard.press("Escape")
            if attempt == 2:
                raise
            page.wait_for_timeout(250)
            continue
        return


def _select_second_dropdown_option(page: Page, selectbox: Locator) -> None:
    """Choose the second available option, retrying a click lost to a rerun."""
    option = page.get_by_role("option").nth(1)
    for _ in range(3):
        selectbox.get_by_role("combobox").click()
        try:
            option.wait_for(state="visible", timeout=5_000)
            option.click(timeout=5_000)
        except PlaywrightTimeoutError:
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)
            continue
        return
    expect(option).to_be_visible(timeout=_E2E_TIMEOUT)


def _add_multiselect_option(page: Page, multiselect: Locator, text: str) -> None:
    """Add *text* to a Streamlit multiselect via type-to-filter + click.

    Robust across repeated calls: a prior selection can leave the dropdown open,
    so a blind re-click would toggle it shut and the option click would time out.
    Instead we focus the box, type to filter the options to the wanted one, and
    wait for that option before clicking.
    """
    multiselect.click()
    multiselect.locator("input").fill(text)
    option = page.get_by_role("option", name=text, exact=True)
    expect(option.first).to_be_visible(timeout=_E2E_TIMEOUT)
    option.first.click()
    page.wait_for_timeout(200)


# Page structure


@pytest.mark.xdist_group("e2e_data_managers_structure")
class TestDataManagersPageStructure:
    """Tier 1: Verify page layout with data loaded."""

    def test_page_loads_with_header(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.assert_page_header_visible()

    def test_all_tabs_visible(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.assert_tabs_visible()

    def test_summary_tab_can_be_selected(self, tier1_page: Page) -> None:
        """The Summary tab can be restored after another tab was active."""
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Summary")
        dm.assert_tab_active("Summary")

    def test_summary_tab_shows_rows_metric(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Summary")
        dm.assert_summary_has_rows(expected=18)

    def test_summary_tab_shows_columns_metric(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Summary")
        dm.assert_summary_has_columns()

    def test_data_visualization_tab_shows_dataframe(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Data Visualization")
        dm.assert_dataframe_visible()

    def test_no_data_warning_absent(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        expect(dm.no_data_warning).not_to_be_visible()


# Outlier Remover


@pytest.mark.xdist_group("e2e_data_managers_outlier")
class TestOutlierRemover:
    """Tier 1: Outlier Remover workflow (ordered tests, state accumulates)."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Outlier Remover")
        dm.assert_tab_active("Outlier Remover")
        expect(dm.outlier_column_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_select_column(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        _select_dropdown_option(tier1_page, dm.outlier_column_selectbox, "simTicks")
        dm.wait_for_streamlit()

    @pytest.mark.order(3)
    def test_03_apply_shows_metrics(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.apply_outlier_remover()
        dm.assert_outlier_shows_metrics()

    @pytest.mark.order(4)
    def test_04_confirm_applies_filter(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.confirm_outlier_remover()
        dm.assert_success_message_visible()


# Seeds Reducer


@pytest.mark.xdist_group("e2e_data_managers_seeds")
class TestSeedsReducer:
    """Tier 1: Seeds Reducer workflow."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Seeds Reducer")
        dm.assert_tab_active("Seeds Reducer")

    @pytest.mark.order(2)
    def test_02_reducer_widgets_visible(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.assert_reducer_ready()
        expect(dm.seeds_categorical_multiselect).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(3)
    def test_03_apply_reducer(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.apply_seeds_reducer()
        expect(dm.seeds_confirm_button).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(4)
    def test_04_confirm_reduces_rows(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.confirm_seeds_reducer()
        dm.assert_summary_has_rows(expected=3)


# Mixer


@pytest.mark.xdist_group("e2e_data_managers_mixer")
class TestMixer:
    """Tier 1: Column Mixer workflow."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Mixer")
        dm.assert_tab_active("Mixer")
        expect(dm.mixer_columns_multiselect).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_widgets_visible(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        expect(dm.mixer_new_name_input).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.mixer_preview_button).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(3)
    def test_03_preview_merge(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        _add_multiselect_option(tier1_page, dm.mixer_columns_multiselect, "system.cpu.ipc")
        _add_multiselect_option(tier1_page, dm.mixer_columns_multiselect, "simTicks")
        tier1_page.keyboard.press("Escape")
        dm.wait_for_streamlit()
        dm.mixer_new_name_input.fill("mixed_metric")
        dm.apply_mixer_preview()

    @pytest.mark.order(4)
    def test_04_confirm_merge(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.confirm_mixer()
        dm.assert_success_message_visible()


# Preprocessor


@pytest.mark.xdist_group("e2e_data_managers_preproc")
class TestPreprocessor:
    """Tier 1: Preprocessor workflow."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Preprocessor")
        dm.assert_tab_active("Preprocessor")
        expect(dm.preproc_src1_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_widgets_visible(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        expect(dm.preproc_operation_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.preproc_src2_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.preproc_preview_button).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(3)
    def test_03_preview_result(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        _select_dropdown_option(tier1_page, dm.preproc_src1_selectbox, "simTicks")
        dm.wait_for_streamlit()
        _select_dropdown_option(tier1_page, dm.preproc_src2_selectbox, "system.cpu.committedInsts")
        dm.wait_for_streamlit()
        dm.preproc_name_input.fill("ticks_per_inst")
        dm.apply_preprocessor_preview()

    @pytest.mark.order(4)
    def test_04_confirm_add_column(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.confirm_preprocessor()
        dm.assert_summary_has_columns(9)


# Baseline comparison


@pytest.mark.xdist_group("e2e_data_managers_comparison")
class TestRegressionComparison:
    """Tier 1: Compare two configurations without dropping alignment failures."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Compare")
        dm.assert_tab_active("Compare")
        expect(dm.comparison_group_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_comparison_preview(self, tier1_page: Page) -> None:
        # [test->req~ring5.analysis.regression-comparison~1]
        # [test->req~ring5.analysis.regression-annotations~1]
        # [test->req~ring5.automation.machine-readable-regression~1]
        dm = DataManagersPage(tier1_page)
        _select_dropdown_option(
            tier1_page,
            dm.comparison_group_selectbox,
            "config_description",
        )
        dm.wait_for_streamlit()
        _add_multiselect_option(tier1_page, dm.comparison_metrics_multiselect, "system.cpu.ipc")
        dm.wait_for_streamlit()
        _add_multiselect_option(tier1_page, dm.comparison_keys_multiselect, "benchmark_name")
        dm.wait_for_streamlit()
        _add_multiselect_option(tier1_page, dm.comparison_keys_multiselect, "seed")
        tier1_page.keyboard.press("Escape")
        dm.wait_for_streamlit()
        dm.apply_comparison()
        expect(dm.comparison_confirm_button).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.regression_plot).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.comparison_json_download_button).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.comparison_junit_download_button).to_be_visible(timeout=_E2E_TIMEOUT)


@pytest.mark.xdist_group("e2e_data_managers_statistics")
class TestStatisticalComparison:
    """Tier 1: Compare repeated samples for two configurations."""

    def test_statistical_preview(self, tier1_page: Page) -> None:
        # [test->req~ring5.analysis.statistical-comparison~1]
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Compare")
        _select_dropdown_option(
            tier1_page,
            dm.comparison_group_selectbox,
            "config_description",
        )
        dm.wait_for_streamlit()
        _select_dropdown_option(
            tier1_page,
            dm.comparison_method_selectbox,
            "Statistics",
        )
        dm.wait_for_streamlit()
        _add_multiselect_option(tier1_page, dm.comparison_metrics_multiselect, "system.cpu.ipc")
        dm.wait_for_streamlit()
        _add_multiselect_option(tier1_page, dm.comparison_keys_multiselect, "benchmark_name")
        tier1_page.keyboard.press("Escape")
        dm.wait_for_streamlit()
        dm.apply_comparison()
        expect(dm.comparison_confirm_button).to_be_visible(timeout=_E2E_TIMEOUT)


@pytest.mark.xdist_group("e2e_data_managers_workspace")
class TestNamedDatasetWorkspace:
    """Tier 1: Retain the active table without losing it on workspace reruns."""

    def test_retain_current_dataset(self, tier1_page: Page) -> None:
        # [test->req~ring5.data.multi-dataset-workspace~1]
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Workspace")
        dm.retain_current_dataset("tier1_results")
        expect(dm.workspace_dataset_metric_value).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_lineage_inspection_undo_and_redo(self, tier1_page: Page) -> None:
        # [test->req~ring5.data.lineage-undo-redo~1]
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Workspace")
        dm.retain_current_dataset("recoverable_results")

        dm.select_tab("Preprocessor")
        # Other randomly ordered workspace tests can leave a derived dataset
        # active. The preprocessor defaults are always numeric columns in the
        # active dataset, which is all this lineage test needs.
        _select_second_dropdown_option(tier1_page, dm.preproc_src2_selectbox)
        dm.wait_for_streamlit()
        dm.preproc_name_input.fill("lineage_ratio")
        dm.apply_preprocessor_preview()
        dm.confirm_preprocessor()

        dm.select_tab("Workspace")
        _select_dropdown_option(
            tier1_page,
            dm.workspace_dataset_selectbox,
            "recoverable_results",
        )
        dm.wait_for_streamlit()
        expect(dm.workspace_lineage_panel).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.workspace_undo_button).to_be_enabled()
        dm.undo_workspace_dataset()
        expect(dm.workspace_redo_button).to_be_enabled(timeout=_E2E_TIMEOUT)
        dm.redo_workspace_dataset()
        expect(dm.workspace_undo_button).to_be_enabled(timeout=_E2E_TIMEOUT)

    def test_save_and_reload_verified_dataset_snapshot(self, tier1_page: Page) -> None:
        # [test->req~ring5.data.dataset-snapshots~1]
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Workspace")
        dm.retain_current_dataset("snapshot_source")
        before_count = int(dm.workspace_dataset_metric_value.inner_text())

        dm.save_workspace_snapshot("tier1_reusable_snapshot")
        dm.load_workspace_snapshot("snapshot_restored")

        expect(dm.workspace_dataset_metric_value).to_have_text(
            str(before_count + 1),
            timeout=_E2E_TIMEOUT,
        )

    def test_join_cardinality_diagnostics_gate_output(self, tier1_page: Page) -> None:
        # [test->req~ring5.data.validated-joins~1]
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Workspace")
        dm.retain_current_dataset("join_left")
        dm.retain_current_dataset("join_right")
        before_count = int(dm.workspace_dataset_metric_value.inner_text())

        _select_dropdown_option(tier1_page, dm.workspace_operation_selectbox, "Join")
        dm.wait_for_streamlit()
        _select_dropdown_option(tier1_page, dm.workspace_join_left, "join_left")
        dm.wait_for_streamlit()
        _select_dropdown_option(tier1_page, dm.workspace_join_right, "join_right")
        dm.wait_for_streamlit()
        dm.workspace_join_output_input.fill("validated_join_output")
        _add_multiselect_option(tier1_page, dm.workspace_join_keys, "benchmark_name")
        dm.wait_for_streamlit()
        expect(dm.workspace_cardinality_metric).to_contain_text(
            "Conflict",
            timeout=_E2E_TIMEOUT,
        )
        expect(dm.workspace_join_button).to_be_disabled()

        _select_dropdown_option(
            tier1_page,
            dm.workspace_join_cardinality,
            "Many rows on both sides",
        )
        dm.wait_for_streamlit()
        expect(dm.workspace_cardinality_metric).to_contain_text("Valid", timeout=_E2E_TIMEOUT)
        expect(dm.workspace_join_button).to_be_enabled()
        dm.join_workspace_datasets()
        expect(dm.workspace_dataset_metric_value).to_have_text(
            str(before_count + 1),
            timeout=_E2E_TIMEOUT,
        )


@pytest.mark.xdist_group("e2e_data_managers_quality")
class TestDataQualityProfile:
    """Tier 1: Inspect quality measurements without changing the dataset."""

    def test_profile_dataset(self, tier1_page: Page) -> None:
        # [test->req~ring5.data.quality-profiler~1]
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Data Quality")
        dm.profile_data()
        expect(dm.quality_schema_metric).to_be_visible(timeout=_E2E_TIMEOUT)


@pytest.mark.xdist_group("e2e_data_managers_schema_contract")
class TestDatasetSchemaContract:
    """Tier 1: Infer, edit, and validate an explicit schema contract."""

    def test_validate_inferred_contract(self, tier1_page: Page) -> None:
        # [test->req~ring5.data.schema-contracts~1]
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Schema Contract")
        dm.validate_schema_contract()
        expect(dm.schema_contract_status_metric).to_contain_text(
            "Valid",
            timeout=_E2E_TIMEOUT,
        )

    def test_apply_semantic_metadata_from_human_first_editor(self, tier1_page: Page) -> None:
        # [test->req~ring5.data.semantic-units~1]
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Schema Contract")
        expect(dm.schema_semantics_apply_button).to_be_visible(timeout=_E2E_TIMEOUT)
        dm.apply_schema_semantics()
        expect(dm.schema_semantics_success).to_be_visible(timeout=_E2E_TIMEOUT)


# Operations History


@pytest.mark.xdist_group("e2e_data_managers_history")
class TestOperationsHistory:
    """Tier 1: Operations History after data management."""

    def test_history_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Operations History")
        dm.assert_tab_active("Operations History")

    def test_history_initially_empty(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.select_tab("Operations History")
        dm.assert_history_empty()
