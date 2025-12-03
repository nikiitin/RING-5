from src.data_plotter.src.shaper.impl.selector import Selector
from typing import Any
import src.utils.utils as utils
import pandas as pd

class ItemSelector(Selector):
    """
    ItemSelector is a Selector that selects items based on a specified list of strings.
    """

    # Generate getters and setters for the column and strings attributes
    @property
    def _strings(self) -> list:
        return self._strings_data
    @_strings.setter
    def _strings(self, value: Any) -> None:
        utils.checkVarType(value, list)
        for string in value:
            utils.checkVarType(string, str)
        self._strings_data = value

    def __init__(self, params: dict):
        super().__init__(params)
        self._column = utils.getElementValue(self._params, "column")
        self._strings = utils.getElementValue(self._params, "strings")

    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()
        # The column that must be present in the DataFrame
        utils.checkElementExists(self._params, "column")
        # Check if the 'strings' parameter exists
        utils.checkElementExists(self._params, "strings")
        return verified

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        verified = super()._verifyPreconditions(data_frame)
        # Check if at least one provided string is in the DataFrame
        # at the specified column
        if not any(data_frame[self._column].astype(str).str.contains('|'.join(self._strings), na=False)):
            print("Warning: None of the provided strings are present in the DataFrame at the specified column. No items will be selected.")
            verified = False
        # Print a warning in case a string is not in the DataFrame
        for string in self._strings:
            if not data_frame[self._column].astype(str).str.contains(string, na=False).any():
                print(f"Warning: The string '{string}' is not present in the DataFrame at the specified column.")
        return verified

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Main functionality of the ItemSelector class.
        Selects items from the DataFrame that match the specified strings.
        """
        data_frame = super().__call__(data_frame)
        # Select items based on the specified strings
        return data_frame[data_frame[self._column].astype(str).str.contains('|'.join(self._strings), na=False)]

# Main function to test the Iselector class
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
        'column': 'system_id',
        'strings': ['S1', 'S3']
    }
    print("input: ")
    print(df)
    shaper = ItemSelector(params)
    df = shaper(df)
    print("result: ")
    print(df)