"""
Benchmark utilities for RING-5 performance testing.

Provides tools for measuring and comparing performance of critical operations.
"""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, TypeVar

import pandas as pd

T = TypeVar("T")


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "iterations": self.iterations,
            "avg_ms": self.avg_ms,
        }


class BenchmarkSuite:
    """Suite for running multiple benchmarks."""

    def __init__(self, name: str):
        """
        Initialize benchmark suite.

        Args:
            name: Name of the benchmark suite
        """
        self.name = name
        self.results: List[BenchmarkResult] = []

    @contextmanager
    def measure(self, operation_name: str) -> Any:
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
        name: Optional[str] = None,
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
        """
        operation_name = name or func.__name__

        result = None
        start = time.perf_counter()

        for _ in range(iterations):
            result = func(*args, **kwargs)

        elapsed = (time.perf_counter() - start) * 1000  # ms
        bench_result = BenchmarkResult(operation_name, elapsed, iterations)
        self.results.append(bench_result)

        return result  # type: ignore[return-value]

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
        """Print formatted summary of all benchmarks."""
        print(f"\n{'='*60}")
        print(f"Benchmark Suite: {self.name}")
        print(f"{'='*60}")

        if not self.results:
            print("No benchmarks run yet.")
            return

        for result in self.results:
            print(f"  {result}")

        total_time = sum(r.duration_ms for r in self.results)
        print(f"{'='*60}")
        print(f"Total Time: {total_time:.2f}ms")
        print(f"{'='*60}\n")

    def compare_with(self, other: "BenchmarkSuite") -> pd.DataFrame:
        """
        Compare this suite with another suite.

        Args:
            other: Another benchmark suite to compare against

        Returns:
            DataFrame showing performance comparison
        """
        df1 = self.summary()
        df2 = other.summary()

        if df1.empty or df2.empty:
            return pd.DataFrame()

        # Merge on operation name
        comparison = df1.merge(df2, on="name", suffixes=("_baseline", "_current"))

        # Calculate speedup
        comparison["speedup"] = comparison["avg_ms_baseline"] / comparison["avg_ms_current"]
        comparison["improvement_pct"] = (
            (comparison["avg_ms_baseline"] - comparison["avg_ms_current"])
            / comparison["avg_ms_baseline"]
            * 100
        )

        return comparison


def benchmark_decorator(
    iterations: int = 1, name: Optional[str] = None
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
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            operation_name = name or func.__name__

            result = None
            start = time.perf_counter()

            for _ in range(iterations):
                result = func(*args, **kwargs)

            elapsed = (time.perf_counter() - start) * 1000  # ms

            if iterations == 1:
                print(f"⏱️  {operation_name}: {elapsed:.2f}ms")
            else:
                avg = elapsed / iterations
                print(
                    f"⏱️  {operation_name}: {elapsed:.2f}ms total "
                    f"({avg:.2f}ms avg over {iterations} iterations)"
                )

            return result  # type: ignore[return-value]

        return wrapper

    return decorator


@contextmanager
def timer(name: str) -> Any:
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
        print(f"⏱️  {name}: {elapsed:.2f}ms")
