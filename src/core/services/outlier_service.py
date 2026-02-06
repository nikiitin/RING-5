from typing import List

import pandas as pd


class OutlierService:
    """Service for outlier removal operations."""

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame, outlier_col: str, group_by_cols: List[str]
    ) -> pd.DataFrame:
        """Remove outliers relative to the 3rd Quartile (Q3)."""
        if df.empty or outlier_col not in df.columns:
            return df

        if not group_by_cols:
            q3 = df[outlier_col].quantile(0.75)
            return df[df[outlier_col] <= q3]

        q3_series = df.groupby(group_by_cols)[outlier_col].transform(lambda x: x.quantile(0.75))
        return df[df[outlier_col] <= q3_series]

    @staticmethod
    def validate_outlier_inputs(
        df: pd.DataFrame, outlier_col: str, group_by_cols: List[str]
    ) -> List[str]:
        """Validate inputs for remove_outliers operation."""
        errors: List[str] = []

        if not outlier_col:
            errors.append("Outlier column must be specified")
        elif outlier_col not in df.columns:
            errors.append(f"Outlier column '{outlier_col}' not found in DataFrame")

        if outlier_col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[outlier_col]):
                errors.append(f"Outlier column '{outlier_col}' must be numeric")

        if group_by_cols:
            missing = [col for col in group_by_cols if col not in df.columns]
            if missing:
                errors.append(f"Group by columns not found: {', '.join(missing)}")

        return errors
