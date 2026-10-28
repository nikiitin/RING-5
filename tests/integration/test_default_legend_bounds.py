"""Automatic public legends fit the configured canvas through native rendering and replay."""

from copy import deepcopy
import json
from pathlib import Path
from typing import Literal

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import pytest

import ring5
from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering.figure_preparation import PreparedFigure


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("typed", [False, True])
@pytest.mark.parametrize("route", ["direct", "portfolio", "recipe"])
def test_default_public_legend_fits_fixed_canvas_and_survives_replay(
    engine: Literal["plotly", "matplotlib"],
    typed: bool,
    route: str,
    tmp_path: Path,
    portfolios_dir: Path,
) -> None:
    """An omitted legend position stays automatic without clipping ordinary series labels."""
    # [test->req~ring5.figure.legends~1]
    source = tmp_path / "measurements.csv"
    source_bytes = b"category,mass\nA,1\nB,3\nC,2\n"
    source.write_bytes(source_bytes)
    spec = ring5.FigureSpec(
        x="category",
        y_columns=["mass"],
        width=480,
        height=320,
        title="Measured",
        font_family="DejaVu Sans",
        xlabel="Category",
        ylabel="Mass",
    )
    config = spec if typed else spec.to_config()
    with ring5.Session() as session:
        data = session.load(str(source))
        rows_before = data.rows()
        plot = session.create_plot("bar", data=data, config=config, name="Measured")
        original_config = deepcopy(plot.config)
        assert "legend_x" not in original_config and "legend_y" not in original_config
        if route == "portfolio":
            session.save_portfolio("legend-current")
            payload = json.loads((portfolios_dir / "legend-current.json").read_text())
            assert (payload["schema_version"], payload["version"]) == (13, "13.0")
            assert session.load_portfolio("legend-current").complete
            plot = session.plots[0]
        elif route == "recipe":
            recipe = session.capture_analysis_recipe("Legend current")
            payload_bytes = session.export_analysis_recipe(recipe)
            assert json.loads(payload_bytes)["schema_version"] == 8
            decoded = session.decode_analysis_recipe(payload_bytes)
            assert session.export_analysis_recipe(decoded) == payload_bytes
            session.run_analysis_recipe(decoded)
            plot = session.plots[0]
        figure = session.render(plot, engine=engine)
        try:
            prepared = plot.render_artifact.preparation
            assert isinstance(prepared, PreparedFigure)
            legend_style = prepared.spec.legends[0]
            assert (legend_style.position_x, legend_style.position_y) == (-1.0, -1.0)
            assert (legend_style.anchor_x, legend_style.anchor_y) == ("auto", "auto")
            assert not legend_style.custom_position
            assert (
                FigureConfig.from_dict(prepared.spec.to_dict()).to_dict() == prepared.spec.to_dict()
            )
            assert plot.config == original_config
            assert data.rows() == rows_before
            assert source.read_bytes() == source_bytes
            if isinstance(figure, go.Figure):
                assert engine == "plotly"
                assert (figure.layout.width, figure.layout.height) == (480, 320)
                assert figure.layout.margin.r == 18
                assert all(
                    getattr(figure.layout.legend, key) is None
                    for key in ("x", "y", "xanchor", "yanchor")
                )
                assert len(figure.data) == 1
                trace = figure.data[0]
                assert isinstance(trace, go.Bar)
                assert trace.x is not None and trace.y is not None
                assert list(trace.x) == ["A", "B", "C"]
                assert list(trace.y) == [1, 3, 2]
                assert trace.name == "mass" and trace.showlegend is not False
            else:
                assert engine == "matplotlib" and isinstance(figure, Figure)
                assert tuple(figure.get_size_inches()) == pytest.approx((5, 320 / 96))
                axis = figure.axes[0]
                bars = [patch for patch in axis.patches if isinstance(patch, Rectangle)]
                assert len(bars) == len(axis.patches) == 3
                assert [bar.get_height() for bar in bars] == [1, 3, 2]
                assert [bar.get_x() + bar.get_width() / 2 for bar in bars] == pytest.approx(
                    [0, 1, 2]
                )
                geometry = [bar.get_bbox().bounds for bar in bars]
                canvas = FigureCanvasAgg(figure)
                canvas.draw()
                renderer = canvas.get_renderer()
                legend = axis.get_legend()
                assert legend is not None
                assert [text.get_text() for text in legend.get_texts()] == ["mass"]
                extents = [legend.get_window_extent(renderer)]
                extents.extend(text.get_window_extent(renderer) for text in legend.get_texts())
                for bounds in extents:
                    assert bounds.x0 >= figure.bbox.x0 and bounds.y0 >= figure.bbox.y0
                    assert bounds.x1 <= figure.bbox.x1 and bounds.y1 <= figure.bbox.y1
                assert figure.bbox.bounds == pytest.approx((0, 0, 480, 320))
                assert [bar.get_bbox().bounds for bar in bars] == geometry
        finally:
            if isinstance(figure, Figure):
                plt.close(figure)
