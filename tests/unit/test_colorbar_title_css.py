"""Concrete CSS title colors reach both native heatmap engines without changing values."""

from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import pytest
from matplotlib.colors import to_rgba

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import LegendConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.figure_preparation import PreparedFigure
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
from src.web.rendering.plotly_figure_builder import build_plotly_figure


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize(
    "color,expected",
    [
        ("rgba(10,20,30,0.5)", (10 / 255, 20 / 255, 30 / 255, 0.5)),
        ("hsla(120,100%,25%,0.5)", (0.0, 0.5, 0.0, 0.5)),
        ("#0a141e80", (10 / 255, 20 / 255, 30 / 255, 128 / 255)),
        ("red", (1.0, 0.0, 0.0, 1.0)),
    ],
)
def test_native_heatmap_title_preserves_css_color_and_measured_cells(
    engine: Literal["plotly", "matplotlib"], color: str, expected: tuple[float, float, float, float]
) -> None:
    spec = resolve_config(
        FigureConfig(legends=[LegendConfig(title="Scale", title_font_color=color)])
    )
    trace = HeatmapTraceConfig(
        name="ipc", z=[[3.0, 5.0]], col_labels=["001", "NA"], row_labels=["row"]
    )
    prepared = PreparedFigure({}, TraceBuildResult(traces=[trace]), spec)
    if engine == "plotly":
        plotly = build_plotly_figure(prepared)
        native = plotly.figure.data[0]
        assert isinstance(native, go.Heatmap)
        assert native.colorbar.title.font.color == color
        assert native.colorbar.title.text == "Scale"
        np.testing.assert_array_equal(np.asarray(native.z), [[3.0, 5.0]])
    else:
        matplotlib = build_matplotlib_figure_from_prepared(prepared)
        try:
            matplotlib.figure.canvas.draw()
            output = matplotlib.native_outputs.colorbars[0]
            title = output.colorbar.ax.title
            assert title.get_text() == "Scale"
            np.testing.assert_allclose(to_rgba(title.get_color()), expected)
            np.testing.assert_array_equal(
                np.asarray(output.colorbar.mappable.get_array()), [[3.0, 5.0]]
            )
        finally:
            plt.close(matplotlib.figure)
    assert spec.legends[0].title_font_color == color
    assert trace.z == [[3.0, 5.0]]
