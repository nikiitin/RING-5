"""Every shared hatch token has an explicit native projection and presence semantics."""

from dataclasses import replace
from typing import Any, Literal, cast

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5
from src.core.common.plot_payload import BAR_HATCH_PATTERNS
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
)
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.figure_preparation import PreparedFigure, prepare_figure
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
from src.web.rendering.plotly_connector import FigureSpecToPlotly
from src.web.rendering.plotly_figure_builder import build_plotly_figure


def _prepared(pattern: str = "", **config: Any) -> PreparedFigure:
    data = pd.DataFrame({"x": ["a", "b"], "y": [3.0, 5.0]})

    def traces(frame: pd.DataFrame, candidate: dict[str, Any]) -> TraceBuildResult:
        return TraceBuildResult(
            traces=[
                BarTraceConfig(
                    name="Measured", x=frame["x"].tolist(), y=frame["y"].tolist(), pattern=pattern
                )
            ]
        )

    return prepare_figure(data, config, "bar", traces)


def _native(prepared: PreparedFigure, engine: str) -> Any:
    return (
        build_plotly_figure(prepared)
        if engine == "plotly"
        else build_matplotlib_figure_from_prepared(prepared)[0]
    )


def _assert_pattern(native: Any, engine: str, pattern: str, index: int = 0) -> None:
    if engine == "plotly":
        style = native.data[index].marker.pattern
        if pattern in ("o", "O", "*"):
            assert style.path and style.shape is None and style.solidity is None
            assert style.size == 8
        else:
            assert style.shape == pattern and style.path is None
    else:
        assert native.axes[0].patches[index].get_hatch() == pattern


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("pattern", BAR_HATCH_PATTERNS)
def test_public_series_override_renders_every_current_pattern(
    engine: Literal["plotly", "matplotlib"], pattern: str
) -> None:
    # [test->req~ring5.figure.series-styling~1]
    frame = pd.DataFrame({"x": ["a", "b"], "y": [3.0, 5.0]})
    original = frame.copy(deep=True)
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(frame),
            config={
                "x": "x",
                "y": "y",
                "series_styles": {"y": {"pattern": pattern, "color": "#123456", "use_color": True}},
            },
        )
        native = cast(Any, session.render(plot, engine=engine))
        _assert_pattern(native, engine, pattern)
        if engine == "plotly":
            assert list(native.data[0].y) == [3.0, 5.0]
            assert native.data[0].marker.color == "#123456"
        else:
            assert [patch.get_height() for patch in native.axes[0].patches] == [3.0, 5.0]
            legend = native.axes[0].get_legend()
            assert legend.legend_handles[0].get_hatch() == pattern
        pd.testing.assert_frame_equal(frame, original)
        assert plot.config["series_styles"]["y"]["pattern"] == pattern


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("pattern", BAR_HATCH_PATTERNS)
@pytest.mark.parametrize("owner", ["intrinsic", "global"])
def test_neutral_and_global_typed_patterns_use_the_same_native_projection(
    engine: str, pattern: str, owner: str
) -> None:
    prepared = _prepared(pattern if owner == "intrinsic" else "")
    if owner == "global":
        prepared = replace(
            prepared,
            spec=replace(
                prepared.spec, series_styles=[SeriesStyleConfig(hatching_pattern=pattern)]
            ),
        )
    native = _native(prepared, engine)
    try:
        if pattern or owner == "global":
            _assert_pattern(native, engine, pattern)
        elif engine == "plotly":
            assert native.data[0].marker.pattern.shape is None
        else:
            assert native.axes[0].patches[0].get_hatch() is None
    finally:
        if engine == "matplotlib":
            plt.close(native)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_reapplication_clears_incompatible_paths_and_preserves_absent_pattern(engine: str) -> None:
    # [test->req~ring5.figure.series-styling~1]
    native = _native(_prepared("O"), engine)
    try:
        for pattern in ("/", "", "*", "o", "O", "x"):
            spec = resolve_config(
                FigureConfig(
                    trace_overrides={"Measured": SeriesStyleConfig(hatching_pattern=pattern)}
                )
            )
            if engine == "plotly":
                FigureSpecToPlotly.apply(spec, native)
            else:
                FigureSpecToMatplotlib.apply(spec, native.axes[0])
            _assert_pattern(native, engine, pattern)
        spec = resolve_config(
            FigureConfig(trace_overrides={"Measured": SeriesStyleConfig(color="#ff0000")})
        )
        if engine == "plotly":
            FigureSpecToPlotly.apply(spec, native)
            assert native.data[0].marker.color == "#ff0000"
            assert list(native.data[0].y) == [3.0, 5.0]
        else:
            FigureSpecToMatplotlib.apply(spec, native.axes[0])
            assert [patch.get_height() for patch in native.axes[0].patches] == [3.0, 5.0]
        _assert_pattern(native, engine, "x")
    finally:
        if engine == "matplotlib":
            plt.close(native)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("override", ["", "*"])
def test_explicit_override_wins_over_default_stripes_and_global_style(
    engine: str, override: str
) -> None:
    prepared = _prepared(
        "x",
        enable_stripes=True,
        hatching_sequence=["/"],
        series_styles={"Measured": {"pattern": override}},
    )
    prepared = replace(
        prepared,
        spec=replace(prepared.spec, series_styles=[SeriesStyleConfig(hatching_pattern="O")]),
    )
    native = _native(prepared, engine)
    try:
        _assert_pattern(native, engine, override)
        if engine == "matplotlib":
            legend = native.axes[0].get_legend()
            assert legend.legend_handles[0].get_hatch() == override
    finally:
        if engine == "matplotlib":
            plt.close(native)


def test_pattern_absence_and_solid_remain_distinct_through_typed_roundtrip() -> None:
    # [test->req~ring5.figure.series-styling~1]
    assert SeriesStyleConfig().hatching_pattern is None
    assert SeriesStyleConfig.from_dict({}).hatching_pattern is None
    assert SeriesStyleConfig.from_dict({"hatching_pattern": ""}).hatching_pattern == ""
    for value in (None, "", "o"):
        style = SeriesStyleConfig(hatching_pattern=value)
        assert SeriesStyleConfig.from_dict(style.to_dict()) == style
    absent = ConfigSpecBuilder.from_config({"series_styles": {"Measured": {"color": "red"}}})
    solid = ConfigSpecBuilder.from_config({"series_styles": {"Measured": {"pattern": ""}}})
    assert absent.trace_overrides["Measured"].hatching_pattern is None
    assert solid.trace_overrides["Measured"].hatching_pattern == ""


@pytest.mark.parametrize("value", [{"shape": "x"}, True, 3, [], "bad", "//"])
def test_wrong_typed_patterns_reject_without_coercion(value: Any) -> None:
    with pytest.raises(ValueError, match="hatching_pattern"):
        SeriesStyleConfig(hatching_pattern=value)
    with pytest.raises(ValueError, match="hatching_pattern"):
        SeriesStyleConfig.from_dict({"hatching_pattern": value})


@pytest.mark.parametrize("owner", ["global", "per_trace"])
def test_typed_marker_sizes_target_only_native_marker_families(owner: str) -> None:
    frame = pd.DataFrame({"x": [1, 2], "y": [3.0, 5.0]})

    def traces(data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        return TraceBuildResult(
            traces=[
                BarTraceConfig(name="Bars", x=[1, 2], y=[3.0, 5.0]),
                LineTraceConfig(name="Line", x=[1, 2], y=[3.0, 5.0]),
                ScatterTraceConfig(name="Points", x=[1, 2], y=[3.0, 5.0]),
            ]
        )

    prepared = prepare_figure(frame, {}, "bar", traces)
    style = SeriesStyleConfig(marker_size=13, symbol="diamond", hatching_pattern="O")
    spec = replace(
        prepared.spec,
        **(
            {"series_styles": [style]}
            if owner == "global"
            else {"trace_overrides": {name: style for name in ("Bars", "Line", "Points")}}
        ),
    )
    native = build_plotly_figure(replace(prepared, spec=spec))
    _assert_pattern(native, "plotly", "O")
    assert isinstance(native.data[0], go.Bar)
    assert "size" not in native.data[0].marker.to_plotly_json()
    for trace in native.data[1:]:
        assert isinstance(trace, go.Scatter)
        assert trace.marker.size == 13
        if owner == "per_trace":
            assert trace.marker.symbol == "diamond"
        assert list(trace.x) == [1, 2] and list(trace.y) == [3.0, 5.0]
