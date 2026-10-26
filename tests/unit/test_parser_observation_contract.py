"""Missingness, histogram interval and CSV shape regression contracts."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.types.distribution import Distribution
from src.parsing.gem5.types.histogram import Histogram


@pytest.mark.parametrize(
    "stat",
    [
        Distribution(minimum=0, maximum=1, bucket_size=1, zero_policy="missing"),
        Histogram(bins=2, max_range=10),
    ],
)
def test_absent_frequency_stat_remains_nan(stat: Distribution | Histogram) -> None:
    stat.balance_content()
    stat.reduce_duplicates()
    assert all(math.isnan(value) for value in stat.reduced_content.values())


def test_observed_distribution_omits_only_zero_frequency_bins() -> None:
    stat = Distribution(
        minimum=0, maximum=2, statistics=["mean"], bucket_size=1, zero_policy="nozero"
    )
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


def test_final_csv_union_is_order_independent_and_keeps_absent_first_histogram(
    tmp_path: Path,
) -> None:
    schemas = []
    for reverse in (False, True):
        rows = [
            ParsedFileResult(
                "a", (ParsedVariableResult("h", "number", "entries", (), layout=None),)
            ),
            ParsedFileResult(
                "b",
                (
                    ParsedVariableResult(
                        "h",
                        "number",
                        "entries",
                        (ParsedCell("h..0-9", "number", 9.0),),
                        layout=None,
                    ),
                ),
            ),
            ParsedFileResult(
                "c",
                (
                    ParsedVariableResult(
                        "h",
                        "number",
                        "entries",
                        (ParsedCell("h..0-19", "number", 12.0),),
                        layout=None,
                    ),
                ),
            ),
        ]
        output = ParsedOutputIO.publish(
            tmp_path / "results.csv",
            ParsedOutputIO.resolve(rows[::-1] if reverse else rows, ["h"], ("a", "b", "c")),
        )
        assert output is not None
        with Path(output.csv_path).open(newline="", encoding="utf-8") as stream:
            parsed = list(csv.reader(stream))
        schemas.append(parsed[0])
        assert all(len(row) == 2 for row in parsed)
        assert sorted(parsed[1:]) == sorted([["NaN", "NaN"], ["NaN", "9.0"], ["12.0", "NaN"]])
    assert schemas == [["h..0-19", "h..0-9"]] * 2


def test_final_csv_missing_vector_preserves_following_scalar_position(tmp_path: Path) -> None:
    results = [
        ParsedFileResult(
            "a",
            (
                ParsedVariableResult(
                    "v",
                    "number",
                    "entries",
                    (ParsedCell("v..a", "number", 1.0), ParsedCell("v..b", "number", 2.0)),
                    layout=None,
                ),
                ParsedVariableResult(
                    "s", "number", "scalar", (ParsedCell("s", "number", 99.0),), layout=None
                ),
            ),
        ),
        ParsedFileResult(
            "b",
            (
                ParsedVariableResult("v", "number", "entries", (), layout=None),
                ParsedVariableResult(
                    "s", "number", "scalar", (ParsedCell("s", "number", 55.0),), layout=None
                ),
            ),
        ),
    ]
    output = ParsedOutputIO.publish(
        tmp_path / "results.csv", ParsedOutputIO.resolve(results, ["v", "s"], ("a", "b"))
    )
    assert output is not None
    with Path(output.csv_path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows == [["v..a", "v..b", "s"], ["1.0", "2.0", "99.0"], ["NaN", "NaN", "55.0"]]


def test_final_csv_invalid_shape_preserves_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "results.csv"
    output.write_text("previous\nresult\n", encoding="utf-8")
    results = [
        ParsedFileResult(
            "a",
            (
                ParsedVariableResult(
                    "h", "number", "scalar", (ParsedCell("h", "number", 1.0),), layout=None
                ),
            ),
        ),
        ParsedFileResult(
            "b",
            (
                ParsedVariableResult(
                    "h", "number", "entries", (ParsedCell("h..0-9", "number", 3.0),), layout=None
                ),
            ),
        ),
    ]
    with pytest.raises(ValueError, match="Conflicting declaration"):
        ParsedOutputIO.publish(output, ParsedOutputIO.resolve(results, ["h"], ("a", "b")))
    assert output.read_text(encoding="utf-8") == "previous\nresult\n"


def test_literal_configuration_na_is_not_a_numeric_missing_sentinel(tmp_path: Path) -> None:
    from src.core.models.parsing_models import StatConfig

    (tmp_path / "stats.txt").write_text("label=NA\n", encoding="utf-8")
    batch = Gem5Parser.submit_parse_async(
        str(tmp_path),
        "stats.txt",
        [
            StatConfig(
                "label",
                "configuration",
                params={"source_type": "configuration", "on_empty": "fallback"},
            ),
            StatConfig("number", "scalar", params={"source_type": "scalar"}),
        ],
        str(tmp_path / "output"),
    )
    output = Gem5Parser.finalize_parsing(
        batch, [future.result(timeout=30) for future in batch.futures]
    )
    assert output is not None
    with Path(output.csv_path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows == [["label", "number"], ["NA", "NaN"]]
