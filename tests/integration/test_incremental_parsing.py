"""End-to-end contract for content-addressed incremental simulator parsing."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("perl_pool")]


def _write_run(root: Path, name: str, ticks: int) -> Path:
    run = root / name
    run.mkdir(parents=True, exist_ok=True)
    (run / "stats.txt").write_text(f"simTicks {ticks} # ticks\n", encoding="utf-8")
    return run / "stats.txt"


def test_incremental_parse_reuses_updates_and_removes_exact_source_rows(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.incremental-parsing~1]
    inputs = tmp_path / "inputs"
    first_source = _write_run(inputs, "run-a", 100)
    second_source = _write_run(inputs, "run-b", 200)
    output = tmp_path / "output"

    with ring5.Session() as session:
        initial = session.parse(
            str(inputs),
            ["simTicks"],
            output_dir=str(output),
            scan_limit=0,
            incremental=True,
        )
        assert (initial.parsed_files, initial.reused_files, initial.removed_files) == (2, 0, 0)
        assert sorted(pd.read_csv(initial.csv_path)["simTicks"].tolist()) == [100, 200]
        initial_csv = Path(initial.csv_path).read_bytes()
        initial_cache = (output / ".ring5-incremental-parse.json").read_bytes()

        unchanged = session.parse(
            str(inputs),
            ["simTicks"],
            output_dir=str(output),
            scan_limit=0,
            incremental=True,
        )
        assert (unchanged.parsed_files, unchanged.reused_files, unchanged.removed_files) == (
            0,
            2,
            0,
        )
        assert Path(unchanged.csv_path).read_bytes() == initial_csv
        assert (output / ".ring5-incremental-parse.json").read_bytes() == initial_cache

        second_source.write_text("simTicks 250 # ticks\n", encoding="utf-8")
        updated = session.parse(
            str(inputs),
            ["simTicks"],
            output_dir=str(output),
            scan_limit=0,
            incremental=True,
        )
        assert (updated.parsed_files, updated.reused_files, updated.removed_files) == (1, 1, 0)
        assert sorted(pd.read_csv(updated.csv_path)["simTicks"].tolist()) == [100, 250]

        first_source.unlink()
        removed = session.parse(
            str(inputs),
            ["simTicks"],
            output_dir=str(output),
            scan_limit=0,
            incremental=True,
        )
        assert (removed.parsed_files, removed.reused_files, removed.removed_files) == (0, 1, 1)
        assert pd.read_csv(removed.csv_path)["simTicks"].tolist() == [250]

    cache = output / ".ring5-incremental-parse.json"
    assert cache.is_file()
    assert "simTicks" in cache.read_text(encoding="utf-8")


def test_incremental_finalize_rejects_a_source_changed_after_submission(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    source = _write_run(inputs, "run", 100)
    output = tmp_path / "output"

    with ring5.Session() as session:
        job = session.parse_submit(
            str(inputs),
            ["simTicks"],
            output_dir=str(output),
            scan_limit=0,
            incremental=True,
        )
        source.write_text("simTicks 200 # changed while parsing\n", encoding="utf-8")
        with pytest.raises(ring5.ParseError, match="changed during incremental parsing"):
            job.finalize()

    assert not (output / ".ring5-incremental-parse.json").exists()


def test_incremental_cache_cannot_replace_output_or_simulator_input(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    source = _write_run(inputs, "run", 100)
    output = tmp_path / "output"

    with ring5.Session() as session:
        for protected_path in (output / "results.csv", source):
            with pytest.raises(ring5.ParseError, match="must not replace"):
                session.parse_submit(
                    str(inputs),
                    ["simTicks"],
                    output_dir=str(output),
                    scan_limit=0,
                    incremental=True,
                    cache_path=str(protected_path),
                )

    assert source.read_text(encoding="utf-8") == "simTicks 100 # ticks\n"
