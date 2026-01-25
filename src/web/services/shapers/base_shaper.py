from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class Shaper(ABC):
    """
    Abstract base class for all data shapers.

    A Shaper defines a transformation on simulation data, such as filtering,
    aggregation, or normalization.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize the shaper with configuration parameters.

        Args:
            params: Dictionary of configuration parameters.

        Raises:
            ValueError: If parameters are invalid.
        """
        if not isinstance(params, dict):
            raise ValueError("Shaper parameters must be a dictionary.")

        self.params = params
        self._verify_params()

    @abstractmethod
    def _verify_params(self) -> bool:
        """
        Verify that the initialization parameters are valid.

        Returns:
            True if valid.

        Raises:
            ValueError: If mandatory parameters are missing or incorrect.
        """
        if self.params is None:
            raise ValueError("Shaper: parameters cannot be None.")
        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """
        Verify that the dataframe state is compatible with this shaper.

        Args:
            data_frame: Data to check.

        Returns:
            True if compatible.

        Raises:
            ValueError: If preconditions are not met.
        """
        if data_frame is None:
            raise ValueError("Shaper: Input dataframe cannot be None.")
        if data_frame.empty:
            raise ValueError("Shaper: Cannot operate on an empty dataframe.")
        return True

    def __call__(self, data_frame: Any) -> pd.DataFrame:
        """
        Execute the transformation on the data.

        Args:
            data_frame: The data to transform.

        Returns:
            The transformed dataframe.
        """
        self._verify_preconditions(data_frame)
        return data_frame
