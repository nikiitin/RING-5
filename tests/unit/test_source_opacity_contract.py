"""Native source opacity, intrinsic color ownership and explicit capability boundaries."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from io import BytesIO
from typing import Any, Literal, TypedDict, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.artist import Artist
from matplotlib.collections import Collection, LineCollection, QuadMesh
from matplotlib.colorbar import Colorbar
from matplotlib.colors import LinearSegmentedColormap, to_rgba
from matplotlib.container import BarContainer, Container
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
import plotly.graph_objects as go
from matplotlib.text import Text

from src.core.common.opacity import require_opacity
from src.core.common.plot_payload import validate_plot_config_keys, validate_plot_config_values
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    BoxTraceConfig,
    HeatmapTraceConfig,
    LineTraceConfig,
    ParallelCoordinatesTraceConfig,
    ParallelDimensionConfig,
    RadarTraceConfig,
    SankeyTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
    ViolinTraceConfig,
    WaterfallTraceConfig,
)
from src.web.rendering._appearance import MatplotlibAppearance, seed_matplotlib_appearance
from src.web.rendering._matplotlib_copy import copy_matplotlib_figure
from src.web.rendering._render_result import (
    MatplotlibFigureResult,
    MatplotlibRenderResult,
    MatplotlibTraceBinding,
    PlotlyRenderResult,
)
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.figure_preparation import PreparedFigure, prepare_figure
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
from src.web.rendering.plotly_connector import FigureSpecToPlotly
from src.web.rendering.plotly_figure_builder import build_plotly_figure

COLOR = "rgba(10,20,30,0.4)"
EDGE = "rgba(200,100,50,0.2)"
FAMILIES = (
    "bar",
    "line",
    "scatter",
    "box",
    "violin",
    "radar",
    "waterfall",
    "sankey",
    "heatmap",
    "parallel_coordinates",
)


class _TraceIdentity(TypedDict):
    name: str
    opacity: float


def _trace(family: str) -> TraceConfig:
    common: _TraceIdentity = {"name": "data", "opacity": 0.5}
    if family == "bar":
        return BarTraceConfig(
            **common,
            x=[1, 2],
            y=[3, 5],
            color=COLOR,
            border_width=1,
            border_color=EDGE,
            error_y=[0.2, 0.3],
        )
    if family == "line":
        return LineTraceConfig(
            **common, x=[1, 2], y=[3, 5], color=COLOR, error_y=[0.2, 0.3], fill="tozeroy"
        )
    if family == "scatter":
        return ScatterTraceConfig(
            **common,
            x=[1, 2],
            y=[3, 5],
            color=COLOR,
            marker_line_width=1,
            marker_line_color=EDGE,
            size_values=[4, 9],
            error_y=[0.2, 0.3],
        )
    if family == "box":
        return BoxTraceConfig(
            **common,
            color=COLOR,
            values=[1, 2, 3, 4, 5],
            q1=2,
            median=3,
            q3=4,
            lower_whisker=1,
            upper_whisker=5,
            mean=3,
            show_mean=True,
            point_mode="all",
            category="A",
        )
    if family == "violin":
        return ViolinTraceConfig(
            **common,
            color=COLOR,
            values=[1, 2, 3, 4, 5],
            density_coordinates=[1, 2, 3, 4, 5],
            density=[0.2, 0.6, 1, 0.6, 0.2],
            q1=2,
            median=3,
            q3=4,
            mean=3,
            show_mean=True,
            point_mode="all",
            category="A",
        )
    if family == "radar":
        return RadarTraceConfig(
            **common,
            color=COLOR,
            categories=["A", "B", "C"],
            values=[2, 3, 4],
            radial_min=0,
            radial_max=5,
        )
    if family == "waterfall":
        return WaterfallTraceConfig(
            **common,
            categories=["A", "B", "Total"],
            values=[3, -2, 1],
            measures=["relative", "relative", "total"],
            kinds=["relative", "relative", "total"],
            starts=[0, 3, 0],
            ends=[3, 1, 1],
            increasing_color=COLOR,
            decreasing_color="rgba(30,20,10,0.6)",
            total_color="rgba(5,6,7,0.8)",
            connector_color=EDGE,
            show_values=True,
            value_labels=["3", "-2", "1"],
        )
    if family == "sankey":
        return SankeyTraceConfig(
            **common,
            node_labels=["A", "B"],
            source_indices=[0],
            target_indices=[1],
            values=[3],
            node_colors=[COLOR, "rgba(30,20,10,0.6)"],
            link_colors=["rgba(40,50,60,0.6)"],
            node_x=[0, 1],
            node_y=[0.5, 0.5],
            node_line_color=EDGE,
            link_opacity=0.35,
            show_node_labels=True,
        )
    if family == "heatmap":
        return HeatmapTraceConfig(
            **common,
            col_labels=["A", "B"],
            row_labels=["R"],
            z=[[3, 5]],
            colorscale=[[0, COLOR], [1, "rgba(30,20,10,0.6)"]],
            show_values=True,
            text=[["3", "5"]],
        )
    if family == "parallel_coordinates":
        return ParallelCoordinatesTraceConfig(
            name="data",
            opacity=1,
            line_color="#0a141e",
            show_colorbar=False,
            unselected_opacity=0.08,
            dimensions=[
                ParallelDimensionConfig(
                    column="a", label="A", values=[1, 2], range=(0, 5), constraintrange=(0, 1.5)
                ),
                ParallelDimensionConfig(column="b", label="B", values=[3, 4], range=(0, 5)),
            ],
        )
    raise AssertionError(family)


def _style(opacity: float | None = None, *, color: str = "") -> SeriesStyleConfig:
    # Other typed style defaults retain their existing meaning; isolate opacity here.
    return SeriesStyleConfig(opacity=opacity, color=color, marker_size=0, line_width=0)


@contextmanager
def _native(
    trace: TraceConfig, *, labels: bool = False
) -> Iterator[tuple[PreparedFigure, MatplotlibFigureResult, PlotlyRenderResult]]:
    prepared = prepare_figure(
        pd.DataFrame(), {}, "custom", lambda *_: TraceBuildResult(traces=[trace])
    )
    if labels:
        prepared = replace(
            prepared, spec=replace(prepared.spec, data_labels=DataLabelConfig(enabled=True))
        )
    mpl = build_matplotlib_figure_from_prepared(prepared)
    try:
        plotly = build_plotly_figure(prepared)
        yield prepared, mpl, plotly
    finally:
        plt.close(mpl.figure)


def _artists(owned: tuple[Artist | Container, ...]) -> tuple[Artist, ...]:
    output = []
    seen = set()

    def visit(item: Artist | Container) -> None:
        if id(item) in seen:
            return
        seen.add(id(item))
        if isinstance(item, Container):
            for child in item.get_children():
                visit(child)
        else:
            output.append(item)

    for item in owned:
        visit(item)
    return tuple(output)


def _geometry(artists: tuple[Artist, ...]) -> tuple[Any, ...]:
    values: list[object] = []
    for artist in artists:
        if isinstance(artist, Line2D):
            values.append(
                (np.asarray(artist.get_xdata()).tobytes(), np.asarray(artist.get_ydata()).tobytes())
            )
        elif isinstance(artist, Collection):
            array = artist.get_array()
            values.append(
                (
                    np.asarray(artist.get_offsets()).tobytes(),
                    None if array is None else np.asarray(array).tobytes(),
                    tuple(np.asarray(path.vertices).tobytes() for path in artist.get_paths()),
                    tuple(artist.get_sizes()) if hasattr(artist, "get_sizes") else (),
                )
            )
        elif isinstance(artist, Patch):
            values.append(
                (
                    np.asarray(artist.get_path().vertices).tobytes(),
                    np.asarray(artist.get_patch_transform().get_matrix()).tobytes(),
                )
            )
        elif isinstance(artist, Text):
            values.append((artist.get_text(), artist.get_position()))
    return tuple(values)


@pytest.mark.parametrize("value", [0, 0.25, 1, np.int64(0), np.float32(0.5), np.longdouble(1)])
def test_opacity_admits_only_supported_real_scalars(value: Any) -> None:
    assert require_opacity(value) == float(value)
    assert SeriesStyleConfig(opacity=value).opacity == float(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        "0.5",
        float("nan"),
        float("inf"),
        -0.1,
        1.1,
        np.bool_(True),
        np.clongdouble(0.5),
        np.longdouble(-1e-300) / np.longdouble(1e300),
        np.longdouble(1) + np.finfo(np.longdouble).eps,
    ],
)
def test_opacity_rejects_invalid_values_without_coercion(value: Any) -> None:
    with pytest.raises(ValueError, match="finite real number"):
        require_opacity(value)


def test_opacity_does_not_call_arbitrary_float_hooks() -> None:
    class Convertible:
        calls = 0

        def __float__(self) -> float:
            self.calls += 1
            return 0.5

    value = Convertible()
    with pytest.raises(ValueError):
        require_opacity(value)
    assert value.calls == 0


def test_typed_inheritance_and_editable_presence_have_one_contract() -> None:
    assert SeriesStyleConfig().opacity is None
    assert SeriesStyleConfig.from_dict(SeriesStyleConfig().to_dict()).opacity is None
    for value in (0, 1):
        style = SeriesStyleConfig.from_dict({"opacity": value})
        assert style.to_dict()["opacity"] == value
        config = {"series_styles": {"data": {"opacity": value}}}
        validate_plot_config_values(config)
        assert ConfigSpecBuilder.from_config(config).trace_overrides["data"].opacity == value
    assert ConfigSpecBuilder.from_config({"line_width": 3}).series_styles[0].opacity is None
    with pytest.raises(ValueError):
        validate_plot_config_values({"series_styles": {"data": {"opacity": None}}})
    validate_plot_config_keys({"series_styles": {"data": {"opacity": "{{opacity}}"}}})
    with pytest.raises(ValueError):
        validate_plot_config_values({"series_styles": {"data": {"opacity": "{{opacity}}"}}})


@pytest.mark.parametrize("family", FAMILIES)
def test_all_families_preserve_science_and_reapply_explicit_zero(family: str) -> None:
    with _native(_trace(family)) as (prepared, mpl, plotly):
        binding = mpl.panels[0].bindings[0]
        artists = _artists(binding.owned_data)
        before = _geometry(artists)
        for value in (0, 0, 0.25, 1):
            spec = replace(prepared.spec, trace_overrides={"data": _style(value)})
            if family == "parallel_coordinates" and value != 1:
                with pytest.raises(ValueError, match="selected source opacity 1"):
                    FigureSpecToMatplotlib.apply(spec, mpl)
                with pytest.raises(ValueError, match="selected source opacity 1"):
                    FigureSpecToPlotly.apply(spec, plotly)
            else:
                FigureSpecToMatplotlib.apply(spec, mpl)
                FigureSpecToPlotly.apply(spec, plotly)
                for artist in artists:
                    if isinstance(artist, Text):
                        assert to_rgba(artist.get_color())[3] == pytest.approx(value)
                if family not in ("sankey", "parallel_coordinates"):
                    assert plotly.figure.data[0]["opacity"] == value
                elif family == "sankey":
                    sankey = plotly.figure.data[0]
                    assert isinstance(sankey, go.Sankey)
                    assert float(sankey.node.color[0].rsplit(",", 1)[1][:-1]) == pytest.approx(
                        0.4 * value
                    )
                    assert sankey.link.hovercolor == sankey.link.color
            assert _geometry(artists) == before
        mpl.figure.canvas.draw()


def test_intrinsic_companion_channels_and_family_factors() -> None:
    expected = {
        "bar": 0.2,
        "line": 0.2,
        "scatter": 0.2,
        "box": 0.2,
        "violin": 0.2,
        "radar": 0.2,
        "waterfall": 0.2,
    }
    for family, alpha in expected.items():
        with _native(_trace(family)) as (_, mpl, _):
            binding = mpl.panels[0].bindings[0]
            handle = binding.legend_handle
            if family in ("bar", "waterfall"):
                assert isinstance(handle, BarContainer)
                primary = handle.patches[0].get_facecolor()
            elif isinstance(handle, Line2D):
                primary = to_rgba(handle.get_color())
            else:
                assert isinstance(handle, (Patch, Collection))
                primary = np.asarray(handle.get_facecolor()).reshape((-1, 4))[0]
            assert np.asarray(primary)[3] == pytest.approx(alpha)
            if family == "bar":
                assert isinstance(handle, BarContainer)
                assert np.asarray(handle.patches[0].get_edgecolor())[3] == pytest.approx(0.1)
            if family == "radar":
                fill = next(item for item in binding.owned_data if isinstance(item, Patch))
                assert np.asarray(fill.get_facecolor())[3] == pytest.approx(0.09)
            if family == "violin":
                inner = next(item for item in binding.owned_data if isinstance(item, Patch))
                assert inner.get_facecolor() == pytest.approx((1, 1, 1, 0.4))
                assert np.asarray(inner.get_edgecolor())[3] == pytest.approx(0.16)
            if family == "waterfall":
                bars = [item for item in binding.owned_data if isinstance(item, BarContainer)]
                assert [
                    np.asarray(bar.patches[0].get_facecolor())[3] for bar in bars
                ] == pytest.approx([0.2, 0.3, 0.4])


def test_width_only_config_preserves_source_opacity_and_named_wins() -> None:
    with _native(_trace("line")) as (prepared, mpl, plotly):
        spec = ConfigSpecBuilder.from_config({"line_width": 4})
        FigureSpecToMatplotlib.apply(spec, mpl)
        FigureSpecToPlotly.apply(spec, plotly)
        line = mpl.panels[0].bindings[0].legend_handle
        assert isinstance(line, Line2D)
        assert to_rgba(line.get_color())[3] == pytest.approx(0.2)
        assert plotly.figure.data[0]["opacity"] == 0.5
        spec = replace(
            prepared.spec, series_styles=[_style(0.75)], trace_overrides={"data": _style(0)}
        )
        FigureSpecToMatplotlib.apply(spec, mpl)
        FigureSpecToPlotly.apply(spec, plotly)
        assert to_rgba(line.get_color())[3] == 0
        assert plotly.figure.data[0]["opacity"] == 0


def test_manual_native_color_survives_unrelated_apply_and_requires_known_base() -> None:
    with _native(_trace("bar")) as (prepared, mpl, _):
        bars = mpl.panels[0].bindings[0].legend_handle
        assert isinstance(bars, BarContainer)
        patch = bars.patches[0]
        patch.set_facecolor("purple")
        FigureSpecToMatplotlib.apply(replace(prepared.spec, title="Unrelated"), mpl)
        assert patch.get_facecolor() == to_rgba("purple")
        with pytest.raises(ValueError, match="new explicit color/context"):
            FigureSpecToMatplotlib.apply(
                replace(
                    prepared.spec, title="Must not change", trace_overrides={"data": _style(0.25)}
                ),
                mpl,
            )
        assert mpl.panels[0].primary_axes.get_title() == "Unrelated"
        assert patch.get_facecolor() == to_rgba("purple")
        FigureSpecToMatplotlib.apply(
            replace(prepared.spec, trace_overrides={"data": _style(0.25, color="orange")}), mpl
        )
        assert patch.get_facecolor() == pytest.approx((*to_rgba("orange")[:3], 0.25))


def test_independent_manual_edge_is_not_adopted_by_new_main_color() -> None:
    with _native(_trace("bar")) as (prepared, mpl, _):
        handle = mpl.panels[0].bindings[0].legend_handle
        assert isinstance(handle, BarContainer)
        patch = handle.patches[0]
        before = patch.get_facecolor()
        patch.set_edgecolor("green")
        with pytest.raises(ValueError, match="new explicit color/context"):
            FigureSpecToMatplotlib.apply(
                replace(prepared.spec, trace_overrides={"data": _style(0.25, color="orange")}), mpl
            )
        assert patch.get_facecolor() == before
        assert patch.get_edgecolor() == to_rgba("green")


def test_ordinary_plotly_manual_color_has_independent_opacity() -> None:
    with _native(_trace("line")) as (prepared, _, plotly):
        native = plotly.figure.data[0]
        assert isinstance(native, go.Scatter)
        native.line.color = "purple"
        FigureSpecToPlotly.apply(
            replace(prepared.spec, trace_overrides={"data": _style(0.25)}), plotly
        )
        assert native.line.color == "purple"
        assert native.opacity == 0.25


def test_sankey_manual_hover_color_cannot_escape_explicit_opacity_preflight() -> None:
    with _native(_trace("sankey")) as (prepared, _, plotly):
        native = plotly.figure.data[0]
        assert isinstance(native, go.Sankey)
        native.link.hovercolor = ["red"]
        FigureSpecToPlotly.apply(replace(prepared.spec, title="Unrelated"), plotly)
        before = plotly.figure.to_plotly_json()
        with pytest.raises(ValueError, match="new explicit context"):
            FigureSpecToPlotly.apply(
                replace(
                    prepared.spec, title="Must not change", trace_overrides={"data": _style(0)}
                ),
                plotly,
            )
        assert plotly.figure.to_plotly_json() == before


def test_unmanaged_appearance_preserves_native_alpha_arrays_and_blocks_updates() -> None:
    figure, axes = plt.subplots()
    try:
        points = axes.scatter([1, 2], [3, 5], color="blue")
        points.set_alpha(cast(Sequence[float], np.array([0.2, 0.7])))
        binding = MatplotlibTraceBinding(
            0,
            "data",
            axes,
            "primary",
            "",
            True,
            "scatter",
            (points,),
            (points,),
            points,
            appearance=MatplotlibAppearance.unmanaged(),
        )
        rendered = MatplotlibFigureResult(
            figure, (MatplotlibRenderResult(axes, bindings=(binding,)),)
        )
        FigureSpecToMatplotlib.apply(FigureConfig(title="Allowed"), rendered)
        np.testing.assert_array_equal(points.get_alpha(), [0.2, 0.7])
        before = np.array(points.get_facecolor(), copy=True)
        with pytest.raises(ValueError, match="explicitly unmanaged"):
            FigureSpecToMatplotlib.apply(
                FigureConfig(title="Blocked", trace_overrides={"data": _style(0)}), rendered
            )
        assert axes.get_title() == "Allowed"
        np.testing.assert_array_equal(points.get_facecolor(), before)
    finally:
        plt.close(figure)


def test_zero_unselected_opacity_keeps_every_parallel_row() -> None:
    trace = _trace("parallel_coordinates")
    assert isinstance(trace, ParallelCoordinatesTraceConfig)
    trace.unselected_opacity = 0
    with _native(trace) as (_, mpl, plotly):
        lines = mpl.panels[0].bindings[0].owned_data
        assert len(lines) == 2
        assert all(isinstance(line, Line2D) for line in lines)
        assert sorted(
            to_rgba(line.get_color())[3] for line in lines if isinstance(line, Line2D)
        ) == [0, 1]
        parcoords = plotly.figure.data[0]
        assert isinstance(parcoords, go.Parcoords)
        assert parcoords.unselected.line.opacity == 0


@pytest.mark.parametrize("change", ["source", "color", "scale"])
def test_parallel_selected_transparency_rejects_before_any_figure(change: str) -> None:
    trace = _trace("parallel_coordinates")
    assert isinstance(trace, ParallelCoordinatesTraceConfig)
    if change == "source":
        trace.opacity = 0.5
    elif change == "color":
        trace.line_color = COLOR
    else:
        trace.line_color_values = [1, 2]
        trace.colorscale = [[0, COLOR], [1, "blue"]]
    before = plt.get_fignums()
    with pytest.raises(ValueError, match="Parallel coordinates require"):
        prepare_figure(pd.DataFrame(), {}, "custom", lambda *_: TraceBuildResult(traces=[trace]))
    assert plt.get_fignums() == before


def test_source_labels_reuse_ownership_and_copy_without_touching_live_outputs() -> None:
    for family in ("bar", "heatmap"):
        with _native(_trace(family), labels=family == "bar") as (prepared, mpl, plotly):
            binding = mpl.panels[0].bindings[0]
            labels = binding.appearance.labels
            for value in (0, 0, 1, 0.25):
                spec = replace(prepared.spec, trace_overrides={"data": _style(value)})
                FigureSpecToMatplotlib.apply(spec, mpl)
                FigureSpecToPlotly.apply(spec, plotly)
                assert binding.appearance.labels == labels
                for label in labels:
                    assert to_rgba(label.get_color())[3] == pytest.approx(value)
            artists = _artists(binding.owned_data)
            before = _geometry(artists)
            text_before = tuple(
                (text.get_text(), text.get_color()) for text in mpl.figure.findobj(Text)
            )
            copied = copy_matplotlib_figure(mpl.figure)
            copied.canvas.draw()
            copied.savefig(BytesIO(), format="png")
            assert _geometry(artists) == before
            assert (
                tuple((text.get_text(), text.get_color()) for text in mpl.figure.findobj(Text))
                == text_before
            )
            if family == "heatmap":
                image = binding.owned_data[0]
                assert isinstance(image, QuadMesh)
                output = mpl.native_outputs.colorbars[0]
                assert image.get_cmap()(0.0)[3] == pytest.approx(0.1)
                assert output.colorbar.solids is not None
                assert output.colorbar.solids.get_cmap()(0.0)[3] == pytest.approx(0.4)
                image.set_clim(1, 6)
                assert output.colorbar.solids.get_cmap()(0.0)[3] == pytest.approx(0.4)
                copied_images = [
                    item
                    for axis in copied.axes
                    for item in axis.collections
                    if getattr(item, "colorbar", None) is not None
                ]
                assert len(copied_images) == 1
                copied_image = copied_images[0]
                assert copied_image.colorbar is not None
                assert copied_image.colorbar is not output.colorbar
                assert copied_image.colorbar.mappable is copied_image
                assert copied_image.callbacks.callbacks.get("changed", {}) == {}
                copied_image.set_clim(0, 10)
                assert image.get_clim() == (1, 6)


def test_intrinsic_bad_under_over_mapping_and_visible_manual_mutator_boundary() -> None:
    figure, axes = plt.subplots()
    try:
        intrinsic = LinearSegmentedColormap.from_list(
            "owned", [(0, (1, 0, 0, 0.4)), (1, (0, 0, 1, 0.6))]
        ).with_extremes(bad=(0, 1, 0, 0.8), under=(1, 1, 0, 0.3), over=(0, 1, 1, 0.7))
        image = axes.pcolormesh([[0.25, 0.75]], cmap=intrinsic)
        seed_matplotlib_appearance((image,), opacity=0.5)
        mapped = image.get_cmap()
        samples = np.ma.array([-1.0, 0.0, 1.0, 2.0, 0.0], mask=[False, False, False, False, True])
        expected = np.array(intrinsic(samples), copy=True)
        expected[:, 3] *= 0.5
        np.testing.assert_array_equal(mapped(samples), expected)
        copied = mapped.copy()
        assert copied is not mapped and copied == mapped
        assert copied != intrinsic
        np.testing.assert_array_equal(copied(samples), expected)
        np.testing.assert_array_equal(mapped.with_extremes()(samples), expected)
        reversed_expected = np.array(intrinsic.reversed()(samples), copy=True)
        reversed_expected[:, 3] *= 0.5
        np.testing.assert_array_equal(mapped.reversed()(samples), reversed_expected)
        resampled_expected = np.array(intrinsic.resampled(17)(samples), copy=True)
        resampled_expected[:, 3] *= 0.5
        np.testing.assert_array_equal(mapped.resampled(17)(samples), resampled_expected)
        for mutate in (
            lambda: mapped.set_bad("purple"),
            lambda: mapped.set_under("purple"),
            lambda: mapped.set_over("purple"),
            lambda: mapped.with_extremes(bad="purple"),
            lambda: mapped.set_extremes(under="purple"),
            lambda: mapped.with_alpha(0.5),
        ):
            with pytest.raises(ValueError, match="new intrinsic context"):
                mutate()
            np.testing.assert_array_equal(mapped(samples), expected)
    finally:
        plt.close(figure)


@pytest.mark.parametrize("change", ["extension", "foreign", "manual_map"])
def test_affected_colorbar_capability_failure_precedes_native_changes(change: str) -> None:
    with _native(_trace("heatmap")) as (prepared, mpl, _):
        image = mpl.panels[0].bindings[0].owned_data[0]
        assert isinstance(image, QuadMesh)
        output = mpl.native_outputs.colorbars[0]
        if change == "extension":
            output.colorbar.extend = "both"
        elif change == "foreign":
            mpl.figure.colorbar(image, ax=mpl.panels[0].primary_axes)
        else:
            image.set_cmap("plasma")
            FigureSpecToMatplotlib.apply(replace(prepared.spec, title="Unrelated"), mpl)
        before = (
            mpl.panels[0].primary_axes.get_title(),
            image.get_cmap(),
            image.get_clim(),
            tuple(mpl.figure.axes),
            tuple(image.callbacks.callbacks.get("changed", {})),
        )
        with pytest.raises(ValueError, match="neither|foreign colorbar|new explicit color/context"):
            FigureSpecToMatplotlib.apply(
                replace(
                    prepared.spec, title="Must not change", trace_overrides={"data": _style(0)}
                ),
                mpl,
            )
        after = (
            mpl.panels[0].primary_axes.get_title(),
            image.get_cmap(),
            image.get_clim(),
            tuple(mpl.figure.axes),
            tuple(image.callbacks.callbacks.get("changed", {})),
        )
        assert after == before


def test_color_only_replacement_preserves_unaffected_manual_companion() -> None:
    with _native(_trace("bar")) as (prepared, mpl, _):
        handle = mpl.panels[0].bindings[0].legend_handle
        assert isinstance(handle, BarContainer)
        patch = handle.patches[0]
        patch.set_edgecolor("green")
        FigureSpecToMatplotlib.apply(
            replace(prepared.spec, trace_overrides={"data": _style(color="orange")}), mpl
        )
        assert patch.get_facecolor() == pytest.approx((*to_rgba("orange")[:3], 0.5))
        assert patch.get_edgecolor() == to_rgba("green")
        with pytest.raises(ValueError, match="new explicit color/context"):
            FigureSpecToMatplotlib.apply(
                replace(prepared.spec, trace_overrides={"data": _style(0)}), mpl
            )
        assert patch.get_edgecolor() == to_rgba("green")


def test_unknown_label_format_change_fails_before_native_updates() -> None:
    with _native(_trace("bar"), labels=True) as (prepared, mpl, _):
        binding = mpl.panels[0].bindings[0]
        original = binding.appearance.labels
        original[0].set_color("purple")
        before = mpl.panels[0].primary_axes.get_title()
        assert prepared.spec.data_labels is not None
        changed = replace(prepared.spec.data_labels, format_string=".1f")
        with pytest.raises(ValueError, match="new explicit color/context"):
            FigureSpecToMatplotlib.apply(
                replace(prepared.spec, title="Blocked", data_labels=changed), mpl
            )
        assert mpl.panels[0].primary_axes.get_title() == before
        assert binding.appearance.labels == original
        assert original[0].get_color() == "purple"
        FigureSpecToMatplotlib.apply(
            replace(
                prepared.spec,
                data_labels=replace(changed, color_mode="custom", custom_color=EDGE),
            ),
            mpl,
        )
        assert all(
            to_rgba(label.get_color())[3] == pytest.approx(0.1)
            for label in binding.appearance.labels
        )


def test_later_panel_unknown_channel_preflight_preserves_earlier_panel() -> None:
    from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer

    figure, axes = plt.subplots(1, 2)
    try:
        panels = tuple(
            MatplotlibTraceRenderer.render(
                [BarTraceConfig(name=name, x=[1], y=[value], color=COLOR)], axis
            )
            for name, value, axis in zip(("left", "right"), (3, 5), axes, strict=True)
        )
        root = MatplotlibFigureResult(figure, panels)
        left = panels[0].bindings[0].legend_handle
        right = panels[1].bindings[0].legend_handle
        assert isinstance(left, BarContainer) and isinstance(right, BarContainer)
        right.patches[0].set_facecolor("purple")
        before = left.patches[0].get_facecolor()
        with pytest.raises(ValueError, match="new explicit color/context"):
            FigureSpecToMatplotlib.apply(
                FigureConfig(
                    title="Blocked", trace_overrides={"left": _style(0), "right": _style(0)}
                ),
                root,
            )
        assert left.patches[0].get_facecolor() == before
        assert all(axis.get_title() == "" for axis in axes)
        assert [
            patch.get_height()
            for panel in panels
            for patch in panel.primary_axes.patches
            if isinstance(patch, Rectangle)
        ] == [3, 5]
    finally:
        plt.close(figure)


def test_later_sankey_hover_preflight_preserves_earlier_plotly_source() -> None:
    from src.web.rendering.trace_to_plotly import traces_to_plotly

    first = LineTraceConfig(name="first", x=[1, 2], y=[3, 5], color=COLOR, opacity=0.5)
    rendered = traces_to_plotly(TraceBuildResult(traces=[first, _trace("sankey")]))
    sankey = rendered.figure.data[1]
    assert isinstance(sankey, go.Sankey)
    sankey.link.hovercolor = ["purple"]
    before = rendered.figure.to_plotly_json()
    with pytest.raises(ValueError, match="new explicit context"):
        FigureSpecToPlotly.apply(
            FigureConfig(title="Blocked", trace_overrides={"first": _style(0), "data": _style(0)}),
            rendered,
        )
    assert rendered.figure.to_plotly_json() == before


def test_hidden_source_ordinals_and_secondary_axes_keep_opacity_precedence() -> None:
    traces = [
        BarTraceConfig(name="hidden", x=["a"], y=[2], visible=False),
        BarTraceConfig(name="left", x=["a"], y=[3], color=COLOR, opacity=0.5),
        LineTraceConfig(name="right", x=["a"], y=[5], color=COLOR, yaxis="y2", opacity=0.5),
    ]
    prepared = prepare_figure(
        pd.DataFrame(), {}, "custom", lambda *_: TraceBuildResult(traces=traces, secondary_y=True)
    )
    mpl = build_matplotlib_figure_from_prepared(prepared)
    try:
        plotly = build_plotly_figure(prepared)
        changed = replace(
            prepared.spec,
            series_styles=[_style(0), _style(0.25), _style(0.75)],
            trace_overrides={"right": _style(0)},
            legend_labels={"left": "Display", "right": "Display"},
        )
        FigureSpecToMatplotlib.apply(changed, mpl)
        FigureSpecToPlotly.apply(changed, plotly)
        assert [binding.source_ordinal for binding in mpl.panels[0].bindings] == [0, 1, 2]
        hidden, left, right = mpl.panels[0].bindings
        assert hidden.owned_data == ()
        assert isinstance(left.legend_handle, BarContainer)
        assert isinstance(right.legend_handle, Line2D)
        assert left.legend_handle.patches[0].get_facecolor() == pytest.approx(
            (10 / 255, 20 / 255, 30 / 255, 0.1)
        )
        assert to_rgba(right.legend_handle.get_color())[3] == 0
        assert right.axes is mpl.panels[0].secondary_axes
        assert [trace["opacity"] for trace in plotly.figure.data] == [0, 0.25, 0]
        assert list(plotly.figure.data[1]["y"]) == [3]
        assert list(plotly.figure.data[2]["y"]) == [5]
    finally:
        plt.close(mpl.figure)


def test_explicit_sankey_hover_baseline_composes_independently() -> None:
    from src.web.rendering._appearance import seed_sankey_appearance
    from src.web.rendering.trace_to_plotly import traces_to_plotly

    trace = _trace("sankey")
    assert isinstance(trace, SankeyTraceConfig)
    rendered = traces_to_plotly(TraceBuildResult(traces=[trace]))
    native = rendered.figure.data[0]
    assert isinstance(native, go.Sankey)
    output = seed_sankey_appearance(
        native,
        opacity=trace.opacity,
        node_colors=trace.node_colors,
        node_line=trace.node_line_color,
        link_colors=trace.link_colors,
        link_factor=trace.link_opacity,
        hover_colors=["rgba(1,2,3,0.8)"],
    )
    binding = replace(rendered.panel_bindings[0][0], appearance=output)
    rendered = replace(rendered, panel_bindings=((binding,),))
    for value in (0, 1, 0.25):
        FigureSpecToPlotly.apply(FigureConfig(trace_overrides={"data": _style(value)}), rendered)
        assert len(native.link.hovercolor) == 1
        assert native.link.hovercolor[0].startswith("rgba(1,2,3,")
        assert float(native.link.hovercolor[0].rsplit(",", 1)[1][:-1]) == pytest.approx(
            0.8 * 0.35 * value
        )
        assert native.link.color != native.link.hovercolor
        assert list(native.link.value) == [3]


def test_opaque_positioned_parallel_scale_is_preserved() -> None:
    trace = _trace("parallel_coordinates")
    assert isinstance(trace, ParallelCoordinatesTraceConfig)
    trace.line_color_values = [0, 1]
    trace.colorscale = [[0, "red"], [1, "blue"]]
    trace.color_min, trace.color_max = 0, 1
    with _native(trace) as (_, mpl, plotly):
        native = plotly.figure.data[0]
        assert isinstance(native, go.Parcoords)
        assert native.line.colorscale == ((0, "red"), (1, "blue"))
        paths = mpl.panels[0].bindings[0].owned_data
        assert all(isinstance(path, Line2D) for path in paths)
        rgba = [to_rgba(path.get_color()) for path in paths if isinstance(path, Line2D)]
        np.testing.assert_allclose(rgba, [(0, 0, 1, 0.08), (1, 0, 0, 1)])


@pytest.mark.parametrize("family", ["bar", "line", "scatter"])
def test_errorbar_and_area_colors_compose_intrinsic_alpha(family: str) -> None:
    with _native(_trace(family)) as (prepared, mpl, _):
        binding = mpl.panels[0].bindings[0]
        artists = _artists(binding.owned_data)
        errors = [artist for artist in artists if isinstance(artist, LineCollection)]
        assert len(errors) == 1
        expected_intrinsic = 1.0 if family == "bar" else 0.4
        assert np.asarray(errors[0].get_edgecolor())[0, 3] == pytest.approx(
            expected_intrinsic * 0.5
        )
        for value in (0, 1):
            FigureSpecToMatplotlib.apply(
                replace(prepared.spec, trace_overrides={"data": _style(value)}), mpl
            )
            assert np.asarray(errors[0].get_edgecolor())[0, 3] == pytest.approx(
                expected_intrinsic * value
            )
            assert all(artist.get_alpha() is None for artist in artists)
            if family == "line":
                fills = [
                    artist
                    for artist in artists
                    if isinstance(artist, Collection) and not isinstance(artist, LineCollection)
                ]
                assert len(fills) == 1
                assert np.asarray(fills[0].get_facecolor())[0, 3] == pytest.approx(0.4 * value)


def test_data_mapped_collection_requires_deliberate_unknown_capability() -> None:
    figure, axes = plt.subplots()
    try:
        points = axes.scatter([1, 2], [3, 5], c=[1, 2], cmap="viridis")
        before = np.array(points.get_facecolor(), copy=True)
        with pytest.raises(ValueError, match="explicit unmanaged appearance"):
            seed_matplotlib_appearance((points,), opacity=0.5)
        np.testing.assert_array_equal(points.get_facecolor(), before)
        np.testing.assert_array_equal(points.get_array(), [1, 2])
        assert points.get_alpha() is None
    finally:
        plt.close(figure)


@pytest.mark.parametrize("change", ["mapping", "alpha_array"])
def test_new_manual_scalar_mapping_is_preserved_then_rejected_when_affected(change: str) -> None:
    with _native(_trace("scatter")) as (prepared, mpl, _):
        points = mpl.panels[0].bindings[0].legend_handle
        assert isinstance(points, Collection)
        if change == "mapping":
            points.set_array(np.array([1, 2]))
        else:
            points.set_alpha(cast(Sequence[float], np.array([0.2, 0.7])))
        FigureSpecToMatplotlib.apply(replace(prepared.spec, title="Unrelated"), mpl)
        mpl.figure.canvas.draw()
        before = np.array(points.get_facecolor(), copy=True)
        for requested in (_style(0), _style(color="orange")):
            with pytest.raises(ValueError, match="new explicit color/context"):
                FigureSpecToMatplotlib.apply(
                    replace(prepared.spec, title="Blocked", trace_overrides={"data": requested}),
                    mpl,
                )
            assert mpl.panels[0].primary_axes.get_title() == "Unrelated"
            np.testing.assert_array_equal(points.get_facecolor(), before)
        if change == "mapping":
            np.testing.assert_array_equal(points.get_array(), [1, 2])
        else:
            np.testing.assert_array_equal(points.get_alpha(), [0.2, 0.7])


def _mappable_state(image: QuadMesh) -> tuple[object, ...]:
    mapping = image.get_cmap()
    return (
        id(mapping),
        np.asarray(mapping([0.0, 0.5, 1.0])).tobytes(),
        np.asarray(mapping.get_bad()).tobytes(),
        np.asarray(mapping.get_under()).tobytes(),
        np.asarray(mapping.get_over()).tobytes(),
        image.get_clim(),
        np.asarray(image.get_array()).tobytes(),
        np.asarray(image.get_coordinates()).tobytes(),
        tuple(
            (signal, tuple(entries.items()))
            for signal, entries in image.callbacks.callbacks.items()
        ),
    )


def _colorbar_state(colorbar: Colorbar) -> tuple[object, ...]:
    image = colorbar.mappable
    assert isinstance(image, QuadMesh)
    return (
        _mappable_state(image),
        colorbar.ax.get_title(),
        colorbar.extend,
        colorbar.ax.get_position().bounds,
        colorbar.ax.get_position(original=True).bounds,
        tuple(
            (text.get_text(), text.get_color(), tuple(text.get_fontfamily()))
            for text in colorbar.ax.findobj(Text)
        ),
        id(colorbar.solids.get_cmap()) if colorbar.solids is not None else None,
    )


@contextmanager
def _heatmap_without_managed_colorbar(
    extension: Literal["both", "min", "max", "neither"], *, foreign: bool
) -> Iterator[tuple[MatplotlibFigureResult, QuadMesh, Colorbar | None]]:
    figure = plt.figure()
    try:
        axes = figure.add_subplot(121 if foreign else 111)
        mapping = LinearSegmentedColormap.from_list("declared", [(1, 0, 0, 0.4), (0, 0, 1, 0.6)])
        # The native public field accepts extend strings; the current stub declares bool only.
        setattr(mapping, "colorbar_extend", extension)
        image = axes.pcolormesh([[1.0, 2.0]], cmap=mapping)
        appearance = seed_matplotlib_appearance((image,), opacity=0.5)
        binding = MatplotlibTraceBinding(
            0, "data", axes, "primary", "", True, "heatmap", (image,), appearance=appearance
        )
        panel = MatplotlibRenderResult(axes, bindings=(binding,), heatmap_image=image)
        native = MatplotlibFigureResult(figure, (panel,))
        axes.set_title("Original")
        foreign_output = None
        if foreign:
            other = figure.add_subplot(122)
            foreign_image = other.pcolormesh([[7.0, 9.0]], cmap="plasma")
            foreign_output = figure.colorbar(foreign_image, ax=other)
            foreign_output.ax.set_title("Independent")
        yield native, image, foreign_output
    finally:
        plt.close(figure)


@pytest.mark.parametrize("extension", ["both", "min", "max"])
@pytest.mark.parametrize("foreign", [False, True])
def test_new_unsupported_colorbar_rejects_before_any_native_change(
    extension: Literal["both", "min", "max"], foreign: bool
) -> None:
    with _heatmap_without_managed_colorbar(extension, foreign=foreign) as (native, image, other):
        appearance = native.panels[0].bindings[0].appearance
        original_snapshot = appearance.snapshot
        original_axes = tuple(native.figure.axes)
        original_geometry = tuple(
            (
                axis.get_position().bounds,
                axis.get_position(original=True).bounds,
                axis.get_subplotspec(),
            )
            for axis in original_axes
        )
        original_size = tuple(native.figure.get_size_inches())
        original_mapping = _mappable_state(image)
        foreign_before = _colorbar_state(other) if other is not None else None
        assert native.native_outputs.colorbars == ()
        with pytest.raises(ValueError, match="colorbar extend='neither'"):
            FigureSpecToMatplotlib.apply(
                FigureConfig(title="Blocked", trace_overrides={"data": _style(0.25)}), native
            )
        assert native.panels[0].primary_axes.get_title() == "Original"
        assert tuple(native.figure.axes) == original_axes
        assert tuple(native.figure.get_size_inches()) == original_size
        assert (
            tuple(
                (
                    axis.get_position().bounds,
                    axis.get_position(original=True).bounds,
                    axis.get_subplotspec(),
                )
                for axis in original_axes
            )
            == original_geometry
        )
        assert _mappable_state(image) == original_mapping
        assert appearance.snapshot is original_snapshot
        assert appearance.snapshot.opacity == 0.5
        assert native.native_outputs.colorbars == ()
        if other is not None:
            assert _colorbar_state(other) == foreign_before


@pytest.mark.parametrize("foreign", [False, True])
def test_new_legal_colorbar_reuses_output_and_preserves_foreign_mapping(foreign: bool) -> None:
    with _heatmap_without_managed_colorbar("neither", foreign=foreign) as (native, image, other):
        foreign_before = _colorbar_state(other) if other is not None else None
        original_data = np.asarray(image.get_array()).tobytes()
        original_coordinates = np.asarray(image.get_coordinates()).tobytes()
        # Isolate opacity: an empty family preserves unrelated native font choices.
        spec = FigureConfig(title="Allowed", font_family="", trace_overrides={"data": _style(0.25)})
        FigureSpecToMatplotlib.apply(spec, native, apply_margins=False)
        outputs = native.native_outputs.colorbars
        assert len(outputs) == 1
        original_geometry = tuple(
            axis.get_position(original=True).bounds for axis in native.figure.axes
        )
        callbacks = tuple(image.callbacks.callbacks["changed"].items())
        for opacity in (0.25, 0.0, 0.25, 1.0):
            FigureSpecToMatplotlib.apply(
                replace(spec, trace_overrides={"data": _style(opacity)}),
                native,
                apply_margins=False,
            )
            assert native.native_outputs.colorbars == outputs
            assert (
                tuple(axis.get_position(original=True).bounds for axis in native.figure.axes)
                == original_geometry
            )
            assert tuple(image.callbacks.callbacks["changed"].items()) == callbacks
            assert image.get_cmap()(0.0)[3] == pytest.approx(0.4 * opacity)
            assert outputs[0].colorbar.solids is not None
            assert outputs[0].colorbar.solids.get_cmap()(0.0)[3] == pytest.approx(0.4)
            assert native.panels[0].bindings[0].appearance.snapshot.opacity == opacity
            assert np.asarray(image.get_array()).tobytes() == original_data
            assert np.asarray(image.get_coordinates()).tobytes() == original_coordinates
            if other is not None:
                assert _colorbar_state(other) == foreign_before
