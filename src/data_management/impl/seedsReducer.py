from argumentParser import AnalyzerInfo
from src.data_management.dataManager import DataManager
import src.utils.utils as utils
import pandas as pd

class seedsReducer(DataManager):
    """
    This manager is used to remove the seeds column from the DataFrame
    and calculate the mean and standard deviation from the values of all
    the numeric statistics (columns).
    """
    def _verifyParams(self):
        super()._verifyParams()
        # Ensure the random_seed column exists
        if "random_seed" not in self._df.columns:
            raise ValueError("The 'random_seed' column is missing from the DataFrame.")
        # Seeds reducer is a boolean
        if not isinstance(self._seedsReducerElement, bool):
            raise ValueError("Seeds reducer element is not correctly defined at json file. Must be a boolean")

    def __init__(self, params: AnalyzerInfo) -> None:
        """
        Constructor for the seedsReducer class. Instance the class only
        if the seedsReducer is present in the json file.
        Args:
            params: The analyzer info object.
        """
        super().__init__(params)
        # Check if the seedsReducer is present in the json file
        utils.checkElementExists(self._json, "seedsReducer")
        self._seedsReducerElement = self._json["seedsReducer"]

def __call__(self):
    """
    Remove the seeds column from the DataFrame and calculate the mean
    and standard deviation from the values of all the numeric statistics (columns).
    """
    super().__call__()
    # Check if the seedsReducer is set to True
    if self._seedsReducerElement:
        # Identify numeric statistic columns (all columns not in categorical_columns or 'random_seed').
        # Note that categorical_columns already includes 'random_seed'.
        statistic_columns = [col for col in self._df.columns if col not in self._categorical_columns]
        
        # Remove 'random_seed' from statistic_columns
        statistic_columns.remove("random_seed")
        # Set categorical columns to exclude 'random_seed'
        self._categorical_columns.remove("random_seed")

        # Group by categorical columns and calculate mean and standard deviation
        grouped = self._df.groupby(self._categorical_columns)
        mean_df = grouped[statistic_columns].mean().reset_index()
        std_df = grouped[statistic_columns].std().reset_index()

        # Rename standard deviation columns to include '_std'
        std_df = std_df.rename(columns=lambda x: f"{x}_sd" if x in statistic_columns else x)

        # Merge mean and standard deviation DataFrames
        result_df = pd.merge(mean_df, std_df, on=self._categorical_columns)

        # Update the DataFrame with the reduced data
        self._df = result_df