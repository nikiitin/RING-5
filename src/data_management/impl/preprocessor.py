from argumentParser import AnalyzerInfo
from src.data_management.dataManager import DataManager
import src.utils.utils as utils
import pandas as pd

class operator:
    """
    Class to define the operator to be used in the preprocessor.
    """
    def __call__(self, dataFrame: pd.DataFrame, src1: str, src2: str, dst: str) -> pd.DataFrame:
        """
        Method to be implemented by the operator.
        """
        raise NotImplementedError("Operator not implemented")

class DivideOperator(operator):
    """
    Class to define the divide operator.
    """
    def __call__(self, dataFrame: pd.DataFrame, src1: str, src2: str, dst: str) -> pd.DataFrame:
        # Divide the src1 column by the src2 column and store the result in the dst column.
        # Avoid division by zero by letting the result be the src1 column
        # if the src2 column is zero.
        print(f"Dividing {src1} by {src2} and storing the result in {dst}")
        dataFrame[dst] = dataFrame[src1] / dataFrame[src2].replace(0, 1)
        return dataFrame
    
class SumOperator(operator):
    """
    Class to define the sum operator.
    """
    def __call__(self, dataFrame: pd.DataFrame, src1: str, src2: str, dst: str) -> pd.DataFrame:
        # Sum the src1 column and the src2 column and store the result in the dst column.
        print(f"Summing {src1} and {src2} and storing the result in {dst}")
        dataFrame[dst] = dataFrame[src1] + dataFrame[src2]
        return dataFrame


class OperatorFactory:
    """
    Factory class to create the operator.
    """
    @classmethod
    def getOperator(cls, operator: str):
        if operator == "divide":
            return DivideOperator()
        if operator == "sum":
            return SumOperator()
        raise ValueError(f"Operator {operator} not implemented")

class Preprocessor(DataManager):
    """
    Class to divide a column by other column in
    a data frame.
    """
    def _verifyParams(self):
        super()._verifyParams()
        # Check if the divider is a dictionary
        if not isinstance(self._preprocessorElement, dict):
            raise ValueError("Preprocessor element is not correctly defined at json file")
        
        # Check if the divider is empty
        if not self._preprocessorElement:
            raise ValueError("Preprocessor element is empty at json file")

        # Verify that the keys are strings, not previously present in the DataFrame
        # and that all source columns are present in the DataFrame
        for key, values in self._preprocessorElement.items():
            # Check if the key is a string
            if not isinstance(key, str):
                raise ValueError(f"Key {key} is not a string")
            # Check if the key is not already in the DataFrame
            if key in DataManager._df.columns:
                raise ValueError(f"Dst {key} is already in the DataFrame")
            utils.checkElementExists(values, "operator")
            utils.checkElementExists(values, "src1")
            utils.checkElementExists(values, "src2")
    
    def __init__(self, params, json):
        super().__init__(params, json)
        # Check if the preprocessor is present in the json file
        utils.checkElementExists(self._json, "preprocessor")
        self._preprocessorElement = self._json["preprocessor"]

    def __call__(self):
        """
        For every element in the preprocessor, get the operator and
        apply it to the data frame.
        """
        super().__call__()
        if self._preprocessorElement:
            # Apply the operator to the data frame
            for key, values in self._preprocessorElement.items():
                # Get the operator
                operator = OperatorFactory.getOperator(values["operator"])
                # Apply the operator to the data frame
                DataManager._df = operator(DataManager._df, values["src1"], values["src2"], key)
                # Add the new column to the statistic columns
                DataManager._statistic_columns.append(key)
    
