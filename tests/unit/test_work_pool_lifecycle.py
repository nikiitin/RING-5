"""Deterministic submission, retirement, and recreation contracts."""

from __future__ import annotations

import threading
from collections.abc import Generator
from concurrent.futures import Future
from typing import Any
from unittest.mock import patch

import pytest

from src.parsing.framework.work_pool import WorkPool, _shutdown_workpool


@pytest.fixture
def pool(monkeypatch: pytest.MonkeyPatch) -> Generator[WorkPool, None, None]:
    _shutdown_workpool()
    monkeypatch.setenv("RING5_WORK_POOL_SIZE", "1")
    instance = WorkPool.get_instance()
    yield instance
    _shutdown_workpool()


class TestWorkPoolLifecycle:
    # [test->req~ring5.api.process-lifecycle~1]

    def test_executor_is_lazy_bounded_and_reused(self, pool: WorkPool) -> None:
        assert pool._thread_executor is None
        assert pool.submit(lambda: 1).result(timeout=3) == 1
        executor = pool._thread_executor
        assert executor is not None
        assert executor._max_workers == 1
        assert pool.submit(lambda: 2).result(timeout=3) == 2
        assert pool._thread_executor is executor

    def test_invalid_batch_fails_before_any_work_is_submitted(self, pool: WorkPool) -> None:
        started = threading.Event()
        with pytest.raises(TypeError, match="callable"):
            pool.submit_many([started.set, None])  # type: ignore[list-item]
        assert not started.is_set()
        assert pool._thread_executor is None
        assert pool.submit_many([]) == []

    def test_nonwaiting_shutdown_can_be_joined_and_recreated_without_overlap(
        self, pool: WorkPool
    ) -> None:
        started = threading.Event()
        release = threading.Event()
        finished = [threading.Event(), threading.Event()]

        def running() -> int:
            started.set()
            assert release.wait(5)
            return 7

        future = pool.submit(running)
        executor = pool._thread_executor
        waiters = [
            threading.Thread(target=lambda done=done: (pool.shutdown(wait=True), done.set()))
            for done in finished
        ]
        try:
            assert started.wait(3)
            pool.shutdown(wait=False)
            with pytest.raises(RuntimeError, match="shutting down"):
                pool.submit(lambda: 99)
            assert pool._thread_executor is None
            for waiter in waiters:
                waiter.start()
            assert not any(done.wait(0.05) for done in finished)
            release.set()
            for waiter in waiters:
                waiter.join(3)
            assert all(done.is_set() for done in finished)
            assert future.result(timeout=3) == 7
            pool.shutdown(wait=True)
            assert pool.submit(lambda: 8).result(timeout=3) == 8
            assert pool._thread_executor is not executor
        finally:
            release.set()
            for waiter in waiters:
                if waiter.ident is not None:
                    waiter.join(3)

    def test_worker_resubmission_during_drain_fails_without_deadlock(self, pool: WorkPool) -> None:
        started = threading.Event()
        draining = threading.Event()
        lock_available: list[bool] = []

        def running() -> str:
            started.set()
            assert draining.wait(3)
            with pytest.raises(RuntimeError, match="shutting down"):
                pool.submit(lambda: "unexpected")
            return "settled"

        future = pool.submit(running)
        executor = pool._thread_executor
        assert executor is not None
        original_shutdown = executor.shutdown

        def observed_shutdown(*, wait: bool = True) -> None:
            available = pool._executor_lock.acquire(blocking=False)
            lock_available.append(available)
            if available:
                pool._executor_lock.release()
            draining.set()
            # A lock-order regression must fail this test without hanging its cleanup.
            original_shutdown(wait=wait if available else False)

        try:
            assert started.wait(3)
            with patch.object(executor, "shutdown", side_effect=observed_shutdown):
                pool.shutdown(wait=True)
            assert lock_available == [True]
            assert future.result(timeout=3) == "settled"
        finally:
            draining.set()
            original_shutdown(wait=True)

    def test_shutdown_cannot_close_an_executor_between_selection_and_dispatch(
        self, pool: WorkPool
    ) -> None:
        assert pool.submit(lambda: 0).result(timeout=3) == 0
        executor = pool._thread_executor
        assert executor is not None
        dispatch_started = threading.Event()
        release_dispatch = threading.Event()
        shutdown_called = threading.Event()
        futures: list[Future[Any]] = []
        errors: list[BaseException] = []
        original_submit = executor.submit
        original_shutdown = executor.shutdown

        def delayed_submit(task: Any) -> Future[Any]:
            dispatch_started.set()
            assert release_dispatch.wait(5)
            return original_submit(task)

        def observed_shutdown(*, wait: bool = True) -> None:
            shutdown_called.set()
            original_shutdown(wait=wait)

        def submit() -> None:
            try:
                futures.append(pool.submit(lambda: 42))
            except Exception as error:
                errors.append(error)

        submitter = threading.Thread(target=submit)
        closer = threading.Thread(target=lambda: pool.shutdown(wait=True))
        try:
            with (
                patch.object(executor, "submit", side_effect=delayed_submit),
                patch.object(executor, "shutdown", side_effect=observed_shutdown),
            ):
                submitter.start()
                assert dispatch_started.wait(3)
                closer.start()
                assert not shutdown_called.wait(0.05)
                release_dispatch.set()
                submitter.join(3)
                closer.join(3)
            assert not submitter.is_alive()
            assert not closer.is_alive()
            assert not errors
            assert [future.result(timeout=3) for future in futures] == [42]
        finally:
            release_dispatch.set()
            submitter.join(3)
            if closer.ident is not None:
                closer.join(3)
            original_shutdown(wait=True)

    def test_worker_cannot_wait_for_its_own_shutdown(self, pool: WorkPool) -> None:
        future = pool.submit(lambda: pool.shutdown(wait=True))
        with pytest.raises(RuntimeError, match="own shutdown"):
            future.result(timeout=3)
        assert pool.submit(lambda: "usable").result(timeout=3) == "usable"

    def test_failed_drain_keeps_submissions_closed_until_a_successful_retry(
        self, pool: WorkPool
    ) -> None:
        assert pool.submit(lambda: 1).result(timeout=3) == 1
        executor = pool._thread_executor
        assert executor is not None
        with patch.object(executor, "shutdown", side_effect=RuntimeError("join failed")):
            with pytest.raises(RuntimeError, match="join failed"):
                pool.shutdown(wait=True)
        with pytest.raises(RuntimeError, match="shutting down"):
            pool.submit(lambda: 2)
        pool.shutdown(wait=True)
        assert pool.submit(lambda: 3).result(timeout=3) == 3

    def test_exit_cleanup_needs_no_new_thread(self, pool: WorkPool) -> None:
        assert pool.submit(lambda: 1).result(timeout=3) == 1
        with patch.object(threading.Thread, "start", side_effect=AssertionError("late thread")):
            _shutdown_workpool()
        assert WorkPool._instance is None
