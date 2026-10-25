"""Categorical totals use rendered raw coordinates rather than display labels."""

from typing import Literal

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import pytest

from ring5 import Session
from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer


@pytest.mark.parametrize("order", [["B", "A", "C"], ["B"]])
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_stack_total_values_and_coordinates_survive_reorder_and_duplicate_display_names(
    engine: Literal["plotly", "matplotlib"],
    order: list[str],
) -> None:
    # [test->req~ring5.figure.stack-totals~1]
    data = pd.DataFrame({"category": ["A", "C", "B"], "a": [1.0, 3.0, 2.0], "b": [3.0, 5.0, 4.0]})
    original = data.copy(deep=True)
    with Session() as session:
        plot = session.create_plot(
            "stacked_bar",
            data=data,
            config={
                "x": "category",
                "y_columns": ["a", "b"],
                "show_totals": True,
                "xaxis_order": order,
                "xaxis_labels": {"A": "same", "B": "same", "C": "same"},
                "total_font_size": 17,
            },
        )
        figure = session.render(plot, engine=engine)
    if isinstance(figure, go.Figure):
        assert list(figure.layout.xaxis.categoryarray) == order
        assert {ann.text: ann.x for ann in figure.layout.annotations} == {
            "4.00": "A",
            "6.00": "B",
            "8.00": "C",
        }
        assert dict(zip(figure.layout.xaxis.tickvals, figure.layout.xaxis.ticktext)) == {
            "A": "same",
            "B": "same",
            "C": "same",
        }
    else:
        axis = figure.axes[0]
        assert [tick.get_text() for tick in axis.get_xticklabels()] == ["same", "same", "same"]
        assert {text.get_text(): text.get_position() for text in axis.texts} == {
            "4.00": (1.0, 4.0),
            "6.00": (0.0, 6.0),
            "8.00": (2.0, 8.0),
        }
        centers = [patch.get_x() + patch.get_width() / 2 for patch in axis.patches]
        assert centers == pytest.approx([1.0, 2.0, 0.0, 1.0, 2.0, 0.0])
    pd.testing.assert_frame_equal(data, original)


def test_annotation_context_preserves_numeric_positions_paper_coordinates_and_unknowns() -> None:
    figure, axis = plt.subplots()
    try:
        result = MatplotlibTraceRenderer.render([BarTraceConfig(x=[10, 20], y=[2, 3])], axis)
        assert result.x_category_positions == {}
        spec = FigureConfig(
            annotations=[
                AnnotationConfig(x=10, y=2, text="numeric", xref="data", yref="data"),
                AnnotationConfig(x=0.25, y=0.75, text="paper", xref="paper", yref="paper"),
                AnnotationConfig(x="missing", y=2, text="unknown", xref="data", yref="data"),
            ]
        )
        FigureSpecToMatplotlib._apply_annotations(spec, axis, result)
        texts = {text.get_text(): text for text in axis.texts}
        assert set(texts) == {"numeric", "paper"}
        assert texts["numeric"].get_position() == (10, 2)
        assert texts["paper"].get_position() == (0.25, 0.75)
        assert texts["numeric"].xycoords is axis.transData
        assert texts["paper"].xycoords is axis.transAxes
    finally:
        plt.close(figure)


def test_precomputed_group_coordinates_do_not_gain_categorical_mapping() -> None:
    figure, axis = plt.subplots()
    try:
        result = MatplotlibTraceRenderer.render(
            [BarTraceConfig(x=["A", "B"], x_positions=[7.0, 9.0], y=[2, 3])],
            axis,
            category_order=["B", "A"],
        )
        assert not result.x_category_positions
        centers = [patch.get_x() + patch.get_width() / 2 for patch in axis.patches]
        assert centers == [7.0, 9.0]
    finally:
        plt.close(figure)
