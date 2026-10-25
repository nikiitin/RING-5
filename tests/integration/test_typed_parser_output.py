"""Real worker, cache and preview contracts for the current typed parser output."""

from __future__ import annotations

import json
import math
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from src.core.models.parsed_output_models import ParsedFileResult
from src.core.models.parsing_models import PARSER_RESULT_VERSION, StatConfig
from src.core.common.parsed_output import ParsedOutputIO
from src.parsing.framework import incremental_cache
from src.parsing.framework.incremental_cache import CACHE_SCHEMA_VERSION, load_cache
from src.parsing.gem5.impl.gem5_parser import Gem5Parser

pytestmark = pytest.mark.xdist_group("perl_pool")


def _source(root: Path, name: str, token: str = "1.25", *, config: str | None = None) -> Path:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "stats.txt"
    path.write_text(f"simTicks {token}\n", encoding="utf-8")
    if config is not None:
        (directory / "config.ini").write_text(config, encoding="utf-8")
    return path


def _variables(literal: str) -> list[StatConfig]:
    return [
        StatConfig("value", "scalar", source_name="simTicks", params={"source_type": "scalar"}),
        StatConfig(
            "label", "configuration", params={"source_type": "configuration", "on_empty": literal}
        ),
    ]


def _collect(batch) -> list[ParsedFileResult]:
    return [future.result(timeout=15) for future in batch.futures]


@pytest.mark.parametrize(
    "literal",
    ["NA", "nan", "NaN", "", "001", "1e3", "μarch", "  whitespace  ", "95%", "1e400", "-1e-400"],
)
def test_real_worker_full_incremental_and_playground_share_exact_literal_semantics(
    tmp_path: Path, literal: str
) -> None:
    source = _source(tmp_path / "inputs", "run")
    variables = _variables(literal)
    full = Gem5Parser.submit_parse_async(
        str(source.parent), "stats.txt", variables, str(tmp_path / "full")
    )
    results = _collect(full)
    assert type(results[0]) is ParsedFileResult
    assert results[0].source_path == str(source)
    assert [(value.kind, value.shape) for value in results[0].variables] == [
        ("number", "scalar"),
        ("text", "scalar"),
    ]
    assert results[0].variables[1].cells[0].value == literal
    with pytest.raises(FrozenInstanceError):
        results[0].source_path = "changed"
    published = Gem5Parser.finalize_parsing(full, results)
    assert ParsedOutputIO.read(published).rows == ((1.25, literal),)
    assert ParsedOutputIO.read(published).missing_variables == ()
    incremental = Gem5Parser.submit_incremental_parse_async(
        str(source.parent), "stats.txt", variables, str(tmp_path / "incremental")
    )
    initial = Gem5Parser.finalize_incremental_parsing(incremental, _collect(incremental))
    assert initial.output.sha256 == published.sha256
    cached = Gem5Parser.submit_incremental_parse_async(
        str(source.parent), "stats.txt", variables, str(tmp_path / "incremental")
    )
    assert cached.futures == () and cached.reused_file_count == 1
    assert cached.cached_results[0].variables[1].cells[0].value == literal
    reused = Gem5Parser.finalize_incremental_parsing(cached, [])
    assert reused.output.sha256 == published.sha256
    preview = Gem5Parser.submit_parser_playground_async(
        str(source.parent), "stats.txt", variables, str(tmp_path / "preview")
    )
    result = Gem5Parser.finalize_parser_playground(preview, _collect(preview))
    assert result.rows == ((1.25, literal),)
    assert result.missing_variables == () and result.ready_for_full_parse
    assert not (tmp_path / "preview").exists()
    assert PARSER_RESULT_VERSION == 10 and CACHE_SCHEMA_VERSION == 2


@pytest.mark.parametrize("token", ["0", "-0.0", "1.25", "5e-324", "inf", "-inf", "NaN"])
def test_real_numeric_wire_retains_supported_float_boundaries(tmp_path: Path, token: str) -> None:
    source = _source(tmp_path / "inputs", "run", token)
    batch = Gem5Parser.submit_parse_async(
        str(source.parent), "stats.txt", _variables("001"), str(tmp_path / "out")
    )
    result = _collect(batch)[0]
    assert result.variables[0].missing_measurements == 0
    output = Gem5Parser.finalize_parsing(batch, [result])
    restored = ParsedOutputIO.read(output)
    value = restored.rows[0][0]
    expected = float(token)
    assert type(value) is float
    if math.isnan(expected):
        assert math.isnan(value)
        assert restored.missing_variables == ("value",)
    else:
        assert value == expected and restored.missing_variables == ()
        # The established population mean canonicalizes signed zero to +0.0;
        # transport retains measured zero as numeric and non-missing.


@pytest.mark.parametrize("token", ["1e400", "-1e400", "1e-400", "-1e-400", "2e-324"])
def test_real_numeric_wire_range_failure_happens_before_publication(
    tmp_path: Path, token: str
) -> None:
    source = _source(tmp_path / "inputs", "run", token)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    target = output_dir / "results.csv"
    target.write_bytes(b"old committed output")
    batch = Gem5Parser.submit_parse_async(
        str(source.parent), "stats.txt", _variables("1e400"), str(output_dir)
    )
    with pytest.raises(ValueError, match="Float64 range"):
        batch.futures[0].result(timeout=15)
    with pytest.raises(ValueError, match="non-empty"):
        Gem5Parser.finalize_parsing(batch, [])
    assert target.read_bytes() == b"old committed output"


def test_exact_source_plan_and_submission_context_remain_owned(tmp_path: Path) -> None:
    first_source = _source(tmp_path / "first", "run")
    second_source = _source(tmp_path / "second", "run", "2.5")
    first = Gem5Parser.submit_parse_async(
        str(first_source.parent), "stats.txt", _variables("NA"), str(tmp_path / "first-out")
    )
    second = Gem5Parser.submit_parse_async(
        str(second_source.parent), "stats.txt", _variables("001"), str(tmp_path / "second-out")
    )
    first_values, second_values = _collect(first), _collect(second)
    with pytest.raises(ValueError, match="Unplanned"):
        Gem5Parser.finalize_parsing(first, second_values)
    with pytest.raises(ValueError, match="Duplicate"):
        Gem5Parser.finalize_parsing(first, first_values * 2)
    one = Gem5Parser.finalize_parsing(first, first_values)
    two = Gem5Parser.finalize_parsing(second, second_values)
    assert Path(one.csv_path).parent.name == "first-out"
    assert Path(two.csv_path).parent.name == "second-out"
    assert ParsedOutputIO.read(one).rows == ((1.25, "NA"),)
    assert ParsedOutputIO.read(two).rows == ((2.5, "001"),)
    with pytest.raises(FrozenInstanceError):
        first.output_dir = "changed"


@pytest.mark.parametrize("mode", ["missing", "malformed", "collision"])
def test_config_aware_metadata_failure_is_a_future_failure_with_partial_row_ownership(
    tmp_path: Path, mode: str
) -> None:
    inputs = tmp_path / "inputs"
    _source(inputs, "good", config="[system]\nCaseSensitive = 95% μ\n")
    bad = _source(inputs, "bad", config="[system]\nCaseSensitive = good\n")
    variables = _variables("NA")
    if mode == "missing":
        (bad.parent / "config.ini").unlink()
    elif mode == "malformed":
        (bad.parent / "config.ini").write_text("not a valid ini", encoding="utf-8")
    else:
        variables[0] = replace(variables[0], name="sim_path")
    batch = Gem5Parser.submit_parse_async(
        str(inputs), "stats.txt", variables, str(tmp_path / "out"), "config_aware"
    )
    successful = []
    failed = []
    for future in batch.futures:
        try:
            successful.append(future.result(timeout=15))
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            failed.append(str(exc))
    assert len(failed) == (2 if mode == "collision" else 1)
    assert len(successful) == (0 if mode == "collision" else 1)
    if mode == "collision":
        assert all("collision" in message for message in failed)
        with pytest.raises(ValueError, match="non-empty"):
            Gem5Parser.finalize_parsing(batch, successful, complete=False)
    else:
        with pytest.raises(ValueError, match="every planned"):
            Gem5Parser.finalize_parsing(batch, successful)
        output = Gem5Parser.finalize_parsing(batch, successful, complete=False)
        frame = ParsedOutputIO.to_frame(output)
        assert frame["label"].tolist() == ["NA"]
        assert json.loads(frame["config_json"].iloc[0]) == {"system": {"CaseSensitive": "95% μ"}}


def test_incremental_partial_retains_typed_cached_rows_and_failed_cache_promotion_restores_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, output = tmp_path / "inputs", tmp_path / "out"
    cached_source = _source(inputs, "cached", "0")
    changed_source = _source(inputs, "changed", "1.25")
    failed_source = _source(inputs, "failed", "2.5")
    variables = _variables("")
    initial_batch = Gem5Parser.submit_incremental_parse_async(
        str(inputs), "stats.txt", variables, str(output)
    )
    initial = Gem5Parser.finalize_incremental_parsing(initial_batch, _collect(initial_batch))
    before_csv = Path(initial.csv_path).read_bytes()
    cache_path = Path(initial_batch.cache_path)
    before_cache = cache_path.read_bytes()
    changed_source.write_text("simTicks 3.75\n", encoding="utf-8")
    failed_source.write_text("simTicks=unsupported\n", encoding="utf-8")
    batch = Gem5Parser.submit_incremental_parse_async(
        str(inputs), "stats.txt", variables, str(output)
    )
    results = []
    for future in batch.futures:
        try:
            results.append(future.result(timeout=15))
        except RuntimeError:
            pass
    assert len(results) == 1 and batch.cached_results[0].source_path == str(cached_source)
    partial = Gem5Parser.finalize_incremental_parsing(batch, results, complete=False)
    assert ParsedOutputIO.to_frame(partial.output)["label"].tolist() == ["", ""]
    assert ParsedOutputIO.to_frame(partial.output)["value"].tolist() == [0.0, 3.75]
    assert (partial.parsed_files, partial.reused_files, partial.total_files) == (1, 1, 3)
    assert cache_path.read_bytes() == before_cache
    partial_bytes = Path(partial.csv_path).read_bytes()
    with pytest.raises(ValueError, match="every planned"):
        Gem5Parser.finalize_incremental_parsing(batch, results)
    assert (
        Path(partial.csv_path).read_bytes() == partial_bytes
        and cache_path.read_bytes() == before_cache
    )
    failed_source.write_text("simTicks 2.5\n", encoding="utf-8")
    complete = Gem5Parser.submit_incremental_parse_async(
        str(inputs), "stats.txt", variables, str(output)
    )
    values = _collect(complete)

    original_replace = incremental_cache.os.replace

    def fail_cache(source, target):
        if Path(target) == cache_path:
            raise OSError("injected cache promotion failure")
        return original_replace(source, target)

    monkeypatch.setattr(incremental_cache.os, "replace", fail_cache)
    with pytest.raises(OSError, match="cache promotion"):
        Gem5Parser.finalize_incremental_parsing(complete, values)
    assert Path(partial.csv_path).read_bytes() == partial_bytes
    assert cache_path.read_bytes() == before_cache
    assert before_csv != partial_bytes
    names, records = load_cache(cache_path, initial_batch.configuration_hash)
    assert names == ("value", "label")
    assert records[str(cached_source)][1].variables[1].cells[0].value == ""
    assert not list(output.glob("*.tmp")) and not list(output.glob(".parsed-old-*"))


def test_entry_workers_reduce_before_future_and_keep_absent_histogram_schema_empty(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    absent = _source(inputs, "absent")
    present = _source(inputs, "present")
    present.write_text(
        "simTicks 1.25\nv::a 0\nv::b 2.5\n"
        "d::underflows 0 0% 0%\nd::0 1 33% 33%\nd::1 2 67% 100%\nd::overflows 0 0% 100%\n"
        "d::underflows 0 0% 0%\nd::0 2 40% 40%\nd::1 3 60% 100%\nd::overflows 0 0% 100%\n"
        "h::0-9 1 100% 100%\nh::0-9 2 100% 100%\n",
        encoding="utf-8",
    )
    variables = [
        StatConfig(
            "V", "vector", source_name="v", params={"source_type": "vector", "entries": ["a", "b"]}
        ),
        StatConfig(
            "D",
            "distribution",
            repeat=2,
            source_name="d",
            params={"source_type": "distribution", "minimum": 0, "maximum": 1},
        ),
        StatConfig(
            "H", "histogram", repeat=2, source_name="h", params={"source_type": "histogram"}
        ),
    ]
    batch = Gem5Parser.submit_parse_async(
        str(inputs), "stats.txt", variables, str(tmp_path / "out")
    )
    results = _collect(batch)
    by_source = {result.source_path: result for result in results}
    assert by_source[str(absent)].variables[2].cells == ()
    assert by_source[str(present)].variables[0].cells[0].value == 0.0
    assert by_source[str(present)].variables[0].cells[1].value == 2.5
    assert [cell.value for cell in by_source[str(present)].variables[1].cells] == [
        0.0,
        1.5,
        2.5,
        0.0,
    ]
    assert by_source[str(present)].variables[2].cells[0].value == 1.5
    assert all(
        variable.shape == "entries" and variable.kind == "number"
        for variable in by_source[str(present)].variables
    )
    output = Gem5Parser.finalize_parsing(batch, results)
    frame = ParsedOutputIO.to_frame(output)
    assert list(frame.columns) == [
        "V..a",
        "V..b",
        "D..underflows",
        "D..0",
        "D..1",
        "D..overflows",
        "H..0-9",
    ]
    assert math.isnan(frame["H..0-9"].iloc[0]) and frame["H..0-9"].iloc[1] == 1.5
    zero_batch = Gem5Parser.submit_parse_async(
        str(absent.parent), "stats.txt", [variables[2]], str(tmp_path / "zero")
    )
    zero_output = Gem5Parser.finalize_parsing(zero_batch, _collect(zero_batch))
    assert zero_output.schema.columns == ()
    assert ParsedOutputIO.to_frame(zero_output).shape == (1, 0)
    assert ParsedOutputIO.read(zero_output).missing_variables == ("H",)


@pytest.mark.parametrize("literal", ["NA", "nan", "001", "1e400", "-1e-400"])
def test_real_observed_configuration_is_text_before_any_numeric_wire_conversion(
    tmp_path: Path, literal: str
) -> None:
    source = _source(tmp_path / "inputs", "run")
    source.write_text(f"simTicks 1.25\nlabel={literal}\n", encoding="utf-8")
    batch = Gem5Parser.submit_parse_async(
        str(source.parent), "stats.txt", _variables("unused fallback"), str(tmp_path / "out")
    )
    values = _collect(batch)
    assert values[0].variables[1].cells[0].value == literal
    output = Gem5Parser.finalize_parsing(batch, values)
    assert ParsedOutputIO.read(output).rows == ((1.25, literal),)
    assert ParsedOutputIO.read(output).missing_variables == ()


@pytest.mark.parametrize("token", ["1e400", "1e-400"])
def test_real_entry_tokens_use_the_same_numeric_range_guard(tmp_path: Path, token: str) -> None:
    source = _source(tmp_path / "inputs", "run")
    source.write_text(f"v::a {token}\n", encoding="utf-8")
    variables = [StatConfig("v", "vector", params={"source_type": "vector", "entries": ["a"]})]
    batch = Gem5Parser.submit_parse_async(
        str(source.parent), "stats.txt", variables, str(tmp_path / "out")
    )
    with pytest.raises(ValueError, match="Float64 range"):
        batch.futures[0].result(timeout=15)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("literal", ["001", "1e400", "-1e-400"])
def test_explicit_text_output_from_scalar_source_keeps_literal_token(
    tmp_path: Path, literal: str
) -> None:
    source = _source(tmp_path / "inputs", "run", literal)
    variables = [
        StatConfig(
            "label",
            "configuration",
            source_name="simTicks",
            params={"source_type": "scalar", "on_empty": "fallback"},
        )
    ]
    batch = Gem5Parser.submit_parse_async(
        str(source.parent), "stats.txt", variables, str(tmp_path / "out")
    )
    values = _collect(batch)
    assert values[0].variables[0].kind == "text"
    assert values[0].variables[0].cells[0].value == literal
    output = Gem5Parser.finalize_parsing(batch, values)
    assert ParsedOutputIO.read(output).rows == ((literal,),)
