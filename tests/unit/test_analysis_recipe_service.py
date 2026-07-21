"""Analysis-recipe validation, materialization, capture, and storage tests."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import (
    AnalysisRecipe,
    RecipeExport,
    RecipeParameter,
    RecipePlot,
    RecipeSource,
    ShaperStepConfig,
)
from src.core.services.data_services.analysis_recipe_service import (
    ANALYSIS_RECIPE_FORMAT,
    AnalysisRecipeService,
)
from src.core.services.data_services.path_service import PathService


@pytest.fixture
def recipes_dir(tmp_path: Path) -> Generator[Path, None, None]:
    directory = tmp_path / "analysis_recipes"
    directory.mkdir()
    with patch.object(PathService, "get_analysis_recipes_dir", return_value=directory):
        yield directory


def _recipe() -> AnalysisRecipe:
    transformations = cast(
        tuple[ShaperStepConfig, ...],
        (
            {
                "type": "conditionSelector",
                "column": "value",
                "mode": "greater_than",
                "threshold": "{{minimum}}",
            },
        ),
    )
    return AnalysisRecipe(
        name="Parameterized comparison",
        description="Build the filtered value plot.",
        parameters=(
            RecipeParameter("input_csv", "path", default="data.csv"),
            RecipeParameter("minimum", "number", default=1.5),
            RecipeParameter("output_dir", "path", default="out"),
            RecipeParameter("label", "string", default="Reviewed"),
        ),
        source=RecipeSource(kind="csv", path="{{input_csv}}"),
        transformations=transformations,
        plots=(
            RecipePlot(
                name="Values",
                plot_type="bar",
                config={"x": "category", "y": "value", "title": "{{label}} values"},
            ),
        ),
        exports=(
            RecipeExport(
                plot="Values",
                path="{{output_dir}}/values.html",
                engine="plotly",
                format="html",
            ),
        ),
    )


def test_recipe_json_is_deterministic_versioned_and_materializes_typed_values() -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    recipe = _recipe()
    first = AnalysisRecipeService.dumps(recipe)
    second = AnalysisRecipeService.dumps(recipe)
    restored = AnalysisRecipeService.loads(first)
    materialized = AnalysisRecipeService.materialize(
        restored,
        {
            "input_csv": "/data/run.csv",
            "minimum": 2.25,
            "output_dir": "/tmp/report",
            "label": "Candidate",
        },
    )

    assert first == second
    assert json.loads(first)["format"] == ANALYSIS_RECIPE_FORMAT
    assert restored == recipe
    assert materialized.source.path == "/data/run.csv"
    assert materialized.transformations[0]["threshold"] == 2.25  # type: ignore[typeddict-item]
    assert materialized.plots[0].config["title"] == "Candidate values"
    assert materialized.exports[0].path == "/tmp/report/values.html"


def test_recipe_rejects_undeclared_mistyped_and_future_content() -> None:
    recipe = _recipe()
    with pytest.raises(TypeError, match="expects a number"):
        AnalysisRecipeService.materialize(recipe, {"minimum": "2"})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="Unknown analysis recipe parameters"):
        AnalysisRecipeService.materialize(recipe, {"extra": 2})

    invalid = json.loads(AnalysisRecipeService.dumps(recipe))
    invalid["schema_version"] = 2
    with pytest.raises(ValueError, match="schema version"):
        AnalysisRecipeService.loads(json.dumps(invalid))
    invalid["schema_version"] = 1
    invalid["future"] = True
    with pytest.raises(ValueError, match="unsupported fields"):
        AnalysisRecipeService.loads(json.dumps(invalid))

    undeclared = AnalysisRecipe(
        name="Bad",
        source=RecipeSource(kind="csv", path="{{missing}}"),
    )
    with pytest.raises(ValueError, match="undeclared parameters"):
        AnalysisRecipeService.dumps(undeclared)

    with pytest.raises(ValueError, match="non-empty valid path"):
        AnalysisRecipeService.materialize(recipe, {"input_csv": ""})

    invalid_export = AnalysisRecipe(
        name="Bad export",
        source=RecipeSource(kind="csv", path="data.csv"),
        plots=(RecipePlot(name="Plot", plot_type="bar", config={}),),
        exports=(RecipeExport(plot="Plot", path="plot.json", engine="plotly", format="json"),),
    )
    with pytest.raises(ValueError, match="not supported for plotly"):
        AnalysisRecipeService.dumps(invalid_export)

    duplicate_exports = AnalysisRecipe(
        name="Duplicate exports",
        source=RecipeSource(kind="csv", path="data.csv"),
        plots=(RecipePlot(name="Plot", plot_type="bar", config={}),),
        exports=(
            RecipeExport(plot="Plot", path="plot.pdf"),
            RecipeExport(plot="Plot", path="plot.pdf"),
        ),
    )
    with pytest.raises(ValueError, match="Duplicate recipe export path"):
        AnalysisRecipeService.dumps(duplicate_exports)

    malformed_schema = AnalysisRecipe(
        name="Bad schema",
        source=RecipeSource(kind="csv", path="data.csv"),
        schema_version=True,  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="schema version must be an integer"):
        AnalysisRecipeService.dumps(malformed_schema)

    malformed_plot = AnalysisRecipe(
        name="Bad plot",
        source=RecipeSource(kind="csv", path="data.csv"),
        plots=({"name": "Plot"},),  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="must be RecipePlot"):
        AnalysisRecipeService.dumps(malformed_plot)

    cyclic_step = cast(ShaperStepConfig, {"type": "columnSelector"})
    cyclic_step["cycle"] = cyclic_step  # type: ignore[typeddict-unknown-key]
    cyclic_recipe = AnalysisRecipe(
        name="Cyclic",
        source=RecipeSource(kind="csv", path="data.csv"),
        transformations=(cyclic_step,),
    )
    with pytest.raises(ValueError, match="nesting is too deep"):
        AnalysisRecipeService.dumps(cyclic_recipe)


def test_recipe_storage_protects_names_and_lists_valid_records(recipes_dir: Path) -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    recipe = _recipe()
    path = AnalysisRecipeService.save(recipe)

    with pytest.raises(FileExistsError, match="already exists"):
        AnalysisRecipeService.save(recipe)
    (recipes_dir / "corrupt.json").write_text("not json")
    entries = AnalysisRecipeService.list()

    assert len(entries) == 1
    assert entries[0].name == recipe.name
    assert entries[0].parameters == 4
    assert AnalysisRecipeService.load(recipe.name) == recipe
    assert Path(path).exists()

    first_collision = AnalysisRecipe(
        name="slash/name",
        source=RecipeSource(kind="csv", path="data.csv"),
    )
    second_collision = AnalysisRecipe(
        name="slash_name",
        source=RecipeSource(kind="csv", path="data.csv"),
    )
    first_path = AnalysisRecipeService.save(first_collision)
    second_path = AnalysisRecipeService.save(second_collision)
    assert first_path != second_path
    assert AnalysisRecipeService.load(first_collision.name) == first_collision
    assert AnalysisRecipeService.load(second_collision.name) == second_collision

    AnalysisRecipeService.delete(recipe.name)
    with pytest.raises(FileNotFoundError, match="not found"):
        AnalysisRecipeService.load(recipe.name)


def test_capture_retains_parser_variables_plot_configs_and_pipelines() -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    state = MagicMock()
    state.is_using_parser.return_value = True
    state.get_stats_path.return_value = "/simulations"
    state.get_stats_pattern.return_value = "stats*.txt"
    state.get_parser_strategy.return_value = "simple"
    state.get_parse_variables.return_value = [
        {"name": "simTicks", "type": "scalar", "_id": "ticks"}
    ]
    state.get_scanned_variables.return_value = [
        {"name": "simTicks", "type": "scalar", "entries": []}
    ]
    plot = MagicMock()
    plot.name = "Ticks"
    plot.plot_type = "bar"
    plot.config = {"x": "benchmark", "y": "simTicks"}
    plot.pipeline = [
        {
            "id": 4,
            "type": "columnSelector",
            "config": {
                "type": "columnSelector",
                "columns": ["benchmark", "simTicks"],
            },
        }
    ]
    state.get_plots.return_value = [plot]

    recipe = AnalysisRecipeService(state).capture("Ticks recipe")

    assert recipe.source.kind == "parser"
    assert recipe.source.variables[0]["name"] == "simTicks"
    assert recipe.source.scanned_variables[0]["entries"] == []
    assert recipe.plots[0].config == {"x": "benchmark", "y": "simTicks"}
    assert recipe.plots[0].pipeline[0]["type"] == "columnSelector"


def test_capture_requires_reusable_source_provenance() -> None:
    state = MagicMock()
    state.is_using_parser.return_value = False
    state.get_csv_path.return_value = None
    state.get_plots.return_value = []

    with pytest.raises(ValueError, match="no reusable CSV source"):
        AnalysisRecipeService(state).capture("Missing source")
