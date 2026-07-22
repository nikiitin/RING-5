"""
Test: Pool facades hold no future references (statelessness).

The pools are process-wide singletons shared by every session. Retaining the
last-submitted batch in the singleton (the old design) had two consequences:
``cancel_all()`` cancelled whichever caller submitted last — demonstrated
cross-caller cancellation — and the retained futures pinned a full batch of
parsed results in memory. The facades are now stateless: the returned futures
are the caller's only handles, and cancellation is per-handle, session-scoped
(``ApplicationAPI.cancel_pending_scans`` cancels only its own futures).
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import Future
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.parsing.gem5.impl.pool.pool import ParseWorkPool, ScanWorkPool


@pytest.fixture(autouse=True)
def _reset_singletons() -> Iterator[None]:
    """Ensure pool singletons are fresh for each test."""
    ScanWorkPool.reset()
    ParseWorkPool.reset()
    yield  # type: ignore[misc]
    ScanWorkPool.reset()
    ParseWorkPool.reset()


def _new_future() -> Future[Any]:
    return Future()


class TestScanWorkPoolStateless:
    # [test->req~ring5.quality.async-ownership~1]

    """ScanWorkPool must keep no reference to submitted futures."""

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_returns_one_future_per_work(self, mock_pool_cls: MagicMock) -> None:
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance
        mock_pool_instance.submit.side_effect = lambda w: _new_future()

        pool = ScanWorkPool.get_instance()
        futures = pool.submit_batch_async([MagicMock() for _ in range(5)])
        assert len(futures) == 5

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_facade_retains_no_futures(self, mock_pool_cls: MagicMock) -> None:
        """No instance attribute may hold the batch — retained futures pin
        results in memory and enable cross-caller cancellation."""
        mock_pool_cls.get_instance.return_value = MagicMock()
        pool = ScanWorkPool.get_instance()
        pool.submit_batch_async([MagicMock() for _ in range(4)])

        retained = [
            (name, value) for name, value in vars(pool).items() if isinstance(value, list) and value
        ]
        assert retained == [], f"facade retains future lists: {retained}"

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_callers_own_independent_batches(self, mock_pool_cls: MagicMock) -> None:
        """Caller A cancelling its handles must not touch caller B's batch."""
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance
        mock_pool_instance.submit.side_effect = lambda w: _new_future()

        pool = ScanWorkPool.get_instance()
        futures_a = pool.submit_batch_async([MagicMock() for _ in range(3)])
        futures_b = pool.submit_batch_async([MagicMock() for _ in range(3)])

        for f in futures_a:
            f.cancel()

        assert all(f.cancelled() for f in futures_a)
        assert not any(f.cancelled() for f in futures_b)


class TestParseWorkPoolStateless:
    # [test->req~ring5.quality.async-ownership~1]

    """ParseWorkPool must keep no reference to submitted futures."""

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_returns_one_future_per_work(self, mock_pool_cls: MagicMock) -> None:
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance
        mock_pool_instance.submit.side_effect = lambda w: _new_future()

        pool = ParseWorkPool.get_instance()
        futures = pool.submit_batch_async([MagicMock() for _ in range(8)])
        assert len(futures) == 8

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_facade_retains_no_futures(self, mock_pool_cls: MagicMock) -> None:
        mock_pool_cls.get_instance.return_value = MagicMock()
        pool = ParseWorkPool.get_instance()
        pool.submit_batch_async([MagicMock() for _ in range(4)])

        retained = [
            (name, value) for name, value in vars(pool).items() if isinstance(value, list) and value
        ]
        assert retained == [], f"facade retains future lists: {retained}"

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_none_works_are_skipped(self, mock_pool_cls: MagicMock) -> None:
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance
        mock_pool_instance.submit.side_effect = lambda w: _new_future()

        pool = ParseWorkPool.get_instance()
        works = [MagicMock(), None, MagicMock()]
        futures = pool.submit_batch_async(works)  # type: ignore[arg-type]
        assert len(futures) == 2


class TestSessionScopedCancellation:
    # [test->req~ring5.quality.async-ownership~1]

    """ApplicationAPI.cancel_pending_scans cancels only its own futures."""

    def test_cancel_only_own_session_futures(self) -> None:
        from src.core.application_api import ApplicationAPI

        api_a = ApplicationAPI()
        api_b = ApplicationAPI()

        futures_a = [_new_future() for _ in range(3)]
        futures_b = [_new_future() for _ in range(3)]
        api_a._pending_scan_futures = list(futures_a)
        api_b._pending_scan_futures = list(futures_b)

        api_b.cancel_pending_scans()

        assert all(f.cancelled() for f in futures_b)
        assert not any(f.cancelled() for f in futures_a), (
            "cancel_pending_scans cancelled ANOTHER session's futures — "
            "the cross-caller cancellation bug is back"
        )
        assert api_b._pending_scan_futures == []
