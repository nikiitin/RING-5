"""Pure linked-selection transformation tests."""

from datetime import date

import plotly.graph_objects as go
import pytest

from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec
from src.web.rendering.linked_selection import (
    apply_linked_selection,
    selection_values_from_event,
)


def test_highlight_links_matching_values_without_mutating_figure() -> None:
    # [test->req~ring5.plots.linked-selections~1]
    original = go.Figure(
        data=[
            go.Bar(x=["A", "B", "C"], y=[1, 2, 3], name="first"),
            go.Scatter(x=["C", "A", "B"], y=[4, 5, 6], mode="markers", name="second"),
        ]
    )
    snapshot = original.to_plotly_json()
    spec = LinkedSelectionSpec((1, 2), axis="x", mode="highlight")

    selected = apply_linked_selection(original, spec, ["B"])

    assert list(selected.data[0].selectedpoints) == [1]
    assert list(selected.data[1].selectedpoints) == [2]
    assert selected.data[0].unselected.marker.opacity == pytest.approx(0.18)
    assert selected.layout.selectionrevision.startswith("x:highlight:")
    assert original.to_plotly_json() == snapshot

    another = apply_linked_selection(original, spec, ["A"])
    assert another.layout.selectionrevision != selected.layout.selectionrevision


def test_filter_slices_aligned_point_metadata_and_keeps_source_data() -> None:
    original = go.Figure(
        go.Scatter(
            x=["A", "B", "C"],
            y=[10, 20, 30],
            text=["a", "b", "c"],
            customdata=[[1], [2], [3]],
            ids=["one", "two", "three"],
            marker={"color": ["red", "green", "blue"], "size": [4, 5, 6]},
            error_y={"array": [0.1, 0.2, 0.3], "arrayminus": [0.4, 0.5, 0.6]},
        )
    )
    spec = LinkedSelectionSpec((1, 2), axis="x", mode="filter")

    filtered = apply_linked_selection(original, spec, ["C", "A"])
    trace = filtered.data[0]

    assert list(trace.x) == ["A", "C"]
    assert list(trace.y) == [10, 30]
    assert list(trace.text) == ["a", "c"]
    assert list(trace.customdata) == [[1], [3]]
    assert list(trace.ids) == ["one", "three"]
    assert list(trace.marker.color) == ["red", "blue"]
    assert list(trace.marker.size) == [4, 6]
    assert list(trace.error_y.array) == [0.1, 0.3]
    assert list(trace.error_y.arrayminus) == [0.4, 0.6]
    assert list(original.data[0].x) == ["A", "B", "C"]


@pytest.mark.parametrize(
    ("axis", "values", "expected_x", "expected_y", "expected_z"),
    [
        ("x", ["B"], ["B"], ["r1", "r2"], [[2], [5]]),
        ("y", ["r2"], ["A", "B", "C"], ["r2"], [[4, 5, 6]]),
    ],
)
def test_heatmap_cross_filter_slices_rows_or_columns(
    axis: str,
    values: list[str],
    expected_x: list[str],
    expected_y: list[str],
    expected_z: list[list[int]],
) -> None:
    figure = go.Figure(
        go.Heatmap(
            x=["A", "B", "C"],
            y=["r1", "r2"],
            z=[[1, 2, 3], [4, 5, 6]],
            text=[["a", "b", "c"], ["d", "e", "f"]],
        )
    )
    spec = LinkedSelectionSpec((1, 2), axis=axis, mode="highlight")  # type: ignore[arg-type]

    filtered = apply_linked_selection(figure, spec, values)

    assert list(filtered.data[0].x) == expected_x
    assert list(filtered.data[0].y) == expected_y
    assert list(filtered.data[0].z) == expected_z


def test_empty_selection_restores_copy_and_event_values_are_ordered_unique() -> None:
    figure = go.Figure(go.Bar(x=[1, 2], y=[3, 4]))
    spec = LinkedSelectionSpec((1, 2))

    restored = apply_linked_selection(figure, spec, [])
    event = {
        "kind": "selection",
        "points": [
            {"x": 2, "y": date(2026, 1, 1)},
            {"x": 1, "y": date(2026, 1, 2)},
            {"x": 2, "y": date(2026, 1, 1)},
            "not-a-point",
        ],
    }

    assert restored is not figure
    assert restored.to_plotly_json() == figure.to_plotly_json()
    assert selection_values_from_event(event, "x") == (2, 1)
    assert selection_values_from_event(event, "y") == (
        date(2026, 1, 1),
        date(2026, 1, 2),
    )
    assert selection_values_from_event({"points": "invalid"}, "x") == ()
    with pytest.raises(ValueError, match="axis must be"):
        selection_values_from_event(event, "z")


def test_linked_selection_rejects_non_plotly_figures() -> None:
    with pytest.raises(TypeError, match="Plotly figure"):
        apply_linked_selection(object(), LinkedSelectionSpec((1, 2)), [])  # type: ignore[arg-type]
