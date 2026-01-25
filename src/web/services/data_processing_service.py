from typing import List

import numpy as np
import pandas as pd


class DataProcessingService:
    """
    Service for data transformation operations (Seeds Reducer, Outlier Removal, etc).
    Replaces legacy src/processing/managers logic with stateless transformations.
    """

    @staticmethod
    def reduce_seeds(
        df: pd.DataFrame, categorical_cols: List[str], statistic_cols: List[str]
    ) -> pd.DataFrame:
        """
        Group by categorical columns and calculate mean and std dev (seeds reduction).
        Removes random_seed column implicitly by not including it in categorical_cols.
        """
        if df.empty:
            return df

        # Group by categorical columns
        grouped = df.groupby(categorical_cols)[statistic_cols]

        # Calculate mean
        mean_df = grouped.mean().reset_index()

        # Calculate std dev
        std_df = grouped.std().reset_index()

        # Rename std dev columns to .sd
        std_df = std_df.rename(columns=lambda x: f"{x}.sd" if x in statistic_cols else x)

        # Merge
        result_df = pd.merge(mean_df, std_df, on=categorical_cols)

        # Reorder columns: Categorical first, then Logic
        cols = categorical_cols + [c for c in result_df.columns if c not in categorical_cols]
        return result_df[cols]

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame, outlier_col: str, group_by_cols: List[str]
    ) -> pd.DataFrame:
        """
        Remove outliers relative to the 3rd Quartile (Q3).
        Legacy behavior: Keep values <= Q3 for each group.
        """
        if df.empty or outlier_col not in df.columns:
            return df

        if not group_by_cols:
            # Global Q3
            q3 = df[outlier_col].quantile(0.75)
            return df[df[outlier_col] <= q3]

        # Group-wise Q3
        # Transform returns a series aligned with original index
        q3_series = df.groupby(group_by_cols)[outlier_col].transform(lambda x: x.quantile(0.75))

        # Filter
        return df[df[outlier_col] <= q3_series]

    @staticmethod
    def list_operators() -> List[str]:
        return ["Division", "Sum", "Subtraction", "Multiplication"]

    @staticmethod
    def apply_operation(
        df: pd.DataFrame, operation: str, src1: str, src2: str, dest: str
    ) -> pd.DataFrame:
        """
        Apply arithmetic operation between two columns.
        """
        result = df.copy()

        s1 = result[src1]
        s2 = result[src2]

        op = operation.lower()
        if op in ["division", "divide", "/"]:
            # Clean division: div by zero becomes NaN
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
        """
        Merge multiple columns into a destination column.
        Supports: Sum, Mean, Concatenate.
        Also propagates Standard Deviation for Sum/Mean if .sd or .std columns exist.
        """
        if not source_cols:
            return df

        result = df.copy()

        # 1. Perform Operation
        if operation == "Sum":
            result[dest_col] = result[source_cols].sum(axis=1)
        elif operation == "Mean" or operation == "Mean (Average)":
            result[dest_col] = result[source_cols].mean(axis=1)
        elif operation == "Concatenate":
            result[dest_col] = result[source_cols].astype(str).agg(separator.join, axis=1)
        else:
            raise ValueError(f"Unknown mixer operation: {operation}")

        # 2. Propagate Error (Variance) for Numeric Operations
        if operation in ["Sum", "Mean", "Mean (Average)"]:
            variance_series = None
            has_sd = False

            for col in source_cols:
                # Try common suffixes
                potential_sds = [f"{col}.sd", f"{col}_stdev"]
                sd_col = next((s for s in potential_sds if s in result.columns), None)

                if sd_col:
                    has_sd = True
                    variance = result[sd_col] ** 2
                    if variance_series is None:
                        variance_series = variance
                    else:
                        variance_series = variance_series.fillna(0) + variance.fillna(0)
                # If no SD found, variance is implicitly 0

            if has_sd and variance_series is not None:
                new_sd_col = f"{dest_col}.sd"
                if operation == "Sum":
                    result[new_sd_col] = np.sqrt(variance_series)
                else:  # Mean
                    n = len(source_cols)
                    result[new_sd_col] = np.sqrt(variance_series) / n

        return result
