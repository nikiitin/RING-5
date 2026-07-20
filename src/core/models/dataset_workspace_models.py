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
