from argumentParser import AnalyzerInfo
from abc import ABC, abstractmethod
import src.utils.utils as utils
import pandas as pd

class DataManager:

    _df = None
    _categorical_columns = None
    _statistic_columns = None
    _csvPath = None
    def __init__(self, params: AnalyzerInfo, json: dict) -> None:
        """
        Constructor for the DataManager class.
        Args:
            params (AnalyzerInfo): The parameters for the data manager.
        """
        if DataManager._csvPath is None:
            DataManager._csvPath = params.getWorkCsv()
        if DataManager._df is None:
            if utils.checkFileExists(DataManager._csvPath):
                DataManager._df = pd.read_csv(DataManager._csvPath, header=0, delim_whitespace=True)
            else:
                raise FileNotFoundError(f"The file {DataManager._csvPath} does not exist.")

        # This should be the json dictionary that contains the parameters for all the managers
        self._json = json
        # Retrieve the categorical columns from the parameters.
        # This will be useful for all the managers that inherit from this class.
        if DataManager._categorical_columns is None:
            # Get the categorical columns from the parameters
            DataManager._categorical_columns = params.getCategoricalColumns()
            # Set categorical columns to exclude 'random_seed'
            DataManager._categorical_columns.remove("random_seed")
        # Identify numeric statistic columns (all columns not in categorical_columns or 'random_seed').
        if DataManager._statistic_columns is None:
            DataManager._statistic_columns = [col for col in DataManager._df.columns if col not in DataManager._categorical_columns and col != "random_seed"]


    @abstractmethod
    def _verifyParams(self) -> None:
        """
        Verify that the manager is valid, else raise an exception.
        Raises:
            ValueError: If the DataFrame is empty.
        """
        # Check if the DataFrame is empty
        if DataManager._df.empty:
            raise ValueError("DataFrame is empty")
        # Ensure all specified categorical columns exist in the DataFrame
        missing_columns = set(DataManager._categorical_columns) - set(self._df.columns.astype(str))
        if missing_columns:
            raise ValueError(f"The following categorical columns are missing from the DataFrame: {list(missing_columns)}")
        pass

    @abstractmethod
    def __call__(self) -> None:
        """
        Main functionality of the DataManager class.
        Loads the csv file into a DataFrame
        """
        self._verifyParams()
        pass

    @classmethod
    def persist(cls) -> None:
        """
        Persist the DataFrame to a csv file.
        """
        if cls._df is not None:
            cls._df.to_csv(cls._csvPath, index=False, sep=" ")
            print(f"DataFrame persisted to {cls._csvPath}")
        else:
            print("DataFrame is None, cannot persist.")