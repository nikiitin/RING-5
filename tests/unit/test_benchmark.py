"""
Tests for benchmark utilities.

Exercises benchmark model behavior, validation, and serialization:
- Fixture-first design for test data
- Parametrization for multiple scenarios
- Testing timing logic with tolerance
- caplog for capturing log output
"""

import logging
import time
from typing import Any

import pytest

from tests.helpers.benchmark import (
    BenchmarkResult,
    BenchmarkSuite,
    benchmark_decorator,
    timer,
)


@pytest.fixture
def sample_benchmark_result() -> BenchmarkResult:
    """Create a sample benchmark result."""
    return BenchmarkResult(name="test_op", duration_ms=150.5, iterations=10)


@pytest.fixture
def sample_suite() -> Any:
    """Create a benchmark suite with some results."""
    suite = BenchmarkSuite("Test Suite")
    suite.results.append(BenchmarkResult("op1", 100.0, 1))
    suite.results.append(BenchmarkResult("op2", 200.0, 5))
    suite.results.append(BenchmarkResult("op3", 50.0, 1))
    return suite


class TestBenchmarkResult:
    """Test BenchmarkResult container."""

    def test_initialization(self) -> None:
        result = BenchmarkResult("parse_file", 123.45, iterations=5)

        assert result.name == "parse_file"
        assert result.duration_ms == 123.45
        assert result.iterations == 5
        assert result.avg_ms == 123.45 / 5

    def test_single_iteration_avg(self) -> None:
        result = BenchmarkResult("single_op", 100.0, iterations=1)

        assert result.avg_ms == 100.0

    def test_zero_iterations_avg(self) -> None:
        result = BenchmarkResult("zero_op", 0.0, iterations=0)

        assert result.avg_ms == 0.0  # No division by zero

    def test_str_single_iteration(self) -> None:
        result = BenchmarkResult("test_op", 42.5, iterations=1)

        output = str(result)

        assert "test_op" in output
        assert "42.5" in output
        assert "avg" not in output.lower()  # Single iteration doesn't show avg

    def test_str_multiple_iterations(self) -> None:
        result = BenchmarkResult("test_op", 200.0, iterations=10)

        output = str(result)

        assert "test_op" in output
        assert "200.0" in output
        assert "20.0" in output  # avg
        assert "10 iterations" in output

    def test_to_dict(self, sample_benchmark_result: Any) -> None:

        result = sample_benchmark_result

        data = result.to_dict()

        assert data["name"] == "test_op"
        assert data["duration_ms"] == 150.5
        assert data["iterations"] == 10
        assert data["avg_ms"] == 15.05


class TestBenchmarkSuiteInitialization:
    """Test BenchmarkSuite initialization."""

    def test_initialization(self) -> None:
        suite = BenchmarkSuite("My Suite")

        assert suite.name == "My Suite"
        assert suite.results == []


class TestBenchmarkSuiteMeasure:
    """Test BenchmarkSuite.measure context manager."""

    def test_measure_records_duration(self) -> None:
        suite = BenchmarkSuite("Test")

        with suite.measure("sleep_test"):
            time.sleep(0.01)  # 10ms

        assert len(suite.results) == 1
        assert suite.results[0].name == "sleep_test"
        assert suite.results[0].duration_ms >= 10.0  # At least 10ms
        assert suite.results[0].iterations == 1

    def test_measure_multiple_operations(self) -> None:
        suite = BenchmarkSuite("Multi")

        with suite.measure("op1"):
            time.sleep(0.005)
        with suite.measure("op2"):
            time.sleep(0.005)

        assert len(suite.results) == 2
        assert suite.results[0].name == "op1"
        assert suite.results[1].name == "op2"

    def test_measure_with_exception_still_records(self) -> None:
        suite = BenchmarkSuite("Error Test")

        with pytest.raises(ValueError):
            with suite.measure("failing_op"):
                raise ValueError("Test error")

        assert len(suite.results) == 1
        assert suite.results[0].name == "failing_op"


class TestBenchmarkSuiteBenchmark:
    """Test BenchmarkSuite.benchmark method."""

    def test_benchmark_single_iteration(self) -> None:
        suite = BenchmarkSuite("Func Test")

        def add_numbers(a: Any, b: Any) -> None:

            return a + b

        result = suite.benchmark(add_numbers, 5, 10)

        assert result == 15
        assert len(suite.results) == 1
        assert suite.results[0].name == "add_numbers"
        assert suite.results[0].iterations == 1

    def test_benchmark_multiple_iterations(self) -> None:
        suite = BenchmarkSuite("Multi Iter")
        counter = [0]

        def increment() -> Any:
            counter[0] += 1
            return counter[0]

        result = suite.benchmark(increment, iterations=5)

        assert result == 5  # Last iteration
        assert counter[0] == 5  # Called 5 times
        assert suite.results[0].iterations == 5

    def test_benchmark_with_custom_name(self) -> None:
        suite = BenchmarkSuite("Named")

        suite.benchmark(lambda: 42, name="custom_operation")

        assert suite.results[0].name == "custom_operation"

    def test_benchmark_with_kwargs(self) -> None:
        suite = BenchmarkSuite("Kwargs Test")

        def divide(numerator: Any, denominator: Any = 1) -> None:

            return numerator / denominator

        result = suite.benchmark(divide, 10, denominator=2)

        assert result == 5.0


class TestBenchmarkSuiteSummary:
    """Test BenchmarkSuite.summary method."""

    def test_summary_empty_suite(self) -> None:
        suite = BenchmarkSuite("Empty")

        df = suite.summary()

        assert df.empty

    def test_summary_with_results(self, sample_suite: Any) -> None:

        suite = sample_suite

        df = suite.summary()

        assert len(df) == 3
        assert list(df.columns) == ["name", "duration_ms", "iterations", "avg_ms"]
        assert df["name"].tolist() == ["op1", "op2", "op3"]
        assert df["duration_ms"].tolist() == [100.0, 200.0, 50.0]


class TestBenchmarkSuitePrintSummary:
    """Test BenchmarkSuite.print_summary method."""

    def test_print_summary_empty_suite(self, caplog: Any) -> None:

        suite = BenchmarkSuite("Empty")

        with caplog.at_level(logging.INFO, logger="tests.helpers.benchmark"):
            suite.print_summary()

        assert "Empty" in caplog.text
        assert "No benchmarks run yet" in caplog.text

    def test_print_summary_with_results(self, sample_suite: Any, caplog: Any) -> None:

        suite = sample_suite

        with caplog.at_level(logging.INFO, logger="tests.helpers.benchmark"):
            suite.print_summary()

        assert "Test Suite" in caplog.text
        assert "op1" in caplog.text
        assert "op2" in caplog.text
        assert "op3" in caplog.text
        assert "Total Time: 350.00ms" in caplog.text


class TestBenchmarkDecorator:
    """Test benchmark_decorator function."""

    def test_decorator_single_iteration(self, caplog: Any) -> None:

        @benchmark_decorator(iterations=1, name="test_func")
        def sample_func(x: Any) -> None:

            return x * 2

        with caplog.at_level(logging.INFO, logger="tests.helpers.benchmark"):
            result = sample_func(5)

        assert result == 10
        assert "test_func" in caplog.text
        assert "ms" in caplog.text

    def test_decorator_multiple_iterations(self, caplog: Any) -> None:

        @benchmark_decorator(iterations=3)
        def sample_func() -> int:
            return 42

        with caplog.at_level(logging.INFO, logger="tests.helpers.benchmark"):
            result = sample_func()

        assert result == 42
        assert "avg over 3 iterations" in caplog.text

    def test_decorator_preserves_function_name(self) -> None:
        @benchmark_decorator(iterations=1)
        def my_function() -> str:
            return "result"

        assert my_function.__name__ == "my_function"

    def test_decorator_with_args_and_kwargs(self, caplog: Any) -> None:

        @benchmark_decorator(iterations=1, name="Complex Func")
        def complex_func(a: Any, b: Any, c: Any = 3) -> None:

            return a + b + c

        with caplog.at_level(logging.INFO, logger="tests.helpers.benchmark"):
            result = complex_func(1, 2, c=4)

        assert result == 7
        assert "Complex Func" in caplog.text


class TestTimer:
    """Test timer context manager."""

    def test_timer_prints_duration(self, caplog: Any) -> None:

        with caplog.at_level(logging.INFO, logger="tests.helpers.benchmark"):
            with timer("test operation"):
                time.sleep(0.01)  # 10ms

        assert "test operation" in caplog.text
        assert "ms" in caplog.text

    def test_timer_with_exception_still_prints(self, caplog: Any) -> None:

        with caplog.at_level(logging.INFO, logger="tests.helpers.benchmark"):
            with pytest.raises(RuntimeError):
                with timer("failing operation"):
                    raise RuntimeError("Error")

        assert "failing operation" in caplog.text
        assert "ms" in caplog.text
