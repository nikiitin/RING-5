"""
Test: Pool Future Leak Prevention.

Validates that ScanWorkPool and ParseWorkPool do not accumulate
futures across successive batch submissions. The pools are singletons;
without cleanup, repeated submissions would leak future references,
causing unbounded memory growth and performance degradation.
"""

from __future__ import annotations

from collections.abc import Iterator
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


class TestScanWorkPoolFutureCleanup:
    """Verify ScanWorkPool clears stale futures on new batch submission."""

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_futures_cleared_between_batches(self, mock_pool_cls: MagicMock) -> None:
        """Submitting a new batch must not retain futures from a prior batch."""
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance
        mock_pool_instance.submit.return_value = MagicMock()

        pool = ScanWorkPool.get_instance()

        # First batch — 5 work items
        works_a = [MagicMock() for _ in range(5)]
        futures_a = pool.submit_batch_async(works_a)
        assert len(futures_a) == 5
        assert len(pool._futures) == 5

        # Second batch — 3 work items
        works_b = [MagicMock() for _ in range(3)]
        futures_b = pool.submit_batch_async(works_b)
        assert len(futures_b) == 3
        # The internal list should only contain the NEW batch's futures.
        assert len(pool._futures) == 3, (
            f"Expected 3 futures after second batch, got {len(pool._futures)}. "
            "Stale futures from the first batch are leaking."
        )

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_cancel_all_clears_list(self, mock_pool_cls: MagicMock) -> None:
        """cancel_all() must clear the internal list after cancelling."""
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance
        mock_future = MagicMock()
        mock_pool_instance.submit.return_value = mock_future

        pool = ScanWorkPool.get_instance()
        works = [MagicMock() for _ in range(4)]
        pool.submit_batch_async(works)
        assert len(pool._futures) == 4

        pool.cancel_all()
        assert len(pool._futures) == 0, "cancel_all() did not clear futures list"

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_empty_batch_returns_empty(self, mock_pool_cls: MagicMock) -> None:
        """Submitting an empty batch should return empty list without side effects."""
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance

        pool = ScanWorkPool.get_instance()
        result = pool.submit_batch_async([])
        assert result == []
        assert len(pool._futures) == 0


class TestParseWorkPoolFutureCleanup:
    """Verify ParseWorkPool clears stale futures on new batch submission."""

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_futures_cleared_between_batches(self, mock_pool_cls: MagicMock) -> None:
        """Submitting a new batch must not retain futures from a prior batch."""
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance
        mock_pool_instance.submit.return_value = MagicMock()

        pool = ParseWorkPool.get_instance()

        # First batch
        works_a = [MagicMock() for _ in range(8)]
        futures_a = pool.submit_batch_async(works_a)
        assert len(futures_a) == 8
        assert len(pool._futures) == 8

        # Second batch
        works_b = [MagicMock() for _ in range(2)]
        futures_b = pool.submit_batch_async(works_b)
        assert len(futures_b) == 2
        assert len(pool._futures) == 2, (
            f"Expected 2 futures after second batch, got {len(pool._futures)}. "
            "Stale futures from the first batch are leaking."
        )

    @patch("src.parsing.gem5.impl.pool.pool.WorkPool")
    def test_cancel_all_clears_list(self, mock_pool_cls: MagicMock) -> None:
        """cancel_all() must clear the internal list after cancelling."""
        mock_pool_instance = MagicMock()
        mock_pool_cls.get_instance.return_value = mock_pool_instance
        mock_future = MagicMock()
        mock_pool_instance.submit.return_value = mock_future

        pool = ParseWorkPool.get_instance()
        works = [MagicMock() for _ in range(6)]
        pool.submit_batch_async(works)
        assert len(pool._futures) == 6

        pool.cancel_all()
        assert len(pool._futures) == 0, "cancel_all() did not clear futures list"
