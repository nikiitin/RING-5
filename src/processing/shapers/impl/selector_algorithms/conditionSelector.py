import pandas as pd

from src.processing.shapers.impl.selector import Selector


class ConditionSelector(Selector):
    """
    ConditionSelector is a Selector that selects items based on a specified condition.
    It supports numeric comparisons, ranges, and categorical inclusion.
    """

    def __init__(self, params: dict):
        # Initialize attributes before super() to ensure they exist
        self._mode = params.get("mode", "legacy")
        self._condition = params.get("condition")
        self._value = params.get("value")
        self._threshold = params.get("threshold")
        self._range = params.get("range")
        self._values = params.get("values")
        
        super().__init__(params)

    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()

        # Verify based on what parameters are present
        if self._values is not None:
            # Categorical mode
            if not isinstance(self._values, list):
                raise ValueError("'values' must be a list")
        elif self._range is not None:
            # Range mode
            if not isinstance(self._range, list) or len(self._range) != 2:
                raise ValueError("'range' must be a list of 2 values")
        elif self._mode == "greater_than" or self._mode == "less_than":
            if self._threshold is None:
                raise ValueError(f"'{self._mode}' mode requires 'threshold'")
        elif self._mode == "equals":
            if self._value is None:
                raise ValueError("'equals' mode requires 'value'")
        elif self._condition is not None and self._value is not None:
            # Legacy mode
            if self._condition not in ["<", ">", "<=", ">=", "==", "!="]:
                raise ValueError(
                    "The 'condition' parameter must be one of: '<', '>', '<=', '>=', '==', '!='."
                )
        else:
            # If we are here, we might have a missing parameter configuration
            # But we allow initialization, validation happens at runtime or we can be strict here.
            pass

        return verified

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        return super()._verifyPreconditions(data_frame)

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        super().__call__(data_frame)

        col = self._column

        # 1. Categorical / List of values
        if self._values is not None:
            return data_frame[data_frame[col].isin(self._values)]

        # 2. Range
        if self._range is not None:
            min_val, max_val = self._range
            return data_frame[(data_frame[col] >= min_val) & (data_frame[col] <= max_val)]

        # 3. Explicit Modes from UI
        if self._mode == "greater_than":
            return data_frame[data_frame[col] > self._threshold]
        elif self._mode == "less_than":
            return data_frame[data_frame[col] < self._threshold]
        elif self._mode == "equals":
            return data_frame[data_frame[col] == self._value]

        # 4. Legacy Condition
        if self._condition is not None and self._value is not None:
            return data_frame.query(f"{col} {self._condition} {self._value}")

        return data_frame


# Main function to test the Cselector class
def test():
    # Create a sample data frame
    df = pd.DataFrame(
        {
            "system_id": ["S1", "S1", "S1", "S1", "S2", "S2", "S2", "S2", "S3", "S3", "S3", "S3"],
            "benchmark": ["B1", "B2", "B1", "B2", "B1", "B2", "B1", "B2", "B1", "B2", "B1", "B2"],
            "throughput": [100, 105, 120, 118, 80, 82, 78, 85, 90, 95, 100, 102],
            "latency": [1.2, 1.1, 1.5, 1.4, 2.0, 1.9, 2.1, 2.2, 1.8, 1.7, 1.6, 1.5],
            "config_param": [
                "A1",
                "A1",
                "A2",
                "A2",
                "B1",
                "B1",
                "B2",
                "B2",
                "C1",
                "C1",
                "C2",
                "C2",
            ],
        }
    )
    params = {"column": "throughput", "condition": ">=", "value": 100}
    print("input: ")
    print(df)
    shaper = ConditionSelector(params)
    df = shaper(df)
    print("result: ")
    print(df)
