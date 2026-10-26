"""Shared native text evidence, async source binding and partial scan ownership."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator

import pytest
import ring5

from src.core.models.source_evidence import source_kind_candidates
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.scanning.scanner import Gem5StatsScanner
from src.parsing.gem5.impl.source_bindings import literal_source_filter
from src.parsing.gem5.impl.source_events import SourceEvidence, decode_source_event
from src.parsing.gem5.impl.strategies.perl_worker_pool import get_worker_pool, shutdown_worker_pool

pytestmark = pytest.mark.xdist_group("perl_pool")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/gem5_native_text"
NATIVE_CASES = sorted(path.stem for path in FIXTURES.glob("*.txt"))


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "storage"))


@pytest.fixture(scope="module", autouse=True)
def close_native_workers() -> Generator[None, None, None]:
    yield
    shutdown_worker_pool()


@pytest.mark.parametrize("case", NATIVE_CASES)
def test_native_goldens_feed_the_same_observed_contracts_to_scanner_and_worker(case: str) -> None:
    source = FIXTURES / f"{case}.txt"
    scanned = Gem5StatsScanner.get_instance().scan_file(source)
    assert scanned.ok
    assert len(scanned.variables) == 1
    variable = scanned.variables[0]
    lines = get_worker_pool().parse_file(str(source), [literal_source_filter(variable.name)])
    events = [decode_source_event(line) for line in lines]
    evidence = [event for event in events if isinstance(event, SourceEvidence)]
    assert len(evidence) == 1
    assert evidence[0].evidence == variable.source_evidence
    assert evidence[0].entries == tuple(variable.entries)
    if case.startswith("fractional_vector"):
        assert source_kind_candidates(variable.source_evidence) == {"vector"}
        assert variable.type == "vector"
    else:
        assert source_kind_candidates(variable.source_evidence) == {"distribution", "vector"}
        assert variable.type is None
    assert "source_type" not in variable.to_dict()
    assert "minimum" not in variable.to_dict()
    assert "maximum" not in variable.to_dict()


def test_byte_identical_native_vector_and_distribution_remain_ambiguous() -> None:
    assert (FIXTURES / "empty_vector.txt").read_bytes() == (
        FIXTURES / "empty_dist.txt"
    ).read_bytes()
    scans = [
        Gem5StatsScanner.get_instance().scan_file(FIXTURES / f"{name}.txt")
        for name in ("empty_vector", "empty_dist")
    ]
    assert scans[0].variables[0].source_evidence == scans[1].variables[0].source_evidence
    assert scans[0].variables[0].type is None


def test_source_local_contradictions_keep_other_variables_and_strict_editor_atomicity(
    tmp_path: Path,
) -> None:
    source = tmp_path / "stats.txt"
    source.write_text("good 1\nbad 1\nbad::a 2\n", encoding="utf-8")
    with ring5.Session() as session:
        before_path = session.api.state_manager.get_stats_path()
        before_catalog = session.api.state_manager.get_scanned_variables()
        with pytest.raises(ring5.ScanError, match="incomplete"):
            session.scan(str(tmp_path))
        assert session.api.state_manager.get_stats_path() == before_path
        assert session.api.state_manager.get_scanned_variables() == before_catalog
        partial = session.scan(str(tmp_path), strict=False)
        assert [variable.name for variable in partial.variables] == ["good"]
        assert partial.scanned_files == 1 and partial.successful_files == 0
        assert len(partial.failures) == 1
        assert "bad" in str(partial.failures[0].error)


def test_cross_file_contradiction_excludes_only_the_affected_source(tmp_path: Path) -> None:
    for folder, text in (("a", "bad 1\nfirst 2\n"), ("b", "bad::x 3\nsecond 4\n")):
        directory = tmp_path / folder
        directory.mkdir()
        (directory / "stats.txt").write_text(text)
    futures = Gem5Parser.submit_scan_async(str(tmp_path), limit=0)
    scan = Gem5Parser.aggregate_scan_results([future.result(timeout=30) for future in futures])
    assert {variable.name for variable in scan.variables} == {"first", "second"}
    assert len(scan.failures) == scan.scanned_files == 2
    assert scan.successful_files == 0


def test_scalar_patterns_preserve_actual_source_coordinates_with_resolved_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / "stats.txt").write_text("system.cpu00.v 2\nsystem.cpu01.v 4\n")
    with ring5.Session() as session:
        scanned = session.scan(str(tmp_path))
        assert len(scanned.variables) == 1
        variable = scanned.variables[0]
        assert variable.type == "vector" and variable.entries == []
        assert variable.source_evidence == ring5.ResolvedSourceKind("scalar", "wire_contract")
        assert [instance.indices for instance in variable.instances] == [("00",), ("01",)]
        result = session.parse(str(tmp_path), variables=[variable.name])
        assert session.load(result).rows() == [
            {f"{variable.name}..00": 2.0, f"{variable.name}..01": 4.0}
        ]


def test_numeric_point_vector_requires_an_explicit_compatible_source_contract(
    tmp_path: Path,
) -> None:
    (tmp_path / "stats.txt").write_text("v::0 2\nv::1 3\n")
    with ring5.Session() as session:
        scan = session.scan(str(tmp_path))
        assert scan.variables[0].type is None
        assert source_kind_candidates(scan.variables[0].source_evidence) == {
            "distribution",
            "vector",
        }
        with pytest.raises(ring5.ParseError):
            session.parse(
                str(tmp_path),
                variables=[ring5.StatConfig("v", "histogram", params={"source_type": "histogram"})],
            )
        result = session.parse(
            str(tmp_path),
            variables=[
                ring5.StatConfig(
                    "v", "vector", params={"source_type": "vector", "entries": ["0", "1"]}
                )
            ],
        )
        assert session.load(result).rows() == [{"v..0": 2.0, "v..1": 3.0}]
        # Explicit Vector-to-Histogram output conversion is a separate retained feature.
        converted = session.parse(
            str(tmp_path),
            variables=[
                ring5.StatConfig(
                    "v", "histogram", params={"source_type": "vector", "entries": ["0", "1"]}
                )
            ],
        )
        assert session.load(converted).rows() == [{"v..0-0": 2.0, "v..1-1": 3.0}]


def test_string_only_ambiguous_request_does_not_invent_a_grid_or_kind(tmp_path: Path) -> None:
    (tmp_path / "stats.txt").write_text("d::underflows 0\nd::0 1\nd::overflows 0\n")
    with ring5.Session() as session:
        with pytest.raises((ring5.ParseError, ring5.ScanError), match="type|contract|source"):
            session.parse(str(tmp_path), variables=["d"])
        assert session.api.state_manager.get_data() is None


def test_fractional_percentage_vector_and_literal_text_survive_real_worker(tmp_path: Path) -> None:
    (tmp_path / "stats.txt").write_text(
        "v::a .5 28.57% 28.57%\nv::b 1.25 71.43% 100%\nc= 001 NA λ left\x00right\n"
    )
    with ring5.Session() as session:
        parsed = session.parse(
            str(tmp_path),
            variables=[
                ring5.StatConfig(
                    "v", "vector", params={"source_type": "vector", "entries": ["a", "b"]}
                ),
                ring5.StatConfig("c", "configuration", params={"source_type": "configuration"}),
            ],
        )
        assert session.load(parsed).rows() == [
            {"v..a": 0.5, "v..b": 1.25, "c": " 001 NA λ left\x00right"}
        ]
        origin = session.api.state_manager.get_loaded_origin()
        assert origin is not None
        context = origin.source
        assert isinstance(context, ring5.ParserSourceContext)
        assert "source_evidence" in context.scanned_variables_json
        assert '"minimum"' not in context.scanned_variables_json
        assert (
            json.loads(context.scanned_variables_json)[0]["source_evidence"]["state"] == "resolved"
        )


def test_large_scan_catalog_does_not_borrow_the_parse_variable_count_limit(tmp_path: Path) -> None:
    path = tmp_path / "stats.txt"
    path.write_text("".join(f"counter{index} {index}\n" for index in range(12001)))
    scanned = Gem5StatsScanner.get_instance().scan_file(path)
    assert scanned.ok and len(scanned.variables) == 12001
    assert all(
        variable.source_evidence == ring5.ResolvedSourceKind("scalar", "wire_contract")
        for variable in scanned.variables
    )


def test_repeated_oneline_geometry_is_owned_by_its_actual_observation(tmp_path: Path) -> None:
    (tmp_path / "stats.txt").write_text(
        "h::bucket_size 1\nh::min_bucket 0\nh::max_bucket 1\nh |2 |4\n"
        "h::bucket_size 2\nh::min_bucket 0\nh::max_bucket 3\nh |6 |8\n"
    )
    with ring5.Session() as session:
        result = session.parse(
            str(tmp_path),
            variables=[
                ring5.StatConfig("h", "histogram", repeat=2, params={"source_type": "histogram"})
            ],
            strict=False,
        )
        rows = session.load(result).rows()
        assert len(rows) == 1
        # The two real grids retain distinct labels; no second header reinterprets the first.
        assert set(rows[0]) == {"h..0-0", "h..1-1", "h..0-1", "h..2-3"}
        assert all(value != value for value in rows[0].values())
        rebinned = session.parse(
            str(tmp_path),
            variables=[
                ring5.StatConfig(
                    "h",
                    "histogram",
                    repeat=2,
                    params={"source_type": "histogram", "bins": 2, "max_range": 4},
                )
            ],
        )
        assert session.load(rebinned).rows() == [{"h..0-3": 10.0, "h..4+": 0.0}]


def test_prior_semantic_cache_is_reparsed_before_returning_fractional_percentage_values(
    tmp_path: Path,
) -> None:
    from dataclasses import replace
    from unittest.mock import patch
    from src.core.common.parsed_output import ParsedOutputIO
    from src.core.models.parsing_models import PARSER_RESULT_VERSION
    from src.parsing.framework import incremental_cache

    assert PARSER_RESULT_VERSION > 10
    (tmp_path / "stats.txt").write_text("v::a .5 28.57% 28.57%\nv::b 1.25 71.43% 100%\n")
    configs = [
        ring5.StatConfig("v", "vector", params={"source_type": "vector", "entries": ["a", "b"]})
    ]
    cache = tmp_path / "out" / "cache.json"
    initial = Gem5Parser.submit_incremental_parse_async(
        str(tmp_path), "stats.txt", configs, str(cache.parent), cache_path=str(cache)
    )
    values = [future.result(timeout=30) for future in initial.futures]
    Gem5Parser.finalize_incremental_parsing(initial, values)
    # This is the typed shape actually emitted by semantic10 for these records.
    stale_variable = replace(
        values[0].variables[0],
        cells=tuple(replace(cell, value=float("nan")) for cell in values[0].variables[0].cells),
        missing_measurements=2,
    )
    stale_record = replace(values[0], variables=(stale_variable,))
    with patch.object(incremental_cache, "PARSER_RESULT_VERSION", 10):
        old_hash = incremental_cache.configuration_hash("stats.txt", "simple", configs, None)
    cache.write_bytes(
        incremental_cache.encode_cache(old_hash, ("v",), initial.fingerprints, [stale_record])
    )
    current = Gem5Parser.submit_incremental_parse_async(
        str(tmp_path), "stats.txt", configs, str(cache.parent), cache_path=str(cache)
    )
    assert len(current.futures) == 1 and current.reused_file_count == 0
    result = Gem5Parser.finalize_incremental_parsing(
        current, [future.result(timeout=30) for future in current.futures]
    )
    assert ParsedOutputIO.to_frame(result.output).to_dict("records") == [
        {"v..a": 0.5, "v..b": 1.25}
    ]


@pytest.mark.parametrize("value", ["35482", "3.25", "nan", "inf"])
def test_singleton_vector_printer_scalar_wire_with_percentages_keeps_first_measurement(
    tmp_path: Path, value: str
) -> None:
    (tmp_path / "stats.txt").write_text(
        f"system.ruby.Directory_Controller.I.Fetch {value} 0.00% 0.00% (Unspecified)\n"
    )
    with ring5.Session() as session:
        scan = session.scan(str(tmp_path))
        assert scan.complete and len(scan.variables) == 1
        assert scan.variables[0].source_evidence == ring5.ResolvedSourceKind(
            "scalar", "wire_contract"
        )
        assert scan.variables[0].entries == []
        result = session.parse(str(tmp_path), variables=[scan.variables[0].name], strict=False)
        row = session.load(result).rows()[0]
        measurement = row[scan.variables[0].name]
        if value == "nan":
            assert measurement != measurement
        else:
            assert measurement == float(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("bucket_size", "9" * 5000),
        ("bucket_size", "0" * 5000 + "1"),
        ("min_bucket", "-" + "0" * 5000 + "1"),
    ],
)
def test_oversize_integral_geometry_releases_work_while_failed_future_is_held(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    import gc
    import weakref
    from concurrent.futures import wait
    from threading import Barrier
    from src.core.models.parse_failure_models import ParseDataValueError, ParseFailureFacts
    from src.parsing.framework.work_pool import WorkPool
    from src.parsing.gem5.impl.source_bindings import SourcePlan
    from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork, VarsDictType

    refs: list[weakref.ReferenceType[Gem5ParseWork]] = []
    original_init = Gem5ParseWork.__init__

    def track(
        self: Gem5ParseWork, file_to_parse: str, accumulators: VarsDictType, plan: SourcePlan
    ) -> None:
        original_init(self, file_to_parse, accumulators, plan)
        refs.append(weakref.ref(self))

    monkeypatch.setattr(Gem5ParseWork, "__init__", track)
    geometry = {"bucket_size": "1", "min_bucket": "0", "max_bucket": "0", field: value}
    (tmp_path / "stats.txt").write_text(
        "".join(f"h::{key} {token}\n" for key, token in geometry.items()) + "h |1\n"
    )
    batch = Gem5Parser.submit_parse_async(
        str(tmp_path),
        "stats.txt",
        [ring5.StatConfig("h", "histogram", params={"source_type": "histogram"})],
        str(tmp_path / "output"),
    )
    error = batch.futures[0].exception(timeout=15)
    assert isinstance(error, ParseDataValueError) and type(error) is ParseDataValueError
    assert error.__cause__ is error.__context__ is None
    facts = error.__dict__["failure_facts"]
    assert isinstance(facts, ParseFailureFacts)
    assert facts.source_path == str(tmp_path / "stats.txt")
    assert "_oneline_entries" in facts.origin
    assert len(str(error)) <= 1024 and len(facts.origin) <= 2048
    barrier = Barrier(2)
    drained = [WorkPool.get_instance().submit(lambda: barrier.wait(timeout=5)) for _ in range(2)]
    assert not wait(drained, timeout=5).not_done
    gc.collect()
    assert len(refs) == 1 and refs[0]() is None
    assert not (tmp_path / "output/results.csv").exists()


@pytest.mark.parametrize(
    "case,first",
    [
        ("fractional_vector_nonfinite_pdf", float("inf")),
        ("fractional_vector_units", 0.5),
    ],
)
def test_pinned_optional_percentage_and_unit_annotations_preserve_measurements(
    tmp_path: Path,
    case: str,
    first: float,
) -> None:
    (tmp_path / "stats.txt").write_bytes((FIXTURES / f"{case}.txt").read_bytes())
    with ring5.Session() as session:
        result = session.parse(
            str(tmp_path),
            [
                ring5.StatConfig(
                    "V",
                    "vector",
                    source_name="system.cpu00.vector",
                    params={"source_type": "vector", "entries": ["a", "b"]},
                )
            ],
        )
        assert session.load(result).rows() == [{"V..a": first, "V..b": 1.25}]


@pytest.mark.parametrize("row", ["v 1 10% 20% 30%", "v::a 1 10% 20% 30%", "v |1 10% 20% 30%"])
def test_extra_percentage_fields_reject_the_source_without_publishing_output(
    tmp_path: Path,
    row: str,
) -> None:
    from src.core.models.parse_failure_models import ParseDataRuntimeError

    (tmp_path / "stats.txt").write_text("good 9\n" + row + "\n")
    scanned = Gem5StatsScanner.get_instance().scan_file(tmp_path / "stats.txt")
    assert not scanned.ok and [value.name for value in scanned.variables] == ["good"]
    assert scanned.error is not None and "Malformed" in scanned.error
    batch = Gem5Parser.submit_parse_async(
        str(tmp_path),
        "stats.txt",
        [ring5.StatConfig("v", "scalar", params={"source_type": "scalar"})],
        str(tmp_path / "out"),
    )
    error = batch.futures[0].exception(timeout=15)
    assert type(error) is ParseDataRuntimeError
    assert not (tmp_path / "out/results.csv").exists()


def test_optional_derived_annotations_are_ignored_only_after_literal_configuration(
    tmp_path: Path,
) -> None:
    (tmp_path / "stats.txt").write_text(
        "c=literal (Count) #keep 10%\n"
        "s 1.25 100% (Count/Second)\n"
        "v |1 25% |3 75% (Count)\nv::total 4 (Count)\n"
    )
    with ring5.Session() as session:
        parsed = session.parse(
            str(tmp_path),
            [
                ring5.StatConfig("c", "configuration", params={"source_type": "configuration"}),
                ring5.StatConfig("s", "scalar", params={"source_type": "scalar"}),
                ring5.StatConfig(
                    "v",
                    "vector",
                    statistics_only=True,
                    params={"source_type": "vector", "statistics": ["total"]},
                ),
            ],
        )
        assert session.load(parsed).rows() == [
            {"c": "literal (Count) #keep 10%", "s": 1.25, "v..total": 4.0}
        ]
