"""Immutable summaries for named datasets in a session workspace."""

from dataclasses import dataclass
from typing import Literal, TypeAlias

JoinCardinality: TypeAlias = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    """Metadata for one named in-memory dataset."""

    # [impl->req~ring5.data.multi-dataset-workspace~1]

    name: str
    row_count: int
    column_count: int
    selected: bool


@dataclass(frozen=True, slots=True)
class DatasetSnapshotInfo:
    """Inspectable metadata for one reusable, fingerprinted dataset snapshot."""

    # [impl->req~ring5.data.dataset-snapshots~1]

    name: str
    source_dataset: str
    created_at: str
    row_count: int
    column_count: int
    fingerprint: str
    size_bytes: int
    format_version: int


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


@dataclass(frozen=True, slots=True)
class JoinDiagnostics:
    """Pre-join key cardinality, duplication, and match diagnostics."""

    # [impl->req~ring5.data.validated-joins~1]

    key_columns: tuple[str, ...]
    expected_cardinality: JoinCardinality
    cardinality_valid: bool
    left_rows: int
    right_rows: int
    left_duplicate_key_rows: int
    right_duplicate_key_rows: int
    left_duplicate_key_groups: int
    right_duplicate_key_groups: int
    left_unmatched_rows: int
    right_unmatched_rows: int
    matched_key_count: int
