"""Worker observation routing uses resolved sources and real registered accumulators."""

from src.core.models.source_evidence import ResolvedSourceKind


import json
import math
from unittest.mock import patch

import pytest

from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig
from src.parsing.gem5.impl.source_bindings import resolve_sources
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.types.type_mapper import TypeMapper


def _wire(*records):
    return "\n".join(json.dumps(record) for record in records)


def _point(name, value, shape="scalar"):
    return {"event": "measurement", "name": name, "shape": shape, "entry": None, "value": value}


def _entry(name, entry, value):
    return {"event": "measurement", "name": name, "shape": "entry", "entry": entry, "value": value}


def _source(name, kind, entries=()):
    return {
        "event": "source",
        "name": name,
        "entries": list(entries),
        "source_evidence": {"state": "resolved", "kind": kind, "basis": "wire_contract"},
    }


def _worker(configs, metadata=None, path="unused"):
    plan = resolve_sources(configs, metadata)
    accumulators = {spec.output_name: TypeMapper.create_stat(spec) for spec in plan.accumulators}
    return Gem5ParseWork(path, accumulators, plan), accumulators


def test_exact_scalar_and_vector_observations_remain_independent():
    work, values = _worker(
        [
            StatConfig("ipc", "scalar", repeat=2, params={"source_type": "scalar"}),
            StatConfig("v", "vector", repeat=2, params={"source_type": "vector", "entries": ["a"]}),
        ]
    )
    assert (
        work._process_output(
            _wire(
                _point("ipc", "2"),
                _point("ipc", "4"),
                _source("ipc", "scalar"),
                _entry("v", "a", "6"),
                _entry("v", "a", "8"),
                _source("v", "vector", ["a"]),
            )
        )
        is values
    )
    for value in values.values():
        value.balance_content()
        value.reduce_duplicates()
    assert values["ipc"].reduced_content == 3.0
    assert values["v"].reduced_content == {"a": 7.0}


def test_dump_boundaries_keep_missing_samples_visible_instead_of_realigning_entries():
    work, values = _worker(
        [
            StatConfig(
                "v", "vector", repeat=2, params={"source_type": "vector", "entries": ["a", "b"]}
            )
        ]
    )
    work._process_output(
        _wire(
            _entry("v", "a", "2"),
            _source("v", "vector", ["a"]),
            {"event": "dump"},
            _entry("v", "b", "4"),
            _source("v", "vector", ["b"]),
            {"event": "dump"},
        )
    )
    content = values["v"].content
    assert isinstance(content, dict)
    assert content["a"][0] == 2.0 and math.isnan(content["a"][1])
    assert math.isnan(content["b"][0]) and content["b"][1] == 4.0
    values["v"].balance_content()
    values["v"].reduce_duplicates()
    assert all(str(value) == "nan" for value in values["v"].reduced_content.values())


def test_one_scalar_source_populates_two_distinct_logical_aliases():
    configs = [
        StatConfig(name, "scalar", source_name="ipc", params={"source_type": "scalar"})
        for name in ["first", "second"]
    ]
    work, values = _worker(configs)
    work._process_output(_wire(_point("ipc", "1.25"), _source("ipc", "scalar")))
    assert set(values) == {"first", "second"}
    assert values["first"] is not values["second"]
    assert values["first"].content == values["second"].content == [1.25]


@pytest.mark.parametrize("pattern", [r"cpu\d+.ipc", r"cpu\d+\.ipc"])
def test_scalar_pattern_vector_uses_explicit_precomputed_numeric_labels(pattern):
    metadata = [
        ScannedVariable(
            r"cpu\d+.ipc",
            "vector",
            [],
            source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
            instances=(SourceInstance("cpu012.ipc", ("012",)), SourceInstance("cpu1.ipc", ("1",))),
        )
    ]
    config = StatConfig("IPC", "vector", source_name=pattern, params={"source_type": "scalar"})
    work, values = _worker([config], metadata)
    with patch(
        "src.core.common.safe_regex.numeric_pattern_id",
        side_effect=AssertionError("worker rematched"),
    ):
        work._process_output(
            _wire(
                _point("cpu012.ipc", "10"),
                _source("cpu012.ipc", "scalar"),
                _point("cpu1.ipc", "20"),
                _source("cpu1.ipc", "scalar"),
            )
        )
    assert values["IPC"].content == {"012": [10.0], "1": [20.0]}


def test_missing_numeric_source_logs_and_stays_empty(caplog):
    work, values = _worker([StatConfig("ipc", "scalar", params={"source_type": "scalar"})])
    work._process_output("")
    assert values["ipc"].content == []
    assert "absent or incomplete" in caplog.text


def test_configuration_fallback_comes_from_declared_params():
    # [test->req~ring5.ingestion.configuration-fallbacks~1]
    work, values = _worker(
        [
            StatConfig(
                "benchmark",
                "configuration",
                params={"source_type": "configuration", "on_empty": "unknown"},
            )
        ]
    )
    work._process_output("")
    assert values["benchmark"].content == []
    values["benchmark"].balance_content()
    values["benchmark"].reduce_duplicates()
    assert values["benchmark"].reduced_content == "unknown"


@pytest.mark.parametrize("kind", ["vector", "configuration"])
def test_raw_source_kind_mismatch_is_visible(kind):
    work, _ = _worker([StatConfig("ipc", "scalar", params={"source_type": "scalar"})])
    with pytest.raises(RuntimeError, match="contradicts actual observations"):
        work._process_output(_wire(_source("ipc", kind)))


def test_unknown_and_malformed_records_do_not_populate_outputs(caplog):
    work, values = _worker([StatConfig("ipc", "scalar", params={"source_type": "scalar"})])
    for wire in ["malformed", _wire(_point("other", "3")), "Scalar/ipc/2"]:
        with pytest.raises(ValueError):
            work._process_output(wire)
        assert values["ipc"].content == []


def test_worker_rejects_accumulator_maps_that_do_not_match_plan():
    plan = resolve_sources([StatConfig("ipc", "scalar", params={"source_type": "scalar"})], [])
    with pytest.raises(RuntimeError, match="requires logical accumulators"):
        Gem5ParseWork("unused", {}, plan)
    with pytest.raises(ValueError, match="exactly match"):
        Gem5ParseWork("unused", {"wrong": TypeMapper.create_stat(plan.accumulators[0])}, plan)


@pytest.mark.parametrize(
    ("output_type", "raw_type", "wire", "expected"),
    [("configuration", "scalar", "001", "001"), ("scalar", "configuration", "1.25", 1.25)],
)
def test_scalar_configuration_reinterpretation_uses_output_observation_shape(
    output_type, raw_type, wire, expected
):
    config = StatConfig(
        "alias",
        output_type,
        source_name="source",
        params={
            "source_type": raw_type,
            **({"on_empty": "missing"} if output_type == "configuration" else {}),
        },
    )
    work, values = _worker([config])
    work._process_output(_wire(_point("source", wire, raw_type), _source("source", raw_type)))
    stat = values["alias"]
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == expected
