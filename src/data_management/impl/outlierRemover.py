from argumentParser import AnalyzerInfo
from src.data_management.dataManager import DataManager
import src.utils.utils as utils
import pandas as pd

class OutlierRemover(DataManager):
    """
    Class to remove outliers from a DataFrame.
    Inherits from the DataManager class.
    """
    def _verifyParams(self):
        super()._verifyParams()
        # Outlier stat must be an string and that column must exist in the DataFrame
        if not isinstance(self._outlierStat, str):
            raise ValueError("Outlier stat element is not correctly defined at json file. Must be a string")
        if self._outlierStat not in self._df.columns:
            raise ValueError(f"Outlier stat column {self._outlierStat} does not exist in the DataFrame")

    def __init__(self, params: AnalyzerInfo) -> None:
        """
        Constructor for the OutlierRemover class. Instance the class only
        if the outlierRemover is present in the json file.
        Args:
            params: The parameters for the outlier remover.
        """
        super().__init__(params)
        # Check if the outlierRemover is present in the json file
        utils.checkElementExists(self._json, "outlierRemover")
        self._outlierRemoverElement = self._json["outlierRemover"]
        # Outlier remover should contain a statistic used as reference for the
        # outlier removal. That should be one of the statistic columns.
        utils.checkElementExists(self._outlierRemoverElement, "outlierStat")
        self._outlierStat = self._outlierRemoverElement["outlierStat"]

    def __call__(self):
        """
        Remove outliers from the DataFrame. Consider outlier values that
        lie outside the 3rd quartile (Q3). Never biased, however this is not
        the best method to remove outliers...
        """
        super().__call__()
        # Check if the outlierRemover is set to True
        if self._outlierRemoverElement:
            # Identify numeric statistic columns (all columns not in categorical_columns).
            # Note that categorical_columns already includes 'seed_number'.
            statistic_columns = [col for col in self._df.columns if col not in self._categorical_columns]
            # Remove outliers, that data that is outside the 3rd quartile (Q3)
            for column in statistic_columns:
                # Calculate Q3 (75th percentile)
                Q3 = self._df[column].quantile(0.75)
                # Remove outliers
                self._df = self._df[self._df[column] <= Q3]
