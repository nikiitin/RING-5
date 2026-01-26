import pytest
import time
from src.parsers.workers.pool import ScanWorkPool
from src.parsers.workers.scan_work import ScanWork

@pytest.fixture
def clean_pool_singleton():
    """Reset the singleton instance of ScanWorkPool."""
    instance = ScanWorkPool.get_instance()
    # Reset internal state
    instance._cancel_event.clear()
    instance._progress = {"total": 0, "current": 0, "status": "idle", "errors": []}
    instance._results = []
    instance._futures = []
    return instance

class MockWork(ScanWork):
    def __init__(self, val, duration=0.1):
        self.val = val
        self.duration = duration
    
    def __call__(self):
        time.sleep(self.duration)
        return {"name": f"var_{self.val}", "type": "scalar"}

def test_async_scan_flow(clean_pool_singleton):
    """Test full async flow with progress tracking."""
    pool = ScanWorkPool.get_instance()
    
    works = [MockWork(i, 0.05) for i in range(5)]
    pool.submit_batch_async(works)
    
    # Check running status
    status = pool.get_status()
    assert status["total"] == 5
    # Might be running or done depending on speed, but status dict structure should be valid
    assert status["status"] in ("running", "done")
    
    # Wait for completion
    timeout = 2.0
    start = time.time()
    while pool.get_status()["status"] == "running":
        if time.time() - start > timeout:
            pytest.fail("Async scan timed out")
        time.sleep(0.05)
    final_status = pool.get_status()
    assert final_status["status"] == "done"
    assert final_status["current"] == 5
    assert not final_status["errors"]
    
    results = pool.get_results_async_snapshot()
    assert len(results) == 5

def test_async_scan_cancellation(clean_pool_singleton):
    """Test cancellation of async scan."""
    pool = ScanWorkPool.get_instance()
    
    # Long duration works
    works = [MockWork(i, 0.5) for i in range(5)]
    pool.submit_batch_async(works)
    
    # Let it start
    time.sleep(0.1)
    status = pool.get_status()
    assert status["status"] == "running"
    
    # Cancel
    pool.cancel_current_job()
    
    # Wait for status update
    time.time()
    while pool.get_status()["status"] == "running":
        time.sleep(0.05)
    final_status = pool.get_status()
    assert final_status["status"] == "cancelled"
    # Should not have completed all
    assert final_status["current"] < 5

def test_async_scan_busy_lock(clean_pool_singleton):
    """Test that submitting while busy raises RuntimeError."""
    pool = ScanWorkPool.get_instance()
    works = [MockWork(i, 0.5) for i in range(2)]
    pool.submit_batch_async(works)
    
    # Immediate second submit should fail
    with pytest.raises(RuntimeError) as excinfo:
        pool.submit_batch_async(works)
    
    # Error message comes from ScanWorkPool.submit_batch_async logic
    # "Scanner is currently busy..." or "Scanner thread is still running"
    assert "busy" in str(excinfo.value) or "running" in str(excinfo.value)
    
    # Clean up (cancel running job)
    pool.cancel_current_job()
