"""
Mixer Service - Multi-Column Merge and Aggregation.

Combines multiple columns into a single derived column with proper standard
deviation propagation. Supports sum, mean, and other aggregation operations
for creating composite metrics from base statistics.
"""

from typing import List

import numpy as np
import pandas as pd


class MixerService:
    """Service for multi-column merge and mixing operations."""

    @staticmethod
    def apply_mixer(
        df: pd.DataFrame,
        dest_col: str,
        source_cols: List[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into a destination column with SD propagation."""
        if not source_cols:
            return df

        result = df.copy()

        if operation == "Sum":
            result[dest_col] = result[source_cols].sum(axis=1)
        elif operation == "Mean" or operation == "Mean (Average)":
            result[dest_col] = result[source_cols].mean(axis=1)
        elif operation == "Concatenate":
            result[dest_col] = result[source_cols].astype(str).agg(separator.join, axis=1)
        else:
            raise ValueError(f"Unknown mixer operation: {operation}")

        if operation in ["Sum", "Mean", "Mean (Average)"]:
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
        """Alias for apply_mixer."""
        return MixerService.apply_mixer(
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
        """Validate inputs for merge_columns operation."""
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
