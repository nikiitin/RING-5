"""Engine-independent contract for linking selections across plot panels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SelectionAxis = Literal["x", "y"]
SelectionMode = Literal["highlight", "filter"]


@dataclass(frozen=True)
class LinkedSelectionSpec:
    # [impl->req~ring5.plots.linked-selections~1]
    """Describe how values selected in one panel affect linked panels."""

    plot_ids: tuple[int, ...]
    axis: SelectionAxis = "x"
    mode: SelectionMode = "highlight"

    def __post_init__(self) -> None:
        """Reject selections that cannot identify a linked panel set."""
        if len(self.plot_ids) < 2:
            raise ValueError("A linked selection needs at least two plots.")
        if any(
            isinstance(plot_id, bool) or not isinstance(plot_id, int) for plot_id in self.plot_ids
        ):
            raise ValueError("Linked-selection plot IDs must be integers.")
        if len(set(self.plot_ids)) != len(self.plot_ids):
            raise ValueError("A linked selection cannot contain the same plot more than once.")
        if self.axis not in ("x", "y"):
            raise ValueError("Linked-selection axis must be 'x' or 'y'.")
        if self.mode not in ("highlight", "filter"):
            raise ValueError("Linked-selection mode must be 'highlight' or 'filter'.")


__all__ = ["LinkedSelectionSpec", "SelectionAxis", "SelectionMode"]
