"""
Tests for Perl Worker Pool.

Tests connection pooling, error handling, worker recovery, and health monitoring.
"""

import logging
import tempfile
import time
from pathlib import Path

import pytest

from src.parsers.workers.perl_worker_pool import (
    PerlWorker,
    PerlWorkerPool,
    get_worker_pool,
    shutdown_worker_pool,
)

# Enable debug logging for tests
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def test_stats_file():
    """Create a temporary stats file for testing."""
    content = """
---------- Begin Simulation Statistics ----------
system.cpu.numCycles                          1000                       # Number of cycles
system.cpu.ipc                                   1.5                       # Instructions per cycle
system.mem.readReqs                            500                       # Total read requests
---------- End Simulation Statistics   ----------
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def worker_pool():
    """Create a worker pool for testing."""
    # Small pool for testing
    pool = PerlWorkerPool(pool_size=2)
    yield pool
    pool.shutdown()


class TestPerlWorker:
    """Test individual Perl worker functionality."""

    def test_worker_startup(self):
        """Worker should start successfully and be healthy."""
        script_path = str(
            Path(__file__).parent.parent.parent / "src" / "parsers" / "perl" / "fileParserServer.pl"
        )

        worker = PerlWorker(worker_id=0, script_path=script_path)

        try:
            assert worker.is_healthy
            assert worker.process is not None
            assert worker.process.poll() is None  # Still running
            assert worker.requests_served == 0
        finally:
            worker.shutdown()

    def test_worker_health_check(self):
        """Health check should work correctly."""
        script_path = str(
            Path(__file__).parent.parent.parent / "src" / "parsers" / "perl" / "fileParserServer.pl"
        )

        worker = PerlWorker(worker_id=0, script_path=script_path)

        try:
            # Should be healthy
            assert worker.health_check()

            # Kill the process
            worker.process.kill()
            time.sleep(0.1)

            # Should detect unhealthy
            assert not worker.health_check()
        finally:
            worker.shutdown()

    def test_worker_parse_file(self, test_stats_file):
        """Worker should parse files correctly."""
        script_path = str(
            Path(__file__).parent.parent.parent / "src" / "parsers" / "perl" / "fileParserServer.pl"
        )

        worker = PerlWorker(worker_id=0, script_path=script_path)

        try:
            output, success = worker.parse_file(
                test_stats_file, ["system.cpu.numCycles", "system.cpu.ipc"], timeout=10.0
            )

            assert success
            assert len(output) > 0
            assert worker.requests_served == 1

            # Parse again to test reuse
            output2, success2 = worker.parse_file(
                test_stats_file, ["system.mem.readReqs"], timeout=10.0
            )

            assert success2
            assert worker.requests_served == 2
        finally:
            worker.shutdown()

    def test_worker_restart(self):
        """Worker should restart successfully."""
        script_path = str(
            Path(__file__).parent.parent.parent / "src" / "parsers" / "perl" / "fileParserServer.pl"
        )

        worker = PerlWorker(worker_id=0, script_path=script_path)

        try:
            original_pid = worker.process.pid

            # Restart
            assert worker.restart()

            # Should have new PID and be healthy
            assert worker.process.pid != original_pid
            assert worker.is_healthy
            assert worker.restarts == 1
        finally:
            worker.shutdown()


class TestPerlWorkerPool:
    """Test worker pool functionality."""

    def test_pool_initialization(self, worker_pool):
        """Pool should initialize with correct number of workers."""
        stats = worker_pool.get_stats()

        assert stats["pool_size"] == 2
        assert stats["healthy_workers"] == 2
        assert stats["total_requests"] == 0

    def test_pool_parse_file(self, worker_pool, test_stats_file):
        """Pool should parse files using workers."""
        output = worker_pool.parse_file(test_stats_file, ["system.cpu.numCycles", "system.cpu.ipc"])

        assert len(output) > 0

        # Check stats
        stats = worker_pool.get_stats()
        assert stats["total_requests"] >= 1

    def test_pool_multiple_files(self, worker_pool, test_stats_file):
        """Pool should handle multiple files efficiently."""
        results = []

        # Parse same file multiple times
        for _i in range(5):
            output = worker_pool.parse_file(test_stats_file, ["system.cpu.numCycles"])
            results.append(output)

        # All should succeed
        assert all(len(r) > 0 for r in results)

        # Check that requests were distributed
        stats = worker_pool.get_stats()
        assert stats["total_requests"] == 5

    def test_pool_worker_failure_recovery(self, worker_pool, test_stats_file):
        """Pool should recover from worker failures."""
        # Kill one worker
        worker_pool.workers[0].process.kill()
        worker_pool.workers[0].is_healthy = False

        # Give time for health monitor to detect
        time.sleep(0.5)

        # Should still be able to parse (using other worker)
        output = worker_pool.parse_file(test_stats_file, ["system.cpu.ipc"])

        assert len(output) > 0

    def test_pool_statistics(self, worker_pool, test_stats_file):
        """Pool should track statistics correctly."""
        # Parse multiple files
        for _i in range(3):
            worker_pool.parse_file(test_stats_file, ["system.cpu.numCycles"])

        stats = worker_pool.get_stats()

        assert stats["pool_size"] == 2
        assert stats["total_requests"] == 3
        assert len(stats["workers"]) == 2

        # Check worker stats - workers is a list of WorkerStats dataclass objects
        for worker_stats in stats["workers"]:
            assert hasattr(worker_stats, "pid")
            assert hasattr(worker_stats, "requests_served")
            assert hasattr(worker_stats, "is_healthy")
            assert worker_stats.requests_served > 0  # Verify it served requests

    def test_pool_graceful_shutdown(self, worker_pool):
        """Pool should shut down gracefully."""
        # Get PIDs before shutdown
        [w.process.pid for w in worker_pool.workers if w.process]

        # Shutdown
        worker_pool.shutdown()

        # Give time for processes to exit
        time.sleep(0.5)

        # All workers should be stopped
        for worker in worker_pool.workers:
            assert worker.process is None or worker.process.poll() is not None


class TestWorkerPoolIntegration:
    """Integration tests for worker pool."""

    def test_worker_pool_vs_subprocess_mode(self, test_stats_file: Path):
        """Test worker pool performance."""
        # Test with worker pool (the ONLY mechanism now!)
        pool = get_worker_pool(pool_size=2)

        import time

        start = time.time()
        result = pool.parse_file(str(test_stats_file), ["system.cpu.numCycles"])
        pool_time = time.time() - start

        assert len(result) > 0
        print(f"Pool time: {pool_time:.3f}s")

        shutdown_worker_pool()

    def test_singleton_pool(self):
        """Test singleton pattern for worker pool."""
        # Get pool instance
        pool1 = get_worker_pool(pool_size=2)
        pool2 = get_worker_pool(pool_size=4)  # Should return same instance

        assert pool1 is pool2
        assert pool1.pool_size == 2  # Should use first call's config

        # Cleanup
        shutdown_worker_pool()

        # After shutdown, should be able to create new instance
        pool3 = get_worker_pool(pool_size=3)
        assert pool3 is not pool1
        assert pool3.pool_size == 3

        shutdown_worker_pool()


class TestErrorHandling:
    """Test error handling and robustness."""

    def test_worker_invalid_file(self, worker_pool):
        """Worker should handle invalid file gracefully."""
        # Worker logs error but returns empty result (doesn't raise)
        result = worker_pool.parse_file("/nonexistent/file.txt", ["system.cpu.ipc"])
        assert result == []  # Empty result on error

    def test_worker_timeout(self, worker_pool):
        """Worker should timeout on hung operations."""
        # This would require a file that causes hang - skip for now
        pass

    def test_pool_no_available_workers(self):
        """Pool should handle no available workers."""
        # Create pool with 1 worker
        pool = PerlWorkerPool(pool_size=1)

        try:
            # Kill the worker
            pool.workers[0].process.kill()
            pool.workers[0].is_healthy = False

            # Should raise error when trying to parse
            with pytest.raises((RuntimeError, TimeoutError)):
                pool.parse_file("/tmp/test.txt", ["var"], timeout=2.0)
        finally:
            pool.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
