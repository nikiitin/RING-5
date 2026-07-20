"""Validation tests for the engine-independent dashboard contract."""

import pytest

from src.core.models.visualization.dashboard_spec import DashboardSpec


def _spec(**overrides: object) -> DashboardSpec:
    values = {
        "plot_ids": (1, 2),
        "rows": 1,
        "columns": 2,
        "panel_titles": ("One", "Two"),
    }
    values.update(overrides)
    return DashboardSpec(**values)  # type: ignore[arg-type]


def test_dashboard_spec_rejects_ambiguous_or_impossible_layouts() -> None:
    with pytest.raises(ValueError, match="at least two"):
        _spec(plot_ids=(1,), panel_titles=("One",))
    with pytest.raises(ValueError, match="same plot"):
        _spec(plot_ids=(1, 1))
    with pytest.raises(ValueError, match="too few panels"):
        _spec(plot_ids=(1, 2, 3), panel_titles=("1", "2", "3"))
    with pytest.raises(ValueError, match="one title per plot"):
        _spec(panel_titles=("One",))
    with pytest.raises(ValueError, match="at least 320 x 240"):
        _spec(width=319)
    with pytest.raises(ValueError, match="must be integers"):
        _spec(columns=1.5)
    with pytest.raises(ValueError, match="plot IDs must be integers"):
        _spec(plot_ids=(1, "2"))
    with pytest.raises(ValueError, match="panel titles must be strings"):
        _spec(panel_titles=("One", 2))


def test_dashboard_spec_is_immutable() -> None:
    spec = _spec(title="Paper figures")

    with pytest.raises(AttributeError):
        spec.title = "Changed"  # type: ignore[misc]
