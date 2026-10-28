"""
Base Shaper - Abstract Data Transformation Interface.

Defines the abstraction for all data transformation operations (shapers).
Implements the Strategy pattern to support pluggable, composable transformations
like filtering, aggregation, normalization, sorting, and selection.

Core concept: Shapers transform DataFrames through a plugin architecture,
enabling users to create custom analysis pipelines.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any

import pandas as pd

from src.core.common.source_contributions import SourceTracker


class Shaper(ABC):
    """
    Abstract base class for all data shapers.

    A Shaper defines a transformation on simulation data, such as filtering,
    aggregation, or normalization. Follows the Strategy pattern for
    interchangeable data transformations.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Initialize the shaper with configuration parameters.

        Args:
            params: Dictionary of configuration parameters

        Raises:
            ValueError: If parameters are invalid or not a dictionary
        """
        if not isinstance(params, dict):
            raise ValueError("Shaper parameters must be a dictionary.")

        from src.core.services.shapers.factory import ShaperFactory

        ShaperFactory.validate_implementation(type(self), params)
        self.params: dict[str, Any] = deepcopy(params)
        self._source_tracker: SourceTracker | None = None

    def _call_with_source_rows(
        self, data_frame: pd.DataFrame, tracker: SourceTracker
    ) -> pd.DataFrame:
        """Scope an owned contribution sidecar to this one canonical operation."""
        self._source_tracker = tracker
        try:
            return self(data_frame)
        finally:
            self._source_tracker = None

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """
        Verify that the dataframe state is compatible with this shaper.

        Args:
            data_frame: Data to check

        Returns:
            True if compatible

        Raises:
            ValueError: If preconditions are not met (None or empty)
        """
        if data_frame is None:
            raise ValueError("Shaper: Input dataframe cannot be None.")
        if not isinstance(data_frame, pd.DataFrame):
            raise ValueError(f"Shaper: Expected pandas DataFrame, got {type(data_frame).__name__}.")
        if data_frame.empty:
            raise ValueError("Shaper: Cannot operate on an empty dataframe.")
        return True

    @abstractmethod
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Execute the transformation on the data.

        Args:
            data_frame: The data to transform

        Returns:
            The transformed dataframe

        Raises:
            ValueError: If preconditions are not met
        """
        self._verify_preconditions(data_frame)
        return data_frame
