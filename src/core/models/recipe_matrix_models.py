"""Immutable results for parameterized analysis-recipe matrices."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models.recipe_models import AnalysisRecipeRunResult, RecipeScalar


@dataclass(frozen=True)
class AnalysisRecipeMatrixCase:
    # [impl->req~ring5.automation.batch-matrices~1]
    """Outcome of one deterministic parameter combination.

    Attributes:
        case_id: Stable ordinal and parameter-digest identifier.
        parameter_values: Fully resolved values in recipe declaration order.
        output_directory: Collision-free directory assigned to this case.
        result: Normal recipe result when execution completed.
        error: Bounded single-line diagnostic when execution failed.
    """

    case_id: str
    parameter_values: tuple[tuple[str, RecipeScalar], ...]
    output_directory: str
    result: AnalysisRecipeRunResult | None = None
    error: str | None = None

    @property
    def successful(self) -> bool:
        """Return whether the case completed successfully."""
        return self.result is not None and self.error is None


@dataclass(frozen=True)
class AnalysisRecipeMatrixResult:
    # [impl->req~ring5.automation.batch-matrices~1]
    """Deterministically ordered result of a bounded recipe matrix.

    Attributes:
        recipe_name: Executed recipe name.
        output_directory: Root containing collision-free case directories.
        max_workers: Actual concurrency bound used for this matrix.
        cases: Outcomes in Cartesian-product order.
    """

    recipe_name: str
    output_directory: str
    max_workers: int
    cases: tuple[AnalysisRecipeMatrixCase, ...]

    @property
    def complete(self) -> bool:
        """Return whether every case completed successfully."""
        return all(case.successful for case in self.cases)

    @property
    def completed_cases(self) -> int:
        """Return the number of successful cases."""
        return sum(case.successful for case in self.cases)

    @property
    def failed_cases(self) -> int:
        """Return the number of failed cases."""
        return len(self.cases) - self.completed_cases
