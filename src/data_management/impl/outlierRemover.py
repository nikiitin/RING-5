import src.utils.utils as utils
from src.data_management.dataManager import DataManager
from src.data_management.manager_params import DataManagerParams


class OutlierRemover(DataManager):
    """
    Class to remove outliers from a DataFrame.
    Inherits from the DataManager class.
    """

    def _verifyParams(self):
        super()._verifyParams()
        # Skip validation if no outlier removal is configured
        if self._outlierStat is None:
            return
        # Outlier stat must be a string and that column must exist in the DataFrame
        if not isinstance(self._outlierStat, str):
            raise ValueError(
                "Outlier stat element is not correctly defined at json file. Must be a string"
            )
        if self._outlierStat not in DataManager._df.columns:
            raise ValueError(
                f"Outlier stat column {self._outlierStat} does not exist in the DataFrame"
            )

    def __init__(self, params: DataManagerParams, json: dict) -> None:
        """
        Constructor for the OutlierRemover class. Instance the class only
        if the outlierRemover is present in the json file.
        Args:
            params: The parameters for the outlier remover.
        """
        super().__init__(params, json)

        # Handle two JSON formats:
        # 1. Empty: {} - skip outlier removal
        # 2. Nested: {"outlierRemover": {"outlierStat": "column_name"}}
        # 3. Simple: {"outlierStat": "column_name"}

        if not self._json or len(self._json) == 0:
            # Empty dict - skip outlier removal
            self._outlierRemoverElement = None
            self._outlierStat = None
        elif "outlierRemover" in self._json:
            # Nested format
            self._outlierRemoverElement = self._json["outlierRemover"]
            utils.checkElementExists(self._outlierRemoverElement, "outlierStat")
            self._outlierStat = self._outlierRemoverElement["outlierStat"]
        elif "outlierStat" in self._json:
            # Simple format
            self._outlierStat = self._json["outlierStat"]
            self._outlierRemoverElement = self._json
        else:
            # No outlier removal config
            self._outlierRemoverElement = None
            self._outlierStat = None

    def __call__(self):
        """
        Remove outliers from the DataFrame. Consider outlier values that
        lie outside the 3rd quartile (Q3). Never biased, however this is not
        the best method to remove outliers...
        """
        super().__call__()
        # Check if the outlierRemover is set to True
        if self._outlierRemoverElement:
            print("Removing outliers...")
            # pd.set_option('display.max_colwidth', None)
            # pd.set_option('display.max_rows', None)
            # Remove outliers, that data that is outside the 3rd quartile (Q3)

            # Group by categorical columns
            grouped = DataManager._df.groupby(DataManager._categorical_columns)

            # Calculate Q3 for each group
            Q3 = grouped[self._outlierStat].transform(lambda x: x.quantile(0.75))

            # Filter rows where the specified column is <= Q3 for their group
            filtered_df = DataManager._df[DataManager._df[self._outlierStat] <= Q3]
            # Update the DataFrame with the filtered data
            DataManager._df = filtered_df
