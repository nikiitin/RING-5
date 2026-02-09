"""
Managers API Protocol -- Interface for data transformation managers.

Defines the contract for stateless data transformation operations used by
the data-manager UI components: arithmetic operations, outlier removal,
and seed reduction.
"""

from typing import List, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class ManagersAPI(Protocol):
    """Protocol for stateless data transformation operations.

    Groups arithmetic, outlier removal, reduction, and column-merge
    operations used by the data-manager UI components.
    """

    # -- Arithmetic (Preprocessor) --

    def list_operators(self) -> List[str]:
        """Return supported binary arithmetic operators."""
        ...

    def apply_operation(
        self,
        df: pd.DataFrame,
        operation: str,
        src1: str,
        src2: str,
        dest: str,
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        ...

    # -- Mixer (Multi-column merge) --

    def apply_mixer(
        self,
        df: pd.DataFrame,
        dest_col: str,
        source_cols: List[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into one with SD propagation."""
        ...

    def validate_merge_inputs(
        self,
        df: pd.DataFrame,
        columns: List[str],
        operation: str,
        new_column_name: str,
    ) -> List[str]:
        """Validate inputs for merge/mixer operations."""
        ...

    # -- Outlier Removal --

    def remove_outliers(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: List[str],
    ) -> pd.DataFrame:
        """Remove statistical outliers based on Q3 threshold."""
        ...

    def validate_outlier_inputs(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: List[str],
    ) -> List[str]:
        """Validate inputs for outlier removal."""
        ...

    # -- Seeds Reduction --

    def reduce_seeds(
        self,
        df: pd.DataFrame,
        categorical_cols: List[str],
        statistic_cols: List[str],
    ) -> pd.DataFrame:
        """Aggregate data across random seeds (mean + stdev)."""
        ...

    def validate_seeds_reducer_inputs(
        self,
        df: pd.DataFrame,
        categorical_cols: List[str],
        statistic_cols: List[str],
    ) -> List[str]:
        """Validate inputs for seeds reduction."""
        ...
