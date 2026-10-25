"""Caller-owned futures remain independent and collectible after settlement."""

from __future__ import annotations

import gc
import threading
import weakref
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from src.core.application_api import ApplicationAPI
from src.core.models import ScanFileResult
from src.parsing.framework.work_pool import WorkPool, _shutdown_workpool


@pytest.fixture
def pool(monkeypatch: pytest.MonkeyPatch) -> Generator[WorkPool, None, None]:
    _shutdown_workpool()
    monkeypatch.setenv("RING5_WORK_POOL_SIZE", "1")
    instance = WorkPool.get_instance()
    yield instance
    _shutdown_workpool()


class TestWorkPoolOwnership:
    # [test->req~ring5.quality.async-ownership~1]

    def test_returns_one_future_per_callable_in_submission_order(self, pool: WorkPool) -> None:
        futures = pool.submit_many([lambda value=value: value for value in range(5)])
        assert [future.result(timeout=3) for future in futures] == list(range(5))

    def test_settled_futures_and_their_results_are_collectible(self, pool: WorkPool) -> None:
        class Payload:
            pass

        future = pool.submit(Payload)
        result = future.result(timeout=3)
        pool.submit(lambda: None).result(timeout=3)
        future_ref = weakref.ref(future)
        result_ref = weakref.ref(result)
        del future, result
        gc.collect()
        assert future_ref() is None
        assert result_ref() is None


class TestSessionScopedCancellation:
    # [test->req~ring5.quality.async-ownership~1]

    def test_close_cancels_only_queued_work_owned_by_its_session(self, pool: WorkPool) -> None:
        started = threading.Event()
        release = threading.Event()

        def blocking_work() -> None:
            started.set()
            assert release.wait(5)

        blocker = pool.submit(blocking_work)
        parser = MagicMock()
        parser.submit_scan_async.side_effect = lambda path, *_: pool.submit_many(
            [lambda: ScanFileResult(file_path=path)]
        )
        first = ApplicationAPI(parser=parser)
        second = ApplicationAPI(parser=parser)
        try:
            assert started.wait(3)
            first_futures = first.submit_scan_async("first", "stats.txt")
            second_futures = second.submit_scan_async("second", "stats.txt")
            first.close()
            assert first_futures[0].cancelled()
            assert not second_futures[0].cancelled()
            release.set()
            blocker.result(timeout=3)
            assert second_futures[0].result(timeout=3).file_path == "second"
            assert pool.submit(lambda: "still available").result(timeout=3) == "still available"
        finally:
            release.set()
            first.close()
            second.close()
