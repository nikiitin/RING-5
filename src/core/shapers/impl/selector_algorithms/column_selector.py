"""
Column Selector - DataFrame Column Subsetting.

Filters a DataFrame to include only specified columns. Part of the
selector algorithm family for data filtering and subsetting.
"""

from typing import Any, Dict, List

import pandas as pd

from src.core.shapers.uni_df_shaper import UniDfShaper


class ColumnSelector(UniDfShaper):
    """
    Shaper that subsets columns in the dataframe.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize ColumnSelector.

        Args:
            params: Must contain 'columns' (List[str]).
        """
        self.columns: List[str] = params.get("columns", [])
        super().__init__(params)

    def _verify_params(self) -> bool:
        """Verify 'columns' parameter exists and is a non-empty list of strings."""
        super()._verify_params()
        if "columns" not in self.params:
            raise ValueError("ColumnSelector requires 'columns' parameter.")

        cols = self.params["columns"]
        if not isinstance(cols, list):
            raise TypeError("ColumnSelector 'columns' parameter must be a list.")

        if not all(isinstance(c, str) and c for c in cols):
            raise ValueError("ColumnSelector 'columns' must be a list of non-empty strings.")

        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that all requested columns exist in the dataframe."""
        super()._verify_preconditions(data_frame)

        missing = [c for c in self.columns if c not in data_frame.columns]
        if missing:
            raise ValueError(f"ColumnSelector: Columns not found: {missing}")

        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Subsets the dataframe to only include specified columns."""
        self._verify_preconditions(data_frame)
        return data_frame[self.columns]
