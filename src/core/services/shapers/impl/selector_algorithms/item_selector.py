"""
Item Selector - Value-Based Row Filtering.

Filters DataFrame rows based on value membership (exact match or substring).
Supports both exact value matching and partial string matching.
Part of the selector algorithm family for value-based filtering.
"""

import logging
from typing import Any, cast

import pandas as pd

from src.core.common.security_limits import MAX_SEARCH_TERM_LENGTH, MAX_SELECTOR_STRINGS
from src.core.models.shaper_models import ItemSelectorConfig
from src.core.services.shapers.impl.selector import Selector


class ItemSelector(Selector):
    """
    Shaper that filters rows based on a list of values.
    Supports exact match (isin) or substring matching (contains).
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Initialize ItemSelector.

        Args:
            params: Must contain 'column' and 'strings'.
                - mode (str): 'exact' (default) or 'contains'.
        """
        config = cast(ItemSelectorConfig, params)
        self.strings: list[str] = [str(s) for s in config.get("strings", [])]
        self.mode: str = config.get("mode", "exact")
        super().__init__(params)

    def _verify_params(self) -> bool:
        """Verify that 'strings' parameter is a valid list."""
        super()._verify_params()
        config = cast(ItemSelectorConfig, self.params)

        if "strings" not in config:
            raise ValueError("ItemSelector requires 'strings' parameter.")
        if not isinstance(config["strings"], list):
            raise TypeError("ItemSelector 'strings' parameter must be a list.")
        if len(config["strings"]) > MAX_SELECTOR_STRINGS:
            raise ValueError(f"ItemSelector accepts at most {MAX_SELECTOR_STRINGS} search strings.")
        if any(len(str(value)) > MAX_SEARCH_TERM_LENGTH for value in config["strings"]):
            raise ValueError(
                f"ItemSelector search strings cannot exceed {MAX_SEARCH_TERM_LENGTH} characters."
            )
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Filter the dataframe to only include rows with matching strings."""
        self._verify_preconditions(data_frame)

        if self.mode == "exact":
            result = data_frame[data_frame[self.column].astype(str).isin(self.strings)]
        else:
            values = data_frame[self.column].astype(str)
            mask = pd.Series(False, index=data_frame.index)
            for literal in self.strings:
                mask = mask | values.str.contains(literal, na=False, regex=False)
            result = data_frame[mask]

        if result.empty:
            logging.getLogger(__name__).warning(
                f"ItemSelector: None of the strings {self.strings} "
                f"found in column '{self.column}'."
            )

        # .copy() so the shaper returns an independent frame, not a view.
        return result.copy()
