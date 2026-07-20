"""In-memory repository for primary and processed datasets."""

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone

import pandas as pd

from src.core.models.dataset_workspace_models import DatasetInfo, DatasetLineage, DatasetRevision

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _StoredDatasetRevision:
    """Internal immutable metadata plus its defensive dataframe snapshot."""

    info: DatasetRevision
    data: pd.DataFrame


class DataRepository:
    """Store primary and processed dataframes."""

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._data: pd.DataFrame | None = None
        self._processed_data: pd.DataFrame | None = None
        self._datasets: dict[str, pd.DataFrame] = {}
        self._selected_dataset: str | None = None
        self._revisions: dict[str, _StoredDatasetRevision] = {}
        self._dataset_revision_ids: dict[str, list[str]] = {}
        self._current_revision_ids: dict[str, str] = {}
        self._redo_revision_ids: dict[str, list[str]] = {}
        self._revision_counter = 0

    def get_data(self) -> pd.DataFrame | None:
        """
        Retrieve the primary dataset.

        Returns:
            A copy of the primary DataFrame (defensive copy-on-read), or None.
        """
        return self._data.copy() if self._data is not None else None

    def set_data(
        self,
        data: pd.DataFrame | None,
        on_change: Callable[[], None] | None = None,
        *,
        operation: str = "Update dataset",
        source_datasets: tuple[str, ...] = (),
    ) -> None:
        """
        Store the primary dataset with optional change callback.

        Args:
            data: DataFrame to store (None to clear)
            on_change: Optional callback to execute after setting data.
            operation: Human-readable lineage operation for named data.
            source_datasets: Other named datasets used by the operation.
        """
        if data is None:
            self._data = None
            self._selected_dataset = None
        elif self._selected_dataset is not None:
            self._record_revision(
                self._selected_dataset,
                data,
                operation=operation,
                source_datasets=source_datasets,
            )
        else:
            self._data = data.copy(deep=True)

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
        self._revisions.clear()
        self._dataset_revision_ids.clear()
        self._current_revision_ids.clear()
        self._redo_revision_ids.clear()
        self._revision_counter = 0
        logger.info("DATA_REPO: All data cleared (primary + processed)")

    def add_dataset(
        self,
        name: str,
        data: pd.DataFrame,
        *,
        select: bool = True,
        replace: bool = False,
        operation: str = "Add dataset",
        source_datasets: tuple[str, ...] = (),
    ) -> DatasetInfo:
        """Store a defensive copy under a session-unique name.

        Args:
            name: Human-readable dataset name.
            data: Dataset to retain.
            select: Make the stored dataset the active compatibility view.
            replace: Permit replacing a dataset with the same name.
            operation: Human-readable operation that produced the dataset.
            source_datasets: Named source datasets used by the operation.

        Returns:
            Metadata for the stored dataset.

        Raises:
            ValueError: The name is invalid or already exists.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        resolved = self._validate_dataset_name(name)
        if resolved in self._datasets and not replace:
            raise ValueError(f"Dataset {resolved!r} already exists.")
        self._record_revision(
            resolved,
            data,
            operation=operation,
            source_datasets=source_datasets,
        )
        if select or self._selected_dataset is None:
            self._selected_dataset = resolved
            self._data = self._datasets[resolved]
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
        removed_revisions = self._dataset_revision_ids.pop(resolved, [])
        for revision_id in removed_revisions:
            self._revisions.pop(revision_id, None)
        self._current_revision_ids.pop(resolved, None)
        self._redo_revision_ids.pop(resolved, None)
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

    def get_dataset_lineage(self, name: str | None = None) -> DatasetLineage:
        """Return all retained revisions and recovery capabilities for a dataset."""
        # [impl->req~ring5.data.lineage-undo-redo~1]
        resolved = self._resolve_dataset_name(name)
        current_id = self._current_revision_ids[resolved]
        revisions = tuple(
            replace(
                self._revisions[revision_id].info,
                current=revision_id == current_id,
            )
            for revision_id in self._dataset_revision_ids[resolved]
        )
        return DatasetLineage(
            dataset_name=resolved,
            revisions=revisions,
            current_revision_id=current_id,
            can_undo=self._same_dataset_parent(current_id) is not None,
            can_redo=bool(self._redo_revision_ids[resolved]),
        )

    def get_dataset_revision(self, revision_id: str) -> pd.DataFrame:
        """Return a defensive copy of one immutable revision snapshot."""
        resolved = self._validate_revision_id(revision_id)
        try:
            revision = self._revisions[resolved]
        except KeyError as exc:
            raise KeyError(f"Dataset revision {resolved!r} does not exist.") from exc
        return revision.data.copy(deep=True)

    def undo_dataset(self, name: str | None = None) -> DatasetRevision:
        """Move a dataset to its preceding same-dataset revision."""
        resolved = self._resolve_dataset_name(name)
        current_id = self._current_revision_ids[resolved]
        parent_id = self._same_dataset_parent(current_id)
        if parent_id is None:
            raise ValueError(f"Dataset {resolved!r} has no earlier revision to restore.")
        self._redo_revision_ids[resolved].append(current_id)
        return self._activate_revision(resolved, parent_id)

    def redo_dataset(self, name: str | None = None) -> DatasetRevision:
        """Reapply the most recently undone revision for a dataset."""
        resolved = self._resolve_dataset_name(name)
        if not self._redo_revision_ids[resolved]:
            raise ValueError(f"Dataset {resolved!r} has no revision to redo.")
        return self._activate_revision(resolved, self._redo_revision_ids[resolved].pop())

    def restore_dataset_revision(self, revision_id: str) -> DatasetRevision:
        """Restore any retained intermediate revision without creating a new snapshot."""
        resolved_id = self._validate_revision_id(revision_id)
        try:
            stored = self._revisions[resolved_id]
        except KeyError as exc:
            raise KeyError(f"Dataset revision {resolved_id!r} does not exist.") from exc
        name = stored.info.dataset_name
        if name not in self._datasets or resolved_id not in self._dataset_revision_ids[name]:
            raise KeyError(f"Dataset {name!r} is no longer retained.")
        self._redo_revision_ids[name].clear()
        return self._activate_revision(name, resolved_id)

    def _dataset_info(self, name: str) -> DatasetInfo:
        data = self._datasets[name]
        return DatasetInfo(
            name=name,
            row_count=len(data),
            column_count=len(data.columns),
            selected=name == self._selected_dataset,
        )

    def _record_revision(
        self,
        name: str,
        data: pd.DataFrame,
        *,
        operation: str,
        source_datasets: tuple[str, ...],
    ) -> DatasetRevision:
        """Snapshot a named dataset and connect it to its reproducible ancestry."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Named workspace data must be a pandas DataFrame.")
        resolved_operation = self._validate_operation(operation)
        resolved_sources = tuple(self._validate_dataset_name(source) for source in source_datasets)
        missing = [source for source in resolved_sources if source not in self._datasets]
        if missing:
            raise KeyError(f"Source dataset {missing[0]!r} does not exist.")

        parents: list[str] = []
        current_id = self._current_revision_ids.get(name)
        if current_id is not None:
            parents.append(current_id)
        for source in resolved_sources:
            source_revision = self._current_revision_ids[source]
            if source_revision not in parents:
                parents.append(source_revision)

        snapshot = data.copy(deep=True)
        self._revision_counter += 1
        revision_id = f"rev-{self._revision_counter:06d}"
        revision_ids = self._dataset_revision_ids.setdefault(name, [])
        info = DatasetRevision(
            revision_id=revision_id,
            dataset_name=name,
            sequence=len(revision_ids) + 1,
            operation=resolved_operation,
            created_at=datetime.now(timezone.utc).isoformat(),
            row_count=len(snapshot),
            column_count=len(snapshot.columns),
            fingerprint=self._fingerprint(snapshot),
            source_datasets=resolved_sources,
            parent_revision_ids=tuple(parents),
        )
        self._revisions[revision_id] = _StoredDatasetRevision(info=info, data=snapshot)
        revision_ids.append(revision_id)
        self._current_revision_ids[name] = revision_id
        self._redo_revision_ids.setdefault(name, []).clear()
        self._datasets[name] = snapshot
        if self._selected_dataset == name:
            self._data = snapshot
            self._processed_data = None
        return replace(info, current=True)

    def _activate_revision(self, name: str, revision_id: str) -> DatasetRevision:
        stored = self._revisions[revision_id]
        restored = stored.data.copy(deep=True)
        self._current_revision_ids[name] = revision_id
        self._datasets[name] = restored
        if self._selected_dataset == name:
            self._data = restored
            self._processed_data = None
        return replace(stored.info, current=True)

    def _same_dataset_parent(self, revision_id: str) -> str | None:
        revision = self._revisions[revision_id].info
        for parent_id in revision.parent_revision_ids:
            parent = self._revisions.get(parent_id)
            if parent is not None and parent.info.dataset_name == revision.dataset_name:
                return parent_id
        return None

    def _resolve_dataset_name(self, name: str | None) -> str:
        resolved = self._selected_dataset if name is None else self._validate_dataset_name(name)
        if resolved is None:
            raise ValueError("No dataset is selected.")
        if resolved not in self._datasets:
            raise KeyError(f"Dataset {resolved!r} does not exist.")
        return resolved

    @staticmethod
    def _validate_operation(operation: str) -> str:
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("Dataset operation must be a non-empty string.")
        resolved = operation.strip()
        if len(resolved) > 200:
            raise ValueError("Dataset operation cannot exceed 200 characters.")
        if any(ord(character) < 32 for character in resolved):
            raise ValueError("Dataset operation cannot contain control characters.")
        return resolved

    @staticmethod
    def _validate_revision_id(revision_id: str) -> str:
        if not isinstance(revision_id, str) or not revision_id.strip():
            raise ValueError("Dataset revision ID must be a non-empty string.")
        return revision_id.strip()

    @staticmethod
    def _fingerprint(data: pd.DataFrame) -> str:
        digest = hashlib.sha256()
        digest.update(repr(tuple(data.columns)).encode("utf-8"))
        digest.update(repr(tuple(str(dtype) for dtype in data.dtypes)).encode("utf-8"))
        try:
            hashes = pd.util.hash_pandas_object(data, index=True, categorize=True)
            digest.update(hashes.to_numpy(copy=False).tobytes())
        except (TypeError, ValueError):
            digest.update(data.to_csv(index=True).encode("utf-8"))
        return f"sha256:{digest.hexdigest()}"

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
