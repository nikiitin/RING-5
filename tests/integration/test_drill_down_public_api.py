"""Public API coverage for reversible plot source-row drill-down."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import ring5

from src.core.common.source_contributions import SOURCE_CONTRIBUTIONS_ATTR
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.services.data_services.portfolio_validation_service import validate_portfolio_document
from src.core.services.shapers.pipeline_service import PipelineService
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.plot_service import PlotService

pytestmark = pytest.mark.public_api


def _aggregate_pipeline() -> list[dict[str, Any]]:
    return [
        {
            "type": "mean",
            "meanVars": ["ipc"],
            "meanAlgorithm": "arithmean",
            "groupingColumns": ["workload"],
            "replacingColumn": "seed",
        },
        {"type": "itemSelector", "column": "seed", "strings": ["arithmean"], "mode": "exact"},
    ]


def test_public_drill_down_recovers_aggregate_source_rows_without_mutation() -> None:
    # [test->req~ring5.plots.drill-down~1]
    source = pd.DataFrame(
        {
            "workload": ["A", "A", "B"],
            "seed": [0, 1, 0],
            "ipc": [1.0, 1.2, 0.8],
        }
    )
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(source),
            config={"x": "workload", "y": "ipc"},
        )
        pipeline = _aggregate_pipeline()
        plot.pipeline = [
            {"id": index, "type": config["type"], "config": config}
            for index, config in enumerate(pipeline)
        ]
        processed = PipelineService.process_pipeline(source, pipeline, track_source_rows=True)
        plot.replace_pipeline_data(source, processed)
        config_snapshot = dict(plot.config)

        result = session.drill_down(plot, {"workload": "A"})

        assert isinstance(result, ring5.DrillDownResult)
        assert result.row_count == 2
        assert result.rows.frame["seed"].tolist() == [0, 1]
        assert plot.config == config_snapshot
        assert source["ipc"].tolist() == [1.0, 1.2, 0.8]

        by_id = session.drill_down(plot.plot_id, {"workload": "B"})
        assert by_id.rows.frame["seed"].tolist() == [0]


def test_public_drill_down_uses_typed_validation_errors() -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["A"], "y": [1.0]})),
            config={"x": "x", "y": "y"},
        )
        with pytest.raises(ring5.DataValidationError, match="unknown plot ID"):
            session.drill_down(999, {"x": "A"})
        with pytest.raises(ring5.DataValidationError, match="plot ID"):
            session.drill_down(True, {"x": "A"})
        with pytest.raises(ring5.DataValidationError, match="no column"):
            session.drill_down(plot, {"missing": "A"})
        with pytest.raises(ring5.DataValidationError, match="scalar"):
            session.drill_down(plot, {"x": ["A"]})

        plot.replace_source_data(None)
        plot.replace_processed_data(None)
        with pytest.raises(ring5.DataValidationError, match="no source data"):
            session.drill_down(plot, {})


def test_draft_edits_cannot_change_finalized_contributors_or_original_metadata() -> None:
    source = pd.DataFrame(
        {
            "scenario": ["keep", "keep", "remove"],
            "workload": ["A", "A", "A"],
            "seed": [0, 1, 2],
            "ipc": [1.0, 1.2, 100.0],
        }
    )
    pipeline = [
        {"type": "itemSelector", "column": "scenario", "strings": ["keep"], "mode": "exact"},
        {"type": "columnSelector", "columns": ["workload", "ipc"]},
    ]
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar", data=ring5.Table(source), config={"x": "workload", "y": "ipc"}
        )
        finalized = PipelineService.process_pipeline(source, pipeline, track_source_rows=True)
        plot.replace_pipeline_data(source, finalized)
        plot.pipeline = [
            {
                "id": 0,
                "type": "itemSelector",
                "config": {
                    "type": "itemSelector",
                    "column": "scenario",
                    "strings": ["remove"],
                    "mode": "exact",
                },
            }
        ]
        result = session.drill_down(plot, {"workload": "A"})
        assert result.rows.frame["seed"].tolist() == [0, 1]
        assert result.rows.frame["ipc"].tolist() == [1.0, 1.2]
        assert result.rows.frame["scenario"].tolist() == ["keep", "keep"]
        assert session.drill_down(plot, {"workload": "A", "seed": 1}).row_count == 1
        pd.testing.assert_frame_equal(plot.source_data, source)
        exposed = result.rows.frame
        exposed.loc[:, "ipc"] = 999.0
        assert exposed["ipc"].tolist() == [999.0, 999.0]
        assert session.drill_down(plot, {"workload": "A"}).rows.frame["ipc"].tolist() == [1.0, 1.2]


def test_normalized_click_returns_original_candidate_and_supporting_baseline() -> None:
    source = pd.DataFrame(
        {
            "workload": ["A", "A", "B", "B"],
            "variant": ["base", "fast", "base", "fast"],
            "ipc": [2.0, 4.0, 3.0, 9.0],
        }
    )
    pipeline = [
        {
            "type": "normalize",
            "normalizeVars": ["ipc"],
            "normalizerColumn": "variant",
            "normalizerValue": "base",
            "groupBy": ["workload"],
        }
    ]
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar", data=ring5.Table(source), config={"x": "workload", "y": "ipc"}
        )
        finalized = PipelineService.process_pipeline(source, pipeline, track_source_rows=True)
        plot.replace_pipeline_data(source, finalized)
        result = session.drill_down(plot, {"workload": "A", "variant": "fast"})
        assert result.rows.frame["variant"].tolist() == ["base", "fast"]
        assert result.rows.frame["ipc"].tolist() == [2.0, 4.0]
        assert finalized["ipc"].tolist() == [1.0, 2.0, 1.0, 3.0]


def test_contributor_pair_survives_duplication_and_portfolio_round_trip(
    isolated_application_data: Path,
) -> None:
    source = pd.DataFrame({"workload": ["A", "A", "B"], "seed": [0, 1, 0], "ipc": [1.0, 1.2, 0.8]})
    with ring5.Session() as session:
        session.api.state_manager.set_data(source)
        plot = session.create_plot(
            "bar",
            data=ring5.Table(source),
            config={"x": "workload", "y": "ipc"},
            name="Provenanced mean",
        )
        plot.replace_pipeline_data(
            source,
            PipelineService.process_pipeline(
                source,
                _aggregate_pipeline(),
                track_source_rows=True,
            ),
        )
        duplicate = PlotService.duplicate_plot(plot, session.api.state_manager)
        assert duplicate.processed_data is not None and plot.processed_data is not None
        assert (
            duplicate.processed_data.attrs[SOURCE_CONTRIBUTIONS_ATTR]
            is not plot.processed_data.attrs[SOURCE_CONTRIBUTIONS_ATTR]
        )
        assert session.drill_down(duplicate, {"workload": "A"}).rows.frame["seed"].tolist() == [
            0,
            1,
        ]
        session.save_portfolio("contribution-proof")
    with ring5.Session() as restored:
        assert restored.load_portfolio("contribution-proof").complete
        assert len(restored.plots) == 2
        for plot in restored.plots:
            result = restored.drill_down(plot, {"workload": "A"})
            assert result.rows.frame["seed"].tolist() == [0, 1]
            assert result.rows.frame["ipc"].tolist() == [1.0, 1.2]


def test_mismatched_present_proof_is_rejected_before_restore_changes_state(
    isolated_application_data: Path,
) -> None:
    source = pd.DataFrame({"workload": ["A", "B"], "ipc": [1.0, 2.0]})
    with ring5.Session() as session:
        session.api.state_manager.set_data(source)
        plot = session.create_plot(
            "bar", data=ring5.Table(source), config={"x": "workload", "y": "ipc"}
        )
        payload = plot.to_dict()
        payload["source_data"] = TypedTableCodec.encode(source.assign(ipc=[10.0, 20.0]))
        with pytest.raises(ValueError, match="input identity"):
            PlotFactory.from_dict(payload)
        session.save_portfolio("good-proof")
        document = deepcopy(session.api.data_services.load_portfolio("good-proof"))
        document["plots"][0]["source_data"] = payload["source_data"]
        with pytest.raises(ValueError, match="input identity"):
            validate_portfolio_document(document)
        before = session.api.state_manager.get_plots()
        with pytest.raises(ValueError, match="input identity"):
            session.api.state_manager.restore_session(document)
        assert session.api.state_manager.get_plots() == before
        assert session.drill_down(plot, {"workload": "A"}).row_count == 1


def test_atomic_finalization_rejects_bad_proof_without_changing_either_table() -> None:
    source = pd.DataFrame({"x": ["A", "B"], "y": [1.0, 2.0]})
    with ring5.Session() as session:
        plot = session.create_plot("bar", data=ring5.Table(source), config={"x": "x", "y": "y"})
        before_source, before_output = plot.source_data, plot.processed_data
        changed_source = source.assign(y=[9.0, 8.0])
        bad_output = PipelineService.process_pipeline(source, [], track_source_rows=True)
        with pytest.raises(ValueError, match="input identity"):
            plot.replace_pipeline_data(changed_source, bad_output)
        assert plot.source_data is before_source
        assert plot.processed_data is before_output
        assert session.drill_down(plot, {"x": "A"}).rows.frame["y"].tolist() == [1.0]


def test_unproven_frames_remain_renderable_but_never_claim_raw_contributors() -> None:
    source = pd.DataFrame({"x": ["A"], "y": [1.0]})
    with ring5.Session() as session:
        plot = session.create_plot("bar", data=ring5.Table(source), config={"x": "x", "y": "y"})
        plot.replace_processed_data(source.copy())
        assert plot.processed_data is not None
        assert plot.processed_data.equals(source)
        with pytest.raises(ring5.DataValidationError, match="Insufficient source provenance"):
            session.drill_down(plot, {"x": "A"})
        serialized = plot.to_dict()
        recovered = PlotFactory.from_dict(serialized)
        assert recovered.processed_data is not None
        pd.testing.assert_frame_equal(recovered.processed_data, source)


def test_public_table_transforms_detach_proof_and_new_plots_establish_their_source() -> None:
    from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics

    original = pd.DataFrame({"x": ["B", "A"], "y": [2000.0, 1000.0]})
    proven = PipelineService.process_pipeline(original, [], track_source_rows=True)
    table = ring5.Table(proven)
    with ring5.Session() as session:
        semantic = session.apply_semantics(
            table, DatasetSemantics((ColumnSemantics("y", "Latency", "ns"),))
        )
        results = [
            table.filter_eq("x", "A"),
            table.sort(["x"]),
            table.concat(table),
            table.with_scalar_op("scaled", "y", "*", 2),
            session.shape(table, []),
            semantic,
            session.convert_unit(semantic, "y", "us"),
            session.apply_operation(table, "Sum", "y", "y", "doubled"),
        ]
        for transformed in results:
            assert SOURCE_CONTRIBUTIONS_ATTR not in transformed.frame.attrs
            plot = session.create_plot("bar", data=transformed, config={"x": "x", "y": "y"})
            selected = session.drill_down(plot, {"x": "A"})
            assert selected.row_count >= 1
            assert SOURCE_CONTRIBUTIONS_ATTR not in selected.rows.frame.attrs
        assert SOURCE_CONTRIBUTIONS_ATTR in table.frame.attrs
        session.add_dataset("left", table)
        session.add_dataset("right", table, select=False)
        appended = session.append_datasets(["left", "right"], "appended")
        assert SOURCE_CONTRIBUTIONS_ATTR not in appended.frame.attrs
        assert SOURCE_CONTRIBUTIONS_ATTR not in session.get_dataset("appended").frame.attrs
        joined = session.join_datasets("left", "right", "joined", ["x"])
        assert SOURCE_CONTRIBUTIONS_ATTR not in joined.frame.attrs
        assert SOURCE_CONTRIBUTIONS_ATTR not in session.get_dataset("joined").frame.attrs


def test_public_creation_rejects_unfingerprintable_data_without_registering_a_plot() -> None:
    source = pd.DataFrame({"x": ["A"], "y": [1.0]})
    source.attrs["unsupported"] = object()
    with ring5.Session() as session:
        before = session.api.state_manager.get_plot_counter()
        with pytest.raises(ring5.DataValidationError, match="Invalid plot data"):
            session.create_plot("bar", data=ring5.Table(source), config={"x": "x", "y": "y"})
        assert session.plots == []
        assert session.api.state_manager.get_plot_counter() == before
        assert session.api.state_manager.get_current_plot_id() is None


def test_public_table_admission_rejects_malformed_contribution_metadata() -> None:
    source = pd.DataFrame({"x": ["A"], "y": [1.0]})
    source.attrs[SOURCE_CONTRIBUTIONS_ATTR] = {"version": True}
    with pytest.raises(ring5.DataValidationError, match="contribution metadata"):
        ring5.Table(source)


def test_core_facade_drill_down_owns_nested_source_cells_and_metadata() -> None:
    source = pd.DataFrame({"x": ["A"], "y": [1.0], "notes": [["original"]]})
    source.attrs["notes"] = {"tags": ["source"]}
    with ring5.Session() as session:
        plot = session.create_plot("bar", data=ring5.Table(source), config={"x": "x", "y": "y"})
        result = session.api.drill_down_plot(plot.plot_id, {"x": "A"})
        exposed = result.rows
        exposed.loc[0, "notes"].append("changed")
        exposed.attrs["notes"]["tags"].append("changed")
        again = session.api.drill_down_plot(plot.plot_id, {"x": "A"}).rows
        assert again.loc[0, "notes"] == ["original"]
        assert again.attrs["notes"] == {"tags": ["source"]}


def test_recipe_pipeline_keeps_original_aggregate_sources_and_typed_step_errors(
    tmp_path: Path,
) -> None:
    source = pd.DataFrame({"workload": ["A", "A", "B"], "seed": [0, 1, 0], "ipc": [1.0, 1.2, 0.8]})
    path = tmp_path / "recipe-input.csv"
    source.to_csv(path, index=False)

    def recipe(pipeline: list[dict[str, Any]]) -> ring5.AnalysisRecipe:
        return ring5.AnalysisRecipe(
            name="Original samples",
            source=ring5.RecipeSource(kind="csv", path=str(path)),
            plots=(
                ring5.RecipePlot(
                    name="Aggregate",
                    plot_type="bar",
                    config={"x": "workload", "y": "ipc"},
                    pipeline=tuple(pipeline),
                ),
            ),
        )

    with ring5.Session() as session:
        session.run_analysis_recipe(recipe(_aggregate_pipeline()))
        assert session.drill_down(session.plots[0], {"workload": "A"}).rows.frame[
            "seed"
        ].tolist() == [0, 1]
        existing = session.plots
        with pytest.raises(ring5.PipelineError) as caught:
            session.run_analysis_recipe(recipe([{"type": "columnSelector", "columns": ["absent"]}]))
        assert caught.value.step_index == 0
        assert caught.value.shaper_type == "columnSelector"
        assert session.plots == existing
