"""GroupPredicateSelector shaper — drop/keep groups by a baseline-row predicate.

For each group, the predicate is evaluated on the group's *baseline row* (the row whose
``baselineColumn`` equals ``baselineValue``). Groups whose baseline value is zero/NaN are
dropped (default) — e.g. excluding stall-free benchmarks from a downstream mean while the
caller re-adds them as placeholder zero rows. Pure row selection; immutable (``copy()`` first).
"""

from typing import Any, cast, override

import pandas as pd

from src.core.models.shaper_models import GroupPredicateSelectorConfig
from src.core.services.shapers.uni_df_shaper import UniDfShaper

_DROP_WHEN = frozenset({"zero_or_nan", "zero", "nan"})
_ACTIONS = frozenset({"drop", "keep"})


class GroupPredicateSelector(UniDfShaper):
    """Keep or drop whole groups based on the predicate on each group's baseline row."""

    def __init__(self, params: dict[str, Any]) -> None:
        config = cast(GroupPredicateSelectorConfig, params)
        self.group_by: list[str] = list(config.get("groupBy", []))
        self.baseline_column: str = config.get("baselineColumn", "")
        self.baseline_value: str = config.get("baselineValue", "")
        self.predicate_column: str = config.get("predicateColumn", "")
        self.drop_when: str = config.get("drop_when", "zero_or_nan")
        self.action: str = config.get("action", "drop")
        super().__init__(params)

    @override
    def _verify_params(self) -> bool:
        super()._verify_params()
        if not self.group_by:
            raise ValueError("GroupPredicateSelector requires a non-empty 'groupBy'.")
        for field in ("baseline_column", "baseline_value", "predicate_column"):
            if not getattr(self, field):
                raise ValueError(f"GroupPredicateSelector requires '{field}'.")
        if self.drop_when not in _DROP_WHEN:
            raise ValueError(
                f"GroupPredicateSelector 'drop_when' must be one of {sorted(_DROP_WHEN)}."
            )
        if self.action not in _ACTIONS:
            raise ValueError(f"GroupPredicateSelector 'action' must be one of {sorted(_ACTIONS)}.")
        return True

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        super()._verify_preconditions(data_frame)
        needed = [*self.group_by, self.baseline_column, self.predicate_column]
        missing = [c for c in needed if c not in data_frame.columns]
        if missing:
            raise ValueError(f"GroupPredicateSelector: columns not found: {missing}")
        return True

    def _holds(self, value: Any) -> bool:
        is_zero = value == 0
        is_nan = pd.isna(value)
        if self.drop_when == "zero_or_nan":
            return bool(is_nan or is_zero)
        if self.drop_when == "nan":
            return bool(is_nan)
        return bool(is_zero)

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        self._verify_preconditions(data_frame)
        result = data_frame.copy()

        baseline = result[result[self.baseline_column] == self.baseline_value]
        per_group = baseline.groupby(self.group_by)[self.predicate_column].first()
        flagged = {key for key, value in per_group.items() if self._holds(value)}

        if len(self.group_by) == 1:
            in_flagged = result[self.group_by[0]].isin(flagged)
        else:
            row_keys = result[self.group_by].itertuples(index=False, name=None)
            in_flagged = pd.Series([key in flagged for key in row_keys], index=result.index)

        keep = in_flagged if self.action == "keep" else ~in_flagged
        return result[keep].reset_index(drop=True)
