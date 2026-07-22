"""Bounded deterministic Cartesian execution of analysis recipes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path

from src.core.common.security_limits import (
    MAX_ANALYSIS_RECIPE_PARAMETERS,
    MAX_ANALYSIS_RECIPE_MATRIX_CASES,
    MAX_ANALYSIS_RECIPE_MATRIX_WORKERS,
    MAX_ANALYSIS_RECIPE_STRING_LENGTH,
    MAX_BACKGROUND_JOB_ERROR_LENGTH,
)
from src.core.common.utils import sanitize_filename, sanitize_log_value
from src.core.models import (
    AnalysisRecipe,
    AnalysisRecipeMatrixCase,
    AnalysisRecipeMatrixResult,
    AnalysisRecipeRunResult,
    RecipeExport,
    RecipeScalar,
)
from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService

RecipeMatrix = Mapping[str, Sequence[RecipeScalar]]
RecipeRunner = Callable[[AnalysisRecipe, Mapping[str, RecipeScalar]], AnalysisRecipeRunResult]


@dataclass(frozen=True)
class _PreparedCase:
    case_id: str
    parameter_values: tuple[tuple[str, RecipeScalar], ...]
    output_directory: str
    recipe: AnalysisRecipe


class AnalysisRecipeMatrixService:
    """Validate, isolate, and execute a bounded recipe parameter matrix."""

    @staticmethod
    def execute(
        recipe: AnalysisRecipe,
        matrix: RecipeMatrix,
        output_directory: str,
        runner: RecipeRunner,
        *,
        max_workers: int = 2,
    ) -> AnalysisRecipeMatrixResult:
        """Execute prepared cases concurrently and return them in stable order."""
        # [impl->req~ring5.automation.batch-matrices~1]
        prepared = AnalysisRecipeMatrixService.prepare(
            recipe,
            matrix,
            output_directory,
            max_workers=max_workers,
        )
        if not callable(runner):
            raise TypeError("Analysis recipe matrix runner must be callable.")
        worker_count = min(max_workers, len(prepared))
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="ring5-recipe-matrix",
        ) as executor:
            futures: list[Future[AnalysisRecipeRunResult]] = [
                executor.submit(runner, case.recipe, dict(case.parameter_values))
                for case in prepared
            ]
            cases = tuple(
                AnalysisRecipeMatrixService._settle(case, future)
                for case, future in zip(prepared, futures, strict=True)
            )
        return AnalysisRecipeMatrixResult(
            recipe_name=recipe.name,
            output_directory=output_directory,
            max_workers=worker_count,
            cases=cases,
        )

    @staticmethod
    def prepare(
        recipe: AnalysisRecipe,
        matrix: RecipeMatrix,
        output_directory: str,
        *,
        max_workers: int = 2,
    ) -> tuple[_PreparedCase, ...]:
        """Validate and materialize collision-free cases without executing them."""
        AnalysisRecipeService.validate(recipe)
        AnalysisRecipeMatrixService._validate_workers(max_workers)
        root = AnalysisRecipeMatrixService._validate_output_directory(output_directory)
        dimensions = AnalysisRecipeMatrixService._validate_matrix(recipe, matrix)
        combinations = product(*(values for _name, values in dimensions))
        prepared: list[_PreparedCase] = []
        width = max(3, len(str(AnalysisRecipeMatrixService._case_count(dimensions))))
        for index, combination in enumerate(combinations, start=1):
            supplied = {
                name: value for (name, _values), value in zip(dimensions, combination, strict=True)
            }
            resolved = AnalysisRecipeService.resolve_parameters(recipe, supplied)
            parameter_values = tuple(resolved.items())
            case_id = AnalysisRecipeMatrixService._case_id(index, width, parameter_values)
            case_directory = root / case_id
            materialized = AnalysisRecipeService.materialize(recipe, resolved)
            prepared.append(
                _PreparedCase(
                    case_id=case_id,
                    parameter_values=parameter_values,
                    output_directory=str(case_directory),
                    recipe=replace(
                        materialized,
                        exports=AnalysisRecipeMatrixService._retarget_exports(
                            materialized.exports,
                            case_directory,
                        ),
                    ),
                )
            )
        return tuple(prepared)

    @staticmethod
    def _validate_matrix(
        recipe: AnalysisRecipe,
        matrix: RecipeMatrix,
    ) -> tuple[tuple[str, tuple[RecipeScalar, ...]], ...]:
        if not isinstance(matrix, Mapping):
            raise TypeError("Analysis recipe matrix must be a mapping of parameters to values.")
        if len(matrix) > MAX_ANALYSIS_RECIPE_PARAMETERS:
            raise ValueError("Analysis recipe matrix exceeds the parameter limit.")
        declared = {parameter.name for parameter in recipe.parameters}
        if not all(isinstance(name, str) for name in matrix):
            raise TypeError("Analysis recipe matrix parameter names must be text.")
        unknown = sorted(set(matrix) - declared)
        if unknown:
            raise ValueError(
                "Unknown analysis recipe matrix parameters: " + ", ".join(unknown) + "."
            )
        dimensions: list[tuple[str, tuple[RecipeScalar, ...]]] = []
        for parameter in recipe.parameters:
            if parameter.name not in matrix:
                continue
            source_values = matrix[parameter.name]
            if isinstance(source_values, (str, bytes, bytearray)) or not isinstance(
                source_values, Sequence
            ):
                raise TypeError(
                    f"Analysis recipe matrix parameter {parameter.name!r} must be a sequence."
                )
            if len(source_values) > MAX_ANALYSIS_RECIPE_MATRIX_CASES:
                raise ValueError(
                    "Analysis recipe matrix expands beyond the "
                    f"{MAX_ANALYSIS_RECIPE_MATRIX_CASES}-case limit."
                )
            values = tuple(source_values)
            if not values:
                raise ValueError(
                    f"Analysis recipe matrix parameter {parameter.name!r} has no values."
                )
            fingerprints = [
                json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
                for value in values
            ]
            if len(fingerprints) != len(set(fingerprints)):
                raise ValueError(
                    f"Analysis recipe matrix parameter {parameter.name!r} has duplicate values."
                )
            dimensions.append((parameter.name, values))
        count = AnalysisRecipeMatrixService._case_count(tuple(dimensions))
        if count > MAX_ANALYSIS_RECIPE_MATRIX_CASES:
            raise ValueError(
                "Analysis recipe matrix expands to "
                f"{count} cases; the limit is {MAX_ANALYSIS_RECIPE_MATRIX_CASES}."
            )
        return tuple(dimensions)

    @staticmethod
    def _case_count(dimensions: tuple[tuple[str, tuple[RecipeScalar, ...]], ...]) -> int:
        count = 1
        for _name, values in dimensions:
            count *= len(values)
        return count

    @staticmethod
    def _validate_workers(max_workers: int) -> None:
        if isinstance(max_workers, bool) or not isinstance(max_workers, int):
            raise TypeError("Analysis recipe matrix max_workers must be an integer.")
        if not 1 <= max_workers <= MAX_ANALYSIS_RECIPE_MATRIX_WORKERS:
            raise ValueError(
                "Analysis recipe matrix max_workers must be between 1 and "
                f"{MAX_ANALYSIS_RECIPE_MATRIX_WORKERS}."
            )

    @staticmethod
    def _validate_output_directory(output_directory: str) -> Path:
        if not isinstance(output_directory, str):
            raise TypeError("Analysis recipe matrix output_directory must be text.")
        if len(output_directory) > MAX_ANALYSIS_RECIPE_STRING_LENGTH:
            raise ValueError("Analysis recipe matrix output_directory is too long.")
        if not output_directory.strip() or any(
            ord(character) < 32 for character in output_directory
        ):
            raise ValueError(
                "Analysis recipe matrix output_directory must be a non-empty valid path."
            )
        return Path(output_directory)

    @staticmethod
    def _case_id(
        index: int,
        width: int,
        values: tuple[tuple[str, RecipeScalar], ...],
    ) -> str:
        canonical = json.dumps(values, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
        return f"case-{index:0{width}d}-{digest}"

    @staticmethod
    def _retarget_exports(
        exports: tuple[RecipeExport, ...],
        case_directory: Path,
    ) -> tuple[RecipeExport, ...]:
        rewritten: list[RecipeExport] = []
        for index, export in enumerate(exports, start=1):
            stem = sanitize_filename(Path(export.path).stem)
            filename = f"{index:02d}-{stem}.{export.format}"
            rewritten.append(replace(export, path=str(case_directory / filename)))
        return tuple(rewritten)

    @staticmethod
    def _settle(
        case: _PreparedCase,
        future: Future[AnalysisRecipeRunResult],
    ) -> AnalysisRecipeMatrixCase:
        try:
            result = future.result()
            if not isinstance(result, AnalysisRecipeRunResult):
                raise TypeError("Analysis recipe matrix runner returned an invalid result.")
        except Exception as exc:
            error = sanitize_log_value(exc)[:MAX_BACKGROUND_JOB_ERROR_LENGTH]
            return AnalysisRecipeMatrixCase(
                case_id=case.case_id,
                parameter_values=case.parameter_values,
                output_directory=case.output_directory,
                error=error or type(exc).__name__,
            )
        return AnalysisRecipeMatrixCase(
            case_id=case.case_id,
            parameter_values=case.parameter_values,
            output_directory=case.output_directory,
            result=result,
        )
