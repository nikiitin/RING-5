"""Public creation, persistence, materialization, and execution of analysis recipes."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import ring5
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.parsing_models import StatConfig
from src.core.models.recipe_models import ANALYSIS_RECIPE_SCHEMA_VERSION
from tests.helpers.html_assertions import assert_plotly_document
from src.core.services.data_services.path_service import PathService

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_analysis_recipes")]


def test_recipe_exports_execute_through_only_the_public_api(tmp_path: Path) -> None:
    # [test->req~ring5.automation.script-notebook-export~1]
    csv_path = tmp_path / "automation.csv"
    pd.DataFrame({"benchmark": ["a", "b"], "value": [1.0, 2.0]}).to_csv(csv_path, index=False)
    recipe = ring5.AnalysisRecipe(
        name="Portable automation",
        description="Re-run a reviewed dataset.",
        parameters=(
            ring5.RecipeParameter(
                "input_csv",
                "path",
                description="Input measurements.",
                default=str(csv_path),
            ),
        ),
        source=ring5.RecipeSource(kind="csv", path="{{input_csv}}"),
    )

    with ring5.Session() as session:
        canonical = session.export_analysis_recipe(recipe)
        assert session.decode_analysis_recipe(canonical) == recipe
        script = session.export_analysis_recipe_script(recipe)
        notebook_payload = session.export_analysis_recipe_notebook(recipe)

        with pytest.raises(ring5.RecipeError, match="valid finite UTF-8 JSON"):
            session.decode_analysis_recipe(b"not json")
        with pytest.raises(ring5.RecipeError, match="Analysis recipe must"):
            session.export_analysis_recipe_script("bad")  # type: ignore[arg-type]
        with pytest.raises(ring5.RecipeError, match="Analysis recipe must"):
            session.export_analysis_recipe_notebook("bad")  # type: ignore[arg-type]

    script_path = tmp_path / "portable_automation.py"
    script_path.write_bytes(script)
    completed = subprocess.run(  # noqa: S603
        [sys.executable, str(script_path), "--input-csv", str(csv_path)],
        cwd=Path(__file__).parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {
        "columns": ["benchmark", "value"],
        "exports": [],
        "parameters": {"input_csv": str(csv_path)},
        "plots": [],
        "recipe": "Portable automation",
        "rows": 2,
    }

    notebook = json.loads(notebook_payload)
    namespace: dict[str, object] = {}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            exec(compile(cell["source"], f"{cell['id']}.py", "exec"), namespace)
    result = namespace["result"]
    assert isinstance(result, ring5.AnalysisRecipeRunResult)
    assert result.rows == 2


def test_parameterized_recipe_round_trip_executes_plots_and_exports(tmp_path: Path) -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    csv_path = tmp_path / "measurements.csv"
    pd.DataFrame({"benchmark": ["a", "b", "c"], "value": [1.0, 2.0, 3.0]}).to_csv(
        csv_path, index=False
    )
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    output_dir = tmp_path / "outputs"
    transformation = cast(
        ring5.ShaperStepConfig,
        {
            "type": "conditionSelector",
            "column": "value",
            "mode": "greater_than",
            "threshold": "{{minimum}}",
        },
    )
    recipe = ring5.AnalysisRecipe(
        name="Threshold report",
        description="Filter measurements and export a bar chart.",
        parameters=(
            ring5.RecipeParameter("input_csv", "path", default=str(csv_path)),
            ring5.RecipeParameter("minimum", "number", default=1.5),
            ring5.RecipeParameter("output_dir", "path", default=str(output_dir)),
        ),
        source=ring5.RecipeSource(kind="csv", path="{{input_csv}}"),
        transformations=(transformation,),
        plots=(
            ring5.RecipePlot(
                name="Filtered values",
                plot_type="bar",
                config={"x": "benchmark", "y": "value"},
            ),
        ),
        exports=(
            ring5.RecipeExport(
                plot="Filtered values",
                path="{{output_dir}}/values.html",
                engine="plotly",
                format="html",
            ),
            ring5.RecipeExport(
                plot="Filtered values",
                path="{{output_dir}}/values-copy.html",
                engine="plotly",
                format="html",
            ),
        ),
    )

    with patch.object(PathService, "get_analysis_recipes_dir", return_value=recipes_dir):
        with ring5.Session() as session:
            initial = pd.read_csv(csv_path)
            old_plot = session.create_plot(
                "bar",
                data=ring5.Table(initial),
                config={"x": "benchmark", "y": "value"},
                name="Old plot",
            )
            session.api.set_visualization_config(old_plot.plot_id, MagicMock())
            saved_path = session.save_analysis_recipe(recipe)
            payload = session.export_analysis_recipe(recipe)
            materialized = session.materialize_analysis_recipe(recipe, {"minimum": 2.0})
            result = session.run_analysis_recipe("Threshold report", {"minimum": 2.0})

            assert isinstance(recipe, ring5.AnalysisRecipe)
            assert isinstance(session.list_analysis_recipes()[0], ring5.AnalysisRecipeInfo)
            assert isinstance(result, ring5.AnalysisRecipeRunResult)
            assert Path(saved_path).exists()
            assert payload == session.export_analysis_recipe(
                session.load_analysis_recipe(recipe.name)
            )
            assert (
                materialized.transformations[0]["threshold"] == 2.0
            )  # type: ignore[typeddict-item]
            assert result.rows == 1
            assert result.columns == ("benchmark", "value")
            assert result.plot_names == ("Filtered values",)
            assert result.exported_paths == (
                str(output_dir / "values.html"),
                str(output_dir / "values-copy.html"),
            )
            for path in result.exported_paths:
                assert_plotly_document(Path(path).read_text(encoding="utf-8"))
            assert session.plots[0].pipeline == []
            assert session.api.get_visualization_config(old_plot.plot_id) is None


def test_recipe_capture_and_errors_use_the_public_contract(tmp_path: Path) -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    csv_path = tmp_path / "source.csv"
    pd.DataFrame({"x": ["a"], "y": [1]}).to_csv(csv_path, index=False)
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    with patch.object(PathService, "get_analysis_recipes_dir", return_value=recipes_dir):
        with ring5.Session() as session:
            data = session.load(str(csv_path))
            session.create_plot("bar", data=data, config={"x": "x", "y": "y"}, name="Bars")
            captured = session.capture_analysis_recipe("Captured")

            assert captured.source == ring5.RecipeSource(
                kind="csv",
                path=str(csv_path),
                csv_policy=ring5.InferredCsvPolicy(("benchmark_name", "config_description")),
            )
            assert captured.plots[0].name == "Bars"
            assert captured.plots[0].config == {"x": "x", "y": "y"}

            session.save_analysis_recipe(captured)
            with pytest.raises(ring5.RecipeError, match="already exists"):
                session.save_analysis_recipe(captured)
            with pytest.raises(ring5.RecipeError, match="expects a number"):
                session.materialize_analysis_recipe(
                    ring5.AnalysisRecipe(
                        name="Typed",
                        source=ring5.RecipeSource(kind="csv", path=str(csv_path)),
                        parameters=(ring5.RecipeParameter("limit", "number"),),
                    ),
                    {"limit": "two"},  # type: ignore[dict-item]
                )
            with pytest.raises(ring5.RecipeError, match="not found"):
                session.load_analysis_recipe("missing")

            payload = session.export_analysis_recipe(captured)
            session.delete_analysis_recipe("Captured")
            imported = session.import_analysis_recipe(payload)
            assert imported == captured
            with pytest.raises(ring5.RecipeError, match="not found"):
                session.delete_analysis_recipe("missing")
            with pytest.raises(ring5.RecipeError, match="must be text"):
                session.delete_analysis_recipe(1)  # type: ignore[arg-type]
            with pytest.raises(ring5.RecipeError, match="Analysis recipe must"):
                session.export_analysis_recipe("invalid")  # type: ignore[arg-type]
            future = json.loads(payload)
            future["schema_version"] = ANALYSIS_RECIPE_SCHEMA_VERSION + 1
            with pytest.raises(ring5.RecipeError, match="schema version"):
                session.import_analysis_recipe(json.dumps(future))

        with ring5.Session() as empty_session:
            with pytest.raises(ring5.RecipeError, match="no explicit reusable source"):
                empty_session.capture_analysis_recipe("No source")


def test_parser_recipe_uses_captured_variable_metadata_and_source_errors_are_typed(
    tmp_path: Path,
) -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    inputs = tmp_path / "simulations"
    inputs.mkdir()
    (inputs / "stats.txt").write_text(
        "system.cpu0.simTicks 123\nsystem.cpu.ipc 1.25\n", encoding="utf-8"
    )
    variables = (
        StatConfigCodec.to_payload(
            StatConfig(
                name="simTicks",
                source_name=r"system.cpu\d+.simTicks",
                type="scalar",
                statistics_only=True,
                keep_indices=True,
                params={"source_type": "scalar"},
            )
        ),
        StatConfigCodec.to_payload(
            StatConfig(
                name="ipc",
                type="scalar",
                source_name="system.cpu.ipc",
                params={"source_type": "scalar"},
            )
        ),
    )
    recipe = ring5.AnalysisRecipe(
        name="Parser recipe",
        source=ring5.RecipeSource(
            kind="parser",
            path=str(inputs),
            variables=variables,
            scanned_variables=(
                {
                    "name": r"system.cpu\d+.simTicks",
                    "type": "vector",
                    "entries": ["0"],
                    "source_evidence": {
                        "state": "resolved",
                        "kind": "scalar",
                        "basis": "backend_metadata",
                    },
                    "instances": [{"source_name": "system.cpu0.simTicks", "indices": ["0"]}],
                },
                {
                    "name": "system.cpu.ipc",
                    "type": "scalar",
                    "entries": [],
                    "source_evidence": {
                        "state": "resolved",
                        "kind": "scalar",
                        "basis": "backend_metadata",
                    },
                    "instances": [{"source_name": "system.cpu.ipc", "indices": []}],
                },
            ),
            scan_limit=None,
        ),
    )

    with ring5.Session() as session:
        parser = session.api._parser
        with (
            patch.object(parser, "submit_parse_async", wraps=parser.submit_parse_async) as parse,
            patch.object(parser, "submit_scan_async") as scan,
        ):
            result = session.run_analysis_recipe(recipe)
        scan.assert_not_called()
        submitted = parse.call_args.args[2]
        assert submitted[0].statistics_only is True
        assert submitted[0].keep_indices is True
        assert submitted[1].name == "ipc"
        assert submitted[1].source_name == "system.cpu.ipc"
        assert result.rows == 1
        frame = session.api.state_manager.get_data()
        assert frame is not None
        assert frame.to_dict("records") == [{"system.cpu0.simTicks": 123.0, "ipc": 1.25}]
        assert session.api.state_manager.is_using_parser() is True

        invalid_repeat = ring5.AnalysisRecipe(
            name="Invalid parser metadata",
            source=ring5.RecipeSource(
                kind="parser",
                path="/simulations",
                variables=cast(
                    tuple[dict[str, object], ...],
                    (
                        {
                            **StatConfigCodec.to_payload(
                                StatConfig(
                                    name="x", type="scalar", params={"source_type": "scalar"}
                                )
                            ),
                            "repeat": "many",
                        },
                    ),
                ),  # type: ignore[arg-type]
            ),
        )
        with pytest.raises(ring5.RecipeError, match="repeat must be a positive integer"):
            session.run_analysis_recipe(invalid_repeat)

        csv_recipe = ring5.AnalysisRecipe(
            name="Unreadable source",
            source=ring5.RecipeSource(kind="csv", path="missing.csv"),
        )
        with patch.object(
            session.api.data_services,
            "load_csv_file",
            side_effect=OSError("unreadable"),
        ):
            with pytest.raises(ring5.RecipeError, match="Could not load recipe source"):
                session.run_analysis_recipe(csv_recipe)


@pytest.mark.parametrize("numeric_pattern", [False, True], ids=["literal", "numeric-pattern"])
def test_saved_parser_recipe_replays_complete_catalog_without_rescanning(
    tmp_path: Path, numeric_pattern: bool
) -> None:
    """Replay saved scanner records exactly, including unused physical evidence."""
    # [test->req~ring5.portfolio.analysis-recipes~1]
    inputs = tmp_path / "simulations"
    inputs.mkdir()
    stats = inputs / "stats.txt"
    raw_stats = b"system.cpu0.simTicks 123\n" b"system.cpu1.simTicks 456\n" b"system.cpu.ipc 1.25\n"
    stats.write_bytes(raw_stats)
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    with patch.object(PathService, "get_analysis_recipes_dir", return_value=recipes_dir):
        with ring5.Session() as session:
            discovery = session.scan_submit(str(inputs), limit=0).finalize()
            catalog = [variable.to_dict() for variable in discovery.variables]
            observed = copy.deepcopy(catalog)
            assert discovery.complete and discovery.scanned_files == 1
            assert len(catalog) == 2
            assert {
                instance["source_name"] for record in catalog for instance in record["instances"]
            } == {"system.cpu0.simTicks", "system.cpu1.simTicks", "system.cpu.ipc"}
            variable = ring5.StatConfig(
                name="ticks",
                type="scalar",
                source_name=(
                    r"system.cpu\d+.simTicks" if numeric_pattern else "system.cpu0.simTicks"
                ),
                keep_indices=numeric_pattern,
                params={"source_type": "scalar"},
            )
            recipe = ring5.AnalysisRecipe(
                name="Full saved catalog",
                source=ring5.RecipeSource(
                    kind="parser",
                    path=str(inputs),
                    variables=(StatConfigCodec.to_payload(variable),),
                    scanned_variables=tuple(catalog),
                    scan_limit=0,
                ),
            )
            saved_path = Path(session.save_analysis_recipe(recipe))
            saved_bytes = saved_path.read_bytes()
            loaded = session.load_analysis_recipe(recipe.name)
            expected_source = copy.deepcopy(loaded.source)
            assert loaded == recipe
            assert list(loaded.source.scanned_variables) == observed
            with patch(
                "src.parsing.gem5.impl.gem5_parser.Gem5Parser.submit_scan_async",
                side_effect=AssertionError("Saved recipe replay rescanned"),
            ) as rescan:
                result = session.run_analysis_recipe(loaded)
            rescan.assert_not_called()
            assert result.rows == 1
            frame = session.api.state_manager.get_data()
            assert frame is not None
            expected_row = (
                {"system.cpu0.simTicks": 123.0, "system.cpu1.simTicks": 456.0}
                if numeric_pattern
                else {"ticks": 123.0}
            )
            assert frame.to_dict("records") == [expected_row]
            assert result.columns == tuple(expected_row)
            assert catalog == observed
            assert session.api.state_manager.get_scanned_variables() == observed
            recaptured = session.capture_analysis_recipe("Recaptured full catalog")
            assert recaptured.source == expected_source
            assert session.load_analysis_recipe(recipe.name).source == expected_source

            # Neither caller-owned declarations nor editor drafts own the loaded origin.
            catalog[0]["entries"].append("caller mutation")
            loaded.source.scanned_variables[0]["entries"].append("loaded recipe mutation")
            recaptured.source.scanned_variables[0]["entries"].append("capture mutation")
            session.api.state_manager.set_scanned_variables([])
            assert session.capture_analysis_recipe("Owned origin").source == expected_source
            assert saved_path.read_bytes() == saved_bytes
    assert stats.read_bytes() == raw_stats
