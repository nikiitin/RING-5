"""Public global shutdown drains file work before closing backend processes."""

from __future__ import annotations

import csv
import threading
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import ring5
from ring5.errors import JobError
from src.core.models import StatConfig
from src.parsing.framework.work_pool import WorkPool
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.strategies.perl_worker_pool import get_worker_pool

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("perl_pool")]


def test_global_shutdown_closes_perl_only_after_accepted_work_settles() -> None:
    # [test->req~ring5.api.process-lifecycle~1]
    ring5.shutdown()
    pool = WorkPool.get_instance()
    started = threading.Event()
    release = threading.Event()
    draining = threading.Event()
    perl_closed = threading.Event()
    errors: list[Exception] = []

    def work() -> int:
        started.set()
        assert release.wait(5)
        return 7

    def close() -> None:
        try:
            ring5.shutdown()
        except Exception as error:
            errors.append(error)

    original_drain = pool._drain_executor

    def drain(executor: Any) -> None:
        draining.set()
        original_drain(executor)

    future = pool.submit(work)
    closer = threading.Thread(target=close)
    try:
        assert started.wait(3)
        with (
            patch.object(pool, "_drain_executor", side_effect=drain),
            patch(
                "src.parsing.gem5.impl.strategies.perl_worker_pool.shutdown_worker_pool",
                side_effect=perl_closed.set,
            ),
        ):
            closer.start()
            assert draining.wait(3)
            assert not perl_closed.is_set()
            assert closer.is_alive()
            release.set()
            closer.join(3)
        assert not closer.is_alive()
        assert not errors
        assert future.result(timeout=3) == 7
        assert perl_closed.is_set()
    finally:
        release.set()
        if closer.ident is not None:
            closer.join(3)
        ring5.shutdown()


def test_global_shutdown_failure_is_typed_and_keeps_dependencies_open() -> None:
    # [test->req~ring5.api.typed-errors~1]
    ring5.shutdown()
    pool = WorkPool.get_instance()
    try:
        with patch(
            "src.parsing.gem5.impl.strategies.perl_worker_pool.shutdown_worker_pool"
        ) as close_perl:
            future = pool.submit(ring5.shutdown)
            with pytest.raises(JobError, match="own shutdown"):
                future.result(timeout=3)
            close_perl.assert_not_called()
        assert pool.submit(lambda: "usable").result(timeout=3) == "usable"
    finally:
        ring5.shutdown()


def test_real_parse_survives_global_shutdown_and_recreates_both_pools(tmp_path: Path) -> None:
    # [test->req~ring5.api.process-lifecycle~1]
    ring5.shutdown()
    stats = tmp_path / "stats.txt"
    previous_executor = None
    previous_perl = None
    try:
        for value in [3, 5]:
            stats.write_text(f"ipc {value}\n", encoding="utf-8")
            batch = Gem5Parser.submit_parse_async(
                str(tmp_path),
                "stats.txt",
                [StatConfig("ipc", "scalar")],
                str(tmp_path / str(value)),
            )
            executor = WorkPool.get_instance()._thread_executor
            perl = get_worker_pool()
            if previous_executor is not None:
                assert executor is not previous_executor
                assert perl is not previous_perl
            ring5.shutdown()
            assert all(future.done() for future in batch.futures)
            results = [future.result(timeout=3) for future in batch.futures]
            output = Gem5Parser.finalize_parsing(
                str(tmp_path / str(value)), results, var_names=batch.var_names
            )
            assert output is not None
            with Path(output).open(encoding="utf-8", newline="") as stream:
                assert next(csv.DictReader(stream))["ipc"] == f"{value}.0"
            previous_executor, previous_perl = executor, perl
    finally:
        ring5.shutdown()


def test_global_shutdown_rejects_real_parse_through_perl_teardown(tmp_path: Path) -> None:
    # [test->req~ring5.api.process-lifecycle~1]
    """Draining the executor cannot reopen admission before its dependencies close."""
    ring5.shutdown()
    get_worker_pool(pool_size=1)
    stats = tmp_path / "stats.txt"
    stats.write_text("ipc 3\n", encoding="utf-8")
    teardown_started = threading.Event()
    release_teardown = threading.Event()
    errors: list[Exception] = []
    from src.parsing.gem5.impl.strategies.perl_worker_pool import shutdown_worker_pool

    def close_perl() -> None:
        teardown_started.set()
        assert release_teardown.wait(5)
        shutdown_worker_pool()

    def close() -> None:
        try:
            ring5.shutdown()
        except Exception as error:
            errors.append(error)

    closer = threading.Thread(target=close)
    try:
        with patch(
            "src.parsing.gem5.impl.strategies.perl_worker_pool.shutdown_worker_pool",
            side_effect=close_perl,
        ):
            closer.start()
            assert teardown_started.wait(3)
            with pytest.raises(RuntimeError, match="shutting down"):
                Gem5Parser.submit_parse_async(
                    str(tmp_path), "stats.txt", [StatConfig("ipc", "scalar")], str(tmp_path / "out")
                )
            release_teardown.set()
            closer.join(3)
        assert not closer.is_alive()
        assert not errors
        batch = Gem5Parser.submit_parse_async(
            str(tmp_path), "stats.txt", [StatConfig("ipc", "scalar")], str(tmp_path / "retry")
        )
        assert batch.futures[0].result(timeout=3)["ipc"].content == [3.0]
    finally:
        release_teardown.set()
        if closer.ident is not None:
            closer.join(3)
        ring5.shutdown()


def test_concurrent_global_shutdowns_serialize_dependency_teardown() -> None:
    ring5.shutdown()
    pool = WorkPool.get_instance()
    entered = [threading.Event(), threading.Event()]
    release = [threading.Event(), threading.Event()]
    calls: list[int] = []
    errors: list[Exception] = []
    counts = {"active": 0, "maximum": 0}
    lock = threading.Lock()

    def close_perl() -> None:
        with lock:
            index = len(calls)
            calls.append(index)
            counts["active"] += 1
            counts["maximum"] = max(counts["maximum"], counts["active"])
        entered[index].set()
        assert release[index].wait(5)
        with lock:
            counts["active"] -= 1

    def close() -> None:
        try:
            ring5.shutdown()
        except Exception as error:
            errors.append(error)

    closers = [threading.Thread(target=close), threading.Thread(target=close)]
    try:
        with patch(
            "src.parsing.gem5.impl.strategies.perl_worker_pool.shutdown_worker_pool",
            side_effect=close_perl,
        ):
            closers[0].start()
            assert entered[0].wait(3)
            closers[1].start()
            assert not entered[1].wait(0.05)
            release[0].set()
            assert entered[1].wait(3)
            with pytest.raises(RuntimeError, match="shutting down"):
                pool.submit(lambda: "too early")
            release[1].set()
            for closer in closers:
                closer.join(3)
        assert all(not closer.is_alive() for closer in closers)
        assert not errors
        assert calls == [0, 1]
        assert counts["maximum"] == 1
        assert pool.submit(lambda: "reopened").result(timeout=3) == "reopened"
    finally:
        for event in release:
            event.set()
        for closer in closers:
            if closer.ident is not None:
                closer.join(3)
        ring5.shutdown()


@pytest.mark.parametrize("stage", ["drain", "dependencies"])
def test_failed_global_shutdown_keeps_admission_closed_until_global_retry(stage: str) -> None:
    ring5.shutdown()
    pool = WorkPool.get_instance()
    target = (
        patch.object(pool, "shutdown", side_effect=RuntimeError("drain failed"))
        if stage == "drain"
        else patch(
            "src.parsing.gem5.impl.strategies.perl_worker_pool.shutdown_worker_pool",
            side_effect=RuntimeError("dependencies failed"),
        )
    )
    try:
        with target:
            with pytest.raises(JobError, match=f"{stage} failed"):
                ring5.shutdown()
        pool.shutdown(wait=True)
        with pytest.raises(RuntimeError, match="shutting down"):
            pool.submit(lambda: "too early")
        ring5.shutdown()
        assert pool.submit(lambda: "reopened").result(timeout=3) == "reopened"
    finally:
        ring5.shutdown()


def test_worker_global_shutdown_checks_context_before_waiting_for_global_lock() -> None:
    ring5.shutdown()
    pool = WorkPool.get_instance()
    worker_started = threading.Event()
    draining = threading.Event()
    errors: list[Exception] = []
    original_drain = pool._drain_executor

    class GuardedLock:
        """Turn a wrong worker lock acquisition into a failure without hanging the test."""

        def __init__(self) -> None:
            self.lock = threading.Lock()

        def __enter__(self) -> None:
            assert not getattr(pool._worker_context, "active", False)
            self.lock.acquire()

        def __exit__(self, *_: Any) -> None:
            self.lock.release()

    def drain(executor: Any) -> None:
        draining.set()
        original_drain(executor)

    def worker() -> str:
        worker_started.set()
        assert draining.wait(3)
        with pytest.raises(JobError, match="own shutdown"):
            ring5.shutdown()
        return "settled"

    def close() -> None:
        try:
            ring5.shutdown()
        except Exception as error:
            errors.append(error)

    closer = threading.Thread(target=close)
    try:
        with (
            patch.object(pool, "_global_shutdown_lock", GuardedLock()),
            patch.object(pool, "_drain_executor", side_effect=drain),
        ):
            future = pool.submit(worker)
            assert worker_started.wait(3)
            closer.start()
            closer.join(3)
            assert not closer.is_alive()
            assert future.result(timeout=3) == "settled"
        assert not errors
    finally:
        draining.set()
        if closer.ident is not None:
            closer.join(3)
        ring5.shutdown()
