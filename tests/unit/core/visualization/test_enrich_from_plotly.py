"""Tests for PlotlyFigureSpecBuilder.enrich_from_plotly()."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.core.models.visualization.figure_config import FigureConfig
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
    """Boxed legend (legend3) transfer."""

    def test_appends_boxed_legend_spec(self) -> None:
        legend3 = MagicMock()
        legend3.x = 0.5
        legend3.y = -0.2
        legend3.xanchor = "center"
        legend3.yanchor = "top"
        layout = _make_layout(legend3=legend3)
        fig = _make_fig(layout)

        spec = _make_spec()
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, fig)

        boxed = [lg for lg in spec.legends if lg.role == "boxed"]
        assert len(boxed) == 1
        assert boxed[0].position_x == 0.5
        assert boxed[0].position_y == -0.2

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
