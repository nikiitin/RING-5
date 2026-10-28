"""Current typed output descriptors own schema meaning without filename reconstruction."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.core.common import parsed_output_codec
from src.core.common.parsed_output_codec import decode_parsed_output, encode_parsed_output
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult


def _output(tmp_path: Path):
    results = [
        ParsedFileResult(
            "source",
            (
                ParsedVariableResult(
                    "literal",
                    "text",
                    "scalar",
                    (ParsedCell("literal", "text", "NaN"),),
                    layout=None,
                ),
                ParsedVariableResult(
                    "value",
                    "number",
                    "scalar",
                    (ParsedCell("value", "number", float("nan")),),
                    layout=None,
                ),
            ),
        )
    ]
    return ParsedOutputIO.publish(
        tmp_path / "output.csv", ParsedOutputIO.resolve(results, ["literal", "value"], ("source",))
    )


def test_descriptor_roundtrip_retains_logical_types_owners_and_schema_bound_digest(tmp_path):
    output = _output(tmp_path)
    wire = encode_parsed_output(output)
    assert decode_parsed_output(wire) == output
    assert encode_parsed_output(decode_parsed_output(wire)) == wire
    frame = ParsedOutputIO.to_frame(decode_parsed_output(wire))
    assert frame["literal"].tolist() == ["NaN"]
    assert frame["value"].isna().all()
    moved = replace(output, csv_path="arbitrary-name.csv")
    assert decode_parsed_output(encode_parsed_output(moved)) == moved


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(version=0),
        lambda p: p.update(version=True),
        lambda p: p.update(format="other"),
        lambda p: p.update(extra=True),
        lambda p: p.pop("schema"),
        lambda p: p["schema"].update(version=0),
        lambda p: p["schema"].update(extra=True),
        lambda p: p["schema"]["columns"][0].update(owner="undeclared"),
        lambda p: p["schema"]["variables"][0].update(shape=".."),
    ],
)
def test_descriptor_rejects_unknown_missing_or_invalid_current_fields(tmp_path, mutate):
    payload = json.loads(encode_parsed_output(_output(tmp_path)))
    mutate(payload)
    with pytest.raises((TypeError, ValueError)):
        decode_parsed_output(json.dumps(payload))


def test_descriptor_admits_byte_budget_before_json_parse(monkeypatch):
    monkeypatch.setattr(parsed_output_codec, "MAX_PARSED_DESCRIPTOR_BYTES", 8)

    def forbidden(*args, **kwargs):
        pytest.fail("Over-budget descriptor reached JSON allocation")

    monkeypatch.setattr(parsed_output_codec.json, "loads", forbidden)
    with pytest.raises(ValueError, match="bounded"):
        decode_parsed_output("x" * 9)


def test_descriptor_rejects_duplicate_keys_and_schema_substitution(tmp_path):
    output = _output(tmp_path)
    with pytest.raises(ValueError, match="Duplicate"):
        decode_parsed_output('{"version":1,"version":1}')
    payload = json.loads(encode_parsed_output(output))
    payload["schema"]["variables"][0]["kind"] = "number"
    payload["schema"]["columns"][0]["kind"] = "number"
    altered = decode_parsed_output(json.dumps(payload))
    with pytest.raises(ValueError):
        ParsedOutputIO.read(altered)
