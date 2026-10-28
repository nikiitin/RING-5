"""Typed loads and replay describe the data actually published to the workspace."""

from __future__ import annotations

import json
from collections.abc import Generator
import math
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import ring5
from src.core.models.source_context_models import ParserSourceContext, CsvSourceContext

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("perl_pool")]


@pytest.fixture(autouse=True)
def _private_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    from src.core.services.data_services.path_service import PathService

    PathService.reset_caches()
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "ring5-data"))
    yield
    PathService.reset_caches()


def _active(session: ring5.Session) -> ring5.Table:
    frame = session.api.state_manager.get_data()
    assert frame is not None
    return ring5.Table(frame)


def _stats(path: Path, token: str = "1.25") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "stats.txt").write_text(f"simTicks {token}\n", encoding="utf-8")
    return path


def _variables(literal: str) -> list[ring5.StatConfig]:
    return [
        ring5.StatConfig(
            "value", "scalar", source_name="simTicks", params={"source_type": "scalar"}
        ),
        ring5.StatConfig(
            "label", "configuration", params={"source_type": "configuration", "on_empty": literal}
        ),
    ]


@pytest.mark.parametrize(
    "literal", ["NA", "nan", "NaN", "", "001", "μarch", "  whitespace  ", "95%", "1e400", "-1e-400"]
)
def test_real_parser_typed_load_portfolio_and_recipe_preserve_literal_cells(
    tmp_path: Path, literal: str
) -> None:
    source = _stats(tmp_path / "inputs")
    with ring5.Session() as session:
        result = session.parse(str(source), _variables(literal), scan_limit=0)
        table = session.load(result)
        assert table.rows() == [{"value": 1.25, "label": literal}]
        # A later editor draft cannot reinterpret typed numeric output as text.
        session.api.state_manager.set_parse_variables(
            [
                {
                    "name": "value",
                    "type": "configuration",
                    "params": {"source_type": "configuration", "on_empty": "other"},
                }
            ]
        )
        assert session.load(result).rows() == table.rows()
        assert _active(session).frame["value"].dtype.kind == "f"
        captured = session.capture_analysis_recipe("typed")
        assert captured.source.variables[1]["params"]["on_empty"] == literal
        session.save_portfolio("typed")
        session.load(str(result.csv_path))  # Explicit genuine CSV inference is a separate request.
        session.load_portfolio("typed")
        assert _active(session).rows() == table.rows()
        with patch(
            "src.parsing.gem5.impl.gem5_parser.Gem5Parser.submit_scan_async",
            side_effect=AssertionError("Recipe rescanned"),
        ):
            session.run_analysis_recipe(captured)
        assert _active(session).rows() == table.rows()
        assert session.capture_analysis_recipe("recaptured").source == captured.source


@pytest.mark.parametrize("token", ["nan", "inf", "-inf", "0", "5e-324"])
def test_numeric_cells_remain_numeric_and_strict_missing_uses_owned_variable_kinds(
    tmp_path: Path, token: str
) -> None:
    source = _stats(tmp_path / "inputs", token)
    with ring5.Session() as session:
        result = session.parse(str(source), _variables("NaN"), strict=False)
        table = session.load(result)
        value = table.rows()[0]["value"]
        assert type(value) is float
        assert table.rows()[0]["label"] == "NaN"
        if token == "nan":
            assert math.isnan(value)
            assert result.missing_stats == ("value",)
            with pytest.raises(ring5.MissingStatError):
                session.parse(str(source), _variables("NaN"), strict=True)
        else:
            assert value == float(token)
            assert result.missing_stats == ()


def test_submit_without_load_and_failed_load_preserve_active_source_recipe(tmp_path: Path) -> None:
    first = _stats(tmp_path / "first", "1.25")
    second = _stats(tmp_path / "second", "9.5")
    with ring5.Session() as session:
        loaded = session.parse(str(first), _variables("001"), scan_limit=0, strict=False)
        expected = session.load(loaded)
        unloaded = session.parse(str(second), _variables("NA"), scan_limit=1)
        assert _active(session).rows() == expected.rows()
        captured = session.capture_analysis_recipe("active")
        assert captured.source.path == str(first)
        assert captured.source.scan_limit == 0
        assert captured.source.strict is False
        Path(unloaded.csv_path).write_text("tampered", encoding="utf-8")
        with pytest.raises(ring5.DataLoadError):
            session.load(unloaded)
        assert _active(session).rows() == expected.rows()
        assert session.capture_analysis_recipe("still-active").source == captured.source
        from dataclasses import replace

        state = session.api.state_manager
        before_editor = (
            state.get_stats_path(),
            state.get_parse_variables(),
            state.get_scanned_variables(),
        )
        before_origin = state.get_loaded_origin()
        invalid = replace(
            captured,
            source=replace(captured.source, path=str(second)),
            transformations=({"type": "columnSelector", "columns": ["not-a-real-column"]},),
        )
        with pytest.raises(ring5.PipelineError):
            session.run_analysis_recipe(invalid)
        assert _active(session).rows() == expected.rows()
        assert state.get_loaded_origin() is before_origin
        assert (
            state.get_stats_path(),
            state.get_parse_variables(),
            state.get_scanned_variables(),
        ) == before_editor
        session.run_analysis_recipe(captured)
        assert _active(session).rows() == expected.rows()
        assert state.get_stats_path() == str(first)
        assert state.get_stats_pattern() == captured.source.pattern
        assert state.get_parser_strategy() == captured.source.strategy
        assert state.get_simulator() == captured.source.simulator
        retained_origin = state.get_loaded_origin()
        assert retained_origin is not None and isinstance(
            retained_origin.source, ParserSourceContext
        )
        assert json.loads(retained_origin.source.variables_json) == list(captured.source.variables)
        assert state.get_scanned_variables() == list(captured.source.scanned_variables)
        state.set_stats_path("a-later-unloaded-editor-request")
        assert session.capture_analysis_recipe("after-editor-change").source == captured.source


def test_recipe_retains_executed_pipeline_once_and_explicit_source_uses_only_caller_steps(
    tmp_path: Path,
) -> None:
    path = tmp_path / "source.csv"
    path.write_text("label,a,b\noriginal,1,2\n", encoding="utf-8")
    # A repeated non-idempotent step exposes accidental pipeline duplication.
    first = {
        "type": "deriveColumn",
        "dest": "a",
        "op": "scalar",
        "sources": ["a"],
        "scalar": 1.0,
        "scalar_op": "+",
    }
    recipe = ring5.AnalysisRecipe(
        "initial", ring5.RecipeSource("csv", str(path)), transformations=(first,)
    )
    with ring5.Session() as session:
        session.run_analysis_recipe(recipe)
        assert _active(session).rows()[0]["a"] == 2
        captured = session.capture_analysis_recipe("captured")
        assert captured.transformations == (first,)
        session.run_analysis_recipe(captured)
        assert _active(session).rows()[0]["a"] == 2
        extra = session.capture_analysis_recipe("additional", transformations=[first])
        assert extra.transformations == (first, first)
        session.run_analysis_recipe(extra)
        assert _active(session).rows()[0]["a"] == 3
        explicit = session.capture_analysis_recipe("explicit", source=recipe.source)
        assert explicit.transformations == ()


def test_reviewed_import_parameterized_recipe_replays_actual_options_and_rejected_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reviewed.csv"
    path.write_text(
        "ignored\nlabel;value\nNA;1\nnan;2\n;3\n001;4\nμ;5\n  whitespace  ;6\n95%;7\nreject;bad\n",
        encoding="utf-8",
    )
    options = ring5.ImportOptions(
        encoding="utf-8",
        delimiter=";",
        header_row=2,
        trim_whitespace=False,
        null_values=("MISSING",),
        column_types=(
            ring5.ImportColumnCorrection("label", "text"),
            ring5.ImportColumnCorrection("value", "integer"),
        ),
    )
    with ring5.Session() as session:
        preview = session.preview_import(
            str(path),
            encoding=options.encoding,
            delimiter=options.delimiter,
            header_row=options.header_row,
            trim_whitespace=options.trim_whitespace,
            null_values=options.null_values,
            column_types={
                correction.column: correction.import_as for correction in options.column_types
            },
        )
        assert preview.rejected_row_count == 1
        expected = session.load_import(preview)
        assert [row["label"] for row in expected.rows()] == [
            "NA",
            "nan",
            "",
            "001",
            "μ",
            "  whitespace  ",
            "95%",
        ]
        captured = session.capture_analysis_recipe("reviewed")
        assert captured.source.csv_policy == ring5.ReviewedCsvPolicy(options)
        from dataclasses import replace

        parameterized = replace(
            captured,
            source=replace(captured.source, path="{{source_path}}"),
            parameters=(ring5.RecipeParameter("source_path", "path", default=str(path)),),
        )
        session.api.state_manager.set_parse_variables(
            [{"name": "value", "type": "configuration", "params": {"source_type": "configuration"}}]
        )
        session.run_analysis_recipe(
            session.decode_analysis_recipe(session.export_analysis_recipe(parameterized))
        )
        pd.testing.assert_frame_equal(_active(session).frame, expected.frame)
        wire = json.loads(session.export_analysis_recipe(parameterized))
        from src.core.models.recipe_models import ANALYSIS_RECIPE_SCHEMA_VERSION

        assert wire["schema_version"] == ANALYSIS_RECIPE_SCHEMA_VERSION
        assert wire["source"]["csv_policy"]["rejected_rows"] == "exclude"
        path.write_text("ignored\nlabel;value\nreject;bad\n", encoding="utf-8")
        with pytest.raises(ring5.RecipeError):
            session.run_analysis_recipe(parameterized)
        pd.testing.assert_frame_equal(_active(session).frame, expected.frame)
        assert (
            session.capture_analysis_recipe("unchanged").source.csv_policy
            == captured.source.csv_policy
        )


def test_plain_csv_recipe_retains_ingestion_configuration_columns_after_editor_changes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "source.csv"
    path.write_text("label,numeric\n001,1.25\n", encoding="utf-8")
    with ring5.Session() as session:
        session.api.state_manager.set_parse_variables(
            [
                {
                    "name": "numeric",
                    "type": "configuration",
                    "params": {"source_type": "configuration"},
                }
            ]
        )
        expected = session.load(str(path))
        captured = session.capture_analysis_recipe("actual-csv")
        assert captured.source.csv_policy == ring5.InferredCsvPolicy(("numeric",))
        session.api.state_manager.set_parse_variables([])
        session.run_analysis_recipe(captured)
        pd.testing.assert_frame_equal(_active(session).frame, expected.frame)
        # Explicit Table publication cannot inherit the previous file's replay claim.
        session.api.state_manager.set_data(expected.frame)
        with pytest.raises(ring5.RecipeError, match="explicit reusable source"):
            session.capture_analysis_recipe("arbitrary-table")


def test_table_and_confirmed_preview_publish_exact_types_and_clear_uncaptured_origin(
    tmp_path: Path,
) -> None:
    source = _stats(tmp_path / "inputs")
    with ring5.Session() as session:
        session.load(session.parse(str(source), _variables("NA")))
        session.api.add_current_dataset("original")
        session.api.state_manager.set_parse_variables(
            [
                {
                    "name": "value",
                    "type": "configuration",
                    "params": {"source_type": "configuration"},
                }
            ]
        )
        inputs = session.api.capture_preview_inputs()
        preview = pd.DataFrame({"value": [2.5], "label": ["NA"]})
        config = {"factor": 2.0}
        session.api.set_preview("scale", preview, operation_config=config, inputs=inputs)
        confirmed = session.api.confirm_preview(
            "scale", operation_config=config, operation="Scale value"
        )
        assert confirmed["value"].dtype.kind == "f"
        assert _active(session).rows() == [{"value": 2.5, "label": "NA"}]
        with pytest.raises(ring5.RecipeError, match="explicit reusable source"):
            session.capture_analysis_recipe("edited")
        session.undo_dataset()
        assert session.capture_analysis_recipe("restored").source.kind == "parser"
        assert _active(session).rows() == [{"value": 1.25, "label": "NA"}]
        session.redo_dataset()
        with pytest.raises(ring5.RecipeError, match="explicit reusable source"):
            session.capture_analysis_recipe("edited-again")
        session.add_dataset("table", ring5.Table.from_rows([{"value": 3.5}]))
        assert session.get_dataset("table").frame["value"].dtype.kind == "f"
        assert session.get_dataset("table").rows() == [{"value": 3.5}]


def test_large_csv_configuration_policy_loads_tiny_frame_and_capture_budget_is_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.services.data_services import analysis_recipe_service

    path = tmp_path / "tiny.csv"
    path.write_text("value\n1.25\n", encoding="utf-8")
    names = ("value", *(f"unloaded_column_{index}" for index in range(2048)))
    with ring5.Session() as session:
        session.api.state_manager.set_parse_variables(
            [
                {"name": name, "type": "configuration", "params": {"source_type": "configuration"}}
                for name in names
            ]
        )
        loaded = session.load(str(path))
        assert loaded.rows() == [{"value": "1.25"}]
        assert len(loaded) == 1
        assert loaded.columns() == ["value"]
        origin = session.api.state_manager.get_loaded_origin()
        assert origin is not None and isinstance(origin.source, CsvSourceContext)
        assert isinstance(origin.source.policy, ring5.InferredCsvPolicy)
        assert origin.source.policy.configuration_columns == names
        captured = session.capture_analysis_recipe("many-columns")
        assert isinstance(captured.source.csv_policy, ring5.InferredCsvPolicy)
        assert captured.source.csv_policy.configuration_columns == names
        policy_size = len(json.dumps({"configuration_columns": names}).encode("utf-8"))
        monkeypatch.setattr(analysis_recipe_service, "MAX_ANALYSIS_RECIPE_BYTES", policy_size // 2)
        with pytest.raises(ring5.RecipeError, match="budget"):
            session.capture_analysis_recipe("over-serialization-budget")
        pd.testing.assert_frame_equal(_active(session).frame, loaded.frame)
        assert session.api.state_manager.get_loaded_origin() is origin


def test_observed_evidence_and_declared_geometry_survive_source_recipe_and_editor_roundtrip(
    tmp_path: Path,
) -> None:
    from src.core.common.source_context_codec import SourceContextCodec

    inputs = tmp_path / "distribution"
    inputs.mkdir()
    (inputs / "stats.txt").write_text(
        "d::underflows 0\nd::-2 1 33% 33%\nd::4 2 67% 100%\nd::overflows 0\n",
        encoding="utf-8",
    )
    with ring5.Session() as session:
        scan = session.scan(str(inputs), limit=0)
        observed = next(v.to_dict() for v in scan.variables if v.name == "d")
        assert observed["type"] is None
        assert observed["source_evidence"] == {
            "state": "ambiguous",
            "candidates": ["distribution", "vector"],
        }
        assert "minimum" not in observed and "maximum" not in observed
        parsed = session.parse(
            str(inputs),
            [
                ring5.StatConfig(
                    "d",
                    "distribution",
                    params={
                        "source_type": "distribution",
                        "minimum": -2.0,
                        "maximum": 4.0,
                        "bucket_size": 1,
                        "zero_policy": "missing",
                    },
                )
            ],
            scan_limit=0,
        )
        session.load(parsed)
        assert SourceContextCodec.scanned_payloads(parsed.source_context) == [observed]
        assert (
            SourceContextCodec.decode(SourceContextCodec.encode(parsed.source_context))
            == parsed.source_context
        )
        recipe = session.capture_analysis_recipe("bounded-distribution")
        assert recipe.source.scanned_variables == (observed,)
        assert recipe.source.variables[0]["params"]["minimum"] == -2.0
        assert recipe.source.variables[0]["params"]["maximum"] == 4.0
        with patch(
            "src.parsing.gem5.impl.gem5_parser.Gem5Parser.submit_scan_async",
            side_effect=AssertionError("Recipe rescanned"),
        ):
            session.run_analysis_recipe(
                session.decode_analysis_recipe(session.export_analysis_recipe(recipe))
            )
        assert session.api.state_manager.get_scanned_variables() == [observed]
        session.api.state_manager.set_scanned_variables([])
        assert session.capture_analysis_recipe("origin-retained").source.scanned_variables == (
            observed,
        )


def test_unobserved_dynamic_entry_variable_loads_one_row_without_invented_bucket(
    tmp_path: Path,
) -> None:
    source = _stats(tmp_path / "inputs")
    variable = ring5.StatConfig("unobserved", "histogram", params={"source_type": "histogram"})
    with ring5.Session() as session:
        result = session.parse(str(source), [variable], strict=False)
        assert result.missing_stats == ("unobserved",)
        assert result.output.schema.variables[0].shape == "entries"
        assert result.output.schema.columns == ()
        table = session.load(result)
        assert len(table) == 1
        assert table.columns() == []
        assert table.rows() == [{}]


def test_public_parse_projects_real_large_discovery_and_replays_complete_selected_records(
    tmp_path: Path,
) -> None:
    from src.core.common.source_context_codec import SourceContextCodec
    from src.core.services.parse_job_store import MAX_REQUEST_JSON_BYTES

    inputs = _stats(tmp_path / "inputs")
    stats = inputs / "stats.txt"
    original = (
        "simTicks 1.25\n"
        + "".join(f"unused::entry{index:05d}_" + "x" * 250 + " 1\n" for index in range(5000))
    ).encode("utf-8")
    stats.write_bytes(original)
    with ring5.Session() as session:
        discovery = session.scan(str(inputs), limit=0)
        catalog = [value.to_dict() for value in discovery.variables]
        assert discovery.complete and discovery.scanned_files == 1
        assert len(json.dumps(catalog).encode("utf-8")) > MAX_REQUEST_JSON_BYTES
        expected = [record for record in catalog if record["name"] == "simTicks"]
        assert len(expected) == 1
        result = session.parse(str(inputs), _variables("001"), scan_limit=0)
        assert SourceContextCodec.scanned_payloads(result.source_context) == expected
        table = session.load(result)
        assert table.rows() == [{"value": 1.25, "label": "001"}]
        captured = session.capture_analysis_recipe("selected")
        assert list(captured.source.scanned_variables) == expected
        assert (
            SourceContextCodec.from_payload(SourceContextCodec.to_payload(result.source_context))
            == result.source_context
        )
        with patch(
            "src.parsing.gem5.impl.gem5_parser.Gem5Parser.submit_scan_async",
            side_effect=AssertionError("Exact saved execution snapshot rescanned"),
        ):
            session.run_analysis_recipe(captured)
        assert _active(session).rows() == table.rows()
        assert session.capture_analysis_recipe("replayed").source == captured.source
        session.save_portfolio("selected")
        session.load_portfolio("selected")
        assert _active(session).rows() == table.rows()
        assert session.capture_analysis_recipe("restored").source == captured.source
    assert stats.read_bytes() == original
