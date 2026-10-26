"""External typed backends use the supported ring5-only SDK, without DTO adapters."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import ring5
from tests.helpers.public_typed_parser import ExampleParser

pytestmark = pytest.mark.public_api


def test_external_backend_script_imports_only_public_sdk_and_stdlib(tmp_path):
    original = Path(__file__).parents[1] / "helpers" / "public_typed_parser.py"
    text = original.read_text(encoding="utf-8")
    imports = {
        (
            node.module.split(".")[0]
            if isinstance(node, ast.ImportFrom) and node.module
            else alias.name.split(".")[0]
        )
        for node in ast.walk(ast.parse(text))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports <= {"__future__", "hashlib", "json", "sys", "concurrent", "pathlib", "ring5"}
    script = tmp_path / "external_backend.py"
    script.write_text(text, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path / "run")],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[2])},
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert json.loads(result.stdout)["rows"] == [
        {"value": 1.25, "label": "NA"},
        {"value": 2.5, "label": "NA"},
    ]


def test_default_session_replays_actual_registered_backend_without_scan_or_editor_selection(
    tmp_path,
    monkeypatch,
):
    from src.parsing.registry import ParsingStrategy, SimulatorInfo, SimulatorRegistry

    backend = ExampleParser()
    name = "typed-example"
    info = SimulatorInfo(
        name, "Typed example", parsing_strategies=[ParsingStrategy("simple", "Simple")]
    )
    monkeypatch.setitem(SimulatorRegistry._registry, name, (info, lambda: backend))
    monkeypatch.setitem(SimulatorRegistry._instances, name, backend)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "a.txt").write_text("1.25", encoding="utf-8")
    variables = (
        {
            "name": "value",
            "type": "scalar",
            "repeat": 1,
            "params": {"source_type": "scalar"},
            "statistics_only": False,
            "is_regex": False,
            "keep_indices": False,
            "source_name": None,
        },
    )
    recipe = ring5.AnalysisRecipe(
        "registered",
        ring5.RecipeSource(
            "parser",
            str(inputs),
            pattern="*.txt",
            variables=variables,
            simulator=name,
            scan_limit=None,
        ),
    )
    try:
        with ring5.Session() as session:
            session.api.state_manager.set_simulator("gem5")
            session.run_analysis_recipe(recipe)
            assert session.api.state_manager.get_data()["value"].tolist() == [1.25]
            captured = session.capture_analysis_recipe("actual")
            assert captured.source.simulator == name
            assert captured.source.scanned_variables == ()
            assert captured.source.scan_limit is None
            assert backend.scans == 0
            session.api.state_manager.set_simulator("not-the-declared-backend")
            session.run_analysis_recipe(captured)
            assert session.api.state_manager.get_data()["value"].tolist() == [1.25]
            assert backend.scans == 0
    finally:
        backend.close()


def test_public_resolution_and_publication_normalize_errors_and_preserve_old_output(tmp_path):
    result = ring5.ParsedFileResult(
        "a",
        (
            ring5.ParsedVariableResult(
                "label", "text", "scalar", (ring5.ParsedCell("label", "text", "NA"),)
            ),
        ),
    )
    resolved = ring5.resolve_parsed_output([result], ["label"], ["a"])
    output = ring5.publish_parsed_output(resolved, tmp_path / "results.csv")
    original = Path(output.csv_path).read_bytes()
    for values, paths in [([], ["a"]), ([result, result], ["a"]), ([result], ["b"])]:
        with pytest.raises(ring5.ParseError):
            ring5.resolve_parsed_output(values, ["label"], paths)
    invalid = ring5.ResolvedParsedRows(output.schema, (("\ud800",),), ("a",), ())
    with pytest.raises(ring5.ParseError):
        ring5.publish_parsed_output(invalid, output.csv_path)
    assert Path(output.csv_path).read_bytes() == original
    with pytest.raises(TypeError):
        ring5.ParsedCell("value", "number", 1)
    with pytest.raises(ValueError):
        ring5.ParsedVariableResult("value", "number", "scalar", ())
    with pytest.raises(ValueError):
        ring5.ParsedVariableSchema("value", "number", "..")


def test_public_transport_constructors_keep_cold_root_import_light():
    script = """
import sys
import ring5
ring5.ParsedCell('label', 'text', 'NA')
ring5.InferredCsvPolicy(('label',))
ring5.ReviewedCsvPolicy(ring5.ImportOptions())
assert not ({'numpy', 'pandas', 'plotly', 'matplotlib', 'streamlit'} & sys.modules.keys())
"""
    subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)
