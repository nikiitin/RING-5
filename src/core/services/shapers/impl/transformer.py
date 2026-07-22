"""Shaper for numeric and categorical column conversion."""

from typing import Any, cast, override

import pandas as pd

from src.core.models.shaper_models import TransformerShaperConfig
from src.core.services.shapers.uni_df_shaper import UniDfShaper


class Transformer(UniDfShaper):
    """
    Shaper that converts a column to a specific type (Numeric/Scalar or Categorical/Factor).

    Can also apply a fixed sorting order when converting to Factor.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Initialize Transformer.

        Args:
            params: Dictionary containing:
                - column (str): Target column to transform.
                - target_type (str): 'scalar' or 'factor'.
                - order (list[str] | None): Specific categorical order for factors.
        """
        config = cast(TransformerShaperConfig, params)
        self.column: str = config.get("column", "")
        self.target_type: str = config.get("target_type", "")
        self.order: list[str] | None = config.get("order")
        super().__init__(params)

    @override
    def _verify_params(self) -> bool:
        """Verify parameter presence and value validity."""
        super()._verify_params()
        config = cast(TransformerShaperConfig, self.params)

        if not isinstance(config.get("column"), str) or not config["column"]:
            raise ValueError("Transformer requires non-empty string 'column' parameter.")

        target_type = config.get("target_type")
        if target_type not in ["scalar", "factor"]:
            raise ValueError("Transformer 'target_type' must be 'scalar' or 'factor'.")

        return True

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that the target column exists."""
        super()._verify_preconditions(data_frame)
        if self.column not in data_frame.columns:
            raise ValueError(f"Transformer: Column '{self.column}' not found in dataframe.")
        return True

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Executes the data type conversion."""
        # [impl->req~ring5.shaping.transformer~1]
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
                # Invalid scalar values become missing values.
                df[self.column] = pd.to_numeric(df[self.column], errors="coerce")
        except Exception as e:
            raise ValueError(
                f"TRANSFORMER: Failed to convert '{self.column}' to {self.target_type}: {e}"
            ) from e

        return df
