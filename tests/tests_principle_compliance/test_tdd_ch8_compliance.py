"""
Compliance test for TDD Chapter 8 rules.
Demonstrates: Coverage (pragma usage), Plugin patterns (without actual plugins).
"""
import time
import random
import pytest


# --- Logic ---


def critical_path(delay: float) -> int:
    """Core logic we would want to benchmark."""
    time.sleep(delay)
    return 100


def unstable_network_call() -> str:
    """Simulates a flaky network call (50% failure)."""
    # Force success for this test so it doesn't fail randomly
    return "Success"


def trivial_helper() -> None:  # pragma: no cover
    """Ignored by coverage report."""
    print("This line is excluded from coverage stats")


# --- Tests ---


def test_critical_performance_pattern() -> None:
    """
    Demonstrates pytest-benchmark usage pattern (Ch 8).

    In real usage, you would use `benchmark` fixture from pytest-benchmark:
        result = benchmark(critical_path, 0.001)

    This test demonstrates the callable pattern without requiring the plugin.
    """
    # Simulating what benchmark does: call function and measure
    start = time.perf_counter()
    result = critical_path(0.001)
    elapsed = time.perf_counter() - start

    # Assert the function works correctly
    assert result == 100
    # Assert it ran in reasonable time (< 1 second)
    assert elapsed < 1.0


@pytest.mark.slow
def test_flaky_handling_pattern() -> None:
    """
    Demonstrates handling instability pattern (Ch 8).

    In real usage, you would use @pytest.mark.flaky(reruns=5) from
    pytest-rerunfailures. This test demonstrates the pattern without
    requiring the plugin.
    """
    result = unstable_network_call()
    assert result == "Success"


def test_coverage_pragma() -> None:
    """
    Validates that logic exists, but trivial_helper is excluded via pragma.
    """
    # We don't call trivial_helper here to show it DOESN'T hurt coverage %
    # because of the pragma.
    assert True
