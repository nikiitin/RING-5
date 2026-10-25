"""Missing diagnostics use observation presence, independently of numeric NaN values."""

from __future__ import annotations

import math

import pytest

from src.core.models.parsing_models import StatConfig, StatParamValue
from src.parsing.gem5.impl.source_bindings import resolve_sources
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.types.type_mapper import TypeMapper
from src.parsing.gem5.types.vector import Vector


@pytest.mark.parametrize(
    ("kind", "repeat", "params", "wire", "missing"),
    [
        ("vector", 1, {"entries": ["a", "b"]}, "vector/source::a/2", 1),
        ("vector", 1, {"entries": ["a", "b"]}, "vector/source::other/3", 2),
        ("vector", 1, {"entries": ["a", "b"]}, "", 2),
        (
            "vector",
            2,
            {"entries": ["a", "b"]},
            "vector/source::a/2\nvector/source::b/3\ndump//\nvector/source::a/4\ndump//",
            1,
        ),
        ("vector", 1, {"entries": ["a", "b"]}, "vector/source::a/nan\nvector/source::b/nan", 0),
        ("scalar", 1, {}, "scalar/source/nan", 0),
        ("scalar", 2, {}, "scalar/source/2", 1),
        ("scalar", 1, {}, "", 1),
        (
            "histogram",
            1,
            {"entries": ["0-0"], "statistics": ["mean"]},
            "histogram/source::0-0/2",
            1,
        ),
        (
            "histogram",
            1,
            {"entries": ["0-0"], "statistics": ["mean"]},
            "histogram/source::0-0/2\nsummary/source::mean/nan",
            0,
        ),
        ("histogram", 1, {}, "", 1),
        (
            "distribution",
            1,
            {"minimum": 0, "maximum": 0, "statistics": ["mean"]},
            (
                "distribution/source::underflows/0\n"
                "distribution/source::0/2\n"
                "distribution/source::overflows/0"
            ),
            1,
        ),
        (
            "distribution",
            1,
            {"minimum": 0, "maximum": 0, "statistics": ["mean"]},
            (
                "distribution/source::underflows/0\n"
                "distribution/source::0/2\n"
                "distribution/source::overflows/0\n"
                "summary/source::mean/nan"
            ),
            0,
        ),
        ("configuration", 3, {"on_empty": "unknown"}, "", 0),
        ("configuration", 1, {"on_empty": "unknown"}, "configuration/source/nan", 0),
    ],
)
def test_worker_diagnostics_distinguish_absence_from_measured_nan_and_text_policy(
    kind: str,
    repeat: int,
    params: dict[str, StatParamValue],
    wire: str,
    missing: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # [test->req~ring5.ingestion.parse-integrity~1]
    config = StatConfig(
        "output",
        kind,
        source_name="source",
        repeat=repeat,
        params={"source_type": kind, **params},
    )
    plan = resolve_sources([config], None)
    stat = TypeMapper.create_stat(plan.accumulators[0])
    worker = Gem5ParseWork("unused", {"output": stat}, plan)
    worker._process_output(wire)
    assert stat.missing_measurement_count == missing
    assert ("absent or incomplete" in caplog.text) == bool(missing)
    stat.balance_content()
    assert stat.missing_measurement_count == stat.padded_count == missing
    stat.reduce_duplicates()
    if kind == "configuration":
        assert stat.reduced_content == ("nan" if wire else "unknown")


def test_derived_nan_views_do_not_hide_absence_or_mutate_presence() -> None:
    stat = Vector(entries=["a", "b"])
    stat.add_observation({"a": 2.0})
    view = stat.content
    assert math.isnan(view["b"][0])
    assert stat.missing_measurement_count == 1
    view["b"][0] = 99
    assert stat.missing_measurement_count == 1
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content["a"] == 2.0
    assert math.isnan(stat.reduced_content["b"])

    observed_nan = Vector(entries=["a", "b"])
    observed_nan.add_observation({"a": 2.0, "b": math.nan})
    assert observed_nan.missing_measurement_count == 0
    observed_nan.balance_content()
    observed_nan.reduce_duplicates()
    assert math.isnan(observed_nan.reduced_content["b"])
    assert observed_nan.padded_count == 0
