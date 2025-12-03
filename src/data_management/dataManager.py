from argumentParser import AnalyzerInfo
from typing import Any, ClassVar
from abc import ABC, abstractmethod
import src.utils.utils as utils
import pandas as pd

class MetaDataManager(type):
    """
    Meta class for the DataManager class.
    """
    @property
    def _df(cls) -> pd.DataFrame:
        return cls._df_data
    @_df.setter
    def _df(cls, value: Any) -> None:
        utils.checkVarType(value, pd.DataFrame)
        # Check the dataframe is not empty
        if value.empty:
            raise ValueError("The dataframe is empty")
        cls._df_data = value
    @property
    def _categorical_columns(cls) -> list:
        return cls._categorical_columns_data
    @_categorical_columns.setter
    def _categorical_columns(cls, value: Any) -> None:
        utils.checkVarType(value, list)
        # Check the strings are not empty
        for col in value:
            utils.checkVarType(col, str)
            if col == "":
                raise ValueError("The categorical columns list contains empty strings")
        cls._categorical_columns_data = value
    @property
    def _statistic_columns(cls) -> list:
        return cls._statistic_columns_data
    @_statistic_columns.setter
    def _statistic_columns(cls, value: Any) -> None:
        utils.checkVarType(value, list)
        # Check the strings are not empty
        for col in value:
            utils.checkVarType(col, str)
            if col == "":
                raise ValueError("The statistic columns list contains empty strings")
        cls._statistic_columns_data = value
    @property
    def _csvPath(cls) -> str:
        return cls._csvPath_data
    @_csvPath.setter
    def _csvPath(cls, value: str) -> None:
        utils.checkVarType(value, str)
        if value == "":
            raise ValueError("The csv path is empty")
        if not utils.checkFileExists(value):
            raise ValueError("The csv path does not exist")
        cls._csvPath_data = value

class DataManager(metaclass=MetaDataManager):
    """
    Generic data manager class. A data manager is responsible for managing some properties
    of the data. It is used to preprocess the data, rename, mix columns, reduce the seeds, etc.
    """
    _df_data = None
    _categorical_columns_data = None
    _statistic_columns_data = None
    _csvPath_data = None

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
                DataManager._df = pd.read_csv(DataManager._csvPath, header=0, sep='\s+')
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
        if DataManager._df is None:
            raise ValueError("DataFrame is not initialized")
        if DataManager._df.empty:
            raise ValueError("DataFrame is empty")
        # Ensure all specified categorical columns exist in the DataFrame
        if DataManager._categorical_columns is None:
            raise ValueError("Categorical columns are not initialized")
        
        missing_columns = set(DataManager._categorical_columns) - set(DataManager._df.columns.astype(str))
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
        if DataManager._df is not None:
            DataManager._df.to_csv(DataManager._csvPath, index=False, sep=" ")
            print(f"DataFrame persisted to {DataManager._csvPath}")
        else:
            print("DataFrame is None, cannot persist.")