"""
Arithmetic Service - Column-Based Mathematical Operations.

Provides utilities for performing arithmetic transformations on DataFrame
columns: division, sum, subtraction, multiplication, and multi-column
merge with standard deviation propagation. Used to create derived
metrics from base statistics.
"""

from typing import List

import numpy as np
import pandas as pd


class ArithmeticService:
    """Service for arithmetic column operations and multi-column merging."""

    @staticmethod
    def list_operators() -> List[str]:
        """Return the list of supported binary arithmetic operators."""
        return ["Division", "Sum", "Subtraction", "Multiplication"]

    @staticmethod
    def apply_operation(
        df: pd.DataFrame, operation: str, src1: str, src2: str, dest: str
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        result = df.copy()

        s1 = result[src1]
        s2 = result[src2]

        op = operation.lower()
        if op in ["division", "divide", "/"]:
            result[dest] = s1 / s2.replace(0, np.nan)
        elif op in ["sum", "add", "+"]:
            result[dest] = s1 + s2
        elif op in ["subtraction", "subtract", "minus", "-"]:
            result[dest] = s1 - s2
        elif op in ["multiplication", "multiply", "*"]:
            result[dest] = s1 * s2
        else:
            raise ValueError(f"Unknown operation: {operation}")

        return result

    @staticmethod
    def apply_mixer(
        df: pd.DataFrame,
        dest_col: str,
        source_cols: List[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into a destination column with SD propagation.

        Supports Sum, Mean, Mean (Average), and Concatenate operations.
        For numeric operations, automatically propagates standard deviation
        columns (.sd or _stdev suffixes).

        Args:
            df: Source DataFrame.
            dest_col: Name of the new merged column.
            source_cols: List of columns to merge.
            operation: One of 'Sum', 'Mean', 'Mean (Average)', 'Concatenate'.
            separator: Separator string for concatenation.

        Returns:
            New DataFrame with the merged column added.

        Raises:
            ValueError: If the operation is not supported.
        """
        if not source_cols:
            return df

        result = df.copy()

        if operation == "Sum":
            result[dest_col] = result[source_cols].sum(axis=1)
        elif operation in ("Mean", "Mean (Average)"):
            result[dest_col] = result[source_cols].mean(axis=1)
        elif operation == "Concatenate":
            result[dest_col] = result[source_cols].astype(str).agg(separator.join, axis=1)
        else:
            raise ValueError(f"Unknown mixer operation: {operation}")

        if operation in ("Sum", "Mean", "Mean (Average)"):
            variance_series = None
            has_sd = False

            for col in source_cols:
                potential_sds = [f"{col}.sd", f"{col}_stdev"]
                sd_col = next((s for s in potential_sds if s in result.columns), None)

                if sd_col:
                    has_sd = True
                    variance = result[sd_col] ** 2
                    if variance_series is None:
                        variance_series = variance
                    else:
                        variance_series = variance_series.fillna(0) + variance.fillna(0)

            if has_sd and variance_series is not None:
                new_sd_col = f"{dest_col}.sd"
                if operation == "Sum":
                    result[new_sd_col] = np.sqrt(variance_series)
                else:  # Mean
                    n = len(source_cols)
                    result[new_sd_col] = np.sqrt(variance_series) / n

        return result

    @staticmethod
    def merge_columns(
        df: pd.DataFrame,
        columns: List[str],
        operation: str,
        new_column_name: str,
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into a single column.

        Convenience wrapper around :meth:`apply_mixer`.
        """
        return ArithmeticService.apply_mixer(
            df=df,
            dest_col=new_column_name,
            source_cols=columns,
            operation=operation,
            separator=separator,
        )

    @staticmethod
    def validate_merge_inputs(
        df: pd.DataFrame,
        columns: List[str],
        operation: str,
        new_column_name: str,
    ) -> List[str]:
        """Validate inputs for merge_columns / apply_mixer operations.

        Args:
            df: The DataFrame to validate against.
            columns: Source columns to merge.
            operation: The merge operation name.
            new_column_name: Desired name for the result column.

        Returns:
            List of error messages (empty if valid).
        """
        errors: List[str] = []

        if not columns:
            errors.append("At least one column must be selected")
        elif len(columns) < 2:
            errors.append("At least two columns must be selected for merging")

        missing = [col for col in columns if col not in df.columns]
        if missing:
            errors.append(f"Columns not found in DataFrame: {', '.join(missing)}")

        valid_ops = {"Sum", "Mean", "Mean (Average)", "Concatenate"}
        if operation not in valid_ops:
            errors.append(f"Invalid operation: '{operation}'. Valid: {', '.join(valid_ops)}")

        if not new_column_name:
            errors.append("New column name cannot be empty")
        elif new_column_name in df.columns:
            errors.append(f"Column '{new_column_name}' already exists in DataFrame")

        return errors
