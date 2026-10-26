"""Histogram modes admit measured zero and finite arithmetic at their actual owners."""

from __future__ import annotations

import copy
import math
from fractions import Fraction
from typing import Literal, cast

import pandas as pd
import pytest

import ring5
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.rendering.figure_preparation import PreparedFigure
from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot
from src.web.pages.ui.plotting.utils import histogram_bins
from src.web.pages.ui.plotting.utils.histogram_bins import (
    HistogramBin,
    aggregate_histogram_observations,
    rebin_histogram,
)


def test_per_bin_aggregation_overflow_has_a_local_value_error_cause() -> None:
    with pytest.raises(ValueError, match="finite numeric range") as caught:
        aggregate_histogram_observations(["0-0"], [[1e308], [1e308]])
    assert type(caught.value.__cause__) is OverflowError


def test_rebin_preserves_large_count_without_intermediate_overflow() -> None:
    bins, values = rebin_histogram([HistogramBin(0, 10, "[0,10)")], [1e308], 10)
    assert [(bucket.lower, bucket.upper) for bucket in bins] == [(0, 10)]
    assert values == [1e308]


@pytest.mark.parametrize("span_overflow", [False, True])
def test_rebin_nonfinite_count_geometry_rejects_before_target_allocation(
    monkeypatch: pytest.MonkeyPatch, span_overflow: bool
) -> None:
    bins = (
        [HistogramBin(-1e308, -9e307, "left"), HistogramBin(9e307, 1e308, "right")]
        if span_overflow
        else [HistogramBin(0, 1, "unit")]
    )
    values = [1.0] * len(bins)
    size = 1e308 if span_overflow else 5e-324

    def no_allocation(*args: object, **kwargs: object) -> None:
        raise AssertionError("Invalid rebin geometry reached target allocation.")

    monkeypatch.setattr(histogram_bins, "HistogramBin", no_allocation)
    with pytest.raises(ValueError, match="rebin geometry.*finite"):
        rebin_histogram(bins, values, size)


def test_rebin_cannot_publish_nonfinite_combined_target_mass() -> None:
    with pytest.raises(ValueError, match="Histogram counts.*finite"):
        rebin_histogram(
            [HistogramBin(0, 2, "left"), HistogramBin(1, 3, "right")], [1e308, 1e308], 3
        )


def test_distinct_finite_large_counts_need_no_global_total_for_raw_count() -> None:
    # [test->req~ring5.figure.histogram-cumulative~2]
    plot = HistogramPlot(1, "Finite")
    frame = pd.DataFrame({"h..0-0": [1e308], "h..1-1": [1e308]})
    result = plot.create_traces(frame, {"histogram_variable": "h"})
    assert cast(BarTraceConfig, result.traces[0]).y == [1e308, 1e308]
    with pytest.raises(ValueError, match="finite numeric range") as caught:
        plot.create_traces(frame, {"histogram_variable": "h", "normalization": "probability"})
    assert type(caught.value.__cause__) is OverflowError
    with pytest.raises(ValueError, match="Cumulative.*finite"):
        plot.create_traces(frame, {"histogram_variable": "h", "cumulative": True})


def test_density_output_must_remain_finite() -> None:
    with pytest.raises(ValueError, match="mass exceeds the finite numeric range"):
        HistogramPlot(1, "Finite").create_traces(
            pd.DataFrame({"h..[0,5e-324)": [1.0]}),
            {"histogram_variable": "h", "normalization": "density"},
        )


@pytest.mark.parametrize("engine", ["matplotlib", "plotly"])
@pytest.mark.parametrize("normalization", ["probability", "percent", "density"])
@pytest.mark.parametrize("cumulative", [False, True])
@pytest.mark.public_api
def test_public_generic_zero_mass_normalization_rejects_visibly(
    engine: Literal["matplotlib", "plotly"], normalization: str, cumulative: bool
) -> None:
    # [test->req~ring5.figure.histogram-cumulative~2]
    frame = pd.DataFrame({"h..0-0": [0.0], "h..1-1": [0.0]})
    before = frame.copy(deep=True)
    with ring5.Session() as session:
        with pytest.raises(ring5.RenderError, match="positive selected mass"):
            session.plot(
                "histogram",
                data=ring5.Table(frame),
                config={
                    "histogram_variable": "h",
                    "normalization": normalization,
                    "cumulative": cumulative,
                },
                engine=engine,
            )
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("engine", ["matplotlib", "plotly"])
@pytest.mark.parametrize("cumulative", [False, True])
@pytest.mark.public_api
def test_public_generic_observed_zero_count_remains_valid(
    engine: Literal["matplotlib", "plotly"], cumulative: bool
) -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "histogram",
            data=ring5.Table.from_rows([{"h..0-0": 0.0, "h..1-1": 0.0}]),
            config={"histogram_variable": "h", "cumulative": cumulative},
        )
        session.render(plot, engine=engine)
        preparation = plot.render_artifact.preparation
        assert isinstance(preparation, PreparedFigure)
        assert cast(BarTraceConfig, preparation.trace_result.traces[0]).y == [0.0, 0.0]


@pytest.mark.parametrize("engine", ["matplotlib", "plotly"])
@pytest.mark.parametrize("missing", [False, True])
@pytest.mark.public_api
def test_one_invalid_group_rejects_whole_normalized_render_and_preserves_artifact(
    engine: Literal["matplotlib", "plotly"], missing: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    good = pd.DataFrame({"h..0-0": [1.0], "group": ["good"]})
    invalid = pd.DataFrame(
        {"h..0-0": [1.0, math.nan if missing else 0.0], "group": ["good", "empty"]}
    )
    before, attrs = invalid.copy(deep=True), copy.deepcopy(invalid.attrs)
    with ring5.Session() as session:
        plot = session.create_plot(
            "histogram",
            data=ring5.Table(good),
            config={"histogram_variable": "h", "normalization": "probability", "group_by": "group"},
        )
        session.render(plot, engine=engine)
        artifact, config = plot.render_artifact, plot.config
        create = plot.create_traces
        monkeypatch.setattr(plot, "create_traces", lambda _data, request: create(invalid, request))
        with pytest.raises(ring5.RenderError, match="measured bucket|positive selected mass"):
            session.render(plot, engine=engine)
        assert plot.render_artifact is artifact and plot.config == config
    pd.testing.assert_frame_equal(invalid, before)
    assert invalid.attrs == attrs


def test_overlap_rebin_preserves_representable_tiny_mass_beside_a_large_interval() -> None:
    # [test->req~ring5.plot.histogram~2]
    bins, values = rebin_histogram(
        [HistogramBin(0, 1e-308, "small"), HistogramBin(0, 1e308, "large")],
        [0.0, 1e308],
        None,
    )
    assert [(bucket.lower, bucket.upper) for bucket in bins] == [(0, 1e-308), (1e-308, 1e308)]
    assert values[0] == 1e-308 and values[1] == 1e308


@pytest.mark.parametrize(
    "value,overlap,width",
    [
        (1e308, 10.0, 10.0),
        (1e308, 1e-308, 1e308),
        (float.fromhex("0x0.0000000000003p-1022"), float.fromhex("0x1.5555555555556p-3"), 1.0),
        (math.ulp(0.0), 1.0, 1.0),
        (float.fromhex("0x1.fffffffffffffp+1023"), 1.0, 1.0),
        (3.0, 1.0, 10.0),
    ],
)
def test_overlap_contribution_matches_one_final_exact_ratio_rounding(
    value: float, overlap: float, width: float
) -> None:
    # [test->req~ring5.plot.histogram~2]
    expected = float(Fraction(value) * Fraction(overlap) / Fraction(width))
    assert expected > 0
    assert histogram_bins.histogram_mass_ratio(value, overlap, width) == expected


def test_positive_unrepresentable_overlap_mass_rejects_instead_of_becoming_zero() -> None:
    with pytest.raises(ValueError, match="finite nonzero range"):
        histogram_bins.histogram_mass_ratio(math.ulp(0.0), 0.25, 1.0)
    assert histogram_bins.histogram_mass_ratio(0.0, 0.25, 1.0) == 0.0
    assert histogram_bins.histogram_mass_ratio(math.ulp(0.0), 0.0, 1.0) == 0.0


def test_percent_and_density_round_final_mass_without_staged_underflow() -> None:
    plot = HistogramPlot(1, "Finite")
    minimum = math.ulp(0.0)
    percent = plot._normalize_values([minimum, 100.0], {"normalization": "percent"})
    assert percent[0] == float(Fraction(minimum) * 100 / Fraction(100.0)) == minimum
    density = plot._normalize_values([1e-308, 1e308], {"normalization": "density"}, [1e-308, 1.0])
    assert density[0] == float(Fraction(1e-308) / (Fraction(1e308) * Fraction(1e-308))) == 1e-308
    with pytest.raises(ValueError, match="finite nonzero range"):
        plot._normalize_values([minimum, 100.0], {"normalization": "probability"})


def test_rebin_accumulates_representable_small_contributions_once() -> None:
    bins = [HistogramBin(0, 1, "a"), HistogramBin(0, 1, "b"), HistogramBin(0, 1, "c")]
    _, values = rebin_histogram(bins, [1e16, 1.0, 1.0], 1.0)
    assert values == [1e16 + 2.0]


@pytest.mark.parametrize(
    "values",
    [
        [1e16, 1.0, 1.0],
        [0.0, 0.0],
        [math.ulp(0.0)] * 3,
        [float.fromhex("0x1.fffffffffffffp+1022")] * 2,
    ],
)
def test_cumulative_counts_match_exact_represented_prefixes(values: list[float]) -> None:
    # [test->req~ring5.plot.histogram~2]
    exact = Fraction(0)
    expected = []
    for value in values:
        exact += Fraction(value)
        expected.append(float(exact))
    actual = HistogramPlot(1, "Finite")._normalize_values(values, {"cumulative": True})
    assert actual == expected
    if values == [1e16, 1.0, 1.0]:
        assert actual == [1e16, 1e16, 1e16 + 2.0]


def test_cumulative_overflow_keeps_known_conversion_cause() -> None:
    with pytest.raises(ValueError, match="Cumulative.*finite") as caught:
        histogram_bins.cumulative_histogram_counts([1e308, 1e308])
    assert type(caught.value.__cause__) is OverflowError
