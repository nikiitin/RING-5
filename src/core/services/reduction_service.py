from typing import List

import pandas as pd


class ReductionService:
    """Service for data reduction operations (Seeds Reducer)."""

    @staticmethod
    def reduce_seeds(
        df: pd.DataFrame, categorical_cols: List[str], statistic_cols: List[str]
    ) -> pd.DataFrame:
        """Group by categorical columns and calculate mean and std dev."""
        if df.empty:
            return df

        grouped = df.groupby(categorical_cols)[statistic_cols]
        mean_df = grouped.mean().reset_index()
        std_df = grouped.std().reset_index()

        std_df = std_df.rename(columns=lambda x: f"{x}.sd" if x in statistic_cols else x)
        result_df = pd.merge(mean_df, std_df, on=categorical_cols)

        cols = categorical_cols + [c for c in result_df.columns if c not in categorical_cols]
        return result_df[cols]

    @staticmethod
    def validate_seeds_reducer_inputs(
        df: pd.DataFrame, categorical_cols: List[str], statistic_cols: List[str]
    ) -> List[str]:
        """Validate inputs for reduce_seeds operation."""
        errors: List[str] = []

        if not categorical_cols:
            errors.append("At least one categorical column must be selected")
        if not statistic_cols:
            errors.append("At least one statistic column must be selected")

        missing_cat = [col for col in categorical_cols if col not in df.columns]
        if missing_cat:
            errors.append(f"Categorical columns not found: {', '.join(missing_cat)}")

        missing_stat = [col for col in statistic_cols if col not in df.columns]
        if missing_stat:
            errors.append(f"Statistic columns not found: {', '.join(missing_stat)}")

        for col in statistic_cols:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Statistic column '{col}' must be numeric")

        return errors
