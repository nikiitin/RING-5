"""Current cache metadata is fully validated before sharing admitted request layouts."""

import copy
import json
from unittest.mock import patch

import pytest

from src.core.common import distribution_layout_codec as codec
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.native_distribution_layout import DistributionColumn
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.core.models.parsing_models import StatConfig
from src.parsing.framework.incremental_cache import encode_cache, load_cache
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.source_bindings import resolve_sources


def request():
    return StatConfig(
        "out",
        "distribution",
        source_name="d",
        params={
            "source_type": "distribution",
            "minimum": 0.25,
            "maximum": 1.25,
            "bucket_size": 0.5,
            "zero_policy": "nozero",
        },
    )


def cache_fixture(tmp_path):
    layout = (
        resolve_sources([request()], None, file_count=2, metadata_columns=()).accumulators[0].layout
    )
    results = tuple(
        ParsedFileResult(
            name,
            (
                ParsedVariableResult(
                    "out",
                    "number",
                    "entries",
                    tuple(
                        ParsedCell(column.column, "number", float(index))
                        for index, column in enumerate(layout.columns)
                    ),
                    layout=layout,
                ),
            ),
        )
        for name in ("a", "b")
    )
    fingerprints = (("a", "b" * 64), ("b", "c" * 64))
    path = tmp_path / "cache.json"
    path.write_bytes(encode_cache("a" * 64, ("out",), fingerprints, results))
    return layout, path, fingerprints


def test_multiple_cache_files_reuse_one_request_graph_after_full_validation(tmp_path, monkeypatch):
    layout, path, fingerprints = cache_fixture(tmp_path)

    def no_role_allocation(*args, **kwargs):
        raise AssertionError("Cache reuse must not allocate another role graph.")

    monkeypatch.setattr(DistributionColumn, "__init__", no_role_allocation)
    reuse = load_cache(path, "a" * 64, fingerprints, layout_declarations={"out": layout})
    assert len(reuse.results) == 2
    assert all(result.variables[0].layout is layout for result in reuse.results)


@pytest.mark.parametrize(
    "corruption", ["geometry", "role", "bool_index", "column_type", "bytes", "missing"]
)
def test_corrupt_cached_layout_never_reuses_planned_roles(tmp_path, monkeypatch, corruption):
    layout, path, fingerprints = cache_fixture(tmp_path)
    payload = json.loads(path.read_text())
    raw = payload["files"][0]["result"]["variables"][0]["layout"]
    if corruption == "geometry":
        raw["geometry"]["minimum"] += 0.00001
    elif corruption == "role":
        raw["columns"][1]["role"] = "summary"
    elif corruption == "bool_index":
        raw["columns"][1]["native_index"] = False
    elif corruption == "column_type":
        raw["columns"][0]["column"] = 1
    elif corruption == "missing":
        payload["files"][0]["result"]["variables"][0]["layout"] = None
    else:
        monkeypatch.setattr(codec, "MAX_PARSED_SCHEMA_BYTES", 50)
    path.write_text(json.dumps(payload))
    reuse = load_cache(path, "a" * 64, fingerprints, layout_declarations={"out": layout})
    assert reuse.results == ()


def test_native_layout_survives_full_cache_schema_preview_and_frame_metadata(tmp_path):
    inputs = tmp_path / "inputs"
    for name in ("a", "b"):
        folder = inputs / name
        folder.mkdir(parents=True)
        (folder / "stats.txt").write_text("d::samples 1\nd::0.25 2\n")
    full = Gem5Parser.submit_parse_async(
        str(inputs), "stats.txt", [request()], str(tmp_path / "full")
    )
    results = [future.result(timeout=10) for future in full.futures]
    assert results[0].variables[0].layout is results[1].variables[0].layout
    output = Gem5Parser.finalize_parsing(full, results)
    frame = ParsedOutputIO.to_frame(output)
    raw = frame.attrs["ring5.distribution_layouts"]["out"]
    assert raw["geometry"] == {"minimum": 0.25, "maximum": 1.25, "bucket_size": 0.5}
    assert raw["columns"][4]["source_label"] == "1.75"
    original = copy.deepcopy(frame.attrs)
    incremental = Gem5Parser.submit_incremental_parse_async(
        str(inputs), "stats.txt", [request()], str(tmp_path / "inc")
    )
    Gem5Parser.finalize_incremental_parsing(
        incremental, [future.result(timeout=10) for future in incremental.futures]
    )
    reused = Gem5Parser.submit_incremental_parse_async(
        str(inputs), "stats.txt", [request()], str(tmp_path / "inc")
    )
    assert reused.futures == () and len(reused.cached_results) == 2
    assert (
        reused.cached_results[0].variables[0].layout is reused.cached_results[1].variables[0].layout
    )
    restored = Gem5Parser.finalize_incremental_parsing(reused, [])
    assert ParsedOutputIO.to_frame(restored.output).attrs == original
    preview = Gem5Parser.submit_parser_playground_async(
        str(inputs), "stats.txt", [request()], str(tmp_path / "preview")
    )
    preview_values = [future.result(timeout=10) for future in preview.futures]
    assert preview_values[0].variables[0].layout == output.schema.variables[0].layout
    result = Gem5Parser.finalize_parser_playground(preview, preview_values)
    assert result.columns == tuple(column.name for column in output.schema.columns)
    assert result.ready_for_full_parse


def test_incremental_all_selected_files_admitted_before_cache_decode(tmp_path, monkeypatch):
    inputs = tmp_path / "inputs"
    for name in ("a", "b"):
        folder = inputs / name
        folder.mkdir(parents=True)
        (folder / "stats.txt").write_text("d::samples 1\nd::0.25 2\n")
    monkeypatch.setattr("src.parsing.gem5.impl.source_bindings.MAX_PARSE_MATRIX_CELLS", 7)
    with patch(
        "src.parsing.gem5.impl.gem5_parser.load_cache", side_effect=AssertionError("cache decoded")
    ):
        with pytest.raises(ValueError, match="physical column"):
            Gem5Parser.submit_incremental_parse_async(
                str(inputs), "stats.txt", [request()], str(tmp_path / "inc")
            )


def test_preview_and_subset_charge_only_their_actual_selected_files(tmp_path, monkeypatch):
    inputs = tmp_path / "inputs"
    files = []
    for name in ("a", "b", "c"):
        folder = inputs / name
        folder.mkdir(parents=True)
        file = folder / "stats.txt"
        file.write_text("d::samples 1\nd::0.25 2\n")
        files.append(file)
    monkeypatch.setattr("src.parsing.gem5.impl.gem5_parser.MAX_PARSE_FILES", 2)
    monkeypatch.setattr("src.parsing.gem5.impl.gem5_parser.MAX_PARSER_PLAYGROUND_FILES", 1)
    preview = Gem5Parser.submit_parser_playground_async(
        str(inputs), "stats.txt", [request()], str(tmp_path / "preview")
    )
    assert preview.matched_file_count == 3 and preview.sampled_files == (str(files[0]),)
    for future in preview.futures:
        future.result(timeout=10)
    aliases = [str(files[2]), str(files[0]), str(files[0].parent / ".." / "a" / "stats.txt")]
    subset = Gem5Parser.submit_parse_async(
        str(inputs), "stats.txt", [request()], str(tmp_path / "subset"), file_paths=aliases
    )
    assert subset.source_paths == (str(files[0]), str(files[2]))
    for future in subset.futures:
        future.result(timeout=10)


def zero_origin_result(name, minimum):
    config = StatConfig(
        "out",
        "distribution",
        params={
            "source_type": "distribution",
            "minimum": minimum,
            "maximum": 0.0,
            "bucket_size": 1.0,
            "zero_policy": "missing",
        },
    )
    layout = (
        resolve_sources([config], None, file_count=1, metadata_columns=()).accumulators[0].layout
    )
    return ParsedFileResult(
        name,
        (
            ParsedVariableResult(
                "out",
                "number",
                "entries",
                tuple(ParsedCell(column.column, "number", 0.0) for column in layout.columns),
                layout=layout,
            ),
        ),
    )


def test_cache_geometry_preserves_canonical_signed_zero_declaration(tmp_path):
    result = zero_origin_result("a", 0.0)
    fingerprints = (("a", "b" * 64),)
    path = tmp_path / "zero-cache.json"
    payload = json.loads(encode_cache("a" * 64, ("out",), fingerprints, [result]))
    payload["files"][0]["result"]["variables"][0]["layout"]["geometry"]["minimum"] = -0.0
    path.write_text(json.dumps(payload))
    reuse = load_cache(
        path, "a" * 64, fingerprints, layout_declarations={"out": result.variables[0].layout}
    )
    assert reuse.results == ()


def test_custom_file_layouts_cannot_average_canonically_different_zero_origins():
    positive = zero_origin_result("a", 0.0)
    negative = zero_origin_result("b", -0.0)
    with pytest.raises(ValueError, match="Conflicting declaration"):
        ParsedOutputIO.resolve([positive, negative], ["out"], ["a", "b"])
