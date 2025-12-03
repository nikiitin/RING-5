from argumentParser import AnalyzerInfo
from src.data_management.dataManager import DataManager
import src.utils.utils as utils

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

        # Verify that the keys are strings, not previously present in the DataFrame
        # and that all source columns are present in the DataFrame
        for key, values in self._mixerElement.items():
            # Check if the key is a string
            if not isinstance(key, str):
                raise ValueError(f"Key {key} is not a string")
            # Check if the key is not already in the DataFrame
            if key in DataManager._df.columns:
                raise ValueError(f"Dst {key} is already in the DataFrame")
            # Check if the values are an iterable
            if not isinstance(values, list):
                raise ValueError(f"Values for {key} are not a list")
            # Check if the values are in the DataFrame
            for value in values:
                if value not in DataManager._df.columns:
                    print(f"Value {value} is not in the DataFrame")
                    raise ValueError(f"Source value {value} is not in the DataFrame")

    def __init__(self, params: AnalyzerInfo, json: dict) -> None:
        """
        Constructor for the Mixer class. Instance the class only
        if the mixer is present in the json file.
        Args:
            params: The parameters for the renamer.
        """
        super().__init__(params, json)
        # Check if the renamer is present in the json file
        utils.checkElementExists(self._json, "mixer")
        self._mixerElement = self._json["mixer"]
        

    def __call__(self):
        """
        Mix several stats into a single statistic. The name is given by the
        key of the dictionary and the values are the columns to be mixed.
        """
        super().__call__()
        if self._mixerElement:
            # Mix the columns in the DataFrame and create a new column with the name being the key
            # Mixer are defined as a dictionary, where the key is the name of the new column
            # and the values are the columns to be mixed.
            for key, values in self._mixerElement.items():
                print("Mixing columns:", end=" ")
                # Check if the values are a list
                mixed_column = None
                for value in values:
                    print(f" {value}", end=",")
                    # The values are the columns to be mixed
                    if mixed_column is None:
                        mixed_column = DataManager._df[value]
                    else:
                        mixed_column += DataManager._df[value]
                # Create the new column with the name being the key
                print(f"  | into: {key}")
                DataManager._df[key] = mixed_column
                # Add the new column to the statistic columns
                DataManager._statistic_columns.append(key)
