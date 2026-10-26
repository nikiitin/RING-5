"""Native storage-cell views preserve declared order, measured mass and axis semantics."""

from __future__ import annotations

import copy
import math
from typing import Literal, cast

import pandas as pd
import pytest
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import plotly.graph_objects as go

import ring5
from src.core.common.distribution_metadata import with_distribution_layouts
from src.core.models.distribution_geometry import native_bucket_label
from src.core.models.plot_config import PlotConfig
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot
from src.web.rendering.figure_preparation import PreparedFigure, prepare_figure


def native_frame(
    rows: list[list[float]],
    geometry: ring5.DistributionGeometry | None = None,
) -> pd.DataFrame:
    geometry = geometry or ring5.DistributionGeometry(0, 1, 1)
    bindings = (
        ring5.DistributionColumn("left", "underflows", "underflow", None),
        *(
            ring5.DistributionColumn(
                f"physical_{index}", native_bucket_label(geometry, index), "bucket", index
            )
            for index in range(geometry.bucket_count)
        ),
        ring5.DistributionColumn("right", "overflows", "overflow", None),
        ring5.DistributionColumn("average", "mean", "summary", None),
    )
    layout = ring5.NativeDistributionLayout(geometry, "missing", bindings)
    frame = pd.DataFrame(
        [row + [math.nan] for row in rows], columns=[binding.column for binding in bindings]
    )
    return with_distribution_layouts(frame, {"logical": layout})


@pytest.mark.parametrize(
    "geometry,labels",
    [
        ((0.25, 0.25, 1), ["underflows", "0.25", "overflows"]),
        ((0.25, 5.75, 2.5), ["underflows", "0.25-1.75", "2.75-4.25", "5.25-5.75", "overflows"]),
        ((0, 3, 0.5), ["underflows", "0", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "overflows"]),
        ((-1.25, 1.25, 1), ["underflows", "-1.25", "-0.25", "0.75", "1.75", "overflows"]),
        ((1e6, 1e6, 1), ["underflows", "1e+06", "overflows"]),
    ],
)
def test_native_cells_keep_literal_labels_and_ordinal_positions(
    geometry: tuple[float, float, float], labels: list[str]
) -> None:
    # [test->req~ring5.plot.histogram~2]
    counts = [float(index) for index in range(len(labels))]
    frame = native_frame([counts], ring5.DistributionGeometry(*geometry))
    before, attrs = frame.copy(deep=True), copy.deepcopy(frame.attrs)
    config: PlotConfig = {"histogram_variable": "logical"}
    result = HistogramPlot(1, "Native").create_traces(frame, config)
    trace = result.traces[0]
    assert isinstance(trace, BarTraceConfig)
    assert trace.x == labels and trace.y == counts
    assert trace.x_positions == [float(index) for index in range(len(labels))]
    assert trace.bar_width == [1.0] * len(labels)
    assert result.custom_x_ticks == {"vals": trace.x_positions, "text": labels}
    assert result.default_x_axis_label == "Native bucket"
    assert config == {"histogram_variable": "logical"}
    pd.testing.assert_frame_equal(frame, before)
    assert frame.attrs == attrs


@pytest.mark.parametrize(
    "normalization,cumulative,expected",
    [
        ("count", False, [1, 2, 3, 4]),
        ("count", True, [1, 3, 6, 10]),
        ("probability", False, [0.1, 0.2, 0.3, 0.4]),
        ("percent", False, [10, 20, 30, 40]),
        ("probability", True, [0.1, 0.3, 0.6, 1]),
        ("percent", True, [10, 30, 60, 100]),
        ("density", True, [0.1, 0.3, 0.6, 1]),
    ],
)
def test_native_mass_modes(normalization: str, cumulative: bool, expected: list[float]) -> None:
    # [test->req~ring5.figure.histogram-cumulative~2]
    result = HistogramPlot(1, "Native").create_traces(
        native_frame([[1, 2, 3, 4]]),
        {"histogram_variable": "logical", "normalization": normalization, "cumulative": cumulative},
    )
    trace = result.traces[0]
    assert isinstance(trace, BarTraceConfig)
    assert trace.y == pytest.approx(expected)


@pytest.mark.parametrize("normalization", ["probability", "percent", "density"])
def test_zero_native_mass_normalized_views_reject(normalization: str) -> None:
    with pytest.raises(ValueError, match="positive selected mass"):
        HistogramPlot(1, "Native").create_traces(
            native_frame([[0, 0, 0, 0]]),
            {"histogram_variable": "logical", "normalization": normalization, "cumulative": True},
        )


@pytest.mark.parametrize("cumulative", [False, True])
def test_observed_native_zero_counts_remain_valid(cumulative: bool) -> None:
    result = HistogramPlot(1, "Native").create_traces(
        native_frame([[0, 0, 0, 0]]), {"histogram_variable": "logical", "cumulative": cumulative}
    )
    assert cast(BarTraceConfig, result.traces[0]).y == [0, 0, 0, 0]


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -1.0])
def test_native_view_never_drops_invalid_frequency_cells(invalid: float) -> None:
    with pytest.raises(ValueError, match="measured, finite and nonnegative"):
        HistogramPlot(1, "Native").create_traces(
            native_frame([[0, invalid, 2, 0]]), {"histogram_variable": "logical"}
        )


def test_native_groups_sum_actual_cells_and_reject_one_zero_mass_group() -> None:
    frame = native_frame([[0, 1, 2, 0], [0, 3, 4, 0], [0, 0, 0, 0]])
    frame["group"] = ["positive", "positive", "zero"]
    plot = HistogramPlot(1, "Native")
    result = plot.create_traces(frame, {"histogram_variable": "logical", "group_by": "group"})
    assert [cast(BarTraceConfig, trace).y for trace in result.traces] == [
        [0, 4, 6, 0],
        [0, 0, 0, 0],
    ]
    with pytest.raises(ValueError, match="positive selected mass"):
        plot.create_traces(
            frame,
            {"histogram_variable": "logical", "group_by": "group", "normalization": "probability"},
        )


@pytest.mark.parametrize("engine", ["matplotlib", "plotly"])
@pytest.mark.parametrize("label_key", [None, "xlabel", "xaxis_title"])
@pytest.mark.public_api
def test_public_native_arbitrary_bindings_render_default_and_explicit_axis_labels(
    engine: Literal["matplotlib", "plotly"], label_key: str | None
) -> None:
    frame = native_frame([[0, 2, 3, 0]])
    config: PlotConfig = {"histogram_variable": "logical"}
    if label_key is not None:
        config[label_key] = "Explicit label"
    expected_label = "Explicit label" if label_key else "Native bucket"
    with ring5.Session() as session:
        plot = session.create_plot("histogram", data=ring5.Table(frame), config=config)
        figure = session.render(plot, engine=engine)
        preparation = plot.render_artifact.preparation
        assert (
            isinstance(preparation, PreparedFigure)
            and preparation.spec.axes.x.label == expected_label
        )
        assert preparation.trace_result.custom_x_ticks == {
            "vals": [0, 1, 2, 3],
            "text": ["underflows", "0", "1", "overflows"],
        }
        if isinstance(figure, Figure):
            assert figure.axes[0].get_xlabel() == expected_label
            assert [cast(Rectangle, patch).get_height() for patch in figure.axes[0].patches] == [
                0,
                2,
                3,
                0,
            ]
        else:
            assert isinstance(figure, go.Figure)
            assert figure.layout.xaxis.title.text == expected_label
            assert isinstance(figure.data[0], go.Bar)
            assert list(figure.data[0].y) == [0, 2, 3, 0]
    assert config == (
        {"histogram_variable": "logical", label_key: "Explicit label"}
        if label_key
        else {"histogram_variable": "logical"}
    )


def test_neutral_axis_default_does_not_change_ordinary_plot_or_caller_config() -> None:
    frame = pd.DataFrame({"ordinary..0-1": [2.0]})
    config: PlotConfig = {"histogram_variable": "ordinary"}
    result = prepare_figure(frame, config, "histogram", HistogramPlot(1, "Generic").create_traces)
    assert result.spec.axes.x.label == "" and result.trace_result.default_x_axis_label is None
    assert config == {"histogram_variable": "ordinary"}


@pytest.mark.parametrize("engine", ["matplotlib", "plotly"])
@pytest.mark.parametrize("extra", [{"bucket_size": 1.0}, {"normalization": "density"}])
@pytest.mark.public_api
def test_public_native_unsupported_views_are_typed_and_preserve_previous_artifact(
    engine: Literal["matplotlib", "plotly"], extra: PlotConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = native_frame([[0, 2, 3, 0]])
    before = frame.copy(deep=True)
    attrs = copy.deepcopy(frame.attrs)
    with ring5.Session() as session:
        plot = session.create_plot(
            "histogram", data=ring5.Table(frame), config={"histogram_variable": "logical"}
        )
        session.render(plot, engine=engine)
        artifact, config = plot.render_artifact, plot.config
        create = plot.create_traces
        monkeypatch.setattr(
            plot, "create_traces", lambda data, request: create(data, {**request, **extra})
        )
        with pytest.raises(ring5.RenderError, match="Native Distribution"):
            session.render(plot, engine=engine)
        assert plot.render_artifact is artifact and plot.config == config
    pd.testing.assert_frame_equal(frame, before)
    assert frame.attrs == attrs


@pytest.mark.parametrize("selection", ["empty_frame", "missing_groups"])
def test_native_view_requires_an_observed_selected_frame_and_group(selection: str) -> None:
    frame = native_frame([[0, 2, 3, 0]])
    config: PlotConfig = {"histogram_variable": "logical"}
    if selection == "empty_frame":
        frame = frame.head(0)
    else:
        frame["group"] = [None]
        config["group_by"] = "group"
    with pytest.raises(ValueError, match="measured, finite|observed selected group"):
        HistogramPlot(1, "Native").create_traces(frame, config)


def test_native_actual_zero_group_is_an_observed_count_view() -> None:
    frame = native_frame([[0, 0, 0, 0]])
    frame["group"] = ["zero"]
    result = HistogramPlot(1, "Native").create_traces(
        frame, {"histogram_variable": "logical", "group_by": "group"}
    )
    assert len(result.traces) == 1
    assert cast(BarTraceConfig, result.traces[0]).y == [0, 0, 0, 0]


def test_native_group_selection_excludes_null_keys_without_mutating_stored_cells() -> None:
    frame = native_frame([[0, 2, 3, 0], [math.nan, math.nan, math.nan, math.nan]])
    frame["group"] = ["selected", None]
    before, attrs = frame.copy(deep=True), copy.deepcopy(frame.attrs)
    result = HistogramPlot(1, "Native").create_traces(
        frame, {"histogram_variable": "logical", "group_by": "group"}
    )
    assert len(result.traces) == 1
    assert cast(BarTraceConfig, result.traces[0]).y == [0, 2, 3, 0]
    pd.testing.assert_frame_equal(frame, before)
    assert frame.attrs == attrs


@pytest.mark.parametrize("opaque", [False, True])
@pytest.mark.parametrize("engine", ["matplotlib", "plotly"])
@pytest.mark.public_api
def test_public_generic_prefix_cannot_reinterpret_declared_physical_bindings(
    opaque: bool, engine: Literal["matplotlib", "plotly"]
) -> None:
    frame = native_frame([[0, 2, 3, 0]])
    from src.core.common.distribution_metadata import inspect_distribution_layouts
    from src.core.common.distribution_layout_codec import encode_distribution_layout

    layout = inspect_distribution_layouts(frame)["logical"]
    bindings = tuple(
        ring5.DistributionColumn(
            f"physical..{column.source_label}",
            column.source_label,
            "source" if opaque else column.role,
            None if opaque else column.native_index,
        )
        for column in layout.columns
    )
    mapped = frame.rename(
        columns={
            column.column: binding.column
            for column, binding in zip(layout.columns, bindings, strict=True)
        }
    )
    declared = (
        ring5.OpaqueDistributionLayout(bindings)
        if opaque
        else ring5.NativeDistributionLayout(
            cast(ring5.NativeDistributionLayout, layout).geometry, "missing", bindings
        )
    )
    mapped.attrs["ring5.distribution_layouts"] = {"logical": encode_distribution_layout(declared)}
    mapped["physical..aux"] = 1.0
    mapped["ordinary..0-0"] = 4.0
    before, attrs = mapped.copy(deep=True), copy.deepcopy(mapped.attrs)
    with ring5.Session() as session:
        ordinary = session.create_plot(
            "histogram", data=ring5.Table(mapped), config={"histogram_variable": "ordinary"}
        )
        session.render(ordinary, engine=engine)
        artifact, config = ordinary.render_artifact, ordinary.config
        with pytest.raises(ring5.RenderError, match="prefix overlaps declared"):
            session.plot(
                "histogram",
                data=ring5.Table(mapped),
                config={"histogram_variable": "physical"},
                engine=engine,
            )
        assert ordinary.render_artifact is artifact and ordinary.config == config
        preparation = ordinary.render_artifact.preparation
        assert isinstance(preparation, PreparedFigure)
        assert cast(BarTraceConfig, preparation.trace_result.traces[0]).y == [4.0]
    pd.testing.assert_frame_equal(mapped, before)
    assert mapped.attrs == attrs


@pytest.mark.parametrize("engine", ["matplotlib", "plotly"])
@pytest.mark.parametrize("label_mode", ["absent", "empty", "xlabel", "xaxis_title", "figure_spec"])
@pytest.mark.public_api
def test_native_semantic_axis_default_precedes_inferred_physical_units_only(
    engine: Literal["matplotlib", "plotly"], label_mode: str
) -> None:
    frame = native_frame([[0, 2, 3, 0]])
    request: PlotConfig = {"histogram_variable": "logical", "x": "physical_0"}
    if label_mode == "empty":
        request.update(xlabel="", xaxis_title="")
    elif label_mode in {"xlabel", "xaxis_title"}:
        request[label_mode] = "Explicit label"
    original = copy.deepcopy(request)
    expected = "Explicit label" if label_mode in {"xlabel", "xaxis_title"} else "Native bucket"
    with ring5.Session() as session:
        table = session.apply_semantics(
            ring5.Table(frame),
            ring5.DatasetSemantics((ring5.ColumnSemantics("physical_0", "Latency", "ns"),)),
        )
        before, attrs = table.frame, copy.deepcopy(table.frame.attrs)
        configured = (
            ring5.FigureSpec(x="physical_0", extra={"histogram_variable": "logical"})
            if label_mode == "figure_spec"
            else request
        )
        plot = session.create_plot("histogram", data=table, config=configured)
        figure = session.render(plot, engine=engine)
        preparation = plot.render_artifact.preparation
        assert isinstance(preparation, PreparedFigure)
        assert preparation.spec.axes.x.label == expected
        assert (
            preparation.config.get("xlabel") or preparation.config.get("xaxis_title")
        ) == expected
        if expected == "Native bucket":
            assert plot.config["xlabel"] == expected
        if isinstance(figure, Figure):
            assert figure.axes[0].get_xlabel() == expected
        else:
            assert isinstance(figure, go.Figure) and figure.layout.xaxis.title.text == expected
        pd.testing.assert_frame_equal(table.frame, before)
        assert table.frame.attrs == attrs
    assert request == original


def test_ordinary_interval_axis_keeps_inferred_physical_semantics() -> None:
    from src.core.services.managers.semantic_metadata_service import SemanticMetadataService

    frame = SemanticMetadataService.attach(
        pd.DataFrame({"ordinary..0-1": [2.0]}),
        ring5.DatasetSemantics((ring5.ColumnSemantics("ordinary..0-1", "Latency", "ns"),)),
    )
    original, attrs = frame.copy(deep=True), copy.deepcopy(frame.attrs)
    config: PlotConfig = {"histogram_variable": "ordinary", "x": "ordinary..0-1"}
    result = prepare_figure(frame, config, "histogram", HistogramPlot(1, "Generic").create_traces)
    assert result.spec.axes.x.label == "Latency (ns)"
    assert result.trace_result.default_x_axis_label is None
    assert config == {"histogram_variable": "ordinary", "x": "ordinary..0-1"}
    pd.testing.assert_frame_equal(frame, original)
    assert frame.attrs == attrs
