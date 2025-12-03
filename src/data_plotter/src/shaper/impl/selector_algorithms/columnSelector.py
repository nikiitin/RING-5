import pandas as pd
from src.data_plotter.src.shaper.impl.selector import Selector
from typing import Any
import src.utils.utils as utils
class ColumnSelector(Selector):
    """
    ColumnSelector is a Selector that selects columns based on a specified list of strings.
    """
    # Getters and setters
    @property
    def _columns(self) -> list:
        return self._columns_data
    @_columns.setter
    def _columns(self, value: Any) -> None:
        utils.checkVarType(value, list)
        # Check the strings are not empty
        for col in value:
            utils.checkVarType(col, str)
            if col == "":
                raise ValueError("The 'columns' parameter must not contain empty strings.")
        self._columns_data = value

    def __init__(self, params: dict) -> None:
        self._params = params
        self._columns = utils.getElementValue(self._params, "columns")

    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()
        utils.checkElementExists(self._params, "columns")
        return verified

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        verified = super()._verifyPreconditions(data_frame)
        # Check that all columns exist in the data frame
        for column in self._columns:
            if column not in data_frame.columns:
                verified = False
                print(f"Warning: The column '{column}' does not exist in the data frame.")
        return verified

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        # Select the columns
        return data_frame[self._columns]


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
        'columns': ["throughput", "latency", "config_param", "benchmark"]
    }
    print("input: ")
    print(df)
    shaper = ColumnSelector(params)
    df = shaper(df)
    print("result: ")
    print(df)