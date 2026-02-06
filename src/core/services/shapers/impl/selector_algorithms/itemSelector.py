"""
Item Selector - Value-Based Row Filtering.

Filters DataFrame rows based on value membership (exact match or substring).
Supports both exact value matching and partial string matching.
Part of the selector algorithm family for value-based filtering.
"""

from typing import Any, Dict, List

import pandas as pd

from src.core.services.shapers.impl.selector import Selector


class ItemSelector(Selector):
    """
    Shaper that filters rows based on a list of values.
    Supports exact match (isin) or substring matching (contains).
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize ItemSelector.

        Args:
            params: Must contain 'column' and 'strings'.
                - mode (str): 'exact' (default) or 'contains'.
        """
        self.strings: List[str] = [str(s) for s in params.get("strings", [])]
        self.mode: str = params.get("mode", "exact")
        super().__init__(params)

    def _verify_params(self) -> bool:
        """Verify that 'strings' parameter is a valid list."""
        super()._verify_params()
        if "strings" not in self.params:
            raise ValueError("ItemSelector requires 'strings' parameter.")
        if not isinstance(self.params["strings"], list):
            raise TypeError("ItemSelector 'strings' parameter must be a list.")
        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that items exist to be selected (optional warning)."""
        super()._verify_preconditions(data_frame)

        if self.mode == "exact":
            mask = data_frame[self.column].astype(str).isin(self.strings)
        else:
            pattern = "|".join(self.strings)
            mask = data_frame[self.column].astype(str).str.contains(pattern, na=False)

        if not mask.any():
            import logging

            logging.getLogger(__name__).warning(
                f"ItemSelector: None of the strings {self.strings} found in column '{self.column}'."
            )

        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Filters the dataframe to only include rows with matching strings.
        """
        self._verify_preconditions(data_frame)

        if self.mode == "exact":
            return data_frame[data_frame[self.column].astype(str).isin(self.strings)]
        else:
            # Regex mode (previous behavior)
            pattern = "|".join(self.strings)
            return data_frame[data_frame[self.column].astype(str).str.contains(pattern, na=False)]
