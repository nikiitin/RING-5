"""Missingness, histogram interval and CSV shape regression contracts."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.types.distribution import Distribution
from src.parsing.gem5.types.histogram import Histogram
from src.parsing.gem5.types.scalar import Scalar
from src.parsing.gem5.types.vector import Vector


@pytest.mark.parametrize(
    "stat", [Distribution(minimum=0, maximum=1), Histogram(bins=2, max_range=10)]
)
def test_absent_frequency_stat_remains_nan(stat: Distribution | Histogram) -> None:
    stat.balance_content()
    stat.reduce_duplicates()
    assert all(math.isnan(value) for value in stat.reduced_content.values())


def test_observed_distribution_omits_only_zero_frequency_bins() -> None:
    stat = Distribution(minimum=0, maximum=2, statistics=["mean"])
    stat.add_observation({"underflows": 0, "0": 0, "2": 4, "overflows": 0})
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content["0"] == 0
    assert stat.reduced_content["1"] == 0
    assert stat.reduced_content["2"] == 4
    assert math.isnan(stat.reduced_content["mean"])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"0-0": 9, "10-10": 1}, {"0-9": 9, "10+": 1}),
        ({"9-10": 10}, {"0-9": 5, "10+": 5}),
        ({"-10--1": 7, "-1-0": 4}, {"<0": 9, "0-9": 2, "10+": 0}),
    ],
)
def test_inclusive_histogram_rebin_conserves_mass(
    raw: dict[str, int], expected: dict[str, int]
) -> None:
    stat = Histogram(bins=2, max_range=10)
    stat.add_observation({key: value for key, value in raw.items()})
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == pytest.approx(expected)
    assert sum(stat.reduced_content.values()) == pytest.approx(sum(raw.values()))


def test_fractional_target_edges_are_explicit_and_distinct() -> None:
    stat = Histogram(bins=4, max_range=1)
    stat.add_observation({"0-0": 12})
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.entries == [
        "[0,0.333333333333)",
        "[0.333333333333,0.666666666667)",
        "[0.666666666667,1)",
        "1+",
    ]
    assert list(stat.reduced_content.values()).count(4) == 3
    assert sum(stat.reduced_content.values()) == pytest.approx(12)


def test_rebin_missing_expected_instance_does_not_dilute_frequency() -> None:
    stat = Histogram(repeat=2, bins=2, max_range=10, statistics=["mean"])
    stat.add_observation({"0-9": 4})
    stat.balance_content()
    stat.reduce_duplicates()
    assert all(math.isnan(value) for value in stat.reduced_content.values())


def _histogram(entries: dict[str, int]) -> Histogram:
    stat = Histogram()
    stat.add_observation({key: value for key, value in entries.items()})
    return stat


def test_final_csv_union_is_order_independent_and_keeps_absent_first_histogram(
    tmp_path: Path,
) -> None:
    schemas = []
    for reverse in (False, True):
        rows = [{"h": Histogram()}, {"h": _histogram({"0-9": 9})}, {"h": _histogram({"0-19": 12})}]
        output = Gem5Parser.construct_final_csv(
            str(tmp_path), rows[::-1] if reverse else rows, ["h"]
        )
        assert output is not None
        with Path(output).open(newline="", encoding="utf-8") as stream:
            parsed = list(csv.reader(stream))
        schemas.append(parsed[0])
        assert all(len(row) == 2 for row in parsed)
        assert sorted(parsed[1:]) == sorted([["NaN", "NaN"], ["NaN", "9.0"], ["12.0", "NaN"]])
    assert schemas == [["h..0-19", "h..0-9"]] * 2


def test_final_csv_missing_vector_preserves_following_scalar_position(tmp_path: Path) -> None:
    vector = Vector(entries=["a", "b"])
    vector.add_observation({"a": 1, "b": 2})
    first = Scalar()
    first.add_observation(99)
    second = Scalar()
    second.add_observation(55)
    output = Gem5Parser.construct_final_csv(
        str(tmp_path), [{"v": vector, "s": first}, {"s": second}], ["v", "s"]
    )
    assert output is not None
    with Path(output).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows == [["v..a", "v..b", "s"], ["1.0", "2.0", "99.0"], ["NaN", "NaN", "55.0"]]


def test_final_csv_invalid_shape_preserves_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "results.csv"
    output.write_text("previous\nresult\n", encoding="utf-8")
    scalar = Scalar()
    scalar.add_observation(1)
    with pytest.raises(RuntimeError, match="inconsistent scalar/entry"):
        Gem5Parser.construct_final_csv(
            str(tmp_path), [{"h": scalar}, {"h": _histogram({"0-9": 3})}], ["h"]
        )
    assert output.read_text(encoding="utf-8") == "previous\nresult\n"


def test_literal_configuration_na_is_not_a_numeric_missing_sentinel(tmp_path: Path) -> None:
    from src.core.models.parsing_models import StatConfig
    from src.parsing.gem5.impl.source_bindings import resolve_sources
    from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
    from src.parsing.gem5.types.type_mapper import TypeMapper

    plan = resolve_sources(
        [
            StatConfig(
                "label",
                "configuration",
                params={"source_type": "configuration", "on_empty": "fallback"},
            ),
            StatConfig("number", "scalar", params={"source_type": "scalar"}),
        ],
        None,
    )
    stats = {spec.output_name: TypeMapper.create_stat(spec) for spec in plan.accumulators}
    worker = Gem5ParseWork("unused", stats, plan)
    worker._process_output("configuration/label/NA")
    output = Gem5Parser.construct_final_csv(str(tmp_path), [stats], ["label", "number"])
    assert output is not None
    with Path(output).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows == [["label", "number"], ["NA", "NaN"]]
