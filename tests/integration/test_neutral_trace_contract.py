"""Unsupported neutral trace families fail visibly through both engines."""

from typing import Any, Literal, cast

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import ring5
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HeatmapTraceConfig,
    TraceConfig,
)
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer
from src.web.rendering.trace_to_plotly import _convert_trace, traces_to_plotly


class UnknownTrace(TraceConfig):
    """Unregistered family whose inherited tag must not turn it into a bar."""


class SpecializedBar(BarTraceConfig):
    """A registered plot may specialize a supported neutral trace family."""


@pytest.mark.parametrize("trace_class", [TraceConfig, UnknownTrace])
@pytest.mark.parametrize("visible", [False, True])
def test_both_converters_reject_unknown_families_before_drawing(
    trace_class: type[TraceConfig], visible: bool
) -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    trace = trace_class(name="unsupported", x=["a"], y=[1.0], visible=visible)
    with pytest.raises(TypeError, match=f"Unsupported trace type: {trace_class.__name__}"):
        traces_to_plotly(TraceBuildResult(traces=[trace]))
    with pytest.raises(TypeError, match=f"Unsupported trace type: {trace_class.__name__}"):
        _convert_trace(trace)
    figure, axis = plt.subplots()
    try:
        with pytest.raises(TypeError, match=f"Unsupported trace type: {trace_class.__name__}"):
            MatplotlibTraceRenderer.render([BarTraceConfig(x=["a"], y=[2.0]), trace], axis)
        assert not axis.patches and not axis.lines
    finally:
        plt.close(figure)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("mixed_heatmaps", [False, True])
@pytest.mark.public_api
def test_public_render_exposes_unknown_trace_as_typed_error(
    engine: Literal["plotly", "matplotlib"],
    mixed_heatmaps: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    before = set(plt.get_fignums())
    traces: list[TraceConfig] = [UnknownTrace(name="unsupported", x=["a"], y=[1.0])]
    if mixed_heatmaps:
        traces.extend([HeatmapTraceConfig(z=[[1.0]]), HeatmapTraceConfig(z=[[2.0]])])
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar", data=pd.DataFrame({"x": ["a"], "y": [1.0]}), config={"x": "x", "y": "y"}
        )
        monkeypatch.setattr(
            plot,
            "create_traces",
            lambda data, config: TraceBuildResult(traces=traces),
        )
        with pytest.raises(ring5.RenderError, match="Unsupported trace type: UnknownTrace"):
            session.render(plot, engine=engine)
    assert set(plt.get_fignums()) == before


def test_supported_trace_subclasses_preserve_data_in_both_engines() -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    trace = SpecializedBar(name="measurements", x=["a", "b"], y=[2.0, 5.0])
    native = traces_to_plotly(TraceBuildResult(traces=[trace]))
    assert list(cast(Any, native.data[0]).y) == [2.0, 5.0]
    figure, axis = plt.subplots()
    try:
        result = MatplotlibTraceRenderer.render([trace], axis)
        assert result.trace_count == 1
        assert [cast(Any, patch).get_height() for patch in axis.patches] == [2.0, 5.0]
    finally:
        plt.close(figure)
