"""Original series identities survive native styling, display aliases and composition."""

from copy import deepcopy
from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from matplotlib.colors import to_hex
from matplotlib.container import BarContainer

from ring5 import Session, Table
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import LegendConfig
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering._render_result import (
    MatplotlibFigureResult,
    NativeRenderResult,
    PlotlyRenderResult,
)
from src.web.rendering.dashboard_builder import build_dashboard_figure, prepare_dashboard
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.plotly_connector import FigureSpecToPlotly

Engine = Literal["plotly", "matplotlib"]


def _apply(spec: FigureConfig, native: NativeRenderResult) -> None:
    if isinstance(native, PlotlyRenderResult):
        FigureSpecToPlotly.apply(spec, native)
    else:
        FigureSpecToMatplotlib.apply(spec, native)


def _state(native: NativeRenderResult) -> list[tuple[str, str, tuple[float, ...]]]:
    if isinstance(native, PlotlyRenderResult):
        result = []
        for panel in native.panel_bindings:
            for binding in panel:
                trace = binding.native_trace
                assert isinstance(trace, go.Bar)
                assert isinstance(trace.marker.color, str)
                assert trace.y is not None
                result.append(
                    (
                        binding.original_name,
                        trace.marker.color,
                        tuple(float(y) for y in np.asarray(trace.y)),
                    )
                )
        return result
    result = []
    for mpl_panel in native.panels:
        for mpl_binding in mpl_panel.bindings:
            container = mpl_binding.legend_handle
            assert isinstance(container, BarContainer)
            result.append(
                (
                    mpl_binding.original_name,
                    to_hex(container.patches[0].get_facecolor()),
                    tuple(float(patch.get_height()) for patch in container.patches),
                )
            )
    return result


def _legend_texts(native: NativeRenderResult) -> list[str]:
    if isinstance(native, PlotlyRenderResult):
        labels = []
        for trace in native.figure.data:
            assert isinstance(trace, go.Bar) and isinstance(trace.name, str)
            if trace.showlegend is not False:
                labels.append(trace.name)
        return labels
    if native.shared_legend:
        return [text.get_text() for legend in native.figure.legends for text in legend.texts]
    return [
        text.get_text()
        for axes in native.figure.axes
        if (legend := axes.get_legend()) is not None
        for text in legend.texts
    ]


def _config() -> dict[str, Any]:
    return {
        "x": "x",
        "y": "value",
        "color": "group",
        "legend_order": ["B", "A"],
        "legend_labels": {"A": "Same", "B": "Same", "inactive": "Unselected"},
        "series_styles": {
            "A": {"use_color": True, "color": "#ff0000"},
            "B": {"use_color": True, "color": "#0000ff"},
        },
    }


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {"x": ["a", "b", "a", "b"], "group": ["A", "A", "B", "B"], "value": [3.0, 5.0, 7.0, 9.0]}
    )


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_public_aliases_preserve_original_style_order_values_and_direct_reapply(
    engine: Engine,
) -> None:
    frame, config = _frame(), _config()
    before_frame, before_config = frame.copy(deep=True), deepcopy(config)
    with Session() as session:
        plot = session.create_plot("bar", data=Table(frame), config=config)
        figure = session.render(plot, engine=engine)
        native = plot.render_artifact.native_result
        assert native is not None
        assert _state(native) == [("B", "#0000ff", (7.0, 9.0)), ("A", "#ff0000", (3.0, 5.0))]
        assert _legend_texts(native) == ["Same", "Same"]
        assert plot.render_artifact.trace_result is not None
        assert [trace.name for trace in plot.render_artifact.trace_result.traces] == ["B", "A"]
        if isinstance(figure, go.Figure):
            groups = []
            for trace in figure.data:
                assert isinstance(trace, go.Bar)
                groups.append(trace.legendgroup)
            assert groups == ["B", "A"]
        spec = resolve_config(
            FigureConfig(
                legends=[LegendConfig()],
                legend_labels={"A": "B", "B": "C"},
                trace_overrides={
                    "A": SeriesStyleConfig(color="#008000", marker_size=0, line_width=0),
                    "B": SeriesStyleConfig(color="#800080", marker_size=0, line_width=0),
                },
            )
        )
        _apply(spec, native)
        expected = [("B", "#800080", (7.0, 9.0)), ("A", "#008000", (3.0, 5.0))]
        assert _state(native) == expected
        assert _legend_texts(native) == ["C", "B"]
        _apply(spec, native)
        assert _state(native) == expected
        assert _legend_texts(native) == ["C", "B"]
        assert plot.config == before_config
        assert config == before_config
        pd.testing.assert_frame_equal(frame, before_frame)
        if not isinstance(figure, go.Figure):
            plt.close(figure)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("shared", [False, True])
def test_real_dashboard_keeps_colliding_labels_and_reprojects_shared_entries(
    engine: Engine, shared: bool
) -> None:
    with Session() as session:
        plots = [
            session.create_plot("bar", data=Table(_frame()), config=_config()) for _ in range(2)
        ]
        dashboard = session.create_dashboard(plots, shared_legend=shared)
        native = build_dashboard_figure(prepare_dashboard(plots, dashboard), engine=engine)
        assert _state(native) == [("B", "#0000ff", (7.0, 9.0)), ("A", "#ff0000", (3.0, 5.0))] * 2
        assert _legend_texts(native) == ["Same"] * (2 if shared else 4)
        spec = resolve_config(
            FigureConfig(
                legends=[LegendConfig()],
                legend_labels={"A": "Updated", "B": "Updated"},
                trace_overrides={
                    "A": SeriesStyleConfig(color="#008000", marker_size=0, line_width=0),
                    "B": SeriesStyleConfig(color="#800080", marker_size=0, line_width=0),
                },
            )
        )
        _apply(spec, native)
        _apply(spec, native)
        assert _state(native) == [("B", "#800080", (7.0, 9.0)), ("A", "#008000", (3.0, 5.0))] * 2
        assert _legend_texts(native) == ["Updated"] * (2 if shared else 4)
        native.validate()
        if isinstance(native, MatplotlibFigureResult):
            plt.close(native.figure)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("display", ["", "_Shown", "001"])
def test_literal_display_labels_do_not_change_source_visibility(
    engine: Engine, display: str
) -> None:
    config = {**_config(), "legend_labels": {"A": display, "B": display}}
    with Session() as session:
        plot = session.create_plot("bar", data=Table(_frame()), config=config)
        session.render(plot, engine=engine)
        native = plot.render_artifact.native_result
        assert native is not None
        assert _legend_texts(native) == [display, display]
        assert _state(native) == [("B", "#0000ff", (7.0, 9.0)), ("A", "#ff0000", (3.0, 5.0))]
        if isinstance(native, MatplotlibFigureResult):
            plt.close(native.figure)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_source_style_slots_include_hidden_and_underscore_sources_across_axes(
    engine: Engine,
) -> None:
    from src.core.models.visualization.trace_build_result import TraceBuildResult
    from src.core.models.visualization.trace_config import BarTraceConfig
    from src.web.rendering.figure_preparation import PreparedFigure
    from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
    from src.web.rendering.plotly_figure_builder import build_plotly_figure

    traces = [
        BarTraceConfig(name="primary", x=[0.0], y=[3.0]),
        BarTraceConfig(name="hidden", x=[0.0], y=[9.0], visible=False),
        BarTraceConfig(name="secondary", x=[0.0], y=[5.0], yaxis="y2", legend_role="secondary"),
        BarTraceConfig(name="_raw", x=[0.0], y=[7.0]),
    ]
    spec = resolve_config(
        FigureConfig(
            legends=[LegendConfig(), LegendConfig(role="secondary")],
            series_styles=[
                SeriesStyleConfig(hatching_pattern=pattern, marker_size=0, line_width=0)
                for pattern in ("/", "x", "+", ".")
            ],
        )
    )
    prepared = PreparedFigure({}, TraceBuildResult(traces=traces, secondary_y=True), spec)
    native = (
        build_plotly_figure(prepared)
        if engine == "plotly"
        else build_matplotlib_figure_from_prepared(prepared)
    )
    if isinstance(native, PlotlyRenderResult):
        native.figure.data = tuple(reversed(native.figure.data))
    _apply(spec, native)
    patterns = {}
    values = {}
    if isinstance(native, PlotlyRenderResult):
        for source in native.panel_bindings[0]:
            trace = source.native_trace
            assert isinstance(trace, go.Bar)
            patterns[source.original_name] = trace.marker.pattern.shape
            values[source.original_name] = tuple(float(value) for value in np.asarray(trace.y))
        assert patterns == {"primary": "/", "hidden": "x", "secondary": "+", "_raw": "."}
        assert values == {"primary": (3.0,), "hidden": (9.0,), "secondary": (5.0,), "_raw": (7.0,)}
    else:
        for mpl_source in native.panels[0].bindings:
            if mpl_source.original_name == "hidden":
                assert mpl_source.owned_data == () and mpl_source.legend_handle is None
                continue
            container = mpl_source.legend_handle
            assert isinstance(container, BarContainer)
            patterns[mpl_source.original_name] = container.patches[0].get_hatch()
            values[mpl_source.original_name] = tuple(
                float(patch.get_height()) for patch in container.patches
            )
        assert patterns == {"primary": "/", "secondary": "+", "_raw": "."}
        assert values == {"primary": (3.0,), "secondary": (5.0,), "_raw": (7.0,)}
        plt.close(native.figure)
    assert [trace.name for trace in traces] == ["primary", "hidden", "secondary", "_raw"]
