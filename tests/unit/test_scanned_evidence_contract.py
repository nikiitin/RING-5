"""Current scanner DTO admission and immutable decoder boundary controls."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import ring5
from src.core.common.source_context_codec import SourceContextCodec
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.parse_failure_models import ParseDataValueError
from src.core.models.parsing_models import ScannedVariable
from src.core.models.source_evidence import AmbiguousSourceKind
from src.parsing.gem5.impl import source_events
from src.parsing.gem5.impl.source_events import Measurement, SourceEvidence, decode_source_event


def _payload() -> dict[str, object]:
    return {
        "name": "cpu00.v",
        "type": None,
        "entries": ["0", "1"],
        "source_evidence": {"state": "ambiguous", "candidates": ["distribution", "vector"]},
        "instances": [{"source_name": "cpu00.v", "indices": []}],
    }


def test_scanned_payload_owns_evidence_and_entries_without_legacy_projection() -> None:
    payload = _payload()
    model = ScannedVariable.from_dict(payload)  # type: ignore[arg-type]
    assert model.source_evidence == AmbiguousSourceKind(("distribution", "vector"))
    assert model.type is None
    payload["entries"] = ["changed"]
    output = model.to_dict()
    output["entries"].append("output-only")
    assert model.entries == ["0", "1"]
    assert not hasattr(model, "source_type")
    assert not hasattr(model, "minimum")
    assert not hasattr(model, "maximum")


@pytest.mark.parametrize("key", ["source_type", "minimum", "maximum", "declared_kind"])
def test_retired_scanned_fields_reject_instead_of_adapting(key: str) -> None:
    payload = _payload()
    payload[key] = "vector" if key in {"source_type", "declared_kind"} else 1.0
    with pytest.raises(ValueError, match="exactly"):
        ScannedVariable.from_dict(payload)  # type: ignore[arg-type]


def test_ambiguous_scanned_source_cannot_publish_an_executable_default() -> None:
    payload = _payload()
    payload["type"] = "vector"
    with pytest.raises(ValueError, match="cannot suggest"):
        ScannedVariable.from_dict(payload)  # type: ignore[arg-type]
    draft = StatConfigCodec.from_scanned(_payload(), frozenset())  # type: ignore[arg-type]
    assert draft["type"] == "" and draft["params"] == {}
    with pytest.raises(ValueError):
        StatConfigCodec.from_draft(draft)


def test_backend_evidence_retains_registered_custom_contract_in_owned_request() -> None:
    variable = ring5.ScannedVariable(
        "device.value",
        "device_counter",
        entries=["real-entry"],
        source_evidence=ring5.ResolvedSourceKind("device_counter", "backend_metadata"),
        instances=(ring5.SourceInstance("device.value", ()),),
    )
    assert variable.to_dict()["source_evidence"] == {
        "state": "resolved",
        "kind": "device_counter",
        "basis": "backend_metadata",
    }
    source = SourceContextCodec.parser(
        stats_path="actual-input",
        stats_pattern="stats.txt",
        strategy_type="device_strategy",
        variables=[
            ring5.StatConfig(
                "device.value", "device_counter", params={"source_type": "device_counter"}
            )
        ],
        scanned_variables=[variable.to_dict()],
        simulator="device",
        scan_limit=None,
        strict=True,
    )
    assert SourceContextCodec.scanned_variables(source)[0] == variable
    decoded = SourceContextCodec.scanned_payloads(source)
    decoded[0]["entries"].append("caller-only")
    assert SourceContextCodec.scanned_variables(source)[0].entries == ["real-entry"]


@pytest.mark.parametrize(
    "line",
    [
        "scalar/v/1",
        '{"event":"dump","retired":true}',
        '{"event":"dump","event":"dump"}',
        '{"event":"measurement","name":"v","shape":{},"entry":null,"value":"1"}',
        '{"event":"source","name":"v","source_evidence":{"source_type":"vector"},"entries":[]}',
    ],
)
def test_source_decoder_rejects_retired_wire_and_invalid_current_records(line: str) -> None:
    with pytest.raises(ParseDataValueError):
        decode_source_event(line)


def test_source_decoder_preserves_literal_controls_and_owned_oneline_geometry() -> None:
    value = " 001 NA nan λ left\x00right\r\t%"
    event = decode_source_event(
        json.dumps(
            {
                "event": "measurement",
                "name": "text",
                "shape": "configuration",
                "entry": None,
                "value": value,
            }
        )
    )
    assert isinstance(event, Measurement) and event.value == value
    first = decode_source_event(
        json.dumps(
            {
                "event": "measurement",
                "name": "v",
                "shape": "oneline",
                "values": ["1", "2"],
                "reported_geometry": {"bucket_size": "1"},
            }
        )
    )
    assert isinstance(first, Measurement)
    assert first.reported_geometry == (("bucket_size", "1"),)
    second = decode_source_event(
        json.dumps(
            {
                "event": "source",
                "name": "v",
                "source_evidence": {"state": "ambiguous", "candidates": ["distribution", "vector"]},
                "entries": ["0", "1"],
            }
        )
    )
    assert isinstance(second, SourceEvidence)
    assert first.reported_geometry == (("bucket_size", "1"),)
    assert second.entries == ("0", "1")


@pytest.mark.parametrize("line", ["x" * 81, "λ" * 41])
def test_source_wire_budget_precedes_json_allocation(
    line: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(source_events, "MAX_PARSE_RESULT_BYTES", 80)
    with patch.object(source_events.json, "loads") as allocate:
        with pytest.raises(ParseDataValueError, match="budget"):
            decode_source_event(line)
    allocate.assert_not_called()


def test_unmarked_decoder_programming_error_keeps_its_identity() -> None:
    sentinel = ValueError("unmarked decoder failure")
    with patch.object(source_events.json, "loads", side_effect=sentinel):
        with pytest.raises(ValueError) as caught:
            decode_source_event('{"event":"dump"}')
    assert caught.value is sentinel


def test_unknown_evidence_error_subtype_is_not_reclassified() -> None:
    class Unexpected(ValueError):
        pass

    sentinel = Unexpected("unmarked evidence failure")
    with patch.object(source_events, "decode_source_kind_evidence", side_effect=sentinel):
        with pytest.raises(Unexpected) as caught:
            decode_source_event(
                json.dumps({"event": "source", "name": "v", "source_evidence": {}, "entries": []})
            )
    assert caught.value is sentinel


def test_merged_catalog_byte_admission_precedes_pattern_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.common.source_context_codec import encode_source_json
    from src.core.models.parsing_models import ScanFileResult
    from src.parsing.gem5.impl import gem5_parser

    variables = [
        ring5.ScannedVariable(
            name,
            "vector",
            entries=["x" * 100],
            source_evidence=ring5.ResolvedSourceKind("vector", "backend_metadata"),
            instances=(ring5.SourceInstance(name, ()),),
        )
        for name in ("a", "b")
    ]
    sizes = [len(encode_source_json(variable.to_dict()).encode("utf-8")) for variable in variables]
    monkeypatch.setattr(gem5_parser, "MAX_PARSE_RESULT_BYTES", sum(sizes) + 2)
    with patch.object(gem5_parser.PatternAggregator, "aggregate_patterns") as project:
        with pytest.raises(ValueError, match="catalog.*byte budget"):
            gem5_parser.Gem5Parser.aggregate_scan_results([ScanFileResult("input", variables)])
    project.assert_not_called()
    assert [variable.entries for variable in variables] == [["x" * 100], ["x" * 100]]


def test_unchanged_catalog_across_files_does_not_charge_unique_metadata_repeatedly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.common.source_context_codec import encode_source_json
    from src.core.models.parsing_models import ScanFileResult
    from src.parsing.gem5.impl import gem5_parser

    variable = ring5.ScannedVariable(
        "counter",
        "scalar",
        source_evidence=ring5.ResolvedSourceKind("scalar", "backend_metadata"),
        instances=(ring5.SourceInstance("counter", ()),),
    )
    limit = len(encode_source_json(variable.to_dict()).encode("utf-8")) + 2
    monkeypatch.setattr(gem5_parser, "MAX_PARSE_RESULT_BYTES", limit)
    scan = gem5_parser.Gem5Parser.aggregate_scan_results(
        [ScanFileResult(f"file-{index}", [variable]) for index in range(32)]
    )
    assert scan.variables == [variable]
    assert scan.complete and scan.successful_files == 32
