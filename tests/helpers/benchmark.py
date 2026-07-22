"""
Benchmark utilities for RING-5 performance testing.

Provides tools for measuring and comparing performance of critical operations.
"""

import functools
import logging
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, TypeVar

import pandas as pd

T = TypeVar("T")

logger = logging.getLogger(__name__)


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, name: str, duration_ms: float, iterations: int = 1):
        """
        Initialize benchmark result.

        Args:
            name: Name of the benchmarked operation
            duration_ms: Total duration in milliseconds
            iterations: Number of iterations performed
        """
        self.name = name
        self.duration_ms = duration_ms
        self.iterations = iterations
        self.avg_ms = duration_ms / iterations if iterations > 0 else 0

    def __str__(self) -> str:
        """String representation."""
        if self.iterations == 1:
            return f"{self.name}: {self.duration_ms:.2f}ms"
        else:
            return (
                f"{self.name}: {self.duration_ms:.2f}ms total "
                f"({self.avg_ms:.2f}ms avg over {self.iterations} iterations)"
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "iterations": self.iterations,
            "avg_ms": self.avg_ms,
        }


class BenchmarkSuite:
    """Suite for running multiple benchmarks."""

    # [impl->req~ring5.quality.performance-regression-gates~1]

    def __init__(self, name: str):
        """
        Initialize benchmark suite.

        Args:
            name: Name of the benchmark suite
        """
        self.name = name
        self.results: list[BenchmarkResult] = []

    @contextmanager
    def measure(self, operation_name: str) -> Generator[None, None, None]:
        """
        Context manager to measure operation duration.

        Args:
            operation_name: Name of the operation being measured

        Example:
            suite = BenchmarkSuite("Plot Generation")
            with suite.measure("Create bar plot"):
                # ... expensive operation
                pass
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000  # ms
            result = BenchmarkResult(operation_name, elapsed)
            self.results.append(result)

    def benchmark(
        self,
        func: Callable[..., T],
        *args: Any,
        iterations: int = 1,
        name: str | None = None,
        **kwargs: Any,
    ) -> T:
        """
        Benchmark a function call.

        Args:
            func: Function to benchmark
            *args: Positional arguments to func
            iterations: Number of times to run (default 1)
            name: Custom name for the benchmark
            **kwargs: Keyword arguments to func

        Returns:
            Result from last function call

        Raises:
            ValueError: If iterations < 1
        """
        if iterations < 1:
            raise ValueError("iterations must be at least 1")

        operation_name = name or func.__name__

        start = time.perf_counter()

        result: T = func(*args, **kwargs)
        for _ in range(iterations - 1):
            result = func(*args, **kwargs)

        elapsed = (time.perf_counter() - start) * 1000  # ms
        bench_result = BenchmarkResult(operation_name, elapsed, iterations)
        self.results.append(bench_result)

        return result

    def summary(self) -> pd.DataFrame:
        """
        Get summary DataFrame of all results.

        Returns:
            DataFrame with benchmark results
        """
        if not self.results:
            return pd.DataFrame()

        return pd.DataFrame([r.to_dict() for r in self.results])

    def print_summary(self) -> None:
        """Log formatted summary of all benchmarks."""
        logger.info("=" * 60)
        logger.info("Benchmark Suite: %s", self.name)
        logger.info("=" * 60)

        if not self.results:
            logger.info("No benchmarks run yet.")
            return

        for result in self.results:
            logger.info("  %s", result)

        total_time = sum(r.duration_ms for r in self.results)
        logger.info("=" * 60)
        logger.info("Total Time: %.2fms", total_time)
        logger.info("=" * 60)


def benchmark_decorator(
    iterations: int = 1, name: str | None = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to benchmark a function.

    Args:
        iterations: Number of times to run the function
        name: Custom name for the benchmark

    Example:
        @benchmark_decorator(iterations=10, name="Sort DataFrame")
        def sort_large_df(df):
            return df.sort_values('column')

    Raises:
        ValueError: If iterations < 1
    """
    if iterations < 1:
        raise ValueError("iterations must be at least 1")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            operation_name = name or func.__name__

            start = time.perf_counter()

            result: T = func(*args, **kwargs)
            for _ in range(iterations - 1):
                result = func(*args, **kwargs)

            elapsed = (time.perf_counter() - start) * 1000  # ms

            if iterations == 1:
                logger.info("%s: %.2fms", operation_name, elapsed)
            else:
                avg = elapsed / iterations
                logger.info(
                    "%s: %.2fms total (%.2fms avg over %d iterations)",
                    operation_name,
                    elapsed,
                    avg,
                    iterations,
                )

            # result is always bound (first call before loop)
            return result

        return wrapper

    return decorator


@contextmanager
def timer(name: str) -> Generator[None, None, None]:
    """
    Simple context manager timer.

    Args:
        name: Name of the timed operation

    Example:
        with timer("Data loading"):
            data = pd.read_csv("large_file.csv")
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("%s: %.2fms", name, elapsed)
