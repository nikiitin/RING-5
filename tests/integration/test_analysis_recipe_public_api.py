"""Public creation, persistence, materialization, and execution of analysis recipes."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import ring5
from src.core.services.data_services.path_service import PathService

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_analysis_recipes")]


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
                data=initial,
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
            assert all(
                Path(path).read_text().startswith("<html>") for path in result.exported_paths
            )
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

            assert captured.source == ring5.RecipeSource(kind="csv", path=str(csv_path))
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
            with pytest.raises(ring5.RecipeError, match="schema version"):
                session.import_analysis_recipe(
                    payload.replace(b'"schema_version": 1', b'"schema_version": 2')
                )

        with ring5.Session() as empty_session:
            with pytest.raises(ring5.RecipeError, match="no reusable CSV source"):
                empty_session.capture_analysis_recipe("No source")


def test_parser_recipe_uses_captured_variable_metadata_and_source_errors_are_typed(
    tmp_path: Path,
) -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    parsed_csv = tmp_path / "parsed.csv"
    pd.DataFrame({"simTicks": [123]}).to_csv(parsed_csv, index=False)
    variables = cast(
        tuple[dict[str, object], ...],
        (
            {
                "name": "simTicks",
                "type": "scalar",
                "_id": "ticks",
                "repeat": "1",
                "statisticsOnly": True,
                "keepIndices": True,
            },
            {
                "name": "system.cpu.ipc",
                "alias": "ipc",
                "type": "scalar",
                "_id": "ipc",
            },
        ),
    )
    recipe = ring5.AnalysisRecipe(
        name="Parser recipe",
        source=ring5.RecipeSource(
            kind="parser",
            path="/simulations",
            variables=variables,  # type: ignore[arg-type]
        ),
    )

    with ring5.Session() as session:
        with patch.object(
            session,
            "parse",
            return_value=SimpleNamespace(csv_path=str(parsed_csv)),
        ) as parse:
            result = session.run_analysis_recipe(recipe)
        submitted = parse.call_args.args[1]
        assert submitted[0].statistics_only is True
        assert submitted[0].keep_indices is True
        assert submitted[1].name == "ipc"
        assert submitted[1].source_name == "system.cpu.ipc"
        assert result.rows == 1
        assert session.api.state_manager.is_using_parser() is True

        invalid_repeat = ring5.AnalysisRecipe(
            name="Invalid parser metadata",
            source=ring5.RecipeSource(
                kind="parser",
                path="/simulations",
                variables=cast(
                    tuple[dict[str, object], ...],
                    ({"name": "x", "type": "scalar", "repeat": "many"},),
                ),  # type: ignore[arg-type]
            ),
        )
        with pytest.raises(ring5.RecipeError, match="invalid repeat metadata"):
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
