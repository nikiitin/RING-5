from typing import Any, Callable, Dict, List, Optional, cast

import pandas as pd

from src.core.services.shapers.impl.selector import Selector


class ConditionSelector(Selector):
    """
    Shaper that filters rows based on numeric or categorical conditions.

    Supports:
    - Numeric comparisons (greater_than, less_than, equals)
    - Range queries (min <= x <= max)
    - Categorical inclusion (isin list)
    - Substring matching (contains)
    - Legacy direct comparison strings (<, >, ==, etc.)
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize ConditionSelector.

        Args:
            params: Dictionary containing 'column' and one or more filter definitions:
                - mode (str): 'greater_than', 'less_than', 'equals', 'contains', 'legacy'
                - threshold (float): threshold for numeric modes
                - range (List[float]): [min, max] for range mode
                - values (List[Any]): Allowed values for categorical mode
                - condition (str): operator for legacy mode
                - value (Any): comparison value for legacy/equals/contains mode
        """
        # Load parameters with defaults BEFORE super().__init__
        # because super().__init__ calls _verify_params which uses these.
        self.mode: str = params.get("mode", "legacy")
        self.condition: Optional[str] = params.get("condition")
        self.value: Any = params.get("value")
        self.threshold: Optional[float] = params.get("threshold")
        self.range: Optional[List[float]] = params.get("range")
        self.values: Optional[List[Any]] = params.get("values")

        super().__init__(params)

    def _verify_params(self) -> bool:
        """Validate that the parameter combination is sufficient for filtering."""
        super()._verify_params()

        if self.params.get("values") is not None:
            if not isinstance(self.params["values"], list):
                raise TypeError("ConditionSelector: 'values' must be a list.")

        elif self.params.get("range") is not None:
            r = self.params["range"]
            if not isinstance(r, list) or len(r) != 2:
                raise ValueError("ConditionSelector: 'range' must be a list of 2 values.")

        elif self.mode == "greater_than" or self.mode == "less_than":
            if self.params.get("threshold") is None:
                raise ValueError(f"ConditionSelector: '{self.mode}' mode requires 'threshold'.")

        elif self.mode == "equals" or self.mode == "contains":
            if self.params.get("value") is None:
                raise ValueError(f"ConditionSelector: '{self.mode}' mode requires 'value'.")

        elif self.condition is not None and self.value is not None:
            valid_ops = ["<", ">", "<=", ">=", "==", "!="]
            if self.condition not in valid_ops:
                raise ValueError(f"ConditionSelector: Invalid legacy operator '{self.condition}'.")

        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Execute the filtering logic."""
        self._verify_preconditions(data_frame)

        col = self.column
        # 1. Categorical inclusion
        if self.values is not None:
            return data_frame[data_frame[col].isin(self.values)]

        # 2. Numeric Range
        if self.range is not None:
            v_min, v_max = self.range
            mask = (data_frame[col] >= v_min) & (data_frame[col] <= v_max)
            return data_frame[mask]

        # 3. Explicit UI Modes
        if self.mode == "greater_than":
            return data_frame[data_frame[col] > self.threshold]
        elif self.mode == "less_than":
            return data_frame[data_frame[col] < self.threshold]
        elif self.mode == "equals":
            # Equality comparison may return Any in some pandas contexts
            return cast(pd.DataFrame, data_frame[data_frame[col] == self.value])
        elif self.mode == "contains":
            mask = data_frame[col].astype(str).str.contains(str(self.value), na=False)
            return data_frame[mask]

        # 4. Legacy Operator/Value pair
        if self.condition is not None and self.value is not None:
            # Handle potential quoted strings in legacy values if they come from old UI/Configs
            val = self.value
            if isinstance(val, str) and len(val) >= 2:
                if (val.startswith("'") and val.endswith("'")) or (
                    val.startswith('"') and val.endswith('"')
                ):
                    val = val[1:-1]

            ops = {
                "<": lambda x, y: x < y,
                ">": lambda x, y: x > y,
                "<=": lambda x, y: x <= y,
                ">=": lambda x, y: x >= y,
                "==": lambda x, y: x == y,
                "!=": lambda x, y: x != y,
            }
            typed_ops: Dict[str, Callable[[Any, Any], Any]] = ops
            if self.condition in typed_ops:
                # Lambda returns Any - cast to document DataFrame return
                return cast(
                    pd.DataFrame, data_frame[typed_ops[self.condition](data_frame[col], val)]
                )

        return data_frame
