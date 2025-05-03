from argumentParser import AnalyzerInfo
import src.utils.utils as utils
import pandas as pd

class DataManager:

    loadedCsv = None

    def __init__(self, params: AnalyzerInfo, json: dict) -> None:
        """
        Constructor for the DataManager class.
        Args:
            params (AnalyzerInfo): The parameters for the data manager.
        """
        self._csvPath = params.getWorkCsv()
        if utils.checkFileExists(self._csvPath):
            self._df = pd.read_csv(self._csvPath)
        # This should be the json dictionary that contains the parameters for all the managers
        self._json = json
        # Retrieve the categorical columns from the parameters.
        # This will be useful for all the managers that inherit from this class.
        self._categorical_columns = params.getCategoricalColumns()
    
    def _verifyParams(self) -> None:
        """
        Verify that the manager is valid, else raise an exception.
        Raises:
            ValueError: If the DataFrame is empty.
        """
        # Check if the DataFrame is empty
        if self._df.empty:
            raise ValueError("DataFrame is empty")
        # Ensure all specified categorical columns exist in the DataFrame
        missing_columns = [col for col in self._categorical_columns if col not in self._df.columns]
        if missing_columns:
            raise ValueError(f"The following categorical columns are missing from the DataFrame: {missing_columns}")
        pass

    def __call__(self) -> None:
        """
        Main functionality of the DataManager class.
        Loads the csv file into a DataFrame
        """
        self._verifyParams()
        # Load the csv file into a DataFrame if it is not already loaded
        if DataManager.loadedCsv is None:
            DataManager.loadedCsv = pd.read_csv(self._csvPath)
        pass