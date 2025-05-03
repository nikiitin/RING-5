from argumentParser import AnalyzerInfo
from src.data_management.dataManager import DataManager
import src.utils.utils as utils
import pandas as pd

class Mixer(DataManager):
    """
    Class to rename columns in a DataFrame.
    Inherits from the DataManager class.
    """
    def _verifyParams(self):
        super()._verifyParams()
        # Check if the mixer is a dictionary
        if not isinstance(self._mixerElement, dict):
            raise ValueError("Mixer element is not correctly defined at json file")
        
        # Check if the mixer is empty
        if not self._mixerElement:
            raise ValueError("Mixer element is empty at json file")


    def __init__(self, params: AnalyzerInfo) -> None:
        """
        Constructor for the Mixer class. Instance the class only
        if the mixer is present in the json file.
        Args:
            params: The parameters for the renamer.
        """
        super().__init__(params)
        # Check if the renamer is present in the json file
        utils.checkElementExists(self._json, "mixer")
        self._mixerElement = self._json["mixer"]

    def __call__(self):
        """
        Mix several stats into a single statistic. The name is given by the
        key of the dictionary and the values are the columns to be mixed.
        """
        super().__call__()
        # Mix the columns in the DataFrame and create a new column with the name being the key
        for key, value in self._mixerElement.items():
            # Check if the columns to be mixed exist in the DataFrame
            for column in value:
                if column not in self._df.columns:
                    raise ValueError(f"Column {column} does not exist in the DataFrame")
            # Mix the columns and create a new column with the name being the key
            self._df[key] = self._df[value].sum(axis=1)