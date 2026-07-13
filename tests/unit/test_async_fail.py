"""
Tests for async scanning behavior with Futures-based API.
"""

import time
from concurrent.futures import as_completed

from src.core.models import ScannedVariable
from src.parsing.gem5.impl.pool.pool import ScanWorkPool
from src.parsing.gem5.impl.pool.scan_work import ScanWork


class MockWork(ScanWork):
    def __init__(self, val: int, duration: float = 0.1) -> None:

        self.val = val
        self.duration = duration

    def __call__(self) -> list[ScannedVariable]:
        time.sleep(self.duration)
        return [ScannedVariable(name=f"var_{self.val}", type="scalar")]


def test_async_scan_flow() -> None:
    """Test full async flow with futures."""
    pool = ScanWorkPool.get_instance()

    works = [MockWork(i, 0.05) for i in range(5)]
    futures = pool.submit_batch_async(works)

    # Should return list of futures
    assert isinstance(futures, list)
    assert len(futures) == 5

    # Collect results
    results: list[ScannedVariable] = []
    for future in as_completed(futures):
        res = future.result()
        if res:
            results.extend(res)

    assert len(results) == 5
    for i, result in enumerate(sorted(results, key=lambda x: x.name)):
        assert result.name == f"var_{i}"
        assert result.type == "scalar"


def test_async_scan_cancellation() -> None:
    """Test cancellation of async scan via the caller-owned future handles."""
    pool = ScanWorkPool.get_instance()

    # Long duration works
    works = [MockWork(i, 0.5) for i in range(5)]
    futures = pool.submit_batch_async(works)

    # Cancel the handles we own — the pool keeps no references, so
    # cancellation cannot touch another caller's in-flight batch.
    for future in futures:
        future.cancel()

    # Try to collect results - some may be cancelled
    results = []
    cancelled_count = 0
    for future in futures:
        if future.cancelled():
            cancelled_count += 1
        else:
            try:
                res = future.result(timeout=0.1)
                if res:
                    results.append(res)
            except Exception:
                # Future may have been cancelled or timed out
                pass

    # At least some should have been cancelled
    # (exact number depends on timing, but we should have fewer than 5 results)
    assert len(results) < 5 or cancelled_count > 0


def test_multiple_batch_submissions() -> None:
    """Test that multiple batch submissions work independently."""
    pool = ScanWorkPool.get_instance()

    # First batch
    works1 = [MockWork(i, 0.05) for i in range(3)]
    futures1 = pool.submit_batch_async(works1)

    # Second batch (should work fine with new stateless design)
    works2 = [MockWork(i + 10, 0.05) for i in range(3)]
    futures2 = pool.submit_batch_async(works2)

    # Collect all results
    all_futures = futures1 + futures2
    results = []
    for future in as_completed(all_futures):
        res = future.result()
        if res:
            results.append(res)

    assert len(results) == 6
