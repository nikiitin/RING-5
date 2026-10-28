"""E2E tests for the Data Managers page.

Covers page structure, Outlier Remover, Seeds Reducer, Mixer,
Preprocessor, baseline comparison, and Operations History using the ``tier1_page`` fixture
(18 rows of CSV data pre-loaded: 3 benchmarks x 3 configs x 2 seeds).

Columns: benchmark_name, config_description, seed, system.cpu.ipc,
         system.cpu.numCycles, simTicks, system.cpu.dcache.overall_miss_rate,
         system.cpu.committedInsts
"""

from __future__ import annotations

from pathlib import Path
from statistics import quantiles

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.plot_interactions_page import PlotInteractionsPage

pytestmark = pytest.mark.requires_browser

_E2E_TIMEOUT: int = 30_000


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
    """Remove a known extreme sample through one ordered, grouped IQR workflow."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page, tmp_path: Path) -> None:
        source = tmp_path / "grouped-outlier.csv"
        source.write_text(
            "benchmark_name,config_description,seed,simTicks\n"
            "alpha,baseline,0,10\nalpha,baseline,1,11\nalpha,baseline,2,12\n"
            "alpha,baseline,3,13\nalpha,baseline,4,14\nalpha,baseline,5,1000\n",
            encoding="utf-8",
        )
        uploader = DataSourcePage(tier1_page)
        uploader.navigate()
        uploader.upload_csv(source)
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Outlier Remover")
        dm.assert_tab_active("Outlier Remover")
        expect(dm.outlier_column_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_select_column(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm._open_and_select(dm.outlier_column_selectbox, "simTicks")
        dm.wait_for_streamlit()

    @pytest.mark.order(3)
    def test_03_apply_shows_metrics(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.apply_outlier_remover()
        dm.assert_outlier_shows_metrics()

    @pytest.mark.order(4)
    def test_04_confirm_applies_filter(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        interactions = PlotInteractionsPage(tier1_page)
        before = interactions.download_workspace_rows()
        assert [float(row["simTicks"]) for row in before] == [10, 11, 12, 13, 14, 1000]
        assert {(row["benchmark_name"], row["config_description"]) for row in before} == {
            ("alpha", "baseline")
        }
        q1, _, q3 = quantiles([float(row["simTicks"]) for row in before], n=4, method="inclusive")
        lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        expected = [row for row in before if lower <= float(row["simTicks"]) <= upper]
        assert len(expected) == 5
        dm.select_tab("Outlier Remover")
        dm.confirm_outlier_remover()
        assert interactions.download_workspace_rows() == expected
        dm.assert_summary_has_rows(expected=5)


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
        dm.add_mixer_column("system.cpu.ipc")
        dm.add_mixer_column("simTicks")
        dm._open_and_select(dm.mixer_operation_selectbox, "Sum")
        dm.mixer_new_name_input.fill("mixed_metric")
        dm.apply_mixer_preview()

    @pytest.mark.order(4)
    def test_04_confirm_merge(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        interactions = PlotInteractionsPage(tier1_page)
        before = interactions.download_workspace_rows()
        assert len(before) == 18
        assert all("mixed_metric" not in row for row in before)
        dm.select_tab("Mixer")
        dm.confirm_mixer()
        after = interactions.download_workspace_rows()
        assert len(after) == len(before)
        for source, merged in zip(before, after, strict=True):
            assert set(merged) == set(source) | {"mixed_metric"}
            assert {name: merged[name] for name in source} == source
            assert float(merged["mixed_metric"]) == (
                float(source["system.cpu.ipc"]) + float(source["simTicks"])
            )
        dm.assert_summary_has_rows(expected=18)
        dm.assert_summary_has_columns(expected=9)


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
        dm._open_and_select(dm.preproc_src1_selectbox, "simTicks")
        dm.wait_for_streamlit()
        dm._open_and_select(dm.preproc_src2_selectbox, "system.cpu.committedInsts")
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
        dm._open_and_select(
            dm.comparison_group_selectbox,
            "config_description",
        )
        dm.wait_for_streamlit()
        dm.add_comparison_metric("system.cpu.ipc")
        dm.wait_for_streamlit()
        dm.add_comparison_key("benchmark_name")
        dm.wait_for_streamlit()
        dm.add_comparison_key("seed")
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
        dm._open_and_select(
            dm.comparison_group_selectbox,
            "config_description",
        )
        dm.wait_for_streamlit()
        dm._open_and_select(
            dm.comparison_method_selectbox,
            "Statistics",
        )
        dm.wait_for_streamlit()
        dm.add_comparison_metric("system.cpu.ipc")
        dm.wait_for_streamlit()
        dm.add_comparison_key("benchmark_name")
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
        # A dataset name must not be mistaken for its published Active flag.
        dm.retain_current_dataset("Yes")
        expect(dm.workspace_dataset_metric_value).to_be_visible(timeout=_E2E_TIMEOUT)

    def test_lineage_inspection_undo_and_redo(self, tier1_page: Page, e2e_csv_path: Path) -> None:
        # [test->req~ring5.data.lineage-undo-redo~1]
        source = DataSourcePage(tier1_page)
        source.navigate()
        source.upload_csv(e2e_csv_path)
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        original = PlotInteractionsPage(tier1_page).download_workspace_rows()
        assert len(original) == 18
        assert all("system.cpu.committedInsts" in row for row in original)
        dm.select_tab("Workspace")
        dm.retain_current_dataset("recoverable_results")

        dm.select_tab("Preprocessor")
        dm._open_and_select(dm.preproc_src2_selectbox, "system.cpu.committedInsts")
        dm.wait_for_streamlit()
        dm.preproc_name_input.fill("lineage_ratio")
        dm.apply_preprocessor_preview()
        dm.confirm_preprocessor()

        dm.select_tab("Workspace")
        dm._open_and_select(
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

        dm._open_and_select(dm.workspace_operation_selectbox, "Join")
        dm.wait_for_streamlit()
        dm._open_and_select(dm.workspace_join_left, "join_left")
        dm.wait_for_streamlit()
        dm._open_and_select(dm.workspace_join_right, "join_right")
        dm.wait_for_streamlit()
        dm.workspace_join_output_input.fill("validated_join_output")
        dm.add_workspace_join_key("benchmark_name")
        dm.wait_for_streamlit()
        expect(dm.workspace_cardinality_metric).to_contain_text(
            "Conflict",
            timeout=_E2E_TIMEOUT,
        )
        expect(dm.workspace_join_button).to_be_disabled()

        dm._open_and_select(
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
        interactions = PlotInteractionsPage(tier1_page)
        before = interactions.download_workspace_rows()
        assert len(before) == 18
        dm.select_tab("Schema Contract")
        dm.edit_schema_rule("system.cpu.ipc", "Semantic label", "Instructions per cycle")
        dm.edit_schema_rule("system.cpu.ipc", "Unit", "ratio")
        dm.apply_schema_semantics()
        expect(
            dm.schema_semantics_row("system.cpu.ipc").get_by_role("gridcell", include_hidden=True)
        ).to_have_text(
            ["system.cpu.ipc", "Instructions per cycle", "ratio", "Instructions per cycle (ratio)"],
            timeout=_E2E_TIMEOUT,
        )
        expect(dm.schema_unit_target_selectbox).to_contain_text("currently ratio")
        assert interactions.download_workspace_rows() == before


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
