"""Validation tests for the engine-independent small-multiples contract."""

from __future__ import annotations

import pytest

from src.core.models.visualization.small_multiples_spec import FacetPanel, SmallMultiplesSpec


def _spec(**changes: object) -> SmallMultiplesSpec:
    values: dict[str, object] = {
        "plot_id": 3,
        "facet_columns": ("architecture",),
        "panels": (
            FacetPanel(("x86",), "Architecture: x86"),
            FacetPanel(("arm",), "Architecture: Arm"),
        ),
        "rows": 1,
        "columns": 2,
    }
    values.update(changes)
    return SmallMultiplesSpec(**values)  # type: ignore[arg-type]


def test_small_multiples_spec_is_immutable_and_accepts_a_valid_grid() -> None:
    spec = _spec(shared_xaxes=False)

    assert spec.panels[1].values == ("arm",)
    assert spec.shared_xaxes is False
    with pytest.raises(AttributeError):
        spec.columns = 4  # type: ignore[misc]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"plot_id": True}, "plot_id"),
        ({"facet_columns": ()}, "at least one"),
        ({"facet_columns": ("arch", "arch")}, "unique"),
        ({"panels": (FacetPanel(("x86",), "x86"),)}, "at least two"),
        ({"rows": 0}, "at least 1"),
        ({"rows": 1, "columns": 1}, "too few"),
        ({"width": 100}, "at least 320"),
    ],
)
def test_small_multiples_spec_rejects_invalid_layouts(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _spec(**changes)


def test_facet_panel_rejects_missing_values_or_label() -> None:
    with pytest.raises(ValueError, match="at least one"):
        FacetPanel((), "Panel")
    with pytest.raises(ValueError, match="non-empty"):
        FacetPanel(("x86",), " ")
