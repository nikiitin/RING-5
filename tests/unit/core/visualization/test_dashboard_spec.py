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


def test_publication_fields_align_panels_and_resolve_legacy_spacing() -> None:
    # [test->req~ring5.figure.panel-composition~1]
    spec = _spec(
        panel_labels=("(a)", "(b)"),
        panel_captions=("Baseline", "Optimized"),
        horizontal_spacing=0.05,
        vertical_spacing=0.1,
    )

    assert spec.resolved_panel_labels == ("(a)", "(b)")
    assert spec.resolved_panel_captions == ("Baseline", "Optimized")
    assert spec.resolved_horizontal_spacing == 0.05
    assert spec.resolved_vertical_spacing == 0.1
    assert _spec().resolved_panel_labels == ("", "")
    assert _spec().resolved_panel_captions == ("", "")
    assert _spec().resolved_horizontal_spacing == pytest.approx(0.09)
    assert _spec().resolved_vertical_spacing == pytest.approx(0.16)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"panel_labels": ("(a)",)}, "panel_labels"),
        ({"panel_captions": ("Only one",)}, "panel_captions"),
        ({"panel_labels": ("(a)", 2)}, "panel labels must be strings"),
        ({"horizontal_spacing": -0.01}, "between 0 and 0.2"),
        ({"vertical_spacing": float("nan")}, "between 0 and 0.2"),
        ({"horizontal_spacing": True}, "number or None"),
        (
            {"columns": 6, "horizontal_spacing": 0.2},
            "leaves no room for panel content",
        ),
    ],
)
def test_publication_fields_reject_ambiguous_values(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _spec(**overrides)
