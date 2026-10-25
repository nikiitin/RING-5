"""Row filtering through one explicit predicate and its validated operands."""

import operator
from collections.abc import Callable
from typing import Any

import pandas as pd

from src.core.services.shapers.definition import PREDICATE_OPERANDS
from src.core.services.shapers.impl.selector import Selector

_COMPARISONS: dict[str, Callable[[Any, Any], Any]] = {
    "greater_than": operator.gt,
    "less_than": operator.lt,
    "greater_or_equal": operator.ge,
    "less_or_equal": operator.le,
    "equals": operator.eq,
    "not_equals": operator.ne,
}


class ConditionSelector(Selector):
    """Filter rows with an explicit comparison, range, membership, or substring mode."""

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Return an independent filtered frame without changing the input."""
        # [impl->req~ring5.shaping.condition-selector~1]
        self._verify_preconditions(data_frame)
        values = data_frame[self.column]
        mode = self.params["mode"]
        if mode == "in":
            mask = values.isin(self.params["values"])
        elif mode == "range":
            lower, upper = self.params["range"]
            mask = (values >= lower) & (values <= upper)
        elif mode == "contains":
            mask = values.astype(str).str.contains(self.params["value"], na=False, regex=False)
        else:
            mask = _COMPARISONS[mode](values, self.params[PREDICATE_OPERANDS[mode]])
        return data_frame[mask].copy()
