"""Area lines and fills consume the same supported CSS color formats."""

from copy import deepcopy
from typing import Literal

from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5
from src.core.models.visualization.trace_config import LineTraceConfig


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize(
    "color, expected_rgb",
    [
        ("#0a141e", (10 / 255, 20 / 255, 30 / 255)),
        ("rgba(10,20,30,0.35)", (10 / 255, 20 / 255, 30 / 255)),
        ("hsl(240 100% 50% / 0.25)", (0.0, 0.0, 1.0)),
    ],
)
def test_area_css_colors_preserve_measured_outline_and_fill_geometry(
    engine: Literal["plotly", "matplotlib"],
    color: str,
    expected_rgb: tuple[float, float, float],
) -> None:
    # [test->req~ring5.plot.area~1]
    # [test->req~ring5.figure.colors~1]
    frame = pd.DataFrame({"x": [0.0, 1.0], "y": [3.0, 5.0]})
    original = frame.copy(deep=True)
    config = {"x": "x", "y": "y", "color_palette": [color]}
    original_config = deepcopy(config)

    with ring5.Session() as session:
        plot = session.create_plot("area", data=ring5.Table(frame), config=config)
        native = session.render(plot, engine=engine)
        result = plot.render_artifact.trace_result
        assert result is not None and len(result.traces) == 1
        trace = result.traces[0]
        assert isinstance(trace, LineTraceConfig)
        assert trace.x == [0.0, 1.0] and trace.y == [3.0, 5.0]
        assert trace.fill_base == [0.0, 0.0] and trace.color == color
        assert plot.config["color_palette"] == [color]

        if isinstance(native, go.Figure):
            line = native.data[0]
            assert isinstance(line, go.Scatter)
            assert list(line.x) == [0.0, 1.0] and list(line.y) == [3.0, 5.0]
            assert line.fill == "tozeroy"
            assert line.line.color == color
        else:
            assert isinstance(native, Figure)
            axis = native.axes[0]
            assert len(axis.lines) == len(axis.collections) == 1
            np.testing.assert_array_equal(np.asarray(axis.lines[0].get_xdata()), [0.0, 1.0])
            np.testing.assert_array_equal(np.asarray(axis.lines[0].get_ydata()), [3.0, 5.0])
            assert to_rgba(axis.lines[0].get_color())[:3] == pytest.approx(expected_rgb)
            fill = axis.collections[0]
            assert isinstance(fill, PolyCollection)
            assert np.asarray(fill.get_facecolor())[0, :3] == pytest.approx(expected_rgb)
            vertices = np.asarray(fill.get_paths()[0].vertices, dtype=float)
            points = {tuple(point) for point in vertices}
            assert points == {(0.0, 0.0), (0.0, 3.0), (1.0, 5.0), (1.0, 0.0)}
            assert session.export_bytes(native, "png").startswith(b"\x89PNG\r\n\x1a\n")
        # Opacity composition remains a separate policy; this checks CSS RGB
        # projection and the scientific geometry without changing that policy.
        assert config == original_config
        pd.testing.assert_frame_equal(frame, original)
