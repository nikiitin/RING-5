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

    @staticmethod
    def merge_columns(
        df: pd.DataFrame,
        columns: List[str],
        operation: str,
        new_column_name: str,
        separator: str = "_",
    ) -> pd.DataFrame:
        """
        Merge multiple columns into a single column.

        This is an alias for apply_mixer with clearer naming for the UI layer.
        Supports Sum, Mean, and Concatenate operations with automatic SD propagation.

        Args:
            df: Input DataFrame
            columns: List of column names to merge
            operation: Operation to perform ("Sum", "Mean", "Concatenate")
            new_column_name: Name for the new merged column
            separator: Separator for concatenate operation (default: "_")

        Returns:
            DataFrame with new merged column

        Raises:
            ValueError: If columns list is empty or operation is invalid

        Example:
            >>> data = pd.DataFrame({
            ...     "a": [1, 2, 3],
            ...     "b": [4, 5, 6]
            ... })
            >>> result = DataProcessingService.merge_columns(
            ...     data, ["a", "b"], "Sum", "total"
            ... )
            >>> assert "total" in result.columns
        """
        return DataProcessingService.apply_mixer(
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
        """
        Validate inputs for merge_columns operation.

        Args:
            df: Input DataFrame
            columns: Columns to merge
            operation: Operation type
            new_column_name: Name for merged column

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> data = pd.DataFrame({"a": [1], "b": [2]})
            >>> errors = DataProcessingService.validate_merge_inputs(
            ...     data, ["a", "b"], "Sum", "total"
            ... )
            >>> assert len(errors) == 0
        """
        errors: List[str] = []

        if not columns:
            errors.append("At least one column must be selected")
        elif len(columns) < 2:
            errors.append("At least two columns must be selected for merging")

        # Check columns exist
        missing = [col for col in columns if col not in df.columns]
        if missing:
            errors.append(f"Columns not found in DataFrame: {', '.join(missing)}")

        # Validate operation
        valid_ops = {"Sum", "Mean", "Mean (Average)", "Concatenate"}
        if operation not in valid_ops:
            errors.append(f"Invalid operation: '{operation}'. Valid: {', '.join(valid_ops)}")

        # Validate new column name
        if not new_column_name:
            errors.append("New column name cannot be empty")
        elif new_column_name in df.columns:
            errors.append(f"Column '{new_column_name}' already exists in DataFrame")

        return errors

    @staticmethod
    def validate_outlier_inputs(
        df: pd.DataFrame, outlier_col: str, group_by_cols: List[str]
    ) -> List[str]:
        """
        Validate inputs for remove_outliers operation.

        Args:
            df: Input DataFrame
            outlier_col: Column to detect outliers in
            group_by_cols: Columns to group by

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> data = pd.DataFrame({"val": [1, 2, 100], "group": ["A", "A", "A"]})
            >>> errors = DataProcessingService.validate_outlier_inputs(
            ...     data, "val", ["group"]
            ... )
            >>> assert len(errors) == 0
        """
        errors: List[str] = []

        if not outlier_col:
            errors.append("Outlier column must be specified")
        elif outlier_col not in df.columns:
            errors.append(f"Outlier column '{outlier_col}' not found in DataFrame")

        # Check numeric
        if outlier_col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[outlier_col]):
                errors.append(f"Outlier column '{outlier_col}' must be numeric")

        # Validate group_by columns
        if group_by_cols:
            missing = [col for col in group_by_cols if col not in df.columns]
            if missing:
                errors.append(f"Group by columns not found: {', '.join(missing)}")

        return errors

    @staticmethod
    def validate_seeds_reducer_inputs(
        df: pd.DataFrame, categorical_cols: List[str], statistic_cols: List[str]
    ) -> List[str]:
        """
        Validate inputs for reduce_seeds operation.

        Args:
            df: Input DataFrame
            categorical_cols: Columns to group by
            statistic_cols: Columns to calculate statistics for

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> data = pd.DataFrame({
            ...     "bench": ["A", "A", "B"],
            ...     "value": [1.0, 2.0, 3.0],
            ...     "seed": [1, 2, 1]
            ... })
            >>> errors = DataProcessingService.validate_seeds_reducer_inputs(
            ...     data, ["bench"], ["value"]
            ... )
            >>> assert len(errors) == 0
        """
        errors: List[str] = []

        if not categorical_cols:
            errors.append("At least one categorical column must be selected")
        if not statistic_cols:
            errors.append("At least one statistic column must be selected")

        # Check categorical columns exist
        missing_cat = [col for col in categorical_cols if col not in df.columns]
        if missing_cat:
            errors.append(f"Categorical columns not found: {', '.join(missing_cat)}")

        # Check statistic columns exist and are numeric
        missing_stat = [col for col in statistic_cols if col not in df.columns]
        if missing_stat:
            errors.append(f"Statistic columns not found: {', '.join(missing_stat)}")

        for col in statistic_cols:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Statistic column '{col}' must be numeric")

        return errors
