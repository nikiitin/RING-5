"""Base shaper for filtering rows by column values."""

from copy import deepcopy
from typing import Any, override

import pandas as pd

from src.core.services.shapers.uni_df_shaper import UniDfShaper


class Selector(UniDfShaper):
    """
    Abstract base for shapers that filter data by column values.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Initialize the selector.

        Args:
            params: Must contain 'column'.
        """
        if type(self) is Selector:
            if not isinstance(params, dict):
                raise ValueError("Selector parameters must be a dictionary.")
            self.params = deepcopy(params)
            self._validate_selector()
        else:
            super().__init__(params)
        self.column: str = self.params["column"]

    def _validate_selector(self) -> bool:
        """Verify mandatory 'column' parameter exists."""
        if "column" not in self.params:
            raise ValueError("Selector requires 'column' parameter.")
        if not isinstance(self.params["column"], str) or not self.params["column"]:
            raise ValueError("Selector 'column' parameter cannot be empty.")
        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that the selected column exists in the dataframe."""
        super()._verify_preconditions(data_frame)
        if self.column not in data_frame.columns:
            raise ValueError(f"Selector: Column '{self.column}' not found in dataframe.")
        return True

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Filter the dataframe."""
        return super().__call__(data_frame)
