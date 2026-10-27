"""Expected parser failures retain useful facts, never producer object graphs."""

from __future__ import annotations

import errno
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from types import SimpleNamespace
from typing import NoReturn, cast

import pytest

from src.core.common.parse_failure import (
    MAX_PARSE_FAILURE_CAUSE,
    MAX_PARSE_FAILURE_MESSAGE,
    MAX_PARSE_FAILURE_ORIGIN,
    classify_parse_failure,
    detach_parse_failure,
    parse_error_text,
)
from src.core.models.parse_failure_models import (
    ParseDataRuntimeError,
    ParseDataTypeError,
    ParseDataValueError,
    ParseFailureFacts,
    ResultAdmissionError,
)
from src.parsing.framework.result_admission import AdmittedParseWork, ResultAdmission
from src.parsing.gem5.impl.strategies.perl_worker_pool import PerlWorker, PerlWorkerPool


@pytest.mark.parametrize(
    "error_type",
    [ParseDataRuntimeError, ParseDataTypeError, ParseDataValueError, ResultAdmissionError],
)
def test_expected_failure_keeps_concrete_type_and_bounded_immutable_facts(
    error_type: type[
        ParseDataRuntimeError | ParseDataTypeError | ParseDataValueError | ResultAdmissionError
    ],
) -> None:
    original = error_type("specific data rejection " + "x" * 10_000)
    original.add_note("not retained " + "y" * 10_000)
    original.__cause__ = UnicodeDecodeError("utf8", b"raw buffer" * 10_000, 0, 1, "bad byte")

    def fail(depth: int) -> None:
        if depth:
            fail(depth - 1)
        raise original

    try:
        fail(12)
    except error_type as caught:
        fresh = detach_parse_failure(caught, "/planned/stats.txt")
    assert fresh is not None
    assert type(fresh) is error_type and fresh is not original
    assert fresh.args[0].startswith("specific data rejection")
    assert len(fresh.args[0]) <= MAX_PARSE_FAILURE_MESSAGE
    assert fresh.args[0].endswith("[truncated]")
    assert fresh.__traceback__ is None and fresh.__cause__ is None and fresh.__context__ is None
    assert not hasattr(fresh, "__notes__")
    facts: object = getattr(fresh, "failure_facts")
    assert type(facts) is ParseFailureFacts
    assert facts.source_path == "/planned/stats.txt"
    assert len(facts.origin) <= MAX_PARSE_FAILURE_ORIGIN
    assert facts.origin.count(" <- ") == 7 and ".fail:" in facts.origin
    assert len(facts.cause) <= MAX_PARSE_FAILURE_CAUSE
    assert "UnicodeDecodeError" in facts.cause and "bad byte" in facts.cause
    assert "raw buffer" not in facts.cause


@pytest.mark.parametrize(
    "error_type,code",
    [
        (FileNotFoundError, errno.ENOENT),
        (FileExistsError, errno.EEXIST),
        (IsADirectoryError, errno.EISDIR),
        (NotADirectoryError, errno.ENOTDIR),
        (PermissionError, errno.EACCES),
        (BrokenPipeError, errno.EPIPE),
        (ConnectionResetError, errno.ECONNRESET),
        (InterruptedError, errno.EINTR),
        (TimeoutError, errno.ETIMEDOUT),
        (OSError, errno.EIO),
    ],
)
def test_builtin_io_failure_preserves_exact_errno_and_both_filenames(
    error_type: type[OSError], code: int
) -> None:
    original = error_type(code, "specific IO failure", "/input", None, "/output")
    fresh = detach_parse_failure(original, "/planned/stats.txt")
    assert isinstance(fresh, OSError)
    assert type(fresh) is error_type
    assert fresh.errno == code and fresh.strerror == "specific IO failure"
    assert fresh.filename == "/input" and fresh.filename2 == "/output"
    assert str(fresh) == str(original)
    assert fresh.__cause__ is None and fresh.__context__ is None and fresh.__traceback__ is None


def test_diagnostic_rendering_never_invokes_arbitrary_argument_hooks() -> None:
    class Forbidden:
        def __str__(self) -> str:
            pytest.fail("an arbitrary diagnostic string hook ran")

        def __repr__(self) -> str:
            pytest.fail("an arbitrary diagnostic repr hook ran")

    assert parse_error_text(ParseDataValueError(Forbidden())) == "<Forbidden>"


def test_non_native_io_metadata_is_declined_before_constructor_hooks() -> None:
    class Forbidden:
        def __index__(self) -> int:
            pytest.fail("an arbitrary IO constructor hook ran")

    for field, value in (
        ("errno", Forbidden()),
        ("errno", 1 << 100_000),
        ("filename", object()),
    ):
        error = OSError(errno.EIO, "invalid IO metadata")
        setattr(error, field, value)
        assert classify_parse_failure(error) is None
        assert detach_parse_failure(error, "/source") is None


def test_unmarked_programming_exception_retains_identity_and_original_traceback() -> None:
    unexpected = RuntimeError("unexpected implementation failure")

    class Work:
        source_path = "/planned/stats.txt"

        def __call__(self) -> NoReturn:
            raise unexpected

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(AdmittedParseWork(Work(), ResultAdmission((Work.source_path,))))
        error = future.exception(timeout=5)
    assert error is unexpected
    names = []
    node = error.__traceback__
    while node:
        names.append(node.tb_frame.f_code.co_name)
        node = node.tb_next
    assert names.count("__call__") == 2
    assert not hasattr(error, "failure_facts")


def test_io_and_nominal_subclass_hooks_are_not_used_for_cloning() -> None:
    class ExternalIO(FileNotFoundError):
        pass

    class ExternalData(ParseDataValueError):
        pass

    assert detach_parse_failure(ExternalIO("custom"), "/input") is None
    assert detach_parse_failure(ExternalData("custom"), "/input") is None


def test_pool_retry_does_not_swallow_unmarked_programming_error() -> None:
    unexpected = RuntimeError("unexpected worker implementation failure")

    def fail(*args: object) -> NoReturn:
        raise unexpected

    worker = SimpleNamespace(worker_id=0, is_healthy=True, is_busy=False, parse_file=fail)
    pool = SimpleNamespace(workers=[worker], _lock=threading.Lock(), worker_queue=queue.Queue())
    pool.worker_queue.put(worker)
    with pytest.raises(RuntimeError) as caught:
        # Exercise the real method with an inert receiver, without starting a pool.
        PerlWorkerPool.parse_file(cast(PerlWorkerPool, pool), "/input", ["v"])
    assert caught.value is unexpected
    assert worker.is_busy is False and pool.worker_queue.get_nowait() is worker


def test_worker_transport_does_not_convert_unmarked_programming_error_to_retry() -> None:
    unexpected = RuntimeError("unexpected reader implementation failure")

    def fail(*, timeout: float) -> NoReturn:
        raise unexpected

    worker = SimpleNamespace(
        worker_id=0,
        is_healthy=True,
        _lock=threading.Lock(),
        process=SimpleNamespace(stdin=StringIO()),
        _read_line_with_timeout=fail,
    )
    with pytest.raises(RuntimeError) as caught:
        # Exercise the transport owner without spawning its subprocess.
        PerlWorker.parse_file(cast(PerlWorker, worker), "/input", ["v"])
    assert caught.value is unexpected and worker.is_healthy
