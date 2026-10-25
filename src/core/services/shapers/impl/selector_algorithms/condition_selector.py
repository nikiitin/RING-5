"""Row filtering through one explicit predicate and its validated operands."""

import math
import operator
from collections.abc import Callable
from numbers import Real
from typing import Any

import pandas as pd

from src.core.common.security_limits import MAX_SEARCH_TERM_LENGTH
from src.core.models.shaper_models import ConditionSelectorConfig
from src.core.services.shapers.impl.selector import Selector

_COMPARISONS: dict[str, Callable[[Any, Any], Any]] = {
    "greater_than": operator.gt,
    "less_than": operator.lt,
    "greater_or_equal": operator.ge,
    "less_or_equal": operator.le,
    "equals": operator.eq,
    "not_equals": operator.ne,
}
_OPERANDS = {
    "greater_than": "threshold",
    "less_than": "threshold",
    "greater_or_equal": "threshold",
    "less_or_equal": "threshold",
    "equals": "value",
    "not_equals": "value",
    "contains": "value",
    "range": "range",
    "in": "values",
}
_PREDICATE_FIELDS = frozenset(_OPERANDS.values())


def _finite_number(value: object) -> bool:
    """Check real bounds without accepting booleans or overflowing huge integers."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


class ConditionSelector(Selector):
    """Filter rows with an explicit comparison, range, membership, or substring mode."""

    def _verify_params(self) -> bool:
        """Reject missing, contradictory, or malformed predicate operands."""
        super()._verify_params()
        unknown = sorted(set(self.params) - ConditionSelectorConfig.__annotations__.keys())
        if unknown:
            raise ValueError("ConditionSelector: unsupported fields: " + ", ".join(unknown) + ".")
        mode = self.params.get("mode")
        if not isinstance(mode, str) or mode not in _OPERANDS:
            raise ValueError("ConditionSelector: 'mode' must be an explicit supported predicate.")
        field = _OPERANDS[mode]
        present = set(self.params) & _PREDICATE_FIELDS
        if present != {field}:
            raise ValueError(f"ConditionSelector: '{mode}' requires only the '{field}' operand.")
        value = self.params[field]
        if field == "threshold" and not _finite_number(value):
            raise ValueError("ConditionSelector: 'threshold' must be a finite number.")
        if field == "range":
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError("ConditionSelector: 'range' must be a list of 2 values.")
            if not all(_finite_number(bound) for bound in value) or value[0] > value[1]:
                raise ValueError("ConditionSelector: 'range' must contain ordered finite bounds.")
        if field == "values":
            if not isinstance(value, list):
                raise TypeError("ConditionSelector: 'values' must be a list.")
            if any(
                item is not None and not isinstance(item, (str, int, float, bool)) for item in value
            ):
                raise TypeError("ConditionSelector: membership values must be JSON scalars.")
        if field == "value" and value is None:
            raise ValueError(f"ConditionSelector: '{mode}' requires a non-null 'value'.")
        if field == "value" and not isinstance(value, (str, int, float, bool)):
            raise TypeError("ConditionSelector: 'value' must be a scalar.")
        if mode == "contains":
            if not isinstance(value, str):
                raise TypeError("ConditionSelector: 'contains' requires a text 'value'.")
            if len(value) > MAX_SEARCH_TERM_LENGTH:
                raise ValueError(
                    f"ConditionSelector contains values cannot exceed "
                    f"{MAX_SEARCH_TERM_LENGTH} characters."
                )
        return True

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
            mask = _COMPARISONS[mode](values, self.params[_OPERANDS[mode]])
        return data_frame[mask].copy()
