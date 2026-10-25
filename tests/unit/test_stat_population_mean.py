"""Population means retain finite range, cancellation, subnormals and missingness."""

from __future__ import annotations

import csv
import math
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from src.core.models.parsing_models import StatConfig, StatParamValue
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.types.base import Observation, StatContent, StatResult, StatType
from src.parsing.gem5.types.distribution import Distribution
from src.parsing.gem5.types.histogram import Histogram
from src.parsing.gem5.types.scalar import Scalar
from src.parsing.gem5.types.vector import Vector

Accumulator = StatType[StatContent, StatResult]
_MAX = sys.float_info.max
_MIN = math.ulp(0.0)
_CASES: list[tuple[list[float], float]] = [
    ([1e308, 1e308], 1e308),
    ([_MAX, _MAX], _MAX),
    ([_MAX, _MAX, _MAX], _MAX),
    ([-_MAX, -_MAX], -_MAX),
    ([_MAX, _MAX, -_MAX, -_MAX, 1.0], 0.2),
    ([_MAX, _MAX, -_MAX, -_MAX, _MIN * 5], _MIN),
    ([_MIN, _MIN], _MIN),
    ([_MIN, _MIN, _MIN], _MIN),
    ([0.0, 0.0], 0.0),
    ([math.inf, 1.0], math.inf),
    ([-math.inf, 1.0], -math.inf),
    ([_MAX, _MAX, -math.inf], -math.inf),
    ([-_MAX, -_MAX, math.inf], math.inf),
    ([math.inf, -math.inf], math.nan),
    ([math.nan, math.inf], math.nan),
    ([math.nan, 1.0], math.nan),
]
_KINDS: list[tuple[Callable[[int], Accumulator], Callable[[float], Observation], str | None]] = [
    (lambda repeat: Scalar(repeat=repeat), lambda value: value, None),
    (lambda repeat: Vector(repeat=repeat, entries=["001"]), lambda value: {"001": value}, "001"),
    (
        lambda repeat: Distribution(repeat=repeat, minimum=0, maximum=0),
        lambda value: {"underflows": 0.0, "0": value, "overflows": 0.0},
        "0",
    ),
    (lambda repeat: Histogram(repeat=repeat), lambda value: {"0-0": value}, "0-0"),
    (
        lambda repeat: Histogram(repeat=repeat, bins=2, max_range=1),
        lambda value: {"0-0": value},
        "0-0",
    ),
]


@pytest.mark.parametrize(("values", "expected"), _CASES)
@pytest.mark.parametrize(("factory", "observation", "entry"), _KINDS)
def test_each_numeric_kind_uses_the_same_range_safe_population_mean(
    values: list[float],
    expected: float,
    factory: Callable[[int], Accumulator],
    observation: Callable[[float], Observation],
    entry: str | None,
) -> None:
    # [test->req~ring5.ingestion.parse-integrity~1]
    stat = factory(len(values))
    for value in values:
        stat.add_observation(observation(value))
    stat.balance_content()
    stat.reduce_duplicates()
    result = stat.reduced_content
    if entry is not None:
        assert isinstance(result, dict)
        actual = result[entry]
    else:
        assert isinstance(result, float)
        actual = result
    if math.isnan(expected):
        assert math.isnan(actual)
    else:
        assert actual == expected


@pytest.mark.parametrize(
    ("kind", "source_text", "options", "header"),
    [
        ("scalar", "source 1e308\nsource 1e308\n", {}, "value"),
        ("vector", "source::a 1e308\nsource::a 1e308\n", {"entries": ["a"]}, "value..a"),
        ("histogram", "source::0-0 1e308\nsource::0-0 1e308\n", {}, "value..0-0"),
    ],
)
def test_real_worker_and_csv_keep_a_large_finite_mean(
    tmp_path: Path,
    kind: str,
    source_text: str,
    options: dict[str, StatParamValue],
    header: str,
) -> None:
    (tmp_path / "stats.txt").write_text(source_text, encoding="utf-8")
    params: dict[str, StatParamValue] = {"source_type": kind, **options}
    batch = Gem5Parser.submit_parse_async(
        str(tmp_path),
        "stats.txt",
        [StatConfig("value", kind, source_name="source", repeat=2, params=params)],
        str(tmp_path / "output"),
    )
    results = [future.result(timeout=30) for future in batch.futures]
    output = Gem5Parser.finalize_parsing(str(tmp_path / "output"), results, var_names=["value"])
    assert output is not None
    with Path(output).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows == [[header], ["1e+308"]]
