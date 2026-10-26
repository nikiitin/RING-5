"""Shared legends keep distinct native glyphs and conservatively retain unknown styles."""

from collections.abc import MutableMapping, Sequence
from typing import Any, Literal, cast

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import pytest
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.container import BarContainer
from matplotlib.legend import Legend
from matplotlib.legend_handler import HandlerBase, HandlerLine2D
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.transforms import Affine2D

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import LegendConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering._legend_projection import matplotlib_swatch, plotly_swatch
from src.web.rendering._appearance import MatplotlibAppearance  # noqa: E402
from src.web.rendering._render_result import (
    MatplotlibFigureResult,
    MatplotlibRenderResult,
    MatplotlibTraceBinding,
    PlotlyRenderResult,
    PlotlyTraceBinding,
)
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.plotly_connector import FigureSpecToPlotly


def _plotly_shared(traces: list[go.Scatter | go.Bar]) -> PlotlyRenderResult:
    figure = go.Figure(traces)
    native = PlotlyRenderResult(
        figure,
        tuple((PlotlyTraceBinding(0, "ipc", trace, "primary", "", True),) for trace in figure.data),
        shared_legend=True,
    )
    FigureSpecToPlotly.apply(resolve_config(FigureConfig(legend_labels={"ipc": "IPC"})), native)
    return native


def _shown(native: PlotlyRenderResult) -> list[bool]:
    flags = []
    for trace in native.figure.data:
        assert isinstance(trace, (go.Scatter, go.Bar))
        flags.append(trace.showlegend is True)
    return flags


@pytest.mark.parametrize(
    "modes,expected",
    [(("lines", "markers"), 2), (("lines", "lines"), 1), (("markers", "markers"), 1)],
)
def test_shared_scatter_mode_is_part_of_native_glyph_identity(
    modes: tuple[str, str], expected: int
) -> None:
    # [test->req~ring5.figure.series-styling~1]
    native = _plotly_shared(
        [
            go.Scatter(
                name="ipc", x=[0.0, 1.0], y=values, mode=mode, marker_color="red", line_color="red"
            )
            for mode, values in zip(modes, ([3.0, 5.0], [7.0, 9.0]), strict=True)
        ]
    )
    assert sum(_shown(native)) == expected
    for trace, mode, values in zip(
        native.figure.data, modes, ([3.0, 5.0], [7.0, 9.0]), strict=True
    ):
        assert isinstance(trace, go.Scatter)
        assert trace.mode == mode and trace.name == "IPC"
        np.testing.assert_array_equal(np.asarray(trace.y), values)


@pytest.mark.parametrize(
    "field,values",
    [
        ("fgcolor", ("blue", "green")),
        ("bgcolor", ("blue", "green")),
        ("fgopacity", (0.25, 0.75)),
        ("fillmode", ("replace", "overlay")),
    ],
)
@pytest.mark.parametrize("equal", [False, True])
def test_shared_bar_pattern_uses_native_foreground_background_and_composition(
    field: str, values: tuple[Any, Any], equal: bool
) -> None:
    chosen = (values[0], values[0]) if equal else values
    native = _plotly_shared(
        [
            go.Bar(
                name="ipc",
                x=[0.0, 1.0],
                y=data,
                marker={"color": "red", "pattern": {"shape": "/", field: value}},
            )
            for value, data in zip(chosen, ([3.0, 5.0], [7.0, 9.0]), strict=True)
        ]
    )
    assert sum(_shown(native)) == (1 if equal else 2)
    for trace, value, data in zip(
        native.figure.data, chosen, ([3.0, 5.0], [7.0, 9.0]), strict=True
    ):
        assert isinstance(trace, go.Bar)
        assert trace.marker.pattern[field] == value
        np.testing.assert_array_equal(np.asarray(trace.y), data)


@pytest.mark.parametrize("mode", [None, "text", "lines+text"])
def test_unsupported_or_data_dependent_scatter_glyph_mode_stays_separate(mode: str | None) -> None:
    native = _plotly_shared(
        [
            go.Scatter(name="ipc", x=[0.0, 1.0], y=[3.0, 5.0], mode=mode, marker_color="red")
            for _ in range(2)
        ]
    )
    assert all(_shown(native))


class _OpaqueStyle:
    def __hash__(self) -> int:
        raise AssertionError("An unsupported style object must not be hashed.")

    def __deepcopy__(self, memo: dict[int, object]) -> object:
        raise AssertionError("An unsupported style object must not be copied.")


class _UnvisitedArray(np.ndarray):
    def __iter__(self) -> Any:
        raise AssertionError("A style array must not be traversed.")

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> "_UnvisitedArray":
        raise AssertionError("A style array must not be copied.")


@pytest.mark.parametrize("unknown", ["nested_property", "object", "array"])
def test_native_style_guard_does_not_serialize_hash_or_walk_unsupported_state(unknown: str) -> None:
    trace = go.Bar(marker={"color": "red", "pattern": {"shape": "/"}})
    # A future/foreign native property is inspected only as a key. A known
    # property with an unsupported object/array also remains conservatively unknown.
    if unknown == "nested_property":
        trace.marker.pattern._props["future_glyph"] = _OpaqueStyle()
    elif unknown == "object":
        trace.marker.pattern._props["size"] = _OpaqueStyle()
    else:
        trace.marker.pattern._props["size"] = np.asarray([3.0, 5.0]).view(_UnvisitedArray)
    assert plotly_swatch(trace) is None
    np.testing.assert_array_equal(np.asarray(trace.marker.color), "red")


def _panel(
    axis: Axes, handle: Artist, family: Literal["scatter", "line"]
) -> MatplotlibRenderResult:
    return MatplotlibRenderResult(
        axis,
        bindings=(
            MatplotlibTraceBinding(
                0,
                "ipc",
                axis,
                "primary",
                "",
                True,
                family,
                (handle,),
                (handle,),
                handle,
                appearance=MatplotlibAppearance.unmanaged(),
            ),
        ),
    )


@pytest.mark.parametrize(
    "style,expected",
    [
        ("different_width", 2),
        ("equal", 1),
        ("vector_width", 2),
        ("different_dash", 2),
        ("equal_dash", 1),
        ("array_alpha", 2),
    ],
)
def test_native_collection_legend_stroke_preserves_scalar_distinctions_and_unknown_vectors(
    style: str, expected: int
) -> None:
    # [test->req~ring5.figure.series-styling~1]
    figure, axes = plt.subplots(1, 2)
    widths: tuple[float | list[float], float | list[float]] = (
        ([1.0, 5.0], [1.0, 5.0])
        if style == "vector_width"
        else ((1.0, 5.0) if style == "different_width" else (1.0, 1.0))
    )
    dashes = (
        (":", "--")
        if style == "different_dash"
        else ((":", ":") if style == "equal_dash" else ("solid", "solid"))
    )
    panels = tuple(
        _panel(
            axis,
            axis.scatter(
                [0.0, 1.0],
                data,
                color="red",
                edgecolors="black",
                s=20,
                linewidths=width,
                linestyle=dash,
            ),
            "scatter",
        )
        for axis, data, width, dash in zip(
            axes, ([3.0, 5.0], [7.0, 9.0]), widths, dashes, strict=True
        )
    )
    native = MatplotlibFigureResult(figure, panels, shared_legend=True)
    try:
        if style == "array_alpha":
            for panel in panels:
                # The native method accepts NumPy arrays; its external stub
                # restricts the annotation to Sequence despite this valid case.
                panel.primary_axes.collections[0].set_alpha(cast(Sequence[float], np.array([0.5])))
        FigureSpecToMatplotlib.apply(resolve_config(FigureConfig(legends=[LegendConfig()])), native)
        legend = native.native_outputs.legend
        assert legend is not None
        assert len(legend.texts) == expected
        for glyph, width in zip(legend.legend_handles, widths[:expected], strict=True):
            assert isinstance(glyph, PathCollection)
            np.testing.assert_array_equal(np.asarray(glyph.get_linewidth()), np.atleast_1d(width))
        for panel, data in zip(panels, ([3.0, 5.0], [7.0, 9.0]), strict=True):
            np.testing.assert_array_equal(
                np.asarray(panel.primary_axes.collections[0].get_offsets())[:, 1], data
            )
    finally:
        plt.close(figure)


@pytest.mark.parametrize(
    "styles,expected",
    [
        (("left", "full"), 2),
        (("left", "left"), 1),
        (("custom_dash", "custom_dash"), 2),
        (("transformed", "full"), 2),
        (("full", "full"), 1),
    ],
)
def test_native_line_marker_fill_and_unrepresented_custom_dash_state(
    styles: tuple[str, str], expected: int
) -> None:
    figure, axes = plt.subplots(1, 2)
    panels = []
    for axis, style, values in zip(axes, styles, ([3.0, 5.0], [7.0, 9.0]), strict=True):
        handle = axis.plot(
            [0.0, 1.0],
            values,
            color="red",
            marker=(
                MarkerStyle("o", transform=Affine2D().scale(2, 1))
                if style == "transformed"
                else "o"
            ),
            markerfacecolor="red",
            markerfacecoloralt="blue",
            fillstyle="full" if style in ("custom_dash", "transformed") else style,
            linestyle=(0, (1, 3)) if style == "custom_dash" else "solid",
        )[0]
        panels.append(_panel(axis, handle, "line"))
    native = MatplotlibFigureResult(figure, tuple(panels), shared_legend=True)
    try:
        FigureSpecToMatplotlib.apply(resolve_config(FigureConfig(legends=[LegendConfig()])), native)
        legend = native.native_outputs.legend
        assert legend is not None and len(legend.texts) == expected
        for panel, values in zip(panels, ([3.0, 5.0], [7.0, 9.0]), strict=True):
            np.testing.assert_array_equal(
                np.asarray(panel.primary_axes.lines[0].get_ydata()), values
            )
    finally:
        plt.close(figure)


def test_same_native_handler_class_with_custom_update_is_unknown_without_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    figure, axis = plt.subplots()
    line = axis.plot([0.0, 1.0], [3.0, 5.0], color="red")[0]
    source = _panel(axis, line, "line").bindings[0]
    calls = []

    def custom_update(legend_handle: Artist, original_handle: Artist) -> None:
        calls.append((legend_handle, original_handle))

    try:
        assert matplotlib_swatch(source) is not None
        monkeypatch.setitem(
            Legend.get_default_handler_map(), Line2D, HandlerLine2D(update_func=custom_update)
        )
        assert matplotlib_swatch(source) is None
        assert calls == []
        np.testing.assert_array_equal(np.asarray(line.get_ydata()), [3.0, 5.0])
    finally:
        plt.close(figure)


def test_per_handle_stock_handler_overrides_keep_distinct_actual_marker_glyphs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    figure, axes = plt.subplots(1, 2)
    panels = tuple(
        _panel(axis, axis.plot([0.0, 1.0], values, color="red", marker="o")[0], "line")
        for axis, values in zip(axes, ([3.0, 5.0], [7.0, 9.0]), strict=True)
    )
    native = MatplotlibFigureResult(figure, panels, shared_legend=True)
    try:
        assert all(matplotlib_swatch(panel.bindings[0]) is not None for panel in panels)
        for panel, count in zip(panels, (1, 3), strict=True):
            handle = panel.bindings[0].legend_handle
            assert isinstance(handle, Line2D)
            # Native maps accept both artist instances and classes; the stub
            # restricts this public native extension to class keys.
            handlers = cast(MutableMapping[object, HandlerBase], Legend.get_default_handler_map())
            monkeypatch.setitem(handlers, handle, HandlerLine2D(numpoints=count))
            assert matplotlib_swatch(panel.bindings[0]) is None
        FigureSpecToMatplotlib.apply(resolve_config(FigureConfig(legends=[LegendConfig()])), native)
        legend = native.native_outputs.legend
        assert legend is not None and len(legend.texts) == 2
        first, second = legend.legend_handles
        assert isinstance(first, Line2D) and isinstance(second, Line2D)
        assert first.get_markevery() == [1]
        assert second.get_markevery() is None
        for panel, values in zip(panels, ([3.0, 5.0], [7.0, 9.0]), strict=True):
            np.testing.assert_array_equal(
                np.asarray(panel.primary_axes.lines[0].get_ydata()), values
            )
    finally:
        plt.close(figure)


@pytest.mark.parametrize(
    "style,expected", [("equal", 1), ("different_hatch_color", 2), ("list_dash", 2)]
)
def test_stock_bar_handler_preserves_hatch_color_and_unknown_list_dash(
    style: str, expected: int
) -> None:
    figure, axes = plt.subplots(1, 2)
    panels = []
    for index, (axis, values) in enumerate(zip(axes, ([3.0, 5.0], [7.0, 9.0]), strict=True)):
        bars = axis.bar([0.0, 1.0], values, color="red", edgecolor="black", hatch="/")
        for patch in bars.patches:
            patch.set_hatchcolor("green" if style == "different_hatch_color" and index else "blue")
            if style == "list_dash":
                patch.set_linestyle((0, [1, 2]))
        panels.append(
            MatplotlibRenderResult(
                axis,
                bindings=(
                    MatplotlibTraceBinding(
                        0,
                        "ipc",
                        axis,
                        "primary",
                        "",
                        True,
                        "bar",
                        (bars,),
                        (bars,),
                        bars,
                        appearance=MatplotlibAppearance.unmanaged(),
                    ),
                ),
            )
        )
    native = MatplotlibFigureResult(figure, tuple(panels), shared_legend=True)
    try:
        FigureSpecToMatplotlib.apply(resolve_config(FigureConfig(legends=[LegendConfig()])), native)
        legend = native.native_outputs.legend
        assert legend is not None and len(legend.texts) == expected
        for panel, values in zip(panels, ([3.0, 5.0], [7.0, 9.0]), strict=True):
            handle = panel.bindings[0].legend_handle
            assert isinstance(handle, BarContainer)
            np.testing.assert_array_equal([patch.get_height() for patch in handle.patches], values)
    finally:
        plt.close(figure)


@pytest.mark.parametrize("kind", ["mode", "pattern"])
def test_reapply_recomputes_shared_entries_after_native_glyph_changes(kind: str) -> None:
    if kind == "mode":
        native = _plotly_shared(
            [
                go.Scatter(
                    name="ipc",
                    x=[0.0, 1.0],
                    y=values,
                    mode="lines",
                    line_color="red",
                    marker_color="red",
                )
                for values in ([3.0, 5.0], [7.0, 9.0])
            ]
        )
    else:
        native = _plotly_shared(
            [
                go.Bar(
                    name="ipc",
                    x=[0.0, 1.0],
                    y=values,
                    marker={"color": "red", "pattern": {"shape": "/", "fgcolor": "blue"}},
                )
                for values in ([3.0, 5.0], [7.0, 9.0])
            ]
        )
    assert _shown(native) == [True, False]
    second = native.figure.data[1]
    if isinstance(second, go.Scatter):
        second.mode = "markers"
    else:
        assert isinstance(second, go.Bar)
        second.marker.pattern.fgcolor = "green"
    FigureSpecToPlotly.apply(resolve_config(FigureConfig(legend_labels={"ipc": "IPC"})), native)
    assert _shown(native) == [True, True]
    if isinstance(second, go.Scatter):
        second.mode = "lines"
    else:
        second.marker.pattern.fgcolor = "blue"
    FigureSpecToPlotly.apply(resolve_config(FigureConfig(legend_labels={"ipc": "IPC"})), native)
    assert _shown(native) == [True, False]
    for trace, values in zip(native.figure.data, ([3.0, 5.0], [7.0, 9.0]), strict=True):
        assert isinstance(trace, (go.Scatter, go.Bar))
        np.testing.assert_array_equal(np.asarray(trace.y), values)
