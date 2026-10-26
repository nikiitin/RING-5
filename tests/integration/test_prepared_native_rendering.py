"""Actual native consumers share one preparation and preserve typed render effects."""

from copy import deepcopy
from contextlib import nullcontext
from dataclasses import replace
from typing import Any, Literal, cast
from unittest.mock import patch

import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
import pandas as pd
import pytest

import ring5
from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig, ScatterTraceConfig
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.figure_preparation import prepare_figure
from src.web.rendering.matplotlib_figure_builder import (
    build_matplotlib_figure_from_prepared,
    draw_matplotlib_axes,
)
from src.web.rendering.report_builder import _single_plot_figure, _single_plot_plotly


def _data() -> ring5.Table:
    return ring5.Table(
        pd.DataFrame(
            {"bench": ["a", "b"], "group": ["G", "G"], "left": [2.0, 5.0], "right": [4.0, 10.0]}
        )
    )


def _config(separate: bool) -> dict[str, Any]:
    return {
        "x": "bench",
        "group": "group",
        "y_columns": ["left"],
        "dual_axis": True,
        "y_columns_right": ["right"],
        "right_axis_type": "dots",
        "unified_legend": not separate,
        "ylabel": "Rate",
        "ylabel_right": "Rate",
        "yaxis_title_font_size": 17,
        "yaxis2_title_font_size": -1,
        "yaxis_title_standoff": -1,
        "yaxis2_title_standoff": -1,
        "yaxis2_tickfont_size": 11,
        "yaxis2_tickfont_color": "#123456",
        "range_y2": [0, 12],
        "yaxis2_dtick": 2,
        "legend_font_size": 14.5,
        "legend2_font_size": 12.5,
        "legend2_x": 0.8,
        "legend2_y": 0.3,
        "legend2_anchor_x": "center",
        "legend2_anchor_y": "bottom",
        "legend2_bgcolor": "#eeddcc",
        "legend2_bgalpha": 0.7,
        "legend2_border_color": "#123456",
        "legend2_border_width": 3,
        "legend2_ncols": 2,
        "legend2_handletextpad": 0.35,
    }


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("route", ["session", "report", "dashboard"])
@pytest.mark.parametrize("separate", [False, True])
def test_native_routes_prepare_once_and_preserve_axis_roles(
    engine: Literal["plotly", "matplotlib"],
    route: str,
    separate: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    # [test->req~ring5.figure.dual-axis-controls~1]
    with ring5.Session() as session:
        plot = session.create_plot("grouped_stacked_bar", data=_data(), config=_config(separate))
        other = None
        if route == "dashboard":
            other = session.create_plot(
                "bar",
                data=ring5.Table(pd.DataFrame({"x": ["context"], "v": [7.0]})),
                config={"x": "x", "y": "v"},
                name="Context",
            )
        before = deepcopy(plot.config)
        assert plot.processed_data is not None
        frame_before = plot.processed_data.copy(deep=True)
        callback = plot.create_traces
        calls = []

        def traces(data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
            result = callback(data, config)
            calls.append(result)
            return replace(
                result,
                annotations=[
                    *result.annotations,
                    AnnotationConfig(text="Rate", x=0.4, y=0.6, xref="paper", yref="paper"),
                ],
            )

        monkeypatch.setattr(plot, "create_traces", traces)
        with (
            patch.object(
                ConfigSpecBuilder, "from_config", wraps=ConfigSpecBuilder.from_config
            ) as builder,
            patch(
                "src.web.rendering.figure_preparation.resolve_config", wraps=resolve_config
            ) as resolver,
        ):
            with (
                patch(
                    "src.web.rendering.plotly_figure_builder.traces_to_plotly",
                    side_effect=AssertionError("Plotly on MPL"),
                )
                if engine == "matplotlib"
                else nullcontext()
            ):
                if route == "session":
                    native = cast(Any, session.render(plot, engine=engine))
                elif route == "report":
                    native = (
                        _single_plot_plotly(plot)
                        if engine == "plotly"
                        else _single_plot_figure(plot)
                    )
                else:
                    assert other is not None
                    dashboard = session.create_dashboard([plot, other], shared_legend=False)
                    native = cast(Any, session.render_dashboard(dashboard, engine=engine))
        try:
            assert len(calls) == 1
            assert builder.call_count == resolver.call_count == (2 if route == "dashboard" else 1)
            assert [list(trace.y) for trace in calls[0].traces] == [[2.0, 5.0], [4.0, 10.0]]
            assert plot.processed_data is not None
            pd.testing.assert_frame_equal(plot.processed_data, frame_before)
            if route != "session":
                assert plot.config == before
            if engine == "plotly":
                assert [list(trace.y) for trace in native.data[:2]] == [[2.0, 5.0], [4.0, 10.0]]
                titles = [
                    ann
                    for ann in native.layout.annotations
                    if ann.name in ("ring5-y-title", "ring5-y2-title")
                ]
                assert [(ann.text, ann.textangle, ann.xshift, ann.font.size) for ann in titles] == [
                    ("Rate", -90, -40, 17),
                    ("Rate", 90, 40, 17),
                ]
                assert sum(ann.text == "Rate" for ann in native.layout.annotations) == 3
                assert all(
                    trace.hovertemplate == calls[0].traces[0].custom_data["hovertemplate"]
                    for trace in native.data[:2]
                )
                assert native.data[1].legend == ("legend2" if separate else "legend")
                assert native.layout.yaxis2.tickfont.color == "#123456"
                if route != "dashboard" and separate:
                    assert native.layout.legend2.font.size == 12.5
                    assert (native.layout.legend2.xanchor, native.layout.legend2.yanchor) == (
                        "center",
                        "bottom",
                    )
            else:
                primary = native.axes[0]
                twin = primary._ring5_twin
                assert [bar.get_height() for bar in primary.patches] == [2.0, 5.0]
                assert list(twin.lines[0].get_ydata()) == [4.0, 10.0]
                assert primary.get_ylabel() == twin.get_ylabel() == "Rate"
                assert (primary.yaxis.label.get_rotation(), twin.yaxis.label.get_rotation()) == (
                    90,
                    270,
                )
                assert sum(text.get_text() == "Rate" for text in primary.texts) == 1
                assert twin.get_ylim() == (0, 12)
                assert all(text.get_color() == "#123456" for text in twin.get_yticklabels())
                assert [text.get_text() for text in primary.get_legend().get_texts()] == (
                    ["left"] if separate else ["left", "right"]
                )
                if separate:
                    legend = twin.get_legend()
                    assert [text.get_text() for text in legend.get_texts()] == ["right"]
                    assert legend.get_texts()[0].get_fontsize() == 12.5
                    assert legend.get_frame().get_linewidth() == 3
                    assert legend.get_frame().get_alpha() == 0.7
                else:
                    assert twin.get_legend() is None
        finally:
            if engine == "matplotlib":
                plt.close(native)


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("font_size", [12.5, -1])
@pytest.mark.parametrize("separate", [False, True])
def test_public_fractional_numbered_and_right_legend_fonts_survive_typed_roundtrip(
    engine: Literal["plotly", "matplotlib"],
    font_size: float,
    separate: bool,
) -> None:
    # [test->req~ring5.figure.numbered-xaxis~1]
    with ring5.Session() as session:
        config = ring5.FigureSpec(
            x="bench",
            group="group",
            y_columns=["left"],
            legend=ring5.LegendOpts(font_size=14.5),
            number_legend=ring5.LegendOpts(font_size=font_size, anchor=("center", "top")),
            dual_axis=ring5.DualAxisOpts(
                columns=["right"],
                unified_legend=not separate,
                legend=ring5.LegendOpts(font_size=11.5, anchor=("right", "bottom")),
            ),
            extra={"numbered_xaxis_modes": ["Number legend"]},
        )
        plot = session.create_plot("grouped_stacked_bar", data=_data(), config=config)
        assert plot.processed_data is not None
        prepared = prepare_figure(
            plot.processed_data, plot.config, plot.plot_type, plot.create_traces
        )
        restored = FigureConfig.from_dict(prepared.spec.to_dict())
        expected = 14.5 if font_size == -1 else font_size
        assert restored.annotations[-1].font_size == expected
        assert restored.typography.font_size_legend == 14.5
        native = cast(Any, session.render(plot, engine=engine))
        try:
            if engine == "plotly":
                numbered = next(
                    ann for ann in native.layout.annotations if ann.text.startswith("1.")
                )
                assert numbered.font.size == expected
                assert (numbered.xanchor, numbered.yanchor) == ("center", "top")
                if separate:
                    assert native.layout.legend2.font.size == 11.5
            else:
                numbered = next(
                    text for text in native.axes[0].texts if text.get_text().startswith("1.")
                )
                assert numbered.get_fontsize() == expected
                if separate:
                    assert (
                        native.axes[0]._ring5_twin.get_legend().get_texts()[0].get_fontsize()
                        == 11.5
                    )
        finally:
            if engine == "matplotlib":
                plt.close(native)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_native_artifact_keeps_user_annotations_equal_to_dual_titles(
    engine: Literal["plotly", "matplotlib"], monkeypatch: pytest.MonkeyPatch
) -> None:
    with ring5.Session() as session:
        plot = session.create_plot("grouped_stacked_bar", data=_data(), config=_config(False))
        callback = plot.create_traces
        monkeypatch.setattr(
            plot,
            "create_traces",
            lambda data, config: replace(
                callback(data, config),
                annotations=[
                    AnnotationConfig(text="Rate", x=0.4, y=0.6, xref="paper", yref="paper")
                ],
            ),
        )
        native = session.render(plot, engine=engine)
        assert plot.render_artifact.figure is native
        figure = cast(Any, native)
        assert plot.render_artifact.engine == engine
        assert plot.render_artifact.trace_result is not None
        assert [list(trace.y) for trace in plot.render_artifact.trace_result.traces] == [
            [2.0, 5.0],
            [4.0, 10.0],
        ]
        try:
            if engine == "plotly":
                assert sum(ann.text == "Rate" for ann in figure.layout.annotations) == 3
            else:
                assert sum(text.get_text() == "Rate" for text in figure.axes[0].texts) == 1
                assert (
                    figure.axes[0].get_ylabel() == figure.axes[0]._ring5_twin.get_ylabel() == "Rate"
                )
        finally:
            if engine == "matplotlib":
                plt.close(figure)


@pytest.mark.parametrize("mixed", [False, True])
def test_matplotlib_facets_never_discard_a_supported_mixed_trace(mixed: bool) -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(name="one", col_labels=["a"], row_labels=["r"], z=[[1.0]]),
            HeatmapTraceConfig(name="two", col_labels=["a"], row_labels=["r"], z=[[2.0]]),
        ]
    )
    if mixed:
        result = replace(
            result, traces=[*result.traces, ScatterTraceConfig(name="retained", x=[0.0], y=[9.0])]
        )
    prepared = prepare_figure(pd.DataFrame(), {"xlabel": "Category"}, "custom", lambda *_: result)
    original = prepared.spec.to_dict()
    figure = build_matplotlib_figure_from_prepared(prepared).figure
    try:
        assert prepared.spec.to_dict() == original
        if mixed:
            points = [
                collection
                for collection in figure.axes[0].collections
                if isinstance(collection, PathCollection)
            ]
            assert len(points) == 1
            assert cast(Any, points[0].get_offsets()).tolist() == [[0.0, 9.0]]
        else:
            assert [axis.get_title() for axis in figure.axes[:2]] == ["one", "two"]
            assert figure.axes[0].get_xlabel() == ""
            assert figure.axes[1].get_xlabel() == "Category"
    finally:
        plt.close(figure)


def test_secondary_legend_style_cannot_claim_an_unrelated_dashboard_axes() -> None:
    from src.core.models.visualization.trace_config import BarTraceConfig

    prepared = prepare_figure(
        pd.DataFrame(),
        {"legend2_font_size": 12.5},
        "custom",
        lambda *_: TraceBuildResult(traces=[BarTraceConfig(name="owned", x=["a"], y=[2.0])]),
    )
    figure, axes = plt.subplots(1, 2)
    axes[1].plot([0, 1], [7, 8], label="other panel")
    try:
        draw_matplotlib_axes(prepared, axes[0], apply_margins=False)
        assert [text.get_text() for text in axes[0].get_legend().get_texts()] == ["owned"]
        assert axes[1].get_legend() is None
        assert list(axes[1].lines[0].get_ydata()) == [7, 8]
    finally:
        plt.close(figure)


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("shared", [False, True])
def test_dashboard_owns_each_child_legend_role_and_preserves_numbered_annotation_style(
    engine: Literal["plotly", "matplotlib"],
    shared: bool,
) -> None:
    # [test->req~ring5.figure.panel-composition~1]
    # [test->req~ring5.figure.legends~1]
    with ring5.Session() as session:
        plots = []
        originals = []
        for index in range(2):
            config = {
                **_config(True),
                "legend_font_size": 14.5 + index * 4,
                "legend2_font_size": 12.5 + index * 4,
                "legend3_font_size": 20.5 + index * 4,
                "numbered_xaxis_modes": ["Number legend"],
                "legend_x": 0.1 + index * 0.1,
                "legend_y": 0.9,
                "legend_anchor_x": "left",
                "legend_anchor_y": "top",
                "legend2_x": 0.8 - index * 0.1,
                "legend2_y": 0.3,
                "legend2_anchor_x": "center" if index == 0 else "right",
                "legend2_anchor_y": "bottom",
                "legend_bgcolor": "rgba(238,221,204,0.2)",
                "legend_bgalpha": 0.4,
                "legend3_bgcolor": "rgba(238,221,204,0.2)",
                "legend3_bgalpha": 0.6,
            }
            plot = session.create_plot("grouped_stacked_bar", data=_data(), config=config)
            plots.append(plot)
            originals.append(deepcopy(plot.config))
        dashboard = session.create_dashboard(plots, columns=2, shared_legend=shared)
        native = cast(Any, session.render_dashboard(dashboard, engine=engine))
        try:
            assert [plot.config for plot in plots] == originals
            if engine == "plotly":
                assert [trace.legend for trace in native.data] == (
                    ["legend"] * 4 if shared else ["legend", "legend2", "legend3", "legend4"]
                )
                numbered = [ann for ann in native.layout.annotations if ann.text.startswith("1.")]
                assert [ann.font.size for ann in numbered] == [20.5, 24.5]
                if shared:
                    assert native.layout.legend.font.size == 14.5
                    assert native.layout.legend.bgcolor == "rgba(238,221,204,0.4)"
                else:
                    for index in range(2):
                        panel = native.get_subplot(1, index + 1)
                        x0, x1 = panel.xaxis.domain
                        y0, y1 = panel.yaxis.domain
                        left = getattr(native.layout, "legend" if index == 0 else "legend3")
                        right = getattr(native.layout, "legend2" if index == 0 else "legend4")
                        assert left.font.size == 14.5 + index * 4
                        assert right.font.size == 12.5 + index * 4
                        assert left.x == pytest.approx(x0 + (0.1 + index * 0.1) * (x1 - x0))
                        assert right.x == pytest.approx(x0 + (0.8 - index * 0.1) * (x1 - x0))
                        assert right.y == pytest.approx(y0 + 0.3 * (y1 - y0))
                        assert right.xanchor == ("center" if index == 0 else "right")
                        assert right.yanchor == "bottom"
            elif shared:
                assert [text.get_text() for text in native.legends[0].get_texts()] == [
                    "left",
                    "right",
                ]
                assert all(text.get_fontsize() == 14.5 for text in native.legends[0].get_texts())
                assert native.legends[0].get_frame().get_alpha() == 0.4
            else:
                for index, primary in enumerate(native.axes[:2]):
                    twin = primary._ring5_twin
                    assert primary.get_legend().get_texts()[0].get_fontsize() == 14.5 + index * 4
                    assert twin.get_legend().get_texts()[0].get_fontsize() == 12.5 + index * 4
                    numbered_text = next(
                        text for text in primary.texts if text.get_text().startswith("1.")
                    )
                    assert numbered_text.get_fontsize() == 20.5 + index * 4
                    assert numbered_text.get_bbox_patch().get_facecolor()[-1] == 0.6
                    bounds = (
                        twin.get_legend()
                        .get_bbox_to_anchor()
                        .transformed(twin.transAxes.inverted())
                        .bounds
                    )
                    assert bounds[:2] == pytest.approx((0.8 - index * 0.1, 0.3))
        finally:
            if engine == "matplotlib":
                plt.close(native)


@pytest.mark.public_api
def test_invalid_native_heatmap_range_keeps_previous_artifacts_and_no_pyplot_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with ring5.Session() as session:
        plot = session.create_plot("grouped_stacked_bar", data=_data(), config=_config(False))
        session.render(plot, engine="plotly")
        prior = (
            plot.render_artifact.figure,
            plot.render_artifact.trace_result,
            deepcopy(plot.config),
        )
        before = set(plt.get_fignums())
        monkeypatch.setattr(
            plot,
            "create_traces",
            lambda *_: TraceBuildResult(
                traces=[
                    HeatmapTraceConfig(
                        name="invalid",
                        col_labels=["a"],
                        row_labels=["r"],
                        z=cast(Any, [["invalid"]]),
                    ),
                    HeatmapTraceConfig(
                        name="measured", col_labels=["a"], row_labels=["r"], z=[[2.0]]
                    ),
                ]
            ),
        )
        with pytest.raises(ring5.RenderError):
            session.render(plot, engine="matplotlib")
        assert plot.render_artifact.figure is prior[0]
        assert plot.render_artifact.trace_result is prior[1]
        assert plot.config == prior[2]
        assert set(plt.get_fignums()) == before


@pytest.mark.public_api
def test_native_plotly_appends_user_shapes_once_without_replacing_neutral_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    from src.core.models.visualization.trace_build_result import (
        RuleLine,
        SeparatorLine,
        ShadedRegion,
    )

    with ring5.Session() as session:
        shape = {"type": "circle", "x0": 0.1, "x1": 0.3, "y0": 1.0, "y1": 2.0}
        plot = session.create_plot(
            "grouped_stacked_bar", data=_data(), config={**_config(False), "shapes": [shape]}
        )
        callback = plot.create_traces
        original = deepcopy(plot.config)
        monkeypatch.setattr(
            plot,
            "create_traces",
            lambda data, config: replace(
                callback(data, config),
                separator_lines=[SeparatorLine(x=0.5)],
                shaded_regions=[ShadedRegion(x0=-0.4, x1=0.4)],
                rule_lines=[RuleLine(x0=-0.4, x1=0.4, y=-0.1)],
            ),
        )
        figure = cast(Any, session.render(plot, engine="plotly"))
        assert len(figure.layout.shapes) == 4
        assert [item.type for item in figure.layout.shapes] == ["rect", "line", "line", "circle"]
        assert figure.layout.shapes[-1].to_plotly_json() == shape
        assert original["shapes"] == plot.config["shapes"] == [shape]


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("role", ["primary", "secondary", "numbered"])
@pytest.mark.parametrize(
    ("color", "alpha"),
    [
        (color, alpha)
        for color in ("#eeddcc", "red", "rgba(238,221,204,0.2)")
        for alpha in (0.0, 0.7, 1.0)
    ]
    + [("rgba(238,221,204,0.2)", None)],
)
def test_native_legend_opacity_preserves_embedded_alpha_and_explicit_override(
    engine: Literal["plotly", "matplotlib"],
    role: str,
    alpha: float | None,
    color: str,
) -> None:
    # [test->req~ring5.figure.legends~1]
    expected_alpha = 0.2 if alpha is None else alpha
    expected_rgb = (1.0, 0.0, 0.0) if color == "red" else (238 / 255, 221 / 255, 204 / 255)
    defaults = deepcopy(
        (
            plt.rcParams["font.family"],
            plt.rcParams["legend.fontsize"],
            plt.rcParams["axes.facecolor"],
        )
    )
    with ring5.Session() as session:
        config = _config(role == "secondary")
        prefix = "legend_" if role == "primary" else "legend2_"
        config[f"{prefix}bgcolor"] = color
        config.pop(f"{prefix}bgalpha", None)
        if alpha is not None:
            config[f"{prefix}bgalpha"] = alpha
        if role == "numbered":
            config["numbered_xaxis_modes"] = ["Number legend"]
        plot = session.create_plot("grouped_stacked_bar", data=_data(), config=config)
        native = cast(Any, session.render(plot, engine=engine))
        try:
            if engine == "plotly":
                if role == "numbered":
                    rendered = next(
                        ann.bgcolor
                        for ann in native.layout.annotations
                        if ann.text.startswith("1.")
                    )
                else:
                    rendered = getattr(
                        native.layout, "legend2" if role == "secondary" else "legend"
                    ).bgcolor
                assert rendered.startswith("rgba(")
                channels = [float(value) for value in rendered[5:-1].split(",")]
                actual = (*[value / 255 for value in channels[:3]], channels[3])
            else:
                primary = native.axes[0]
                if role == "numbered":
                    box = next(text for text in primary.texts if text.get_text().startswith("1."))
                    actual = box.get_bbox_patch().get_facecolor()
                else:
                    target = primary._ring5_twin if role == "secondary" else primary
                    actual = target.get_legend().get_frame().get_facecolor()
            assert actual == pytest.approx((*expected_rgb, expected_alpha))
        finally:
            if engine == "matplotlib":
                plt.close(native)
    assert (
        plt.rcParams["font.family"],
        plt.rcParams["legend.fontsize"],
        plt.rcParams["axes.facecolor"],
    ) == defaults


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("show_ticks", [False, True])
def test_public_heatmap_facets_use_bottom_only_explicit_tick_visibility(
    engine: Literal["plotly", "matplotlib"],
    show_ticks: bool,
) -> None:
    # [test->req~ring5.figure.heatmap-controls~1]
    with ring5.Session() as session:
        plot = session.create_plot(
            "heatmap",
            data=ring5.Table(
                pd.DataFrame(
                    {
                        "category": ["a", "b", "a", "b"],
                        "facet": ["one", "one", "two", "two"],
                        "measure": [1.0, 2.0, 3.0, 4.0],
                    }
                )
            ),
            config={
                "x": "category",
                "metric_columns": ["measure"],
                "facet_col": "facet",
                "xlabel": "Category",
                "width": 800,
                "height": 600,
                "show_x_tick_labels": show_ticks,
            },
        )
        native = cast(Any, session.render(plot, engine=engine))
        assert plot.render_artifact.trace_result is not None
        names = [trace.name for trace in plot.render_artifact.trace_result.traces]
        try:
            if engine == "plotly":
                assert (native.layout.width, native.layout.height) == (800, 600)
                assert native.layout.xaxis.showticklabels is False
                assert native.layout.xaxis2.showticklabels is show_ticks
                assert native.layout.xaxis.title.text is None
                assert native.layout.xaxis2.title.text == "Category"
                assert names == [ann.text for ann in native.layout.annotations[:2]]
                for index, trace in enumerate(native.data):
                    assert list(trace.x) == ["a", "b"]
                    assert list(trace.y) == ["measure"]
                    assert [list(row) for row in trace.z] == [[1 + index * 2, 2 + index * 2]]
            else:
                assert native.get_size_inches() * native.dpi == pytest.approx([800, 600])
                for index, axis in enumerate(native.axes[:2]):
                    assert axis.get_title() == names[index]
                    assert axis.get_xlabel() == ("" if index == 0 else "Category")
                    assert axis.get_xticks().tolist() == [0.5, 1.5]
                    assert [tick.get_text() for tick in axis.get_yticklabels()] == ["measure"]
                    assert [tick.get_text() for tick in axis.get_xticklabels()] == (
                        ["a", "b"] if index == 1 and show_ticks else []
                    )
                    assert axis.collections[0].get_array().tolist() == [
                        [1 + index * 2, 2 + index * 2]
                    ]
        finally:
            if engine == "matplotlib":
                plt.close(native)
