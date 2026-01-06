import pandas as pd

import src.utils.utils as utils
from src.processing.managers.base_manager import DataManager
from src.processing.managers.params import DataManagerParams


class SeedsReducer(DataManager):
    """
    This manager is used to remove the seeds column from the DataFrame
    and calculate the mean and standard deviation from the values of all
    the numeric statistics (columns).
    """

    def _verifyParams(self):
        super()._verifyParams()
        # Ensure the random_seed column exists
        if "random_seed" not in DataManager._df.columns:
            raise ValueError("The 'random_seed' column is missing from the DataFrame.")
        # Seeds reducer is a boolean
        if not isinstance(self._seedsReducerElement, bool):
            raise ValueError(
                "Seeds reducer element is not correctly defined at json file. Must be a boolean"
            )
        # Verify none of the categorical columns contain only "NaN" values
        for column in DataManager._categorical_columns:
            if DataManager._df[column].isnull().all():
                raise ValueError(
                    f"The categorical column {column} contains only NaN values, which is not "
                    "allowed.",
                    "Please check the parsing info and stats files for missing values.",
                )

    def __init__(self, params: DataManagerParams, json: dict) -> None:
        """
        Constructor for the seedsReducer class. Instance the class only
        if the seedsReducer is present in the json file.
        Args:
            params: The analyzer info object.
        """
        super().__init__(params, json)
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
            print("Reducing seeds...")
            # Group by categorical columns and calculate mean and standard deviation
            grouped = DataManager._df.groupby(DataManager._categorical_columns)

            # Calculate mean and standard deviation for each group
            # Reset index to flatten the DataFrame
            mean_df = grouped[DataManager._statistic_columns].mean().reset_index()
            std_df = grouped[DataManager._statistic_columns].std().reset_index()

            # Rename standard deviation columns to include '_std'
            std_df = std_df.rename(
                columns=lambda x: f"{x}.sd" if x in DataManager._statistic_columns else x
            )

            # Merge mean and standard deviation DataFrames
            result_df = pd.merge(mean_df, std_df, on=DataManager._categorical_columns)
            correct_order = DataManager._categorical_columns + [
                col for col in result_df.columns if col not in DataManager._categorical_columns
            ]
            # Sort the columns for categorical columns first
            result_df = result_df.reindex(correct_order, axis=1)

            # Update the DataFrame with the reduced data
            DataManager._df = result_df
