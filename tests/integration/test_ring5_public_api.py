"""Integration tests for the complete headless ``ring5`` workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

import pandas as pd
import pytest

import ring5

DATA_ROOT = Path(__file__).parent.parent / "data" / "results-micro26-sens"

pytestmark = [pytest.mark.xdist_group("ring5_portfolios"), pytest.mark.public_api]


def _first_stats_subtree() -> Path:
    """The directory for one real gem5 run from the test dataset."""
    if not DATA_ROOT.exists():
        pytest.skip("test data not downloaded (make test-data)")
    for stats_file in sorted(DATA_ROOT.rglob("stats.txt")):
        return stats_file.parent
    pytest.skip("no stats.txt under test data")


class TestFullWorkflow:
    # [test->req~ring5.api.session~1]
    """stats.txt → figure file, entirely through ring5."""

    def test_parse_to_figure_files(self, tmp_path: Path) -> None:
        # [test->req~ring5.ingestion.csv-load~1]
        subtree = _first_stats_subtree()

        with ring5.Session() as s:
            # parse (the scan resolves each variable's type)
            result = s.parse(
                str(subtree),
                variables=["simTicks", "hostSeconds"],
                output_dir=str(tmp_path / "parse_out"),
            )
            assert result.missing_stats == []
            assert Path(result.csv_path).exists()

            # load + shape
            df = s.load(result.csv_path)
            assert "simTicks" in df.columns
            assert len(df) > 0
            shaped = s.shape(df, [{"type": "columnSelector", "columns": ["simTicks"]}])
            assert list(shaped.columns) == ["simTicks"]

            # plot on a small slice
            plot_df = df.head(5).copy()
            plot_df["run"] = [f"r{i}" for i in range(len(plot_df))]
            plot = s.create_plot(
                "bar",
                data=plot_df,
                config={"x": "run", "y": "simTicks", "title": "simTicks"},
            )

            # render both engines + export zero-dependency formats
            mpl_fig = s.render(plot, engine="matplotlib")
            pdf_path = s.export(mpl_fig, str(tmp_path / "fig.pdf"))
            assert open(pdf_path, "rb").read(5) == b"%PDF-"

            plotly_fig = s.render(plot, engine="plotly")
            html_path = s.export(plotly_fig, str(tmp_path / "fig.html"))
            assert b"<html" in open(html_path, "rb").read(200).lower()

    def test_typoed_stat_raises_missing_stat_error(self, tmp_path: Path) -> None:
        """strict mode turns the all-NaN-column trap into a loud error."""
        subtree = _first_stats_subtree()
        with ring5.Session() as s:
            with pytest.raises(ring5.ScanError, match="not found by the scan"):
                s.parse(
                    str(subtree),
                    variables=["totally.bogus.stat"],
                    output_dir=str(tmp_path / "parse_out"),
                )

    def test_vector_and_pattern_variables_parse(self, tmp_path: Path) -> None:
        """Scan metadata (entries, pattern flag) must reach the parser:
        a bare name+type config crashed vectors and never expanded
        pattern variables (regression)."""
        subtree = _first_stats_subtree()
        with ring5.Session() as s:
            # Full scan: a sampled scan can report a type that later files
            # contradict (gem5 type evolution), which is a parser error by
            # design — this test targets the metadata plumbing, not that.
            futures = s.api.submit_scan_async(str(subtree), "stats.txt", limit=0)
            scan = s.api.finalize_scan([f.result() for f in futures])
            by_name_order = sorted(scan.variables, key=lambda v: v.name)
            # A plain (non-pattern) vector — per-core vectors get aggregated
            # into pattern variables, so one may not exist in every dataset.
            vector = next(
                (
                    v
                    for v in by_name_order
                    if v.type == "vector" and v.entries and "\\d+" not in v.name
                ),
                None,
            )
            pattern = next(
                (v for v in by_name_order if "\\d+" in v.name and v.type == "vector" and v.entries),
                None,
            )
            names = [v.name for v in (vector, pattern) if v is not None]
            if not names:
                pytest.skip("no vector/pattern variables in sampled files")

            result = s.parse(
                str(subtree),
                variables=names,
                output_dir=str(tmp_path / "parse_out"),
                scan_limit=0,
                strict=False,
            )

            # The vector's entries metadata reached TypeMapper (a bare
            # name+type config raised 'entries parameter is required') and
            # real values were parsed for it.
            if vector is not None:
                assert vector.name not in result.missing_stats

            # The pattern variable expanded (is_regex was enabled), produced
            # its per-index entry columns, and retained real values.
            if pattern is not None:
                df = pd.read_csv(result.csv_path)
                pattern_cols = [c for c in df.columns if c.startswith(f"{pattern.name}.")]
                assert pattern_cols, (
                    "pattern variable produced no columns — is_regex was "
                    "not enabled on the way to the parser"
                )
                assert bool(df[pattern_cols].notna().any().any())

    def test_parse_empty_dir_raises_typed(self, tmp_path: Path) -> None:
        """The boundary normalizes the core FileNotFoundError to ScanError."""
        empty = tmp_path / "empty"
        empty.mkdir()
        with ring5.Session() as s:
            with pytest.raises(ring5.ScanError, match="No files matching"):
                s.parse(str(empty), variables=["simTicks"])


class TestRegressionComparison:
    """Compare experiment measurements through the supported public API."""

    def test_dataframe_comparison(self) -> None:
        # [test->req~ring5.analysis.regression-comparison~1]
        baseline = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 2.0]})
        candidate = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.1, 1.7]})

        with ring5.Session() as session:
            result = session.compare(
                baseline,
                candidate,
                ["benchmark"],
                ["ipc"],
                thresholds=5.0,
                baseline_name="main",
                candidate_name="change",
            )

        assert isinstance(result, pd.DataFrame)
        assert result["outcome"].tolist() == ["improvement", "regression"]
        assert result["baseline_name"].tolist() == ["main", "main"]

    def test_table_comparison_returns_table(self) -> None:
        baseline = ring5.Table.from_rows([{"benchmark": "a", "ipc": 1.0}])
        candidate = ring5.Table.from_rows([{"benchmark": "a", "ipc": 0.9}])

        with ring5.Session() as session:
            result = session.compare(
                baseline,
                candidate,
                ["benchmark"],
                ["ipc"],
                directions="lower",
            )

        assert isinstance(result, ring5.Table)
        assert result.rows()[0]["outcome"] == "improvement"

    def test_invalid_comparison_raises_typed_error(self) -> None:
        baseline = pd.DataFrame({"benchmark": ["a", "a"], "ipc": [1.0, 2.0]})
        candidate = pd.DataFrame({"benchmark": ["a"], "ipc": [1.1]})

        with ring5.Session() as session:
            with pytest.raises(ring5.DataValidationError, match="not unique"):
                session.compare(baseline, candidate, ["benchmark"], ["ipc"])

    def test_repeated_sample_statistics(self) -> None:
        # [test->req~ring5.analysis.statistical-comparison~1]
        baseline = ring5.Table.from_rows(
            [
                {"benchmark": "a", "ipc": 1.0},
                {"benchmark": "a", "ipc": 1.1},
                {"benchmark": "a", "ipc": 0.9},
            ]
        )
        candidate = ring5.Table.from_rows(
            [
                {"benchmark": "a", "ipc": 1.5},
                {"benchmark": "a", "ipc": 1.6},
                {"benchmark": "a", "ipc": 1.4},
            ]
        )

        with ring5.Session() as session:
            result = session.compare_statistics(
                baseline,
                candidate,
                ["benchmark"],
                ["ipc"],
                bootstrap_samples=100,
                random_seed=4,
            )

        assert isinstance(result, ring5.Table)
        row = result.rows()[0]
        assert row["baseline_n"] == 3
        assert row["candidate_n"] == 3
        assert row["mean_difference"] == pytest.approx(0.5)

    def test_invalid_statistics_raise_typed_error(self) -> None:
        baseline = pd.DataFrame({"ipc": [1.0, 2.0]})
        candidate = pd.DataFrame({"ipc": [2.0, 3.0]})

        with ring5.Session() as session:
            valid = session.compare_statistics(
                baseline,
                candidate,
                [],
                ["ipc"],
                bootstrap_samples=100,
            )
            assert isinstance(valid, pd.DataFrame)
            with pytest.raises(ring5.DataValidationError, match="confidence_level"):
                session.compare_statistics(
                    baseline,
                    candidate,
                    [],
                    ["ipc"],
                    confidence_level=1.0,
                )

    def test_comparison_annotations_are_plot_ready(self) -> None:
        # [test->req~ring5.analysis.regression-annotations~1]
        baseline = pd.DataFrame({"benchmark": ["a"], "ipc": [1.0]})
        candidate = pd.DataFrame({"benchmark": ["a"], "ipc": [1.2]})

        with ring5.Session() as session:
            comparison = session.compare(
                baseline,
                candidate,
                ["benchmark"],
                ["ipc"],
                thresholds=5.0,
            )
            assert isinstance(comparison, pd.DataFrame)
            annotated = session.annotate_comparison(
                comparison,
                label_columns=["benchmark"],
            )

        assert isinstance(annotated, pd.DataFrame)
        assert annotated.loc[0, "annotation_label"] == "a · ipc"
        assert annotated.loc[0, "annotation_text"] == "▲ Improvement: +20.00%"

    def test_comparison_annotations_preserve_table_and_typed_errors(self) -> None:
        comparison = ring5.Table.from_rows(
            [
                {
                    "benchmark": "a",
                    "metric": "ipc",
                    "baseline_name": "main",
                    "candidate_name": "change",
                    "baseline_value": 1.0,
                    "candidate_value": 0.9,
                    "absolute_change": -0.1,
                    "percentage_change": -10.0,
                    "direction": "higher",
                    "threshold": 2.0,
                    "threshold_mode": "percentage",
                    "outcome": "regression",
                }
            ]
        )

        with ring5.Session() as session:
            annotated = session.annotate_comparison(comparison)
            assert isinstance(annotated, ring5.Table)
            assert annotated.rows()[0]["annotation_symbol"] == "▼"
            with pytest.raises(ring5.DataValidationError, match="missing columns"):
                session.annotate_comparison(pd.DataFrame({"outcome": ["regression"]}))


class TestDataQuality:
    """Inspect dataset quality through the supported public API."""

    def test_profile_table(self) -> None:
        # [test->req~ring5.data.quality-profiler~1]
        data = ring5.Table.from_rows(
            [
                {"value": "1", "label": "a"},
                {"value": "bad", "label": "a"},
            ]
        )

        with ring5.Session() as session:
            report = session.profile_data(data, expected_types={"value": "numeric"})

        assert isinstance(report, ring5.DataQualityReport)
        assert isinstance(report.columns[0], ring5.ColumnQuality)
        assert report.duplicate_rows == 0
        assert report.schema_violations == 1
        assert report.to_frame().loc[0, "invalid_type_values"] == 1

    def test_invalid_expected_type_raises_typed_error(self) -> None:
        with ring5.Session() as session:
            with pytest.raises(ring5.DataValidationError, match="Invalid expected type"):
                session.profile_data(
                    pd.DataFrame({"value": [1]}),
                    expected_types={"value": "currency"},  # type: ignore[dict-item]
                )


class TestDatasetSchemaContracts:
    """Define and validate explicit dataset boundaries through ``ring5``."""

    def test_infer_define_and_validate_schema_contract(self) -> None:
        # [test->req~ring5.data.schema-contracts~1]
        data = ring5.Table.from_rows(
            [
                {"benchmark": "a", "ipc": 1.0, "status": "stable"},
                {"benchmark": "b", "ipc": 3.0, "status": "unexpected"},
            ]
        )
        contract = ring5.DatasetSchemaContract(
            "results-v1",
            (
                ring5.ColumnContract("benchmark", data_type="string"),
                ring5.ColumnContract(
                    "ipc",
                    data_type="numeric",
                    minimum=0.0,
                    maximum=2.0,
                ),
                ring5.ColumnContract(
                    "status",
                    data_type="string",
                    accepted_values=("stable", "experimental"),
                ),
            ),
            allow_extra_columns=False,
        )

        with ring5.Session() as session:
            inferred = session.infer_schema_contract(data, name="inferred")
            report = session.validate_schema(data, contract)

        assert isinstance(inferred, ring5.DatasetSchemaContract)
        assert isinstance(inferred.columns[0], ring5.ColumnContract)
        assert isinstance(report, ring5.SchemaValidationReport)
        assert all(isinstance(item, ring5.SchemaViolation) for item in report.violations)
        assert report.valid is False
        assert {(item.rule, item.column) for item in report.violations} == {
            ("maximum", "ipc"),
            ("accepted_values", "status"),
        }

    def test_schema_contract_errors_are_typed(self) -> None:
        contract = ring5.DatasetSchemaContract("schema", (ring5.ColumnContract("value"),))
        with ring5.Session() as session:
            with pytest.raises(ring5.DataValidationError, match="pandas DataFrame"):
                session.infer_schema_contract(42)  # type: ignore[arg-type]
            with pytest.raises(ring5.DataValidationError, match="DatasetSchemaContract"):
                session.validate_schema(
                    pd.DataFrame({"value": [1]}),
                    object(),  # type: ignore[arg-type]
                )
            with pytest.raises(ring5.DataValidationError, match="unique column names"):
                session.validate_schema(
                    pd.DataFrame([[1, 2]], columns=["value", "value"]),
                    contract,
                )


class TestDatasetSemanticMetadata:
    """Retain human labels and units through conversion, figures, and exports."""

    def test_semantics_drive_conversion_figure_labels_and_csv_export(self, tmp_path: Path) -> None:
        # [test->req~ring5.data.semantic-units~1]
        source = ring5.Table.from_rows(
            [
                {"benchmark": "a", "latency": 1.0},
                {"benchmark": "b", "latency": 2.5},
            ]
        )
        contract = ring5.DatasetSchemaContract(
            "latency-results",
            (
                ring5.ColumnContract("benchmark", semantic_label="Workload"),
                ring5.ColumnContract(
                    "latency",
                    data_type="numeric",
                    semantic_label="Mean latency",
                    unit="ms",
                ),
            ),
        )

        with ring5.Session() as session:
            annotated = session.apply_semantics(source, contract)
            assert isinstance(annotated, ring5.Table)
            converted = session.convert_unit(annotated, "latency", "us")
            semantics = session.inspect_semantics(converted)
            plot = session.create_plot(
                "line",
                data=converted,
                config={"x": "benchmark", "y": "latency"},
            )
            plotly_figure = session.render(plot, engine="plotly")
            matplotlib_figure = session.render(plot, engine="matplotlib")

        latency = semantics.for_column("latency")
        assert isinstance(latency, ring5.ColumnSemantics)
        assert latency.display_label == "Mean latency (us)"
        assert converted.rows()[1]["latency"] == pytest.approx(2500.0)
        assert plotly_figure.layout.xaxis.title.text == "Workload"
        assert plotly_figure.layout.yaxis.title.text == "Mean latency (us)"
        assert matplotlib_figure.axes[0].get_xlabel() == "Workload"
        assert matplotlib_figure.axes[0].get_ylabel() == "Mean latency (us)"

        csv_path = tmp_path / "latency.csv"
        converted.to_csv(str(csv_path))
        sidecar = json.loads(Path(f"{csv_path}.metadata.json").read_text())
        assert sidecar["format"] == "ring5.semantic-columns"
        assert sidecar["columns"]["latency"] == {
            "label": "Mean latency",
            "unit": "us",
        }
        plain_path = tmp_path / "plain.csv"
        converted.to_csv(str(plain_path), include_metadata=False)
        assert not Path(f"{plain_path}.metadata.json").exists()

    def test_semantic_errors_use_the_public_validation_type(self) -> None:
        # [test->req~ring5.data.semantic-units~1]
        data = pd.DataFrame({"latency": [1.0]})
        semantics = ring5.DatasetSemantics((ring5.ColumnSemantics("latency", "Latency", "ms"),))
        with ring5.Session() as session:
            annotated = session.apply_semantics(data, semantics)
            assert "ms" in session.supported_units()
            with pytest.raises(ring5.DataValidationError, match="not compatible"):
                session.convert_unit(annotated, "latency", "MB")
            with pytest.raises(ring5.DataValidationError, match="does not exist"):
                session.apply_semantics(
                    data,
                    ring5.DatasetSemantics((ring5.ColumnSemantics("missing", "Missing"),)),
                )
            with pytest.raises(ring5.DataValidationError, match="pandas DataFrame"):
                session.inspect_semantics(42)  # type: ignore[arg-type]


class TestNamedDatasetWorkspace:
    """Retain and compose independent datasets through the public API."""

    def test_workspace_retains_selects_compares_joins_and_appends(self) -> None:
        # [test->req~ring5.data.multi-dataset-workspace~1]
        baseline = ring5.Table.from_rows(
            [
                {"benchmark": "a", "ipc": 1.0},
                {"benchmark": "b", "ipc": 2.0},
            ]
        )
        candidate = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.2, 1.8], "note": ["x", "y"]})

        with ring5.Session() as session:
            first = session.add_dataset("baseline", baseline)
            second = session.add_dataset("candidate", candidate, select=False)
            assert isinstance(first, ring5.DatasetInfo)
            assert first.selected is True
            assert second.selected is False
            assert [item.name for item in session.list_datasets()] == [
                "baseline",
                "candidate",
            ]

            defensive = session.get_dataset("candidate")
            defensive.loc[0, "ipc"] = 999.0
            assert session.get_dataset("candidate").loc[0, "ipc"] == 1.2

            comparison = session.compare_datasets(
                "baseline",
                "candidate",
                ["benchmark"],
                ["ipc"],
                thresholds=5.0,
            )
            assert comparison["outcome"].tolist() == ["improvement", "regression"]

            appended = session.append_datasets(
                ["baseline", "candidate"],
                "all_runs",
                select=False,
            )
            assert len(appended) == 4
            assert session.get_dataset()["ipc"].tolist() == [1.0, 2.0]

            joined = session.join_datasets(
                "baseline",
                "candidate",
                "paired",
                ["benchmark"],
            )
            assert {"ipc_left", "ipc_right", "note"} <= set(joined.columns)
            assert session.select_dataset("candidate")["ipc"].tolist() == [1.2, 1.8]
            session.remove_dataset("baseline")
            assert "candidate" in {item.name for item in session.list_datasets()}

    def test_workspace_errors_are_typed(self) -> None:
        with ring5.Session() as session:
            session.add_dataset("one", pd.DataFrame({"key": [1], "value": [2.0]}))
            session.add_dataset("two", pd.DataFrame({"key": [1], "value": [3.0]}))
            with pytest.raises(ring5.DataValidationError, match="already exists"):
                session.add_dataset("one", pd.DataFrame({"key": [1]}))
            with pytest.raises(ring5.DataValidationError, match="pandas DataFrame"):
                session.add_dataset("invalid", 42)  # type: ignore[arg-type]
            with pytest.raises(ring5.DataValidationError, match="does not exist"):
                session.get_dataset("missing")
            with pytest.raises(ring5.DataValidationError, match="does not exist"):
                session.select_dataset("missing")
            with pytest.raises(ring5.DataValidationError, match="does not exist"):
                session.remove_dataset("missing")
            with pytest.raises(ring5.DataValidationError, match="at least two"):
                session.append_datasets(["one"], "invalid")
            with pytest.raises(ring5.DataValidationError, match="at least one"):
                session.join_datasets("one", "two", "invalid", [])
            with pytest.raises(ring5.DataValidationError, match="does not exist"):
                session.compare_datasets("missing", "two", ["key"], ["value"])


class TestValidatedDatasetJoins:
    """Diagnose and enforce named-dataset join relationships."""

    def test_diagnose_and_execute_validated_join(self) -> None:
        # [test->req~ring5.data.validated-joins~1]
        left = pd.DataFrame({"key": [1, 2, 4], "name": ["a", "b", "d"]})
        right = pd.DataFrame({"key": [1, 1, 3], "value": [10, 11, 30]})

        with ring5.Session() as session:
            session.add_dataset("left", left)
            session.add_dataset("right", right, select=False)
            diagnostics = session.diagnose_join(
                "left",
                "right",
                ["key"],
                cardinality="one_to_many",
            )
            joined, confirmed = session.join_datasets_validated(
                "left",
                "right",
                "joined",
                ["key"],
                cardinality="one_to_many",
            )

            assert isinstance(diagnostics, ring5.JoinDiagnostics)
            assert diagnostics.cardinality_valid is True
            assert diagnostics.right_duplicate_key_rows == 2
            assert diagnostics.left_unmatched_rows == 2
            assert diagnostics.right_unmatched_rows == 1
            assert diagnostics.matched_key_count == 1
            assert confirmed == diagnostics
            assert joined["value"].tolist() == [10, 11]
            pd.testing.assert_frame_equal(joined, session.get_dataset("joined"))
            assert "one-to-many" in session.dataset_lineage("joined").revisions[0].operation

    def test_cardinality_conflicts_are_typed_and_do_not_store_output(self) -> None:
        with ring5.Session() as session:
            session.add_dataset("left", pd.DataFrame({"key": [1, 2]}))
            session.add_dataset("right", pd.DataFrame({"key": [1, 1]}), select=False)
            with pytest.raises(ring5.DataValidationError, match="Expected a one-to-one join"):
                session.join_datasets_validated(
                    "left",
                    "right",
                    "invalid",
                    ["key"],
                    cardinality="one_to_one",
                )
            assert "invalid" not in {info.name for info in session.list_datasets()}
            with pytest.raises(ring5.DataValidationError, match="Invalid join cardinality"):
                session.diagnose_join(
                    "left",
                    "right",
                    ["key"],
                    cardinality="invalid",  # type: ignore[arg-type]
                )


class TestDatasetLineageAndRecovery:
    """Inspect and recover named dataset states through the supported API."""

    def test_lineage_undo_redo_and_restore(self) -> None:
        # [test->req~ring5.data.lineage-undo-redo~1]
        baseline = pd.DataFrame({"benchmark": ["a"], "ipc": [1.0]})
        candidate = pd.DataFrame({"benchmark": ["b"], "ipc": [2.0], "note": ["candidate"]})

        with ring5.Session() as session:
            session.add_dataset("baseline", baseline)
            session.add_dataset("candidate", candidate, select=False)
            session.append_datasets(["baseline", "candidate"], "combined", join="outer")
            first_lineage = session.dataset_lineage()
            first_revision = first_lineage.revisions[0]

            session.append_datasets(
                ["baseline", "candidate"],
                "combined",
                join="inner",
                replace=True,
            )
            lineage = session.dataset_lineage("combined")

            assert isinstance(lineage, ring5.DatasetLineage)
            assert all(isinstance(item, ring5.DatasetRevision) for item in lineage.revisions)
            assert len(lineage.revisions) == 2
            assert lineage.revisions[-1].operation == "Append datasets (inner)"
            assert lineage.revisions[-1].source_datasets == ("baseline", "candidate")
            assert lineage.revisions[-1].parent_revision_ids[0] == first_revision.revision_id
            assert lineage.can_undo is True
            assert "note" not in session.get_dataset("combined").columns

            inspected = session.get_dataset_revision(first_revision.revision_id)
            inspected.loc[0, "ipc"] = 999.0
            assert session.get_dataset_revision(first_revision.revision_id).loc[0, "ipc"] == 1.0

            undone = session.undo_dataset()
            assert undone.revision_id == first_revision.revision_id
            assert "note" in session.get_dataset("combined").columns
            assert session.dataset_lineage().can_redo is True

            redone = session.redo_dataset("combined")
            assert redone.revision_id == lineage.revisions[-1].revision_id
            assert "note" not in session.get_dataset("combined").columns

            restored = session.restore_dataset_revision(first_revision.revision_id)
            assert restored.revision_id == first_revision.revision_id
            assert session.dataset_lineage().current_revision_id == first_revision.revision_id

    def test_lineage_errors_are_typed(self) -> None:
        with ring5.Session() as session:
            with pytest.raises(ring5.DataValidationError, match="No dataset is selected"):
                session.dataset_lineage()
            session.add_dataset("only", pd.DataFrame({"value": [1]}))
            with pytest.raises(ring5.DataValidationError, match="no earlier revision"):
                session.undo_dataset()
            with pytest.raises(ring5.DataValidationError, match="no revision to redo"):
                session.redo_dataset()
            with pytest.raises(ring5.DataValidationError, match="does not exist"):
                session.get_dataset_revision("missing")
            with pytest.raises(ring5.DataValidationError, match="does not exist"):
                session.restore_dataset_revision("missing")


class TestReusableDatasetSnapshots:
    """Persist exact dataset contents and verify them in a later session."""

    def test_save_list_reload_overwrite_and_delete(self, tmp_path: Path) -> None:
        # [test->req~ring5.data.dataset-snapshots~1]
        snapshots_dir = tmp_path / "dataset_snapshots"
        snapshots_dir.mkdir()
        data = pd.DataFrame(
            {
                "benchmark": pd.Series(["a", "b"], dtype="string"),
                "ipc": [1.0, 2.0],
                "updated": pd.to_datetime(["2026-01-01", "2026-01-02"], utc=True),
            }
        )
        from unittest.mock import patch

        from src.core.services.data_services.path_service import PathService

        with patch.object(
            PathService,
            "get_dataset_snapshots_dir",
            return_value=snapshots_dir,
        ):
            with ring5.Session() as first:
                first.api.state_manager.set_data(data)
                saved = first.save_dataset_snapshot("parsed-once")
                assert isinstance(saved, ring5.DatasetSnapshotInfo)
                assert saved.source_dataset == "active_data"
                assert first.list_dataset_snapshots() == (saved,)
                with pytest.raises(ring5.DataValidationError, match="already exists"):
                    first.save_dataset_snapshot("parsed-once")
                first.save_dataset_snapshot("parsed-once", overwrite=True)

            with ring5.Session() as second:
                restored = second.load_dataset_snapshot(
                    "parsed-once",
                    "restored-results",
                )
                assert isinstance(restored, ring5.DatasetInfo)
                pd.testing.assert_frame_equal(second.get_dataset(), data)
                revision = second.dataset_lineage().revisions[0]
                assert revision.fingerprint == saved.fingerprint
                assert revision.operation == "Load reusable snapshot: parsed-once"
                with pytest.raises(ring5.DataValidationError, match="does not exist"):
                    second.load_dataset_snapshot("missing")

                second.delete_dataset_snapshot("parsed-once")
                assert second.list_dataset_snapshots() == ()
                with pytest.raises(ring5.DataValidationError, match="non-empty"):
                    second.delete_dataset_snapshot("")

    def test_save_named_dataset_defaults_loaded_name(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "dataset_snapshots"
        snapshots_dir.mkdir()
        from unittest.mock import patch

        from src.core.services.data_services.path_service import PathService

        with patch.object(
            PathService,
            "get_dataset_snapshots_dir",
            return_value=snapshots_dir,
        ):
            with ring5.Session() as session:
                session.add_dataset("named-source", pd.DataFrame({"value": [7]}))
                session.save_dataset_snapshot("named", "named-source")
                session.remove_dataset("named-source")
                restored = session.load_dataset_snapshot("named")
                assert restored.name == "named-source"


class TestPortfolioReplay:
    # [test->req~ring5.portfolio.batch-replay~1]
    """Save a session, regenerate every figure from the snapshot."""

    def test_save_then_render_portfolio(self, tmp_path: Path, portfolios_dir: Path) -> None:
        # [test->req~ring5.portfolio.safe-overwrite~1]
        df = pd.DataFrame({"bench": ["a", "b", "c"], "ipc": [1.0, 2.0, 3.0]})
        with ring5.Session() as s:
            s.api.state_manager.set_data(df)
            s.create_plot(
                "bar",
                data=df,
                config={"x": "bench", "y": "ipc", "title": "Replay"},
                name="replay_plot",
            )
            s.save_portfolio("replay_probe")

            # overwrite protection is the script-side default (typed error)
            with pytest.raises(ring5.PortfolioError, match="already exists"):
                s.save_portfolio("replay_probe")
            s.save_portfolio("replay_probe", overwrite=True)

        written = ring5.render_portfolio(
            "replay_probe", str(tmp_path / "figs"), engine="matplotlib", fmt="pdf"
        )
        assert len(written) == 1
        assert written[0].endswith("replay_plot.pdf")
        assert open(written[0], "rb").read(5) == b"%PDF-"

    def test_v1_portfolio_replays(self, tmp_path: Path, portfolios_dir: Path) -> None:
        """The long-horizon reproducibility contract: V1 files keep working."""
        v1: dict[str, Any] = {
            # V1: no schema_version key, export_* keys, no engine field
            "version": "2.0",
            "data_csv": "bench,ipc\na,1.0\nb,2.0\n",
            "csv_path": None,
            "plots": [
                {
                    "id": 0,
                    "name": "v1_plot",
                    "plot_type": "bar",
                    "config": {
                        "x": "bench",
                        "y": "ipc",
                        "title": "V1",
                        "export_format": "png",
                        "export_dpi": 300,
                    },
                    "processed_data": "bench,ipc\na,1.0\nb,2.0\n",
                    "pipeline": [],
                    "pipeline_counter": 0,
                    "legend_mappings_by_column": {},
                    "legend_mappings": {},
                }
            ],
            "plot_counter": 1,
            "config": {},
            "parse_variables": [],
        }
        (portfolios_dir / "v1_probe.json").write_text(json.dumps(v1))

        written = ring5.render_portfolio(
            "v1_probe", str(tmp_path / "figs"), engine="matplotlib", fmt="pdf"
        )
        assert len(written) == 1
        assert open(written[0], "rb").read(5) == b"%PDF-"

    def test_future_portfolio_refused(self, tmp_path: Path, portfolios_dir: Path) -> None:
        # [test->req~ring5.portfolio.migration~1]
        """Forward-version files are refused, never silently downgraded."""
        (portfolios_dir / "future.json").write_text(json.dumps({"schema_version": 4}))
        with pytest.raises(ring5.PortfolioVersionError, match="newer than this RING-5"):
            ring5.render_portfolio("future", str(tmp_path / "figs"))

    def test_missing_portfolio_typed_error(self, tmp_path: Path, portfolios_dir: Path) -> None:
        with pytest.raises(ring5.PortfolioError, match="not found"):
            ring5.render_portfolio("does_not_exist", str(tmp_path / "figs"))


class TestDeterminism:
    # [test->req~ring5.export.deterministic~1]
    """The CI-regression contract for the zero-dependency formats."""

    def test_fig_json_and_exports_stable(self) -> None:
        df = pd.DataFrame({"x": ["a", "b"], "y": [1.0, 2.0]})

        def build() -> tuple[bytes, bytes, str]:
            with ring5.Session() as s:
                plot = s.create_plot("bar", data=df, config={"x": "x", "y": "y"})
                mpl_fig = s.render(plot, engine="matplotlib")
                plotly_fig = s.render(plot, engine="plotly")
                return (
                    s.export_bytes(mpl_fig, "pdf", deterministic=True),
                    s.export_bytes(plotly_fig, "html", deterministic=True),
                    plotly_fig.to_json(),
                )

        pdf_a, html_a, json_a = build()
        pdf_b, html_b, json_b = build()
        assert pdf_a == pdf_b
        assert html_a == html_b
        assert json_a == json_b


class TestErrorSurface:
    # [test->req~ring5.api.typed-errors~1]
    """The typed error hierarchy behaves as documented."""

    def test_pipeline_error_carries_step(self) -> None:
        df = pd.DataFrame({"x": [1.0]})
        with ring5.Session() as s:
            with pytest.raises(ring5.PipelineError) as exc_info:
                s.shape(df, [{"columns": ["x"]}])  # type: ignore[list-item]
        assert exc_info.value.step_index == 0

    def test_missing_column_typed(self) -> None:
        df = pd.DataFrame({"x": [1.0]})
        with ring5.Session() as s:
            with pytest.raises(ring5.ColumnNotFoundError) as exc_info:
                s.remove_outliers(df, "nope")
        assert exc_info.value.column == "nope"
        assert "x" in exc_info.value.available

    def test_all_errors_are_ring5_errors(self) -> None:
        for err in (
            ring5.ScanError,
            ring5.ParseError,
            ring5.MissingStatError,
            ring5.PipelineError,
            ring5.ColumnNotFoundError,
            ring5.DataLoadError,
            ring5.DataValidationError,
            ring5.RenderError,
            ring5.PortfolioError,
            ring5.PortfolioVersionError,
            ring5.ExportError,
            ring5.DependencyMissingError,
        ):
            assert issubclass(err, ring5.Ring5Error)

    def test_missing_csv_raises_typed_error_with_cause(self, tmp_path: Path) -> None:
        """Input-file failures do not leak ``FileNotFoundError``."""
        missing = tmp_path / "missing.csv"
        with ring5.Session() as session:
            with pytest.raises(ring5.DataLoadError) as exc_info:
                session.load(str(missing))
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_invalid_engine_lists_choices(self) -> None:
        # [test->req~ring5.api.plot-validation~1]
        """Invalid render configuration uses the public error hierarchy."""
        data = pd.DataFrame({"x": ["a"], "y": [1.0]})
        with ring5.Session() as session:
            plot = session.create_plot("bar", data=data, config={"x": "x", "y": "y"})
            with pytest.raises(ring5.RenderError, match="matplotlib.*plotly"):
                session.render(plot, engine="invalid")  # type: ignore[arg-type]

    def test_plot_without_data_raises_render_error(self) -> None:
        """A restored or manually cleared plot fails with an actionable error."""
        data = pd.DataFrame({"x": ["a"], "y": [1.0]})
        with ring5.Session() as session:
            plot = session.create_plot("bar", data=data, config={"x": "x", "y": "y"})
            plot.replace_processed_data(None)
            with pytest.raises(ring5.RenderError, match="no processed data"):
                session.render(plot)

    def test_table_missing_column_uses_typed_error(self) -> None:
        """Convenience-table operations share the same column error contract."""
        table = ring5.Table.from_rows([{"x": 1}])
        with pytest.raises(ring5.ColumnNotFoundError) as exc_info:
            table.sort(["missing"])
        assert exc_info.value.column == "missing"


class TestApiErgonomics:
    """Common plotting workflows remain concise and discoverable."""

    def test_plot_accepts_typed_spec_and_display_name(self) -> None:
        data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.5]})
        spec = ring5.FigureSpec(x="benchmark", y_columns=["ipc"], title="IPC")

        with ring5.Session() as session:
            figure = session.plot("Bar Chart", data=data, config=spec, engine="plotly")

            assert figure.layout.title.text == "IPC"
            assert session.plots[0].plot_type == "bar"

    def test_available_plot_types_are_public(self) -> None:
        # [test->req~ring5.api.registry-discovery~1]
        assert "bar" in ring5.available_plot_types()
        assert "grouped_stacked_bar" in ring5.available_plot_types()
        assert set(get_args(ring5.PlotType)) == set(ring5.available_plot_types())

    def test_unknown_plot_type_lists_valid_choices(self) -> None:
        # [test->req~ring5.api.plot-validation~1]
        data = pd.DataFrame({"x": ["a"], "y": [1.0]})

        with ring5.Session() as session:
            with pytest.raises(ring5.DataValidationError, match="Available types:.*bar"):
                session.create_plot("not-a-plot", data=data, config={"x": "x", "y": "y"})
