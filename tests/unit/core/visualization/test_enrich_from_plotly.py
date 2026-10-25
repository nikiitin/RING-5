"""Tests for PlotlyFigureSpecBuilder.enrich_from_plotly()."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes as MplAxes
import plotly.graph_objects as go
import pytest
from unittest.mock import MagicMock

from src.core.models.visualization.figure_config import FigureConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.config_builder import PlotlyFigureSpecBuilder


def _make_spec(**kwargs: Any) -> FigureConfig:
    """Build a minimal FigureConfig for testing."""
    return FigureConfig(**kwargs)


def _make_layout(**attrs: Any) -> MagicMock:
    """Build a mock Plotly layout with configurable attributes."""
    layout = MagicMock()
    for key in ("xaxis", "yaxis", "annotations", "legend3"):
        if key not in attrs:
            setattr(layout, key, None)
    for key, val in attrs.items():
        setattr(layout, key, val)
    return layout


def _make_fig(layout: Any) -> MagicMock:
    fig = MagicMock()
    fig.layout = layout
    return fig


class TestEnrichTickValues:
    """Tick values / tick text transfer."""

    def test_transfers_x_tick_values_and_text(self) -> None:
        xaxis = MagicMock()
        xaxis.tickvals = [0, 1, 2]
        xaxis.ticktext = ["A", "B", "C"]
        layout = _make_layout(xaxis=xaxis)
        fig = _make_fig(layout)

        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        assert spec.axes is not None
        assert spec.axes.x.tick_values == [0, 1, 2]
        assert spec.axes.x.tick_text == ["A", "B", "C"]

    def test_transfers_y_tick_values(self) -> None:
        yaxis = MagicMock()
        yaxis.tickvals = [10, 20]
        yaxis.ticktext = ["Low", "High"]
        layout = _make_layout(yaxis=yaxis)
        fig = _make_fig(layout)

        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        assert spec.axes is not None
        assert spec.axes.y.tick_values == [10, 20]
        assert spec.axes.y.tick_text == ["Low", "High"]

    def test_no_tick_values_leaves_spec_unchanged(self) -> None:
        xaxis = MagicMock()
        xaxis.tickvals = None
        xaxis.ticktext = None
        layout = _make_layout(xaxis=xaxis)
        fig = _make_fig(layout)

        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        assert spec.axes is not None
        assert spec.axes.x.tick_values is None
        assert spec.axes.x.tick_text is None

    def test_handles_numpy_array_tickvals(self) -> None:
        """Tick values might be numpy arrays from Plotly."""
        import numpy as np

        xaxis = MagicMock()
        xaxis.tickvals = np.array([0.5, 1.5, 2.5])
        xaxis.ticktext = np.array(["X", "Y", "Z"])
        layout = _make_layout(xaxis=xaxis)
        fig = _make_fig(layout)

        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        assert spec.axes is not None
        assert spec.axes.x.tick_values == [0.5, 1.5, 2.5]
        assert spec.axes.x.tick_text == ["X", "Y", "Z"]


class TestEnrichAnnotations:
    """Annotation transfer from Plotly layout."""

    def test_transfers_annotations_when_spec_has_none(self) -> None:
        ann = MagicMock()
        ann.text = "Group A"
        ann.x = 1.0
        ann.y = -0.1
        ann.xref = "data"
        ann.yref = "paper"
        ann.showarrow = False
        ann.font = MagicMock(size=10, color="#333")
        ann.textangle = 0
        ann.borderwidth = 0
        ann.bordercolor = ""
        ann.borderpad = 0
        ann.bgcolor = ""
        ann.align = "center"
        ann.xanchor = "center"
        ann.yanchor = "top"

        layout = _make_layout(annotations=[ann])
        fig = _make_fig(layout)

        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        assert len(spec.annotations) == 1
        assert spec.annotations[0].text == "Group A"

    def test_does_not_overwrite_existing_annotations(self) -> None:
        from src.core.models.visualization.annotation_config import AnnotationConfig

        existing = AnnotationConfig(text="Existing")
        spec = _make_spec(annotations=[existing])

        ann = MagicMock()
        ann.text = "New"
        layout = _make_layout(annotations=[ann])
        fig = _make_fig(layout)

        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        assert len(spec.annotations) == 1
        assert spec.annotations[0].text == "Existing"


class TestEnrichLegend3:
    """Tertiary legend (legend3) transfer."""

    def test_appends_tertiary_legend_spec(self) -> None:
        legend3 = MagicMock()
        legend3.x = 0.5
        legend3.y = -0.2
        legend3.xanchor = "center"
        legend3.yanchor = "top"
        layout = _make_layout(legend3=legend3)
        fig = _make_fig(layout)

        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        tertiary = [lg for lg in spec.legends if lg.role == "tertiary"]
        assert len(tertiary) == 1
        assert tertiary[0].position_x == 0.5
        assert tertiary[0].position_y == -0.2

    def test_no_legend3_no_change(self) -> None:
        layout = _make_layout()
        fig = _make_fig(layout)

        spec = _make_spec()
        n_before = len(spec.legends)
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        assert len(spec.legends) == n_before


class TestEnrichEdgeCases:
    """Edge cases and robustness."""

    def test_no_layout_attribute(self) -> None:
        fig = MagicMock(spec=[])  # No layout attribute
        del fig.layout
        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)  # Should not raise

    def test_none_layout(self) -> None:
        fig = MagicMock()
        fig.layout = None
        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)  # Should not raise


class TestEnrichAndApply:
    """Full pipeline: config -> FigureConfig -> enrich -> resolve -> apply."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> Generator[None]:
        fig, ax = plt.subplots()
        assert isinstance(ax, MplAxes)
        self.fig = fig
        self.ax: MplAxes = ax
        yield
        plt.close(self.fig)

    def test_enriched_tick_labels_applied(self) -> None:
        """Tick labels from Plotly figure appear on matplotlib axes."""
        config: dict[str, Any] = {"width": 800, "height": 500}
        spec = ConfigSpecBuilder.from_config(config, "bar")

        plotly_fig = go.Figure()
        plotly_fig.add_bar(x=[0, 1, 2], y=[10, 20, 30])
        plotly_fig.update_xaxes(tickvals=[0, 1, 2], ticktext=["A", "B", "C"])

        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
        spec = resolve_config(spec)

        assert spec.axes is not None
        assert spec.axes.x.tick_values == [0, 1, 2]
        assert spec.axes.x.tick_text == ["A", "B", "C"]

        FigureSpecToMatplotlib.apply(spec, self.ax)

        get_labels_fn = self.ax.get_xticklabels
        labels = [t.get_text() for t in get_labels_fn()]
        assert "A" in labels

    def test_enriched_annotations_applied(self) -> None:
        """Annotations from Plotly figure appear on matplotlib axes."""
        config: dict[str, Any] = {"width": 800, "height": 500}
        spec = ConfigSpecBuilder.from_config(config, "bar")

        plotly_fig = go.Figure()
        plotly_fig.add_bar(x=["A"], y=[10])
        plotly_fig.update_layout(
            annotations=[
                dict(
                    text="Group Label",
                    x=0.5,
                    y=-0.1,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=12, color="#333"),
                )
            ]
        )

        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
        spec = resolve_config(spec)

        assert len(spec.annotations) == 1

        FigureSpecToMatplotlib.apply(spec, self.ax)
        texts = self.ax.texts
        assert len(texts) >= 1
        text_content = " ".join(t.get_text() for t in texts)
        assert "Group" in text_content
