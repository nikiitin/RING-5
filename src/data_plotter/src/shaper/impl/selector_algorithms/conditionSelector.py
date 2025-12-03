from src.data_plotter.src.shaper.impl.selector import Selector
from typing import Any
import src.utils.utils as utils
import pandas as pd

class ConditionSelector(Selector):
    """
    ConditionSelector is a Selector that selects items based on a specified condition.
    It can be used to filter data before further processing or analysis.
    """
    # Getters and setters
    @property
    def _condition(self) -> str:
        return self._condition_data
    @_condition.setter
    def _condition(self, value: Any) -> None:
        utils.checkVarType(value, str)
        if value not in ["<", ">", "<=", ">=", "==", "!="]:
            raise ValueError("The 'condition' parameter must be one of the following: '<', '>', '<=', '>=', '==', '!='.")
        self._condition_data = value
    @property
    def _value(self) -> int | float:
        return self._value_data
    @_value.setter
    def _value(self, value: Any) -> None:
        if not isinstance(value, int) and not isinstance(value, float):
            raise ValueError(f"The 'value' parameter must be an int or a float. Got: {type(value)}")
        self._value_data = value

    def __init__(self, params: dict):
        super().__init__(params)
        self._condition = utils.getElementValue(self._params, "condition")
        self._value = utils.getElementValue(self._params, "value")


    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()
        # The condition that must be applied
        utils.checkElementExists(self._params, "condition")
        # The value that must be used in the condition
        utils.checkElementExists(self._params, "value")
        return verified
    
    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:

        verified = super()._verifyPreconditions(data_frame)
        # Check if condition is valid
        if self._condition not in ["==", ">", "<", ">=", "<=", "!="]:
            raise ValueError(f"Invalid condition '{self._condition}'.")
        return verified

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        super().__call__(data_frame)
        # Select items based on the specified condition
        return data_frame.query(f"{self._column} {self._condition} {self._value}")
    
# Main function to test the Cselector class
def test():
    # Create a sample data frame
    df = pd.DataFrame({
    'system_id': ['S1', 'S1', 'S1', 'S1', 'S2', 'S2', 'S2', 'S2', 'S3', 'S3', 'S3', 'S3'],
    'benchmark': ['B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2'],
    'throughput': [100, 105, 120, 118, 80, 82, 78, 85, 90, 95, 100, 102],
    'latency': [1.2, 1.1, 1.5, 1.4, 2.0, 1.9, 2.1, 2.2, 1.8, 1.7, 1.6, 1.5],
    'config_param': ['A1', 'A1', 'A2', 'A2', 'B1', 'B1', 'B2', 'B2', 'C1', 'C1', 'C2', 'C2']
    })
    params = {
        'column': "throughput",
        'condition': '>=',
        'value': 100
    }
    print("input: ")
    print(df)
    shaper = ConditionSelector(params)
    df = shaper(df)
    print("result: ")
    print(df)