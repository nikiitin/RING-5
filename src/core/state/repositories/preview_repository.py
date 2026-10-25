"""In-memory data-operation previews."""

import logging
from copy import deepcopy

from src.core.common.dataframe_copy import copy_dataframe
from src.core.models.preview_models import PreviewContext

from pandas import DataFrame

logger = logging.getLogger(__name__)


class PreviewRepository:
    """Store independent preview frames by operation name."""

    def __init__(self) -> None:
        self._previews: dict[str, DataFrame] = {}
        self._contexts: dict[str, PreviewContext] = {}

    def set_preview(
        self, operation_name: str, data: DataFrame, *, context: PreviewContext | None = None
    ) -> None:
        """
        Store preview result for an operation.
        """
        # [impl->req~ring5.data.preview-confirm~1]
        if not operation_name:
            raise ValueError("Operation name cannot be empty")
        if data is None:
            raise ValueError("Preview data cannot be None")

        self._previews[operation_name] = copy_dataframe(data)
        if context is None:
            self._contexts.pop(operation_name, None)
        else:
            self._contexts[operation_name] = deepcopy(context)
        logger.debug(f"PREVIEW_REPO: Stored preview for '{operation_name}'")

    def get_preview(self, operation_name: str) -> DataFrame | None:
        """
        Retrieve preview result for an operation.
        """
        if not operation_name:
            return None
        preview = self._previews.get(operation_name)
        return copy_dataframe(preview) if preview is not None else None

    def get_preview_context(self, operation_name: str) -> PreviewContext | None:
        """Return a defensive copy of a guarded preview's source and options."""
        return deepcopy(self._contexts.get(operation_name))

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
            self._contexts.pop(operation_name, None)
            logger.debug(f"PREVIEW_REPO: Cleared preview for '{operation_name}'")

    def clear_all_previews(self) -> int:
        """
        Clear all preview results.
        """
        count = len(self._previews)
        self._previews.clear()
        self._contexts.clear()
        if count > 0:
            logger.info("PREVIEW_REPO: Cleared %d preview(s)", count)
        return count
