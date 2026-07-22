"""Bounded deterministic execution of analysis-recipe parameter matrices."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from src.core.models import (
    AnalysisRecipe,
    AnalysisRecipeRunResult,
    RecipeExport,
    RecipeParameter,
    RecipePlot,
    RecipeSource,
)
from src.core.services.analysis_recipe_matrix_service import AnalysisRecipeMatrixService


def _recipe() -> AnalysisRecipe:
    return AnalysisRecipe(
        name="Matrix review",
        parameters=(
            RecipeParameter("input_csv", "path"),
            RecipeParameter("threshold", "number", default=1.0),
            RecipeParameter("enabled", "boolean", default=True),
        ),
        source=RecipeSource(kind="csv", path="{{input_csv}}"),
        plots=(RecipePlot(name="Values", plot_type="bar", config={}),),
        exports=(
            RecipeExport(
                plot="Values",
                path="reports/{{threshold}}/values.html",
                engine="plotly",
                format="html",
            ),
        ),
    )


def test_prepare_uses_recipe_order_stable_ids_and_collision_free_exports(tmp_path: Path) -> None:
    # [test->req~ring5.automation.batch-matrices~1]
    matrix = {"threshold": [1.0, 2.0], "input_csv": ["a.csv", "b.csv"]}

    first = AnalysisRecipeMatrixService.prepare(
        _recipe(), matrix, str(tmp_path / "out"), max_workers=2
    )
    second = AnalysisRecipeMatrixService.prepare(
        _recipe(), matrix, str(tmp_path / "out"), max_workers=2
    )

    assert first == second
    assert [case.parameter_values for case in first] == [
        (("input_csv", "a.csv"), ("threshold", 1.0), ("enabled", True)),
        (("input_csv", "a.csv"), ("threshold", 2.0), ("enabled", True)),
        (("input_csv", "b.csv"), ("threshold", 1.0), ("enabled", True)),
        (("input_csv", "b.csv"), ("threshold", 2.0), ("enabled", True)),
    ]
    assert all(case.case_id.startswith(f"case-{index:03d}-") for index, case in enumerate(first, 1))
    assert len({case.case_id for case in first}) == 4
    assert first[0].recipe.source.path == "a.csv"
    assert first[0].recipe.exports[0].path == str(
        tmp_path / "out" / first[0].case_id / "01-values.html"
    )


def test_execute_is_bounded_ordered_and_retains_per_case_failures(tmp_path: Path) -> None:
    # [test->req~ring5.automation.batch-matrices~1]
    barrier = threading.Barrier(2)
    lock = threading.Lock()
    active = 0
    maximum_active = 0

    def runner(recipe: AnalysisRecipe, values: dict[str, object]) -> AnalysisRecipeRunResult:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        barrier.wait(timeout=2)
        with lock:
            active -= 1
        if values["threshold"] == 2.0:
            raise RuntimeError("failed\ncase")
        return AnalysisRecipeRunResult(
            recipe_name=recipe.name,
            parameter_values=tuple(values.items()),  # type: ignore[arg-type]
            rows=1,
            columns=("value",),
            exported_paths=tuple(export.path for export in recipe.exports),
        )

    result = AnalysisRecipeMatrixService.execute(
        _recipe(),
        {"input_csv": ["a.csv"], "threshold": [1.0, 2.0]},
        str(tmp_path),
        runner,  # type: ignore[arg-type]
        max_workers=2,
    )

    assert maximum_active == 2
    assert [dict(case.parameter_values)["threshold"] for case in result.cases] == [1.0, 2.0]
    assert result.complete is False
    assert result.completed_cases == 1
    assert result.failed_cases == 1
    assert result.cases[0].successful is True
    assert result.cases[1].successful is False
    assert result.cases[1].error == "failed\\ncase"


@pytest.mark.parametrize(
    ("matrix", "message"),
    [
        ({"unknown": [1]}, "Unknown"),
        ({"input_csv": "a.csv"}, "must be a sequence"),
        ({"input_csv": []}, "has no values"),
        ({"input_csv": ["a.csv", "a.csv"]}, "duplicate values"),
        ({"input_csv": [1]}, "expects a path"),
        ({"threshold": [1.0]}, "input_csv.*required"),
    ],
)
def test_prepare_rejects_invalid_matrices(tmp_path: Path, matrix: object, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        AnalysisRecipeMatrixService.prepare(
            _recipe(), matrix, str(tmp_path)  # type: ignore[arg-type]
        )


def test_prepare_enforces_case_worker_and_path_bounds(tmp_path: Path) -> None:
    recipe = AnalysisRecipe(
        name="Integer matrix",
        source=RecipeSource(kind="csv", path="data.csv"),
        parameters=(RecipeParameter("value", "integer", default=0),),
    )
    with pytest.raises(ValueError, match="256"):
        AnalysisRecipeMatrixService.prepare(recipe, {"value": list(range(257))}, str(tmp_path))
    with pytest.raises(ValueError, match="parameter limit"):
        AnalysisRecipeMatrixService.prepare(
            recipe,
            {f"value{index}": [index] for index in range(33)},
            str(tmp_path),
        )
    with pytest.raises(TypeError, match="must be an integer"):
        AnalysisRecipeMatrixService.prepare(recipe, {}, str(tmp_path), max_workers=True)
    with pytest.raises(ValueError, match="between 1 and 8"):
        AnalysisRecipeMatrixService.prepare(recipe, {}, str(tmp_path), max_workers=0)
    with pytest.raises(TypeError, match="must be text"):
        AnalysisRecipeMatrixService.prepare(recipe, {}, tmp_path)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty valid path"):
        AnalysisRecipeMatrixService.prepare(recipe, {}, "\n")
    with pytest.raises(ValueError, match="too long"):
        AnalysisRecipeMatrixService.prepare(recipe, {}, "x" * 10_001)
    with pytest.raises(TypeError, match="must be callable"):
        AnalysisRecipeMatrixService.execute(
            recipe, {}, str(tmp_path), None  # type: ignore[arg-type]
        )


def test_execute_rejects_invalid_runner_results(tmp_path: Path) -> None:
    recipe = AnalysisRecipe(name="Simple", source=RecipeSource(kind="csv", path="data.csv"))
    result = AnalysisRecipeMatrixService.execute(
        recipe,
        {},
        str(tmp_path),
        lambda _recipe, _values: object(),  # type: ignore[return-value]
    )

    assert result.failed_cases == 1
    assert result.cases[0].error == "Analysis recipe matrix runner returned an invalid result."
