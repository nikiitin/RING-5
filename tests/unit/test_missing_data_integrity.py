"""Missing-data integrity (hard rule 6).

A requested numeric gem5 stat that is absent or incomplete in a stats file must
become NaN (the canonical ``MISSING_VALUE``) in the CSV — never a fabricated 0,
which a researcher could not distinguish from a genuine measured 0.
"""

import csv
from pathlib import Path

import pytest

from src.core.common.parsed_output_codec import MISSING_VALUE, render_parsed_value
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.parsing.gem5.types.scalar import Scalar


def _make_result(source: str, values: list[float], repeat: int) -> ParsedFileResult:
    scalar = Scalar(repeat=repeat)
    for value in values:
        scalar.add_observation(value)
    missing = scalar.missing_measurement_count
    scalar.balance_content()
    scalar.reduce_duplicates()
    return ParsedFileResult(
        source,
        (
            ParsedVariableResult(
                "ipc",
                "number",
                "scalar",
                (ParsedCell("ipc", "number", scalar.reduced_content),),
                missing,
            ),
        ),
    )


def _publish(tmp_path: Path, results: list[ParsedFileResult]) -> None:
    table = ParsedOutputIO.resolve(
        results, ["ipc"], tuple(result.source_path for result in results)
    )
    ParsedOutputIO.publish(tmp_path / "results.csv", table)


def _read_rows(tmp_path: Path) -> list[list[str]]:
    with (tmp_path / "results.csv").open(newline="") as f:
        return list(csv.reader(f))


class TestRenderValue:
    def test_untyped_none_is_rejected_before_publication(self) -> None:
        with pytest.raises(TypeError, match="exact float"):
            ParsedCell("ipc", "number", None)

    def test_nan_is_missing(self) -> None:
        assert render_parsed_value("number", float("nan")) == MISSING_VALUE

    @pytest.mark.parametrize("text", ["NA", "nan", "", "001"])
    def test_literal_configuration_text_is_preserved(self, text: str) -> None:
        assert render_parsed_value("text", text) == text

    def test_real_value_is_rendered(self) -> None:
        assert render_parsed_value("number", 3.5) == "3.5"
        assert render_parsed_value("number", 0.0) == "0.0"  # a genuine 0 is preserved, not hidden


class TestMissingScalarBecomesNaN:
    # [test->req~ring5.ingestion.parse-integrity~1]
    def test_absent_scalar_is_nan_not_zero(self, tmp_path: Path) -> None:
        # File A measured ipc; file B is missing it entirely.
        results = [
            _make_result("a", [2.0], repeat=1),
            _make_result("b", [], repeat=1),
        ]
        _publish(tmp_path, results)
        rows = _read_rows(tmp_path)
        assert rows[0] == ["ipc"]
        assert rows[1] == ["2.0"]
        assert rows[2] == [MISSING_VALUE]  # NaN, never "0"

    def test_incomplete_scalar_is_nan(self, tmp_path: Path) -> None:
        # Two dumps expected, only one present -> incomplete -> NaN.
        results = [_make_result("a", [2.0], repeat=2)]
        _publish(tmp_path, results)
        rows = _read_rows(tmp_path)
        assert rows[1] == [MISSING_VALUE]

    def test_genuine_zero_is_preserved(self, tmp_path: Path) -> None:
        # A measured 0 must stay 0 — only *missing* values become NaN.
        results = [_make_result("a", [0.0], repeat=1)]
        _publish(tmp_path, results)
        rows = _read_rows(tmp_path)
        assert rows[1] == ["0.0"]
