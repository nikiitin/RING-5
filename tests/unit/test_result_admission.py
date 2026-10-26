"""Batch result quotas apply before Future retention and never recycle accepted data."""

from __future__ import annotations

import gc
import json
import weakref
from concurrent.futures import CancelledError, ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

import pytest

from src.core.common.parsed_output_codec import iter_parsed_file_encoding
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.core.models.parse_failure_models import ResultAdmissionError
from src.parsing.framework import incremental_cache, result_admission
from src.parsing.framework.incremental_cache import encode_cache, load_cache
from src.parsing.framework.result_admission import (
    AdmittedParseWork,
    ResultAdmission,
)
from src.parsing.framework.work_pool import WorkPool


def _file(
    source: str, cells: int = 1, *, name: str = "v", text: str | None = None
) -> ParsedFileResult:
    if text is not None:
        variable = ParsedVariableResult(
            "v", "text", "scalar", (ParsedCell(name, "text", text),), layout=None
        )
    else:
        variable = ParsedVariableResult(
            "v",
            "number",
            "entries",
            tuple(ParsedCell(f"{name}{index}", "number", float(index)) for index in range(cells)),
            layout=None,
        )
    return ParsedFileResult(source, (variable,))


class _FreshWork:
    def __init__(
        self, source: str, refs: list, *, barrier: Barrier | None = None, text: bool = False
    ) -> None:
        self.source_path = source
        self._refs = refs
        self._barrier = barrier
        self._text = text

    def __call__(self) -> ParsedFileResult:
        if self._barrier is not None:
            self._barrier.wait(timeout=5)
        value = _file(self.source_path, text="x" * 100_000 if self._text else None)
        self._refs.append(weakref.ref(value))
        return value


def test_source_association_and_failed_cell_admission_commit_no_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(result_admission, "MAX_PARSE_MATRIX_CELLS", 2)
    admission = ResultAdmission(("a", "b"))
    with pytest.raises(ResultAdmissionError, match="planned source"):
        admission.admit(_file("b"), source_path="a")
    admission.admit(_file("a", 2), source_path="a")
    with pytest.raises(ResultAdmissionError, match="cell admission"):
        admission.admit(_file("b"), source_path="b")
    admission.admit(_file("b", 0), source_path="b")
    with pytest.raises(ResultAdmissionError, match="duplicate"):
        admission.admit(_file("a", 0), source_path="a")


def test_record_bytes_charge_repeated_names_and_failed_admission_commits_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _file("a", name="long" * 100)
    second = _file("b", name="long" * 100)
    size = len(b"".join(iter_parsed_file_encoding(first)))
    assert size == len(b"".join(iter_parsed_file_encoding(second)))
    monkeypatch.setattr(result_admission, "MAX_PARSE_RESULT_BYTES", size * 2 - 1)
    admission = ResultAdmission(("a", "b"))
    admission.admit(first, source_path="a")
    with pytest.raises(ResultAdmissionError, match="retained-record"):
        admission.admit(second, source_path="b")
    admission.admit(_file("b"), source_path="b")


@pytest.mark.parametrize("mode", ["cells", "bytes"])
def test_rejected_value_and_work_are_released_while_failed_future_is_retained(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    refs = []
    if mode == "cells":
        monkeypatch.setattr(result_admission, "MAX_PARSE_MATRIX_CELLS", 0)
    else:
        size = len(b"".join(iter_parsed_file_encoding(_file("source", text="x" * 100_000))))
        monkeypatch.setattr(result_admission, "MAX_PARSE_RESULT_BYTES", size - 1)
    admission = ResultAdmission(("source",))
    work = _FreshWork("source", refs, text=True)
    work_ref = weakref.ref(work)
    wrapper = AdmittedParseWork(work, admission)
    del work
    future = WorkPool.get_instance().submit(wrapper)
    with pytest.raises(ResultAdmissionError):
        future.result(timeout=5)
    gc.collect()
    assert len(refs) == 1 and refs[0]() is None
    assert work_ref() is None
    assert isinstance(future.exception(), ResultAdmissionError)
    assert future.exception().__context__ is None
    assert wrapper.source_path == "source"
    with pytest.raises(RuntimeError, match="only once"):
        wrapper()


def test_concurrent_results_cannot_overshoot_atomic_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(result_admission, "MAX_PARSE_MATRIX_CELLS", 1)
    admission = ResultAdmission(("a", "b"))
    barrier = Barrier(2)
    refs = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(AdmittedParseWork(_FreshWork(source, refs, barrier=barrier), admission))
            for source in ("a", "b")
        ]
        values, errors = [], []
        for future in futures:
            try:
                values.append(future.result(timeout=5))
            except ResultAdmissionError as exc:
                errors.append(str(exc))
    assert len(values) == len(errors) == 1
    assert sum(len(variable.cells) for value in values for variable in value.variables) == 1


def test_cancelled_pending_work_consumes_no_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(result_admission, "MAX_PARSE_MATRIX_CELLS", 1)
    admission = ResultAdmission(("a",))
    entered, release = Event(), Event()

    def block():
        entered.set()
        assert release.wait(5)

    with ThreadPoolExecutor(max_workers=1) as executor:
        blocker = executor.submit(block)
        assert entered.wait(5)
        future = executor.submit(AdmittedParseWork(_FreshWork("a", []), admission))
        assert future.cancel()
        release.set()
        blocker.result(timeout=5)
        with pytest.raises(CancelledError):
            future.result()
    admission.admit(_file("a"), source_path="a")


def test_cache_admits_matching_records_during_decode_and_keeps_resource_failures_visible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "cache.json"
    fingerprints = (("a", "b" * 64), ("b", "c" * 64), ("obsolete", "d" * 64))
    values = [_file("a", 2), _file("b", 2), _file("obsolete", 2)]
    path.write_bytes(encode_cache("a" * 64, ("v",), fingerprints, values))
    monkeypatch.setattr(result_admission, "MAX_PARSE_MATRIX_CELLS", 3)
    with pytest.raises(ResultAdmissionError, match="cell admission"):
        load_cache(path, "a" * 64, fingerprints[:2])
    reuse = load_cache(path, "a" * 64, (("a", "b" * 64), ("b", "e" * 64)))
    assert tuple(value.source_path for value in reuse.results) == ("a",)
    assert reuse.removed_files == ("obsolete",)
    with pytest.raises(ResultAdmissionError, match="cell admission"):
        reuse.admission.admit(_file("b", 2), source_path="b")


def test_malformed_cache_discards_provisional_context_before_any_worker_owns_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = tmp_path / "cache.json"
    fingerprints = (("a", "b" * 64), ("b", "c" * 64))
    payload = json.loads(encode_cache("a" * 64, ("v",), fingerprints, [_file("a"), _file("b")]))
    payload["files"][1]["result"]["retired"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    decoded = []
    original = incremental_cache.parsed_file_from_payload

    def track(value, **kwargs):
        result = original(value, **kwargs)
        decoded.append(weakref.ref(result))
        return result

    monkeypatch.setattr(incremental_cache, "parsed_file_from_payload", track)
    reuse = load_cache(path, "a" * 64, fingerprints)
    assert reuse.results == () and reuse.var_names == ()
    gc.collect()
    assert len(decoded) == 1 and decoded[0]() is None
    assert caplog.records
    assert all(
        not isinstance(argument, BaseException)
        for record in caplog.records
        for argument in record.args
    )
    reuse.admission.admit(_file("a"), source_path="a")
    reuse.admission.admit(_file("b"), source_path="b")
