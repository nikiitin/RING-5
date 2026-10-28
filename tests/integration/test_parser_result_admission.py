"""Real parser batches admit dynamic and cached values before Future retention."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.common import parsed_output
from src.core.common.parsed_output import ParsedOutputIO
from src.core.common.parsed_output_codec import iter_parsed_file_encoding
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.core.models.parsing_models import StatConfig
from src.parsing.framework import result_admission
from src.core.models.parse_failure_models import ResultAdmissionError
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl import source_bindings

pytestmark = pytest.mark.xdist_group("perl_pool")


def _write(root: Path, name: str, body: str) -> Path:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "stats.txt"
    source.write_text(body, encoding="utf-8")
    return source


def _collect(batch):
    accepted, errors = [], []
    for future in batch.futures:
        try:
            accepted.append(future.result(timeout=15))
        except ResultAdmissionError as exc:
            errors.append(str(exc))
    return accepted, errors


@pytest.mark.parametrize("mode", ["full", "playground"])
def test_real_dynamic_histogram_results_are_bounded_before_futures_retain_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    inputs = tmp_path / "inputs"
    for index in range(3):
        _write(
            inputs, f"run{index}", f"h::0-9 {index + 1} 50% 50%\nh::10-19 {index + 1} 50% 100%\n"
        )
    output = tmp_path / "out"
    output.mkdir()
    target = output / "results.csv"
    target.write_bytes(b"previous committed output")
    monkeypatch.setattr(source_bindings, "MAX_PARSE_MATRIX_CELLS", 3)
    monkeypatch.setattr(result_admission, "MAX_PARSE_MATRIX_CELLS", 3)
    monkeypatch.setattr(parsed_output, "MAX_PARSE_MATRIX_CELLS", 3)
    variables = [StatConfig("h", "histogram", params={"source_type": "histogram"})]
    submit = (
        Gem5Parser.submit_parse_async
        if mode == "full"
        else Gem5Parser.submit_parser_playground_async
    )
    batch = submit(str(inputs), "stats.txt", variables, str(output))
    accepted, errors = _collect(batch)
    assert len(accepted) == 1 and len(errors) == 2
    assert sum(len(variable.cells) for value in accepted for variable in value.variables) == 2
    assert all("cell admission limit" in error for error in errors)
    with pytest.raises(ValueError, match="every planned"):
        if mode == "full":
            Gem5Parser.finalize_parsing(batch, accepted)
        else:
            Gem5Parser.finalize_parser_playground(batch, accepted)
    assert target.read_bytes() == b"previous committed output"
    if mode == "full":
        partial = Gem5Parser.finalize_parsing(batch, accepted, complete=False)
        expected = tuple(
            cell.value for variable in accepted[0].variables for cell in variable.cells
        )
        assert ParsedOutputIO.read(partial).rows == (expected,)


def test_incremental_cached_and_changed_results_share_the_same_quota(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, output = tmp_path / "inputs", tmp_path / "out"
    sources = [
        _write(inputs, name, f"h::0-9 {index + 1} 100% 100%\n")
        for index, name in enumerate(("a", "b", "c"))
    ]
    variables = [StatConfig("h", "histogram", params={"source_type": "histogram"})]
    initial = Gem5Parser.submit_incremental_parse_async(
        str(inputs), "stats.txt", variables, str(output)
    )
    initial_values = [future.result(timeout=15) for future in initial.futures]
    published = Gem5Parser.finalize_incremental_parsing(initial, initial_values)
    before_cache = Path(initial.cache_path).read_bytes()
    before_csv = Path(published.csv_path).read_bytes()
    sources[2].write_text("h::0-9 3 50% 50%\nh::10-19 4 50% 100%\n", encoding="utf-8")
    monkeypatch.setattr(source_bindings, "MAX_PARSE_MATRIX_CELLS", 3)
    monkeypatch.setattr(result_admission, "MAX_PARSE_MATRIX_CELLS", 3)
    monkeypatch.setattr(parsed_output, "MAX_PARSE_MATRIX_CELLS", 3)
    batch = Gem5Parser.submit_incremental_parse_async(
        str(inputs), "stats.txt", variables, str(output)
    )
    accepted, errors = _collect(batch)
    assert len(batch.cached_results) == 2 and accepted == [] and len(errors) == 1
    assert Path(published.csv_path).read_bytes() == before_csv
    partial = Gem5Parser.finalize_incremental_parsing(batch, [], complete=False)
    assert (partial.parsed_files, partial.reused_files, partial.total_files) == (0, 2, 3)
    assert ParsedOutputIO.read(partial.output).rows == ((1.0,), (2.0,))
    assert Path(initial.cache_path).read_bytes() == before_cache
    with pytest.raises(ValueError, match="every planned"):
        Gem5Parser.finalize_incremental_parsing(batch, [])


def test_config_aware_text_is_charged_to_aggregate_record_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = tmp_path / "inputs"
    sources = [_write(inputs, name, "simTicks 1.25\n") for name in ("a", "b")]
    text = "z" * 1000 + " μ 95%"
    for source in sources:
        (source.parent / "config.ini").write_text(f"[system]\nPayload={text}\n", encoding="utf-8")
    metadata = json.dumps({"system": {"Payload": text}}, sort_keys=True, separators=(",", ":"))
    value = ParsedVariableResult(
        "v", "number", "scalar", (ParsedCell("v", "number", 1.25),), layout=None
    )
    expected = ParsedFileResult(
        str(sources[0]),
        (value,),
        (
            ParsedCell("sim_path", "text", str(sources[0])),
            ParsedCell("config_json", "text", metadata),
        ),
    )
    quota = len(b"".join(iter_parsed_file_encoding(expected)))
    monkeypatch.setattr(result_admission, "MAX_PARSE_RESULT_BYTES", quota)
    variables = [
        StatConfig("v", "scalar", source_name="simTicks", params={"source_type": "scalar"})
    ]
    batch = Gem5Parser.submit_parse_async(
        str(inputs), "stats.txt", variables, str(tmp_path / "out"), "config_aware"
    )
    accepted, errors = _collect(batch)
    assert len(accepted) == len(errors) == 1
    assert "retained-record admission limit" in errors[0]
    assert sum(len(b"".join(iter_parsed_file_encoding(value))) for value in accepted) == quota
    assert json.loads(accepted[0].metadata[1].value) == {"system": {"Payload": text}}


def test_preview_reads_shared_configuration_alias_without_hypothetical_publication(
    tmp_path: Path,
) -> None:
    source = _write(tmp_path / "inputs", "run", "simTicks 1.25\n")
    output = tmp_path / "out"
    output.mkdir()
    target = output / "results.csv"
    target.write_text("[system]\nCase=read only\n", encoding="utf-8")
    (source.parent / "config.ini").symlink_to(target)
    variables = [
        StatConfig("v", "scalar", source_name="simTicks", params={"source_type": "scalar"})
    ]
    batch = Gem5Parser.submit_parser_playground_async(
        str(source.parent), "stats.txt", variables, str(output), "config_aware"
    )
    result = Gem5Parser.finalize_parser_playground(
        batch, [future.result(timeout=15) for future in batch.futures]
    )
    assert result.rows[0][0] == 1.25
    assert json.loads(result.rows[0][1]) == {"system": {"Case": "read only"}}
    assert target.read_text(encoding="utf-8") == "[system]\nCase=read only\n"
    assert list(output.iterdir()) == [target]


def test_preview_source_ids_match_work_when_selected_stats_root_is_a_symlink(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    source = _write(real, "run", "simTicks 1.25\n")
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    variables = [
        StatConfig("v", "scalar", source_name="simTicks", params={"source_type": "scalar"})
    ]
    batch = Gem5Parser.submit_parser_playground_async(
        str(alias), "stats.txt", variables, str(tmp_path / "preview")
    )
    result = Gem5Parser.finalize_parser_playground(
        batch, [future.result(timeout=15) for future in batch.futures]
    )
    assert batch.sampled_files == result.sampled_files == (str(source.resolve()),)
    assert result.rows == ((1.25,),)
