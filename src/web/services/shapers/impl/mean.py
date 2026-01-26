from typing import Any, Dict, List

import pandas as pd
from scipy.stats import gmean, hmean

from src.web.services.shapers.uni_df_shaper import UniDfShaper


class Mean(UniDfShaper):
    """
    Shaper that calculates means (arithmetic, geometric, or harmonic) for
    selected variables across groups and appends the results to the dataframe.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize Mean shaper.

        Args:
            params: Dictionary containing:
                - meanVars (List[str]): Columns to average.
                - meanAlgorithm (str): 'arithmean', 'geomean', or 'hmean'.
                - groupingColumns (List[str]): Columns to group by.
                - replacingColumn (str): Column where the algorithm name will be stored in the new rows.
        """
        # Assigning attributes before super().__init__
        self.mean_vars: List[str] = params.get("meanVars", [])
        self.mean_algorithm: str = params.get("meanAlgorithm", "")
        self.replacing_column: str = params.get("replacingColumn", "")

        # Support both new 'groupingColumns' and legacy 'groupingColumn'
        if "groupingColumns" in params:
            self.grouping_columns: List[str] = params["groupingColumns"]
        elif "groupingColumn" in params:
            self.grouping_columns = [params["groupingColumn"]]
        else:
            self.grouping_columns = []

        super().__init__(params)

    def _verify_params(self) -> bool:
        """Validate parameter structure and algorithm choice."""
        super()._verify_params()

        if self.params["meanAlgorithm"] not in ["arithmean", "geomean", "hmean"]:
            raise ValueError(
                "Mean: 'meanAlgorithm' must be one of 'arithmean', 'geomean', or 'hmean'."
            )

        if not isinstance(self.params.get("meanVars"), list):
            raise TypeError("Mean: 'meanVars' must be a list.")

        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify columns exist and numeric requirements are met."""
        super()._verify_preconditions(data_frame)

        all_required = self.mean_vars + self.grouping_columns + [self.replacing_column]
        for col in all_required:
            if col not in data_frame.columns:
                raise ValueError(f"Mean: Required column '{col}' not found in dataframe.")

        for col in self.mean_vars:
            if not pd.api.types.is_numeric_dtype(data_frame[col]):
                raise ValueError(f"Mean: Column '{col}' must be numeric.")

        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates group means and appends them as new rows.
        """
        self._verify_preconditions(data_frame)

        result = data_frame.copy()
        grouped = result.groupby(self.grouping_columns)

        # Apply appropriate mean aggregation
        if self.mean_algorithm == "arithmean":
            mean_df = grouped[self.mean_vars].mean().reset_index()
        elif self.mean_algorithm == "geomean":
            # Handle potential non-positive values for geometric mean via agg
            mean_df = grouped[self.mean_vars].agg(gmean).reset_index()
        elif self.mean_algorithm == "hmean":
            mean_df = grouped[self.mean_vars].agg(hmean).reset_index()
        else:
            raise ValueError(f"Unknown algorithm: {self.mean_algorithm}")

        # Label the new rows
        mean_df[self.replacing_column] = self.mean_algorithm

        # Carry over other columns by taking the first encountered value in each group
        # This preserves metadata like 'config_description' etc.
        other_cols = [
            col
            for col in result.columns
            if col not in self.mean_vars
            and col not in self.grouping_columns
            and col != self.replacing_column
        ]

        for col in other_cols:
            first_vals = grouped[col].first().reset_index()
            mean_df = mean_df.merge(first_vals, on=self.grouping_columns, how="left")

        # Append to the original data
        return pd.concat([result, mean_df], ignore_index=True)
