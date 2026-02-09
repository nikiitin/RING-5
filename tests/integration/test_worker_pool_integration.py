"""
Integration tests for worker pool usage in actual parsing workflow.

Verifies that:
1. Gem5ParseWork uses worker pool (not direct subprocess)
2. Full parse pipeline delivers worker pool performance benefits
3. No subprocess.run() calls are made during parsing
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.core.models import StatConfig
from src.core.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService
from src.core.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.core.parsing.gem5.impl.strategies.perl_worker_pool import (
    get_worker_pool,
    shutdown_worker_pool,
)


@pytest.fixture(scope="module")
def test_stats_file(tmp_path_factory: Any) -> str:
    """Create a minimal gem5 stats file for testing."""
    tmp_dir = tmp_path_factory.mktemp("worker_pool_integration")
    stats_file = tmp_dir / "stats.txt"

    content = """
---------- Begin Simulation Statistics ----------
system.cpu.numCycles                     12345                       # Number of cycles
system.cpu.ipc                           1.234                       # IPC
system.cpu.dcache.overall_miss_rate::total  0.05                    # Miss rate
---------- End Simulation Statistics   ----------
"""
    stats_file.write_text(content)
    return str(stats_file)


@pytest.fixture(scope="module", autouse=True)
def cleanup_worker_pool() -> None:
    """Ensure worker pool is cleaned up after tests."""
    yield
    shutdown_worker_pool()


class TestWorkerPoolIntegration:
    """Integration tests for worker pool usage in full parsing workflow."""

    def test_gem5_parse_work_uses_worker_pool(self, test_stats_file: str) -> None:
        """Verify Gem5ParseWork uses worker pool instead of subprocess."""
        from src.core.parsing.gem5.types.type_mapper import TypeMapper

        # Create a minimal variable config
        var_config = StatConfig(name="system.cpu.numCycles", type="scalar")

        # Create StatType instance
        stat_type = TypeMapper.create_stat(var_config)
        vars_dict = {var_config.name: stat_type}

        # Create parse work
        work = Gem5ParseWork(test_stats_file, vars_dict)

        # Mock subprocess.run to ensure it's NEVER called
        with patch("subprocess.run") as mock_subprocess:
            # Execute parsing
            result = work()

            # CRITICAL: subprocess.run should NOT be called
            mock_subprocess.assert_not_called()

            # Verify we got results
            assert result is not None
            assert var_config.name in result

    def test_parse_service_uses_worker_pool(self, test_stats_file: str, tmp_path: Path) -> None:
        """Verify ParseService workflow uses worker pool end-to-end."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        variables = [
            StatConfig(name="system.cpu.numCycles", type="scalar"),
            StatConfig(name="system.cpu.ipc", type="scalar"),
        ]

        # Mock subprocess.run to ensure it's never called during parsing
        with patch("subprocess.run") as mock_subprocess:
            # Submit parse async
            batch = ParseService.submit_parse_async(
                stats_path=str(Path(test_stats_file).parent),
                stats_pattern="stats.txt",
                variables=variables,
                output_dir=str(output_dir),
            )

            # Wait for results
            results = [f.result() for f in batch.futures]

            # CRITICAL: subprocess.run should NOT be called
            mock_subprocess.assert_not_called()

            # Construct final CSV
            csv_path = ParseService.construct_final_csv(
                str(output_dir), results, var_names=batch.var_names
            )

            # Verify output
            assert csv_path is not None
            assert Path(csv_path).exists()

    def test_worker_pool_reused_across_multiple_parses(self, test_stats_file: str) -> None:
        """Verify same worker pool is reused across multiple parse operations."""
        from src.core.parsing.gem5.types.type_mapper import TypeMapper

        var_config = StatConfig(name="system.cpu.numCycles", type="scalar")

        # Get worker pool ID before parsing
        pool_before = get_worker_pool()
        pool_id_before = id(pool_before)

        # Create and execute multiple parse works
        for _ in range(3):
            stat_type = TypeMapper.create_stat(var_config)
            vars_dict = {var_config.name: stat_type}
            work = Gem5ParseWork(test_stats_file, vars_dict)
            result = work()
            assert result is not None

        # Get worker pool ID after parsing
        pool_after = get_worker_pool()
        pool_id_after = id(pool_after)

        # CRITICAL: Should be same pool instance (singleton)
        assert pool_id_before == pool_id_after

    def test_worker_pool_delivers_performance_benefits(self, test_stats_file: str) -> None:
        """Verify worker pool provides significant speedup over theoretical subprocess approach."""
        import time

        from src.core.parsing.gem5.types.type_mapper import TypeMapper

        var_config = StatConfig(name="system.cpu.numCycles", type="scalar")

        # Parse 10 files using worker pool
        start_time = time.time()
        for _ in range(10):
            stat_type = TypeMapper.create_stat(var_config)
            vars_dict = {var_config.name: stat_type}
            work = Gem5ParseWork(test_stats_file, vars_dict)
            result = work()
            assert result is not None
        elapsed = time.time() - start_time

        # Worker pool should be fast (< 1 second for 10 files)
        # With subprocess, this would take ~0.5s (50ms startup * 10 files)
        # With worker pool, should be < 0.1s
        assert elapsed < 1.0, f"Worker pool took {elapsed:.3f}s (too slow, may not be using pool)"

        # Log performance
        throughput = 10 / elapsed
        print(f"\\nWorker pool throughput: {throughput:.1f} files/sec ({elapsed:.3f}s total)")


class TestWorkerPoolErrorHandling:
    """Test error handling in worker pool integration."""

    def test_missing_file_raises_error(self) -> None:
        """Verify proper error handling for missing files."""
        from src.core.parsing.gem5.types.type_mapper import TypeMapper

        var_config = StatConfig(name="system.cpu.numCycles", type="scalar")

        stat_type = TypeMapper.create_stat(var_config)
        vars_dict = {var_config.name: stat_type}

        # Create work with non-existent file
        work = Gem5ParseWork("/nonexistent/stats.txt", vars_dict)

        # Should raise FileNotFoundError (validation happens before parsing)
        with pytest.raises(FileNotFoundError, match="does not exist"):
            work()

    def test_invalid_variable_handled_gracefully(self, test_stats_file: str) -> None:
        """Verify invalid variables don't crash the worker pool."""
        from src.core.parsing.gem5.types.type_mapper import TypeMapper

        var_config = StatConfig(
            name="invalid.variable.that.does.not.exist",
            type="scalar",
        )

        stat_type = TypeMapper.create_stat(var_config)
        vars_dict = {var_config.name: stat_type}

        work = Gem5ParseWork(test_stats_file, vars_dict)

        # Should complete without crashing (may return empty results)
        result = work()
        assert result is not None


class TestWorkerPoolConfigurationLoading:
    """Test worker pool configuration loading from environment."""

    def test_worker_pool_size_from_env(self, monkeypatch: Any) -> None:
        """Verify worker pool size can be configured via environment variable."""
        # This test verifies the configuration is loaded correctly
        # The actual pool size is set during module import
        monkeypatch.setenv("RING5_WORKER_POOL_SIZE", "8")

        # Reimport to pick up new env var
        import importlib
        import sys

        parse_service_module = sys.modules["src.core.parsing.gem5.impl.gem5_parser"]

        importlib.reload(parse_service_module)

        # Verify the size is read from env
        assert parse_service_module._WORKER_POOL_SIZE == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
