"""
Preview Repository
Manages temporary preview results for data operations.
"""

import logging

from pandas import DataFrame

logger = logging.getLogger(__name__)


class PreviewRepository:
    """
    Repository for managing temporary preview results.

    Adheres to SRP: Only manages preview state in memory.
    """

    # We use a class variable for storage because PreviewRepository methods were static.
    # To maintain compatibility while removing Streamlit dependency, we can use a class-level dict.
    # If we move to instance-based, we'd need to refactor call sites.
    # Given the new architecture (Singleton ApplicationAPI owning Repos),
    # instance-based is better. However, existing code might call
    # PreviewRepository.static_method(). Refactor Plan: Convert to instance
    # methods and have it managed by SessionRepository/StateManager.

    def __init__(self) -> None:
        self._previews: dict[str, DataFrame] = {}

    def set_preview(self, operation_name: str, data: DataFrame) -> None:
        """
        Store preview result for an operation.
        """
        if not operation_name:
            raise ValueError("Operation name cannot be empty")
        if data is None:
            raise ValueError("Preview data cannot be None")

        self._previews[operation_name] = data
        logger.debug(f"PREVIEW_REPO: Stored preview for '{operation_name}'")

    def get_preview(self, operation_name: str) -> DataFrame | None:
        """
        Retrieve preview result for an operation.
        """
        if not operation_name:
            return None
        preview = self._previews.get(operation_name)
        return preview.copy() if preview is not None else None

    def has_preview(self, operation_name: str) -> bool:
        """
        Check if preview exists for an operation.
        """
        return operation_name in self._previews

    def clear_preview(self, operation_name: str) -> None:
        """
        Clear preview result for an operation.
        """
        if operation_name in self._previews:
            del self._previews[operation_name]
            logger.debug(f"PREVIEW_REPO: Cleared preview for '{operation_name}'")

    def clear_all_previews(self) -> int:
        """
        Clear all preview results.
        """
        count = len(self._previews)
        self._previews.clear()
        if count > 0:
            logger.info("PREVIEW_REPO: Cleared %d preview(s)", count)
        return count

    def list_active_previews(self) -> list[str]:
        """
        List all active preview operations.
        """
        return list(self._previews.keys())
