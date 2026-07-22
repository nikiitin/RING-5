"""Deterministic standalone automation generated from analysis recipes."""

from __future__ import annotations

import json

import pytest

from src.core.models import AnalysisRecipe, RecipeParameter, RecipeSource
from src.core.services.analysis_recipe_automation_service import (
    AnalysisRecipeAutomationService,
)


def _parameterized_recipe() -> AnalysisRecipe:
    return AnalysisRecipe(
        name='Review """ | <candidate> results',
        description="Re-run the reviewed analysis.",
        parameters=(
            RecipeParameter("input_path", "path", description="Input CSV."),
            RecipeParameter("label", "string", default="candidate", choices=("candidate", "base")),
            RecipeParameter("count", "integer", default=2),
            RecipeParameter("ratio", "number", default=1.5),
            RecipeParameter("enabled", "boolean", default=True),
        ),
        source=RecipeSource(kind="csv", path="{{input_path}}"),
    )


def test_script_is_deterministic_documented_typed_and_compilable() -> None:
    # [test->req~ring5.automation.script-notebook-export~1]
    recipe = _parameterized_recipe()
    first = AnalysisRecipeAutomationService.export_script(recipe)
    second = AnalysisRecipeAutomationService.export_script(recipe)
    source = first.decode("utf-8")

    assert first == second
    assert source.startswith("#!/usr/bin/env python3")
    assert "from src." not in source
    assert "ring5.Session()" in source
    assert "session.decode_analysis_recipe(RECIPE_JSON)" in source
    assert "session.run_analysis_recipe(recipe, parameters)" in source
    assert "--input-path" in source
    compile(source, "review.py", "exec")

    namespace: dict[str, object] = {"__name__": "generated_recipe"}
    exec(compile(source, "review.py", "exec"), namespace)
    parser = namespace["_build_parser"]()
    values = vars(  # type: ignore[operator]
        parser.parse_args(
            [
                "--input-path",
                "measurements.csv",
                "--count",
                "4",
                "--ratio",
                "2.25",
                "--enabled",
                "no",
            ]
        )
    )
    assert values == {
        "input_path": "measurements.csv",
        "label": "candidate",
        "count": 4,
        "ratio": 2.25,
        "enabled": False,
    }
    assert namespace["_parse_boolean"]("yes") is True  # type: ignore[operator]
    with pytest.raises(SystemExit):
        parser.parse_args(["--input-path", "measurements.csv", "--enabled", "maybe"])


def test_notebook_is_deterministic_safe_and_uses_standard_v4_cells() -> None:
    # [test->req~ring5.automation.script-notebook-export~1]
    recipe = _parameterized_recipe()
    payload = AnalysisRecipeAutomationService.export_notebook(recipe)
    notebook = json.loads(payload)

    assert payload == AnalysisRecipeAutomationService.export_notebook(recipe)
    assert notebook["nbformat"] == 4
    assert notebook["nbformat_minor"] == 5
    assert [cell["id"] for cell in notebook["cells"]] == [
        "ring5-overview",
        "ring5-setup",
        "ring5-parameters",
        "ring5-run",
    ]
    overview = notebook["cells"][0]["source"]
    assert '""" \\| &lt;candidate&gt;' in overview
    assert "only the supported `ring5` Python API" in overview
    assert "'input_path': None" in notebook["cells"][2]["source"]
    assert "REQUIRED: replace None" in notebook["cells"][2]["source"]
    for cell in notebook["cells"][1:]:
        assert "from src." not in cell["source"]
        compile(cell["source"], f"{cell['id']}.py", "exec")


def test_exports_validate_recipes_and_document_recipes_without_parameters() -> None:
    recipe = AnalysisRecipe(name="Simple", source=RecipeSource(kind="csv", path="data.csv"))

    script = AnalysisRecipeAutomationService.export_script(recipe).decode("utf-8")
    notebook = json.loads(AnalysisRecipeAutomationService.export_notebook(recipe))

    assert "# This recipe has no runtime parameters." in script
    assert "This recipe has no runtime parameters." in notebook["cells"][0]["source"]
    with pytest.raises(TypeError, match="Analysis recipe must"):
        AnalysisRecipeAutomationService.export_script("bad")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Analysis recipe must"):
        AnalysisRecipeAutomationService.export_notebook("bad")  # type: ignore[arg-type]
