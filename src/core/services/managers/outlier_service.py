"""
Outlier Service - Statistical Outlier Removal.

Detects and removes statistical outliers from data using the IQR
(Interquartile Range) method. Supports global and grouped outlier
removal for robust analysis.
"""

import pandas as pd


class OutlierService:
    """Service for outlier removal operations using the IQR method."""

    IQR_MULTIPLIER: float = 1.5

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: list[str],
        multiplier: float = 1.5,
    ) -> pd.DataFrame:
        """Remove outliers using the IQR (Interquartile Range) method.

        Values outside [Q1 - multiplier*IQR, Q3 + multiplier*IQR] are removed.
        The default multiplier of 1.5 identifies mild outliers (standard).
        Use 3.0 for extreme outliers only.
        """
        if df.empty or outlier_col not in df.columns:
            return df

        if not group_by_cols:
            q1 = df[outlier_col].quantile(0.25)
            q3 = df[outlier_col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - multiplier * iqr
            upper = q3 + multiplier * iqr
            return df[(df[outlier_col] >= lower) & (df[outlier_col] <= upper)]

        def _iqr_mask(series: pd.Series) -> pd.Series:  # type: ignore[type-arg]
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - multiplier * iqr
            upper = q3 + multiplier * iqr
            return (series >= lower) & (series <= upper)

        mask = df.groupby(group_by_cols)[outlier_col].transform(_iqr_mask).astype(bool)
        return df[mask]

    @staticmethod
    def validate_outlier_inputs(
        df: pd.DataFrame, outlier_col: str, group_by_cols: list[str]
    ) -> list[str]:
        """Validate inputs for remove_outliers operation."""
        errors: list[str] = []

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
