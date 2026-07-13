"""Shaper for user-defined categorical row ordering."""

from typing import Any, cast, override

import pandas as pd

from src.core.models.shaper_models import SortShaperConfig
from src.core.services.shapers.uni_df_shaper import UniDfShaper


class Sort(UniDfShaper):
    """
    Shaper that sorts a DataFrame based on a custom categorical order for multiple columns.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Initialize Sort shaper.

        Args:
            params: Must contain 'order_dict' which maps column names to
                    a list of values defining the preferred sort order.
        """
        config = cast(SortShaperConfig, params)
        self.order_dict: dict[str, list[str]] = config.get("order_dict", {})
        super().__init__(params)

    @override
    def _verify_params(self) -> bool:
        """Verify that 'order_dict' is correctly structured."""
        super()._verify_params()
        config = cast(SortShaperConfig, self.params)

        if "order_dict" not in config:
            raise ValueError("Sort requires 'order_dict' parameter.")

        order_dict = config["order_dict"]
        if not isinstance(order_dict, dict):
            raise TypeError("Sort 'order_dict' parameter must be a dictionary.")

        for col, values in order_dict.items():
            if not isinstance(col, str):
                raise TypeError(f"Sort column name '{col}' must be a string.")
            if not isinstance(values, list):
                raise TypeError(f"Sort order values for column '{col}' must be a list.")

        return True

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that all columns in 'order_dict' exist in the dataframe."""
        super()._verify_preconditions(data_frame)

        missing = [c for c in self.order_dict.keys() if c not in data_frame.columns]
        if missing:
            raise ValueError(f"Sort: Columns not found in dataframe: {missing}")

        return True

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Applies categorical sorting to the dataframe.
        """
        self._verify_preconditions(data_frame)

        # Avoid modifying the input dataframe
        result = data_frame.copy()

        # Apply categorical ordering to each column specified in order_dict. Values not
        # present in ``orders`` are appended (in first-seen order) so they KEEP their value
        # and sort after the explicitly-ordered ones — the documented partial-order
        # behavior. (Without this, pandas maps unlisted values to a categorical-NaN that the
        # later astype(str) turns into a real float NaN, silently destroying the label.)
        for column, orders in self.order_dict.items():
            extra = [v for v in dict.fromkeys(result[column].tolist()) if v not in orders]
            result[column] = pd.Categorical(
                result[column], categories=list(orders) + extra, ordered=True
            )

        # Sort values using stable sort to preserve existing relative order for equal categories
        result = result.sort_values(by=list(self.order_dict.keys()), kind="stable")

        # Convert categorical columns back to strings to prevent downstream issues
        for column in self.order_dict:
            result[column] = result[column].astype(str)

        return result
