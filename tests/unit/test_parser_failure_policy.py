"""Exact failure policy and generation ownership survive inner retries and startup."""

from __future__ import annotations

import configparser
import gc
import queue
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from io import StringIO
from types import SimpleNamespace

import pytest

from src.core.common.parse_failure import classify_parse_failure, detach_parse_failure
from src.core.models.parse_failure_models import (
    ParseDataRuntimeError,
    ParseDataValueError,
    ResultAdmissionError,
)
from src.core.common import parsed_output_codec
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.parsing.framework import result_admission
from src.parsing.framework.result_admission import AdmittedParseWork, ResultAdmission
from src.parsing.gem5.impl.strategies import config_aware, gem5_parse_work, perl_worker_pool
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.impl.strategies.perl_worker_pool import PerlWorker, PerlWorkerPool

pytestmark = pytest.mark.xdist_group("perl_pool")


class ExternalIO(FileNotFoundError):
    pass


class ExternalTimeout(TimeoutError):
    pass


class ExternalValue(ParseDataValueError):
    pass


class ExternalRuntime(ParseDataRuntimeError):
    pass


class ExternalConfig(configparser.ParsingError):
    pass


class ExternalAdmission(ResultAdmissionError):
    pass


class ExternalEmpty(queue.Empty):
    pass


class ExternalUnicode(UnicodeDecodeError):
    pass


@pytest.mark.parametrize("error_type", [ExternalIO, ExternalTimeout, ValueError, ExternalUnicode])
def test_reader_transports_exact_stream_error_then_eof_without_reclassification(error_type) -> None:
    original = (
        error_type("utf8", b"bad buffer", 0, 1, "sentinel")
        if error_type is ExternalUnicode
        else error_type("reader implementation sentinel")
    )

    def fail():
        raise original

    owned_queue = queue.Queue()
    owner = SimpleNamespace(worker_id=0, _line_queue=owned_queue)
    PerlWorker._start_reader_thread(owner, SimpleNamespace(readline=fail), owned_queue)
    owner._reader_thread.join(timeout=5)
    assert not owner._reader_thread.is_alive()
    with pytest.raises(error_type) as caught:
        PerlWorker._read_line_with_timeout(owner)
    assert caught.value is original
    with pytest.raises(ParseDataRuntimeError, match="EOF"):
        PerlWorker._read_line_with_timeout(owner)


@pytest.mark.parametrize(
    "error_type", [ExternalIO, ExternalTimeout, ExternalValue, ExternalRuntime, ValueError]
)
def test_worker_and_pool_do_not_retry_unsupported_stream_failures(error_type) -> None:
    original = error_type("unsupported stream failure")
    owned_queue = queue.Queue()
    owned_queue.put(original)
    worker = SimpleNamespace(
        worker_id=0,
        is_healthy=True,
        is_busy=False,
        _lock=threading.Lock(),
        _line_queue=owned_queue,
        process=SimpleNamespace(stdin=StringIO()),
    )
    worker._read_line_with_timeout = lambda **kwargs: PerlWorker._read_line_with_timeout(
        worker, **kwargs
    )
    worker.parse_file = lambda *args: PerlWorker.parse_file(worker, *args)
    pool = SimpleNamespace(workers=[worker], _lock=threading.Lock(), worker_queue=queue.Queue())
    pool.worker_queue.put(worker)
    with pytest.raises(error_type) as caught:
        PerlWorkerPool.parse_file(pool, "/input", ["v"])
    assert caught.value is original and worker.is_healthy and not worker.is_busy
    assert pool.worker_queue.get_nowait() is worker


@pytest.mark.parametrize(
    "error_type", [ExternalIO, ExternalTimeout, ExternalValue, ExternalRuntime, RuntimeError]
)
def test_gem5_inner_transport_does_not_turn_unsupported_errors_into_known_data_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type
) -> None:
    source = tmp_path / "stats.txt"
    source.write_text("v 1\n")
    original = error_type("implementation sentinel")
    work = Gem5ParseWork.__new__(Gem5ParseWork)
    work._file_to_parse, work._routes = str(source), {"v": None}

    def fail(*args, **kwargs):
        raise original

    monkeypatch.setattr(
        gem5_parse_work, "get_worker_pool", lambda: SimpleNamespace(parse_file=fail)
    )

    class Task:
        source_path = str(source)

        def __call__(self):
            return work._run_perl_script()

    assert classify_parse_failure(original) is None
    assert detach_parse_failure(original, str(source)) is None
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(AdmittedParseWork(Task(), ResultAdmission((str(source),))))
        error = future.exception(timeout=5)
    assert error is original and not hasattr(error, "failure_facts")
    names = []
    node = error.__traceback__
    while node:
        names.append(node.tb_frame.f_code.co_name)
        node = node.tb_next
    assert "fail" in names and "_run_perl_script" in names


@pytest.mark.parametrize("error_type", [ExternalIO, ExternalConfig])
def test_config_owner_rethrows_unsupported_subtypes_before_wrapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type
) -> None:
    path = tmp_path / "config.ini"
    path.write_text("[system]\nv=1\n")
    original = error_type("implementation sentinel")

    def fail(*args, **kwargs):
        raise original

    if error_type is ExternalIO:
        monkeypatch.setattr(Path, "open", fail)
    else:
        monkeypatch.setattr(config_aware._LiteralConfigParser, "read_string", fail)
    with pytest.raises(error_type) as caught:
        config_aware.ConfigAwareParseWork._read_config(path)
    assert caught.value is original and not hasattr(original, "failure_facts")


@pytest.mark.parametrize(
    "error_type",
    [ValueError, TypeError, ExternalIO, ExternalValue, ExternalRuntime, ExternalAdmission],
)
def test_admission_codec_programming_errors_keep_identity_and_original_traceback(
    monkeypatch: pytest.MonkeyPatch, error_type
) -> None:
    original = error_type("unexpected codec implementation failure")

    def fail(result):
        raise original

    class Work:
        source_path = "source"

        def __call__(self):
            return ParsedFileResult("source", ())

    monkeypatch.setattr(result_admission, "iter_parsed_file_encoding", fail)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(AdmittedParseWork(Work(), ResultAdmission(("source",))))
        error = future.exception(timeout=5)
    assert error is original and not hasattr(error, "failure_facts")
    node = error.__traceback__
    while node.tb_next:
        node = node.tb_next
    assert node.tb_frame.f_code.co_name == "fail"


@pytest.mark.parametrize("mode", ["cell_limit", "surrogate"])
def test_real_cell_encoding_rejection_releases_result_and_work_while_future_is_held(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.setattr(parsed_output_codec, "MAX_PARSED_CELL_CHARACTERS", 4096)
    refs = []

    class Work:
        source_path = "source"

        def __call__(self):
            text = "x" * 4097 if mode == "cell_limit" else "\ud800"
            result = ParsedFileResult(
                "source",
                (ParsedVariableResult("v", "text", "scalar", (ParsedCell("v", "text", text),)),),
            )
            refs.append(weakref.ref(result))
            return result

    work = Work()
    work_ref = weakref.ref(work)
    wrapper = AdmittedParseWork(work, ResultAdmission(("source",)))
    del work
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(wrapper)
        error = future.exception(timeout=5)
    assert type(error) is ResultAdmissionError
    expected = "character limit" if mode == "cell_limit" else "surrogates not allowed"
    assert expected in str(error) and len(str(error)) <= 1024
    assert error.__context__ is error.__cause__ is None
    assert error.failure_facts.source_path == "source"
    assert wrapper._admission._cells == wrapper._admission._bytes == 0
    gc.collect()
    assert work_ref() is None and len(refs) == 1 and refs[0]() is None


@pytest.mark.parametrize("owner", ["worker", "pool"])
@pytest.mark.parametrize("error_type", [queue.Empty, ExternalEmpty])
def test_queue_timeout_translation_uses_exact_transport_failure_policy(owner, error_type) -> None:
    original = error_type("queue sentinel")

    def fail(**kwargs):
        raise original

    owned_queue = SimpleNamespace(get=fail)
    if owner == "worker":
        target = SimpleNamespace(_line_queue=owned_queue, worker_id=0)

        def call():
            return PerlWorker._read_line_with_timeout(target)

    else:
        target = SimpleNamespace(
            workers=[SimpleNamespace(is_healthy=True)],
            _lock=threading.Lock(),
            worker_queue=owned_queue,
        )

        def call():
            return PerlWorkerPool.parse_file(target, "/input", ["v"])

    if error_type is ExternalEmpty:
        with pytest.raises(ExternalEmpty) as caught:
            call()
        assert caught.value is original
    else:
        with pytest.raises(TimeoutError):
            call()


def _script() -> str:
    return str(Path(perl_worker_pool.__file__).parents[2] / "perl" / "fileParserServer.pl")


def _assert_generation_closed(process, worker) -> None:
    assert process.poll() is not None
    assert all(pipe.closed for pipe in (process.stdin, process.stdout, process.stderr))
    assert worker.process is None and not worker.is_healthy
    assert worker._line_queue is None
    for thread in (worker._reader_thread, worker._stderr_thread):
        assert thread is None or not thread.is_alive()


@pytest.mark.parametrize("stage", ["reader", "stderr", "ready", "unsupported_io"])
def test_partial_worker_startup_reaps_its_exact_process_and_readers(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    real_popen = perl_worker_pool.subprocess.Popen
    processes, owners = [], []
    unexpected = (
        ExternalIO("unsupported startup IO")
        if stage == "unsupported_io"
        else RuntimeError("unexpected startup implementation failure")
    )

    def track_process(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(perl_worker_pool.subprocess, "Popen", track_process)
    if stage in {"reader", "stderr"}:
        method = "_start_reader_thread" if stage == "reader" else "_start_stderr_drainer"
        original = getattr(PerlWorker, method)

        def fail(self, *args, **kwargs):
            owners.append(self)
            original(self, *args, **kwargs)
            raise unexpected

        monkeypatch.setattr(PerlWorker, method, fail)
    else:

        def ready(self, **kwargs):
            owners.append(self)
            if stage == "ready":
                return "WRONG"
            raise unexpected

        monkeypatch.setattr(PerlWorker, "_read_line_with_timeout", ready)
    expected_type = ParseDataRuntimeError if stage == "ready" else type(unexpected)
    with pytest.raises(expected_type) as caught:
        PerlWorker(0, _script(), "perl")
    if stage != "ready":
        assert caught.value is unexpected
    assert len(processes) == len(owners) == 1
    _assert_generation_closed(processes[0], owners[0])


@pytest.mark.parametrize("failure", [RuntimeError, ExternalIO, ExternalRuntime])
def test_unexpected_second_worker_startup_closes_all_previously_started_workers(
    monkeypatch: pytest.MonkeyPatch, failure
) -> None:
    real_worker, created = PerlWorker, []
    original = failure("unexpected second worker startup failure")

    def build(*args, **kwargs):
        if created:
            raise original
        worker = real_worker(*args, **kwargs)
        created.append((worker, worker.process))
        return worker

    monkeypatch.setattr(perl_worker_pool, "PerlWorker", build)
    with pytest.raises(failure) as caught:
        PerlWorkerPool(pool_size=2)
    assert caught.value is original and len(created) == 1
    _assert_generation_closed(created[0][1], created[0][0])


def test_pool_monitor_startup_failure_stops_monitor_and_every_started_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = RuntimeError("unexpected monitor startup failure")
    captured = []
    start = PerlWorkerPool._start_health_monitor

    def fail(self):
        start(self)
        captured.append((self, self._health_monitor_thread, [(w, w.process) for w in self.workers]))
        raise original

    monkeypatch.setattr(PerlWorkerPool, "_start_health_monitor", fail)
    with pytest.raises(RuntimeError) as caught:
        PerlWorkerPool(pool_size=2)
    assert caught.value is original
    pool, monitor, workers = captured[0]
    assert pool._shutdown_event.is_set() and not monitor.is_alive()
    for worker, process in workers:
        _assert_generation_closed(process, worker)


def test_failing_restart_cleanup_cannot_close_the_next_concurrent_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker = PerlWorker(0, _script(), "perl")
    unexpected = RuntimeError("unexpected first restart failure")
    cleanup_entered, release_cleanup, second_entered = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    failed_generations = []
    original_read = PerlWorker._read_line_with_timeout
    original_retire = PerlWorker._retire_generation

    def fail_first(self, **kwargs):
        if not failed_generations:
            failed_generations.append((self.process, self._reader_thread, self._stderr_thread))
            raise unexpected
        return original_read(self, **kwargs)

    def gated_cleanup(self, generation):
        if failed_generations and generation.process is failed_generations[0][0]:
            cleanup_entered.set()
            assert release_cleanup.wait(timeout=5)
        return original_retire(self, generation)

    def restart_second():
        second_entered.set()
        return worker.restart()

    monkeypatch.setattr(PerlWorker, "_read_line_with_timeout", fail_first)
    monkeypatch.setattr(PerlWorker, "_retire_generation", gated_cleanup)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(worker.restart)
            assert cleanup_entered.wait(timeout=5)
            second = executor.submit(restart_second)
            assert second_entered.wait(timeout=5) and not second.done()
            assert worker.process is failed_generations[0][0]
            release_cleanup.set()
            assert first.exception(timeout=5) is unexpected
            assert second.result(timeout=5) is True
        failed_process, reader, stderr = failed_generations[0]
        assert failed_process.poll() is not None
        assert all(
            pipe.closed
            for pipe in (failed_process.stdin, failed_process.stdout, failed_process.stderr)
        )
        assert not reader.is_alive() and not stderr.is_alive()
        assert worker.is_healthy and worker.process is not failed_process
        source = tmp_path / "stats.txt"
        source.write_text("v 1\n")
        lines, success = worker.parse_file(str(source), ["v"])
        assert success and "scalar/v/1" in lines
    finally:
        release_cleanup.set()
        worker.shutdown()
