"""
Column Selector - DataFrame Column Subsetting.

Filters a DataFrame to include only specified columns. Part of the
selector algorithm family for data filtering and subsetting.
"""

from typing import Any, cast

import pandas as pd

from src.core.models.shaper_models import ColumnSelectorConfig
from src.core.services.shapers.uni_df_shaper import UniDfShaper


class ColumnSelector(UniDfShaper):
    """
    Shaper that subsets columns in the dataframe.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Initialize ColumnSelector.

        Args:
            params: Must contain 'columns' (list[str]).
        """
        super().__init__(params)
        config = cast(ColumnSelectorConfig, self.params)
        self.columns: list[str] = config["columns"]

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that all requested columns exist in the dataframe."""
        super()._verify_preconditions(data_frame)

        missing = [c for c in self.columns if c not in data_frame.columns]
        if missing:
            raise ValueError(f"ColumnSelector: Columns not found: {missing}")

        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Subsets the dataframe to only include specified columns."""
        # [impl->req~ring5.shaping.column-selector~1]
        self._verify_preconditions(data_frame)
        # .copy() so the shaper returns an independent frame, not a view.
        return data_frame[self.columns].copy()
