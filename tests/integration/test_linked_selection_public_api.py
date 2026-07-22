"""Public API coverage for linked dashboard selections."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def _plots(session: ring5.Session) -> list[object]:
    first = session.create_plot(
        "bar",
        data=pd.DataFrame({"workload": ["A", "B", "C"], "ipc": [1.0, 2.0, 3.0]}),
        config={"x": "workload", "y": "ipc"},
        name="IPC",
    )
    second = session.create_plot(
        "scatter",
        data=pd.DataFrame({"workload": ["A", "B", "C"], "power": [8.0, 6.0, 9.0]}),
        config={"x": "workload", "y": "power"},
        name="Power",
    )
    return [first, second]


def test_public_linked_selection_highlights_dashboard_copy() -> None:
    # [test->req~ring5.plots.linked-selections~1]
    with ring5.Session() as session:
        plots = _plots(session)
        dashboard = session.create_dashboard(plots)
        spec = session.create_linked_selection(dashboard, axis="x", mode="highlight")
        figure = session.render_dashboard(dashboard, engine="plotly")
        snapshot = figure.to_plotly_json()

        linked = ring5.apply_linked_selection(figure, spec, ["B"])

        assert isinstance(spec, ring5.LinkedSelectionSpec)
        assert spec.plot_ids == dashboard.plot_ids
        assert all(list(trace.selectedpoints) == [1] for trace in linked.data)
        assert figure.to_plotly_json() == snapshot


def test_public_linked_selection_filters_and_translates_invalid_inputs() -> None:
    with ring5.Session() as session:
        plots = _plots(session)
        spec = session.create_linked_selection([plots[0], 1], axis="x", mode="filter")
        figure = go.Figure(go.Bar(x=["A", "B", "C"], y=[1, 2, 3]))

        filtered = ring5.apply_linked_selection(figure, spec, ["A", "C"])
        assert list(filtered.data[0].x) == ["A", "C"]
        assert list(filtered.data[0].y) == [1, 3]

        with pytest.raises(ring5.DataValidationError, match="at least two"):
            session.create_linked_selection(plots[:1])
        with pytest.raises(ring5.DataValidationError, match="unknown plot IDs"):
            session.create_linked_selection([plots[0], 999])
        with pytest.raises(ring5.DataValidationError, match="axis must be"):
            session.create_linked_selection(plots, axis="z")  # type: ignore[arg-type]
        with pytest.raises(ring5.DataValidationError, match="mode must be"):
            session.create_linked_selection(plots, mode="replace")  # type: ignore[arg-type]
        with pytest.raises(ring5.RenderError, match="Plotly figure"):
            ring5.apply_linked_selection(object(), spec, [])  # type: ignore[arg-type]
        with pytest.raises(ring5.RenderError, match="Could not apply"):
            ring5.apply_linked_selection(figure, None, ["A"])  # type: ignore[arg-type]
