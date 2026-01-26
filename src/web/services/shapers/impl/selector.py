from typing import Any, Dict

import pandas as pd

from src.web.services.shapers.uni_df_shaper import UniDfShaper


class Selector(UniDfShaper):
    """
    Abstract base for shapers that filter data by column values.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize the selector.

        Args:
            params: Must contain 'column'.
        """
        super().__init__(params)
        self.column: str = params["column"]

    def _verify_params(self) -> bool:
        """Verify mandatory 'column' parameter exists."""
        super()._verify_params()
        if "column" not in self.params:
            raise ValueError("Selector requires 'column' parameter.")
        if not self.params["column"]:
            raise ValueError("Selector 'column' parameter cannot be empty.")
        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that the selected column exists in the dataframe."""
        super()._verify_preconditions(data_frame)
        if self.column not in data_frame.columns:
            raise ValueError(f"Selector: Column '{self.column}' not found in dataframe.")
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Filter the dataframe."""
        return super().__call__(data_frame)
