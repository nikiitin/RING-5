"""Validation tests for the engine-independent linked-selection contract."""

import pytest

from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec


def test_linked_selection_spec_validates_panel_axis_and_mode() -> None:
    with pytest.raises(ValueError, match="at least two"):
        LinkedSelectionSpec((1,))
    with pytest.raises(ValueError, match="same plot"):
        LinkedSelectionSpec((1, 1))
    with pytest.raises(ValueError, match="must be integers"):
        LinkedSelectionSpec((1, True))
    with pytest.raises(ValueError, match="axis must be"):
        LinkedSelectionSpec((1, 2), axis="z")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="mode must be"):
        LinkedSelectionSpec((1, 2), mode="replace")  # type: ignore[arg-type]


def test_linked_selection_spec_is_immutable() -> None:
    spec = LinkedSelectionSpec((1, 2), axis="y", mode="filter")

    with pytest.raises(AttributeError):
        spec.axis = "x"  # type: ignore[misc]
