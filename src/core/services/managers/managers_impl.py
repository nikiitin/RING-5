"""
Default implementation of the ManagersAPI protocol.

Delegates to ArithmeticService, OutlierService, and ReductionService.
"""

from collections.abc import Mapping, Sequence
from typing import Literal

import pandas as pd

from src.core.services.managers.arithmetic_service import ArithmeticService
from src.core.services.managers.comparison_service import ComparisonService
from src.core.services.managers.outlier_service import OutlierService
from src.core.services.managers.reduction_service import ReductionService


class DefaultManagersAPI:
    """Default implementation of ManagersAPI.

    Delegates to ArithmeticService, OutlierService, and ReductionService.
    """

    # -- Arithmetic (Preprocessor) --

    def list_operators(self) -> list[str]:
        """Return supported binary arithmetic operators."""
        return ArithmeticService.list_operators()

    def apply_operation(
        self,
        df: pd.DataFrame,
        operation: str,
        src1: str,
        src2: str,
        dest: str,
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        return ArithmeticService.apply_operation(df, operation, src1, src2, dest)

    # -- Mixer (Multi-column merge) --

    def apply_mixer(
        self,
        df: pd.DataFrame,
        dest_col: str,
        source_cols: list[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into one with SD propagation."""
        return ArithmeticService.apply_mixer(df, dest_col, source_cols, operation, separator)

    def validate_merge_inputs(
        self,
        df: pd.DataFrame,
        columns: list[str],
        operation: str,
        new_column_name: str,
    ) -> list[str]:
        """Validate inputs for merge/mixer operations."""
        return ArithmeticService.validate_merge_inputs(df, columns, operation, new_column_name)

    # -- Outlier Removal --

    def remove_outliers(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: list[str],
    ) -> pd.DataFrame:
        """Remove statistical outliers based on Q3 threshold."""
        return OutlierService.remove_outliers(df, outlier_col, group_by_cols)

    def validate_outlier_inputs(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: list[str],
    ) -> list[str]:
        """Validate inputs for outlier removal."""
        return OutlierService.validate_outlier_inputs(df, outlier_col, group_by_cols)

    # -- Seeds Reduction --

    def reduce_seeds(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str],
        statistic_cols: list[str],
    ) -> pd.DataFrame:
        """Aggregate data across random seeds (mean + stdev)."""
        return ReductionService.reduce_seeds(df, categorical_cols, statistic_cols)

    def validate_seeds_reducer_inputs(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str],
        statistic_cols: list[str],
    ) -> list[str]:
        """Validate inputs for seeds reduction."""
        return ReductionService.validate_seeds_reducer_inputs(df, categorical_cols, statistic_cols)

    # -- Baseline comparison --

    def compare(
        self,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        key_columns: Sequence[str],
        metric_columns: Sequence[str],
        *,
        directions: (
            Literal["higher", "lower"] | Mapping[str, Literal["higher", "lower"]]
        ) = "higher",
        thresholds: float | Mapping[str, float] = 0.0,
        threshold_mode: Literal["percentage", "absolute"] = "percentage",
        baseline_name: str = "baseline",
        candidate_name: str = "candidate",
    ) -> pd.DataFrame:
        """Compare aligned baseline and candidate metrics."""
        return ComparisonService.compare(
            baseline,
            candidate,
            key_columns,
            metric_columns,
            directions=directions,
            thresholds=thresholds,
            threshold_mode=threshold_mode,
            baseline_name=baseline_name,
            candidate_name=candidate_name,
        )
