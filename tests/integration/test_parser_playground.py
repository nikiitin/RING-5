"""End-to-end contracts for the bounded parser configuration playground."""

from __future__ import annotations

from pathlib import Path

import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("perl_pool")]


def _write_runs(root: Path, count: int = 5) -> tuple[Path, ...]:
    sources: list[Path] = []
    for index in range(count):
        run = root / f"run-{index:02d}"
        run.mkdir(parents=True)
        source = run / "gem5_stats.preview"
        source.write_text(f"simTicks {100 + index} # ticks\n", encoding="utf-8")
        (run / "config.ini").write_text(f"[run]\nindex = {index}\n", encoding="utf-8")
        sources.append(source)
    return tuple(sources)


def test_playground_uses_real_parser_on_lexical_sample_without_loading_data(
    tmp_path: Path,
) -> None:
    # [test->req~ring5.ingestion.parser-playground~1]
    inputs = tmp_path / "inputs"
    sources = _write_runs(inputs)
    with ring5.Session() as session:
        assert session.api.state_manager.get_data() is None
        job = session.parser_playground_submit(
            str(inputs),
            ["simTicks"],
            pattern="gem5_stats.*",
            strategy="config_aware",
            scan_limit=0,
        )
        output = Path(job.output_dir)
        assert len(job.futures) == 3
        result = job.finalize()

        assert result.matched_file_count == 5
        assert result.sampled_files == tuple(str(source.resolve()) for source in sources[:3])
        assert result.columns == ("simTicks", "config_json", "sim_path")
        assert result.rows == tuple(
            (
                f"{100 + index}.0",
                f'{{"run":{{"index":"{index}"}}}}',
                str(source.resolve()),
            )
            for index, source in enumerate(sources[:3])
        )
        assert result.missing_variables == ()
        assert result.ready_for_full_parse
        assert "Previewed 3 of 5 matching files" in " ".join(result.diagnostics)
        assert session.api.state_manager.get_data() is None

        assert output.is_dir()
        assert list(output.iterdir()) == []

    assert not output.exists()


def test_playground_surfaces_variables_without_sampled_values(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.parser-playground~1]
    inputs = tmp_path / "inputs"
    _write_runs(inputs, count=1)

    with ring5.Session() as session:
        job = session.parser_playground_submit(
            str(inputs),
            [ring5.StatConfig(name="misspelledTicks", type="scalar")],
            pattern="gem5_stats.*",
            output_dir=str(tmp_path / "preview"),
            scan_limit=0,
        )
        result = job.finalize()

    assert result.rows == (("NaN",),)
    assert result.missing_variables == ("misspelledTicks",)
    assert not result.ready_for_full_parse
    assert "No sampled value was produced for: misspelledTicks." in result.diagnostics


def test_playground_expands_a_scanned_statistic_pattern(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.parser-playground~1]
    inputs = tmp_path / "inputs"
    source = _write_runs(inputs, count=1)[0]
    source.write_text(
        "system.cpu0.ipc 1.5 # ipc\nsystem.cpu1.ipc 2.5 # ipc\n",
        encoding="utf-8",
    )

    with ring5.Session() as session:
        scan = session.scan(str(inputs), pattern="gem5_stats.*", limit=0)
        pattern = next(variable for variable in scan.variables if r"\d+" in variable.name)
        result = session.parser_playground_submit(
            str(inputs),
            [pattern.name],
            pattern="gem5_stats.*",
            output_dir=str(tmp_path / "preview"),
            scan_limit=0,
        ).finalize()

    assert result.missing_variables == ()
    assert result.ready_for_full_parse
    assert result.columns == (
        r"system.cpu\d+.ipc..0",
        r"system.cpu\d+.ipc..1",
    )
    assert result.rows == (("1.5", "2.5"),)


def test_playground_rejects_an_empty_variable_selection(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    _write_runs(inputs, count=1)

    with ring5.Session() as session:
        with pytest.raises(ring5.ParseError, match="add at least one variable"):
            session.parser_playground_submit(
                str(inputs),
                [],
                pattern="gem5_stats.*",
                scan_limit=0,
            )


def test_playground_rejects_more_than_its_reviewable_variable_limit(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    _write_runs(inputs, count=1)
    variables = [ring5.StatConfig(name=f"stat{index}", type="scalar") for index in range(65)]

    with ring5.Session() as session:
        with pytest.raises(ring5.ParseError, match="at most 64 variables"):
            session.parser_playground_submit(
                str(inputs),
                variables,
                pattern="gem5_stats.*",
                output_dir=str(tmp_path / "preview"),
                scan_limit=0,
            )
