from argumentParser import AnalyzerInfo

import src.utils.utils as utils
from src.data_management.dataManager import DataManager


class Renamer(DataManager):
    """
    Class to rename columns in a DataFrame.
    Inherits from the DataManager class.
    """

    def _verifyParams(self):
        super()._verifyParams()
        # Check if the renamer is a dictionary
        if not isinstance(self._renamerElement, dict):
            raise ValueError("Renamer element is not correctly defined at json file")

        # Check if the renamer is empty
        if not self._renamerElement:
            raise ValueError("Renamer element is empty at json file")

    def __init__(self, params: AnalyzerInfo, json: dict) -> None:
        """
        Constructor for the Renamer class. Instance the class only
        if the renamer is present in the json file.
        Args:
            params: The parameters for the renamer.
        """
        super().__init__(params, json)
        # Check if the renamer is present in the json file
        utils.checkElementExists(self._json, "rename")
        self._renamerElement = self._json["rename"]

    def __call__(self):
        super().__call__()
        # Rename the columns in the DataFrame with the values in the renamer dictionary
        DataManager._df.rename(columns=self._renamerElement, inplace=True)
