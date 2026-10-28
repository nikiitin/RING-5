"""Verify imported, transformed and recovered tables through ordinary browser controls."""

from __future__ import annotations

import csv
import json
import math
import re
import tempfile
from io import StringIO
from pathlib import Path
from xml.etree import ElementTree

import pytest
from openpyxl import Workbook
from playwright.sync_api import Download, Page, expect

from tests.e2e.conftest import E2E_TIMEOUT
from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser

_SMALL_CSV = "label,value\nold,7\nkept,9\n"
_REPEATED_CSV = (
    "workload,random_seed,a,b\n" "first,0,10,2\nfirst,1,14,4\n" "second,0,20,5\nsecond,1,24,6\n"
)
_LEFT_CSV = "label,value\na,10\na,12\nb,20\n"
_RIGHT_CSV = "label,value\na,100\nb,200\nc,300\n"


def _csv_rows(payload: str) -> list[dict[str, str]]:
    """Decode a real CSV download without depending on application serializers."""
    return list(csv.DictReader(StringIO(payload)))


def _download_rows(download: Download) -> list[dict[str, str]]:
    """Read the file transferred by the browser."""
    return _csv_rows(download.path().read_text(encoding="utf-8-sig"))


def _active_rows(page: Page) -> list[dict[str, str]]:
    """Download the active workspace through Data Managers."""
    managers = DataManagersPage(page)
    managers.navigate()
    return _download_rows(managers.download_current_view())


def _load_csv(page: Page, directory: Path, name: str, payload: str) -> DataSourcePage:
    """Upload and explicitly accept a small table through the browser."""
    path = directory / name
    path.write_text(payload, encoding="utf-8")
    source = DataSourcePage(page)
    source.navigate()
    source.upload_csv(path)
    return source


def _fresh_csv(page: Page, directory: Path, payload: str) -> DataManagersPage:
    """Start one independent scenario with a reviewed synthetic input."""
    source = DataSourcePage(page)
    source.reset_all()
    _load_csv(page, directory, "input.csv", payload)
    managers = DataManagersPage(page)
    managers.navigate()
    return managers


def _assert_clean(page: Page) -> None:
    """Reject visible application failures after a successful workflow."""
    expect(page.get_by_test_id("stException")).to_have_count(0)
    expect(page.get_by_test_id("stAlertContentError")).to_have_count(0)


@pytest.mark.xdist_group("e2e_tabular_import_journeys")
class TestTabularImportJourneys:
    """Import formats share the same explicit review and workspace boundary."""

    @pytest.mark.parametrize("file_format", ["json", "xlsx"])
    def test_json_and_excel_are_reviewed_before_loading_exact_values(
        self, tier0_page: Page, tmp_path: Path, file_format: str
    ) -> None:
        # [test->req~ring5.ingestion.browser-upload~1]
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        expected = [{"benchmark": "mcf", "ipc": "1.25"}, {"benchmark": "lbm", "ipc": "2.5"}]
        path = tmp_path / f"measurements.{file_format}"
        if file_format == "json":
            path.write_text(
                json.dumps([{"benchmark": "mcf", "ipc": 1.25}, {"benchmark": "lbm", "ipc": 2.5}]),
                encoding="utf-8",
            )
        else:
            workbook = Workbook()
            sheet = workbook.active
            assert sheet is not None
            sheet.title = "Measurements"
            sheet.append(["benchmark", "ipc"])
            sheet.append(["mcf", 1.25])
            sheet.append(["lbm", 2.5])
            workbook.save(path)
            workbook.close()

        source = DataSourcePage(page)
        source.navigate()
        source.upload_for_review(path)
        expect(source.import_review_header).to_be_visible(timeout=E2E_TIMEOUT)
        expect(source.import_accepted_metric.get_by_test_id("stMetricValue")).to_have_text("2")
        expect(source.import_rejected_metric.get_by_test_id("stMetricValue")).to_have_text("0")
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)

        source.navigate()
        source.upload_for_review(path)
        expect(source.import_review_header).to_be_visible(timeout=E2E_TIMEOUT)
        source.load_accepted_import_button.click()
        expect(source.loaded_review_success).to_be_visible(timeout=E2E_TIMEOUT)
        assert _active_rows(page) == expected
        _assert_clean(page)

    def test_rejected_rows_are_explicit_and_an_empty_result_cannot_replace_data(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.ingestion.import-preview~1]
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        path = tmp_path / "partly-invalid.csv"
        path.write_text("label,value\naccepted,11\nbroken,22,extra\nkept,33\n", encoding="utf-8")
        source = DataSourcePage(page)
        source.navigate()
        source.select_csv_mode()
        source.browser_upload_input.set_input_files(str(path))
        expect(source.import_accepted_metric.get_by_test_id("stMetricValue")).to_have_text("2")
        expect(source.import_rejected_metric.get_by_test_id("stMetricValue")).to_have_text("1")
        expect(page.get_by_text("1 row(s) will not be loaded.", exact=False)).to_be_visible()
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)
        source.navigate()
        source.upload_for_review(path)
        source.load_accepted_import_button.click()
        expect(source.loaded_review_success).to_be_visible(timeout=E2E_TIMEOUT)
        accepted = [{"label": "accepted", "value": "11"}, {"label": "kept", "value": "33"}]
        assert _active_rows(page) == accepted

        all_invalid = tmp_path / "all-invalid.csv"
        all_invalid.write_text("label,value\nwrong,1,extra\n", encoding="utf-8")
        source.navigate()
        source.select_csv_mode()
        source.browser_upload_input.set_input_files(str(all_invalid))
        expect(source.import_accepted_metric.get_by_test_id("stMetricValue")).to_have_text("0")
        expect(source.import_rejected_metric.get_by_test_id("stMetricValue")).to_have_text("1")
        expect(source.load_accepted_import_button).to_be_disabled()
        assert _active_rows(page) == accepted
        _assert_clean(page)

    def test_malformed_json_cannot_replace_an_existing_workspace(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        malformed = tmp_path / "invalid.json"
        malformed.write_text('{"unfinished":', encoding="utf-8")
        source = DataSourcePage(page)
        source.navigate()
        source.select_csv_mode()
        source.browser_upload_input.set_input_files(str(malformed))
        expect(source.upload_validation_error).to_be_visible(timeout=E2E_TIMEOUT)
        expect(source.load_accepted_import_button).to_have_count(0)
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)
        expect(page.get_by_test_id("stException")).to_have_count(0)


@pytest.mark.xdist_group("e2e_parser_evidence")
@pytest.mark.timeout(240)
class TestParserEvidence:
    """A real parser preview is read-only; consumed work has exact source values."""

    def test_playground_parse_and_repeated_attempt_preserve_their_boundaries(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.ingestion.parser-playground~1]
        # [test->req~ring5.ingestion.session-background-parse~1]
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        source = DataSourcePage(page)
        source.navigate()
        source.select_recent_mode()
        recent_count = page.get_by_role("button", name="Review & Load", exact=True).count()
        source.ensure_parse_mode()
        stats_root = Path(__file__).parent / "fixtures" / "tutorial_stats"
        source.fill_stats_path(str(stats_root))
        source.fill_stats_pattern("stats.txt")
        source.scan_and_wait(timeout=E2E_TIMEOUT)
        source.assert_scan_success()
        source.add_manual_variable("system.cpu.ipc", "scalar")

        source.test_parser_configuration_button.click()
        dialog = source.dialog_overlay
        expect(dialog.get_by_text("Ready for a full parse.", exact=True)).to_be_visible(
            timeout=E2E_TIMEOUT
        )
        for label in ("Matching files", "Files tested"):
            metric = dialog.get_by_test_id("stMetric").filter(has_text=label)
            expect(metric.get_by_test_id("stMetricValue")).to_have_text("2")
        preview = _download_rows(source.download_playground_sample())
        assert sorted(float(row["simTicks"]) for row in preview) == [123.0, 246.0]
        assert sorted(float(row["system.cpu.ipc"]) for row in preview) == [1.5, 2.5]
        source.close_dialog()
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)
        source.navigate()
        source.select_recent_mode()
        expect(page.get_by_role("button", name="Review & Load", exact=True)).to_have_count(
            recent_count
        )

        source.ensure_parse_mode()
        source.parse_and_wait(timeout=E2E_TIMEOUT)
        first_id = source.get_parse_completion_id()
        source.assert_data_loaded(row_count=2)
        parsed = _active_rows(page)
        assert len(parsed) == 2
        assert {(float(row["simTicks"]), float(row["system.cpu.ipc"])) for row in parsed} == {
            (123.0, 1.5),
            (246.0, 2.5),
        }

        source.navigate()
        source.ensure_parse_mode()
        source.parse_and_wait(timeout=E2E_TIMEOUT)
        assert source.get_parse_completion_id() != first_id
        expect(source.parse_completion_notice).to_contain_text("Reused parsed CSV from Recent")
        assert _active_rows(page) == parsed
        _assert_clean(page)


@pytest.mark.xdist_group("e2e_manager_data_results")
class TestManagerDataResults:
    """Manager confirmations change exact data; previews preserve the active input."""

    def test_arithmetic_preview_invalidation_numeric_and_configuration_mixing(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.data.preview-confirm~1]
        # [test->req~ring5.data.arithmetic~1]
        # [test->req~ring5.data.numeric-mixer~1]
        # [test->req~ring5.data.configuration-mixer~1]
        page = tier0_page
        managers = _fresh_csv(page, tmp_path, _REPEATED_CSV)
        managers.select_tab("Preprocessor")
        managers._open_and_select(managers.preproc_src1_selectbox, "a")
        managers._open_and_select(managers.preproc_operation_selectbox, "Division")
        managers._open_and_select(managers.preproc_src2_selectbox, "b")
        managers.preproc_name_input.fill("ratio")
        managers.apply_preprocessor_preview()
        expect(managers.preproc_confirm_button).to_be_visible()
        assert _active_rows(page) == _csv_rows(_REPEATED_CSV)
        managers.select_tab("Preprocessor")
        managers.preproc_name_input.fill("reviewed_ratio")
        managers.preproc_name_input.press("Tab")
        managers.wait_for_streamlit(expect_rerun=True)
        expect(managers.preproc_confirm_button).to_have_count(0)
        managers.apply_preprocessor_preview()
        managers.confirm_preprocessor()
        arithmetic = _active_rows(page)
        assert [float(row["reviewed_ratio"]) for row in arithmetic] == [5.0, 3.5, 4.0, 4.0]
        assert all("ratio" not in row for row in arithmetic)
        assert [
            {key: row[key] for key in ("workload", "random_seed", "a", "b")} for row in arithmetic
        ] == _csv_rows(_REPEATED_CSV)

        managers.select_tab("Mixer")
        managers.add_mixer_column("a")
        managers.add_mixer_column("b")
        managers._open_and_select(managers.mixer_operation_selectbox, "Sum")
        managers.mixer_new_name_input.fill("total")
        managers.apply_mixer_preview()
        expect(managers.mixer_confirm_button).to_be_visible()
        assert _active_rows(page) == arithmetic
        managers.select_tab("Mixer")
        managers.confirm_mixer()
        numeric = _active_rows(page)
        assert [float(row["total"]) for row in numeric] == [12.0, 18.0, 25.0, 30.0]

        managers.select_tab("Mixer")
        managers.mixer_mode_control.get_by_role("radio", name="Configuration Merge").click()
        managers.wait_for_streamlit(expect_rerun=True)
        managers.clear_multiselect(managers.mixer_columns_multiselect)
        managers.add_mixer_column("workload")
        managers.add_mixer_column("random_seed")
        managers.mixer_separator_input.fill("/")
        managers.mixer_new_name_input.fill("run")
        managers.apply_mixer_preview()
        managers.confirm_mixer()
        mixed = _active_rows(page)
        assert [row["run"] for row in mixed] == ["first/0", "first/1", "second/0", "second/1"]
        assert [float(row["total"]) for row in mixed] == [12.0, 18.0, 25.0, 30.0]
        managers.select_tab("Operations History")
        operations = page.get_by_test_id("stMetric").filter(has_text="Total Operations")
        expect(operations.get_by_test_id("stMetricValue")).to_have_text("3")
        _assert_clean(page)

    def test_seed_reduction_preserves_group_means_and_sample_standard_deviation(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.data.seed-reduction~1]
        page = tier0_page
        managers = _fresh_csv(page, tmp_path, _REPEATED_CSV)
        managers.select_tab("Seeds Reducer")
        managers._open_and_select(managers.reducer_target_selectbox, "random_seed")
        managers.apply_seeds_reducer()
        expect(managers.seeds_confirm_button).to_be_visible()
        assert _active_rows(page) == _csv_rows(_REPEATED_CSV)
        managers.select_tab("Seeds Reducer")
        managers.confirm_seeds_reducer()
        rows = {row["workload"]: row for row in _active_rows(page)}
        assert set(rows) == {"first", "second"}
        assert float(rows["first"]["a"]) == 12.0
        assert float(rows["second"]["a"]) == 22.0
        assert float(rows["first"]["b"]) == 3.0
        assert float(rows["second"]["b"]) == 5.5
        assert float(rows["first"]["a.sd"]) == pytest.approx(math.sqrt(8))
        assert float(rows["second"]["a.sd"]) == pytest.approx(math.sqrt(8))
        assert all("random_seed" not in row for row in rows.values())
        _assert_clean(page)

    def test_outlier_preview_then_confirmation_removes_only_the_extreme_row(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.data.outlier-removal~1]
        page = tier0_page
        payload = "workload,run_id,value\n" + "".join(
            f"same,{index},{value}\n" for index, value in enumerate([10, 11, 12, 13, 14, 15, 1000])
        )
        managers = _fresh_csv(page, tmp_path, payload)
        managers.select_tab("Outlier Remover")
        managers.select_outlier_column("value")
        managers.apply_outlier_remover()
        expect(managers.outlier_confirm_button).to_be_visible()
        assert _active_rows(page) == _csv_rows(payload)
        managers.select_tab("Outlier Remover")
        managers.confirm_outlier_remover()
        assert _active_rows(page) == _csv_rows(payload)[:6]
        _assert_clean(page)


@pytest.mark.xdist_group("e2e_data_inspection_results")
class TestDataInspectionResults:
    """Read-only table exploration and profiling expose their actual measurements."""

    def test_filtered_view_download_has_exact_rows_and_selected_columns(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.data.table-view~1]
        page = tier0_page
        payload = "benchmark,ipc,note\nmcf,1.5,first\nlbm,2.0,second\nmcf,2.5,third\n"
        managers = _fresh_csv(page, tmp_path, payload)
        managers.select_tab("Data Visualization")
        managers._open_and_select(managers.viz_search_column_selectbox, "benchmark")
        managers.viz_search_term_input.fill("mcf")
        managers.viz_search_term_input.press("Tab")
        managers.wait_for_streamlit(expect_rerun=True)
        for column in ("benchmark", "ipc"):
            managers._open_and_select(
                managers.viz_display_columns_multiselect, column, multiple=True
            )
        assert _download_rows(managers.download_current_view()) == [
            {"benchmark": "mcf", "ipc": "1.5"},
            {"benchmark": "mcf", "ipc": "2.5"},
        ]
        managers.viz_search_term_input.fill("")
        managers.viz_search_term_input.press("Tab")
        managers.wait_for_streamlit(expect_rerun=True)
        managers.clear_multiselect(managers.viz_display_columns_multiselect)
        rows = _active_rows(page)
        assert [row["benchmark"] for row in rows] == ["mcf", "lbm", "mcf"]
        assert [float(row["ipc"]) for row in rows] == [1.5, 2.0, 2.5]
        assert [row["note"] for row in rows] == ["first", "second", "third"]
        _assert_clean(page)

    def test_quality_profile_download_counts_missing_and_duplicate_data_without_mutation(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.data.quality-profiler~1]
        page = tier0_page
        payload = "label,value,note\na,10,x\na,10,x\nb,,\nc,100,x\n"
        managers = _fresh_csv(page, tmp_path, payload)
        before = _active_rows(page)
        managers.select_tab("Data Quality")
        managers.profile_data()
        for label, value in (("Missing cells", "2"), ("Duplicate rows", "1")):
            metric = page.get_by_test_id("stMetric").filter(has_text=label)
            expect(metric.get_by_test_id("stMetricValue")).to_have_text(value)
        profile = {row["name"]: row for row in _download_rows(managers.download_quality_profile())}
        assert set(profile) == {"label", "value", "note"}
        assert profile["value"]["missing"] == "1"
        assert profile["value"]["non_null"] == "3"
        assert profile["note"]["missing"] == "1"
        assert profile["label"]["missing"] == "0"
        assert _active_rows(page) == before
        _assert_clean(page)


@pytest.mark.xdist_group("e2e_named_workspace_results")
class TestNamedWorkspaceResults:
    """Compose named sources, recover exact revisions, and reload a verified snapshot."""

    @pytest.fixture(scope="class")
    @classmethod
    def workspace(cls, tier0_page: Page, tmp_path_factory: pytest.TempPathFactory) -> Page:
        """Retain two distinct tables without overwriting the first named source."""
        directory = tmp_path_factory.mktemp("named-workspace")
        managers = _fresh_csv(tier0_page, directory, _LEFT_CSV)
        managers.select_tab("Workspace")
        managers.retain_current_dataset("left_source")
        # Loading replaces the active named table: retain its independent copy first.
        managers.retain_current_dataset("right_source")
        _load_csv(tier0_page, directory, "right.csv", _RIGHT_CSV)
        assert _active_rows(tier0_page) == _csv_rows(_RIGHT_CSV)
        return tier0_page

    @pytest.mark.order(1)
    def test_append_creates_an_independent_table_and_keeps_both_sources(
        self, workspace: Page
    ) -> None:
        # [test->req~ring5.data.multi-dataset-workspace~1]
        managers = DataManagersPage(workspace)
        managers.select_tab("Workspace")
        managers._open_and_select(managers.workspace_operation_selectbox, "Append")
        managers.workspace_append_name_input.fill("all_rows")
        managers.workspace_append_button.click()
        managers.wait_for_streamlit(expect_rerun=True)
        assert _active_rows(workspace) == _csv_rows(_LEFT_CSV) + _csv_rows(_RIGHT_CSV)
        managers.activate_workspace_dataset("left_source")
        assert _active_rows(workspace) == _csv_rows(_LEFT_CSV)
        managers.activate_workspace_dataset("right_source")
        assert _active_rows(workspace) == _csv_rows(_RIGHT_CSV)
        _assert_clean(workspace)

    @pytest.mark.order(2)
    def test_join_conflict_blocks_publication_and_the_declared_relationship_is_exact(
        self, workspace: Page
    ) -> None:
        # [test->req~ring5.data.validated-joins~1]
        managers = DataManagersPage(workspace)
        managers.select_tab("Workspace")
        managers._open_and_select(managers.workspace_operation_selectbox, "Join")
        managers._open_and_select(managers.workspace_join_left, "left_source")
        managers._open_and_select(managers.workspace_join_right, "right_source")
        managers.add_workspace_join_key("label")
        managers._open_and_select(managers.workspace_join_mode, "outer")
        managers.workspace_join_output_input.fill("paired")
        managers.workspace_join_output_input.press("Tab")
        managers.wait_for_streamlit(expect_rerun=True)
        expect(managers.workspace_cardinality_metric).to_contain_text("Conflict")
        expect(managers.workspace_join_button).to_be_disabled()
        expect(managers.workspace_dataset_metric_value).to_have_text("3")
        managers._open_and_select(
            managers.workspace_join_cardinality, "Many left rows to one right row"
        )
        expect(managers.workspace_cardinality_metric).to_contain_text("Valid")
        managers.join_workspace_datasets()
        joined = _active_rows(workspace)
        assert [
            (
                row["label"],
                float(row["value_left"]) if row["value_left"] else None,
                float(row["value_right"]),
            )
            for row in joined
        ] == [("a", 10.0, 100.0), ("a", 12.0, 100.0), ("b", 20.0, 200.0), ("c", None, 300.0)]
        for name, expected in (("left_source", _LEFT_CSV), ("right_source", _RIGHT_CSV)):
            managers.activate_workspace_dataset(name)
            assert _active_rows(workspace) == _csv_rows(expected)
        managers.activate_workspace_dataset("paired")
        _assert_clean(workspace)

    @pytest.mark.order(3)
    def test_undo_redo_revision_restore_and_snapshot_preserve_exact_contents(
        self, workspace: Page
    ) -> None:
        # [test->req~ring5.data.lineage-undo-redo~1]
        # [test->req~ring5.data.dataset-snapshots~1]
        managers = DataManagersPage(workspace)
        original = _active_rows(workspace)
        managers.select_tab("Workspace")
        original_revision = managers.workspace_revision_selectbox.get_by_role(
            "combobox"
        ).input_value()
        managers.select_tab("Preprocessor")
        managers._open_and_select(managers.preproc_src1_selectbox, "value_left")
        managers._open_and_select(managers.preproc_operation_selectbox, "Sum")
        managers._open_and_select(managers.preproc_src2_selectbox, "value_right")
        managers.preproc_name_input.fill("combined")
        managers.apply_preprocessor_preview()
        managers.confirm_preprocessor()
        changed = _active_rows(workspace)
        assert [float(row["combined"]) if row["combined"] else None for row in changed] == [
            110.0,
            112.0,
            220.0,
            None,
        ]
        managers.select_tab("Workspace")
        managers.undo_workspace_dataset()
        assert _active_rows(workspace) == original
        managers.select_tab("Workspace")
        managers.redo_workspace_dataset()
        assert _active_rows(workspace) == changed
        managers.select_tab("Workspace")
        managers._open_and_select(managers.workspace_revision_selectbox, original_revision)
        expect(managers.workspace_restore_button).to_be_enabled()
        managers.workspace_restore_button.click()
        managers.wait_for_streamlit(expect_rerun=True)
        assert _active_rows(workspace) == original

        managers.select_tab("Workspace")
        managers._open_and_select(managers.workspace_snapshot_source_selectbox, "paired")
        managers.save_workspace_snapshot("exact_pairing")
        managers.load_workspace_snapshot("pairing_reloaded")
        managers.activate_workspace_dataset("pairing_reloaded")
        assert _active_rows(workspace) == original
        managers.select_tab("Workspace")
        managers._open_and_select(managers.workspace_dataset_selectbox, "paired")
        managers.workspace_remove_button.click()
        managers.wait_for_streamlit(expect_rerun=True)
        expect(managers.workspace_dataset_metric_value).to_have_text("4")
        managers.activate_workspace_dataset("left_source")
        assert _active_rows(workspace) == _csv_rows(_LEFT_CSV)
        managers.activate_workspace_dataset("pairing_reloaded")
        assert _active_rows(workspace) == original
        _assert_clean(workspace)


@pytest.mark.xdist_group("e2e_comparison_artifacts")
class TestComparisonArtifacts:
    """Browser downloads carry the same comparison evidence the workspace confirms."""

    def test_threshold_results_download_as_exact_csv_json_junit_and_confirm(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.analysis.regression-comparison~1]
        # [test->req~ring5.automation.machine-readable-regression~1]
        page = tier0_page
        payload = (
            "benchmark,configuration,ipc\n"
            "fast,baseline,10\nslow,baseline,10\nsame,baseline,10\nmissing,baseline,5\n"
            "fast,candidate,12\nslow,candidate,8\nsame,candidate,10\n"
        )
        managers = _fresh_csv(page, tmp_path, payload)
        managers.select_tab("Compare")
        managers._open_and_select(managers.comparison_group_selectbox, "configuration")
        managers.add_comparison_metric("ipc")
        managers.add_comparison_key("benchmark")
        managers.apply_comparison()
        expect(managers.comparison_confirm_button).to_be_visible()
        comparison = _download_rows(managers.download_comparison("csv"))
        outcomes = {row["benchmark"]: row["outcome"] for row in comparison}
        assert outcomes == {
            "fast": "improvement",
            "slow": "regression",
            "same": "unchanged",
            "missing": "missing_candidate",
        }
        by_name = {row["benchmark"]: row for row in comparison}
        assert float(by_name["fast"]["percentage_change"]) == 20.0
        assert float(by_name["slow"]["percentage_change"]) == -20.0
        assert by_name["missing"]["candidate_value"] == ""
        document = json.loads(managers.download_comparison("json").path().read_text())
        assert document["format"] == "ring5.regression-results"
        assert document["summary"]["total"] == 4
        assert document["summary"]["failures"] == 1
        assert document["summary"]["incomplete"] == 1
        assert {row["keys"]["benchmark"]: row["outcome"] for row in document["results"]} == outcomes
        junit = ElementTree.parse(managers.download_comparison("junit").path()).getroot()
        assert {
            name: junit.attrib[name] for name in ("tests", "failures", "errors", "skipped")
        } == {"tests": "4", "failures": "1", "errors": "0", "skipped": "1"}
        assert len(junit.findall("testcase/failure")) == 1
        assert len(junit.findall("testcase/skipped")) == 1
        assert _active_rows(page) == _csv_rows(payload)
        managers.select_tab("Compare")
        managers.comparison_confirm_button.click()
        managers.wait_for_streamlit(expect_rerun=True)
        assert _active_rows(page) == comparison
        _assert_clean(page)

    def test_statistical_download_preserves_sample_counts_means_and_warnings(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.analysis.statistical-comparison~1]
        page = tier0_page
        payload = (
            "benchmark,configuration,ipc\n"
            "one,baseline,10\none,baseline,12\none,baseline,14\n"
            "one,candidate,12\none,candidate,14\none,candidate,16\n"
        )
        managers = _fresh_csv(page, tmp_path, payload)
        managers.select_tab("Compare")
        managers._open_and_select(managers.comparison_group_selectbox, "configuration")
        managers._open_and_select(managers.comparison_method_selectbox, "Statistics")
        managers.add_comparison_metric("ipc")
        managers.add_comparison_key("benchmark")
        managers.apply_comparison()
        rows = _download_rows(managers.download_comparison("csv"))
        assert len(rows) == 1
        row = rows[0]
        assert row["benchmark"] == "one"
        assert row["baseline_n"] == row["candidate_n"] == "3"
        assert float(row["baseline_mean"]) == 12.0
        assert float(row["candidate_mean"]) == 14.0
        assert float(row["mean_difference"]) == 2.0
        assert "small_baseline_sample" in row["warning"]
        assert "small_candidate_sample" in row["warning"]
        assert math.isfinite(float(row["p_value"]))
        assert float(row["difference_ci_low"]) <= 2 <= float(row["difference_ci_high"])
        assert _active_rows(page) == _csv_rows(payload)
        _assert_clean(page)


@pytest.fixture
def writable_stats(browser_stats_root: Path) -> Path:
    """Create a test-owned results tree authorized by the isolated web server."""
    return Path(tempfile.mkdtemp(prefix="parser-", dir=browser_stats_root))


def _write_stats(
    root: Path, run: str, ticks: int, ipc: float, *, invalid_utf8: bool = False
) -> Path:
    """Write real simulator input; invalid encoding exercises the real worker failure path."""
    directory = root / run
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "stats.txt"
    payload = (
        f"benchmark_name={run}\nconfig_description=controlled\n"
        f"simTicks {ticks}\nsystem.cpu.ipc {ipc}\n"
    ).encode("utf-8")
    path.write_bytes(payload + (b"\xff\n" if invalid_utf8 else b""))
    return path


def _configure_stats(page: Page, root: Path, variable: str = "system.cpu.ipc") -> DataSourcePage:
    """Choose literal sources through the real parser form without scanning malformed input."""
    source = DataSourcePage(page)
    source.navigate()
    source.ensure_parse_mode()
    source.fill_stats_path(str(root))
    source.fill_stats_pattern("stats.txt")
    source.add_manual_variable(variable, "scalar")
    return source


def _recent_names(source: DataSourcePage) -> set[str]:
    """Read exact pooled filenames, including deduplicated parsed results."""
    source.navigate()
    source.select_recent_mode()
    cards = source.page.get_by_test_id("stExpander").filter(
        has=source.page.get_by_role("button", name="Review & Load", exact=True, include_hidden=True)
    )
    labels = cards.locator("summary p").all_text_contents()
    assert len(labels) == cards.count()
    return {label.rsplit(" (", 1)[0] for label in labels}


def _numeric_observations(rows: list[dict[str, str]]) -> set[tuple[float, float]]:
    """Compare complete paired measurements without relying on file completion order."""
    return {(float(row["simTicks"]), float(row["system.cpu.ipc"])) for row in rows}


@pytest.mark.xdist_group("e2e_parser_recovery")
@pytest.mark.timeout(240)
class TestParserRecovery:
    """Parser failures remain actionable and never silently replace an existing table."""

    def test_partial_result_requires_explicit_loading_before_replacing_data(
        self, tier0_page: Page, tmp_path: Path, writable_stats: Path
    ) -> None:
        # [test->req~ring5.ingestion.session-background-parse~1]
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        _write_stats(writable_stats, "valid", 100, 1.25)
        _write_stats(writable_stats, "invalid", 200, 2.5, invalid_utf8=True)
        source = _configure_stats(page, writable_stats)
        before_recent = _recent_names(source)
        source.ensure_parse_mode()
        source.click_parse()
        source.wait_for_parse_terminal_outcome(timeout=E2E_TIMEOUT)
        expect(source.parse_job_load_partial_button).to_be_visible()
        expect(source.parse_job_retry_button).to_be_enabled()
        expect(source.parse_job_dismiss_button).to_be_enabled()
        expect(
            page.get_by_test_id("stMainBlockContainer").get_by_text(
                "Some files failed; partial CSV is ready", exact=True
            )
        ).to_be_visible()
        expect(source.parse_completion_notice).to_have_count(0)
        partial_id = source.get_parse_recovery_id()
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)
        assert _recent_names(source) == before_recent

        source.ensure_parse_mode()
        source.load_partial_parse_and_wait(timeout=E2E_TIMEOUT)
        assert source.get_parse_completion_id() == partial_id
        expect(source.parse_completion_notice).to_contain_text("Loaded partial CSV:")
        completed_text = source.parse_completion_notice.inner_text()
        loaded_path = completed_text.split("Loaded partial CSV: ", 1)[1].strip()
        loaded_name = Path(loaded_path).name
        assert loaded_name.endswith(".csv")
        rows = _active_rows(page)
        assert len(rows) == 1
        assert _numeric_observations(rows) == {(100.0, 1.25)}
        assert _recent_names(source) == before_recent | {loaded_name}
        _assert_clean(page)

    def test_failed_attempt_retries_corrected_inputs_with_a_fresh_result_identity(
        self, tier0_page: Page, tmp_path: Path, writable_stats: Path
    ) -> None:
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        _write_stats(writable_stats, "first", 100, 1.25, invalid_utf8=True)
        _write_stats(writable_stats, "second", 200, 2.5, invalid_utf8=True)
        source = _configure_stats(page, writable_stats)
        source.click_parse()
        source.wait_for_parse_terminal_outcome(timeout=E2E_TIMEOUT)
        expect(
            page.get_by_test_id("stMainBlockContainer").get_by_text(
                "Parsing produced no usable results", exact=True
            )
        ).to_be_visible()
        expect(source.parse_job_load_partial_button).to_have_count(0)
        expect(source.parse_completion_notice).to_have_count(0)
        failed_id = source.get_parse_recovery_id()
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)

        # A user fixes the actual simulator files; Retry must fingerprint those corrected bytes.
        _write_stats(writable_stats, "first", 300, 3.75)
        _write_stats(writable_stats, "second", 400, 5.0)
        source.navigate()
        source.ensure_parse_mode()
        source.retry_parse_and_wait(timeout=E2E_TIMEOUT)
        assert source.get_parse_completion_id() != failed_id
        rows = _active_rows(page)
        assert len(rows) == 2
        assert _numeric_observations(rows) == {(300.0, 3.75), (400.0, 5.0)}
        _assert_clean(page)

    def test_invalid_statistic_filter_is_reported_and_can_be_dismissed_without_loading(
        self, tier0_page: Page, tmp_path: Path, writable_stats: Path
    ) -> None:
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        _write_stats(writable_stats, "valid", 100, 1.25)
        source = _configure_stats(page, writable_stats, variable="unsupported.*")
        source.click_parse()
        source.wait_for_parse_terminal_outcome(timeout=E2E_TIMEOUT)
        expect(source.parse_job_retry_button).to_be_visible()
        expect(source.parse_job_load_partial_button).to_have_count(0)
        details = (
            page.get_by_test_id("stMainBlockContainer")
            .get_by_test_id("stExpander")
            .filter(has=page.get_by_text("Error details", exact=True))
        )
        details.locator("summary").click()
        expect(details).to_contain_text(
            "Concrete source name is not an exact statistic identifier: 'unsupported.*'."
        )
        expect(source.parse_completion_notice).to_have_count(0)
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)
        source.navigate()
        source.ensure_parse_mode()
        source.parse_job_dismiss_button.click()
        source.wait_for_streamlit(expect_rerun=True)
        expect(source.parse_job_heading).to_have_count(0)
        expect(source.parse_job_retry_button).to_have_count(0)
        expect(source.parse_button).to_be_enabled()
        expect(source.parse_completion_notice).to_have_count(0)
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)
        _assert_clean(page)

    def test_missing_stats_directory_preserves_the_loaded_workspace(
        self, tier0_page: Page, tmp_path: Path, writable_stats: Path
    ) -> None:
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        source = DataSourcePage(page)
        source.navigate()
        source.ensure_parse_mode()
        source.fill_stats_path(str(writable_stats / "does-not-exist"))
        source.click_parse()
        exception = page.get_by_test_id("stMainBlockContainer").get_by_test_id("stException")
        expect(exception).to_contain_text("Stats path does not exist", timeout=E2E_TIMEOUT)
        expect(source.parse_job_heading).to_have_count(0)
        expect(source.parse_completion_notice).to_have_count(0)
        expect(source.parse_button).to_be_enabled()
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)

    def test_missing_measurements_remain_visible_in_preview_and_empty_in_parsed_csv(
        self, tier0_page: Page, tmp_path: Path, writable_stats: Path
    ) -> None:
        # [test->req~ring5.ingestion.parser-playground~1]
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        _write_stats(writable_stats, "first", 100, 1.25)
        _write_stats(writable_stats, "second", 200, 2.5)
        source = _configure_stats(page, writable_stats, variable="missing.measurement")
        source.test_parser_configuration_button.click()
        dialog = source.dialog_overlay
        expect(dialog.get_by_text("Missing sampled values:", exact=False)).to_contain_text(
            "missing.measurement", timeout=E2E_TIMEOUT
        )
        expect(
            dialog.get_by_text("Review the diagnostics before starting a full parse.")
        ).to_be_visible()
        expect(dialog.get_by_text("Ready for a full parse.", exact=True)).to_have_count(0)
        sample = _download_rows(source.download_playground_sample())
        assert len(sample) == 2
        assert all(row["missing.measurement"] == "" for row in sample)
        source.close_dialog()
        assert _active_rows(page) == _csv_rows(_SMALL_CSV)
        source.navigate()
        source.ensure_parse_mode()
        source.parse_and_wait(timeout=E2E_TIMEOUT)
        rows = _active_rows(page)
        assert len(rows) == 2
        assert {float(row["simTicks"]) for row in rows} == {100.0, 200.0}
        assert all(row["missing.measurement"] == "" for row in rows)
        _assert_clean(page)

    def test_incremental_updates_and_removed_files_rebuild_the_exact_current_table(
        self, tier0_page: Page, tmp_path: Path, writable_stats: Path
    ) -> None:
        # [test->req~ring5.ingestion.incremental-parsing~1]
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        first = _write_stats(writable_stats, "unchanged", 100, 1.25)
        _write_stats(writable_stats, "changed", 200, 2.5)
        source = _configure_stats(page, writable_stats)
        expect(source.incremental_parse_checkbox).to_be_checked()
        source.parse_and_wait(timeout=E2E_TIMEOUT)
        initial_id = source.get_parse_completion_id()
        initial = _active_rows(page)
        assert len(initial) == 2
        assert _numeric_observations(initial) == {(100.0, 1.25), (200.0, 2.5)}

        _write_stats(writable_stats, "changed", 400, 5.0)
        _write_stats(writable_stats, "added", 300, 3.75)
        source.navigate()
        source.ensure_parse_mode()
        source.parse_and_wait(timeout=E2E_TIMEOUT)
        changed_id = source.get_parse_completion_id()
        assert changed_id != initial_id
        grown = _active_rows(page)
        assert len(grown) == 3
        assert _numeric_observations(grown) == {(100.0, 1.25), (400.0, 5.0), (300.0, 3.75)}

        first.unlink()
        source.navigate()
        source.ensure_parse_mode()
        source.parse_and_wait(timeout=E2E_TIMEOUT)
        assert source.get_parse_completion_id() not in {initial_id, changed_id}
        reduced = _active_rows(page)
        assert len(reduced) == 2
        assert _numeric_observations(reduced) == {(400.0, 5.0), (300.0, 3.75)}
        _assert_clean(page)


@pytest.mark.xdist_group("e2e_remote_source_boundary")
class TestRemoteSourceBoundary:
    """Each remote form exposes its configuration but obeys the empty host allowlist."""

    @pytest.mark.parametrize(
        ("adapter", "labels"),
        [
            ("HTTPS", ("HTTPS URL", "Bearer token (optional)")),
            (
                "SSH",
                (
                    "SSH host",
                    "SSH username (optional)",
                    "Absolute remote file path",
                    "Server-side identity file (optional)",
                ),
            ),
            (
                "S3-compatible",
                (
                    "S3-compatible HTTPS endpoint",
                    "Bucket",
                    "Object key",
                    "Region",
                    "Access key (optional)",
                    "Secret key (optional)",
                    "Session token (optional)",
                ),
            ),
        ],
    )
    def test_unauthorized_remote_adapters_cannot_fetch(
        self, tier0_page: Page, adapter: str, labels: tuple[str, ...]
    ) -> None:
        # [test->req~ring5.ingestion.remote-sources~1]
        source = DataSourcePage(tier0_page)
        source.navigate()
        source.select_remote_source()
        source._open_and_select(source.remote_adapter_select, adapter)
        expect(tier0_page.get_by_text("Remote access is disabled.", exact=False)).to_be_visible()
        for label in labels:
            expect(tier0_page.get_by_label(label, exact=True)).to_be_visible()
        if adapter == "SSH":
            expect(tier0_page.get_by_role("spinbutton", name="SSH port", exact=True)).to_have_value(
                "22"
            )
        expect(source.remote_fetch_button).to_be_disabled()
        expect(source.load_accepted_import_button).to_have_count(0)
        _assert_clean(tier0_page)


@pytest.mark.xdist_group("e2e_parser_reset_defaults")
class TestParserResetDefaults:
    """Reset All retires authored parser state and reconstructs the ordinary initial page."""

    def test_reset_all_removes_authored_parser_settings_data_and_widget_values(
        self, tier0_page: Page, tmp_path: Path, writable_stats: Path
    ) -> None:
        # [test->req~ring5.workspace.reset~1]
        page = tier0_page
        _fresh_csv(page, tmp_path, _SMALL_CSV)
        _write_stats(writable_stats, "input", 100, 1.25)
        source = _configure_stats(page, writable_stats, variable="authored.measurement")
        source.fill_stats_pattern("authored.stats")
        source.ensure_config_aware_strategy()
        expect(source.incremental_parse_checkbox).to_be_checked()
        with source.expect_script_rerun():
            source.incremental_parse_checkbox.locator("xpath=ancestor::label").click()
        expect(source.incremental_parse_checkbox).not_to_be_checked()
        deep_scan = page.get_by_role(
            "checkbox", name=re.compile(r"^Deep Scan \(up to \d+ files\)$")
        )
        expect(deep_scan).not_to_be_checked()
        with source.expect_script_rerun():
            deep_scan.locator("xpath=ancestor::label").click()
        expect(deep_scan).to_be_checked()
        expect(source.config_json_view).to_contain_text("authored.measurement")
        expect(source.config_json_view).to_contain_text("authored.stats")
        source.select_recent_mode()

        source.reset_all()

        expect(source.step_header).to_be_visible(timeout=E2E_TIMEOUT)
        expect(source.parse_option).to_be_checked()
        expect(source.stats_path_input).to_have_value("/path/to/stats")
        expect(source.stats_pattern_input).to_have_value("stats.txt")
        expect(source.strategy_simple_option).to_be_checked()
        expect(source.strategy_config_aware_option).not_to_be_checked()
        expect(source.incremental_parse_checkbox).to_be_checked()
        expect(deep_scan).not_to_be_checked()
        expect(source.variable_name_inputs).to_have_count(3)
        assert [field.input_value() for field in source.variable_name_inputs.all()] == [
            "simTicks",
            "benchmark_name",
            "config_description",
        ]
        expect(source.config_json_view).not_to_contain_text("authored.measurement")
        expect(source.config_json_view).not_to_contain_text(str(writable_stats))
        expect(
            page.get_by_role("button", name="Load example portfolio", exact=True)
        ).to_be_visible()
        managers = DataManagersPage(page)
        managers.navigate()
        expect(managers.no_data_warning).to_be_visible()
        source.navigate()
        expect(source.stats_path_input).to_have_value("/path/to/stats")
        expect(source.variable_name_inputs).to_have_count(3)
        _assert_clean(page)


@pytest.mark.xdist_group("e2e_schema_contract_semantics")
class TestSchemaContractSemantics:
    """Schema edits and unit conversions retain exact values and undoable revisions."""

    def test_schema_rejection_semantic_conversion_failure_and_undo_preserve_exact_values(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.data.schema-contracts~1]
        # [test->req~ring5.data.semantic-units~1]
        page = tier0_page
        original = "benchmark,time,time.sd\nalpha,1000,100\nbeta,2500,250\n"
        managers = _fresh_csv(page, tmp_path, original)
        managers.select_tab("Workspace")
        managers.retain_current_dataset("timings")
        managers.select_tab("Schema Contract")
        managers.edit_schema_rule("time", "Minimum", "1200")
        managers.validate_schema_contract()
        expect(managers.schema_contract_status_metric.get_by_test_id("stMetricValue")).to_have_text(
            "Needs attention", timeout=E2E_TIMEOUT
        )
        expect(managers.schema_failed_rules_metric.get_by_test_id("stMetricValue")).to_have_text(
            "1"
        )
        expect(managers.schema_affected_rows_metric.get_by_test_id("stMetricValue")).to_have_text(
            "1"
        )
        expect(managers.schema_contract_panel.get_by_test_id("stAlertContentError")).to_have_text(
            "The active dataset does not satisfy this contract."
        )
        assert _active_rows(page) == _csv_rows(original)

        managers.select_tab("Schema Contract")
        managers.edit_schema_rule("time", "Minimum", "0")
        managers.edit_schema_rule("time", "Semantic label", "Latency")
        managers.edit_schema_rule("time", "Unit", "ms")
        managers.validate_schema_contract()
        expect(managers.schema_contract_status_metric.get_by_test_id("stMetricValue")).to_have_text(
            "Valid", timeout=E2E_TIMEOUT
        )
        managers.apply_schema_semantics()
        expect(managers.schema_semantics_success).to_be_visible(timeout=E2E_TIMEOUT)
        expect(managers.schema_unit_target_selectbox).to_contain_text("currently ms")
        assert _active_rows(page) == _csv_rows(original)

        managers.select_tab("Schema Contract")
        managers.convert_schema_unit("time", "s")
        expect(
            managers.schema_contract_panel.get_by_text(
                "Converted time to s; the prior revision remains undoable.", exact=True
            )
        ).to_be_visible(timeout=E2E_TIMEOUT)
        converted = _active_rows(page)
        assert [
            (row["benchmark"], float(row["time"]), float(row["time.sd"])) for row in converted
        ] == [("alpha", 1.0, 0.1), ("beta", 2.5, 0.25)]

        managers.select_tab("Schema Contract")
        managers.convert_schema_unit("time", "W")
        expect(managers.schema_contract_panel.get_by_test_id("stAlertContentError")).to_have_text(
            "Cannot convert 's' to 'W': units are not compatible.", timeout=E2E_TIMEOUT
        )
        assert _active_rows(page) == converted
        managers.select_tab("Workspace")
        expect(managers.workspace_undo_button).to_be_enabled()
        managers.undo_workspace_dataset()
        restored = _active_rows(page)
        assert [
            (row["benchmark"], float(row["time"]), float(row["time.sd"])) for row in restored
        ] == [("alpha", 1000.0, 100.0), ("beta", 2500.0, 250.0)]
        managers.select_tab("Schema Contract")
        expect(managers.schema_unit_target_selectbox).to_contain_text("currently ms")
        assert managers.schema_rule_value("time", "Semantic label") == "Latency"
        assert managers.schema_rule_value("time", "Unit") == "ms"
        _assert_clean(page)
