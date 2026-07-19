"""Missing-data integrity (hard rule 6).

A requested numeric gem5 stat that is absent or incomplete in a stats file must
become NaN (the canonical ``MISSING_VALUE``) in the CSV — never a fabricated 0,
which a researcher could not distinguish from a genuine measured 0.
"""

import csv
from pathlib import Path

from src.core.models.csv_contract import MISSING_VALUE
from src.parsing.gem5.impl.gem5_parser import Gem5Parser, _render_value
from src.parsing.gem5.types.scalar import Scalar


def _make_scalar(values: list[float], repeat: int) -> Scalar:
    s = Scalar(repeat=repeat)
    for v in values:
        s.content = v
    return s


def _read_rows(tmp_path: Path) -> list[list[str]]:
    with (tmp_path / "results.csv").open(newline="") as f:
        return list(csv.reader(f))


class TestRenderValue:
    def test_none_is_missing(self) -> None:
        assert _render_value(None) == MISSING_VALUE

    def test_nan_is_missing(self) -> None:
        assert _render_value(float("nan")) == MISSING_VALUE

    def test_legacy_na_sentinel_is_missing(self) -> None:
        assert _render_value("NA") == MISSING_VALUE

    def test_real_value_is_rendered(self) -> None:
        assert _render_value(3.5) == "3.5"
        assert _render_value(0.0) == "0.0"  # a genuine 0 is preserved, not hidden


class TestMissingScalarBecomesNaN:
    # [test->req~ring5.ingestion.parse-integrity~1]
    def test_absent_scalar_is_nan_not_zero(self, tmp_path: Path) -> None:
        # File A measured ipc; file B is missing it entirely.
        results = [
            {"ipc": _make_scalar([2.0], repeat=1)},
            {"ipc": _make_scalar([], repeat=1)},
        ]
        Gem5Parser.construct_final_csv(str(tmp_path), results, var_names=["ipc"])
        rows = _read_rows(tmp_path)
        assert rows[0] == ["ipc"]
        assert rows[1] == ["2.0"]
        assert rows[2] == [MISSING_VALUE]  # NaN, never "0"

    def test_incomplete_scalar_is_nan(self, tmp_path: Path) -> None:
        # Two dumps expected, only one present -> incomplete -> NaN.
        results = [{"ipc": _make_scalar([2.0], repeat=2)}]
        Gem5Parser.construct_final_csv(str(tmp_path), results, var_names=["ipc"])
        rows = _read_rows(tmp_path)
        assert rows[1] == [MISSING_VALUE]

    def test_genuine_zero_is_preserved(self, tmp_path: Path) -> None:
        # A measured 0 must stay 0 — only *missing* values become NaN.
        results = [{"ipc": _make_scalar([0.0], repeat=1)}]
        Gem5Parser.construct_final_csv(str(tmp_path), results, var_names=["ipc"])
        rows = _read_rows(tmp_path)
        assert rows[1] == ["0.0"]
