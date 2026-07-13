"""In-memory repository for primary and processed datasets."""

import logging
from collections.abc import Callable

import pandas as pd

logger = logging.getLogger(__name__)


class DataRepository:
    """Store primary and processed dataframes."""

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._data: pd.DataFrame | None = None
        self._processed_data: pd.DataFrame | None = None

    def get_data(self) -> pd.DataFrame | None:
        """
        Retrieve the primary dataset.

        Returns:
            A copy of the primary DataFrame (defensive copy-on-read), or None.
        """
        return self._data.copy() if self._data is not None else None

    def set_data(
        self, data: pd.DataFrame | None, on_change: Callable[[], None] | None = None
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
            logger.info(
                "DATA_REPO: Data updated - %d rows × %d columns", len(data), len(data.columns)
            )
        else:
            logger.info("DATA_REPO: Data cleared")

    def get_processed_data(self) -> pd.DataFrame | None:
        """
        Retrieve the processed dataset (after shapers/transformations).

        Returns:
            A copy of the processed DataFrame (defensive copy-on-read), or None.
        """
        return self._processed_data.copy() if self._processed_data is not None else None

    def set_processed_data(self, data: pd.DataFrame | None) -> None:
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
