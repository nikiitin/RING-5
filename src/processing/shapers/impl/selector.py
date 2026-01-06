from abc import abstractmethod
from typing import Any

import pandas as pd

import src.utils.utils as utils
from src.processing.shapers.uni_df_shaper import UniDfShaper


class Selector(UniDfShaper):
    """
    Selector is a Shaper that selects a subset of the data based on a given condition.
    It can be used to filter data before further processing or analysis.
    This class is abstract and should be subclassed to implement specific selection logic.
    Three main types of selectors are:
    - ItemSelector: Selects items based on a specified list of strings.
    - ColumnSelector: Selects items based on a specified column and condition.
    - ConditionSelector: Selects items based on a specified condition.
    """

    @property
    def _column(self) -> str:
        return self._column_data

    @_column.setter
    def _column(self, value: Any) -> None:
        utils.checkVarType(value, str)
        if value == "":
            raise ValueError("The 'column' parameter must not be empty.")
        self._column_data = value

    def __init__(self, params: dict):
        """
        Initializes the Selector with its parameters.
        :type params: dict
        """
        super().__init__(params)
        self._column = utils.getElementValue(self._params, "column")

    @abstractmethod
    def _verifyParams(self) -> bool:
        """
        Verify that the Selector is valid, else raise an exception.
        Raises: (ValueError): if any key parameters are missing or wrong type.
        :returns: True if the parameters are valid, False otherwise.
        """
        utils.checkElementExists(self._params, "column")
        return super()._verifyParams()

    @abstractmethod
    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        """
        Verify that the Selector is valid, else raise an exception.
        Raises: (ValueError): if any preconditions are not met.
        :param data_frame: The DataFrame to be checked.
        :type data_frame: pd.DataFrame
        :returns: True if the preconditions are met, False otherwise.
        """
        verified = super()._verifyPreconditions(data_frame)
        if self._column not in data_frame.columns:
            raise ValueError(f"The column '{self._column}' does not exist in the DataFrame.")
        return verified

    @abstractmethod
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Main functionality of the Selector class.
        Selects a subset of the data based on the specified condition.
        """
        # This method should be implemented in subclasses
        return super().__call__(data_frame)
