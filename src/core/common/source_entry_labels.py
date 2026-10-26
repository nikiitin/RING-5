"""Literal source-label projection for an explicitly declared decoder contract."""

import re


def canonical_source_entry(source_kind: str, entry: str) -> str:
    """Project a Histogram singleton after its source contract is declared.

    Raw discovery retains printed labels. Histogram entry consumers use inclusive
    range labels; a Vector source keeps its literal names even when they are numeric.

    Args:
        source_kind: Exact declared contract, or an empty incomplete draft choice.
        entry: Actual observed label or an already canonical requested label.

    Returns:
        Its canonical contract label, without changing other literal names.

    Raises:
        TypeError: A kind or label is not an exact string.
    """
    if type(source_kind) is not str or type(entry) is not str:
        raise TypeError("Source contracts and entry labels must be exact strings.")
    if source_kind == "histogram" and re.fullmatch(r"-?\d+", entry):
        return f"{entry}-{entry}"
    return entry
