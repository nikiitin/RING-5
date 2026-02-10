"""
Performance regression tests for RING-5.

These tests ensure critical operations maintain acceptable performance.
Run with: pytest tests/performance/ -v
"""

import time

import pandas as pd
import pytest

from src.core.benchmark import BenchmarkSuite
from src.plotting import PlotFactory
from src.web.services.shapers.impl.normalize import Normalize


class TestPlotPerformance:
    """Test plot generation performance."""

    @pytest.fixture
    def sample_data(self):
        """Create sample dataset for plotting."""
        return pd.DataFrame(
            {
                "benchmark": ["bzip2", "gcc", "mcf"] * 100,
                "config": ["baseline", "optimized"] * 150,
                "ipc": [1.2, 1.5, 0.8] * 100 + [0.1] * 0,  # 300 rows
                "cycles": [1000, 900, 1100] * 100,
            }
        )

    def test_bar_plot_generation_speed(self, sample_data):
        """Bar plot generation should complete in < 500ms."""
        suite = BenchmarkSuite("Bar Plot Generation")

        plot = PlotFactory.create_plot("bar", plot_id=1, name="Test Plot")
        plot.processed_data = sample_data
        plot.config = {
            "x": "benchmark",
            "y": "ipc",
            "color": "config",
            "title": "Performance Test",  # Required field
            "xlabel": "Benchmark",
            "ylabel": "IPC",
        }

        # Warm up (first call may be slower)
        _ = plot.create_figure(sample_data, plot.config)

        # Actual benchmark
        result = suite.benchmark(
            plot.create_figure, sample_data, plot.config, iterations=5, name="Create bar figure"
        )

        avg_time = suite.results[0].avg_ms
        assert result is not None, "Plot generation failed"
        assert avg_time < 500, f"Bar plot too slow: {avg_time:.2f}ms (threshold: 500ms)"

    def test_grouped_bar_plot_speed(self, sample_data):
        """Grouped bar plot should complete in < 800ms."""
        suite = BenchmarkSuite("Grouped Bar Plot")

        plot = PlotFactory.create_plot("grouped_bar", plot_id=2, name="Grouped Test")
        plot.processed_data = sample_data
        plot.config = {
            "x": "benchmark",  # Correct key name
            "y": "ipc",
            "color": "config",
            "group": "benchmark",
        }

        _ = plot.create_figure(sample_data, plot.config)

        result = suite.benchmark(
            plot.create_figure,
            sample_data,
            plot.config,
            iterations=3,
            name="Create grouped bar figure",
        )

        avg_time = suite.results[0].avg_ms
        assert result is not None
        assert avg_time < 800, f"Grouped bar too slow: {avg_time:.2f}ms (threshold: 800ms)"


class TestShaperPerformance:
    """Test shaper performance."""

    @pytest.fixture
    def large_dataset(self):
        """Create large dataset for shaper testing."""
        # Create non-baseline data
        benchmarks = ["bzip2", "gcc", "mcf", "perlbench"]
        data_rows = []

        for bench in benchmarks:
            for i in range(500):  # 500 rows per benchmark
                data_rows.append(
                    {
                        "benchmark": bench,
                        "config": f"config_{i % 10}",  # Various configs, not baseline
                        "cycles": 1000 + i,
                        "energy": 50.0 + i * 0.1,
                    }
                )

        return pd.DataFrame(data_rows)

    def test_normalize_shaper_speed(self, large_dataset):
        """Normalize shaper should handle 2000 rows in < 200ms."""
        # Add exactly ONE baseline row per benchmark
        baseline_rows = []
        for bench in ["bzip2", "gcc", "mcf", "perlbench"]:
            baseline_rows.append(
                {
                    "benchmark": bench,
                    "config": "baseline",
                    "cycles": 1000,
                    "energy": 50.0,
                }
            )
        baseline = pd.DataFrame(baseline_rows)

        data = pd.concat([baseline, large_dataset], ignore_index=True)

        normalizer = Normalize(
            {
                "normalizeVars": ["cycles", "energy"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark"],
            }
        )

        suite = BenchmarkSuite("Normalize Shaper")

        # Warm up
        _ = normalizer(data)

        # Benchmark
        result = suite.benchmark(normalizer, data, iterations=5, name="Normalize 2000 rows")

        avg_time = suite.results[0].avg_ms
        assert result is not None
        assert len(result) == len(data)
        assert avg_time < 200, f"Normalize too slow: {avg_time:.2f}ms (threshold: 200ms)"

    def test_normalize_caching_effectiveness(self, large_dataset):
        """Second normalize call should be significantly faster (cached)."""
        # Add exactly ONE baseline row per benchmark
        baseline_rows = []
        for bench in ["bzip2", "gcc", "mcf", "perlbench"]:
            baseline_rows.append(
                {
                    "benchmark": bench,
                    "config": "baseline",
                    "cycles": 1000,
                    "energy": 50.0,
                }
            )
        baseline = pd.DataFrame(baseline_rows)

        # Make dataset much larger to increase computation cost
        large_data = pd.concat([large_dataset] * 20, ignore_index=True)
        data = pd.concat([baseline, large_data], ignore_index=True)

        normalizer = Normalize(
            {
                "normalizeVars": ["cycles", "energy"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark"],
            }
        )

        # Clear cache before first run
        from src.core.performance import clear_all_caches

        clear_all_caches()

        # First call (uncached)
        suite1 = BenchmarkSuite("First Call")
        _ = suite1.benchmark(normalizer, data, name="First normalize")
        first_time = suite1.results[0].duration_ms

        # Second call (should hit cache)
        suite2 = BenchmarkSuite("Second Call")
        _ = suite2.benchmark(normalizer, data, name="Second normalize")
        second_time = suite2.results[0].duration_ms

        # Cache should make second call at least 1.5x faster
        speedup = first_time / second_time if second_time > 0 else 1.0
        assert speedup >= 1.5, (
            f"Caching not effective enough: {speedup:.2f}x speedup " f"(expected >= 1.5x)"
        )


class TestCsvPoolPerformance:
    """Test CSV pool operations performance."""

    def test_csv_metadata_caching(self, tmp_path):
        """CSV metadata should be cached for fast repeated access."""

        from src.web.services.csv_pool_service import CsvPoolService

        # Create a test CSV
        csv_path = tmp_path / "test.csv"
        large_df = pd.DataFrame(
            {"col1": range(1000), "col2": range(1000, 2000), "col3": ["value"] * 1000}
        )
        large_df.to_csv(csv_path, index=False)

        # Clear caches
        CsvPoolService.clear_caches()

        # First call - should compute metadata
        start1 = time.perf_counter()
        metadata1 = CsvPoolService._get_csv_metadata(str(csv_path))
        duration1 = (time.perf_counter() - start1) * 1000

        # Second call - should use cache
        start2 = time.perf_counter()
        metadata2 = CsvPoolService._get_csv_metadata(str(csv_path))
        duration2 = (time.perf_counter() - start2) * 1000

        # Verify metadata is correct
        assert metadata1 is not None
        assert metadata2 is not None
        assert metadata1["rows"] == 1000
        assert len(metadata1["columns"]) == 3

        # Second call should be much faster (at least 5x)
        speedup = duration1 / duration2 if duration2 > 0 else 1.0
        assert speedup >= 5.0, (
            f"Metadata caching not effective: {speedup:.2f}x speedup "
            f"(expected >= 5.0x). First: {duration1:.2f}ms, Second: {duration2:.2f}ms"
        )

    def test_csv_loading_with_cache(self, tmp_path):
        """CSV DataFrame loading should be cached."""
        from src.web.services.csv_pool_service import CsvPoolService

        # Create test CSV
        csv_path = tmp_path / "cached.csv"
        df = pd.DataFrame({"x": range(500), "y": range(500, 1000)})
        df.to_csv(csv_path, index=False)

        # Clear caches
        CsvPoolService.clear_caches()

        # First load
        start1 = time.perf_counter()
        df1 = CsvPoolService.load_csv_file(str(csv_path))
        duration1 = (time.perf_counter() - start1) * 1000

        # Second load (cached)
        start2 = time.perf_counter()
        df2 = CsvPoolService.load_csv_file(str(csv_path))
        duration2 = (time.perf_counter() - start2) * 1000

        # Verify data is same
        pd.testing.assert_frame_equal(df1, df2)

        # Cache should provide speedup
        speedup = duration1 / duration2 if duration2 > 0 else 1.0
        assert speedup >= 2.0, (
            f"CSV caching not effective: {speedup:.2f}x speedup " f"(expected >= 2.0x)"
        )


class TestDataLoadingPerformance:
    """Test data loading and processing performance."""

    def test_dataframe_creation_speed(self):
        """Creating large DataFrame should be fast."""
        suite = BenchmarkSuite("DataFrame Creation")

        def create_large_df():
            return pd.DataFrame(
                {
                    "col1": range(10000),
                    "col2": [f"value_{i}" for i in range(10000)],
                    "col3": [float(i) * 1.5 for i in range(10000)],
                }
            )

        result = suite.benchmark(create_large_df, iterations=3, name="Create 10k row DataFrame")

        avg_time = suite.results[0].avg_ms
        assert result is not None
        assert len(result) == 10000
        assert avg_time < 100, f"DataFrame creation too slow: {avg_time:.2f}ms"

    def test_dataframe_groupby_speed(self):
        """GroupBy operations should be efficient."""
        df = pd.DataFrame(
            {
                "category": ["A", "B", "C"] * 1000,  # 3000 rows
                "value": range(3000),
            }
        )

        suite = BenchmarkSuite("GroupBy Operations")

        def do_groupby():
            return df.groupby("category")["value"].mean()

        result = suite.benchmark(do_groupby, iterations=5, name="GroupBy with 3000 rows")

        avg_time = suite.results[0].avg_ms
        assert result is not None
        assert len(result) == 3
        assert avg_time < 50, f"GroupBy too slow: {avg_time:.2f}ms"


@pytest.mark.benchmark
class TestEndToEndPerformance:
    """End-to-end performance tests."""

    def test_full_pipeline_speed(self):
        """Complete analysis pipeline should complete reasonably fast."""
        # Create data with ONE baseline per benchmark, plus other configs
        benchmarks = ["bzip2", "gcc"]

        data_rows = []
        # Add baseline rows (one per benchmark)
        for bench in benchmarks:
            data_rows.append(
                {
                    "benchmark": bench,
                    "config": "baseline",
                    "ipc": 1.2,
                    "cycles": 1000,
                }
            )

        # Add other config rows
        for bench in benchmarks:
            for config in ["opt1", "opt2", "opt3"]:
                for i in range(50):  # 50 rows per config per benchmark
                    data_rows.append(
                        {
                            "benchmark": bench,
                            "config": config,
                            "ipc": 1.2 + (i % 10) * 0.1,
                            "cycles": 900 - i,
                        }
                    )

        data = pd.DataFrame(data_rows)

        suite = BenchmarkSuite("Full Pipeline")

        with suite.measure("1. Normalize data"):
            normalizer = Normalize(
                {
                    "normalizeVars": ["cycles"],
                    "normalizerColumn": "config",
                    "normalizerValue": "baseline",
                    "groupBy": ["benchmark"],
                }
            )
            normalized = normalizer(data)

        with suite.measure("2. Create plot"):
            plot = PlotFactory.create_plot("bar", plot_id=1, name="Pipeline Test")
            plot.processed_data = normalized
            plot.config = {
                "x": "benchmark",
                "y": "cycles",
                "color": "config",
                "title": "Performance Pipeline Test",
                "xlabel": "Benchmark",
                "ylabel": "Cycles",
            }

        with suite.measure("3. Generate figure"):
            fig = plot.create_figure(normalized, plot.config)

        assert fig is not None

        total_time = sum(r.duration_ms for r in suite.results)
        assert total_time < 1000, f"Full pipeline too slow: {total_time:.2f}ms (threshold: 1000ms)"

        suite.print_summary()
