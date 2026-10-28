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
        super().__init__(params)
        config = cast(SortShaperConfig, self.params)
        self.order_dict: dict[str, list[str | int | float | bool | None]] = config.get(
            "order_dict", {}
        )

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
        # [impl->req~ring5.shaping.sort~1]
        self._verify_preconditions(data_frame)

        # Avoid modifying the input dataframe
        sort_keys = pd.DataFrame(index=pd.RangeIndex(len(data_frame)))

        # Apply categorical ordering to each column specified in order_dict. Values not
        # present in ``orders`` are appended (in first-seen order) so they KEEP their value
        # and sort after the explicitly-ordered ones — the documented partial-order
        # behavior. (Without this, pandas maps unlisted values to a categorical-NaN that the
        # later astype(str) turns into a real float NaN, silently destroying the label.)
        for column, orders in self.order_dict.items():
            preferred = list(dict.fromkeys(value for value in orders if pd.notna(value)))
            extra = [
                value
                for value in pd.unique(data_frame[column])
                if pd.notna(value) and value not in preferred
            ]
            sort_keys[column] = pd.Categorical(
                data_frame[column], categories=preferred + extra, ordered=True
            )

        # Sort values using stable sort to preserve existing relative order for equal categories
        if not self.order_dict:
            if self._source_tracker is not None:
                self._source_tracker.select(range(len(data_frame)))
            return data_frame.copy()
        positions = sort_keys.sort_values(by=list(self.order_dict), kind="stable").index
        if self._source_tracker is not None:
            self._source_tracker.select(positions)
        return data_frame.iloc[positions].copy()
