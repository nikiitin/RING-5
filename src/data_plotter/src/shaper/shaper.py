from abc import abstractmethod
import pandas as pd
from typing import Any


class Shaper:
    """
    Abstract class for shapers.
    """
    @property
    def _params(self) -> dict:
        return self._params_data
    @_params.setter
    def _params(self, value: Any) -> None:
        if isinstance(value, dict):
            self._params_data = value
        else:
            raise ValueError("params must be a dictionary")

    def __init__(self, params: dict) -> None:
        """
        Constructor for the shaper class.
        """
        self._params = params
        if not self._verifyParams():
            return

    @abstractmethod
    def _verifyParams(self) -> bool:
        """
        Verify that the Shaper json is valid, else raise an exception.
        Raises: (ValueError): if any key parameters are missing
        or wrong type.
        :returns: True if the parameters are valid, False otherwise.
        """
        if self._params is None:
            raise ValueError("The parameters are None! Stopping")
        return True
        

    @abstractmethod
    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        """
        Verify that the Shaper read values are valid and coherent with the data frame.
        Raises: (ValueError): if any preconditions are not met.
        :param data_frame: The DataFrame to be checked.
        :type data_frame: pd.DataFrame
        :returns: True if the preconditions are met, False otherwise.
        """
        if data_frame.empty:
            raise ValueError("The DataFrame is empty! Stopping")
        return True

    @abstractmethod
    def __call__(self, data_frame: Any) -> pd.DataFrame:
        """
        Main functionality of the Shaper class.
        Perform a shaping operation on the given DataFrame.
        :param data_frame: The DataFrame to be shaped.
        :type data_frame: pd.DataFrame
        :raises NotImplementedError: If the method is not implemented in a subclass.
        """
        # This method should be implemented in subclasses
        if not self._verifyPreconditions(data_frame):
            raise ValueError("Preconditions not met! Stopping")
        pass
        return data_frame