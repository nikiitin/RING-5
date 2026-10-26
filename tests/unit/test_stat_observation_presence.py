"""Missing diagnostics use observation presence, independently of numeric NaN values."""

from __future__ import annotations

import math

import pytest

from src.core.models.parsing_models import StatConfig, StatParamValue
from src.parsing.gem5.impl.source_bindings import resolve_sources
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.types.type_mapper import TypeMapper
from src.parsing.gem5.types.vector import Vector


@pytest.mark.parametrize(
    ("kind", "repeat", "params", "wire", "missing"),
    [
        (
            "vector",
            1,
            {"entries": ["a", "b"]},
            (
                '{"event":"measurement","name":"source","shape":"entry","entr'
                'y":"a","value":"2"}\n{"event":"source","name":"source","sourc'
                'e_evidence":{"state":"ambiguous","candidates":["distribution'
                '","histogram","vector"]},"entries":["a"]}'
            ),
            1,
        ),
        (
            "vector",
            1,
            {"entries": ["a", "b"]},
            (
                '{"event":"measurement","name":"source","shape":"entry","entr'
                'y":"other","value":"3"}\n{"event":"source","name":"source","s'
                'ource_evidence":{"state":"ambiguous","candidates":["distribu'
                'tion","histogram","vector"]},"entries":["other"]}'
            ),
            2,
        ),
        ("vector", 1, {"entries": ["a", "b"]}, "", 2),
        (
            "vector",
            2,
            {"entries": ["a", "b"]},
            (
                '{"event":"measurement","name":"source","shape":"entry","entr'
                'y":"a","value":"2"}\n{"event":"measurement","name":"source","'
                'shape":"entry","entry":"b","value":"3"}\n{"event":"source","n'
                'ame":"source","source_evidence":{"state":"ambiguous","candid'
                'ates":["distribution","histogram","vector"]},"entries":["a",'
                '"b"]}\n{"event":"dump"}\n{"event":"measurement","name":"source'
                '","shape":"entry","entry":"a","value":"4"}\n{"event":"source"'
                ',"name":"source","source_evidence":{"state":"ambiguous","can'
                'didates":["distribution","histogram","vector"]},"entries":["'
                'a"]}\n{"event":"dump"}'
            ),
            1,
        ),
        (
            "vector",
            1,
            {"entries": ["a", "b"]},
            (
                '{"event":"measurement","name":"source","shape":"entry","entr'
                'y":"a","value":"nan"}\n{"event":"measurement","name":"source"'
                ',"shape":"entry","entry":"b","value":"nan"}\n{"event":"source'
                '","name":"source","source_evidence":{"state":"ambiguous","ca'
                'ndidates":["distribution","histogram","vector"]},"entries":['
                '"a","b"]}'
            ),
            0,
        ),
        (
            "scalar",
            1,
            {},
            (
                '{"event":"measurement","name":"source","shape":"scalar","ent'
                'ry":null,"value":"nan"}\n{"event":"source","name":"source","s'
                'ource_evidence":{"state":"resolved","kind":"scalar","basis":'
                '"wire_contract"},"entries":[]}'
            ),
            0,
        ),
        (
            "scalar",
            2,
            {},
            (
                '{"event":"measurement","name":"source","shape":"scalar","ent'
                'ry":null,"value":"2"}\n{"event":"source","name":"source","sou'
                'rce_evidence":{"state":"resolved","kind":"scalar","basis":"w'
                'ire_contract"},"entries":[]}'
            ),
            1,
        ),
        ("scalar", 1, {}, "", 1),
        (
            "histogram",
            1,
            {"entries": ["0-0"], "statistics": ["mean"]},
            (
                '{"event":"measurement","name":"source","shape":"entry","entr'
                'y":"0-0","value":"2"}\n{"event":"source","name":"source","sou'
                'rce_evidence":{"state":"ambiguous","candidates":["distributi'
                'on","histogram","vector"]},"entries":["0-0"]}'
            ),
            1,
        ),
        (
            "histogram",
            1,
            {"entries": ["0-0"], "statistics": ["mean"]},
            (
                '{"event":"measurement","name":"source","shape":"entry","entr'
                'y":"0-0","value":"2"}\n{"event":"measurement","name":"source"'
                ',"shape":"entry","entry":"mean","value":"nan"}\n{"event":"sou'
                'rce","name":"source","source_evidence":{"state":"ambiguous",'
                '"candidates":["distribution","histogram","vector"]},"entries'
                '":["0-0","mean"]}'
            ),
            0,
        ),
        ("histogram", 1, {}, "", 1),
        (
            "distribution",
            1,
            {
                "minimum": 0,
                "maximum": 0,
                "statistics": ["mean"],
                "bucket_size": 1,
                "zero_policy": "missing",
            },
            (
                '{"event":"measurement","name":"source","shape":"entry","entr'
                'y":"underflows","value":"0"}\n{"event":"measurement","name":"'
                'source","shape":"entry","entry":"0","value":"2"}\n{"event":"m'
                'easurement","name":"source","shape":"entry","entry":"overflo'
                'ws","value":"0"}\n{"event":"source","name":"source","source_e'
                'vidence":{"state":"ambiguous","candidates":["distribution","'
                'histogram","vector"]},"entries":["0","overflows","underflows'
                '"]}'
            ),
            1,
        ),
        (
            "distribution",
            1,
            {
                "minimum": 0,
                "maximum": 0,
                "statistics": ["mean"],
                "bucket_size": 1,
                "zero_policy": "missing",
            },
            (
                '{"event":"measurement","name":"source","shape":"entry","entr'
                'y":"underflows","value":"0"}\n{"event":"measurement","name":"'
                'source","shape":"entry","entry":"0","value":"2"}\n{"event":"m'
                'easurement","name":"source","shape":"entry","entry":"overflo'
                'ws","value":"0"}\n{"event":"measurement","name":"source","sha'
                'pe":"entry","entry":"mean","value":"nan"}\n{"event":"source",'
                '"name":"source","source_evidence":{"state":"ambiguous","cand'
                'idates":["distribution","histogram","vector"]},"entries":["0'
                '","mean","overflows","underflows"]}'
            ),
            0,
        ),
        ("configuration", 3, {"on_empty": "unknown"}, "", 0),
        (
            "configuration",
            1,
            {"on_empty": "unknown"},
            (
                '{"event":"measurement","name":"source","shape":"configuratio'
                'n","entry":null,"value":"nan"}\n{"event":"source","name":"sou'
                'rce","source_evidence":{"state":"resolved","kind":"configura'
                'tion","basis":"wire_contract"},"entries":[]}'
            ),
            0,
        ),
    ],
)
def test_worker_diagnostics_distinguish_absence_from_measured_nan_and_text_policy(
    kind: str,
    repeat: int,
    params: dict[str, StatParamValue],
    wire: str,
    missing: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # [test->req~ring5.ingestion.parse-integrity~1]
    config = StatConfig(
        "output",
        kind,
        source_name="source",
        repeat=repeat,
        params={"source_type": kind, **params},
    )
    plan = resolve_sources([config], None, file_count=1, metadata_columns=())
    stat = TypeMapper.create_stat(plan.accumulators[0])
    worker = Gem5ParseWork("unused", {"output": stat}, plan)
    worker._process_output(wire)
    assert stat.missing_measurement_count == missing
    assert ("absent or incomplete" in caplog.text) == bool(missing)
    stat.balance_content()
    assert stat.missing_measurement_count == stat.padded_count == missing
    stat.reduce_duplicates()
    if kind == "configuration":
        assert stat.reduced_content == ("nan" if wire else "unknown")


def test_derived_nan_views_do_not_hide_absence_or_mutate_presence() -> None:
    stat = Vector(entries=["a", "b"])
    stat.add_observation({"a": 2.0})
    view = stat.content
    assert math.isnan(view["b"][0])
    assert stat.missing_measurement_count == 1
    view["b"][0] = 99
    assert stat.missing_measurement_count == 1
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content["a"] == 2.0
    assert math.isnan(stat.reduced_content["b"])

    observed_nan = Vector(entries=["a", "b"])
    observed_nan.add_observation({"a": 2.0, "b": math.nan})
    assert observed_nan.missing_measurement_count == 0
    observed_nan.balance_content()
    observed_nan.reduce_duplicates()
    assert math.isnan(observed_nan.reduced_content["b"])
    assert observed_nan.padded_count == 0
