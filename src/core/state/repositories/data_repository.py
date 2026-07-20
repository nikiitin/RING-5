"""In-memory repository for primary and processed datasets."""

import logging
from collections.abc import Callable

import pandas as pd

from src.core.models.dataset_workspace_models import DatasetInfo

logger = logging.getLogger(__name__)


class DataRepository:
    """Store primary and processed dataframes."""

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._data: pd.DataFrame | None = None
        self._processed_data: pd.DataFrame | None = None
        self._datasets: dict[str, pd.DataFrame] = {}
        self._selected_dataset: str | None = None

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
        if data is None:
            self._selected_dataset = None
        elif self._selected_dataset is not None:
            self._datasets[self._selected_dataset] = data

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
        self._datasets.clear()
        self._selected_dataset = None
        logger.info("DATA_REPO: All data cleared (primary + processed)")

    def add_dataset(
        self,
        name: str,
        data: pd.DataFrame,
        *,
        select: bool = True,
        replace: bool = False,
    ) -> DatasetInfo:
        """Store a defensive copy under a session-unique name.

        Args:
            name: Human-readable dataset name.
            data: Dataset to retain.
            select: Make the stored dataset the active compatibility view.
            replace: Permit replacing a dataset with the same name.

        Returns:
            Metadata for the stored dataset.

        Raises:
            ValueError: The name is invalid or already exists.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        resolved = self._validate_dataset_name(name)
        if resolved in self._datasets and not replace:
            raise ValueError(f"Dataset {resolved!r} already exists.")
        stored = data.copy(deep=True)
        self._datasets[resolved] = stored
        if select or self._selected_dataset is None:
            self._selected_dataset = resolved
            self._data = stored
            self._processed_data = None
        return self._dataset_info(resolved)

    def list_datasets(self) -> tuple[DatasetInfo, ...]:
        """Return dataset metadata in insertion order."""
        return tuple(self._dataset_info(name) for name in self._datasets)

    def get_dataset(self, name: str | None = None) -> pd.DataFrame:
        """Return a defensive copy of a named or selected dataset.

        Args:
            name: Dataset name, or ``None`` for the selected dataset.

        Returns:
            A new DataFrame.

        Raises:
            ValueError: No dataset is selected.
            KeyError: The requested dataset does not exist.
        """
        resolved = self._selected_dataset if name is None else self._validate_dataset_name(name)
        if resolved is None:
            raise ValueError("No dataset is selected.")
        if resolved not in self._datasets:
            raise KeyError(f"Dataset {resolved!r} does not exist.")
        return self._datasets[resolved].copy(deep=True)

    def select_dataset(self, name: str) -> pd.DataFrame:
        """Select a named dataset and return a defensive copy."""
        resolved = self._validate_dataset_name(name)
        if resolved not in self._datasets:
            raise KeyError(f"Dataset {resolved!r} does not exist.")
        self._selected_dataset = resolved
        self._data = self._datasets[resolved]
        self._processed_data = None
        return self._data.copy(deep=True)

    def remove_dataset(self, name: str) -> None:
        """Remove one dataset while preserving every unrelated dataset."""
        resolved = self._validate_dataset_name(name)
        if resolved not in self._datasets:
            raise KeyError(f"Dataset {resolved!r} does not exist.")
        del self._datasets[resolved]
        if self._selected_dataset != resolved:
            return
        self._selected_dataset = next(iter(self._datasets), None)
        self._data = (
            self._datasets[self._selected_dataset] if self._selected_dataset is not None else None
        )
        self._processed_data = None

    def selected_dataset_name(self) -> str | None:
        """Return the active dataset name, if the active view is named."""
        return self._selected_dataset

    def _dataset_info(self, name: str) -> DatasetInfo:
        data = self._datasets[name]
        return DatasetInfo(
            name=name,
            row_count=len(data),
            column_count=len(data.columns),
            selected=name == self._selected_dataset,
        )

    @staticmethod
    def _validate_dataset_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Dataset name must be a non-empty string.")
        resolved = name.strip()
        if len(resolved) > 100:
            raise ValueError("Dataset name cannot exceed 100 characters.")
        if any(ord(character) < 32 for character in resolved):
            raise ValueError("Dataset name cannot contain control characters.")
        return resolved
