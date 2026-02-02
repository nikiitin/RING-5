"""
Data Repository
Single Responsibility: Manage primary and processed datasets.
"""

import logging
from typing import Callable, Optional

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)


class DataRepository:
    """
    Repository for managing application data (primary and processed datasets).

    Responsibilities:
    - Store and retrieve primary data
    - Store and retrieve processed data
    - Data existence checks
    - Data clearing operations

    Adheres to SRP: Only manages data state, nothing else.
    """

    # State keys
    DATA_KEY = "data"
    PROCESSED_DATA_KEY = "processed_data"

    @staticmethod
    def get_data() -> Optional[pd.DataFrame]:
        """
        Retrieve the primary dataset.

        Returns:
            Primary DataFrame or None if not set
        """
        result = st.session_state.get(DataRepository.DATA_KEY)
        return result if result is None or isinstance(result, pd.DataFrame) else None

    @staticmethod
    def set_data(
        data: Optional[pd.DataFrame], on_change: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Store the primary dataset with optional change callback.

        Args:
            data: DataFrame to store (None to clear)
            on_change: Optional callback to execute after setting data

        Note:
            This triggers frontend re-render via Streamlit's reactivity
        """
        st.session_state[DataRepository.DATA_KEY] = data

        if on_change:
            on_change()

        if data is not None:
            logger.info(f"DATA_REPO: Data updated - {len(data)} rows × {len(data.columns)} columns")
        else:
            logger.info("DATA_REPO: Data cleared")

    @staticmethod
    def get_processed_data() -> Optional[pd.DataFrame]:
        """
        Retrieve the processed dataset (after shapers/transformations).

        Returns:
            Processed DataFrame or None if not set
        """
        result = st.session_state.get(DataRepository.PROCESSED_DATA_KEY)
        return result if result is None or isinstance(result, pd.DataFrame) else None

    @staticmethod
    def set_processed_data(data: Optional[pd.DataFrame]) -> None:
        """
        Store the processed dataset.

        Args:
            data: Processed DataFrame to store
        """
        st.session_state[DataRepository.PROCESSED_DATA_KEY] = data

    @staticmethod
    def has_data() -> bool:
        """
        Check if primary data exists.

        Returns:
            True if primary data is present and non-empty
        """
        data = DataRepository.get_data()
        return data is not None and not data.empty

    @staticmethod
    def clear_data() -> None:
        """
        Clear both primary and processed data.

        Note:
            Also clears processed data to maintain consistency
        """
        st.session_state[DataRepository.DATA_KEY] = None
        st.session_state[DataRepository.PROCESSED_DATA_KEY] = None
        logger.info("DATA_REPO: All data cleared (primary + processed)")
