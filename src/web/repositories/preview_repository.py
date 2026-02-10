"""
Preview Repository
Manages temporary preview results for data operations before user commits them.

This repository implements the preview-commit pattern commonly used in data managers:
1. User triggers operation (e.g., "Preview Merge")
2. Result stored in temporary preview state
3. User reviews result
4. User commits (applies to main data) or discards

ARCHITECTURE NOTE:
- Abstracts Streamlit session_state access behind clean API
- Provides consistent naming convention for preview keys
- Enables testing of preview workflows
- Separates temporary state from persistent state

Design Pattern:
- Repository Pattern: Encapsulates preview state access
- Naming Convention: _preview_{operation_name} for all keys

Thread Safety:
- Relies on Streamlit's single-thread execution model
- Not thread-safe for concurrent access

Usage Example:
>>> PreviewRepository.set_preview("outlier_removal", filtered_df)
>>> if PreviewRepository.has_preview("outlier_removal"):
...     result = PreviewRepository.get_preview("outlier_removal")
...     # Display preview to user
...     PreviewRepository.clear_preview("outlier_removal")

Version: 1.0.0
Last Modified: 2026-01-27 (Phase 2 Refactoring)
"""

import logging
from typing import Optional

import streamlit as st
from pandas import DataFrame

logger = logging.getLogger(__name__)


class PreviewRepository:
    """
    Repository for managing temporary preview results.

    Provides clean abstraction over Streamlit session state for preview data,
    following repository pattern to separate state management from business logic.
    """

    # Prefix for all preview keys to avoid collision with other state
    PREVIEW_KEY_PREFIX: str = "_preview_"

    @staticmethod
    def _make_key(operation_name: str) -> str:
        """
        Generate consistent session state key for operation.

        Args:
            operation_name: Name of the operation (e.g., "outlier_removal", "mixer")

        Returns:
            Prefixed key for session state
        """
        return f"{PreviewRepository.PREVIEW_KEY_PREFIX}{operation_name}"

    @staticmethod
    def set_preview(operation_name: str, data: DataFrame) -> None:
        """
        Store preview result for an operation.

        Args:
            operation_name: Unique identifier for the operation
            data: DataFrame containing preview result

        Raises:
            ValueError: If operation_name is empty or data is None
        """
        if not operation_name:
            raise ValueError("Operation name cannot be empty")

        if data is None:
            raise ValueError("Preview data cannot be None")

        key = PreviewRepository._make_key(operation_name)
        st.session_state[key] = data

        logger.debug(
            f"PREVIEW_REPO: Stored preview for '{operation_name}' "
            f"({len(data)} rows, {len(data.columns)} cols)"
        )

    @staticmethod
    def get_preview(operation_name: str) -> Optional[DataFrame]:
        """
        Retrieve preview result for an operation.

        Args:
            operation_name: Unique identifier for the operation

        Returns:
            DataFrame if preview exists, None otherwise
        """
        if not operation_name:
            logger.warning("PREVIEW_REPO: get_preview called with empty operation_name")
            return None

        key = PreviewRepository._make_key(operation_name)
        result: Optional[DataFrame] = st.session_state.get(key)

        if result is not None:
            logger.debug(f"PREVIEW_REPO: Retrieved preview for '{operation_name}'")
        else:
            logger.debug(f"PREVIEW_REPO: No preview found for '{operation_name}'")

        return result

    @staticmethod
    def has_preview(operation_name: str) -> bool:
        """
        Check if preview exists for an operation.

        Args:
            operation_name: Unique identifier for the operation

        Returns:
            True if preview exists, False otherwise
        """
        if not operation_name:
            return False

        key = PreviewRepository._make_key(operation_name)
        exists: bool = key in st.session_state
        return exists

    @staticmethod
    def clear_preview(operation_name: str) -> None:
        """
        Clear preview result for an operation.

        Args:
            operation_name: Unique identifier for the operation

        Note:
            Safe to call even if preview doesn't exist (idempotent)
        """
        if not operation_name:
            logger.warning("PREVIEW_REPO: clear_preview called with empty operation_name")
            return

        key = PreviewRepository._make_key(operation_name)

        if key in st.session_state:
            del st.session_state[key]
            logger.debug(f"PREVIEW_REPO: Cleared preview for '{operation_name}'")
        else:
            logger.debug(f"PREVIEW_REPO: No preview to clear for '{operation_name}'")

    @staticmethod
    def clear_all_previews() -> int:
        """
        Clear all preview results (cleanup operation).

        Returns:
            Number of previews cleared

        Use Case:
            - Session cleanup
            - Reset application state
            - Testing teardown
        """
        preview_keys = [
            key
            for key in st.session_state.keys()
            if isinstance(key, str) and key.startswith(PreviewRepository.PREVIEW_KEY_PREFIX)
        ]

        for key in preview_keys:
            del st.session_state[key]

        count = len(preview_keys)
        if count > 0:
            logger.info(f"PREVIEW_REPO: Cleared {count} preview(s)")

        return count

    @staticmethod
    def list_active_previews() -> list[str]:
        """
        List all active preview operations.

        Returns:
            List of operation names with active previews

        Use Case:
            - Debugging
            - UI display of pending operations
            - Testing verification
        """
        prefix_len = len(PreviewRepository.PREVIEW_KEY_PREFIX)

        operations: list[str] = []
        for key in st.session_state.keys():
            if isinstance(key, str) and key.startswith(PreviewRepository.PREVIEW_KEY_PREFIX):
                operations.append(key[prefix_len:])

        return operations
