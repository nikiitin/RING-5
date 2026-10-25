"""
Arithmetic Service - Column-Based Mathematical Operations.

Provides utilities for performing arithmetic transformations on DataFrame
columns: division, sum, subtraction, multiplication, and multi-column
merge with standard deviation propagation. Used to create derived
metrics from base statistics.
"""

import numpy as np
import pandas as pd

from src.core.common.dataframe_utils import concat_columns
from src.core.models.arithmetic_models import ArithmeticOperation, MixerOperation


class ArithmeticService:
    """Service for arithmetic column operations and multi-column merging."""

    @staticmethod
    def list_operators() -> list[str]:
        """Return the list of supported binary arithmetic operators."""
        return [operation.value for operation in ArithmeticOperation]

    @staticmethod
    def apply_operation(
        df: pd.DataFrame, operation: str, src1: str, src2: str, dest: str
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        # [impl->req~ring5.data.arithmetic~1]
        # [impl->req~ring5.quality.immutable-data~1]
        result = df.copy()

        s1 = result[src1]
        s2 = result[src2]

        try:
            op = ArithmeticOperation(operation)
        except ValueError as exc:
            raise ValueError(f"Unknown operation: {operation}") from exc
        if op == ArithmeticOperation.DIVISION:
            result[dest] = s1 / s2.replace(0, np.nan)
        elif op == ArithmeticOperation.SUM:
            result[dest] = s1 + s2
        elif op == ArithmeticOperation.SUBTRACTION:
            result[dest] = s1 - s2
        elif op == ArithmeticOperation.MULTIPLICATION:
            result[dest] = s1 * s2
        else:
            raise ValueError(f"Unsupported arithmetic operation: {op}")

        return result

    @staticmethod
    def apply_mixer(
        df: pd.DataFrame,
        dest_col: str,
        source_cols: list[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into a destination column with SD propagation.

        Supports Sum, Mean, and Concatenate operations.
        For numeric operations, automatically propagates standard deviation
        columns with the canonical .sd suffix.

        Args:
            df: Source DataFrame.
            dest_col: Name of the new merged column.
            source_cols: List of columns to merge.
            operation: One of 'Sum', 'Mean', or 'Concatenate'.
            separator: Separator string for concatenation.

        Returns:
            New DataFrame with the merged column added.

        Raises:
            ValueError: If the operation is not supported.
        """
        # [impl->req~ring5.data.configuration-mixer~1]
        # [impl->req~ring5.data.error-propagation~1]
        # [impl->req~ring5.data.numeric-mixer~1]
        try:
            op = MixerOperation(operation)
        except ValueError as exc:
            raise ValueError(f"Unknown mixer operation: {operation}") from exc
        if not source_cols:
            raise ValueError("At least one source column must be selected.")

        result = df.copy()

        if op == MixerOperation.SUM:
            result[dest_col] = result[source_cols].sum(axis=1)
        elif op == MixerOperation.MEAN:
            result[dest_col] = result[source_cols].mean(axis=1)
        elif op == MixerOperation.CONCATENATE:
            result[dest_col] = concat_columns(result, source_cols, separator)
        else:
            raise ValueError(f"Unsupported mixer operation: {op}")

        if op in (MixerOperation.SUM, MixerOperation.MEAN):
            variance_series = None
            has_sd = False

            for col in source_cols:
                sd_col = f"{col}.sd"
                if sd_col in result.columns:
                    has_sd = True
                    variance = result[sd_col] ** 2
                    if variance_series is None:
                        variance_series = variance
                    else:
                        variance_series = variance_series.fillna(0) + variance.fillna(0)

            if has_sd and variance_series is not None:
                new_sd_col = f"{dest_col}.sd"
                if op == MixerOperation.SUM:
                    result[new_sd_col] = np.sqrt(variance_series)
                else:  # Mean
                    n = len(source_cols)
                    result[new_sd_col] = np.sqrt(variance_series) / n

        return result

    @staticmethod
    def validate_merge_inputs(
        df: pd.DataFrame,
        columns: list[str],
        operation: str,
        new_column_name: str,
    ) -> list[str]:
        """Validate inputs for the column mixer.

        Args:
            df: The DataFrame to validate against.
            columns: Source columns to merge.
            operation: The merge operation name.
            new_column_name: Desired name for the result column.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []

        if not columns:
            errors.append("At least one column must be selected")
        elif len(columns) < 2:
            errors.append("At least two columns must be selected for merging")

        missing = [col for col in columns if col not in df.columns]
        if missing:
            errors.append(f"Columns not found in DataFrame: {', '.join(missing)}")

        valid_ops = [op.value for op in MixerOperation]
        if operation not in valid_ops:
            errors.append(f"Invalid operation: '{operation}'. Valid: {', '.join(valid_ops)}")

        if not new_column_name:
            errors.append("New column name cannot be empty")
        elif new_column_name in df.columns:
            errors.append(f"Column '{new_column_name}' already exists in DataFrame")

        return errors
