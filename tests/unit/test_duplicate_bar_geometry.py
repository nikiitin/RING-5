"""Raw duplicate observations retain their geometry in both bar connectors."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import math
from pathlib import Path
import pickle
import re
from typing import cast
from xml.etree import ElementTree as ET

from matplotlib.container import BarContainer, ErrorbarContainer
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import numpy as np
import plotly.graph_objects as go
import pytest

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.rendering.figure_export import plotly_download_bytes
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer
from src.web.rendering.trace_to_plotly import traces_to_plotly


@dataclass(frozen=True)
class BarGeometryCase:
    """Small measured rows with independently calculated baseline/top pairs."""

    name: str
    mode: str
    traces: tuple[BarTraceConfig, ...]
    geometry: tuple[tuple[tuple[float, float], ...], ...]


CASES = (
    BarGeometryCase(
        "group_raw_seed",
        "group",
        (BarTraceConfig(x=["A"] * 6, y=[0, 0, 0, 1, 1, 1]),),
        (((0, 0), (0, 0), (0, 0), (0, 1), (0, 1), (0, 1)),),
    ),
    BarGeometryCase(
        "group_first_trace",
        "group",
        (BarTraceConfig(x=["A", "A"], y=[2, 3]),),
        (((0, 2), (0, 3)),),
    ),
    BarGeometryCase(
        "group_across_traces",
        "group",
        (BarTraceConfig(x=["A", "A"], y=[2, 3]), BarTraceConfig(x=["A", "A"], y=[5, 7])),
        (((0, 2), (0, 3)), ((0, 5), (0, 7))),
    ),
    BarGeometryCase(
        "stack_first_trace",
        "stack",
        (BarTraceConfig(x=["A", "A"], y=[2, 3]),),
        (((0, 2), (2, 5)),),
    ),
    BarGeometryCase(
        "stack_across_traces",
        "stack",
        (BarTraceConfig(x=["A", "A"], y=[2, 3]), BarTraceConfig(x=["A", "A"], y=[5, 7])),
        (((0, 2), (2, 5)), ((5, 10), (10, 17))),
    ),
    BarGeometryCase(
        "stack_one_signed_chain",
        "stack",
        (BarTraceConfig(x=["A"] * 4, y=[5, -2, 3, -4]),),
        (((0, 5), (5, 3), (3, 6), (6, 2)),),
    ),
    BarGeometryCase(
        "relative_first_trace",
        "relative",
        (BarTraceConfig(x=["A"] * 4, y=[5, -2, 3, -4]),),
        (((0, 5), (0, -2), (5, 8), (-2, -6)),),
    ),
    BarGeometryCase(
        "relative_across_traces_and_zero",
        "relative",
        (
            BarTraceConfig(x=["A"] * 5, y=[2, -3, 4, -5, 0]),
            BarTraceConfig(x=["A"] * 3, y=[-7, 6, 0]),
        ),
        (((0, 2), (0, -3), (2, 6), (-3, -8), (6, 6)), ((-8, -15), (6, 12), (12, 12))),
    ),
    BarGeometryCase(
        "stack_sparse_reordered_categories",
        "stack",
        (
            BarTraceConfig(x=["A", "B", "A", "B"], y=[2, 10, 3, 20]),
            BarTraceConfig(x=["B", "A"], y=[7, 5]),
        ),
        (((0, 2), (0, 10), (2, 5), (10, 30)), ((30, 37), (5, 10))),
    ),
    BarGeometryCase(
        "stack_precomputed_numeric_centers",
        "stack",
        (
            BarTraceConfig(
                x=["A", "A", "B"], x_positions=[0.25, 0.25, 1.25], y=[2, 3, 7], bar_width=0.2
            ),
            BarTraceConfig(x=["A", "B"], x_positions=[0.25, 1.25], y=[5, 11], bar_width=0.2),
        ),
        (((0, 2), (2, 5), (0, 7)), ((5, 10), (7, 18))),
    ),
    BarGeometryCase(
        "stack_independent_y_axes",
        "stack",
        (
            BarTraceConfig(x=["A", "A"], y=[2, 3]),
            BarTraceConfig(x=["A", "A"], y=[100, 200], yaxis="y2"),
            BarTraceConfig(x=["A"], y=[7]),
        ),
        (((0, 2), (2, 5)), ((0, 100), (100, 300)), ((5, 12),)),
    ),
    BarGeometryCase(
        "relative_independent_y_axes",
        "relative",
        (
            BarTraceConfig(x=["A"] * 3, y=[2, -3, 4]),
            BarTraceConfig(x=["A"] * 3, y=[100, -100, 50], yaxis="y2"),
            BarTraceConfig(x=["A", "A"], y=[5, -6]),
        ),
        (((0, 2), (0, -3), (2, 6)), ((0, 100), (0, -100), (100, 150)), ((6, 11), (-3, -9))),
    ),
    BarGeometryCase(
        "overlay_stays_unstacked",
        "overlay",
        (BarTraceConfig(x=["A", "A"], y=[2, 3]), BarTraceConfig(x=["A"], y=[5])),
        (((0, 2), (0, 3)), ((0, 5),)),
    ),
    BarGeometryCase(
        "hidden_trace_does_not_contribute",
        "stack",
        (
            BarTraceConfig(x=["A", "A"], y=[100, 200], visible=False),
            BarTraceConfig(x=["A", "A"], y=[2, 3]),
        ),
        ((), ((0, 2), (2, 5))),
    ),
)


def _owned_traces(case: BarGeometryCase) -> list[BarTraceConfig]:
    """Give every test fresh sources and each SVG trace a distinct paint color."""
    traces = list(copy.deepcopy(case.traces))
    for index, trace in enumerate(traces):
        trace.name = f"source-{index}"
        trace.color = f"rgb({40 + index * 40}, 80, 120)"
    return traces


def _containers(axis: object) -> list[BarContainer]:
    """Narrow actual native containers without accepting nonbar artists."""
    from matplotlib.axes import Axes

    assert isinstance(axis, Axes)
    result = []
    for container in axis.containers:
        if isinstance(container, BarContainer):
            result.append(container)
    return result


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_matplotlib_duplicate_bar_rectangles(case: BarGeometryCase) -> None:
    """Every raw row has the expected baseline, signed height and native rectangle."""
    # [test->req~ring5.render.matplotlib~1]
    traces = _owned_traces(case)
    before = pickle.dumps(traces)
    figure = Figure()
    axis = figure.subplots()
    try:
        rendered = MatplotlibTraceRenderer.render(traces, axis, barmode=case.mode)
        for axis_name, actual_axis in (("y", axis), ("y2", rendered.secondary_axes)):
            expected = [
                (trace, geometry)
                for trace, geometry in zip(traces, case.geometry, strict=True)
                if trace.visible and trace.yaxis == axis_name
            ]
            if not expected:
                assert actual_axis is None or not actual_axis.patches
                continue
            assert actual_axis is not None
            containers = _containers(actual_axis)
            assert len(containers) == len(expected)
            for container, (trace, geometry) in zip(containers, expected, strict=True):
                assert len(container.patches) == len(trace.y) == len(geometry)
                for rectangle, raw_value, (bottom, top) in zip(
                    container.patches, trace.y, geometry, strict=True
                ):
                    assert isinstance(rectangle, Rectangle)
                    assert rectangle.get_y() == pytest.approx(bottom)
                    assert rectangle.get_height() == pytest.approx(raw_value)
                    assert rectangle.get_y() + rectangle.get_height() == pytest.approx(top)
                if trace.x_positions:
                    assert [
                        p.get_x() + p.get_width() / 2 for p in container.patches
                    ] == pytest.approx(trace.x_positions)
                    assert [p.get_width() for p in container.patches] == pytest.approx(
                        [trace.bar_width] * len(trace.y)
                    )
        assert pickle.dumps(traces) == before
    finally:
        figure.clear()


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_BAR_PATH = re.compile(rf"M({_NUMBER}),({_NUMBER})V({_NUMBER})H({_NUMBER})V({_NUMBER})Z")
_SVG = "{http://www.w3.org/2000/svg}"


def _svg_bars_by_color(svg: bytes) -> dict[str, list[tuple[float, float, float, float]]]:
    """Read the actual exported rectangle paths, rejecting unexpected path shapes."""
    painted: dict[str, list[tuple[float, float, float, float]]] = {}
    for element in ET.fromstring(svg).iter(f"{_SVG}g"):
        if set(element.attrib.get("class", "").split()) != {"trace", "bars"}:
            continue
        for point in element.iter(f"{_SVG}g"):
            if point.attrib.get("class") != "point":
                continue
            paths = list(point.findall(f"{_SVG}path"))
            assert len(paths) == 1
            path = paths[0]
            match = _BAR_PATH.fullmatch(path.attrib["d"])
            assert match is not None, path.attrib
            left, bottom, top, right, close = map(float, match.groups())
            assert bottom == close and right > left
            declarations = dict(
                part.strip().split(":", 1)
                for part in path.attrib["style"].split(";")
                if part.strip()
            )
            fill = re.sub(r"\s+", "", declarations["fill"])
            painted.setdefault(fill, []).append((left, bottom, top, right))
    return painted


@pytest.mark.serial
@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_plotly_exported_svg_duplicate_bar_geometry(case: BarGeometryCase, tmp_path: Path) -> None:
    """Native Plotly SVG must paint the same independent per-row geometry."""
    # [test->req~ring5.render.plotly~1]
    # [test->req~ring5.export.plotly-static~1]
    traces = _owned_traces(case)
    before = pickle.dumps(traces)
    result = TraceBuildResult(
        traces=traces, barmode=case.mode, secondary_y=any(t.yaxis == "y2" for t in traces)
    )
    figure = traces_to_plotly(result).figure
    for source, native in zip(traces, figure.data, strict=True):
        assert isinstance(native, go.Bar)
        assert native.y is not None and native.x is not None
        assert list(native.y) == source.y
        assert list(native.x) == (source.x_positions or source.x)
        assert native.offset is None
    # Fixed 600px plot height gives 10px/unit on y and 1px/unit on y2.
    figure.update_layout(
        width=700,
        height=700,
        margin={"l": 50, "r": 50, "t": 50, "b": 50, "autoexpand": False},
        showlegend=False,
        yaxis={"range": [-20, 40], "autorange": False},
    )
    if result.secondary_y:
        figure.update_layout(yaxis2={"range": [-200, 400], "autorange": False})
    svg = plotly_download_bytes(figure, "svg", width=700, height=700, scale=1)
    (tmp_path / f"{case.name}.svg").write_bytes(svg)
    painted = _svg_bars_by_color(svg)
    visible = [trace for trace in traces if trace.visible]
    assert set(painted) == {re.sub(r"\s+", "", trace.color) for trace in visible}
    centers = []
    for trace, geometry in zip(traces, case.geometry, strict=True):
        if not trace.visible:
            assert geometry == ()
            continue
        paths = painted[re.sub(r"\s+", "", trace.color)]
        assert len(paths) == len(trace.y) == len(geometry)
        upper, pixels_per_unit = (40, 10) if trace.yaxis == "y" else (400, 1)
        for (_, bottom_px, top_px, _), (bottom, top) in zip(paths, geometry, strict=True):
            assert upper - bottom_px / pixels_per_unit == pytest.approx(bottom, abs=0.011)
            assert upper - top_px / pixels_per_unit == pytest.approx(top, abs=0.011)
        centers.append([(left + right) / 2 for left, _, _, right in paths])
    if case.name == "group_across_traces":
        assert centers[0][0] == centers[0][1]
        assert centers[1][0] == centers[1][1]
        assert centers[0][0] < centers[1][0]
    assert pickle.dumps(traces) == before


@pytest.mark.parametrize("mode", ["group", "stack", "relative", "overlay"])
def test_group_base_is_only_a_group_construction_property(mode: str) -> None:
    """Stack/relative remain under native stacking rather than explicit-base overlay."""
    trace = BarTraceConfig(x=["A", "A"], y=[2, 3], offset=0.125, bar_width=0.3)
    before = copy.deepcopy(trace)
    native = traces_to_plotly(TraceBuildResult(traces=[trace], barmode=mode)).figure.data[0]
    assert isinstance(native, go.Bar)
    expected_base = 0 if mode == "group" else None
    assert native.base == expected_base
    assert native.offset == 0.125 and native.width == 0.3
    assert list(native.x) == ["A", "A"] and list(native.y) == [2, 3]
    assert trace == before


@pytest.mark.parametrize("mode", ["stack", "relative"])
@pytest.mark.parametrize("numeric", [False, True], ids=["categorical", "precomputed"])
@pytest.mark.parametrize("cross_trace", [False, True], ids=["same-trace", "cross-trace"])
def test_missing_bars_do_not_poison_later_measured_duplicates(
    mode: str, numeric: bool, cross_trace: bool
) -> None:
    """None/NaN/infinite gaps stay missing and never add to later measured baselines."""
    raw: list[int | float | None] = [2.0, None, float("nan"), float("inf"), 3.0]
    prior = BarTraceConfig(
        x=["A"] * len(raw),
        y=cast(list[int | float], raw),
        x_positions=[0.25] * len(raw) if numeric else [],
    )
    measured = BarTraceConfig(
        x=["A", "A"],
        y=[4, -2],
        x_positions=[0.25, 0.25] if numeric else [],
    )
    traces = [prior, measured] if cross_trace else [prior]
    before = pickle.dumps(traces)
    figure = Figure()
    axis = figure.subplots()
    try:
        MatplotlibTraceRenderer.render(traces, axis, barmode=mode)
        containers = _containers(axis)
        bars = containers[0].patches
        assert len(bars) == len(raw)
        assert all(not math.isfinite(bars[index].get_height()) for index in (1, 2, 3))
        assert [bars[index].get_y() for index in (0, 4)] == pytest.approx([0, 2])
        assert [bars[index].get_height() for index in (0, 4)] == [2, 3]
        if cross_trace:
            following = containers[1].patches
            assert len(following) == 2
            assert [bar.get_y() for bar in following] == pytest.approx(
                [5, 9] if mode == "stack" else [5, 0]
            )
            assert [bar.get_height() for bar in following] == [4, -2]
        assert pickle.dumps(traces) == before
    finally:
        figure.clear()


def test_precomputed_nearby_distinct_positions_keep_their_own_stack() -> None:
    """Coordinates outside the existing 1e-6 equality boundary remain independent."""
    trace = BarTraceConfig(
        x=["A", "B", "A"],
        x_positions=[0.25, 0.250002, 0.25],
        y=[2, 9, 3],
        bar_width=0.0000001,
    )
    figure = Figure()
    axis = figure.subplots()
    try:
        MatplotlibTraceRenderer.render([trace], axis, barmode="stack")
        bars = _containers(axis)[0].patches
        assert [bar.get_y() for bar in bars] == pytest.approx([0, 0, 2])
        assert [bar.get_x() + bar.get_width() / 2 for bar in bars] == pytest.approx(
            trace.x_positions, abs=1e-12
        )
    finally:
        figure.clear()


def test_stacked_duplicate_errors_attach_to_each_measured_top() -> None:
    """Actual uncertainty segments follow corrected row tops without changing sources."""
    trace = BarTraceConfig(
        name="measured",
        x=["A", "A"],
        y=[2, 3],
        error_y=[0.2, 0.3],
        text_values=["first", "second"],
        custom_data={"customdata": [["r0"], ["r1"]]},
    )
    before = pickle.dumps(trace)
    figure = Figure()
    axis = figure.subplots()
    try:
        MatplotlibTraceRenderer.render([trace], axis, barmode="stack")
        errors = [
            container for container in axis.containers if isinstance(container, ErrorbarContainer)
        ]
        assert len(errors) == 1
        segments = errors[0].lines[2][0].get_segments()
        np.testing.assert_allclose(segments, [[[0, 1.8], [0, 2.2]], [[0, 4.7], [0, 5.3]]])
        assert pickle.dumps(trace) == before
    finally:
        figure.clear()


@pytest.mark.parametrize(
    ("coordinate", "expected"),
    [
        (math.nextafter(1e-6, 0.0), 2),
        (1e-6, 0),
        (math.nextafter(1e-6, math.inf), 0),
    ],
    ids=["inside", "strict-boundary", "outside"],
)
def test_numeric_stack_retains_the_strict_existing_tolerance(
    coordinate: float, expected: float
) -> None:
    """The search window must not change the authoritative strict distance test."""
    traces = [
        BarTraceConfig(x=["first"], x_positions=[0.0], y=[2]),
        BarTraceConfig(x=["second"], x_positions=[coordinate], y=[3]),
    ]
    figure = Figure()
    axis = figure.subplots()
    try:
        MatplotlibTraceRenderer.render(traces, axis, barmode="stack")
        assert _containers(axis)[1].patches[0].get_y() == expected
    finally:
        figure.clear()


@pytest.mark.parametrize(
    ("positions", "bottoms"),
    [
        ([0.0, 5e-7, 1e-6], [0, 2, 3]),
        ([1.0, 1.000001], [0, 2]),
        ([2.0, 1.999999], [0, 2]),
    ],
    ids=["nontransitive-neighbors", "rounded-upper-endpoint", "rounded-lower-endpoint"],
)
def test_numeric_stack_uses_pairwise_distance_not_transitive_bins(
    positions: list[float], bottoms: list[float]
) -> None:
    """Nearby coordinates remain individual positions even when their windows overlap."""
    trace = BarTraceConfig(
        x=[str(index) for index in range(len(positions))],
        x_positions=positions,
        y=[2, 3, 5][: len(positions)],
    )
    figure = Figure()
    axis = figure.subplots()
    try:
        MatplotlibTraceRenderer.render([trace], axis, barmode="stack")
        assert [bar.get_y() for bar in _containers(axis)[0].patches] == bottoms
    finally:
        figure.clear()


def test_large_unique_histogram_positions_keep_individual_measured_counts() -> None:
    """An ordinary first relative trace keeps 10000 independent native rectangles."""
    count = 10_000
    trace = BarTraceConfig(
        x_positions=[float(index) for index in range(count)],
        y=[1] * count,
        bar_width=0.5,
    )
    before = pickle.dumps(trace)
    figure = Figure()
    axis = figure.subplots()
    try:
        MatplotlibTraceRenderer.render([trace], axis, barmode="relative")
        bars = _containers(axis)[0].patches
        assert len(bars) == count
        assert all(bar.get_y() == 0 and bar.get_height() == 1 for bar in bars)
        assert [bar.get_x() + bar.get_width() / 2 for bar in bars] == trace.x_positions
        assert pickle.dumps(trace) == before
    finally:
        figure.clear()


@pytest.mark.parametrize(
    "positions", [[0.0, 0.0, 0.0], [0.0, 5e-7, 0.0]], ids=["one-position", "neighboring-positions"]
)
@pytest.mark.parametrize(
    ("heights", "first_bottoms", "following_bottom"),
    [
        ([1e16, -1e16, 1.0], [0.0, 1e16, 0.0], 1.0),
        ([1e16, 1.0, -1e16], [0.0, 1e16, 1e16], 0.0),
    ],
    ids=["cancellation-keeps-unit", "sequential-addition-loses-unit"],
)
def test_numeric_stack_keeps_emitted_floating_addition_order(
    positions: list[float],
    heights: list[float],
    first_bottoms: list[float],
    following_bottom: float,
) -> None:
    """Coordinate indexing must not regroup signed values before adding later rows."""
    traces = [
        BarTraceConfig(x_positions=positions, y=heights),
        BarTraceConfig(x_positions=[5e-7], y=[3.0]),
    ]
    before = pickle.dumps(traces)
    figure = Figure()
    axis = figure.subplots()
    try:
        MatplotlibTraceRenderer.render(traces, axis, barmode="stack")
        first, following = _containers(axis)
        assert [bar.get_y() for bar in first.patches] == first_bottoms
        assert following.patches[0].get_y() == following_bottom
        assert following.patches[0].get_height() == 3.0
        assert pickle.dumps(traces) == before
    finally:
        figure.clear()
