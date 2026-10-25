"""Typed annotation admission precedes native allocation and partial publication."""

from dataclasses import asdict
from types import SimpleNamespace
from typing import Any, Literal, cast
from unittest.mock import patch

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import ring5
from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.rendering.figure_preparation import prepare_figure
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
from src.web.rendering.trace_to_plotly import traces_to_plotly


def _unknown(kind: str) -> Any:
    if kind == "dict":
        return {"text": ""}
    if kind == "duck":
        return SimpleNamespace(**asdict(AnnotationConfig()))
    return object()


@pytest.mark.parametrize("kind", ["dict", "duck", "object"])
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_unknown_annotations_reject_before_native_allocation(
    kind: str, engine: Literal["plotly", "matplotlib"]
) -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    result = TraceBuildResult(
        traces=[BarTraceConfig(x=["a"], y=[1.0], visible=False)],
        annotations=[_unknown(kind)],
    )
    with (
        patch("plotly.graph_objects.Figure", side_effect=AssertionError("Plotly allocation")),
        patch(
            "src.web.rendering.trace_to_plotly.make_subplots",
            side_effect=AssertionError("subplot allocation"),
        ),
        patch.object(
            FigureSpecToMatplotlib, "create_figure", side_effect=AssertionError("MPL allocation")
        ),
        patch.object(
            FigureSpecToMatplotlib,
            "create_multi_figure",
            side_effect=AssertionError("facet allocation"),
        ),
        pytest.raises(TypeError, match="Unsupported annotation type"),
    ):
        if engine == "plotly":
            traces_to_plotly(result)
        else:
            prepared = prepare_figure(
                pd.DataFrame({"x": ["a"], "y": [1.0]}), {}, "bar", lambda data, config: result
            )
            build_matplotlib_figure_from_prepared(prepared)


@pytest.mark.parametrize("kind", ["dict", "duck", "object"])
@pytest.mark.parametrize("visible", [False, True])
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.public_api
def test_public_annotation_failures_preserve_the_published_native_figure(
    kind: str,
    visible: bool,
    engine: Literal["plotly", "matplotlib"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    before = set(plt.get_fignums())
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [1.0]})),
            config={"x": "x", "y": "y"},
        )
        session.render(plot, engine=engine)
        published = plot.render_artifact.figure
        monkeypatch.setattr(
            plot,
            "create_traces",
            lambda data, config: TraceBuildResult(
                traces=[BarTraceConfig(x=["a"], y=[1.0], visible=visible)],
                annotations=[_unknown(kind)],
            ),
        )
        with pytest.raises(ring5.RenderError, match="Unsupported annotation type"):
            session.render(plot, engine=engine)
        assert plot.render_artifact.figure is published
    assert set(plt.get_fignums()) == before


@pytest.mark.parametrize("kind", ["dict", "duck", "object"])
def test_direct_axes_annotation_admission_prevents_partial_drawing(kind: str) -> None:
    figure, axis = plt.subplots()
    try:
        spec = FigureConfig(annotations=[AnnotationConfig(text="valid"), _unknown(kind)])
        with pytest.raises(TypeError, match="Unsupported annotation type"):
            FigureSpecToMatplotlib._apply_annotations(spec, axis)
        assert not axis.texts
    finally:
        plt.close(figure)


class SpecializedAnnotation(AnnotationConfig):
    """A plot may specialize the current typed annotation family."""


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.public_api
def test_supported_annotation_subclass_survives_public_native_render(
    engine: Literal["plotly", "matplotlib"], monkeypatch: pytest.MonkeyPatch
) -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [1.0]})),
            config={"x": "x", "y": "y"},
        )
        monkeypatch.setattr(
            plot,
            "create_traces",
            lambda data, config: TraceBuildResult(
                traces=[BarTraceConfig(x=["a"], y=[1.0])],
                annotations=[
                    SpecializedAnnotation(
                        text="Measured", x=0.0, y=1.0, font_family="monospace", font_size=13
                    )
                ],
            ),
        )
        native = cast(Any, session.render(plot, engine=engine))
        if engine == "plotly":
            annotation = native.layout.annotations[0]
            assert (annotation.text, annotation.x, annotation.y) == ("Measured", 0.0, 1.0)
            assert annotation.font.family == "monospace" and annotation.font.size == 13
        else:
            annotation = native.axes[0].texts[0]
            assert annotation.get_text() == "Measured" and annotation.xy == (0.0, 1.0)
            assert annotation.get_fontfamily() == ["monospace"] and annotation.get_fontsize() == 13


def test_unknown_annotation_is_rejected_before_ownership_copy() -> None:
    class CannotCopy:
        def __deepcopy__(self, memo: dict[int, Any]) -> Any:
            raise AssertionError("unsupported annotation copied")

    result = TraceBuildResult(annotations=[cast(Any, CannotCopy())])
    with pytest.raises(TypeError, match="Unsupported annotation type: CannotCopy"):
        prepare_figure(pd.DataFrame(), {}, "custom", lambda data, config: result)
