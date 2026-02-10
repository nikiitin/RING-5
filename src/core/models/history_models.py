"""
Operation history models.

Defines the OperationRecord TypedDict used to track data transformation
operations performed by managers (preprocessor, mixer, outlier remover,
seeds reducer).
"""

from typing import List, TypedDict


class OperationRecord(TypedDict):
    """
    Record of a single data transformation operation.

    Attributes:
        source_columns: The input column(s) used in the operation.
        dest_columns: The output column(s) produced or affected.
        operation: Human-readable name of the operation performed.
        timestamp: ISO-8601 timestamp of when the operation was confirmed.
    """

    source_columns: List[str]
    dest_columns: List[str]
    operation: str
    timestamp: str
