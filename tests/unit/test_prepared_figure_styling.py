"""Editable configuration styles native figures through real neutral preparation."""

from typing import Any, cast

import pandas as pd
import plotly.graph_objects as go

from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.rendering.figure_preparation import PreparedFigure, prepare_figure
from src.web.rendering.plotly_figure_builder import build_plotly_figure


def _prepare(plot_type: str, config: dict[str, Any]) -> PreparedFigure:
    frame = pd.DataFrame(
        {
            "x": ["a", "b", "a", "b"],
            "group": ["base", "base", "opt", "opt"],
            "y": [1.0, 2.0, 3.0, 4.0],
        }
    )
    plot = PlotFactory.create_plot(plot_type, plot_id=1, name="Measured")
    return prepare_figure(
        frame, {"x": "x", "y": "y", "group": "group", **config}, plot_type, plot.create_traces
    )


class TestPreparedFigureStyling:
    """The resolved specification and native figure agree on visible settings."""

    def test_full_pipeline(self) -> None:
        # [test->req~ring5.figure.series-styling~1]
        prepared = _prepare(
            "grouped_bar",
            {
                "width": 1000,
                "height": 600,
                "title": "Test",
                "xlabel": "Category",
                "ylabel": "Value",
                "plot_bgcolor": "#FFFFFF",
                "bargap": 0.2,
                "bargroupgap": 0.1,
            },
        )
        result = build_plotly_figure(prepared).figure
        assert result.layout.width == 1000
        assert result.layout.title.text == "Test"
        assert result.layout.bargap == 0.2 and result.layout.bargroupgap == 0.1
        assert [list(trace.y) for trace in prepared.trace_result.traces] == [[1.0, 2.0], [3.0, 4.0]]

    def test_with_show_values(self) -> None:
        prepared = _prepare(
            "bar", {"show_values": True, "text_format": ".1f", "text_position": "outside"}
        )
        result = build_plotly_figure(prepared).figure
        assert cast(go.Bar, result.data[0]).textposition == "outside"
        assert prepared.spec.data_labels is not None
        assert prepared.spec.data_labels.format_string == ".1f"

    def test_with_shapes(self) -> None:
        shapes = [{"type": "line", "x0": 0, "x1": 1, "y0": 0.5, "y1": 0.5}]
        prepared = _prepare("bar", {"shapes": shapes})
        result = build_plotly_figure(prepared).figure
        assert [shape.to_plotly_json() for shape in result.layout.shapes] == shapes
        assert prepared.config["shapes"] == shapes
        assert list(cast(go.Bar, result.data[0]).y) == [1.0, 3.0, 2.0, 4.0]
