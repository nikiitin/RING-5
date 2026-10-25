"""Strict typed result, immutable plan and current-only cache admission contracts."""

from __future__ import annotations

import json
import math
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path

import pytest

from src.core.common.parsed_output_codec import parsed_file_from_payload, parsed_file_payload
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.core.models.parsing_models import (
    ParseBatchResult,
    ParserPlaygroundBatchResult,
    ParserPlaygroundResult,
)
from src.core.common.parsed_output import ParsedOutputIO
from src.parsing.framework import incremental_cache
from src.parsing.framework.incremental_cache import encode_cache, load_cache, write_cache


def _result(source: str = "source", *, absent: int = 0) -> ParsedFileResult:
    return ParsedFileResult(
        source,
        (
            ParsedVariableResult(
                "number", "number", "scalar", (ParsedCell("number", "number", math.nan),), absent
            ),
            ParsedVariableResult("label", "text", "scalar", (ParsedCell("label", "text", "NA"),)),
        ),
        (ParsedCell("sim_path", "text", source),),
    )


@pytest.mark.parametrize("absence", [0, 1])
def test_typed_file_cache_keeps_actual_absence_separate_from_numeric_nan(absence: int) -> None:
    value = _result(absent=absence)
    payload = parsed_file_payload(value)
    restored = parsed_file_from_payload(payload)
    assert restored.source_path == value.source_path
    assert restored.variables[0].missing_measurements == absence
    assert math.isnan(restored.variables[0].cells[0].value)
    assert restored.variables[1].cells[0].value == "NA"
    assert restored.metadata == value.metadata
    assert ParsedOutputIO.resolve(
        [restored], ["number", "label"], ["source"]
    ).missing_variables == ("number",)
    assert payload["variables"][0]["cells"][0]["value"] == "NaN"


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "shape",
        "kind",
        "raw_number",
        "owner_collision",
        "missing_count",
        "metadata_missing",
    ],
)
def test_file_payload_requires_exact_current_typed_fields(mutation: str) -> None:
    payload = parsed_file_payload(_result())
    if mutation == "extra":
        payload["legacy"] = True
    elif mutation == "shape":
        del payload["variables"][0]["shape"]
    elif mutation == "kind":
        payload["variables"][0]["kind"] = "scalar"
    elif mutation == "raw_number":
        payload["variables"][0]["cells"][0]["value"] = 1.0
    elif mutation == "owner_collision":
        payload["metadata"][0]["column"] = "number"
    elif mutation == "missing_count":
        payload["variables"][0]["missing_measurements"] = True
    else:
        del payload["metadata"]
    with pytest.raises((TypeError, ValueError)):
        parsed_file_from_payload(payload)


def test_full_batch_requires_owned_complete_context() -> None:
    future: Future[ParsedFileResult] = Future()
    batch = ParseBatchResult((future,), ("number", "label"), ("source",), "out", "simple")
    assert batch.futures == (future,) and batch.source_paths == ("source",)
    assert (
        replace(batch, strategy_type="external_backend_strategy").strategy_type
        == "external_backend_strategy"
    )
    with pytest.raises(TypeError, match="immutable tuple"):
        replace(batch, source_paths=["source"])
    with pytest.raises(ValueError, match="unique"):
        replace(batch, source_paths=("source", "source"))
    with pytest.raises(ValueError, match="worker source count"):
        replace(batch, futures=())
    with pytest.raises(ValueError, match="output_dir"):
        replace(batch, output_dir="")
    with pytest.raises(TypeError, match="Future"):
        replace(batch, futures=({},))


def test_resolver_requires_planned_provenance_even_for_partial_output() -> None:
    result = _result()
    with pytest.raises(ValueError, match="every planned"):
        ParsedOutputIO.resolve([result], ["number", "label"], ["source", "other"])
    table = ParsedOutputIO.resolve(
        [result], ["number", "label"], ["source", "other"], complete=False
    )
    assert table.source_paths == ("source",)
    with pytest.raises(ValueError, match="Unplanned"):
        ParsedOutputIO.resolve([result], ["number", "label"], ["other"], complete=False)
    with pytest.raises(ValueError, match="Duplicate"):
        ParsedOutputIO.resolve([result, result], ["number", "label"], ["source"], complete=False)
    with pytest.raises(ValueError, match="non-empty"):
        ParsedOutputIO.resolve([], ["number", "label"], ["source"], complete=False)
    with pytest.raises(TypeError, match="boolean"):
        ParsedOutputIO.resolve([result], ["number", "label"], ["source"], complete=1)


def test_current_cache_reloads_literal_values_and_rejects_retired_or_unknown_fields(
    tmp_path: Path,
) -> None:
    path = tmp_path / "cache.json"
    digest = "a" * 64
    encoded = encode_cache(
        digest, ("number", "label"), (("source", "b" * 64),), [_result(absent=1)]
    )
    write_cache(path, encoded)
    names, records = load_cache(path, digest)
    assert names == ("number", "label") and tuple(records) == ("source",)
    assert records["source"][0] == "b" * 64
    assert records["source"][1].variables[0].missing_measurements == 1
    assert records["source"][1].variables[1].cells[0].value == "NA"
    current = json.loads(encoded)
    for invalid in ({**current, "schema_version": 1}, {**current, "old_cells": []}):
        path.write_text(json.dumps(invalid), encoding="utf-8")
        assert load_cache(path, digest) == ((), {})
    path.write_text('{"schema_version":2,"schema_version":2}', encoding="utf-8")
    assert load_cache(path, digest) == ((), {})


def test_cache_preparation_budget_rejects_before_filesystem_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(incremental_cache, "MAX_INCREMENTAL_CACHE_BYTES", 40)
    with pytest.raises(ValueError, match="byte limit"):
        encode_cache("a" * 64, ("number", "label"), (("source", "b" * 64),), [_result()])
    assert list(tmp_path.iterdir()) == []


def test_preview_owns_only_exact_typed_immutable_cells() -> None:
    preview = ParserPlaygroundResult(
        1, ("source",), ("number", "label"), ((1.25, "001"),), (), (), True
    )
    assert preview.rows == ((1.25, "001"),)
    with pytest.raises(TypeError, match="exact float"):
        replace(preview, rows=((True, "001"),))
    with pytest.raises(ValueError, match="immutable"):
        replace(preview, rows=[[1.25, "001"]])
    with pytest.raises(ValueError, match="column width"):
        replace(preview, rows=((1.25,),))
    with pytest.raises(TypeError, match="boolean"):
        replace(preview, ready_for_full_parse=1)


def test_config_metadata_budget_stops_before_expanding_inherited_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.parsing.gem5.impl.strategies import config_aware

    path = tmp_path / "config.ini"
    path.write_text(
        "[DEFAULT]\nlarge = "
        + "x" * 100
        + "\n"
        + "\n".join(f"[section{i:03d}]\n" for i in range(100)),
        encoding="utf-8",
    )
    visited = []
    original = config_aware._LiteralConfigParser.__getitem__

    def section(parser, key):
        visited.append(key)
        return original(parser, key)

    def expanded(*args, **kwargs):
        raise AssertionError("Metadata rendering materialized expanded section dictionaries")

    original_encode = json.JSONEncoder.encode

    def encode(encoder, value):
        if value == "x" * 100:
            raise AssertionError("Oversized value reached JSON string allocation")
        return original_encode(encoder, value)

    monkeypatch.setattr(config_aware, "MAX_PARSED_CELL_CHARACTERS", 80)
    monkeypatch.setattr(config_aware._LiteralConfigParser, "__getitem__", section)
    monkeypatch.setattr(config_aware._LiteralConfigParser, "items", expanded)
    monkeypatch.setattr(json.JSONEncoder, "encode", encode)
    with pytest.raises(ValueError, match="character limit"):
        config_aware.ConfigAwareParseWork._read_config(path)
    assert visited == ["section000"]


def test_incremental_config_metadata_encoding_preserves_inherited_case_and_literal_values(
    tmp_path: Path,
) -> None:
    from src.parsing.gem5.impl.strategies.config_aware import ConfigAwareParseWork

    path = tmp_path / "config.ini"
    path.write_text("[DEFAULT]\nCommon=μ%\n[B]\nx=001\n[A]\nz=NA\n", encoding="utf-8")
    expected = {"A": {"Common": "μ%", "z": "NA"}, "B": {"Common": "μ%", "x": "001"}}
    assert ConfigAwareParseWork._read_config(path) == json.dumps(
        expected, sort_keys=True, separators=(",", ":")
    )


@pytest.mark.parametrize("reverse_completion", [False, True])
def test_playground_resolved_paths_identify_rows_for_shuffled_batch_and_completion(
    reverse_completion: bool,
) -> None:
    from src.parsing.gem5.impl.gem5_parser import Gem5Parser

    values = []
    futures = []
    for path, number in (("b", 2.0), ("a", 1.0)):
        original = _result(path)
        variable = replace(original.variables[0], cells=(ParsedCell("number", "number", number),))
        value = replace(original, variables=(variable, original.variables[1]))
        future = Future()
        future.set_result(value)
        values.append(value)
        futures.append(future)
    batch = ParserPlaygroundBatchResult(
        tuple(futures), ("number", "label"), "unused", "simple", 2, ("b", "a")
    )
    result = Gem5Parser.finalize_parser_playground(
        batch, values[::-1] if reverse_completion else values
    )
    assert result.sampled_files == ("a", "b")
    assert result.columns == ("number", "label", "sim_path")
    assert result.rows == ((1.0, "NA", "a"), (2.0, "NA", "b"))
    assert result.missing_variables == () and result.ready_for_full_parse
