"""
Data Repository
Single Responsibility: Manage primary and processed datasets.
"""

import logging
from typing import Callable, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataRepository:
    """
    Repository for managing application data (primary and processed datasets).

    Responsibilities:
    - Store and retrieve primary data
    - Store and retrieve processed data
    - Data existence checks
    - Data clearing operations

    Adheres to SRP: Only manages data state in memory.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._data: Optional[pd.DataFrame] = None
        self._processed_data: Optional[pd.DataFrame] = None

    def get_data(self) -> Optional[pd.DataFrame]:
        """
        Retrieve the primary dataset.

        Returns:
            Primary DataFrame or None if not set
        """
        return self._data

    def set_data(
        self, data: Optional[pd.DataFrame], on_change: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Store the primary dataset with optional change callback.

        Args:
            data: DataFrame to store (None to clear)
            on_change: Optional callback to execute after setting data
        """
        self._data = data

        if on_change:
            on_change()

        if data is not None:
            logger.info(f"DATA_REPO: Data updated - {len(data)} rows × {len(data.columns)} columns")
        else:
            logger.info("DATA_REPO: Data cleared")

    def get_processed_data(self) -> Optional[pd.DataFrame]:
        """
        Retrieve the processed dataset (after shapers/transformations).

        Returns:
            Processed DataFrame or None if not set
        """
        return self._processed_data

    def set_processed_data(self, data: Optional[pd.DataFrame]) -> None:
        """
        Store the processed dataset.

        Args:
            data: Processed DataFrame to store
        """
        self._processed_data = data

    def has_data(self) -> bool:
        """
        Check if primary data exists.

        Returns:
            True if primary data is present and non-empty
        """
        return self._data is not None and not self._data.empty

    def clear_data(self) -> None:
        """
        Clear both primary and processed data.
        """
        self._data = None
        self._processed_data = None
        logger.info("DATA_REPO: All data cleared (primary + processed)")
