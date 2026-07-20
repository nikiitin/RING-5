"""Immutable summaries for named datasets in a session workspace."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    """Metadata for one named in-memory dataset."""

    # [impl->req~ring5.data.multi-dataset-workspace~1]

    name: str
    row_count: int
    column_count: int
    selected: bool


@dataclass(frozen=True, slots=True)
class DatasetRevision:
    """Inspectable metadata for one immutable dataset state."""

    revision_id: str
    dataset_name: str
    sequence: int
    operation: str
    created_at: str
    row_count: int
    column_count: int
    fingerprint: str
    source_datasets: tuple[str, ...]
    parent_revision_ids: tuple[str, ...]
    current: bool = False


@dataclass(frozen=True, slots=True)
class DatasetLineage:
    """Ordered revision history and recovery capabilities for a dataset."""

    # [impl->req~ring5.data.lineage-undo-redo~1]

    dataset_name: str
    revisions: tuple[DatasetRevision, ...]
    current_revision_id: str
    can_undo: bool
    can_redo: bool
