"""Neutral metadata reaches resolved styling and both native renderers."""

from typing import Any, cast

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from matplotlib.patches import Rectangle
from matplotlib.text import Annotation

from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.rendering.config_builder import enrich_from_traces
from src.web.rendering.figure_preparation import prepare_figure
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
from src.web.rendering.plotly_figure_builder import build_plotly_figure


def _result(**metadata: Any) -> TraceBuildResult:
    return TraceBuildResult(
        traces=[BarTraceConfig(name="Measured", x=[0.0, 1.0, 2.0], y=[10.0, 20.0, 30.0])],
        **metadata,
    )


class TestEnrichTickValues:
    """Typed tick positions and labels are independent of the native engine."""

    def test_transfers_x_tick_values_and_text(self) -> None:
        result = _result(custom_x_ticks={"vals": [0.0, 1.0, 2.0], "text": ["A", "B", "C"]})
        spec = FigureConfig()
        enrich_from_traces(spec, result)
        assert spec.axes.x.tick_values == [0, 1, 2]
        assert spec.axes.x.tick_text == ["A", "B", "C"]

    def test_transfers_y_tick_values(self) -> None:
        result = _result(custom_y_ticks={"vals": [10.0, 20.0], "text": ["Low", "High"]})
        spec = FigureConfig()
        enrich_from_traces(spec, result)
        assert spec.axes.y.tick_values == [10, 20]
        assert spec.axes.y.tick_text == ["Low", "High"]

    def test_no_tick_values_leaves_spec_unchanged(self) -> None:
        spec = FigureConfig()
        enrich_from_traces(spec, _result())
        assert spec.axes.x.tick_values is None
        assert spec.axes.x.tick_text is None

    def test_preserves_fractional_tick_values(self) -> None:
        result = _result(custom_x_ticks={"vals": [0.5, 1.5, 2.5], "text": ["X", "Y", "Z"]})
        spec = FigureConfig()
        enrich_from_traces(spec, result)
        assert spec.axes.x.tick_values == [0.5, 1.5, 2.5]
        assert spec.axes.x.tick_text == ["X", "Y", "Z"]


class TestEnrichAnnotations:
    """Configured and computed annotations share one typed channel."""

    def test_transfers_annotations_when_spec_has_none(self) -> None:
        annotation = AnnotationConfig(text="Group A", x=1.0, y=-0.1, yref="paper")
        spec = FigureConfig()
        enrich_from_traces(spec, _result(annotations=[annotation]))
        assert spec.annotations == [annotation]

    def test_preserves_existing_and_computed_annotations(self) -> None:
        existing = AnnotationConfig(text="Existing")
        computed = AnnotationConfig(text="New")
        spec = FigureConfig(annotations=[existing])
        enrich_from_traces(spec, _result(annotations=[computed]))
        assert spec.annotations == [existing, computed]


class TestPreparedLegend3:
    """Explicit tertiary configuration supplies its native annotation style."""

    def test_preserves_tertiary_legend_position(self) -> None:
        result = _result(
            annotations=[
                AnnotationConfig(
                    text="1. Measured",
                    x=0.5,
                    y=-0.2,
                    xref="paper",
                    yref="paper",
                    annotation_type="boxed",
                    legend_role="tertiary",
                )
            ]
        )
        prepared = prepare_figure(
            pd.DataFrame({"value": [10.0, 20.0, 30.0]}),
            {"legend3_x": 0.5, "legend3_y": -0.2},
            "bar",
            lambda data, config: result,
        )
        tertiary = [legend for legend in prepared.spec.legends if legend.role == "tertiary"]
        assert len(tertiary) == 1
        assert tertiary[0].position_x == 0.5
        assert tertiary[0].position_y == -0.2
        native = build_plotly_figure(prepared)
        assert native.layout.annotations[0].x == 0.5
        assert native.layout.annotations[0].y == -0.2

    def test_no_tertiary_legend_without_explicit_role(self) -> None:
        spec = FigureConfig()
        before = list(spec.legends)
        enrich_from_traces(spec, _result())
        assert spec.legends == before
        assert not any(legend.role == "tertiary" for legend in spec.legends)


class TestEnrichAndApply:
    """Measured traces and neutral metadata reach actual native figures."""

    def test_enriched_tick_labels_applied(self) -> None:
        """Exact tick geometry and labels survive preparation and native drawing."""
        data = pd.DataFrame({"position": [0.0, 1.0, 2.0], "value": [10.0, 20.0, 30.0]})

        def traces(frame: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
            return TraceBuildResult(
                traces=[BarTraceConfig(x=frame["position"].tolist(), y=frame["value"].tolist())],
                custom_x_ticks={"vals": [0.0, 1.0, 2.0], "text": ["A", "B", "C"]},
            )

        prepared = prepare_figure(data, {"width": 800, "height": 500}, "bar", traces)
        assert prepared.spec.axes.x.tick_values == [0, 1, 2]
        assert prepared.spec.axes.x.tick_text == ["A", "B", "C"]
        interactive = build_plotly_figure(prepared)
        assert list(cast(go.Bar, interactive.data[0]).y) == [10, 20, 30]
        assert list(interactive.layout.xaxis.tickvals) == [0, 1, 2]
        assert list(interactive.layout.xaxis.ticktext) == ["A", "B", "C"]
        figure, spec = build_matplotlib_figure_from_prepared(prepared)
        try:
            assert spec is prepared.spec
            axis = figure.axes[0]
            assert axis.get_xticks().tolist() == [0, 1, 2]
            assert [text.get_text() for text in axis.get_xticklabels()] == ["A", "B", "C"]
            assert [cast(Rectangle, bar).get_height() for bar in axis.patches] == [10, 20, 30]
        finally:
            plt.close(figure)

    def test_enriched_annotations_applied(self) -> None:
        """A typed Group Label retains coordinates, styling and actual measured bars."""
        data = pd.DataFrame({"category": ["A"], "value": [10.0]})

        def traces(frame: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
            return TraceBuildResult(
                traces=[BarTraceConfig(x=frame["category"].tolist(), y=frame["value"].tolist())],
                annotations=[
                    AnnotationConfig(
                        text="Group Label",
                        x=0.5,
                        y=-0.1,
                        xref="paper",
                        yref="paper",
                        font_size=12,
                        font_color="#333",
                        show_arrow=False,
                    )
                ],
            )

        prepared = prepare_figure(data, {"width": 800, "height": 500}, "bar", traces)
        assert len(prepared.spec.annotations) == 1
        interactive = build_plotly_figure(prepared)
        annotation = interactive.layout.annotations[0]
        assert (annotation.text, annotation.x, annotation.y) == ("Group Label", 0.5, -0.1)
        assert (annotation.xref, annotation.yref, annotation.font.size) == ("paper", "paper", 12)
        figure, _ = build_matplotlib_figure_from_prepared(prepared)
        try:
            axis = figure.axes[0]
            assert [text.get_text() for text in axis.texts] == ["Group Label"]
            text = axis.texts[0]
            assert isinstance(text, Annotation)
            assert text.get_position() == (0.5, -0.1)
            assert text.xycoords is axis.transAxes
            assert text.get_fontsize() == 12
            assert [cast(Rectangle, bar).get_height() for bar in axis.patches] == [10]
        finally:
            plt.close(figure)
