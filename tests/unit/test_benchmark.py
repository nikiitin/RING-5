"""
Tests for benchmark utilities.

Following Rule 004 (QA Testing Mastery):
- Fixture-first design for test data
- AAA pattern (Arrange-Act-Assert)
- Parametrization for multiple scenarios
- Testing timing logic with tolerance
- Monkeypatch for capturing print output
"""

import time

import pytest

from src.core.benchmark import (
    BenchmarkResult,
    BenchmarkSuite,
    benchmark_decorator,
    timer,
)


@pytest.fixture
def sample_benchmark_result():
    """Create a sample benchmark result."""
    return BenchmarkResult(name="test_op", duration_ms=150.5, iterations=10)


@pytest.fixture
def sample_suite():
    """Create a benchmark suite with some results."""
    suite = BenchmarkSuite("Test Suite")
    suite.results.append(BenchmarkResult("op1", 100.0, 1))
    suite.results.append(BenchmarkResult("op2", 200.0, 5))
    suite.results.append(BenchmarkResult("op3", 50.0, 1))
    return suite


class TestBenchmarkResult:
    """Test BenchmarkResult container."""

    def test_initialization(self):
        # Arrange & Act
        result = BenchmarkResult("parse_file", 123.45, iterations=5)

        # Assert
        assert result.name == "parse_file"
        assert result.duration_ms == 123.45
        assert result.iterations == 5
        assert result.avg_ms == 123.45 / 5

    def test_single_iteration_avg(self):
        # Arrange & Act
        result = BenchmarkResult("single_op", 100.0, iterations=1)

        # Assert
        assert result.avg_ms == 100.0

    def test_zero_iterations_avg(self):
        # Arrange & Act
        result = BenchmarkResult("zero_op", 0.0, iterations=0)

        # Assert
        assert result.avg_ms == 0.0  # No division by zero

    def test_str_single_iteration(self):
        # Arrange
        result = BenchmarkResult("test_op", 42.5, iterations=1)

        # Act
        output = str(result)

        # Assert
        assert "test_op" in output
        assert "42.5" in output
        assert "avg" not in output.lower()  # Single iteration doesn't show avg

    def test_str_multiple_iterations(self):
        # Arrange
        result = BenchmarkResult("test_op", 200.0, iterations=10)

        # Act
        output = str(result)

        # Assert
        assert "test_op" in output
        assert "200.0" in output
        assert "20.0" in output  # avg
        assert "10 iterations" in output

    def test_to_dict(self, sample_benchmark_result):
        # Arrange
        result = sample_benchmark_result

        # Act
        data = result.to_dict()

        # Assert
        assert data["name"] == "test_op"
        assert data["duration_ms"] == 150.5
        assert data["iterations"] == 10
        assert data["avg_ms"] == 15.05


class TestBenchmarkSuiteInitialization:
    """Test BenchmarkSuite initialization."""

    def test_initialization(self):
        # Arrange & Act
        suite = BenchmarkSuite("My Suite")

        # Assert
        assert suite.name == "My Suite"
        assert suite.results == []


class TestBenchmarkSuiteMeasure:
    """Test BenchmarkSuite.measure context manager."""

    def test_measure_records_duration(self):
        # Arrange
        suite = BenchmarkSuite("Test")

        # Act
        with suite.measure("sleep_test"):
            time.sleep(0.01)  # 10ms

        # Assert
        assert len(suite.results) == 1
        assert suite.results[0].name == "sleep_test"
        assert suite.results[0].duration_ms >= 10.0  # At least 10ms
        assert suite.results[0].iterations == 1

    def test_measure_multiple_operations(self):
        # Arrange
        suite = BenchmarkSuite("Multi")

        # Act
        with suite.measure("op1"):
            time.sleep(0.005)
        with suite.measure("op2"):
            time.sleep(0.005)

        # Assert
        assert len(suite.results) == 2
        assert suite.results[0].name == "op1"
        assert suite.results[1].name == "op2"

    def test_measure_with_exception_still_records(self):
        # Arrange
        suite = BenchmarkSuite("Error Test")

        # Act & Assert
        with pytest.raises(ValueError):
            with suite.measure("failing_op"):
                raise ValueError("Test error")

        # Assert measurement was still recorded
        assert len(suite.results) == 1
        assert suite.results[0].name == "failing_op"


class TestBenchmarkSuiteBenchmark:
    """Test BenchmarkSuite.benchmark method."""

    def test_benchmark_single_iteration(self):
        # Arrange
        suite = BenchmarkSuite("Func Test")

        def add_numbers(a, b):
            return a + b

        # Act
        result = suite.benchmark(add_numbers, 5, 10)

        # Assert
        assert result == 15
        assert len(suite.results) == 1
        assert suite.results[0].name == "add_numbers"
        assert suite.results[0].iterations == 1

    def test_benchmark_multiple_iterations(self):
        # Arrange
        suite = BenchmarkSuite("Multi Iter")
        counter = [0]

        def increment():
            counter[0] += 1
            return counter[0]

        # Act
        result = suite.benchmark(increment, iterations=5)

        # Assert
        assert result == 5  # Last iteration
        assert counter[0] == 5  # Called 5 times
        assert suite.results[0].iterations == 5

    def test_benchmark_with_custom_name(self):
        # Arrange
        suite = BenchmarkSuite("Named")

        # Act
        suite.benchmark(lambda: 42, name="custom_operation")

        # Assert
        assert suite.results[0].name == "custom_operation"

    def test_benchmark_with_kwargs(self):
        # Arrange
        suite = BenchmarkSuite("Kwargs Test")

        def divide(numerator, denominator=1):
            return numerator / denominator

        # Act
        result = suite.benchmark(divide, 10, denominator=2)

        # Assert
        assert result == 5.0


class TestBenchmarkSuiteSummary:
    """Test BenchmarkSuite.summary method."""

    def test_summary_empty_suite(self):
        # Arrange
        suite = BenchmarkSuite("Empty")

        # Act
        df = suite.summary()

        # Assert
        assert df.empty

    def test_summary_with_results(self, sample_suite):
        # Arrange
        suite = sample_suite

        # Act
        df = suite.summary()

        # Assert
        assert len(df) == 3
        assert list(df.columns) == ["name", "duration_ms", "iterations", "avg_ms"]
        assert df["name"].tolist() == ["op1", "op2", "op3"]
        assert df["duration_ms"].tolist() == [100.0, 200.0, 50.0]


class TestBenchmarkSuitePrintSummary:
    """Test BenchmarkSuite.print_summary method."""

    def test_print_summary_empty_suite(self, capsys):
        # Arrange
        suite = BenchmarkSuite("Empty")

        # Act
        suite.print_summary()

        # Assert
        captured = capsys.readouterr()
        assert "Empty" in captured.out
        assert "No benchmarks run yet" in captured.out

    def test_print_summary_with_results(self, sample_suite, capsys):
        # Arrange
        suite = sample_suite

        # Act
        suite.print_summary()

        # Assert
        captured = capsys.readouterr()
        assert "Test Suite" in captured.out
        assert "op1" in captured.out
        assert "op2" in captured.out
        assert "op3" in captured.out
        assert "Total Time: 350.00ms" in captured.out


class TestBenchmarkSuiteCompareWith:
    """Test BenchmarkSuite.compare_with method."""

    def test_compare_with_empty_suites(self):
        # Arrange
        suite1 = BenchmarkSuite("Baseline")
        suite2 = BenchmarkSuite("Current")

        # Act
        comparison = suite1.compare_with(suite2)

        # Assert
        assert comparison.empty

    def test_compare_with_matching_operations(self):
        # Arrange
        baseline = BenchmarkSuite("Baseline")
        baseline.results.append(BenchmarkResult("parse", 100.0, 1))
        baseline.results.append(BenchmarkResult("render", 200.0, 1))

        current = BenchmarkSuite("Current")
        current.results.append(BenchmarkResult("parse", 50.0, 1))
        current.results.append(BenchmarkResult("render", 100.0, 1))

        # Act
        comparison = baseline.compare_with(current)

        # Assert
        assert len(comparison) == 2
        assert "speedup" in comparison.columns
        assert "improvement_pct" in comparison.columns
        # Speedup: 100/50 = 2x, 200/100 = 2x
        assert comparison[comparison["name"] == "parse"]["speedup"].iloc[0] == 2.0
        assert comparison[comparison["name"] == "render"]["speedup"].iloc[0] == 2.0
        # Improvement: (100-50)/100*100 = 50%
        assert comparison[comparison["name"] == "parse"]["improvement_pct"].iloc[0] == 50.0

    def test_compare_with_non_matching_operations(self):
        # Arrange
        baseline = BenchmarkSuite("Baseline")
        baseline.results.append(BenchmarkResult("op1", 100.0, 1))

        current = BenchmarkSuite("Current")
        current.results.append(BenchmarkResult("op2", 50.0, 1))

        # Act
        comparison = baseline.compare_with(current)

        # Assert - No matching names, so no comparison rows
        assert len(comparison) == 0


class TestBenchmarkDecorator:
    """Test benchmark_decorator function."""

    def test_decorator_single_iteration(self, capsys):
        # Arrange
        @benchmark_decorator(iterations=1, name="test_func")
        def sample_func(x):
            return x * 2

        # Act
        result = sample_func(5)

        # Assert
        assert result == 10
        captured = capsys.readouterr()
        assert "test_func" in captured.out
        assert "ms" in captured.out

    def test_decorator_multiple_iterations(self, capsys):
        # Arrange
        @benchmark_decorator(iterations=3)
        def sample_func():
            return 42

        # Act
        result = sample_func()

        # Assert
        assert result == 42
        captured = capsys.readouterr()
        assert "avg over 3 iterations" in captured.out

    def test_decorator_preserves_function_name(self):
        # Arrange
        @benchmark_decorator(iterations=1)
        def my_function():
            return "result"

        # Act & Assert
        assert my_function.__name__ == "my_function"

    def test_decorator_with_args_and_kwargs(self, capsys):
        # Arrange
        @benchmark_decorator(iterations=1, name="Complex Func")
        def complex_func(a, b, c=3):
            return a + b + c

        # Act
        result = complex_func(1, 2, c=4)

        # Assert
        assert result == 7
        captured = capsys.readouterr()
        assert "Complex Func" in captured.out


class TestTimer:
    """Test timer context manager."""

    def test_timer_prints_duration(self, capsys):
        # Arrange & Act
        with timer("test operation"):
            time.sleep(0.01)  # 10ms

        # Assert
        captured = capsys.readouterr()
        assert "test operation" in captured.out
        assert "ms" in captured.out

    def test_timer_with_exception_still_prints(self, capsys):
        # Arrange & Act & Assert
        with pytest.raises(RuntimeError):
            with timer("failing operation"):
                raise RuntimeError("Error")

        # Assert timing was still printed
        captured = capsys.readouterr()
        assert "failing operation" in captured.out
        assert "ms" in captured.out
