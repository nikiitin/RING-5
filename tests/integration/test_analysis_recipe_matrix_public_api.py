"""Public bounded-concurrency execution of typed analysis-recipe matrices."""

from __future__ import annotations

import time
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pandas as pd
import pytest

import ring5
from src.core.services.data_services.path_service import PathService

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_analysis_recipes")]


def _matrix_recipe() -> ring5.AnalysisRecipe:
    transformation = cast(
        ring5.ShaperStepConfig,
        {
            "type": "conditionSelector",
            "column": "value",
            "mode": "greater_than",
            "threshold": "{{minimum}}",
        },
    )
    return ring5.AnalysisRecipe(
        name="Matrix report",
        parameters=(
            ring5.RecipeParameter("input_csv", "path"),
            ring5.RecipeParameter("minimum", "number", default=0.0),
        ),
        source=ring5.RecipeSource(kind="csv", path="{{input_csv}}"),
        transformations=(transformation,),
        plots=(
            ring5.RecipePlot(
                name="Values",
                plot_type="bar",
                config={"x": "benchmark", "y": "value"},
            ),
        ),
        exports=(
            ring5.RecipeExport(
                plot="Values",
                path="same-name.html",
                engine="plotly",
                format="html",
            ),
        ),
    )


def test_matrix_runs_in_stable_order_with_collision_free_outputs(tmp_path: Path) -> None:
    # [test->req~ring5.automation.batch-matrices~1]
    first_csv = tmp_path / "first.csv"
    second_csv = tmp_path / "second.csv"
    pd.DataFrame({"benchmark": ["a", "b"], "value": [1.0, 2.0]}).to_csv(first_csv, index=False)
    pd.DataFrame({"benchmark": ["c", "d", "e"], "value": [1.0, 2.0, 3.0]}).to_csv(
        second_csv, index=False
    )
    matrix = {
        "minimum": [0.0, 1.5],
        "input_csv": [str(first_csv), str(second_csv)],
    }

    with ring5.Session() as session:
        result = session.run_analysis_recipe_matrix(
            _matrix_recipe(),
            matrix,
            output_directory=str(tmp_path / "outputs"),
            max_workers=2,
        )
        repeated = session.run_analysis_recipe_matrix(
            _matrix_recipe(),
            matrix,
            output_directory=str(tmp_path / "repeated"),
            max_workers=1,
        )

    assert isinstance(result, ring5.AnalysisRecipeMatrixResult)
    assert isinstance(result.cases[0], ring5.AnalysisRecipeMatrixCase)
    assert result.complete is True
    assert result.completed_cases == 4
    assert result.failed_cases == 0
    assert result.max_workers == 2
    assert [dict(case.parameter_values) for case in result.cases] == [
        {"input_csv": str(first_csv), "minimum": 0.0},
        {"input_csv": str(first_csv), "minimum": 1.5},
        {"input_csv": str(second_csv), "minimum": 0.0},
        {"input_csv": str(second_csv), "minimum": 1.5},
    ]
    assert [case.case_id for case in result.cases] == [case.case_id for case in repeated.cases]
    paths = [Path(case.result.exported_paths[0]) for case in result.cases if case.result]
    assert len(paths) == 4
    assert len(set(paths)) == 4
    assert all(path.name == "01-same-name.html" and path.exists() for path in paths)
    assert all(path.parent.name == case.case_id for path, case in zip(paths, result.cases))


def test_matrix_failures_are_per_case_and_invalid_inputs_are_typed(tmp_path: Path) -> None:
    # [test->req~ring5.automation.batch-matrices~1]
    valid_csv = tmp_path / "valid.csv"
    pd.DataFrame({"benchmark": ["a"], "value": [1.0]}).to_csv(valid_csv, index=False)
    recipe = ring5.AnalysisRecipe(
        name="Load matrix",
        parameters=(ring5.RecipeParameter("input_csv", "path"),),
        source=ring5.RecipeSource(kind="csv", path="{{input_csv}}"),
    )
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    with patch.object(PathService, "get_analysis_recipes_dir", return_value=recipes_dir):
        with ring5.Session() as session:
            session.save_analysis_recipe(recipe)
            result = session.run_analysis_recipe_matrix(
                "Load matrix",
                {"input_csv": [str(valid_csv), str(tmp_path / "missing.csv")]},
                output_directory=str(tmp_path / "cases"),
                max_workers=2,
            )
            with pytest.raises(ring5.RecipeError, match="between 1 and 8"):
                session.run_analysis_recipe_matrix(
                    recipe,
                    {"input_csv": [str(valid_csv)]},
                    max_workers=9,
                )

            submitted = session.run_analysis_recipe_matrix_submit(
                "Load matrix",
                {"input_csv": [str(valid_csv)]},
                output_directory=str(tmp_path / "background"),
            )
            deadline = time.monotonic() + 10
            current = submitted
            while not current.terminal and time.monotonic() < deadline:
                time.sleep(0.01)
                current = next(
                    job for job in session.background_jobs() if job.job_id == submitted.job_id
                )
            background_result = session.background_job_result(current)

            with pytest.raises(ring5.JobError, match="cannot exceed"):
                session.run_analysis_recipe_matrix_submit(
                    recipe,
                    {"input_csv": [str(valid_csv)]},
                    label="x" * 121,
                )

    assert result.complete is False
    assert result.completed_cases == 1
    assert result.failed_cases == 1
    assert result.cases[1].result is None
    assert "Could not load recipe source" in (result.cases[1].error or "")
    assert isinstance(background_result, ring5.AnalysisRecipeMatrixResult)
    assert background_result.complete is True
