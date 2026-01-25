"""Data Transformer Shaper implementation."""

import pandas as pd

from src.web.services.shapers.uni_df_shaper import UniDfShaper


class Transformer(UniDfShaper):
    """
    Shaper that converts a column to a specific type (Scalar or Factor).
    """

    def _verifyParams(self) -> bool:
        """
        Verify that the Shaper json is valid.
        """
        super()._verifyParams()

        column = self._params.get("column")
        target_type = self._params.get("target_type")

        if not column or not isinstance(column, str):
            raise ValueError("The parameter 'column' is missing or not a string!")

        if not target_type or target_type not in ["scalar", "factor"]:
            raise ValueError("The parameter 'target_type' must be 'scalar' or 'factor'!")

        return True

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        """
        Verify that the Shaper read values are valid and coherent with the data frame.
        """
        super()._verifyPreconditions(data_frame)
        col = self._params.get("column")

        # Check if the column exists in the dataframe
        if col not in data_frame.columns:
            # Column required for transformation
            raise ValueError(f"Column '{col}' not found in the dataframe!")

        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Perform a shaping operation on the given DataFrame.
        """
        super().__call__(data_frame)

        df = data_frame.copy()
        col = self._params.get("column")
        target_type = self._params.get("target_type")

        try:
            if target_type == "factor":
                df[col] = df[col].astype(str)
                order = self._params.get("order")
                if order and isinstance(order, list):
                    # Create an ordered categorical type
                    df[col] = pd.Categorical(df[col], categories=order, ordered=True)
            elif target_type == "scalar":
                df[col] = pd.to_numeric(df[col], errors="coerce")
        except Exception as e:
            raise ValueError(f"Failed to transform column '{col}': {e}") from e

        return df
