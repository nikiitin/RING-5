"""GroupCardinalitySelector shaper — keep groups by their distinct-value count.

Filters rows to the groups whose number of distinct ``countColumn`` values satisfies a
predicate against ``count`` — e.g. "keep only benchmarks present under all 5 policies".
No existing selector filters on per-group cardinality (the others test a single column's
own value). Pure row selection: no arithmetic, no NaN concerns. Immutable (``copy()`` first).
"""

from typing import Any, cast, override

import pandas as pd

from src.core.models.shaper_models import GroupCardinalitySelectorConfig
from src.core.services.shapers.uni_df_shaper import UniDfShaper


class GroupCardinalitySelector(UniDfShaper):
    """Keep rows of groups where ``nunique(countColumn)`` ``{eq|ge|le}`` ``count``."""

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        config = cast(GroupCardinalitySelectorConfig, self.params)
        self.group_by: list[str] = config["groupBy"]
        self.count_column: str = config["countColumn"]
        self.count: int = config["count"]
        self.mode: str = config.get("mode", "eq")

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        super()._verify_preconditions(data_frame)
        missing = [c for c in [*self.group_by, self.count_column] if c not in data_frame.columns]
        if missing:
            raise ValueError(f"GroupCardinalitySelector: columns not found: {missing}")
        return True

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        # [impl->req~ring5.shaping.group-cardinality-selector~1]
        self._verify_preconditions(data_frame)
        result = data_frame.copy()
        n = result.groupby(self.group_by)[self.count_column].transform("nunique")
        if self.mode == "eq":
            keep = n == self.count
        elif self.mode == "ge":
            keep = n >= self.count
        else:  # "le"
            keep = n <= self.count
        return result[keep].reset_index(drop=True)
