from typing import Any, Dict, List, Optional

import pandas as pd

from src.web.services.shapers.uni_df_shaper import UniDfShaper


class Transformer(UniDfShaper):
    """
    Shaper that converts a column to a specific type (Numeric/Scalar or Categorical/Factor).

    Can also apply a fixed sorting order when converting to Factor.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize Transformer.

        Args:
            params: Dictionary containing:
                - column (str): Target column to transform.
                - target_type (str): 'scalar' or 'factor'.
                - order (Optional[List[str]]): Specific categorical order for factors.
        """
        self.column: str = params.get("column", "")
        self.target_type: str = params.get("target_type", "")
        self.order: Optional[List[str]] = params.get("order")
        super().__init__(params)

    def _verify_params(self) -> bool:
        """Verify parameter presence and value validity."""
        super()._verify_params()

        if not isinstance(self.params.get("column"), str) or not self.params["column"]:
            raise ValueError("Transformer requires non-empty string 'column' parameter.")

        target_type = self.params.get("target_type")
        if target_type not in ["scalar", "factor"]:
            raise ValueError("Transformer 'target_type' must be 'scalar' or 'factor'.")

        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that the target column exists."""
        super()._verify_preconditions(data_frame)
        if self.column not in data_frame.columns:
            raise ValueError(f"Transformer: Column '{self.column}' not found in dataframe.")
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Executes the data type conversion."""
        self._verify_preconditions(data_frame)

        df = data_frame.copy()

        try:
            if self.target_type == "factor":
                # Convert to string first to ensure clean categorical conversion
                df[self.column] = df[self.column].astype(str)
                if self.order and isinstance(self.order, list):
                    df[self.column] = pd.Categorical(
                        df[self.column], categories=self.order, ordered=True
                    )
            elif self.target_type == "scalar":
                # Convert to numeric, pushing non-convertibles to NaN (Zero Hallucination)
                df[self.column] = pd.to_numeric(df[self.column], errors="coerce")
        except Exception as e:
            # Domain Layer error handling
            raise ValueError(
                f"TRANSFORMER: Failed to convert '{self.column}' to {self.target_type}: {e}"
            ) from e

        return df
