"""The current JSON payload of an exact, non-executable scientific table."""

from typing import Any, Literal, TypedDict


class TypedTablePayload(TypedDict):
    """A table's typed values, axes, dtypes and retained attributes."""

    format: Literal["ring5.typed-table"]
    format_version: Literal[1]
    index: dict[str, Any]
    columns: dict[str, Any]
    dtypes: list[dict[str, Any]]
    values: list[list[Any]]
    attrs: Any
