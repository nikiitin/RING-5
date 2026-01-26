from typing import Any, Dict, List

import pandas as pd

from src.web.services.shapers.uni_df_shaper import UniDfShaper


class Sort(UniDfShaper):
    """
    Shaper that sorts a DataFrame based on a custom categorical order for multiple columns.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize Sort shaper.

        Args:
            params: Must contain 'order_dict' which maps column names to
                    a list of values defining the preferred sort order.
        """
        self.order_dict: Dict[str, List[str]] = params.get("order_dict", {})
        super().__init__(params)

    def _verify_params(self) -> bool:
        """Verify that 'order_dict' is correctly structured."""
        super()._verify_params()
        if "order_dict" not in self.params:
            raise ValueError("Sort requires 'order_dict' parameter.")

        order_dict = self.params["order_dict"]
        if not isinstance(order_dict, dict):
            raise TypeError("Sort 'order_dict' parameter must be a dictionary.")

        for col, values in order_dict.items():
            if not isinstance(col, str):
                raise TypeError(f"Sort column name '{col}' must be a string.")
            if not isinstance(values, list):
                raise TypeError(f"Sort order values for column '{col}' must be a list.")

        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that all columns in 'order_dict' exist in the dataframe."""
        super()._verify_preconditions(data_frame)

        missing = [c for c in self.order_dict.keys() if c not in data_frame.columns]
        if missing:
            raise ValueError(f"Sort: Columns not found in dataframe: {missing}")

        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Applies categorical sorting to the dataframe.
        """
        self._verify_preconditions(data_frame)

        # Avoid modifying the input dataframe
        result = data_frame.copy()

        # Apply categorical ordering to each column specified in order_dict
        for column, orders in self.order_dict.items():
            result[column] = pd.Categorical(result[column], categories=orders, ordered=True)

        # Sort values using stable sort to preserve existing relative order for equal categories
        result = result.sort_values(by=list(self.order_dict.keys()), kind="stable")

        # Convert categorical columns back to strings to prevent downstream issues
        for column in self.order_dict:
            result[column] = result[column].astype(str)

        return result
